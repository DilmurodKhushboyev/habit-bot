#!/usr/bin/env python3
"""
Flask API data routes: today, checkin, stats
"""

import random
from datetime import datetime, date, timedelta, timezone
from flask import jsonify, request

from database import load_user, save_user, load_all_users, load_group, save_group
from helpers import T, get_lang, get_rank, today_uz5
from texts import LANGS
from motivation import MOTIVATSIYA
from bot_setup import bot
from flask_helpers import (require_auth, rate_limit_check, _tz_today,
                           _is_done_today, _calc_best_streak)


def register_data_routes(app):

    @app.route("/api/today/<int:uid>")
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

    @app.route("/api/checkin/<int:uid>/<hid>", methods=["POST"])
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

    @app.route("/api/stats/<int:uid>")
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

