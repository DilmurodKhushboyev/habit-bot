#!/usr/bin/env python3
"""
Sozlamalar callback handlerlari
"""

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import ADMIN_ID
from database import load_user, save_user
from helpers import T, get_lang, today_uz5
from texts import LANGS
from bot_setup import (bot, send_main_menu, send_message_colored,
                       main_menu_dict, cBtn, ok_kb, kb_to_dict,
                       edit_message_colored)


def handle_settings_callbacks(call, uid, cdata, u):
    """Sozlamalar callback larini qayta ishlaydi. True = handled."""

    if cdata == "menu_settings":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        kb_set = InlineKeyboardMarkup()
        kb_set.add(InlineKeyboardButton(T(uid, "btn_change_lang"),        callback_data="settings_lang"))
        kb_set.add(InlineKeyboardButton(T(uid, "btn_change_info"),        callback_data="settings_info"))
        kb_set.add(InlineKeyboardButton("⚙️ Odat sozlamalari",           callback_data="settings_habits_time"))
        kb_set.add(InlineKeyboardButton("💬 Dasturchiga habar",           callback_data="settings_contact_dev"))
        kb_set.add(cBtn(T(uid, "btn_home"), "menu_main", "primary"))
        sent = bot.send_message(uid, T(uid, "settings_title"), parse_mode="Markdown", reply_markup=kb_set)
        u["main_msg_id"] = sent.message_id
        save_user(uid, u)
        return True

    if cdata == "settings_lang":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        u["lang_from_settings"] = True
        save_user(uid, u)
        kb_lang = lang_keyboard()
        kb_lang.row(
            cBtn("⬅️ Orqaga", "menu_settings", "primary"),
            cBtn(T(uid, "btn_home"), "menu_main", "primary")
        )
        sent = bot.send_message(uid, "🌐 Tilni tanlang / Choose language / Выберите язык / Dil seçin:", reply_markup=kb_lang)
        u["main_msg_id"] = sent.message_id
        save_user(uid, u)
        return True

    if cdata == "settings_contact_dev":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        u["state"] = "waiting_dev_message"
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.add(cBtn(T(uid, "btn_cancel"), "menu_settings", "danger"))
        sent = bot.send_message(uid, T(uid, "set_dev_prompt"), parse_mode="Markdown", reply_markup=cancel_kb)
        u["dev_msg_id"] = sent.message_id
        save_user(uid, u)
        return True

    if cdata == "settings_info":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        kb_info = InlineKeyboardMarkup()
        kb_info.add(InlineKeyboardButton("✏️ Ismni o'zgartirish",           callback_data="change_name"))
        kb_info.add(InlineKeyboardButton("📱 Telefon raqamni o'zgartirish", callback_data="change_phone"))
        kb_info.row(
            cBtn("⬅️ Orqaga", "menu_settings", "primary"),
            cBtn(T(uid, "btn_home"),   "menu_main", "primary")
        )
        sent = bot.send_message(uid, T(uid, "change_info_text"), parse_mode="Markdown", reply_markup=kb_info)
        u["main_msg_id"] = sent.message_id
        save_user(uid, u)
        return True

    # --- Odatlar vaqtini tahrirlash menyusi ---
    if cdata == "settings_habits_time":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        habits = u.get("habits", [])
        if not habits:
            sent_e = bot.send_message(uid, T(uid, "no_habits"), parse_mode="Markdown")
            def del_no_h(chat_id, mid):
                time.sleep(3)
                try: bot.delete_message(chat_id, mid)
                except: pass
            threading.Thread(target=del_no_h, args=(uid, sent_e.message_id), daemon=True).start()
            kb_back = InlineKeyboardMarkup()
            kb_back.add(cBtn("⬅️ Orqaga", "settings_info", "primary"))
            bot.send_message(uid, T(uid, "change_info_text"), parse_mode="Markdown", reply_markup=kb_back)
            return True
        # Umumiy vaqt holati
        all_timed    = all(h.get("time") not in (None, "", "vaqtsiz") for h in habits)
        all_timeless = all(h.get("time") in (None, "", "vaqtsiz") for h in habits)
        kb_habits = InlineKeyboardMarkup()
        for h in habits:
            h_type   = h.get("type", "simple")
            has_time = h.get("time") not in (None, "", "vaqtsiz")
            if h_type == "repeat":
                times = h.get("repeat_times", [h.get("time", "?")])
                lbl = f"🔁 {h['name']} ({', '.join(times)})"
            else:
                icon = "⏰" if has_time else "🔕"
                lbl  = f"{icon} {h['name']} ({h.get('time','vaqtsiz')})"
            kb_habits.add(InlineKeyboardButton(lbl, callback_data=f"edit_htime_{h['id']}"))
        # Umumiy vaqt tugmasi
        if all_timeless:
            kb_habits.add(InlineKeyboardButton("⏰ Umumiy vaqt belgilash", callback_data="edit_htime_all_set"))
        else:
            kb_habits.add(InlineKeyboardButton("🔕 Umumiy vaqtni olib tashlash", callback_data="edit_htime_all_remove"))
        kb_habits.add(InlineKeyboardButton("✏️ Odat nomini o'zgartirish", callback_data="change_habit_name"))
        kb_habits.row(
            cBtn("⬅️ Orqaga", "settings_info", "primary"),
            cBtn(T(uid, "btn_home"),  "menu_main", "primary")
        )
        sent = bot.send_message(uid, T(uid, "set_habit_settings"), parse_mode="Markdown", reply_markup=kb_habits)
        u["main_msg_id"] = sent.message_id
        save_user(uid, u)
        return True

    # --- Umumiy vaqtni olib tashlash ---
    if cdata == "edit_htime_all_remove":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        for h in u.get("habits", []):
            h["time"] = "vaqtsiz"
            schedule.clear(f"{uid}_{h['id']}")
        save_user(uid, u)
        sent_ok = bot.send_message(uid, T(uid, "set_all_notime"))
        def del_ok_all(chat_id, mid):
            time.sleep(2)
            try: bot.delete_message(chat_id, mid)
            except: pass
        threading.Thread(target=del_ok_all, args=(uid, sent_ok.message_id), daemon=True).start()
        # Ro'yxatni qayta chiqarish
        habits    = u.get("habits", [])
        kb_habits = InlineKeyboardMarkup()
        for h in habits:
            kb_habits.add(InlineKeyboardButton(f"🔕 {h['name']} (vaqtsiz)", callback_data=f"edit_htime_{h['id']}"))
        kb_habits.add(InlineKeyboardButton("⏰ Umumiy vaqt belgilash", callback_data="edit_htime_all_set"))
        kb_habits.row(
            cBtn("⬅️ Orqaga", "settings_info", "primary"),
            cBtn(T(uid, "btn_home"),  "menu_main", "primary")
        )
        sent2 = bot.send_message(uid, T(uid, "set_which_time"), parse_mode="Markdown", reply_markup=kb_habits)
        u2 = load_user(uid)
        u2["main_msg_id"] = sent2.message_id
        save_user(uid, u2)
        return True

    # --- Umumiy vaqt belgilash (barcha odatlarga bir vaqt) ---
    if cdata == "edit_htime_all_set":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        u["state"]             = "editing_all_habits_time"
        u["editing_habit_id"]  = "ALL"
        save_user(uid, u)
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.add(cBtn(T(uid, "btn_cancel"), "settings_habits_time", "danger"))
        sent = bot.send_message(uid, T(uid, "set_all_time_ask"), parse_mode="Markdown", reply_markup=cancel_kb)
        u["temp_msg_id"] = sent.message_id
        save_user(uid, u)
        return True

    # --- Bitta odat vaqti tahrirlash ---
    if cdata.startswith("edit_htime_") and not cdata.startswith("edit_htime_notime_") and not cdata.startswith("edit_htime_start_"):
        habit_id = cdata[11:]
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        habits = u.get("habits", [])
        h = next((x for x in habits if x["id"] == habit_id), None)
        if not h:
            send_main_menu(uid)
            return True
        h_type    = h.get("type", "simple")
        has_time  = h.get("time") not in (None, "", "vaqtsiz")
        kb_e = InlineKeyboardMarkup()
        if h_type == "repeat":
            times = h.get("repeat_times", [h.get("time", "?")])
            info = f"🔁 *{h['name']}* — takror: {h.get('repeat_count',len(times))} marta\n"
            info += "Joriy vaqtlar: " + " | ".join(f"*{t}*" for t in times) + "\n\n"
            info += "Yangi vaqtlarni qayta kiriting:"
            kb_e.add(InlineKeyboardButton("✏️ Vaqtlarni qayta kiritish", callback_data=f"edit_htime_start_{habit_id}"))
        else:
            curr = h.get("time", "vaqtsiz")
            info = f"⏰ *{h['name']}*\nJoriy vaqt: *{curr}*\n\n"
            if has_time:
                info += "Vaqtni o'zgartirish yoki vaqtsiz holatga o'tkazish:"
                kb_e.add(InlineKeyboardButton("✏️ Vaqtni o'zgartirish",   callback_data=f"edit_htime_start_{habit_id}"))
                kb_e.add(InlineKeyboardButton("🔕 Vaqtsiz holatga o'tish", callback_data=f"edit_htime_notime_{habit_id}"))
            else:
                info += "Hozir vaqtsiz. Vaqt belgilash:"
                kb_e.add(InlineKeyboardButton("⏰ Vaqt belgilash",         callback_data=f"edit_htime_start_{habit_id}"))
        kb_e.row(
            cBtn("⬅️ Orqaga", "settings_habits_time", "primary"),
            cBtn(T(uid, "btn_home"), "menu_main", "primary")
        )
        sent = bot.send_message(uid, info, parse_mode="Markdown", reply_markup=kb_e)
        u["main_msg_id"] = sent.message_id
        save_user(uid, u)
        return True

    # --- Vaqtsiz holatga o'tkazish ---
    if cdata.startswith("edit_htime_notime_"):
        habit_id = cdata[18:]
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        for h in u.get("habits", []):
            if h["id"] == habit_id:
                h["time"] = "vaqtsiz"
                schedule.clear(f"{uid}_{habit_id}")
                break
        save_user(uid, u)
        sent_ok = bot.send_message(uid, T(uid, "set_habit_notime"), parse_mode="Markdown")
        def del_ok_notime(chat_id, mid):
            time.sleep(2)
            try: bot.delete_message(chat_id, mid)
            except: pass
        threading.Thread(target=del_ok_notime, args=(uid, sent_ok.message_id), daemon=True).start()
        # Odatlar ro'yxatiga qaytish
        kb_back = InlineKeyboardMarkup()
        kb_back.add(InlineKeyboardButton("⬅️ Odatlar ro'yxati", callback_data="settings_habits_time"))
        kb_back.add(cBtn(T(uid, "btn_home"),     "menu_main", "primary"))
        sent2 = bot.send_message(uid, T(uid, "set_edit_times"), parse_mode="Markdown", reply_markup=kb_back)
        u["main_msg_id"] = sent2.message_id
        save_user(uid, u)
        return True

    # --- Vaqtni tahrirlash boshlash ---
    if cdata.startswith("edit_htime_start_"):
        habit_id = cdata[17:]
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        h = next((x for x in u.get("habits", []) if x["id"] == habit_id), None)
        if not h:
            send_main_menu(uid)
            return True
        h_type    = h.get("type", "simple")
        rep_count = h.get("repeat_count", 1)
        u["state"] = "editing_habit_time"
        u["editing_habit_id"] = habit_id
        u["editing_habit_times_collected"] = []
        u["editing_habit_type"] = h_type
        u["editing_habit_rep_count"] = rep_count
        save_user(uid, u)
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.add(cBtn(T(uid, "btn_cancel"), "settings_habits_time", "danger"))
        if h_type == "repeat" and rep_count > 1:
            prompt = (
                f"⏰ *{h['name']}* uchun *1/{rep_count}* yangi vaqtni kiriting:\n\n"
                f"_Masalan: 06:00_"
            )
        else:
            prompt = f"⏰ *{h['name']}* uchun yangi vaqtni kiriting:\n\n_Masalan: 07:30_"
        sent = bot.send_message(uid, prompt, parse_mode="Markdown", reply_markup=cancel_kb)
        u["temp_msg_id"] = sent.message_id
        save_user(uid, u)
        return True

    if cdata == "change_habit_name":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        habits = u.get("habits", [])
        if not habits:
            sent_e = bot.send_message(uid, T(uid, "no_habits"), parse_mode="Markdown")
            def _del_no(chat_id, mid):
                import time as _t; _t.sleep(3)
                try: bot.delete_message(chat_id, mid)
                except: pass
            threading.Thread(target=_del_no, args=(uid, sent_e.message_id), daemon=True).start()
            send_main_menu(uid)
            return True
        # Vaqt bo'yicha tartiblash
        def _sk(h):
            t = h.get("time", "23:59")
            try:
                hh, mm = t.split(":")
                return int(hh)*60 + int(mm)
            except: return 9999
        sorted_h = sorted(habits, key=_sk)
        kb_hn = InlineKeyboardMarkup()
        for h in sorted_h:
            kb_hn.add(InlineKeyboardButton(f"✏️ {h['name']} ({h['time']})", callback_data=f"rename_habit_{h['id']}"))
        kb_hn.row(
            cBtn("⬅️ Orqaga", "settings_habits_time", "primary"),
            cBtn(T(uid, "btn_home"), "menu_main", "primary")
        )
        sent = bot.send_message(uid, T(uid, "set_which_rename"), parse_mode="Markdown", reply_markup=kb_hn)
        u["main_msg_id"] = sent.message_id
        save_user(uid, u)
        return True

    if cdata == "change_name":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        u["state"] = "updating_name"
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.add(cBtn("⬅️ Orqaga", "settings_info", "primary"))
        sent = bot.send_message(uid, T(uid, "set_new_name"), reply_markup=cancel_kb)
        u["info_msg_id"] = sent.message_id
        save_user(uid, u)
        return True

    if cdata.startswith("rename_habit_"):
        habit_id = cdata[len("rename_habit_"):]
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        # Odatni topib nomini saqlash
        habit = next((h for h in u.get("habits", []) if h["id"] == habit_id), None)
        if not habit:
            send_main_menu(uid)
            return True
        u["state"] = "renaming_habit"
        u["renaming_habit_id"] = habit_id
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.row(
            cBtn("⬅️ Orqaga", "change_habit_name", "primary"),
            cBtn(T(uid, "btn_home"), "menu_main", "primary")
        )
        sent = bot.send_message(
            uid,
            f"✏️ *{habit['name']}* — yangi nom yozing:",
            parse_mode="Markdown",
            reply_markup=cancel_kb
        )
        u["info_msg_id"] = sent.message_id
        save_user(uid, u)
        return True

    if cdata == "change_phone":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        u["state"] = "updating_phone"
        save_user(uid, u)
        kb_phone = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb_phone.add(KeyboardButton("📱 Yangi raqam yuborish", request_contact=True))
        sent = bot.send_message(
            uid,
            "📱 Yangi telefon raqamingizni yuboring:\n\n"
            "• Tugmani bosib yuboring, _yoki_\n"
            "• Qo'lda kiriting: *+998901234567*",
            parse_mode="Markdown",
            reply_markup=kb_phone
        )
        u["info_msg_id"] = sent.message_id
        save_user(uid, u)
        return True


    return False
