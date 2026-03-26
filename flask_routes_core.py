#!/usr/bin/env python3
"""
Flask API core routes: rating, profile, habits, groups
"""

import uuid
from datetime import datetime, date, timedelta, timezone
from flask import jsonify, request

from config import mongo_db, mongo_col
from database import (load_user, save_user, load_all_users, load_group,
                      save_group, delete_group)
from helpers import get_lang, get_rank, today_uz5
from texts import LANGS
from bot_setup import bot, get_bot_username
from achievements import _ACHIEVEMENTS as ACHIEVEMENTS
from flask_helpers import (require_auth, rate_limit_check, _tz_today,
                           _is_done_today, _calc_best_streak)


def register_core_routes(app):

    @app.route("/api/rating")
    def api_rating():
        # Rate limit: 30 so'rov/daqiqa per IP (ochiq endpoint)
        rl_err = rate_limit_check(uid=None, limit=30, window=60)
        if rl_err:
            return rl_err
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

    @app.route("/api/profile/<int:uid>")
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

    @app.route("/api/habits/<int:uid>", methods=["GET"])
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

    @app.route("/api/habits/<int:uid>", methods=["POST"])
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
            from scheduler import schedule_habit
            schedule_habit(uid, new_habit)
        except Exception as _e: print(f"[warn] schedule_habit: {_e}")
        return jsonify({"ok": True, "habit": new_habit})

    @app.route("/api/habits/<int:uid>/<hid>", methods=["PUT"])
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
                from scheduler import schedule_habit
                schedule_habit(uid, edited_h)
            except Exception as _e:
                print(f"[warn] schedule_habit edit: {_e}")
        return jsonify({"ok": True})

    @app.route("/api/habits/<int:uid>/<hid>", methods=["DELETE"])
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
            from scheduler import unschedule_habit_today
            unschedule_habit_today(uid, hid)
        except Exception as _e:
            print(f"[warn] unschedule_habit_today delete: {_e}")
        return jsonify({"ok": True})

    @app.route("/api/groups/<int:uid>", methods=["GET", "POST"])
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
            _week_start = _now_wg - _td_wg(days=_now_wg.weekday())
            _week_days  = [(_week_start + _td_wg(days=i)).strftime("%Y-%m-%d") for i in range(7)]
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

    @app.route("/api/groups/<int:uid>/<gid>/checkin", methods=["POST"])
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
            done_today[uid_str] = {}
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

    @app.route("/api/groups/<int:uid>/<gid>/goal", methods=["PUT"])
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

    @app.route("/api/groups/<int:uid>/<gid>", methods=["DELETE"])
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

