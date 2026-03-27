#!/usr/bin/env python3
"""
Bozor/do'kon callback handlerlari
"""

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import ADMIN_ID
from database import load_user, save_user
from helpers import T, get_lang
from bot_setup import (bot, send_main_menu, send_message_colored,
                       main_menu_dict, cBtn, ok_kb, kb_to_dict,
                       edit_message_colored, get_bot_username)


def handle_shop_callbacks(call, uid, cdata, u):
    """Bozor callback larini qayta ishlaydi. True = handled."""

    if cdata == "menu_bozor":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        balls = u.get("points", 0)
        ref_count  = len(u.get("referrals", []))
        jon_val = round(u.get("jon", 100.0))
        bozor_text = (
            f"🛒 *Bozor —* bu sizning ballaringiz bilan qilinadigan barcha ammalar joyi.\n\n"
            f"*⭐ Sizning balingiz:* {balls} ball\n"
            f"*👥 Taklif qilganlar:* {ref_count} ta do'st\n"
            f"*❤️ Jon:* {jon_val}%\n\n"
            "*❤️ Jon sotib olish —* 50 ball evaziga jonni 100% ga tiklash\n"
            "*👥 Do'st taklif qilish —* +50 ball (siz), +25 ball (do'st)\n"
            "*💸 Ballarni ayirboshlash —* yaqin insoniga ball yuborish\n"
            "*🔴 Ballarimni 0 ga tushirish —* barcha ballarni nollash\n"
            "*➖ Ballarimdan olib tashlash —* ma'lum miqdorni ayirish"
        )
        bozor_kb = {"inline_keyboard": [
            [{"text": "❤️ Jon sotib olish (50 ball)",  "callback_data": "bozor_buy_jon",       "style": "primary"}],
            [{"text": "👥 Do'st taklif qilish",        "callback_data": "bozor_referral",      "style": "primary"}],
            [{"text": "💸 Ballarni ayirboshlash",       "callback_data": "bozor_transfer"}],
            [{"text": "🔴 Ballarimni 0 ga tushirish",   "callback_data": "bozor_reset_confirm", "style": "danger"}],
            [{"text": "➖ Ballarimdan olib tashlash",    "callback_data": "bozor_subtract"}],
            [{"text": T(uid, "btn_home"),                "callback_data": "menu_main",           "style": "primary"}],
        ]}
        sent = send_message_colored(uid, bozor_text, bozor_kb)
        if sent is None:
            kb_b = InlineKeyboardMarkup()
            kb_b.add(InlineKeyboardButton("❤️ Jon sotib olish (50 ball)", callback_data="bozor_buy_jon"))
            kb_b.add(InlineKeyboardButton("👥 Do'st taklif qilish",      callback_data="bozor_referral"))
            kb_b.add(InlineKeyboardButton("💸 Ballarni ayirboshlash",     callback_data="bozor_transfer"))
            kb_b.add(InlineKeyboardButton("🔴 Ballarimni 0 ga tushirish", callback_data="bozor_reset_confirm"))
            kb_b.add(InlineKeyboardButton("➖ Ballarimdan olib tashlash",  callback_data="bozor_subtract"))
            kb_b.add(cBtn(T(uid, "btn_home"),             "menu_main", "primary"))
            sent = bot.send_message(uid, bozor_text, parse_mode="Markdown", reply_markup=kb_b)
        u["main_msg_id"] = sent.message_id
        save_user(uid, u)
        return True

    if cdata == "bozor_buy_jon":
        bot.answer_callback_query(call.id)
        balls = u.get("points", 0)
        jon_val = round(u.get("jon", 100.0))
        if jon_val > 20:
            bot.send_message(uid,
                f"❤️ *Jon sotib olish mumkin emas!*\n\n"
                f"Jon faqat *20% va undan kam* bo'lganda sotib olinadi.\n"
                f"Hozirgi joningiz: *{jon_val}%*",
                parse_mode="Markdown",
                reply_markup=ok_kb(uid)
            )
            return True
        if balls < 50:
            bot.send_message(uid,
                f"⭐ *Balingiz yetarli emas!*\n\nJon sotib olish uchun *50 ball* kerak.\n"
                f"Sizda hozir: *{balls} ball*\n\n"
                "Har kuni odatlarni bajaring — ball to'playsiz! 💪",
                parse_mode="Markdown",
                reply_markup=ok_kb(uid)
            )
            return True
        u["points"] = balls - 50
        u["jon"]    = 100.0
        save_user(uid, u)
        bot.send_message(uid,
            "❤️ *Jon tiklandi!*\n\n"
            "50 ball sarflandi — joningiz *100%* ga qaytdi!\n"
            "Endi odatlarni davom ettiring! 💪",
            parse_mode="Markdown",
            reply_markup=ok_kb(uid)
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
        # Chegara sovg'alar ro'yxati
        milestones = [
            (5,  "🛡 Streak himoyasi",
                 "Bir kun odat bajarmay qolsangiz\nstreakingiz saqlanib qoladi!"),
            (10, "⭐ +100 ball bonus",  ""),
            (20, "💎 VIP nishon",
                 "Reytingda maxsus belgi +\nkelajakda imtiyozlar!"),
        ]
        # Sarlavha
        text  = "👥 *Do'st taklif qilish*\n\n"
        text += f"*🔗 Sizning linkingiz:*\n`{ref_link}`\n\n"
        text += f"*👥 Taklif qilganlar:* {ref_count} ta do'st\n"
        text += f"*⭐ Yig'ilgan ball:* +{balls_from_refs}\n"
        text += "\n" + "━" * 16 + "\n"
        # Har bir do'st uchun mukofot
        text += "*🎁 Har bir do'st uchun:*\n"
        text += "• Siz: *+50 ball*\n"
        text += "• Do'stingiz: *+25 ball*\n"
        text += "\n" + "━" * 16 + "\n"
        # Chegara sovg'alari
        text += "*🏆 Chegara sovg'alari:*\n"
        next_found = False
        for m_count, m_title, m_desc in milestones:
            if ref_count >= m_count:
                # Allaqachon olindi
                text += f"✅ *{m_count} ta* → {m_title}\n"
            else:
                if not next_found:
                    # Keyingi maqsad
                    need = m_count - ref_count
                    text += f"⬜ *{m_count} ta* → {m_title}\n"
                    if m_desc:
                        for line in m_desc.split("\n"):
                            text += f"          _{line}_\n"
                    next_found = True
                else:
                    text += f"⬜ *{m_count} ta* → {m_title}\n"
                    if m_desc:
                        for line in m_desc.split("\n"):
                            text += f"          _{line}_\n"
        text += "\n"
        # Keyingi chegaragacha qolgan
        next_ms = next((m for m in milestones if ref_count < m[0]), None)
        if next_ms:
            need = next_ms[0] - ref_count
            text += f"*⏳ Keyingi sovg'agacha:* {need} ta do'st qoldi"
        else:
            text += "🏆 *Barcha chegara sovg'alarini oldingiz!*"
        kb_ref = InlineKeyboardMarkup()
        kb_ref.add(InlineKeyboardButton("📋 Havolani nusxalash", switch_inline_query=ref_link))
        kb_ref.row(
            cBtn("⬅️ Orqaga", "menu_bozor", "primary"),
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
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.row(
            cBtn("⬅️ Orqaga", "menu_bozor", "primary"),
            cBtn(T(uid, "btn_home"), "menu_main", "primary")
        )
        sent = bot.send_message(
            uid,
            "💸 *Ballarni ayirboshlash*\n\n"
            "Ballarni yubormoqchi bo'lgan foydalanuvchining *Telegram ID* sini kiriting:\n\n"
            "_ID raqamni foydalanuvchidan so'rang yoki reyitingda ko'ring_",
            parse_mode="Markdown", reply_markup=cancel_kb
        )
        u["temp_msg_id"] = sent.message_id
        save_user(uid, u)
        return True

    if cdata == "bozor_edit":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        balls = u.get("points", 0)
        kb_edit = InlineKeyboardMarkup()
        kb_edit.add(InlineKeyboardButton("🔴 Ballarimni 0 ga tushirish", callback_data="bozor_reset_confirm"))
        kb_edit.add(InlineKeyboardButton("➖ Ballarimdan qanchasini olib tashlash", callback_data="bozor_subtract"))
        kb_edit.row(
            cBtn("⬅️ Orqaga", "menu_bozor", "primary"),
            cBtn(T(uid, "btn_home"), "menu_main", "primary")
        )
        sent = bot.send_message(
            uid,
            f"✏️ *Ballarni tahrirlash*\n\n⭐ Joriy balingiz: *{balls} ball*",
            parse_mode="Markdown", reply_markup=kb_edit
        )
        u["main_msg_id"] = sent.message_id
        save_user(uid, u)
        return True

    if cdata == "bozor_reset_confirm":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        kb_conf = InlineKeyboardMarkup()
        kb_conf.row(
            cBtn("✅ Ha, 0 ga tushirish", "bozor_reset_do", "success"),
            InlineKeyboardButton("❌ Yo'q",               callback_data="menu_bozor")
        )
        sent = bot.send_message(
            uid,
            "⚠️ Haqiqatan ham barcha ballaringizni *0 ga* tushirmoqchimisiz?",
            parse_mode="Markdown", reply_markup=kb_conf
        )
        u["main_msg_id"] = sent.message_id
        save_user(uid, u)
        return True

    if cdata == "bozor_reset_do":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        u["points"] = 0
        save_user(uid, u)
        sent_ok = bot.send_message(uid, T(uid, "ok_points_reset"), parse_mode="Markdown")
        def del_reset_ok(chat_id, mid):
            time.sleep(2)
            try: bot.delete_message(chat_id, mid)
            except: pass
        threading.Thread(target=del_reset_ok, args=(uid, sent_ok.message_id), daemon=True).start()
        # Bozor menyusiga qaytish
        balls = 0
        kb_b  = InlineKeyboardMarkup()
        kb_b.add(InlineKeyboardButton("💸 Ballarni ayirboshlash",    callback_data="bozor_transfer"))
        kb_b.add(InlineKeyboardButton("🔴 Ballarimni 0 ga tushirish", callback_data="bozor_reset_confirm"))
        kb_b.add(InlineKeyboardButton("➖ Ballarimdan olib tashlash",  callback_data="bozor_subtract"))
        kb_b.add(cBtn(T(uid, "btn_home"),             "menu_main", "primary"))
        sent2 = bot.send_message(
            uid,
            f"🛒 *Bozor —* bu sizning ballaringiz bilan qilinadigan barcha ammalar joyi.\n\n*⭐ Sizning balingiz:* {balls} ball\n\n"
            "*💸 Ballarni ayirboshlash —* yaqin insoniga ball yuborish\n"
            "*🔴 Ballarimni 0 ga tushirish —* barcha ballarni nollash\n"
            "*➖ Ballarimdan olib tashlash —* ma'lum miqdorni ayirish",
            parse_mode="Markdown", reply_markup=kb_b
        )
        u2 = load_user(uid)
        u2["main_msg_id"] = sent2.message_id
        save_user(uid, u2)
        return True

    if cdata == "bozor_subtract":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        u["state"] = "bozor_waiting_subtract"
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.row(
            cBtn("⬅️ Orqaga", "menu_bozor", "primary"),
            cBtn(T(uid, "btn_home"), "menu_main", "primary")
        )
        sent = bot.send_message(
            uid,
            f"➖ *Ballarni olib tashlash*\n\n⭐ Joriy balingiz: *{u.get('points', 0)} ball*\n\nQancha ball olib tashlansin?",
            parse_mode="Markdown", reply_markup=cancel_kb
        )
        u["temp_msg_id"] = sent.message_id
        save_user(uid, u)
        return True


    return False
