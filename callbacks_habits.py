#!/usr/bin/env python3
"""
Odat callback handlerlari: bekor qilish, o'chirish, streak shield.
Checkin (`toggle_`/`skip_`/`done_`) — `callbacks_checkin.py` ga delegatsiya
qilinadi (Qoida #24 — fayl hajmi).
"""

import time
import threading
import schedule
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import load_user, save_user
from city_logic import delete_building_for_habit
from helpers import T
from bot_setup import (bot, send_main_menu, main_menu_dict, cBtn, ok_kb,
                       edit_message_colored, build_main_text, main_menu)
from handlers_stats import delete_habit_menu
from callbacks_checkin import handle_checkin_callbacks


def handle_habits_callbacks(call, uid, cdata, u):
    """Odat callback larini qayta ishlaydi. True = handled."""

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

    if cdata.startswith("shield_use_") and cdata != "shield_use_all":

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

    if cdata.startswith("shield_skip_") and cdata != "shield_skip_all":
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

    # ── YANGI: Bitta shield barcha xavf ostidagi odatlarga ──
    # scheduler.py `daily_reset()` umumiy xabar yuboradi, bu handler uni qayta ishlaydi.
    # "Ha" bosilsa: 1 ta shield ishlatiladi, pending_shield dagi BARCHA odat streaki tiklanadi.
    if cdata == "shield_use_all":
        bot.answer_callback_query(call.id)
        pending = u.get("pending_shield", {}) or {}
        shields = u.get("streak_shields", 0)
        if pending and shields > 0:
            # Barcha pending odatlar streakini tiklash
            restored_count = 0
            pending_ids = set(pending.keys())
            for h in u.get("habits", []):
                if h["id"] in pending_ids:
                    h["streak"] = pending[h["id"]]
                    restored_count += 1
            # 1 ta shield ishlatildi, pending tozalandi
            u["streak_shields"] = shields - 1
            u["pending_shield"] = {}
            save_user(uid, u)
            try:
                title = T(uid, "shield_used_title")
                body  = T(uid, "shield_used_body").format(
                    count=restored_count,
                    remaining=u["streak_shields"],
                )
                bot.edit_message_text(
                    f"{title}\n\n{body}",
                    uid, call.message.message_id,
                    parse_mode="Markdown",
                    reply_markup=ok_kb(uid)
                )
            except Exception:
                pass
        else:
            # Pending bo'sh yoki shield yo'q — xabarni o'chirish
            try: bot.delete_message(uid, call.message.message_id)
            except: pass
        return True

    if cdata == "shield_skip_all":
        bot.answer_callback_query(call.id)
        # Pending tozalanadi — odatlar allaqachon scheduler.py da nollangan
        u["pending_shield"] = {}
        save_user(uid, u)
        try:
            bot.edit_message_text(
                T(uid, "shield_skipped"),
                uid, call.message.message_id,
                parse_mode="Markdown",
                reply_markup=ok_kb(uid)
            )
        except Exception:
            pass
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
        # CITY: habit bilan bog'liq binoni ham o'chirish (PHASE A3)
        try:
            delete_building_for_habit(u, habit_id)
        except Exception as _ce:
            print(f"[city] delete_building_for_habit xato (uid={uid}): {_ce}")
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

    # ── Checkin (toggle_/skip_/done_) — alohida modulga delegatsiya ──
    if handle_checkin_callbacks(call, uid, cdata, u):
        return True

    # ── Fallback: agar hech bir handler mos kelmasa ──
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass

    return False
