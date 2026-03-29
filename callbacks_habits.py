#!/usr/bin/env python3
"""
Odat qo'shish/o'chirish/toggle/done callback handlerlari
"""

import time
import threading
import random
import uuid
import schedule
from datetime import date, datetime, timedelta, timezone
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import load_user, save_user, load_group, save_group
from helpers import T, get_lang, today_uz5
from texts import LANGS
from motivation import MOTIVATSIYA
from groups import _save_new_habit
from scheduler import schedule_habit, unschedule_habit_today
from achievements import check_achievements_toplevel
from bot_setup import (bot, send_main_menu, send_message_colored,
                       main_menu_dict, cBtn, ok_kb, kb_to_dict,
                       edit_message_colored, done_keyboard)


def handle_habits_callbacks(call, uid, cdata, u):
    """Odat callback larini qayta ishlaydi. True = handled."""

    if cdata == "menu_add":
        # ── VAQTINCHA O'CHIRILGAN: Odat limiti tekshiruvi ──
        # Bot mukammal darajaga yetgandan keyin qayta yoqiladi.
        # if len(u.get("habits", [])) >= 15:
        #     bot.answer_callback_query(call.id)
        #     sent_limit = bot.send_message(
        #         uid,
        #         T(uid, "limit"),
        #         parse_mode="Markdown"
        #     )
        #     def del_limit(chat_id, msg_id):
        #         time.sleep(3)
        #         try: bot.delete_message(chat_id, msg_id)
        #         except: pass
        #     threading.Thread(target=del_limit, args=(uid, sent_limit.message_id), daemon=True).start()
        #     send_main_menu(uid)
        #     return True
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        # Odat turini tanlash
        kb_type = InlineKeyboardMarkup()
        kb_type.row(
            InlineKeyboardButton(T(uid, "btn_type_simple"),  callback_data="habit_type_simple"),
            InlineKeyboardButton(T(uid, "btn_type_repeat"),  callback_data="habit_type_repeat")
        )
        kb_type.add(cBtn(T(uid, "btn_cancel"), "cancel", "danger"))
        sent = bot.send_message(
            uid,
            T(uid, "habit_type_choose"),
            parse_mode="Markdown", reply_markup=kb_type
        )
        u["temp_msg_id"] = sent.message_id
        save_user(uid, u)
        return True

    if cdata == "habit_type_simple":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        u["state"] = "waiting_habit_name"
        u["temp_habit"] = {"type": "simple"}
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.add(cBtn(T(uid, "btn_cancel"), "cancel", "danger"))
        sent = bot.send_message(uid, T(uid, "ask_habit_name"), parse_mode="Markdown", reply_markup=cancel_kb)
        u["temp_msg_id"] = sent.message_id
        save_user(uid, u)
        return True

    if cdata == "habit_type_repeat":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        # Avval necha marta takrorlanishi so'ralinsin
        u["temp_habit"] = {"type": "repeat"}
        u["state"] = "waiting_repeat_count"
        save_user(uid, u)
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.add(cBtn(T(uid, "btn_cancel"), "cancel", "danger"))
        sent = bot.send_message(
            uid,
            T(uid, "ask_repeat_count"),
            parse_mode="Markdown", reply_markup=cancel_kb
        )
        u["temp_msg_id"] = sent.message_id
        save_user(uid, u)
        return True




    if cdata == "cancel":
        u["state"] = None
        u.pop("temp_habit", None)
        old_msg_id = u.pop("temp_msg_id", None)
        save_user(uid, u)
        bot.answer_callback_query(call.id, T(uid, "btn_cancel"))
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        if old_msg_id:
            try: bot.delete_message(uid, old_msg_id)
            except: pass
        send_main_menu(uid)
        return True

    if cdata == "cancel_to_main":
        u["state"] = None
        u.pop("temp_habit", None)
        old_msg_id = u.pop("temp_msg_id", None)
        save_user(uid, u)
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        if old_msg_id:
            try: bot.delete_message(uid, old_msg_id)
            except: pass
        send_main_menu(uid)
        return True

    if cdata.startswith("shield_use_"):

        habit_id = cdata[len("shield_use_"):]
        bot.answer_callback_query(call.id)
        # pending_shield dan streak qiymatini olish
        pending = u.get("pending_shield", {})
        streak_val = pending.pop(habit_id, None)
        if streak_val is not None and u.get("streak_shields", 0) > 0:
            # Streakni tiklash
            for h in u.get("habits", []):
                if h["id"] == habit_id:
                    h["streak"] = streak_val
                    break
            u["streak_shields"]  = u.get("streak_shields", 0) - 1
            u["pending_shield"]  = pending
            save_user(uid, u)
            try:
                bot.edit_message_text(
                    f"🛡 *Streak himoyangiz ishlatildi!*\n\n"
                    f"*🔥 Streakingiz saqlanib qoldi:* {streak_val} kun\n"
                    f"*🛡 Qolgan himoyalar:* {u['streak_shields']} ta",
                    uid, call.message.message_id,
                    parse_mode="Markdown",
                    reply_markup=ok_kb(uid)
                )
            except Exception:
                pass
        else:
            try: bot.delete_message(uid, call.message.message_id)
            except: pass
        return True

    if cdata.startswith("shield_skip_"):
        habit_id = cdata[len("shield_skip_"):]
        bot.answer_callback_query(call.id)
        pending = u.get("pending_shield", {})
        pending.pop(habit_id, None)
        u["pending_shield"] = pending
        save_user(uid, u)
        try:
            bot.edit_message_text(
                "❌ *Streak nollandi.*\n\n"
                "🛡 Himoyangiz saqlanib qoldi — keyingi safar ishlatishingiz mumkin!",
                uid, call.message.message_id,
                parse_mode="Markdown",
                reply_markup=ok_kb(uid)
            )
        except Exception:
            pass
        return True

    if cdata == "habit_no_time":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        u["temp_habit"]["time"] = "vaqtsiz"
        u.pop("temp_msg_id", None)
        save_user(uid, u)
        _save_new_habit(uid, u)
        return True

    # ── Repeat odat: qo'shimcha vaqt qo'shish ──
    if cdata == "repeat_add_more":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        collected = u.get("temp_habit", {}).get("times_collected", [])
        u["state"] = "waiting_habit_time"
        save_user(uid, u)
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.add(cBtn(T(uid, "btn_cancel"), "cancel", "danger"))
        rep_count = u.get("temp_habit", {}).get("repeat_count", len(collected) + 1)
        sent = bot.send_message(
            uid,
            T(uid, "ask_repeat_next_time", current=len(collected)+1, total=rep_count),
            parse_mode="Markdown", reply_markup=cancel_kb
        )
        u["temp_msg_id"] = sent.message_id
        save_user(uid, u)
        return True

    # ── Repeat odat: yakunlash ──
    if cdata == "repeat_done":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        u.pop("temp_msg_id", None)
        save_user(uid, u)
        _save_new_habit(uid, u)
        return True

    if cdata.startswith("main_page_"):
        page = int(cdata[10:])
        bot.answer_callback_query(call.id)
        try:
            edit_message_colored(uid, call.message.message_id, build_main_text(uid), main_menu_dict(uid, page=page))
        except Exception:
            try:
                bot.edit_message_reply_markup(uid, call.message.message_id, reply_markup=main_menu(uid, page=page))
            except Exception:
                pass
        return True

    if cdata.startswith("delete_"):
        habit_id   = cdata[7:]
        u          = load_user(uid)
        habits     = u.get("habits", [])
        habit_name = next((h["name"] for h in habits if h["id"] == habit_id), "")
        bot.answer_callback_query(call.id)
        if not habit_name:
            send_main_menu(uid)
            return True
        kb_confirm = InlineKeyboardMarkup()
        kb_confirm.row(
            cBtn(T(uid, "btn_yes"), f"confirm_delete_{habit_id}", "success"),
            cBtn(T(uid, "btn_no"),  "cancel_delete", "danger")
        )
        try:
            bot.edit_message_text(
                T(uid, "confirm_delete", name=habit_name),
                uid, call.message.message_id,
                parse_mode="Markdown",
                reply_markup=kb_confirm
            )
        except Exception:
            bot.send_message(uid, T(uid, "confirm_delete", name=habit_name),
                             parse_mode="Markdown", reply_markup=kb_confirm)
        return True

    if cdata.startswith("confirm_delete_"):
        habit_id   = cdata[15:]
        u          = load_user(uid)
        habits     = u.get("habits", [])
        habit_name = next((h["name"] for h in habits if h["id"] == habit_id), "")
        # Schedule dan o'chirish
        schedule.clear(f"{uid}_{habit_id}")
        u["habits"] = [h for h in habits if h["id"] != habit_id]
        save_user(uid, u)
        bot.answer_callback_query(call.id)
        try:
            bot.delete_message(uid, call.message.message_id)
        except Exception:
            pass
        sent_del = bot.send_message(uid, T(uid, "deleted", name=habit_name), parse_mode="Markdown")
        def delete_and_back(chat_id, message_id):
            time.sleep(3)
            try:
                bot.delete_message(chat_id, message_id)
            except Exception:
                pass
            delete_habit_menu(chat_id)
        threading.Thread(target=delete_and_back, args=(uid, sent_del.message_id), daemon=True).start()
        return True

    if cdata == "cancel_delete":
        bot.answer_callback_query(call.id)
        try:
            bot.delete_message(uid, call.message.message_id)
        except Exception:
            pass
        delete_habit_menu(uid)
        return True

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
                        u["points"] = max(0, u.get("points", 0) - _undo_base)
                        # Global streak: faqat bugun boshqa odat bajarilmagan bo'lsa kamaytir
                        _still_done = any(hh.get("last_done") == today for hh in u.get("habits", []) if hh["id"] != habit_id)
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
                            u["points"] = u.get("points", 0) + _base
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
                        u["points"] = max(0, u.get("points", 0) - _undo_base)
                        # Global streak: faqat bugun boshqa odat bajarilmagan bo'lsa kamaytir
                        _still_done = any(hh.get("last_done") == today for hh in u.get("habits", []) if hh["id"] != habit_id)
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
                        u["points"] = u.get("points", 0) + _base
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

    # --- done_ (bildirishnomadan) ---
    if cdata.startswith("skip_"):
        habit_id = cdata[5:]
        bot.answer_callback_query(call.id)
        try:
            bot.delete_message(uid, call.message.message_id)
        except: pass
        return True

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
                        u["points"] = u.get("points", 0) + _base
                        done_log = u.get("done_log", {})
                        done_log[today] = True
                        u["done_log"] = done_log
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
                u["points"]     = u.get("points", 0) + _base
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

    # ── Fallback: agar hech bir handler mos kelmasa ──
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass



    return False
