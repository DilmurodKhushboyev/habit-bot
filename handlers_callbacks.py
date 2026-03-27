#!/usr/bin/env python3
"""
Asosiy callback dispatcher - barcha callback larni yo'naltiradi
"""

import time
import threading

import telebot
from telebot.types import (InlineKeyboardMarkup, InlineKeyboardButton,
                            ReplyKeyboardMarkup, KeyboardButton)

from database import load_user, save_user
from helpers import get_lang, lang_keyboard, T
from bot_setup import (bot, send_main_menu, send_message_colored,
                       main_menu_dict, cBtn, build_main_text, main_menu)
from menus import check_subscription, send_sub_required

# Sub-handler modullar
from callbacks_admin import handle_admin_callbacks
from callbacks_settings import handle_settings_callbacks
from callbacks_habits import handle_habits_callbacks
from callbacks_menu import handle_menu_callbacks
from callbacks_groups import handle_group_callbacks
from callbacks_shop import handle_shop_callbacks


@bot.callback_query_handler(func=lambda c: True)
def callback_handler(call):
    uid   = call.from_user.id
    cdata = call.data
    u     = load_user(uid)

    if cdata == "evening_dismiss":
        try:
            bot.delete_message(uid, call.message.message_id)
        except Exception:
            bot.answer_callback_query(call.id)
        return

    # Universal "Tushunarli" tugma — bot xabarini o'chirish
    if cdata == "ack_delete_msg":
        try:
            bot.delete_message(uid, call.message.message_id)
        except Exception:
            bot.answer_callback_query(call.id)
        return

    # Ulashish natijasini o'chirish — "Tasdiqlash" tugmasi
    if cdata == "share_del":
        try:
            bot.delete_message(uid, call.message.message_id)
        except Exception:
            bot.answer_callback_query(call.id)
        return

    # Eski tugma bosilsa — bot yangilanganini bildirish
    # Til tanlash tugmalari phone bo'lmasa ham ishlashi kerak
    if not u.get("phone") and not cdata.startswith("set_lang_"):
        try:
            bot.answer_callback_query(call.id, "Bot 🆕 yangilangan, /start ni bosing!", show_alert=True)
        except Exception:
            pass
        return

    # Til tanlash
    if cdata.startswith("set_lang_"):
        lang = cdata[9:]
        u["lang"] = lang
        lang_msg_id = u.pop("lang_msg_id", None)
        from_settings = u.pop("lang_from_settings", False)
        save_user(uid, u)
        bot.answer_callback_query(call.id, T(uid, "lang_set"))
        # O'chiriladigan xabarlarni to'plash
        _lang_cleanup = []
        _lang_cleanup.append(call.message.message_id)
        if lang_msg_id and lang_msg_id != call.message.message_id:
            _lang_cleanup.append(lang_msg_id)
        if from_settings:
            # Sozlamalar menyusiga qaytish
            kb_set = InlineKeyboardMarkup()
            kb_set.add(InlineKeyboardButton(T(uid, "btn_change_lang"), callback_data="settings_lang"))
            kb_set.add(InlineKeyboardButton(T(uid, "btn_change_info"), callback_data="settings_info"))
            kb_set.add(cBtn(T(uid, "btn_home"),        "menu_main", "primary"))
            sent = bot.send_message(uid, T(uid, "settings_title"), parse_mode="Markdown", reply_markup=kb_set)
            u["main_msg_id"] = sent.message_id
            save_user(uid, u)
        else:
            name = call.from_user.first_name
            if not u.get("phone"):
                # Til tanlandi, endi telefon so'ralsin
                kb_ph = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
                kb_ph.add(KeyboardButton(T(uid, "share_phone"), request_contact=True))
                sent_ph = bot.send_message(
                    uid,
                    T(uid, "ask_phone"),
                    parse_mode="Markdown",
                    reply_markup=kb_ph
                )
                u["reg_msg_id"] = sent_ph.message_id
                u["state"] = "waiting_phone_reg"
                save_user(uid, u)
            elif u.get("habits"):
                sent_main = send_message_colored(uid, build_main_text(uid), main_menu_dict(uid))
                if sent_main is None:
                    sent_main = bot.send_message(uid, build_main_text(uid), parse_mode="Markdown", reply_markup=main_menu(uid))
                u["main_msg_id"] = sent_main.message_id
                save_user(uid, u)
            else:
                sent_main = send_message_colored(uid, T(uid, "welcome_new", name=name), main_menu_dict(uid))
                if sent_main is None:
                    sent_main = bot.send_message(uid, T(uid, "welcome_new", name=name), parse_mode="Markdown", reply_markup=main_menu(uid))
                u["main_msg_id"] = sent_main.message_id
                save_user(uid, u)
        # Yangi kontent ko'rsatilgandan KEYIN eski til xabarlarini o'chirish
        def _del_lang_batch(cid, ids):
            time.sleep(0.5)
            for mid in ids:
                try: bot.delete_message(cid, mid)
                except: pass
        threading.Thread(target=_del_lang_batch, args=(uid, _lang_cleanup), daemon=True).start()
        return

    if cdata not in ("check_sub", "admin_cancel", "admin_close") and not cdata.startswith("admin_"):
        if not check_subscription(uid):
            bot.answer_callback_query(call.id)
            send_sub_required(uid)
            return

    if cdata == "check_sub":
        if check_subscription(uid):
            bot.answer_callback_query(call.id, "✅")
            _sub_msg = call.message.message_id
            u.pop("sub_msg_id", None)
            save_user(uid, u)
            # Til tanlamagan bo'lsa
            if not u.get("lang"):
                sent_lang = bot.send_message(uid, "🌐 Tilni tanlang / Choose language / Выберите язык / Dil seçin:", reply_markup=lang_keyboard())
                u["lang_msg_id"] = sent_lang.message_id
                save_user(uid, u)
            else:
                send_main_menu(uid)
            # Yangi kontent ko'rsatilgandan KEYIN eski sub xabarini o'chirish
            def _del_sub_bg(cid, mid):
                time.sleep(0.5)
                try: bot.delete_message(cid, mid)
                except: pass
            threading.Thread(target=_del_sub_bg, args=(uid, _sub_msg), daemon=True).start()
        else:
            bot.answer_callback_query(call.id, "❌ Hali a'zo bo'lmadingiz!")
        return


    # ── Dispatch to sub-handlers ──
    if handle_admin_callbacks(call, uid, cdata, u): return
    if handle_settings_callbacks(call, uid, cdata, u): return
    if handle_habits_callbacks(call, uid, cdata, u): return
    if handle_menu_callbacks(call, uid, cdata, u): return
    if handle_group_callbacks(call, uid, cdata, u): return
    if handle_shop_callbacks(call, uid, cdata, u): return
