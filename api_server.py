"""
api_server.py
=============
Flask Web App API serveri (Telegram Mini App uchun) va achievements tizimi.
Bu faylda: check_achievements_toplevel, Flask endpointlari, inline_share_handler.
Bog'liq fayllar: config.py, database.py, languages.py, keyboards.py
"""

import os
import json
import threading
from datetime import datetime, date
from config import BOT_TOKEN, ADMIN_ID, mongo_col, groups_col
from database import load_user, save_user, load_all_users, count_users
from languages import T, get_lang, LANGS, get_rank, today_uz5
from keyboards import bot
from handlers_habits import _ACHIEVEMENTS, check_achievements_toplevel

# ============================================================
#  WEB APP API SERVER (Flask)
# ============================================================

try:
    from flask import Flask, jsonify, request

    api_app = Flask(__name__)

    # ── Simple in-memory rate limiter ──
    import collections
    _rl_buckets = collections.defaultdict(list)  # key -> [timestamp, ...]
    _rl_lock    = __import__('threading').Lock()

    def _rate_limit(key: str, limit: int, window: int = 60) -> bool:
        """True = ruxsat, False = limit oshdi. window=soniya, limit=max so'rov."""
        now = _time.time()
        with _rl_lock:
            bucket = _rl_buckets[key]
            # Eskilarni tozala
            _rl_buckets[key] = [t for t in bucket if now - t < window]
            if len(_rl_buckets[key]) >= limit:
                return False
            _rl_buckets[key].append(now)
            return True

    def rate_limit_check(uid=None, limit=60, window=60):
        """Decorator emas, to'g'ridan-to'g'ri chaqiriladigan tekshirish."""
        key = f"uid:{uid}" if uid else f"ip:{request.remote_addr}"
        if not _rate_limit(key, limit, window):
            return jsonify({"ok": False, "error": "Too many requests"}), 429
        return None


    @api_app.after_request
    def add_cors(response):
        response.headers["Access-Control-Allow-Origin"]  = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        return response

    @api_app.route("/api/rating", methods=["OPTIONS"])
    @api_app.route("/api/profile/<int:uid>", methods=["OPTIONS"])
    @api_app.route("/api/groups/<int:uid>", methods=["OPTIONS"])
    def options_preflight(**kwargs):
        return jsonify({}), 200

    # ── Telegram WebApp initData tekshirish ──
    import hmac, hashlib, urllib.parse, time as _time

    def verify_init_data(init_data_raw: str) -> int | None:
        """
        Telegram WebApp initData ni HMAC-SHA256 bilan tekshiradi.
        Muvaffaqiyatli bo'lsa user_id qaytaradi, aks holda None.
        """
        if not init_data_raw:
            print("[auth] FAIL: init_data_raw bo'sh")
            return None
        try:
            params = dict(urllib.parse.parse_qsl(init_data_raw, keep_blank_values=True))
            received_hash = params.pop("hash", None)
            if not received_hash:
                print("[auth] FAIL: hash yo'q")
                return None
            data_check_string = "\n".join(
                f"{k}={v}" for k, v in sorted(params.items())
            )
            secret_key = hmac.new(BOT_TOKEN.encode(), b"WebAppData", hashlib.sha256).digest()
            computed   = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(computed, received_hash):
                print(f"[auth] FAIL: hash mos kelmadi. computed={computed[:10]}... received={received_hash[:10]}...")
                return None
            auth_date = int(params.get("auth_date", 0))
            age = int(_time.time() - auth_date)
            if age > 604800:
                print(f"[auth] FAIL: auth_date eskirgan ({age} soniya oldin)")
                return None
            import json as _json
            user_obj = _json.loads(params.get("user", "{}"))
            uid = int(user_obj.get("id", 0)) or None
            if uid:
                print(f"[auth] OK: uid={uid}, age={age}s")
            else:
                print("[auth] FAIL: user id topilmadi")
            return uid
        except Exception as e:
            print(f"[auth] EXCEPTION: {e}")
            return None

    def require_auth(f):
        """Decorator: X-User-Id header orqali uid tekshiradi."""
        from functools import wraps
        @wraps(f)
        def decorated(*args, **kwargs):
            if request.method == "OPTIONS":
                return f(*args, **kwargs)
            uid_in_route = kwargs.get("uid")
            try:
                header_uid = int(request.headers.get("X-User-Id", 0))
            except Exception:
                header_uid = 0
            if not header_uid:
                print(f"[auth] FAIL: X-User-Id yo'q. endpoint={request.path}")
                return jsonify({"ok": False, "error": "Unauthorized"}), 401
            if uid_in_route is not None and header_uid != uid_in_route:
                print(f"[auth] FAIL: uid mos kelmadi. header={header_uid}, route={uid_in_route}")
                return jsonify({"ok": False, "error": "Forbidden"}), 403
            rl_err = rate_limit_check(uid=header_uid, limit=60, window=60)
            if rl_err:
                return rl_err
            return f(*args, **kwargs)
        return decorated

    def _tz_today():
        from datetime import timezone, timedelta
        tz_uz = timezone(timedelta(hours=5))
        return datetime.now(tz_uz)

    def _is_done_today(uid_done):
        """done_today[uid_str] qiymatidan foydalanuvchi bajardimi yoki yo'qligini qaytaradi."""
        if isinstance(uid_done, bool):
            return uid_done
        if isinstance(uid_done, dict):
            return True in uid_done.values()
        return False

    def _calc_best_streak(u):
        """Foydalanuvchining eng uzun streakini qaytaradi (saqlangan yoki joriy habitlardan kattasi)."""
        return max(u.get("best_streak", 0), max((h.get("streak", 0) for h in u.get("habits", [])), default=0))

    @api_app.route("/api/rating")
    def api_rating():
        # Rate limit: 30 so'rov/daqiqa per IP (ochiq endpoint)
        rl_err = rate_limit_check(uid=None, limit=30, window=60)
        if rl_err:
            return rl_err
        from datetime import timedelta
        sort_by = request.args.get("sort", "points")   # points | streak | score
        period  = request.args.get("period", "month")  # month | week | all
        uid_arg = request.args.get("uid", "0")

        today_dt  = _tz_today()
        today_str = today_dt.strftime("%Y-%m-%d")
        days      = [(today_dt - timedelta(days=6-i)).strftime("%Y-%m-%d") for i in range(7)]
        day_lbls  = [(today_dt - timedelta(days=6-i)).strftime("%d") for i in range(7)]

        all_users = load_all_users()
        total_users = len(all_users)

        entries = []
        for uid, udata in all_users.items():
            done_log  = udata.get("done_log", {})
            bot_start = min(done_log.keys()) if done_log else today_str
            # score = oxirgi 30 kunda faol kunlar soni
            score = sum(1 for d, v in done_log.items() if v and d >= (today_dt - timedelta(days=30)).strftime("%Y-%m-%d"))
            # Faol itemlarni yig'amiz (reyting'da ko'rsatish uchun)
            _ITEM_EMOJI = {
                "pet_cat": "🐱", "pet_dog": "🐶", "pet_rabbit": "🐰",
                "badge_fire": "🔥", "badge_star": "⭐", "badge_secret": "👑",
                "car_sport": "🏎️",
            }
            _items = []
            _shown_ids = set()
            if udata.get("active_pet"):
                _items.append(_ITEM_EMOJI.get(udata["active_pet"], udata["active_pet"]))
                _shown_ids.add(udata["active_pet"])
            if udata.get("active_badge"):
                _items.append(_ITEM_EMOJI.get(udata["active_badge"], udata["active_badge"]))
                _shown_ids.add(udata["active_badge"])
            if udata.get("active_car"):
                _items.append(_ITEM_EMOJI.get(udata["active_car"], udata["active_car"]))
                _shown_ids.add(udata["active_car"])
            raw_inv = udata.get("inventory", {})
            if isinstance(raw_inv, list):
                inv_dict = {i: 1 for i in raw_inv}
            else:
                inv_dict = dict(raw_inv)
            for iid, qty in inv_dict.items():
                if qty > 0 and iid not in _shown_ids and iid in _ITEM_EMOJI:
                    _items.append(_ITEM_EMOJI[iid])
                    _shown_ids.add(iid)
            if udata.get("streak_shields", 0) > 0: _items.append("🛡")
            if udata.get("bonus_2x_active") and udata.get("bonus_2x_date") == today_str: _items.append("⚡")
            if udata.get("bonus_3x_active") and udata.get("bonus_3x_date") == today_str: _items.append("🚀")
            if udata.get("xp_booster_days", 0) > 0: _items.append("💎")
            entries.append({
                "uid":          uid,
                "name":         udata.get("name", "?"),
                "points":       udata.get("points", 0),
                "streak":       udata.get("streak", 0),
                "score":        score,
                "photo_url":    udata.get("photo_url", ""),
                "done_log":     done_log,
                "bot_start":    bot_start,
                "habits_count": len(udata.get("habits", [])),
                "jon":          round(udata.get("jon", 100)),
                "active_items": " ".join(_items),
            })

        # Saralash
        if sort_by == "streak":
            entries.sort(key=lambda x: x["streak"], reverse=True)
        elif sort_by in ("score", "active"):
            entries.sort(key=lambda x: x["score"], reverse=True)
        else:
            entries.sort(key=lambda x: x["points"], reverse=True)

        top = entries[:10]

        # Caller entry
        caller_entry = None
        try:
            caller_uid = str(int(uid_arg))
            caller_idx = next((i for i, e in enumerate(entries) if e["uid"] == caller_uid), None)
            if caller_idx is not None:
                caller_entry = dict(entries[caller_idx])
                caller_entry["rank"] = caller_idx + 1
        except Exception:
            pass

        return jsonify({
            "today":        today_str,
            "days":         days,
            "day_labels":   day_lbls,
            "users":        top,
            "total_users":  total_users,
            "sort_by":      sort_by,
            "period":       period,
            "caller_entry": caller_entry,
        })

    @api_app.route("/api/profile/<int:uid>")
    @require_auth
    def api_profile(uid):
        u = load_user(uid)
        # Rank: load_all_users o'rniga tez MongoDB so'rov
        my_points  = u.get("points", 0)
        rank       = mongo_col.count_documents({
            "_id":    {"$not": {"$regex": "^_"}},
            "points": {"$gt": my_points}
        }) + 1
        total_users = mongo_col.count_documents({"_id": {"$not": {"$regex": "^_"}}})
        habits = []
        for h in u.get("habits", []):
            habits.append({
                "name":   h.get("name",""),
                "icon":   h.get("icon","✅"),
                "streak": h.get("streak",0),
            })

        # best_streak va total_done_all hisoblash
        best_streak    = _calc_best_streak(u)
        total_done_all = sum(h.get("total_done", 0) for h in u.get("habits", []))

        today_str = _tz_today().strftime("%Y-%m-%d")
        return jsonify({
            "name":             u.get("name","?"),
            "points":           u.get("points",0),
            "streak":           u.get("streak",0),
            "jon":              u.get("jon",100),
            "is_vip":           u.get("is_vip",False),
            "rank":             rank,
            "total_users":      total_users,
            "joined_at":        u.get("joined_at",""),
            "best_streak":      best_streak,
            "best_streak_date": u.get("best_streak_date", ""),
            "total_done_all":   total_done_all,
            "habits":           habits,
            "xp_booster_days":  u.get("xp_booster_days", 0),
            "active_pet":       {"pet_cat":"🐱","pet_dog":"🐶","pet_rabbit":"🐰"}.get(u.get("active_pet",""), u.get("active_pet","")),
            "active_badge":     {"badge_fire":"🔥","badge_star":"⭐","badge_secret":"👑"}.get(u.get("active_badge",""), u.get("active_badge","")),
            "active_car":       {"car_sport":"🏎️"}.get(u.get("active_car",""), u.get("active_car","")),
            "streak_shields":   u.get("streak_shields", 0),
            "bonus_2x_active":  u.get("bonus_2x_active", False) and u.get("bonus_2x_date","") == today_str,
            "bonus_3x_active":  u.get("bonus_3x_active", False) and u.get("bonus_3x_date","") == today_str,
            "dark_mode":        u.get("dark_mode", False),
            "earned_ach":       len([a for a in u.get("achievements", []) if isinstance(a, dict)]),
            "total_ach":        len(ACHIEVEMENTS),
            "display_name":     u.get("display_name", ""),
            "photo_url":        u.get("photo_url", ""),
            "evening_notify":   u.get("evening_notify", True),
            "lang":             u.get("lang", "uz"),
            "phone":            u.get("phone", ""),
            "ref_count":        len(u.get("referrals", [])),
            "ref_link":         f"https://t.me/{get_bot_username()}?start=ref_{uid}",
        })

    @api_app.route("/api/habits/<int:uid>", methods=["GET"])
    @require_auth
    def api_habits_get(uid):
        u = load_user(uid)
        habits = []
        for h in u.get("habits", []):
            habits.append({
                "id":           h.get("id",""),
                "name":         h.get("name",""),
                "icon":         h.get("icon","✅"),
                "time":         h.get("time","vaqtsiz"),
                "type":         h.get("type","simple"),
                "repeat_count": h.get("repeat_count",1),
                "streak":       h.get("streak",0),
                "total_done":   h.get("total_done",0),
            })
        return jsonify({"habits": habits, "jon": round(u.get("jon", 100))})

    @api_app.route("/api/habits/<int:uid>", methods=["POST"])
    @require_auth
    def api_habits_add(uid):
        import uuid, re as _re
        data  = request.get_json() or {}
        name  = (data.get("name") or "").strip()
        icon  = (data.get("icon") or "✅").strip()
        time_ = (data.get("time") or "vaqtsiz").strip()
        hab_type     = data.get("type", "simple")
        try:
            repeat_count = max(1, min(int(data.get("repeat_count", 1)), 100))
        except (ValueError, TypeError):
            repeat_count = 1
        if not name:
            return jsonify({"ok": False, "error": "Nom bo'sh"}), 400
        if len(name) > 100:
            return jsonify({"ok": False, "error": "Nom 100 belgidan oshmasin"}), 400
        if len(icon) > 10:
            icon = "✅"
        if hab_type not in ("simple", "repeat"):
            hab_type = "simple"
        if time_ != "vaqtsiz" and not _re.match(r"^\d{2}:\d{2}$", time_):
            time_ = "vaqtsiz"
        u = load_user(uid)
        if len(u.get("habits", [])) >= 15:
            return jsonify({"ok": False, "error": "Odatlar soni 15 tadan oshmasin"}), 400
        new_habit = {
            "id":           str(uuid.uuid4())[:8],
            "name":         name,
            "icon":         icon,
            "time":         time_,
            "type":         "repeat" if hab_type == "repeat" else "simple",
            "repeat_count": repeat_count if hab_type == "repeat" else 1,
            "streak":       0,
            "total_done":   0,
            "done_today_count": 0,
            "last_done":    None,
            "created_at":   today_uz5(),
        }
        habits = u.get("habits", [])
        habits.append(new_habit)
        u["habits"] = habits
        save_user(uid, u)
        try:
            schedule_habit(uid, new_habit)
        except Exception as _e: print(f"[warn] schedule_habit: {_e}")
        return jsonify({"ok": True, "habit": new_habit})

    @api_app.route("/api/habits/<int:uid>/<hid>", methods=["PUT"])
    @require_auth
    def api_habits_edit(uid, hid):
        import re as _re
        data  = request.get_json() or {}
        name  = (data.get("name") or "").strip()
        icon  = (data.get("icon") or "✅").strip()
        time_ = (data.get("time") or "vaqtsiz").strip()
        type_ = (data.get("type") or "simple").strip()
        try:
            repeat_count = max(1, min(int(data.get("repeat_count") or 1), 100))
        except (ValueError, TypeError):
            repeat_count = 1
        if not name:
            return jsonify({"ok": False, "error": "Nom bo'sh"}), 400
        if len(name) > 100:
            return jsonify({"ok": False, "error": "Nom 100 belgidan oshmasin"}), 400
        if len(icon) > 10:
            icon = "✅"
        if type_ not in ("simple", "repeat"):
            type_ = "simple"
        if time_ != "vaqtsiz" and not _re.match(r"^\d{2}:\d{2}$", time_):
            time_ = "vaqtsiz"
        u = load_user(uid)
        habits = u.get("habits", [])
        for h in habits:
            if h.get("id") == hid:
                h["name"] = name
                h["icon"] = icon
                h["time"] = time_
                h["type"] = type_
                h["repeat_count"] = repeat_count if type_ == "repeat" else 1
                break
        else:
            return jsonify({"ok": False, "error": "Topilmadi"}), 404
        u["habits"] = habits
        save_user(uid, u)
        # Yangi vaqt bilan qayta rejalashtirish
        edited_h = next((h for h in habits if h.get("id") == hid), None)
        if edited_h:
            try:
                schedule_habit(uid, edited_h)
            except Exception as _e:
                print(f"[warn] schedule_habit edit: {_e}")
        return jsonify({"ok": True})

    @api_app.route("/api/habits/<int:uid>/<hid>", methods=["DELETE"])
    @require_auth
    def api_habits_delete(uid, hid):
        u = load_user(uid)
        habits = u.get("habits", [])
        new_habits = [h for h in habits if h.get("id") != hid]
        if len(new_habits) == len(habits):
            return jsonify({"ok": False, "error": "Topilmadi"}), 404
        u["habits"] = new_habits
        save_user(uid, u)
        try:
            unschedule_habit_today(uid, hid)
        except Exception as _e:
            print(f"[warn] unschedule_habit_today delete: {_e}")
        return jsonify({"ok": True})

    @api_app.route("/api/groups/<int:uid>", methods=["GET", "POST"])
    @require_auth
    def api_groups(uid):
        if request.method == "POST":
            import uuid as _uuid
            data       = request.get_json(force=True, silent=True) or {}
            name       = (data.get("name") or "").strip()
            habit_name = (data.get("habit_name") or "").strip()
            habit_time = (data.get("habit_time") or "vaqtsiz").strip()
            if not name or not habit_name:
                return jsonify({"ok": False, "error": "Ism va odat nomi kerak"})
            u = load_user(uid)
            admin_groups = [g for g in u.get("groups", []) if str(g.get("admin_id", "")) == str(uid)]
            if len(admin_groups) >= 3:
                return jsonify({"ok": False, "error": "Siz admin sifatida 3 tadan ko'p guruh yarata olmaysiz"})
            g_id = str(_uuid.uuid4())[:8]
            group = {
                "id":         g_id,
                "name":       name,
                "habit_name": habit_name,
                "habit_time": habit_time,
                "admin_id":   str(uid),
                "members":    [str(uid)],
                "streak":     0,
                "created_at": today_uz5(),
            }
            save_group(g_id, group)
            groups = u.get("groups", [])
            groups.append({"id": g_id, "name": name, "admin_id": str(uid)})
            u["groups"] = groups
            save_user(uid, u)
            inv_link = f"https://t.me/{get_bot_username()}?start=grp_{g_id}"
            return jsonify({"ok": True, "gid": g_id, "invite_link": inv_link})
        # GET
        try:
            all_groups = list(mongo_db["groups"].find({"members": str(uid)}))
        except Exception:
            all_groups = []
        result = []
        today_grp = today_uz5()
        for g in all_groups:
            members_raw = g.get("members", [])
            members = []
            for mid in members_raw[:10]:
                mu = load_user(int(mid))
                members.append({"name": mu.get("name","?"), "points": mu.get("points",0)})
            members.sort(key=lambda x: x["points"], reverse=True)
            # done_today_me: foydalanuvchi bugun bajardimi?
            done_today = g.get("done_today", {}) if g.get("done_date") == today_grp else {}
            uid_done = done_today.get(str(uid), {})
            done_today_me = _is_done_today(uid_done)
            # Haftalik maqsad progress hisoblash
            from datetime import timezone as _tz_wg, timedelta as _td_wg
            _tz_uz_wg  = _tz_wg(_td_wg(hours=5))
            _now_wg    = datetime.now(_tz_uz_wg)
            # Haftaning dushanbasi
            _week_start = (_now_wg - _td_wg(days=_now_wg.weekday())).strftime("%Y-%m-%d")
            _week_days  = [(_now_wg - _td_wg(days=_now_wg.weekday()-i)).strftime("%Y-%m-%d") for i in range(7)]
            _done_log   = g.get("member_done_log", {})
            _weekly_done = 0
            for _mid in members_raw:
                _mid_log = _done_log.get(str(_mid), {})
                for _wd in _week_days:
                    if _mid_log.get(_wd):
                        _weekly_done += 1
            _weekly_total  = len(members_raw) * 7  # maksimal mumkin
            _weekly_goal   = g.get("weekly_goal", 0)
            result.append({
                "gid":          g.get("id", str(g.get("_id", ""))),
                "name":         g.get("name","Guruh"),
                "habit_name":   g.get("habit_name", "—"),
                "member_count": len(members_raw),
                "members":      members[:5],
                "streak":       g.get("streak", 0),
                "is_admin":     g.get("admin_id") == str(uid),
                "invite_link":  f"https://t.me/{get_bot_username()}?start=grp_{g.get('id','')}",  # barcha a'zolarga
                "done_today_me": done_today_me,
                "weekly_goal":  _weekly_goal,
                "weekly_done":  _weekly_done,
                "weekly_total": _weekly_total,
            })
        return jsonify({"groups": result})

    @api_app.route("/api/groups/<int:uid>/<gid>/checkin", methods=["POST"])
    @require_auth
    def api_groups_checkin(uid, gid):
        try:
            g = mongo_db["groups"].find_one({"id": gid})
        except Exception:
            return jsonify({"ok": False, "error": "Guruh topilmadi"})
        if not g:
            return jsonify({"ok": False, "error": "Guruh topilmadi"})
        members = g.get("members", [])
        if str(uid) not in [str(m) for m in members]:
            return jsonify({"ok": False, "error": "Siz bu guruh a'zosi emassiz"})
        today = today_uz5()
        if g.get("done_date") != today:
            g["done_today"] = {}
            g["done_date"]  = today
        done_today = g.get("done_today", {})
        uid_str = str(uid)
        # Toggle: allaqachon bajarilgan bo'lsa — bekor qilish
        uid_done = done_today.get(uid_str, {})
        already_done = _is_done_today(uid_done)
        u = load_user(uid)
        if already_done:
            done_today[uid_str] = False
            g["done_today"] = done_today
            # member_done_log dan bugungi yozuvni olib tashlash
            done_log = g.get("member_done_log", {})
            if uid_str in done_log:
                done_log[uid_str].pop(today, None)
            g["member_done_log"] = done_log
            mongo_db["groups"].replace_one({"id": gid}, g)
            u["points"] = max(0, u.get("points", 0) - 5)
            save_user(uid, u)
            return jsonify({"ok": True, "done": False, "points": u.get("points", 0)})
        # Bajarildi
        done_today[uid_str] = {"main": True}
        g["done_today"] = done_today
        done_count = sum(1 for v in done_today.values() if (v is True or (isinstance(v, dict) and True in v.values())))
        all_done = done_count == len(members)
        if all_done and g.get("streak_date") != today:
            g["streak"]      = g.get("streak", 0) + 1
            g["streak_date"] = today
        # member_done_log
        done_log = g.get("member_done_log", {})
        if uid_str not in done_log:
            done_log[uid_str] = {}
        already_logged_today = done_log[uid_str].get(today, False)
        done_log[uid_str][today] = True
        g["member_done_log"] = done_log
        # member_streaks
        if not already_logged_today:
            from datetime import timezone, timedelta as _td
            _tz = timezone(_td(hours=5))
            yesterday_s = (datetime.now(_tz) - _td(days=1)).strftime("%Y-%m-%d")
            m_streaks = g.get("member_streaks", {})
            if done_log[uid_str].get(yesterday_s):
                m_streaks[uid_str] = m_streaks.get(uid_str, 0) + 1
            else:
                m_streaks[uid_str] = 1
            g["member_streaks"] = m_streaks
        mongo_db["groups"].replace_one({"id": gid}, g)
        u["points"] = u.get("points", 0) + 5
        save_user(uid, u)
        m_streak_val = g.get("member_streaks", {}).get(uid_str, 1)
        return jsonify({
            "ok":       True,
            "done":     True,
            "points":   u.get("points", 0),
            "streak":   m_streak_val,
            "all_done": all_done,
        })

    @api_app.route("/api/groups/<int:uid>/<gid>/goal", methods=["PUT"])
    @require_auth
    def api_groups_set_goal(uid, gid):
        """Admin haftalik guruh maqsadini belgilaydi."""
        data = request.get_json(force=True, silent=True) or {}
        try:
            g = mongo_db["groups"].find_one({"id": gid})
        except Exception:
            return jsonify({"ok": False, "error": "Guruh topilmadi"})
        if not g:
            return jsonify({"ok": False, "error": "Guruh topilmadi"})
        if g.get("admin_id") != str(uid):
            return jsonify({"ok": False, "error": "Faqat admin maqsad belgilaydi"})
        try:
            goal = int(data.get("goal", 0))
            if goal < 0 or goal > 9999:
                raise ValueError
        except (ValueError, TypeError):
            return jsonify({"ok": False, "error": "Noto'g'ri qiymat"})
        g["weekly_goal"] = goal
        mongo_db["groups"].replace_one({"id": gid}, g)
        return jsonify({"ok": True, "weekly_goal": goal})

    @api_app.route("/api/groups/<int:uid>/<gid>", methods=["DELETE"])
    @require_auth
    def api_groups_delete(uid, gid):
        try:
            g = mongo_db["groups"].find_one({"id": gid})
        except Exception:
            return jsonify({"ok": False, "error": "Guruh topilmadi"})
        if not g:
            return jsonify({"ok": False, "error": "Guruh topilmadi"})
        if g.get("admin_id") != str(uid):
            return jsonify({"ok": False, "error": "Faqat admin o'chira oladi"})
        try:
            mongo_db["groups"].delete_one({"id": gid})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)})
        # Barcha a'zolar user profilidan ham o'chirish
        for mid in g.get("members", []):
            try:
                mu = load_user(int(mid))
                mu["groups"] = [gg for gg in mu.get("groups", []) if gg.get("id") != gid]
                save_user(int(mid), mu)
            except Exception:
                pass
        return jsonify({"ok": True})

    @api_app.route("/api/today/<int:uid>")
    @require_auth
    def api_today(uid):
        u = load_user(uid)
        today = today_uz5()
        habits = u.get("habits", [])
        result = []
        done_count = 0
        for h in habits:
            hab_type  = h.get("type", "simple")
            rep_count = h.get("repeat_count", 1)
            today_count = 0
            if hab_type == "repeat" and rep_count > 1:
                if h.get("done_date") == today:
                    today_count = h.get("done_today_count", 0)
                is_done = today_count >= rep_count
            else:
                is_done = h.get("last_done") == today
            if is_done:
                done_count += 1
            result.append({
                "id":           h["id"],
                "name":         h["name"],
                "icon":         h.get("icon", "✅"),
                "time":         h.get("time", "vaqtsiz"),
                "done":         is_done,
                "streak":       h.get("streak", 0),
                "repeat_count": rep_count,
                "today_count":  today_count,
                "type":         hab_type,
            })
        total = len(habits)
        percent = round(done_count / total * 100) if total else 0
        jon_pct = min(100, max(0, u.get("jon", 100)))
        return jsonify({
            "habits":     result,
            "today":      today,
            "done_count": done_count,
            "total":      total,
            "percent":    percent,
            "jon":        jon_pct,
            "points":     u.get("points", 0),
            "streak":     u.get("streak", 0),
            "lang":       get_lang(uid),
        })

    @api_app.route("/api/checkin/<int:uid>/<hid>", methods=["POST"])
    @require_auth
    def api_checkin(uid, hid):
        u = load_user(uid)
        today = today_uz5()
        habits = u.get("habits", [])
        points_before = u.get("points", 0)
        found_h = None
        for h in habits:
            if h["id"] == hid:
                found_h = h
                hab_type  = h.get("type", "simple")
                rep_count = h.get("repeat_count", 1)
                if hab_type == "repeat" and rep_count > 1:
                    done = h.get("done_today_count", 0)
                    if h.get("done_date") != today:
                        done = 0
                    if done >= rep_count:
                        # Allaqachon to'liq bajarilgan — bekor qilish (0 ga tushirish)
                        done = 0
                        h["last_done"] = None
                        h["streak"] = max(0, h.get("streak", 0) - 1)
                        _undo_base = 5
                        if u.get("bonus_3x_active") and u.get("bonus_3x_date") == today:
                            _undo_base = 15
                        elif u.get("bonus_2x_active") and u.get("bonus_2x_date") == today:
                            _undo_base = 10
                        if u.get("xp_booster_days", 0) > 0:
                            _undo_base = round(_undo_base * 1.1)
                        u["points"] = max(0, u.get("points", 0) - _undo_base)
                        # Global streak: faqat bugun boshqa birorta odat bajarilmagan bo'lsa kamaytir
                        _still_done = any(hh.get("last_done") == today for hh in habits if hh["id"] != hid)
                        if not _still_done and u.get("streak_last_date") == today:
                            u["streak"] = max(0, u.get("streak", 0) - 1)
                            u["streak_last_date"] = ""
                    else:
                        done += 1
                        if done >= rep_count:
                            h["last_done"] = today
                            h["streak"] = h.get("streak", 0) + 1
                            # Global streak: kuniga bir marta oshsin
                            if u.get("streak_last_date") != today:
                                u["streak"] = u.get("streak", 0) + 1
                                u["streak_last_date"] = today
                                if u["streak"] > u.get("best_streak", 0):
                                    u["best_streak"] = u["streak"]
                                    u["best_streak_date"] = today
                            _base = 5
                            if u.get("bonus_3x_active") and u.get("bonus_3x_date") == today:
                                _base = 15
                            elif u.get("bonus_2x_active") and u.get("bonus_2x_date") == today:
                                _base = 10
                            if u.get("xp_booster_days", 0) > 0:
                                _base = round(_base * 1.1)
                            u["points"] = u.get("points", 0) + _base
                    h["done_today_count"] = done
                    h["done_date"] = today
                    is_done = done >= rep_count
                    today_count = done
                else:
                    if h.get("last_done") == today:
                        h["last_done"] = None
                        h["streak"] = max(0, h.get("streak", 0) - 1)
                        _undo_base = 5
                        if u.get("bonus_3x_active") and u.get("bonus_3x_date") == today:
                            _undo_base = 15
                        elif u.get("bonus_2x_active") and u.get("bonus_2x_date") == today:
                            _undo_base = 10
                        if u.get("xp_booster_days", 0) > 0:
                            _undo_base = round(_undo_base * 1.1)
                        u["points"] = max(0, u.get("points", 0) - _undo_base)
                        # Global streak: faqat bugun boshqa birorta odat bajarilmagan bo'lsa kamaytir
                        _still_done = any(hh.get("last_done") == today for hh in habits if hh["id"] != hid)
                        if not _still_done and u.get("streak_last_date") == today:
                            u["streak"] = max(0, u.get("streak", 0) - 1)
                            u["streak_last_date"] = ""
                        is_done = False
                    else:
                        from datetime import timezone, timedelta as _td
                        _tz = timezone(_td(hours=5))
                        _yesterday = (datetime.now(_tz) - _td(days=1)).strftime("%Y-%m-%d")
                        h["streak"] = h.get("streak", 0) + 1 if h.get("last_done") == _yesterday else 1
                        h["last_done"] = today
                        _base = 5
                        if u.get("bonus_3x_active") and u.get("bonus_3x_date") == today:
                            _base = 15
                        elif u.get("bonus_2x_active") and u.get("bonus_2x_date") == today:
                            _base = 10
                        if u.get("xp_booster_days", 0) > 0:
                            _base = round(_base * 1.1)
                        u["points"] = u.get("points", 0) + _base
                        # Global streak: kuniga bir marta oshsin
                        if u.get("streak_last_date") != today:
                            u["streak"] = u.get("streak", 0) + 1
                            u["streak_last_date"] = today
                            if u["streak"] > u.get("best_streak", 0):
                                u["best_streak"] = u["streak"]
                                u["best_streak_date"] = today
                        is_done = True
                    today_count = 1 if is_done else 0
                break
        u["habits"] = habits
        # History yangilash (statistika uchun)
        history = u.get("history", {})
        day_data = history.get(today, {})
        done_count_now = sum(1 for hh in habits if hh.get("last_done") == today)
        total_now = len(habits)
        # Har bir odat holatini ham saqlash
        hab_map = day_data.get("habits", {})
        if found_h:
            hab_map[hid] = found_h.get("last_done") == today
        day_data["done"]   = done_count_now
        day_data["total"]  = total_now
        day_data["habits"] = hab_map
        # Smart reminder uchun checkin vaqtini saqlash
        _ctimes = day_data.get("checkin_times", {})
        if found_h:
            if is_done:
                from datetime import datetime as _dt_sr, timedelta as _td_sr
                _ctimes[hid] = (_dt_sr.now() + _td_sr(hours=5)).strftime("%H:%M")
            else:
                _ctimes.pop(hid, None)
        day_data["checkin_times"] = _ctimes
        history[today] = day_data
        u["history"] = history
        # done_log yangilash (rating score uchun — 30 kunlik faollik)
        if is_done:
            done_log = u.get("done_log", {})
            done_log[today] = True
            u["done_log"] = done_log
        elif not is_done and found_h:
            # Undo: agar bugun hech bir odat bajarilmagan bo'lsa — done_log dan o'chirish
            still_any_done = any(hh.get("last_done") == today for hh in habits if hh["id"] != hid)
            if not still_any_done:
                done_log = u.get("done_log", {})
                done_log.pop(today, None)
                u["done_log"] = done_log
        # total_done yangilash (achievements uchun)
        if found_h:
            if is_done and found_h.get("last_done") == today:
                found_h["total_done"] = found_h.get("total_done", 0) + 1
            elif not is_done:
                found_h["total_done"] = max(0, found_h.get("total_done", 0) - 1)
        # XP booster kunini kamaytirish (kuniga bir marta)
        if u.get("xp_booster_days", 0) > 0:
            last_boost = u.get("xp_booster_last_day", "")
            if last_boost != today:
                u["xp_booster_days"] = max(0, u["xp_booster_days"] - 1)
                u["xp_booster_last_day"] = today
        save_user(uid, u)
        if not found_h:
            return jsonify({"ok": False, "error": "Odat topilmadi"})
        # done_count hisoblash
        done_count = sum(1 for hh in habits if hh.get("last_done") == today)
        total = len(habits)
        all_done = done_count == total and total > 0
        # Yutuqlarni tekshir
        new_ach = check_achievements(uid, u)
        new_badges = [{"id": a["id"], "icon": a["icon"], "title": a["title"]} for a in new_ach]
        # Streak milestone tekshiruvi (WebApp uchun — bot xabar yubormasdan, faqat response orqali)
        streak_milestone = None
        new_global_streak = u.get("streak", 0)
        if is_done and new_global_streak in STREAK_MILESTONES:
            ms = STREAK_MILESTONES[new_global_streak]
            sent_list = u.get("streak_milestones_sent", [])
            if new_global_streak not in sent_list:
                u["points"] = u.get("points", 0) + ms["bonus"]
                sent_list.append(new_global_streak)
                u["streak_milestones_sent"] = sent_list
                save_user(uid, u)
                streak_milestone = {
                    "streak": new_global_streak,
                    "emoji":  ms["emoji"],
                    "title":  ms["title"],
                    "bonus":  ms["bonus"],
                }
        return jsonify({
            "ok":              True,
            "done":            is_done,
            "streak":          found_h.get("streak", 0),
            "repeat_count":    found_h.get("repeat_count", 1),
            "today_count":     today_count,
            "points":          u.get("points", 0),
            "earned":          u.get("points", 0) - points_before,
            "all_done":        all_done,
            "done_count":      done_count,
            "total":           total,
            "new_badges":      new_badges,
            "streak_milestone": streak_milestone,
        })

    def _calc_trend(history, habits, now_uz, total):
        """Joriy hafta vs oldingi hafta bajarilish foizini solishtiradi."""
        from datetime import timedelta
        def week_pct(offset_start, offset_end):
            scores = []
            for i in range(offset_start, offset_end, -1):
                d = (now_uz - timedelta(days=i)).strftime("%Y-%m-%d")
                day_data = history.get(d, {})
                done  = day_data.get("done", 0)
                tot   = day_data.get("total", 0) or total
                if tot > 0:
                    scores.append(done / tot * 100)
                else:
                    scores.append(0)
            return round(sum(scores) / len(scores)) if scores else 0

        this_week = week_pct(6,  -1)   # oxirgi 7 kun (0..6)
        prev_week = week_pct(13,  6)   # undan oldingi 7 kun (7..13)
        diff = this_week - prev_week
        if diff > 5:
            direction = "up"
        elif diff < -5:
            direction = "down"
        else:
            direction = "same"
        return {
            "this_week": this_week,
            "prev_week": prev_week,
            "diff":      diff,
            "direction": direction,
        }

    @api_app.route("/api/stats/<int:uid>")
    @require_auth
    def api_stats(uid):
        from datetime import datetime, timedelta
        u = load_user(uid)
        habits = u.get("habits", [])
        today = today_uz5()
        now_uz = datetime.now() + timedelta(hours=5)
        done_today = sum(1 for h in habits if h.get("last_done") == today)
        total = len(habits)
        history = u.get("history", {})
        # 30 kunlik sanalar
        days_30 = []
        for i in range(29, -1, -1):
            d = (now_uz - timedelta(days=i)).strftime("%Y-%m-%d")
            days_30.append(d)
        # Heatmap
        # Bugungi holat uchun habits.last_done dan to'ldirish
        if not history.get(today, {}).get("done"):
            done_today_count = sum(1 for h in habits if h.get("last_done") == today)
            if done_today_count > 0:
                td = history.get(today, {})
                if not td.get("habits"):
                    td["habits"] = {h["id"]: (h.get("last_done") == today) for h in habits}
                td["done"]  = done_today_count
                td["total"] = total
                history[today] = td
        heatmap = {}
        for d in days_30:
            day_data = history.get(d, {})
            heatmap[d] = day_data.get("done", 0) > 0
        # Haftalik (oxirgi 7 kun)
        weekly = []
        for i in range(6, -1, -1):
            d = (now_uz - timedelta(days=i)).strftime("%Y-%m-%d")
            day_data = history.get(d, {})
            w_count = day_data.get("done", 0)
            w_total = day_data.get("total", 0)
            if w_count == 0 and w_total == 0:
                w_count = sum(1 for h in habits if h.get("last_done") == d)
                w_total = total
            weekly.append({
                "date":  d,
                "count": w_count,
                "total": w_total or total,
            })
        # Oylik (oxirgi 30 kun)
        monthly = []
        for i in range(29, -1, -1):
            d = (now_uz - timedelta(days=i)).strftime("%Y-%m-%d")
            day_data = history.get(d, {})
            hist_count = day_data.get("done", 0)
            hist_total = day_data.get("total", 0)
            # history bo'sh bo'lsa — habits dagi last_done dan hisoblash
            if hist_count == 0 and hist_total == 0:
                hist_count = sum(1 for h in habits if h.get("last_done") == d)
                hist_total = total
            monthly.append({
                "date":  d,
                "count": hist_count,
                "total": hist_total or total,
            })
        # Faol kunlar (30)
        active_days_30 = sum(1 for d in days_30 if heatmap.get(d))
        # Har bir odat statistikasi
        habit_stats = []
        for h in habits:
            # history dan hisoblash (yangi ma'lumotlar)
            done_7_hist  = sum(1 for i in range(7)  if history.get((now_uz-timedelta(days=i)).strftime("%Y-%m-%d"),{}).get("habits",{}).get(h["id"]))
            done_30_hist = sum(1 for i in range(30) if history.get((now_uz-timedelta(days=i)).strftime("%Y-%m-%d"),{}).get("habits",{}).get(h["id"]))
            week_dots = [bool(history.get((now_uz-timedelta(days=6-i)).strftime("%Y-%m-%d"),{}).get("habits",{}).get(h["id"])) for i in range(7)]
            # Agar history bo'sh bo'lsa (eski foydalanuvchilar) — streak va total_done dan foydalanish
            total_done_saved = h.get("total_done", 0)
            streak_val = h.get("streak", 0)
            # done_7: history mavjud bo'lsa undan, yo'qsa streak dan taxminan
            done_7  = done_7_hist  if done_7_hist  > 0 else min(streak_val, 7)
            done_30 = done_30_hist if done_30_hist > 0 else min(total_done_saved, 30)
            # done_all: total_done field eng ishonchli
            done_all = total_done_saved if total_done_saved > 0 else done_30_hist
            # week_dots: history bo'sh bo'lsa last_done asosida bugungi katakni to'ldirish
            if not any(week_dots) and h.get("last_done") == today:
                week_dots[-1] = True
            # percent: done_30 asosida
            percent = round(done_30 / 30 * 100)
            # 66 kun kalkulyatori
            from datetime import datetime as _dt66
            _created = h.get("created_at", "")
            _days_since = 0
            if _created:
                try:
                    _days_since = (now_uz.date() - _dt66.fromisoformat(_created).date()).days + 1
                except Exception:
                    _days_since = 0
            _days_66 = min(66, max(_days_since, done_all, streak_val))
            _days_66_done = min(done_all, 66)
            habit_stats.append({
                "id":         h["id"],
                "name":       h["name"],
                "icon":       h.get("icon", "✅"),
                "streak":     streak_val,
                "percent":    percent,
                "done_7":     done_7,
                "done_30":    done_30,
                "total_done": done_all,
                "week_dots":  week_dots,
                "days_66":      _days_66,
                "days_66_done": _days_66_done,
            })
        return jsonify({
            "today":   today,
            "summary": {
                "streak":        u.get("streak", 0),
                "points":        u.get("points", 0),
                "active_days_30": active_days_30,
                "total_habits":  total,
                "best_streak":   _calc_best_streak(u),
            },
            "weekly":      weekly,
            "monthly":     monthly,
            "heatmap":     heatmap,
            "days_30":     days_30,
            "habit_stats": habit_stats,
            "points":      u.get("points", 0),
            "streak":      u.get("streak", 0),
            "trend":       _calc_trend(history, habits, now_uz, total),
        })


    # ── Yutuqlar (Achievements) ──
    ACHIEVEMENTS = [
        # Streak
        {"id":"streak_3",    "cat":"streak",  "icon":"🔥", "title":"Ilk olov",       "desc":"3 kun ketma-ket bajaring",     "req":3,    "field":"streak"},
        {"id":"streak_7",    "cat":"streak",  "icon":"🌟", "title":"Haftalik qahramon","desc":"7 kun ketma-ket bajaring",    "req":7,    "field":"streak"},
        {"id":"streak_30",   "cat":"streak",  "icon":"💎", "title":"Oylik ustoz",     "desc":"30 kun ketma-ket bajaring",   "req":30,   "field":"streak"},
        {"id":"streak_100",  "cat":"streak",  "icon":"👑", "title":"100 kun shohi",   "desc":"100 kun ketma-ket bajaring",  "req":100,  "field":"streak"},
        # Ball
        {"id":"pts_100",     "cat":"ball",    "icon":"⭐", "title":"Birinchi yulduz", "desc":"100 ball to'plang",           "req":100,  "field":"points"},
        {"id":"pts_500",     "cat":"ball",    "icon":"🌠", "title":"Yulduz yomg'iri","desc":"500 ball to'plang",           "req":500,  "field":"points"},
        {"id":"pts_1000",    "cat":"ball",    "icon":"🏆", "title":"Ming ball",       "desc":"1000 ball to'plang",          "req":1000, "field":"points"},
        {"id":"pts_5000",    "cat":"ball",    "icon":"💰", "title":"Ball millioneri", "desc":"5000 ball to'plang",          "req":5000, "field":"points"},
        # Odat soni
        {"id":"hab_1",       "cat":"odat",    "icon":"🌱", "title":"Birinchi qadam",  "desc":"1 ta odat qo'shing",          "req":1,    "field":"habits_count"},
        {"id":"hab_5",       "cat":"odat",    "icon":"🌿", "title":"To'plam",         "desc":"5 ta odat qo'shing",          "req":5,    "field":"habits_count"},
        {"id":"hab_10",      "cat":"odat",    "icon":"🌳", "title":"Bog'bon",         "desc":"10 ta odat qo'shing",         "req":10,   "field":"habits_count"},
        # Jami bajarilgan
        {"id":"done_10",     "cat":"faollik", "icon":"✅", "title":"O'n marta",       "desc":"Jami 10 ta odat bajaring",    "req":10,   "field":"total_done"},
        {"id":"done_50",     "cat":"faollik", "icon":"🎯", "title":"Ellik marta",     "desc":"Jami 50 ta odat bajaring",    "req":50,   "field":"total_done"},
        {"id":"done_100",    "cat":"faollik", "icon":"🚀", "title":"Yuz marta",       "desc":"Jami 100 ta odat bajaring",   "req":100,  "field":"total_done"},
        {"id":"done_500",    "cat":"faollik", "icon":"⚡", "title":"Besh yuz",        "desc":"Jami 500 ta odat bajaring",   "req":500,  "field":"total_done"},
        # Do'stlar
        {"id":"friend_1",    "cat":"ijtimoiy","icon":"🤝", "title":"Birinchi do'st",  "desc":"1 ta do'st qo'shing",         "req":1,    "field":"friends_count"},
        {"id":"friend_5",    "cat":"ijtimoiy","icon":"👥", "title":"Jamoatchi",       "desc":"5 ta do'st qo'shing",         "req":5,    "field":"friends_count"},
    ]

    CAT_LABELS = {
        "streak":  {"uz":"Streak","ru":"Streak","en":"Streak"},
        "ball":    {"uz":"Ball","ru":"Очки","en":"Points"},
        "odat":    {"uz":"Odat","ru":"Привычки","en":"Habits"},
        "faollik": {"uz":"Faollik","ru":"Активность","en":"Activity"},
        "ijtimoiy":{"uz":"Ijtimoiy","ru":"Социальные","en":"Social"},
    }

    def check_achievements(uid, u):
        """Yangi qozonilgan yutuqlarni tekshiradi, qaytaradi: list of new achievement dicts"""
        earned_ids = {a["id"] for a in u.get("achievements", []) if isinstance(a, dict)}
        streak      = u.get("streak", 0)
        points      = u.get("points", 0)
        habits      = u.get("habits", [])
        total_done  = sum(h.get("total_done", 0) for h in habits)
        friends_cnt = len(u.get("friends", []))
        habits_cnt  = len(habits)

        field_vals = {
            "streak":       streak,
            "points":       points,
            "habits_count": habits_cnt,
            "total_done":   total_done,
            "friends_count":friends_cnt,
        }

        new_ach = []
        ach_list = list(u.get("achievements", []))
        changed = False
        for ach in ACHIEVEMENTS:
            if ach["id"] in earned_ids:
                continue
            val = field_vals.get(ach["field"], 0)
            if val >= ach["req"]:
                ach_list.append({"id": ach["id"], "earned_at": today_uz5()})
                new_ach.append(ach)
                changed = True
        if changed:
            u["achievements"] = ach_list
            save_user(uid, u)
        return new_ach

    @api_app.route("/api/achievements/<int:uid>")
    @require_auth
    def api_achievements(uid):
        u    = load_user(uid)
        lang = u.get("lang", "uz")
        earned_ids = {a["id"] for a in u.get("achievements", []) if isinstance(a, dict)}
        streak      = u.get("streak", 0)
        points      = u.get("points", 0)
        habits      = u.get("habits", [])
        total_done  = sum(h.get("total_done", 0) for h in habits)
        friends_cnt = len(u.get("friends", []))
        habits_cnt  = len(habits)
        field_vals  = {
            "streak":       streak,
            "points":       points,
            "habits_count": habits_cnt,
            "total_done":   total_done,
            "friends_count":friends_cnt,
        }
        result = []
        cats_seen = {}
        for ach in ACHIEVEMENTS:
            earned = ach["id"] in earned_ids
            current = min(field_vals.get(ach["field"], 0), ach["req"])
            cat_id  = ach["cat"]
            if cat_id not in cats_seen:
                label = CAT_LABELS.get(cat_id, {}).get(lang, cat_id)
                cats_seen[cat_id] = {"id": cat_id, "label": label}
            result.append({
                "id":      ach["id"],
                "cat":     cat_id,
                "icon":    ach["icon"],
                "title":   ach["title"],
                "desc":    ach["desc"],
                "req":     ach["req"],
                "current": current,
                "earned":  1 if earned else 0,
            })
        earned_count = sum(1 for a in result if a["earned"])
        return jsonify({
            "achievements": result,
            "cats":         list(cats_seen.values()),
            "earned_count": earned_count,
            "total_count":  len(result),
        })

    @api_app.route("/api/shop/<int:uid>")
    @require_auth
    def api_shop(uid):
        u = load_user(uid)
        lang = get_lang(uid)
        _shop_i18n = {
            "shield_1":   {"uz":("Streak himoyasi","1 kunlik streak himoyasi"), "ru":("Защита стрика","1 день защиты стрика"), "en":("Streak shield","1 day streak protection")},
            "shield_3":   {"uz":("3x Streak freeze","3 kunlik streak himoyasi"), "ru":("3x Заморозка стрика","3 дня защиты стрика"), "en":("3x Streak freeze","3 days streak protection")},
            "bonus_2x":   {"uz":("2x Ball bonus","1 kun uchun 2x ball"), "ru":("2x Бонус очков","2x очков на 1 день"), "en":("2x Points bonus","2x points for 1 day")},
            "bonus_3x":   {"uz":("3x Ball bonus","1 kun uchun 3x ball"), "ru":("3x Бонус очков","3x очков на 1 день"), "en":("3x Points bonus","3x points for 1 day")},
            "xp_booster": {"uz":("XP Booster","7 kun davomida +10% qo'shimcha ball"), "ru":("XP Бустер","7 дней +10% дополнительных очков"), "en":("XP Booster","7 days +10% extra points")},
            "badge_fire": {"uz":("Olov badge","Profilda ko'rsatiladi"), "ru":("Значок Огонь","Показывается в профиле"), "en":("Fire badge","Shows on profile")},
            "badge_star": {"uz":("Yulduz badge","Profilda ko'rsatiladi"), "ru":("Значок Звезда","Показывается в профиле"), "en":("Star badge","Shows on profile")},
            "badge_secret":{"uz":("Maxfiy badge","Noyob toj — faqat bozordan"), "ru":("Секретный значок","Редкая корона — только из магазина"), "en":("Secret badge","Rare crown — shop exclusive")},
            "pet_cat":    {"uz":("Mushuk","Sevimli mushukcha"), "ru":("Кошка","Милый котёнок"), "en":("Cat","Cute kitty")},
            "pet_dog":    {"uz":("It","Sodiq do'st"), "ru":("Собака","Верный друг"), "en":("Dog","Loyal friend")},
            "pet_rabbit": {"uz":("Quyon","Tez-tez sakrashi"), "ru":("Кролик","Часто прыгает"), "en":("Rabbit","Hops around")},
            "car_sport":  {"uz":("Sport mashina","Tez mashina"), "ru":("Спорткар","Быстрая машина"), "en":("Sports car","Fast car")},
            "jon_restore":{"uz":("Jon tiklash","Jonni 100% ga tiklash (faqat 20% va kam holda)"), "ru":("Восстановить жизнь","Восстановить до 100% (только при 20% и ниже)"), "en":("Restore life","Restore to 100% (only at 20% or below)")},
            "gift_box":   {"uz":("Sovga qutisi","Tasodifiy mukofot"), "ru":("Подарочная коробка","Случайная награда"), "en":("Gift box","Random reward")},
        }
        shop_items = [
            {"id": "shield_1",    "cat": "protection", "emoji": "\U0001f6e1",  "price_ball": 100,  "price_stars": 0},
            {"id": "shield_3",    "cat": "protection", "emoji": "\U0001f9ca",  "price_ball": 250,  "price_stars": 0},
            {"id": "bonus_2x",    "cat": "bonus",      "emoji": "\u26a1",  "price_ball": 150,  "price_stars": 0},
            {"id": "bonus_3x",    "cat": "bonus",      "emoji": "\U0001f680",  "price_ball": 300,  "price_stars": 0},
            {"id": "xp_booster",  "cat": "bonus",      "emoji": "\U0001f48e",  "price_ball": 400,  "price_stars": 0},
            {"id": "badge_fire",  "cat": "badge",      "emoji": "\U0001f525",  "price_ball": 200,  "price_stars": 0},
            {"id": "badge_star",  "cat": "badge",      "emoji": "\u2b50",  "price_ball": 250,  "price_stars": 0},
            {"id": "badge_secret","cat": "badge",      "emoji": "\U0001f451",  "price_ball": 600,  "price_stars": 0},
            {"id": "pet_cat",     "cat": "pet",        "emoji": "\U0001f431",  "price_ball": 300,  "price_stars": 0},
            {"id": "pet_dog",     "cat": "pet",        "emoji": "\U0001f436",  "price_ball": 350,  "price_stars": 0},
            {"id": "pet_rabbit",  "cat": "pet",        "emoji": "\U0001f430",  "price_ball": 300,  "price_stars": 0},
            {"id": "car_sport",   "cat": "car",        "emoji": "\U0001f3ce\ufe0f", "price_ball": 500,  "price_stars": 0},
            {"id": "jon_restore", "cat": "bonus",      "emoji": "\u2764\ufe0f", "price_ball": 25,   "price_stars": 0},
            {"id": "gift_box",    "cat": "gift",       "emoji": "\U0001f381",  "price_ball": 0,    "price_stars": 5},
        ]
        for item in shop_items:
            tr = _shop_i18n.get(item["id"], {}).get(lang, _shop_i18n.get(item["id"], {}).get("uz", ("",""))  )
            item["name"] = tr[0]
            item["desc"] = tr[1]
        raw_inventory = u.get("inventory", [])
        # inventory: list -> dict formatiga
        if isinstance(raw_inventory, list):
            inventory = {item_id: 1 for item_id in raw_inventory}
        else:
            inventory = raw_inventory
        active_pet   = u.get("active_pet", "")
        active_badge = u.get("active_badge", "")
        active_car   = u.get("active_car", "")
        # can_buy va owned fieldlarini har bir item ga qo'shish
        one_time = ["badge_fire","badge_star","badge_secret","pet_cat","pet_dog","pet_rabbit","car_sport"]
        # Counter fieldlardan owned miqdorini to'ldirish
        _counter_owned = {
            "shield_1":  min(u.get("streak_shields", 0), 1) if u.get("streak_shields", 0) > 0 else 0,
            "shield_3":  max(0, u.get("streak_shields", 0) - 1) if u.get("streak_shields", 0) > 1 else 0,
            "bonus_2x":  1 if (u.get("bonus_2x_active") and u.get("bonus_2x_date") == today_uz5()) else 0,
            "bonus_3x":  1 if (u.get("bonus_3x_active") and u.get("bonus_3x_date") == today_uz5()) else 0,
            "xp_booster": u.get("xp_booster_days", 0),
        }
        for item in shop_items:
            if item["id"] in _counter_owned:
                owned_qty = _counter_owned[item["id"]]
            else:
                owned_qty = inventory.get(item["id"], 0)
            item["owned"] = owned_qty
            # Bir martalik narsalar: allaqachon olingan bo'lsa can_buy=False
            if item["id"] in one_time:
                item["can_buy"] = owned_qty == 0
            else:
                item["can_buy"] = True
        return jsonify({
            "points":       u.get("points", 0),
            "items":        shop_items,
            "inventory":    inventory,
            "active_pet":   active_pet,
            "active_badge": active_badge,
            "active_car":   active_car,
        })

    @api_app.route("/api/shop/<int:uid>/buy", methods=["POST"])
    @require_auth
    def api_shop_buy(uid):
        data = request.get_json() or {}
        item_id   = data.get("item_id", "")
        pay_type  = data.get("type", "ball")  # "ball" yoki "stars"
        prices = {
            "shield_1": 100, "shield_3": 250,
            "bonus_2x": 150, "bonus_3x": 300, "xp_booster": 400,
            "badge_fire": 200, "badge_star": 250, "badge_secret": 600,
            "pet_cat": 300, "pet_dog": 350, "pet_rabbit": 300, "car_sport": 500,
            "jon_restore": 25,
        }
        price = prices.get(item_id, 0)
        if not price and item_id != "gift_box":
            return jsonify({"ok": False, "error": "Noma'lum mahsulot"})
        u = load_user(uid)
        raw_inv = u.get("inventory", [])
        if isinstance(raw_inv, list):
            inventory = {i: 1 for i in raw_inv}
        else:
            inventory = raw_inv
        # Faqat badge/pet/car bir marta sotib olinadi
        one_time = ["badge_fire","badge_star","badge_secret","pet_cat","pet_dog","pet_rabbit","car_sport"]
        if item_id in one_time and inventory.get(item_id, 0) > 0:
            return jsonify({"ok": False, "error": "Allaqachon sotib olingan"})
        if item_id == "jon_restore":
            jon_val = round(u.get("jon", 100.0))
            if jon_val > 20:
                return jsonify({"ok": False, "error": f"Jon faqat 20% va undan kam bo'lganda tiklanadi. Hozir: {jon_val}%"})
            if u.get("points", 0) < 25:
                return jsonify({"ok": False, "error": "Ball yetarli emas"})
            u["points"] = u.get("points", 0) - 25
            u["jon"] = 100.0
            save_user(uid, u)
            return jsonify({"ok": True, "points": u["points"]})
        if item_id == "shield_1":
            if u.get("points", 0) < 100:
                return jsonify({"ok": False, "error": "Ball yetarli emas"})
            u["points"] = u.get("points", 0) - 100
            u["streak_shields"] = u.get("streak_shields", 0) + 1
            save_user(uid, u)
            return jsonify({"ok": True, "points": u["points"], "streak_shields": u["streak_shields"]})
        if item_id == "shield_3":
            if u.get("points", 0) < 250:
                return jsonify({"ok": False, "error": "Ball yetarli emas"})
            u["points"] = u.get("points", 0) - 250
            u["streak_shields"] = u.get("streak_shields", 0) + 3
            save_user(uid, u)
            return jsonify({"ok": True, "points": u["points"], "streak_shields": u["streak_shields"]})
        if item_id == "bonus_2x":
            if u.get("points", 0) < 150:
                return jsonify({"ok": False, "error": "Ball yetarli emas"})
            if u.get("bonus_2x_active") and u.get("bonus_2x_date") == today_uz5():
                return jsonify({"ok": False, "error": "Bugun 2x bonus allaqachon aktiv"})
            u["points"] = u.get("points", 0) - 150
            u["bonus_2x_active"] = True
            u["bonus_2x_date"] = today_uz5()
            save_user(uid, u)
            return jsonify({"ok": True, "points": u["points"]})
        if item_id == "bonus_3x":
            if u.get("points", 0) < 300:
                return jsonify({"ok": False, "error": "Ball yetarli emas"})
            if u.get("bonus_3x_active") and u.get("bonus_3x_date") == today_uz5():
                return jsonify({"ok": False, "error": "Bugun 3x bonus allaqachon aktiv"})
            u["points"] = u.get("points", 0) - 300
            u["bonus_3x_active"] = True
            u["bonus_3x_date"] = today_uz5()
            save_user(uid, u)
            return jsonify({"ok": True, "points": u["points"]})
        if item_id == "xp_booster":
            if u.get("points", 0) < 400:
                return jsonify({"ok": False, "error": "Ball yetarli emas"})
            u["points"] = u.get("points", 0) - 400
            u["xp_booster_days"] = u.get("xp_booster_days", 0) + 7
            save_user(uid, u)
            return jsonify({"ok": True, "points": u["points"], "xp_booster_days": u["xp_booster_days"]})
        if pay_type == "ball":
            if u.get("points", 0) < price:
                return jsonify({"ok": False, "error": "Ball yetarli emas"})
            u["points"] = u.get("points", 0) - price
        inventory[item_id] = inventory.get(item_id, 0) + 1
        u["inventory"] = inventory
        save_user(uid, u)
        return jsonify({"ok": True, "points": u["points"]})

    @api_app.route("/api/shop/<int:uid>/stars_invoice", methods=["POST"])
    @require_auth
    def api_shop_stars_invoice(uid):
        data    = request.get_json(force=True, silent=True) or {}
        item_id = data.get("item_id", "")
        stars_prices = {"gift_box": 5}
        price = stars_prices.get(item_id)
        if not price:
            return jsonify({"ok": False, "error": "Stars bilan sotib bo'lmaydigan mahsulot"})
        item_names = {"gift_box": "Sovga qutisi"}
        item_descs = {"gift_box": "Tasodifiy mukofot: ball, streak himoya yoki XP booster"}
        try:
            from telebot.types import LabeledPrice as _LP
            bot.send_invoice(
                chat_id=uid,
                title=item_names.get(item_id, item_id),
                description=item_descs.get(item_id, ""),
                invoice_payload=f"stars_{item_id}",
                provider_token="",
                currency="XTR",
                prices=[_LP(item_names.get(item_id, item_id), price)],
            )
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)})

    @api_app.route("/api/shop/<int:uid>/activate", methods=["POST"])
    @require_auth
    def api_shop_activate(uid):
        data = request.get_json() or {}
        item_id  = data.get("item_id", "")
        deactive = data.get("deactivate", False)
        u = load_user(uid)
        if item_id.startswith("pet_"):
            u["active_pet"]   = "" if deactive else item_id
        elif item_id.startswith("badge_"):
            u["active_badge"] = "" if deactive else item_id
        elif item_id.startswith("car_"):
            u["active_car"]   = "" if deactive else item_id
        save_user(uid, u)
        return jsonify({"ok": True})

    @api_app.route("/api/shop/<int:uid>/sell", methods=["POST"])
    @require_auth
    def api_shop_sell(uid):
        """Inventardagi narsani 50% narxiga sotish."""
        data    = request.get_json() or {}
        item_id = data.get("item_id", "")
        # Sotish narxlari (asl narxning 50%)
        sell_prices = {
            "badge_fire":   100, "badge_star":  125, "badge_secret": 300,
            "pet_cat":      150, "pet_dog":     175, "pet_rabbit":   150,
            "car_sport":    250,
            "shield_1":      50, "shield_3":    125,
            "bonus_2x":      75, "bonus_3x":    150,
            "xp_booster":   200,
        }
        refund = sell_prices.get(item_id)
        if refund is None:
            return jsonify({"ok": False, "error": "Bu narsa sotilmaydi"})
        u = load_user(uid)
        today = today_uz5()
        # Counter fieldlar uchun alohida tekshirish
        if item_id in ("shield_1", "shield_3"):
            raw_inv_s = u.get("inventory", [])
            inv_s = {i: 1 for i in raw_inv_s} if isinstance(raw_inv_s, list) else dict(raw_inv_s)
            shields = u.get("streak_shields", 0)
            in_inv  = inv_s.get(item_id, 0) >= 1
            if shields < 1 and not in_inv:
                return jsonify({"ok": False, "error": "Inventarda topilmadi"})
            if shields >= 1:
                sell_qty = min(shields, 3) if item_id == "shield_3" else 1
                actual_refund = refund * sell_qty // 3 if item_id == "shield_3" else refund
                u["streak_shields"] = max(0, shields - sell_qty)
            else:
                actual_refund = refund
                inv_s[item_id] = inv_s.get(item_id, 0) - 1
                if inv_s[item_id] <= 0:
                    del inv_s[item_id]
                u["inventory"] = inv_s
            u["points"] = u.get("points", 0) + actual_refund
            save_user(uid, u)
            return jsonify({"ok": True, "points": u["points"], "refund": actual_refund})
        if item_id == "bonus_2x":
            if not (u.get("bonus_2x_active") and u.get("bonus_2x_date") == today):
                return jsonify({"ok": False, "error": "Aktiv bonus topilmadi"})
            u["bonus_2x_active"] = False
            u["points"] = u.get("points", 0) + refund
            save_user(uid, u)
            return jsonify({"ok": True, "points": u["points"], "refund": refund})
        if item_id == "bonus_3x":
            if not (u.get("bonus_3x_active") and u.get("bonus_3x_date") == today):
                return jsonify({"ok": False, "error": "Aktiv bonus topilmadi"})
            u["bonus_3x_active"] = False
            u["points"] = u.get("points", 0) + refund
            save_user(uid, u)
            return jsonify({"ok": True, "points": u["points"], "refund": refund})
        if item_id == "xp_booster":
            if u.get("xp_booster_days", 0) < 1:
                return jsonify({"ok": False, "error": "Inventarda topilmadi"})
            days_left = u["xp_booster_days"]
            actual_refund = round(refund * days_left / 7)
            u["xp_booster_days"] = 0
            u["points"] = u.get("points", 0) + actual_refund
            save_user(uid, u)
            return jsonify({"ok": True, "points": u["points"], "refund": actual_refund})
        # Inventory narsalar (badge/pet/car)
        raw_inv = u.get("inventory", [])
        if isinstance(raw_inv, list):
            inventory = {i: 1 for i in raw_inv}
        else:
            inventory = dict(raw_inv)
        if inventory.get(item_id, 0) < 1:
            return jsonify({"ok": False, "error": "Inventarda topilmadi"})
        inventory[item_id] = inventory.get(item_id, 0) - 1
        if inventory[item_id] <= 0:
            del inventory[item_id]
        u["inventory"] = inventory
        if item_id.startswith("pet_")   and u.get("active_pet")   == item_id:
            u["active_pet"]   = ""
        if item_id.startswith("badge_") and u.get("active_badge") == item_id:
            u["active_badge"] = ""
        if item_id.startswith("car_")   and u.get("active_car")   == item_id:
            u["active_car"]   = ""
        u["points"] = u.get("points", 0) + refund
        save_user(uid, u)
        return jsonify({"ok": True, "points": u["points"], "refund": refund})

    @api_app.route("/api/friends/<int:uid>")
    @require_auth
    def api_friends(uid):
        u = load_user(uid)
        friends_ids = u.get("friends", [])
        today = today_uz5()
        friends = []
        for fid in friends_ids[:20]:
            fu = load_user(fid)
            if fu:
                # done_today: bugun kamida bitta odat bajarilganmi
                fhabits = fu.get("habits", [])
                f_done_today = any(h.get("last_done") == today for h in fhabits)
                friends.append({
                    "id":           fid,
                    "name":         fu.get("name", "?"),
                    "points":       fu.get("points", 0),
                    "streak":       fu.get("streak", 0),
                    "photo":        fu.get("photo_url", ""),
                    "done_today":   f_done_today,
                    "mutual_streak": min(u.get("streak", 0), fu.get("streak", 0)),
                })
        # Invite link
        invite_link = f"https://t.me/{get_bot_username()}?start=ref_{uid}"
        return jsonify({"friends": friends, "invite_link": invite_link})

    @api_app.route("/api/friends/<int:uid>/search")
    @require_auth
    def api_friends_search(uid):
        q = (request.args.get("q") or "").strip().lower().lstrip("@")
        if len(q) < 2:
            return jsonify({"ok": False, "error": "Kamida 2 harf kiriting"}), 400
        u = load_user(uid)
        my_friends = set(str(f) for f in u.get("friends", []))
        results = []
        all_users = load_all_users()
        for fid_str, udata in all_users.items():
            if str(fid_str) == str(uid):
                continue
            uname = (udata.get("username") or "").lower()
            uname_display = (udata.get("name") or "").lower()
            if q in uname or q in uname_display:
                results.append({
                    "id":        int(fid_str),
                    "name":      udata.get("name", "?"),
                    "username":  udata.get("username", ""),
                    "points":    udata.get("points", 0),
                    "streak":    udata.get("streak", 0),
                    "photo":     udata.get("photo_url", ""),
                    "is_friend": fid_str in my_friends,
                })
            if len(results) >= 10:
                break
        return jsonify({"results": results})

    @api_app.route("/api/friends/<int:uid>/add/<int:fid>", methods=["POST"])
    @require_auth
    def api_friends_add(uid, fid):
        if uid == fid:
            return jsonify({"ok": False, "error": "O'zingizni qo'sha olmaysiz"}), 400
        u = load_user(uid)
        friends = u.get("friends", [])
        if fid not in friends:
            if len(friends) >= 50:
                return jsonify({"ok": False, "error": "Do'stlar limiti 50 ta"}), 400
            friends.append(fid)
            u["friends"] = friends
            save_user(uid, u)
        # Ikkinchi tomon: fid ning ro'yxatiga ham uid ni qo'shish
        f = load_user(fid)
        if f:
            f_friends = f.get("friends", [])
            if uid not in f_friends and len(f_friends) < 50:
                f_friends.append(uid)
                f["friends"] = f_friends
                save_user(fid, f)
        return jsonify({"ok": True})

    @api_app.route("/api/friends/<int:uid>/remove/<int:fid>", methods=["DELETE"])
    @require_auth
    def api_friends_remove(uid, fid):
        u = load_user(uid)
        friends = u.get("friends", [])
        if fid in friends:
            friends.remove(fid)
            u["friends"] = friends
            save_user(uid, u)
        # Ikkinchi tomon: fid ning ro'yxatidan ham uid ni o'chirish
        f = load_user(fid)
        if f:
            f_friends = f.get("friends", [])
            if uid in f_friends:
                f_friends.remove(uid)
                f["friends"] = f_friends
                save_user(fid, f)
        return jsonify({"ok": True})

    @api_app.route("/api/challenges/<int:uid>")
    @require_auth
    def api_challenges(uid):
        challenges_col = mongo_db.get_collection("challenges") if hasattr(mongo_db, "get_collection") else mongo_db["challenges"]
        sent = list(challenges_col.find({"from_uid": str(uid)}))
        recv = list(challenges_col.find({"to_uid":   str(uid), "status": "pending"}))
        def fmt(c):
            from_uid_str = c.get("from_uid", "")
            try:
                fu = load_user(int(from_uid_str)) if from_uid_str else {}
                from_name = fu.get("name", "?") if fu else "?"
            except Exception:
                from_name = "?"
            return {
                "id":          str(c.get("_id","")),
                "habit_name":  c.get("habit_name",""),
                "from_uid":    from_uid_str,
                "from_name":   from_name,
                "to_uid":      c.get("to_uid",""),
                "status":      c.get("status","pending"),
                "days":        c.get("days", 7),
                "bet":         c.get("bet", 50),
                "expires_at":  c.get("expires_at",""),
                "created_at":  c.get("created_at",""),
            }
        return jsonify({"sent": [fmt(c) for c in sent], "received": [fmt(c) for c in recv]})

    @api_app.route("/api/challenges/<int:uid>/send", methods=["POST"])
    @require_auth
    def api_challenges_send(uid):
        data        = request.get_json(force=True, silent=True) or {}
        receiver_id = data.get("receiver_id")
        habit_name  = (data.get("habit_name") or "").strip()
        try:
            days = int(data.get("days") or 7)
        except (ValueError, TypeError):
            days = 7
        try:
            bet = int(data.get("bet") or 50)
        except (ValueError, TypeError):
            bet = 50
        # Validatsiya
        if not habit_name:
            return jsonify({"ok": False, "error": "Odat nomi kerak"})
        if len(habit_name) > 100:
            return jsonify({"ok": False, "error": "Odat nomi 100 belgidan oshmasin"})
        if not receiver_id:
            return jsonify({"ok": False, "error": "Qabul qiluvchi ID kerak"})
        try:
            receiver_id = int(receiver_id)
        except (ValueError, TypeError):
            return jsonify({"ok": False, "error": "Noto'g'ri ID"})
        if receiver_id == uid:
            return jsonify({"ok": False, "error": "O'zingizga challenge yubora olmaysiz"})
        if days < 1 or days > 30:
            return jsonify({"ok": False, "error": "Muddat 1 dan 30 kungacha bo'lishi kerak"})
        if bet < 10 or bet > 1000:
            return jsonify({"ok": False, "error": "Garov 10 dan 1000 ballgacha bo'lishi kerak"})
        if not user_exists(receiver_id):
            return jsonify({"ok": False, "error": "Foydalanuvchi topilmadi"})
        sender = load_user(uid)
        if sender.get("points", 0) < bet:
            return jsonify({"ok": False, "error": f"Yetarli ball yo'q (kerak: {bet})"})
        challenges_col = mongo_db["challenges"]
        existing = challenges_col.find_one({
            "from_uid": str(uid),
            "to_uid":   str(receiver_id),
            "status":   "pending"
        })
        if existing:
            return jsonify({"ok": False, "error": "Allaqachon kutilayotgan challenge bor"})
        import datetime as _dt
        challenges_col.insert_one({
            "from_uid":   str(uid),
            "to_uid":     str(receiver_id),
            "habit_name": habit_name,
            "days":       days,
            "bet":        bet,
            "status":     "pending",
            "created_at": today_uz5(),
            "expires_at": (datetime.now(__import__('datetime').timezone(__import__('datetime').timedelta(hours=5))) + _dt.timedelta(days=days)).strftime("%Y-%m-%d"),
        })
        try:
            sender_name = sender.get("name", "Kimdir")
            bot.send_message(
                int(receiver_id),
                f"🎯 *Challenge keldi!*\n\n"
                f"👤 *{sender_name}* sizni challenge qildi!\n"
                f"📌 Odat: *{habit_name}*\n"
                f"📅 Muddat: *{days} kun*\n"
                f"💰 Garov: *{bet} ball*\n\n"
                f"_Qabul qilish uchun botga kiring._",
                parse_mode="Markdown"
            )
        except Exception:
            pass
        return jsonify({"ok": True})

    @api_app.route("/api/challenges/<int:uid>/<cid>/accept", methods=["POST"])
    @require_auth
    def api_challenges_accept(uid, cid):
        from bson import ObjectId
        challenges_col = mongo_db["challenges"]
        try:
            c = challenges_col.find_one({"_id": ObjectId(cid), "to_uid": str(uid), "status": "pending"})
        except Exception:
            return jsonify({"ok": False, "error": "Topilmadi"})
        if not c:
            return jsonify({"ok": False, "error": "Challenge topilmadi yoki allaqachon ko'rib chiqilgan"})
        bet        = c.get("bet", 50)
        from_uid   = int(c.get("from_uid", 0))
        # Ikkalasidan ham garov yechish
        u_recv = load_user(uid)
        u_send = load_user(from_uid)
        if not u_recv or not u_send:
            return jsonify({"ok": False, "error": "Foydalanuvchi topilmadi"})
        if u_recv.get("points", 0) < bet:
            return jsonify({"ok": False, "error": f"Sizda yetarli ball yo'q (kerak: {bet})"})
        if u_send.get("points", 0) < bet:
            return jsonify({"ok": False, "error": "Challenger'da yetarli ball yo'q"})
        u_recv["points"] = u_recv.get("points", 0) - bet
        u_send["points"] = u_send.get("points", 0) - bet
        save_user(uid, u_recv)
        save_user(from_uid, u_send)
        challenges_col.update_one(
            {"_id": ObjectId(cid)},
            {"$set": {
                "status":      "active",
                "accepted_at": today_uz5(),
                "expires_at":  (datetime.now(__import__("datetime").timezone(__import__("datetime").timedelta(hours=5))) + __import__("datetime").timedelta(days=c.get("days", 7))).strftime("%Y-%m-%d"),
            }}
        )
        # Yuboruvchiga xabar
        try:
            recv_name = u_recv.get("name", "Raqib")
            bot.send_message(
                from_uid,
                f"✅ *Challenge qabul qilindi!*\n\n"
                f"👤 *{recv_name}* sizning challengingizni qabul qildi!\n"
                f"📌 Odat: *{c.get('habit_name','')}*\n"
                f"📅 Muddat: *{c.get('days',7)} kun*\n"
                f"💰 Garov: *{bet} ball* (ikkalangizdan)\n\n"
                f"_Omad! 💪_",
                parse_mode="Markdown"
            )
        except Exception:
            pass
        return jsonify({"ok": True, "points": u_recv.get("points", 0)})

    @api_app.route("/api/challenges/<int:uid>/<cid>/reject", methods=["POST"])
    @require_auth
    def api_challenges_reject(uid, cid):
        from bson import ObjectId
        challenges_col = mongo_db["challenges"]
        try:
            c = challenges_col.find_one({"_id": ObjectId(cid), "to_uid": str(uid), "status": "pending"})
        except Exception:
            return jsonify({"ok": False, "error": "Topilmadi"})
        if not c:
            return jsonify({"ok": False, "error": "Challenge topilmadi"})
        challenges_col.update_one(
            {"_id": ObjectId(cid)},
            {"$set": {"status": "rejected", "rejected_at": today_uz5()}}
        )
        # Yuboruvchiga xabar
        try:
            from_uid  = int(c.get("from_uid", 0))
            u_recv    = load_user(uid)
            recv_name = u_recv.get("name", "Raqib") if u_recv else "Raqib"
            bot.send_message(
                from_uid,
                f"❌ *Challenge rad etildi*\n\n"
                f"👤 *{recv_name}* sizning challengingizni rad etdi.\n"
                f"📌 Odat: *{c.get('habit_name','')}*",
                parse_mode="Markdown"
            )
        except Exception:
            pass
        return jsonify({"ok": True})

    @api_app.route("/api/reminder/<int:uid>/<hid>", methods=["PUT"])
    @require_auth
    def api_reminder(uid, hid):
        data = request.get_json() or {}
        u = load_user(uid)
        habits = u.get("habits", [])
        for h in habits:
            if h["id"] == hid:
                h["time"] = data.get("time", h.get("time", ""))
                h["reminder"] = data.get("reminder", h.get("reminder", False))
                break
        u["habits"] = habits
        save_user(uid, u)
        # Yangi vaqt bilan qayta rejalashtirish
        updated_h = next((h for h in habits if h.get("id") == hid), None)
        if updated_h:
            try:
                schedule_habit(uid, updated_h)
            except Exception as _e:
                print(f"[warn] schedule_habit reminder: {_e}")
        return jsonify({"ok": True})

    @api_app.route("/api/profile/<int:uid>", methods=["PUT"])
    @require_auth
    def api_profile_put(uid):
        data = request.get_json() or {}
        u = load_user(uid)
        # lang
        if "lang" in data:
            if data["lang"] in ("uz", "ru", "en"):
                u["lang"] = data["lang"]
        # evening_notify
        if "evening_notify" in data:
            u["evening_notify"] = bool(data["evening_notify"])
        # dark_mode
        if "dark_mode" in data:
            u["dark_mode"] = bool(data["dark_mode"])
        # photo_url
        if "photo_url" in data:
            url = str(data["photo_url"] or "")[:500]
            u["photo_url"] = url
        # display_name
        if "display_name" in data:
            dn = str(data["display_name"] or "").strip()[:50]
            u["display_name"] = dn
        # phone
        if "phone" in data:
            phone = str(data["phone"] or "").strip()[:20]
            u["phone"] = phone
        save_user(uid, u)
        return jsonify({"ok": True})

    @api_app.route("/api/share-card/<int:uid>", methods=["POST"])
    @require_auth
    def api_share_card(uid):
        """Canvas rasmni qabul qilib, Telegram chatga yuboradi."""
        try:
            if 'photo' not in request.files:
                return jsonify({"ok": False, "error": "photo not found"}), 400
            photo = request.files['photo']
            import io
            photo_bytes = io.BytesIO(photo.read())
            photo_bytes.name = "weekly.png"
            caption_text = "\U0001f4ca " + T(uid, "weekly_share_caption")
            kb = InlineKeyboardMarkup()
            kb.row(
                InlineKeyboardButton(T(uid, "share_del_btn"), callback_data="share_del")
            )
            sent = bot.send_photo(uid, photo_bytes, caption=caption_text, reply_markup=kb)
            return jsonify({"ok": True})
        except Exception as e:
            print(f"[share-card] xato: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @api_app.route("/")
    def api_index():
        import os as _os
        html_path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "index.html")
        if _os.path.exists(html_path):
            from flask import send_file
            return send_file(html_path)
        return jsonify({"status": "ok", "bot": "Super Habits"})

    @api_app.route("/health")
    def api_health():
        return jsonify({"status": "ok", "bot": "Super Habits"})

    # ── Webhook endpoint (Telegram xabarlarini qabul qiladi) ──
    _WEBHOOK_PATH = "/webhook/" + BOT_TOKEN

    @api_app.route(_WEBHOOK_PATH, methods=["POST"])
    def telegram_webhook():
        import json as _wjson
        import threading as _thr
        from flask import request as _wreq
        if _wreq.headers.get("content-type") == "application/json":
            update = telebot.types.Update.de_json(_wjson.loads(_wreq.data))
            _thr.Thread(target=bot.process_new_updates, args=([update],), daemon=True).start()
        return "", 200

    @api_app.route("/setup_webhook")
    def setup_webhook():
        """Bir marta brauzerdan ochiladi — webhook o'rnatadi"""
        _base = os.environ.get("WEBAPP_URL", "").rstrip("/")
        if not _base:
            return jsonify({"ok": False, "error": "WEBAPP_URL sozlanmagan"}), 500
        _url = _base + _WEBHOOK_PATH
        try:
            bot.set_webhook(url=_url, allowed_updates=["message", "callback_query", "pre_checkout_query"])
            from telebot.types import BotCommand
            bot.set_my_commands([
                BotCommand("start",       "Botni ishga tushirish"),
                BotCommand("admin_panel", "Admin panel"),
            ])
            # Oldingi API orqali o'rnatilgan bio/tavsifni BARCHA tillar uchun tozalash
            try:
                for _lc in [None, "uz", "ru", "en"]:
                    try:
                        if _lc:
                            bot.set_my_short_description("", language_code=_lc)
                            bot.set_my_description("", language_code=_lc)
                        else:
                            bot.set_my_short_description("")
                            bot.set_my_description("")
                    except Exception:
                        pass
            except Exception:
                pass
            return jsonify({"ok": True, "webhook": _url})
        except Exception as _e:
            return jsonify({"ok": False, "error": str(_e)}), 502

    def run_api():
        port = int(os.environ.get("PORT", 8080))
        api_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

    print("[API] Flask server tayyor (port 8080)")

except ImportError:
    print("[API] Flask yo'q — Web App API ishlamaydi. 'pip install flask flask-cors' qiling.")
    run_api = None


