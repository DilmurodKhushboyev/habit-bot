#!/usr/bin/env python3
"""
Odat checkin callback handlerlari: `toggle_` (WebApp/menyu) va `skip_`.
`callbacks_habits.py` dan ajratilgan (Qoida #24 — fayl hajmi).
`done_` (bildirishnoma) — `callbacks_checkin_done.py` ga delegatsiya qilinadi.
"""

import time
import threading
from datetime import datetime, timedelta, timezone

from database import load_user, save_user, add_points_history
from points_logic import apply_item_bonuses, apply_pet_dog_bonus
from city_logic import update_building_progress
from helpers import T, today_uz5
from scheduler import schedule_habit, unschedule_habit_today, _send_auto_delete
from achievements import check_achievements_toplevel
from bot_setup import (bot, send_main_menu, main_menu_dict,
                       edit_message_colored, build_main_text)


# ─── STREAK MILESTONE ───────────────────────────────────────────
# Foydalanuvchi streak bosqichiga yetganda tabrik yuborish uchun.
# Bu funksiya `threading.Thread` orqali fon rejimida chaqiriladi
# (`toggle_` 2 joyda + `done_` 2 joyda — callbacks_checkin_done.py import qiladi).
STREAK_MILESTONES = (3, 7, 14, 30, 60, 100, 180, 365)


def _check_streak_milestone(uid: int, streak: int) -> None:
    """Streak milestone ga yetilganda foydalanuvchiga tabrik yuboradi."""
    try:
        if streak not in STREAK_MILESTONES:
            return
        text = T(uid, "streak_milestone").format(days=streak)
        _send_auto_delete(uid, text)
    except Exception as e:
        print(f"[streak_milestone] xato uid={uid} streak={streak}: {e}")


# done_ handleri — import shu yerda (STREAK_MILESTONES ta'rifidan keyin,
# circular import bo'lmasligi uchun: callbacks_checkin_done.py bu fayldan
# faqat _check_streak_milestone ni oladi).
from callbacks_checkin_done import handle_done_callbacks


