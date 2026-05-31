#!/usr/bin/env python3
"""
Bozor/do'kon callback handlerlari
"""

import time
import threading
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import ADMIN_ID, SHOP_PRICES
from database import load_user, save_user, add_points_history
from db_lock import user_lock
from helpers import T, get_lang
from bot_setup import (bot, send_main_menu, send_message_colored,
                       main_menu_dict, cBtn, ok_kb, kb_to_dict,
                       edit_message_colored, get_bot_username)


def _bozor_back_row(uid):
    """Orqaga + Asosiy menyu tugmalar qatori (qayta ishlatiladigan)."""
    kb = InlineKeyboardMarkup()
    kb.row(
        cBtn(T(uid, "bozor_btn_back"), "menu_bozor", "primary"),
        cBtn(T(uid, "btn_home"), "menu_main", "primary")
    )
    return kb


def handle_shop_callbacks(call, uid, cdata, u):
    """Bozor callback larini qayta ishlaydi. True = handled."""

    if cdata == "menu_bozor":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        balls = u.get("points", 0)
        ref_count = len(u.get("referrals", []))
        jon_val = round(u.get("jon", 100.0))
        jon_price = SHOP_PRICES["jon_restore"]
        bozor_text = T(uid, "bozor_title").format(
            points=balls, ref_count=ref_count,
            jon=jon_val, jon_price=jon_price
        )
        btn_jon = T(uid, "bozor_btn_buy_jon").format(price=jon_price)
        bozor_kb = {"inline_keyboard": [
            [{"text": btn_jon,                          "callback_data": "bozor_buy_jon",       "style": "primary"}],
            [{"text": T(uid, "bozor_btn_referral"),     "callback_data": "bozor_referral",      "style": "primary"}],
            [{"text": T(uid, "bozor_btn_transfer"),     "callback_data": "bozor_transfer"}],
            [{"text": T(uid, "bozor_btn_reset"),        "callback_data": "bozor_reset_confirm", "style": "danger"}],
            [{"text": T(uid, "btn_home"),               "callback_data": "menu_main",           "style": "primary"}],
        ]}
        sent = send_message_colored(uid, bozor_text, bozor_kb)
        if sent is None:
            kb_b = InlineKeyboardMarkup()
            kb_b.add(InlineKeyboardButton(btn_jon, callback_data="bozor_buy_jon"))
            kb_b.add(InlineKeyboardButton(T(uid, "bozor_btn_referral"), callback_data="bozor_referral"))
            kb_b.add(InlineKeyboardButton(T(uid, "bozor_btn_transfer"), callback_data="bozor_transfer"))
            kb_b.add(InlineKeyboardButton(T(uid, "bozor_btn_reset"),    callback_data="bozor_reset_confirm"))
            kb_b.add(cBtn(T(uid, "btn_home"), "menu_main", "primary"))
            sent = bot.send_message(uid, bozor_text, parse_mode="Markdown", reply_markup=kb_b)
        u["main_msg_id"] = sent.message_id
        save_user(uid, u)
        return True

    if cdata == "jonfix":
        # 💀 "Jon 0%" ogohlantirishidagi tugma — bir martalik, bosilgach xabar o'chadi
        bot.answer_callback_query(call.id)
        balls = u.get("points", 0)
        jon_val = round(u.get("jon", 100.0))
        jon_price = SHOP_PRICES["jon_restore"]

        def _del_jonfix_msg():
            try: bot.delete_message(uid, call.message.message_id)
            except Exception: pass

        # S1 (race condition): load→modify→save bloki lock ichida, u QAYTA o'qiladi
        # (tashqaridagi u eski nusxa bo'lishi mumkin). Tekshiruvlar ham lock ichida.
        try:
            with user_lock(uid):
                u = load_user(uid)
                jon_val = round(u.get("jon", 100.0))
                balls = u.get("points", 0)

                # Jon allaqachon yetarli (odat bajarib tiklagan) → tashqarida o'chir
                if jon_val > 20:
                    fixed = "already"
                # Ball yetmaydi → xabar QOLADI (keyin bosishi mumkin)
                elif balls < jon_price:
                    fixed = "no_pts"
                else:
                    u["points"] = balls - jon_price
                    add_points_history(u, -jon_price)
                    u["jon"] = 100.0
                    save_user(uid, u)
                    fixed = "done"
        except TimeoutError:
            bot.send_message(uid, T(uid, "err_server_busy"),
                             parse_mode="Markdown", reply_markup=ok_kb(uid))
            return True

        if fixed == "already":
            _del_jonfix_msg()
            bot.answer_callback_query(call.id, T(uid, "jon_zero_already"), show_alert=False)
            return True
        if fixed == "no_pts":
            bot.send_message(uid,
                T(uid, "bozor_jon_no_pts").format(price=jon_price, points=balls),
                parse_mode="Markdown", reply_markup=ok_kb(uid)
            )
            return True

        # fixed == "done" → jon berildi, xabarni o'chir
        _del_jonfix_msg()
        sent_ok = bot.send_message(uid, T(uid, "jon_zero_done"), parse_mode="Markdown")
        def _del_jonfix_ok(chat_id, mid):
            time.sleep(2)
            try: bot.delete_message(chat_id, mid)
            except: pass
        threading.Thread(target=_del_jonfix_ok, args=(uid, sent_ok.message_id), daemon=True).start()
        return True

    if cdata == "bozor_buy_jon":
        bot.answer_callback_query(call.id)
        jon_price = SHOP_PRICES["jon_restore"]
        # S1 (race condition): tekshiruv + load→modify→save lock ichida, u QAYTA o'qiladi.
        try:
            with user_lock(uid):
                u = load_user(uid)
                balls = u.get("points", 0)
                jon_val = round(u.get("jon", 100.0))
                if jon_val > 20:
                    outcome = "high"
                elif balls < jon_price:
                    outcome = "no_pts"
                else:
                    u["points"] = balls - jon_price
                    add_points_history(u, -jon_price)
                    u["jon"]    = 100.0
                    save_user(uid, u)
                    outcome = "ok"
        except TimeoutError:
            bot.send_message(uid, T(uid, "err_server_busy"),
                             parse_mode="Markdown", reply_markup=ok_kb(uid))
            return True

        if outcome == "high":
            bot.send_message(uid,
                T(uid, "bozor_jon_high").format(jon=jon_val),
                parse_mode="Markdown", reply_markup=ok_kb(uid)
            )
            return True
        if outcome == "no_pts":
            bot.send_message(uid,
                T(uid, "bozor_jon_no_pts").format(price=jon_price, points=balls),
                parse_mode="Markdown", reply_markup=ok_kb(uid)
            )
            return True
        bot.send_message(uid,
            T(uid, "bozor_jon_ok").format(price=jon_price),
            parse_mode="Markdown", reply_markup=ok_kb(uid)
        )
        return True

    if cdata == "bozor_referral":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        bot_info     = bot.get_me()
        bot_username = bot_info.username
        ref_link     = f"https://t.me/{bot_username}?start=ref_{uid}"
        ref_count    = len(u.get("referrals", []))
        balls_from_refs = ref_count * 50
        # Chegara sovg'alar ro'yxati (til-neytral, emoji + raqam)
        milestones = [
            (5,  "🛡 Streak shield",   ""),
            (10, "⭐ +100 bonus",       ""),
            (20, "💎 VIP badge",        ""),
        ]
        # Matn yig'ish
        text  = T(uid, "bozor_ref_title") + "\n\n"
        text += T(uid, "bozor_ref_link").format(link=ref_link) + "\n\n"
        text += T(uid, "bozor_ref_stats").format(count=ref_count, balls=balls_from_refs) + "\n"
        text += "\n" + "━" * 16 + "\n"
        text += T(uid, "bozor_ref_reward") + "\n"
        text += "\n" + "━" * 16 + "\n"
        text += T(uid, "bozor_ref_goals") + "\n"
        for m_count, m_title, m_desc in milestones:
            if ref_count >= m_count:
                text += f"✅ *{m_count}* → {m_title}\n"
            else:
                text += f"⬜ *{m_count}* → {m_title}\n"
                if m_desc:
                    for line in m_desc.split("\n"):
                        text += f"          _{line}_\n"
        text += "\n"
        next_ms = next((m for m in milestones if ref_count < m[0]), None)
        if next_ms:
            need = next_ms[0] - ref_count
            text += T(uid, "bozor_ref_next").format(need=need)
        else:
            text += T(uid, "bozor_ref_all_done")
        kb_ref = InlineKeyboardMarkup()
        kb_ref.add(InlineKeyboardButton(
            T(uid, "bozor_ref_copy"), switch_inline_query=ref_link
        ))
        kb_ref.row(
            cBtn(T(uid, "bozor_btn_back"), "menu_bozor", "primary"),
            cBtn(T(uid, "btn_home"), "menu_main", "primary")
        )
        sent = bot.send_message(uid, text, parse_mode="Markdown", reply_markup=kb_ref)
        u["main_msg_id"] = sent.message_id
        save_user(uid, u)
        return True

    if cdata == "bozor_transfer":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        u["state"] = "bozor_waiting_transfer_id"
        sent = bot.send_message(
            uid, T(uid, "bozor_transfer_ask"),
            parse_mode="Markdown", reply_markup=_bozor_back_row(uid)
        )
        u["temp_msg_id"] = sent.message_id
        save_user(uid, u)
        return True

    if cdata == "bozor_reset_confirm":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        kb_conf = InlineKeyboardMarkup()
        kb_conf.row(
            cBtn(T(uid, "bozor_reset_yes"), "bozor_reset_do", "success"),
            InlineKeyboardButton(T(uid, "bozor_reset_no"), callback_data="menu_bozor")
        )
        sent = bot.send_message(
            uid, T(uid, "bozor_reset_warn"),
            parse_mode="Markdown", reply_markup=kb_conf
        )
        u["main_msg_id"] = sent.message_id
        save_user(uid, u)
        return True

    if cdata == "bozor_reset_do":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        old_points = u.get("points", 0)
        # S1 (race condition): ball nolga tushirish lock ichida, u QAYTA o'qiladi
        # (ayni vaqtda checkin ball qo'shsa — yo'qolmasin, joriy balansdan reset).
        try:
            with user_lock(uid):
                u = load_user(uid)
                old_points = u.get("points", 0)
                u["points"] = 0
                # Period-filtered rating uchun reset hodisasini points_history ga yozish
                if old_points > 0:
                    add_points_history(u, -old_points)
                save_user(uid, u)
        except TimeoutError:
            bot.send_message(uid, T(uid, "err_server_busy"),
                             parse_mode="Markdown", reply_markup=ok_kb(uid))
            return True
        sent_ok = bot.send_message(uid, T(uid, "ok_points_reset"), parse_mode="Markdown")
        def del_reset_ok(chat_id, mid):
            time.sleep(2)
            try: bot.delete_message(chat_id, mid)
            except: pass
        threading.Thread(target=del_reset_ok, args=(uid, sent_ok.message_id), daemon=True).start()
        # Bozor menyusiga qaytish — yangilangan matn bilan
        jon_val = round(u.get("jon", 100.0))
        jon_price = SHOP_PRICES["jon_restore"]
        ref_count = len(u.get("referrals", []))
        bozor_text = T(uid, "bozor_title").format(
            points=0, ref_count=ref_count,
            jon=jon_val, jon_price=jon_price
        )
        btn_jon = T(uid, "bozor_btn_buy_jon").format(price=jon_price)
        kb_b = InlineKeyboardMarkup()
        kb_b.add(InlineKeyboardButton(btn_jon, callback_data="bozor_buy_jon"))
        kb_b.add(InlineKeyboardButton(T(uid, "bozor_btn_referral"), callback_data="bozor_referral"))
        kb_b.add(InlineKeyboardButton(T(uid, "bozor_btn_transfer"), callback_data="bozor_transfer"))
        kb_b.add(InlineKeyboardButton(T(uid, "bozor_btn_reset"),    callback_data="bozor_reset_confirm"))
        kb_b.add(cBtn(T(uid, "btn_home"), "menu_main", "primary"))
        sent2 = bot.send_message(
            uid, bozor_text, parse_mode="Markdown", reply_markup=kb_b
        )
        u2 = load_user(uid)
        u2["main_msg_id"] = sent2.message_id
        save_user(uid, u2)
        return True

    if cdata == "bozor_subtract":
        # Olib tashlangan (audit #7): foydalanuvchi o'ziga ball ayira olmaydi.
        # Reset (bozor_reset_confirm) saqlanib qoladi — to'liq 0 ga tushirish uchun.
        bot.answer_callback_query(call.id)
        return True


    return False
