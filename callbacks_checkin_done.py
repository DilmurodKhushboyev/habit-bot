#!/usr/bin/env python3
"""
Bildirishnomadan kelgan `done_` checkin callback handleri.
`callbacks_checkin.py` dan ajratilgan (Qoida #24 — fayl hajmi).
"""

import time
import threading
from datetime import datetime, timedelta, timezone

from database import load_user, save_user, add_points_history
from points_logic import apply_item_bonuses, apply_pet_dog_bonus
from city_logic import update_building_progress
from helpers import T, today_uz5
from scheduler import unschedule_habit_today
from achievements import check_achievements_toplevel
from bot_setup import (bot, main_menu_dict, edit_message_colored,
                       build_main_text)
from callbacks_checkin import _check_streak_milestone


def handle_done_callbacks(call, uid, cdata, u):
    """`done_` (bildirishnomadan) callback larini qayta ishlaydi. True = handled."""

    if cdata.startswith("done_"):
        habit_id = cdata[5:]
        today    = today_uz5()
        from datetime import timezone, timedelta
        tz_uz     = timezone(timedelta(hours=5))
        yesterday = (datetime.now(tz_uz) - timedelta(days=1)).strftime("%Y-%m-%d")
        u        = load_user(uid)
        for h in u.get("habits", []):
            if h["id"] == habit_id:
                hab_type  = h.get("type", "simple")
                rep_count = h.get("repeat_count", 1)

                if hab_type == "repeat" and rep_count > 1:
                    # Repeat odat: progress +1
                    done_today_count = h.get("done_today_count", 0)
                    if h.get("done_date") != today:
                        done_today_count = 0
                    if h.get("last_done") == today:
                        bot.answer_callback_query(call.id, T(uid, "done_today"))
                        return True
                    done_today_count += 1
                    h["done_today_count"] = done_today_count
                    h["done_date"] = today
                    if done_today_count >= rep_count:
                        # To'liq bajarildi
                        h["streak"] = h.get("streak", 0) + 1 if h.get("last_done") == yesterday else 1
                        if h["streak"] > h.get("best_streak", 0):
                            h["best_streak"] = h["streak"]
                        h["last_done"] = today
                        h["total_done"] = h.get("total_done", 0) + 1
                        if u.get("streak_last_date") != today:
                            u["streak"] = u.get("streak", 0) + 1
                            u["streak_last_date"] = today
                            if u["streak"] > u.get("best_streak", 0):
                                u["best_streak"] = u["streak"]
                                u["best_streak_date"] = today
                            threading.Thread(target=_check_streak_milestone, args=(uid, u["streak"]), daemon=True).start()
                        _base = 5
                        if u.get("bonus_3x_active") and u.get("bonus_3x_date") == today:
                            _base = 15
                        elif u.get("bonus_2x_active") and u.get("bonus_2x_date") == today:
                            _base = 10
                        if u.get("xp_booster_days", 0) > 0:
                            _base = round(_base * 1.1)
                        _base = apply_item_bonuses(u, _base)
                        u["points"] = u.get("points", 0) + _base
                        add_points_history(u, _base, today)
                        # pet_dog kunlik birinchi checkin bonusi (faqat bir marta)
                        apply_pet_dog_bonus(u, today, is_undo=False)
                        done_log = u.get("done_log", {})
                        done_log[today] = True
                        u["done_log"] = done_log
                        # history yangilash (statistika/heatmap uchun)
                        history = u.get("history", {})
                        day_data = history.get(today, {})
                        done_count_now = sum(1 for hh in u.get("habits", []) if hh.get("last_done") == today)
                        hab_map = day_data.get("habits", {})
                        hab_map[habit_id] = True
                        day_data["done"]   = done_count_now
                        day_data["total"]  = len(u.get("habits", []))
                        day_data["habits"] = hab_map
                        history[today] = day_data
                        u["history"] = history
                        # XP booster kunini kamaytirish (kuniga bir marta)
                        if u.get("xp_booster_days", 0) > 0:
                            if u.get("xp_booster_last_day", "") != today:
                                u["xp_booster_days"] = max(0, u["xp_booster_days"] - 1)
                                u["xp_booster_last_day"] = today
                        # CITY: bino progress +1 (fully bajarildi) (PHASE A3)
                        try:
                            update_building_progress(u, habit_id, +1)
                        except Exception as _ce:
                            print(f"[city] update_building_progress +1 xato (uid={uid}): {_ce}")
                        save_user(uid, u)
                        try:
                            check_achievements_toplevel(uid, u)
                        except Exception: pass
                        unschedule_habit_today(uid, habit_id)
                        bot.answer_callback_query(call.id, "✅")
                        try:
                            bot.edit_message_text(
                                f"{T(uid, 'done_ok', name=h['name'])} *+{_base} ⭐ ball*\n\n🔥 Streak: {h['streak']} kun",
                                uid, call.message.message_id, parse_mode="Markdown"
                            )
                        except Exception: pass
                    else:
                        # Hali to'liq emas — progress ko'rsatish
                        save_user(uid, u)
                        bot.answer_callback_query(call.id, f"✅ {done_today_count}/{rep_count}")
                        try:
                            bot.edit_message_text(
                                f"✅ *{h['name']}* — *{done_today_count}/{rep_count}* bajarildi!",
                                uid, call.message.message_id, parse_mode="Markdown"
                            )
                        except Exception: pass
                    def del_remind_r(chat_id, message_id):
                        time.sleep(3)
                        try: bot.delete_message(chat_id, message_id)
                        except: pass
                    threading.Thread(target=del_remind_r, args=(uid, call.message.message_id), daemon=True).start()
                    main_msg_id = u.get("main_msg_id")
                    if main_msg_id:
                        try: edit_message_colored(uid, main_msg_id, build_main_text(uid), main_menu_dict(uid))
                        except Exception: pass
                    return True

                # Oddiy (simple) odat
                if h.get("last_done") == today:
                    bot.answer_callback_query(call.id, T(uid, "done_today"))
                    return True
                h["streak"] = h.get("streak", 0) + 1 if h.get("last_done") == yesterday else 1
                if h["streak"] > h.get("best_streak", 0):
                    h["best_streak"] = h["streak"]
                h["last_done"]  = today
                h["total_done"] = h.get("total_done", 0) + 1
                # Global streak: kuniga bir marta oshsin
                if u.get("streak_last_date") != today:
                    u["streak"] = u.get("streak", 0) + 1
                    u["streak_last_date"] = today
                    if u["streak"] > u.get("best_streak", 0):
                        u["best_streak"] = u["streak"]
                        u["best_streak_date"] = today
                    threading.Thread(target=_check_streak_milestone, args=(uid, u["streak"]), daemon=True).start()
                # Bonus multiplier hisoblash (WebApp api_checkin bilan bir xil)
                _base = 5
                if u.get("bonus_3x_active") and u.get("bonus_3x_date") == today:
                    _base = 15
                elif u.get("bonus_2x_active") and u.get("bonus_2x_date") == today:
                    _base = 10
                if u.get("xp_booster_days", 0) > 0:
                    _base = round(_base * 1.1)
                _base = apply_item_bonuses(u, _base)
                u["points"]     = u.get("points", 0) + _base
                add_points_history(u, _base, today)
                # pet_dog kunlik birinchi checkin bonusi (faqat bir marta)
                apply_pet_dog_bonus(u, today, is_undo=False)
                # done_log: kunlik bajarilgan kunlarni saqlash
                done_log = u.get("done_log", {})
                done_log[today] = True
                u["done_log"] = done_log
                # History yangilash (statistika/heatmap uchun)
                habits_list = u.get("habits", [])
                history = u.get("history", {})
                day_data = history.get(today, {})
                done_count_now = sum(1 for hh in habits_list if hh.get("last_done") == today)
                total_now = len(habits_list)
                hab_map = day_data.get("habits", {})
                hab_map[habit_id] = True
                day_data["done"]   = done_count_now
                day_data["total"]  = total_now
                day_data["habits"] = hab_map
                history[today] = day_data
                u["history"] = history
                # XP booster kunini kamaytirish (kuniga bir marta)
                if u.get("xp_booster_days", 0) > 0:
                    last_boost = u.get("xp_booster_last_day", "")
                    if last_boost != today:
                        u["xp_booster_days"] = max(0, u["xp_booster_days"] - 1)
                        u["xp_booster_last_day"] = today
                # CITY: bino progress +1 (simple done) (PHASE A3)
                try:
                    update_building_progress(u, habit_id, +1)
                except Exception as _ce:
                    print(f"[city] update_building_progress +1 xato (uid={uid}): {_ce}")
                save_user(uid, u)
                # Achievements tekshirish (top-level funksiya orqali)
                try:
                    check_achievements_toplevel(uid, u)
                except Exception as _ae:
                    print(f"[warn] check_achievements: {_ae}")
                unschedule_habit_today(uid, habit_id)
                streak = h["streak"]
                if streak >= 30:   msg_extra = f"🔥 Streak: {streak} kun 🏆"
                elif streak >= 14: msg_extra = f"🔥 Streak: {streak} kun 🌟"
                elif streak >= 7:  msg_extra = f"🔥 Streak: {streak} kun 🔥"
                else:              msg_extra = f"🔥 Streak: {streak} kun"
                bot.answer_callback_query(call.id, "✅")
                try:
                    bot.edit_message_text(
                        f"{T(uid, 'done_ok', name=h['name'])} *+{_base} ⭐ ball*\n\n{msg_extra}",
                        uid, call.message.message_id, parse_mode="Markdown"
                    )
                except Exception:
                    pass
                def del_remind(chat_id, message_id):
                    time.sleep(3)
                    try: bot.delete_message(chat_id, message_id)
                    except: pass
                threading.Thread(target=del_remind, args=(uid, call.message.message_id), daemon=True).start()
                main_msg_id = u.get("main_msg_id")
                if main_msg_id:
                    try:
                        edit_message_colored(uid, main_msg_id, build_main_text(uid), main_menu_dict(uid))
                    except Exception:
                        pass
                return True
        # Odat topilmadi
        bot.answer_callback_query(call.id)
        return True

    return False