def handle_checkin_callbacks(call, uid, cdata, u):
    """Checkin callback larini qayta ishlaydi: toggle_/skip_/done_. True = handled."""

    # --- toggle_ ---
    if cdata.startswith("toggle_"):
        habit_id = cdata[7:]
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
                    # Takrorlanuvchi odat: done_today_count bilan ishlash
                    done_today_count = h.get("done_today_count", 0)
                    if h.get("done_date") != today:
                        done_today_count = 0
                    fully_done       = done_today_count >= rep_count

                    if fully_done:
                        # Bekor qilish: to'liq bajarilganidan qaytarish
                        h["done_today_count"] = 0
                        h["last_done"]  = None
                        h["streak"]     = max(0, h.get("streak", 0) - 1)
                        h["total_done"] = max(0, h.get("total_done", 0) - 1)
                        # Bonus multiplier (api_checkin bilan bir xil)
                        _undo_base = 5
                        if u.get("bonus_3x_active") and u.get("bonus_3x_date") == today:
                            _undo_base = 15
                        elif u.get("bonus_2x_active") and u.get("bonus_2x_date") == today:
                            _undo_base = 10
                        if u.get("xp_booster_days", 0) > 0:
                            _undo_base = round(_undo_base * 1.1)
                        _undo_base = apply_item_bonuses(u, _undo_base)
                        _old_pts = u.get("points", 0)
                        u["points"] = max(0, _old_pts - _undo_base)
                        add_points_history(u, u["points"] - _old_pts, today)
                        # Global streak: faqat bugun boshqa odat bajarilmagan bo'lsa kamaytir
                        _still_done = any(hh.get("last_done") == today for hh in u.get("habits", []) if hh["id"] != habit_id)
                        # pet_dog kunlik bonusini qaytarish (boshqa odat qolmagan bo'lsa)
                        if not _still_done:
                            apply_pet_dog_bonus(u, today, is_undo=True)
                        if not _still_done and u.get("streak_last_date") == today:
                            u["streak"] = max(0, u.get("streak", 0) - 1)
                            u["streak_last_date"] = ""
                        # done_log: boshqa odat bajarilmagan bo'lsa o'chirish
                        if not _still_done:
                            done_log = u.get("done_log", {})
                            done_log.pop(today, None)
                            u["done_log"] = done_log
                        # History yangilash (undo)
                        history = u.get("history", {})
                        day_data = history.get(today, {})
                        done_count_now = sum(1 for hh in u.get("habits", []) if hh.get("last_done") == today)
                        hab_map = day_data.get("habits", {})
                        hab_map[habit_id] = False
                        day_data["done"] = done_count_now
                        day_data["total"] = len(u.get("habits", []))
                        day_data["habits"] = hab_map
                        history[today] = day_data
                        u["history"] = history
                        # CITY: bino progress regress (fully_done bekor qilindi) (PHASE A3)
                        try:
                            update_building_progress(u, habit_id, -1)
                        except Exception as _ce:
                            print(f"[city] update_building_progress -1 xato (uid={uid}): {_ce}")
                        save_user(uid, u)
                        schedule_habit(uid, h)
                        bot.answer_callback_query(call.id, f"↩️ 0/{rep_count}")
                    else:
                        # Bir bosish = progress +1, lekin ball YO'Q
                        done_today_count += 1
                        h["done_today_count"] = done_today_count
                        h["done_date"] = today
                        if done_today_count >= rep_count:
                            # To'liq bajarildi — faqat shu yerda ball beriladi
                            # BUG FIX: last_done yangilashdan OLDIN yesterday bilan solishtirish kerak
                            h["streak"]     = h.get("streak", 0) + 1 if h.get("last_done") == yesterday else 1
                            if h["streak"] > h.get("best_streak", 0):
                                h["best_streak"] = h["streak"]
                            h["last_done"]  = today
                            h["total_done"] = h.get("total_done", 0) + 1
                            # Bonus multiplier (api_checkin bilan bir xil)
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
                            # Global streak: kuniga bir marta oshsin
                            if u.get("streak_last_date") != today:
                                u["streak"] = u.get("streak", 0) + 1
                                u["streak_last_date"] = today
                                if u["streak"] > u.get("best_streak", 0):
                                    u["best_streak"] = u["streak"]
                                    u["best_streak_date"] = today
                                threading.Thread(target=_check_streak_milestone, args=(uid, u["streak"]), daemon=True).start()
                            # done_log: kunlik bajarilish tarixi
                            done_log = u.get("done_log", {})
                            done_log[today] = True
                            u["done_log"] = done_log
                            # history yangilash (statistika uchun)
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
                            unschedule_habit_today(uid, habit_id)
                            # CITY: bino progress +1 (fully_done — to'liq bajarildi) (PHASE A3)
                            try:
                                update_building_progress(u, habit_id, +1)
                            except Exception as _ce:
                                print(f"[city] update_building_progress +1 xato (uid={uid}): {_ce}")
                            save_user(uid, u)
                            # Achievements tekshirish
                            try:
                                check_achievements_toplevel(uid, u)
                            except Exception as _ae:
                                print(f"[warn] check_achievements toggle_repeat: {_ae}")
                            bot.answer_callback_query(call.id)
                            streak_r = h.get("streak", 1)
                            if streak_r >= 30:   s_extra_r = f"\n🔥 Streak: {streak_r} kun 🏆"
                            elif streak_r >= 14: s_extra_r = f"\n🔥 Streak: {streak_r} kun 🌟"
                            elif streak_r >= 7:  s_extra_r = f"\n🔥 Streak: {streak_r} kun 🔥"
                            else:                s_extra_r = f"\n🔥 Streak: {streak_r} kun"
                            sent_msg = bot.send_message(
                                uid,
                                T(uid, "done_ok", name=h["name"]) + f" *+{_base} ⭐ ball*" + s_extra_r,
                                parse_mode="Markdown"
                            )
                        else:
                            save_user(uid, u)
                            bot.answer_callback_query(call.id, f"✅ {done_today_count}/{rep_count}")
                            sent_msg = bot.send_message(
                                uid,
                                f"✅ *{h['name']}* — *{done_today_count}/{rep_count}* bajarildi!",
                                parse_mode="Markdown"
                            )
                        def del_msg_rep(chat_id, msg_id):
                            time.sleep(3)
                            try: bot.delete_message(chat_id, msg_id)
                            except: pass
                        threading.Thread(target=del_msg_rep, args=(uid, sent_msg.message_id), daemon=True).start()
                        # Barcha odat bajarildi?
                        all_done = all(
                            (hh.get("last_done") == today if hh.get("type","simple") != "repeat"
                             else hh.get("done_today_count",0) >= hh.get("repeat_count",1))
                            for hh in u.get("habits", [])
                        )
                        if all_done and done_today_count >= rep_count:
                            sent_c = bot.send_message(uid, T(uid, "all_done"))
                            def del_c_rep(chat_id, msg_id):
                                time.sleep(5)
                                try: bot.delete_message(chat_id, msg_id)
                                except: pass
                            threading.Thread(target=del_c_rep, args=(uid, sent_c.message_id), daemon=True).start()

                else:
                    # Oddiy odat
                    if h.get("last_done") == today:
                        # Bekor qilish
                        h["last_done"]  = None
                        h["streak"]     = max(0, h.get("streak", 0) - 1)
                        h["total_done"] = max(0, h.get("total_done", 0) - 1)
                        # Bonus multiplier (api_checkin bilan bir xil)
                        _undo_base = 5
                        if u.get("bonus_3x_active") and u.get("bonus_3x_date") == today:
                            _undo_base = 15
                        elif u.get("bonus_2x_active") and u.get("bonus_2x_date") == today:
                            _undo_base = 10
                        if u.get("xp_booster_days", 0) > 0:
                            _undo_base = round(_undo_base * 1.1)
                        _undo_base = apply_item_bonuses(u, _undo_base)
                        _old_pts = u.get("points", 0)
                        u["points"] = max(0, _old_pts - _undo_base)
                        add_points_history(u, u["points"] - _old_pts, today)
                        # Global streak: faqat bugun boshqa odat bajarilmagan bo'lsa kamaytir
                        _still_done = any(hh.get("last_done") == today for hh in u.get("habits", []) if hh["id"] != habit_id)
                        # pet_dog kunlik bonusini qaytarish (boshqa odat qolmagan bo'lsa)
                        if not _still_done:
                            apply_pet_dog_bonus(u, today, is_undo=True)
                        if not _still_done and u.get("streak_last_date") == today:
                            u["streak"] = max(0, u.get("streak", 0) - 1)
                            u["streak_last_date"] = ""
                        # done_log: boshqa odat bajarilmagan bo'lsa o'chirish
                        if not _still_done:
                            done_log = u.get("done_log", {})
                            done_log.pop(today, None)
                            u["done_log"] = done_log
                        # History yangilash (undo)
                        history = u.get("history", {})
                        day_data = history.get(today, {})
                        done_count_now = sum(1 for hh in u.get("habits", []) if hh.get("last_done") == today)
                        hab_map = day_data.get("habits", {})
                        hab_map[habit_id] = False
                        day_data["done"] = done_count_now
                        day_data["total"] = len(u.get("habits", []))
                        day_data["habits"] = hab_map
                        history[today] = day_data
                        u["history"] = history
                        # CITY: bino progress regress (simple undo) (PHASE A3)
                        try:
                            update_building_progress(u, habit_id, -1)
                        except Exception as _ce:
                            print(f"[city] update_building_progress -1 xato (uid={uid}): {_ce}")
                        save_user(uid, u)
                        schedule_habit(uid, h)
                        bot.answer_callback_query(call.id)
                        sent_msg = bot.send_message(uid, T(uid, "undone", name=h["name"]), parse_mode="Markdown")
                        def del_msg1(chat_id, msg_id):
                            time.sleep(3)
                            try: bot.delete_message(chat_id, msg_id)
                            except: pass
                        threading.Thread(target=del_msg1, args=(uid, sent_msg.message_id), daemon=True).start()
                    else:
                        # Bajarildi
                        # BUG FIX: last_done yangilashdan OLDIN yesterday bilan solishtirish kerak
                        h["streak"]     = h.get("streak", 0) + 1 if h.get("last_done") == yesterday else 1
                        h["last_done"]  = today
                        h["total_done"] = h.get("total_done", 0) + 1
                        # Bonus multiplier (api_checkin bilan bir xil)
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
                        # Global streak: kuniga bir marta oshsin
                        if u.get("streak_last_date") != today:
                            u["streak"] = u.get("streak", 0) + 1
                            u["streak_last_date"] = today
                            if u["streak"] > u.get("best_streak", 0):
                                u["best_streak"] = u["streak"]
                                u["best_streak_date"] = today
                            threading.Thread(target=_check_streak_milestone, args=(uid, u["streak"]), daemon=True).start()
                        # done_log: kunlik bajarilgan kun
                        done_log = u.get("done_log", {})
                        done_log[today] = True
                        u["done_log"] = done_log
                        # history yangilash (statistika uchun)
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
                        # CITY: bino progress +1 (simple done) (PHASE A3)
                        try:
                            update_building_progress(u, habit_id, +1)
                        except Exception as _ce:
                            print(f"[city] update_building_progress +1 xato (uid={uid}): {_ce}")
                        save_user(uid, u)
                        # Achievements tekshirish
                        try:
                            check_achievements_toplevel(uid, u)
                        except Exception as _ae:
                            print(f"[warn] check_achievements toggle: {_ae}")
                        unschedule_habit_today(uid, habit_id)
                        bot.answer_callback_query(call.id)
                        streak_s = h.get("streak", 1)
                        if streak_s >= 30:   s_extra_s = f"\n🔥 Streak: {streak_s} kun 🏆"
                        elif streak_s >= 14: s_extra_s = f"\n🔥 Streak: {streak_s} kun 🌟"
                        elif streak_s >= 7:  s_extra_s = f"\n🔥 Streak: {streak_s} kun 🔥"
                        else:                s_extra_s = f"\n🔥 Streak: {streak_s} kun"
                        sent_msg = bot.send_message(uid, T(uid, "done_ok", name=h["name"]) + f" *+{_base} ⭐ ball*" + s_extra_s, parse_mode="Markdown")
                        def del_msg2(chat_id, msg_id):
                            time.sleep(3)
                            try: bot.delete_message(chat_id, msg_id)
                            except: pass
                        threading.Thread(target=del_msg2, args=(uid, sent_msg.message_id), daemon=True).start()
                        # Barcha odat bajarildi?
                        all_done = all(
                            (hh.get("last_done") == today if hh.get("type","simple") != "repeat"
                             else hh.get("done_today_count",0) >= hh.get("repeat_count",1))
                            for hh in u.get("habits", [])
                        )
                        if all_done:
                            sent_c = bot.send_message(uid, T(uid, "all_done"))
                            def del_c(chat_id, msg_id):
                                time.sleep(5)
                                try: bot.delete_message(chat_id, msg_id)
                                except: pass
                            threading.Thread(target=del_c, args=(uid, sent_c.message_id), daemon=True).start()

                # Menyu yangilash
                main_msg_id = u.get("main_msg_id")
                if main_msg_id:
                    try:
                        edit_message_colored(uid, main_msg_id, build_main_text(uid), main_menu_dict(uid))
                    except Exception:
                        pass
                return True

        # toggle_ - habit topilmadi (o'chirilgan bo'lishi mumkin)
        bot.answer_callback_query(call.id)
        send_main_menu(uid)

    # --- skip_ (bildirishnomadan) ---
    if cdata.startswith("skip_"):
        habit_id = cdata[5:]
        bot.answer_callback_query(call.id)
        try:
            bot.delete_message(uid, call.message.message_id)
        except: pass
        return True

    # --- done_ (bildirishnomadan) — alohida modulga delegatsiya ---
    if handle_done_callbacks(call, uid, cdata, u):
        return True

    return False
