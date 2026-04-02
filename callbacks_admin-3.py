#!/usr/bin/env python3
"""
Admin callback handlerlari
"""

import time
import threading
from datetime import date, datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import ADMIN_ID
from database import (load_user, save_user, load_all_users, count_users,
                      load_settings, save_settings)
from helpers import T, get_lang
from bot_setup import (bot, send_main_menu, send_message_colored,
                       main_menu_dict, cBtn, ok_kb, kb_to_dict)
from menus import (admin_menu, admin_broadcast_menu, admin_stats_period_menu,
                   check_subscription, send_sub_required)


def handle_admin_callbacks(call, uid, cdata, u):
    """Admin callback larini qayta ishlaydi. True qaytarsa = handled."""

    def _clean_admin_msgs(uid, u):
        """Admin panel ichidagi barcha eski so'rov xabarlarini o'chirish"""
        for key in ("channel_msg_id", "give_points_msg_id", "bc_trigger_msg_id",
                     "reply_msg_id", "notify_confirm_msg_id", "admin_msg_id"):
            mid = u.pop(key, None)
            if mid:
                try: bot.delete_message(uid, mid)
                except: pass

    if cdata == "admin_test_onboard":
        if uid != ADMIN_ID:
            return True
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        send_main_menu(uid)
        return True

    if cdata == "admin_close":
        if uid != ADMIN_ID:
            return True
        u["state"] = None
        _clean_admin_msgs(uid, u)
        save_user(uid, u)
        bot.answer_callback_query(call.id)
        try:
            bot.delete_message(uid, call.message.message_id)
        except Exception:
            pass
        send_main_menu(uid)
        return True

    if cdata == "bc_user_ack":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        return True

    if cdata == "bc_confirm":
        if uid != ADMIN_ID:
            return True
        bot.answer_callback_query(call.id, "✅ Tasdiqlandi")
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        try: bot.send_message(uid, "🛠 *Admin panel*", parse_mode="Markdown", reply_markup=admin_menu())
        except: pass
        return True

    if cdata == "bc_detail":
        if uid != ADMIN_ID:
            return True
        failed_list = u.get("bc_failed_list", [])
        if not failed_list:
            bot.answer_callback_query(call.id, "Bloklagan foydalanuvchi yo'q", show_alert=True)
            return True
        bot.answer_callback_query(call.id)
        detail = "🚫 *Botni bloklagan foydalanuvchilar:*\n\n"
        for i, fl in enumerate(failed_list, 1):
            detail += f"  {i}. {fl}\n"
        kb_detail = InlineKeyboardMarkup()
        kb_detail.add(InlineKeyboardButton("✅ Tasdiqlash", callback_data="bc_detail_confirm"))
        try:
            bot.edit_message_text(detail, uid, call.message.message_id,
                                  parse_mode="Markdown", reply_markup=kb_detail)
        except:
            pass
        return True

    if cdata == "bc_detail_confirm":
        if uid != ADMIN_ID:
            return True
        bot.answer_callback_query(call.id, "✅ Tasdiqlandi")
        u.pop("bc_failed_list", None)
        save_user(uid, u)
        def del_bc_detail(chat_id, mid):
            time.sleep(5)
            try: bot.delete_message(chat_id, mid)
            except: pass
        threading.Thread(target=del_bc_detail, args=(uid, call.message.message_id), daemon=True).start()
        return True

    if cdata == "admin_cancel":
        if uid != ADMIN_ID:
            return True
        u["state"] = None
        _clean_admin_msgs(uid, u)
        save_user(uid, u)
        bot.answer_callback_query(call.id, "Bekor qilindi")
        try:
            bot.delete_message(uid, call.message.message_id)
        except Exception:
            pass
        bot.send_message(uid, "🛠 *Admin panel | Maxfiy va muhim qism*", parse_mode="Markdown", reply_markup=admin_menu())
        return True

    if cdata == "admin_notify_update":
        if uid != ADMIN_ID:
            return True
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        kb_confirm = InlineKeyboardMarkup()
        kb_confirm.row(
            InlineKeyboardButton("✅ Ha, yuborish", callback_data="admin_notify_confirm"),
            cBtn("❌ Yo'q", "admin_cancel", "danger")
        )
        sent_ask = bot.send_message(
            uid,
            "🆕 *Bot yangilandi xabari*\n\n"
            "Barcha foydalanuvchilarga quyidagi xabar yuboriladi:\n\n"
            "_\"Bot 🆕 yangilandi. /start ni bosib yoki yuborib siz ham yangilang!\"_\n\n"
            "Davom etasizmi?",
            parse_mode="Markdown",
            reply_markup=kb_confirm
        )
        u["notify_confirm_msg_id"] = sent_ask.message_id
        save_user(uid, u)
        return True

    if cdata == "admin_notify_confirm":
        if uid != ADMIN_ID:
            return True
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        users      = load_all_users(force=True)
        sent_count = 0
        failed     = 0
        update_text = "*Bot 🆕 yangilandi. /start ni bosib yoki yuborib siz ham yangilang!*"
        for target_uid in users:
            if int(target_uid) == ADMIN_ID:
                continue
            try:
                bot.send_message(int(target_uid), update_text, parse_mode="Markdown")
                sent_count += 1
            except Exception:
                failed += 1
        result = f"✅ Yangilanish xabari {sent_count} ta foydalanuvchiga yuborildi."
        if failed:
            result += f"\n❌ {failed} ta foydalanuvchiga yetmadi."
        sent_res = bot.send_message(uid, result)
        def del_res(chat_id, mid):
            time.sleep(5)
            try: bot.delete_message(chat_id, mid)
            except: pass
        threading.Thread(target=del_res, args=(uid, sent_res.message_id), daemon=True).start()
        bot.send_message(uid, "🛠 *Admin panel | Maxfiy va muhim qism*", parse_mode="Markdown", reply_markup=admin_menu())
        return True

    if cdata == "admin_give_points":
        if uid != ADMIN_ID:
            return True
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        u["state"] = "admin_waiting_points_id"
        kb2 = InlineKeyboardMarkup()
        kb2.add(cBtn("❌ Bekor qilish", "admin_cancel", "danger"))
        sent_gp = bot.send_message(
            uid,
            "🎁 *Ball berish / ayirish*\n\n"
            "Foydalanuvchi *ID raqamini* kiriting:\n\n"
            "_ID raqamni foydalanuvchilar ro'yxatidan topishingiz mumkin_",
            parse_mode="Markdown",
            reply_markup=kb2
        )
        u["give_points_msg_id"] = sent_gp.message_id
        save_user(uid, u)
        return True

    if cdata == "admin_broadcast":
        if uid != ADMIN_ID:
            return True
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        bot.send_message(uid, "📢 *Habar yuborish*\n\nQayerga yubormoqchisiz?", parse_mode="Markdown", reply_markup=admin_broadcast_menu())
        return True

    if cdata in ("admin_bc_private", "admin_bc_groups", "admin_bc_all"):
        if uid != ADMIN_ID:
            return True
        u["state"] = cdata
        save_user(uid, u)
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        labels = {"admin_bc_private": "shaxsiy chatlarga", "admin_bc_groups": "guruhlarga", "admin_bc_all": "hammaga"}
        # Trigger xabari — admindan reply kutamiz
        sent_trigger = bot.send_message(
            uid,
            f"✏️ *Yubormoqchi bo'lgan xabaringizni yozing ({labels[cdata]}):*\n\n"
            f"_Yozing — matn, rasm yoki video_",
            parse_mode="Markdown"
        )
        u["bc_trigger_msg_id"] = sent_trigger.message_id
        save_user(uid, u)
        return True

    if cdata == "admin_users" or cdata.startswith("admin_users_page_"):
        if uid != ADMIN_ID:
            return True
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        users = load_all_users(force=True)
        if not users:
            bot.send_message(uid, "👥 Foydalanuvchilar yo'q.", reply_markup=admin_menu())
            return True
        per_page    = 10
        users_list  = list(users.items())
        total       = len(users_list)
        total_pages = (total + per_page - 1) // per_page
        page        = 1
        if cdata.startswith("admin_users_page_"):
            page = int(cdata[17:])
        page = max(1, min(page, total_pages))
        start = (page - 1) * per_page
        end   = start + per_page
        page_users = users_list[start:end]

        text = f"👥 Jami: {total} ta foydalanuvchi | Sahifa {page}/{total_pages}\n" + "▬" * 20 + "\n\n"
        for i, (target_uid, udata) in enumerate(page_users, start + 1):
            name     = udata.get("name", "—")
            username = udata.get("username", "—")
            if username and username != "—" and not username.startswith("@"):
                username = "@" + username
            phone  = udata.get("phone", "Kiritilmagan")
            joined = udata.get("joined_at", "—")
            habits = udata.get("habits", [])
            text += f"👤 {i}. {name}\n"
            text += f"  🆔 ID: {target_uid}\n"
            text += f"  📌 Username: {username}\n"
            text += f"  📞 Tel: {phone}\n"
            text += f"  📅 Qo'shilgan: {joined}\n"
            if habits:
                text += f"  📋 Odatlar ({len(habits)} ta):\n"
                for h in habits:
                    text += f"    • {h['name']} | {h['time']} | streak: {h.get('streak',0)} kun\n"
            else:
                text += "  📋 Odatlar: yo'q\n"
            text += "\n"

        kb = InlineKeyboardMarkup()
        nav = []
        if page > 1:
            nav.append(InlineKeyboardButton(f"⬅️ {page-1}", callback_data=f"admin_users_page_{page-1}"))
        nav.append(InlineKeyboardButton(f"📄 {page}/{total_pages}", callback_data="noop"))
        if page < total_pages:
            nav.append(InlineKeyboardButton(f"{page+1} ➡️", callback_data=f"admin_users_page_{page+1}"))
        if len(nav) > 1 or total_pages > 1:
            kb.row(*nav)
        kb.row(
            cBtn("🔙 Admin panel", "admin_cancel", "primary"),
            cBtn("🏠 Asosiy menyu", "admin_close", "primary")
        )
        bot.send_message(uid, text, reply_markup=kb)
        return True

    if cdata == "admin_channel":
        if uid != ADMIN_ID:
            return True
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        settings = load_settings()
        msg_text = "🔗 *Majburiy kanallar* (maksimal 3 ta)\n\n"
        kb2 = InlineKeyboardMarkup()
        for i in range(1, 4):
            ch    = settings.get(f"required_channel_{i}", None)
            title = settings.get(f"required_channel_title_{i}", None)
            if ch:
                label = f"✅ {i}. {title or ch}"
                msg_text += f"{i}. {title or ch} ({ch})\n"
                kb2.row(
                    InlineKeyboardButton(f"✏️ {i}-ni o'zgartirish", callback_data=f"admin_ch_edit_{i}"),
                    InlineKeyboardButton(f"🗑 {i}-ni o'chirish",    callback_data=f"admin_ch_del_{i}")
                )
            else:
                msg_text += f"{i}. — (bo'sh)\n"
                kb2.add(InlineKeyboardButton(f"➕ {i}-kanal qo'shish", callback_data=f"admin_ch_edit_{i}"))
        # Eski format bilan moslik
        old_ch = settings.get("required_channel", None)
        if old_ch:
            msg_text += f"\n_(Eski format: {old_ch})_"
        msg_text += "\n\nQaysi kanalni boshqarmoqchisiz?"
        kb2.add(cBtn("❌ Bekor qilish", "admin_cancel", "danger"))
        sent_ch = bot.send_message(uid, msg_text, parse_mode="Markdown", reply_markup=kb2)
        u["channel_msg_id"] = sent_ch.message_id
        save_user(uid, u)
        return True

    if cdata.startswith("admin_ch_edit_"):
        if uid != ADMIN_ID:
            return True
        slot = int(cdata[14:])
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        u["state"] = f"admin_waiting_channel_{slot}"
        kb2 = InlineKeyboardMarkup()
        kb2.add(cBtn("❌ Bekor qilish", "admin_cancel", "danger"))
        sent_ch = bot.send_message(
            uid,
            f"🔗 {slot}-kanal username yozing:\n\nMasalan: `@mening_kanalim`",
            parse_mode="Markdown",
            reply_markup=kb2
        )
        u["channel_msg_id"] = sent_ch.message_id
        save_user(uid, u)
        return True

    if cdata.startswith("admin_ch_del_"):
        if uid != ADMIN_ID:
            return True
        slot = int(cdata[13:])
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        settings = load_settings()
        settings.pop(f"required_channel_{slot}", None)
        settings.pop(f"required_channel_title_{slot}", None)
        save_settings(settings)
        bot.send_message(uid, f"✅ {slot}-kanal o'chirildi.", reply_markup=admin_menu())
        return True

    if cdata == "admin_stats":
        if uid != ADMIN_ID:
            return True
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        bot.send_message(uid, "📈 *Statistika — davr tanlang:*", parse_mode="Markdown", reply_markup=admin_stats_period_menu())
        return True

    if cdata.startswith("admin_stats_"):
        if uid != ADMIN_ID:
            return True
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        period = cdata[12:]
        users  = load_all_users(force=True)
        today  = date.today()
        if period == "all":
            filtered     = users
            period_label = "Umumiy"
        else:
            days     = int(period)
            filtered = {}
            for k, v in users.items():
                try:
                    joined = date.fromisoformat(v.get("joined_at", "2000-01-01"))
                    if (today - joined).days <= days:
                        filtered[k] = v
                except Exception:
                    pass
            labels       = {"1": "1 kun", "7": "1 hafta", "30": "1 oy", "365": "1 yil"}
            period_label = labels.get(period, period)
        text  = f"📈 *Statistika — {period_label}*\n\n"
        text += f"👥 Qo'shilgan foydalanuvchilar: *{len(filtered)} ta*\n\n"
        text += "📋 *Odat yaratish bo'yicha:*\n"
        habit_counts = []
        for target_uid, udata in users.items():
            count = len(udata.get("habits", []))
            if count > 0:
                habit_counts.append((udata.get("name", f"ID:{target_uid}"), count))
        habit_counts.sort(key=lambda x: x[1], reverse=True)
        if habit_counts:
            for name, count in habit_counts[:20]:
                text += f"  • *{name}*: {count} ta odat\n"
        else:
            text += "  Hali odat yaratilmagan.\n"
        kb2 = InlineKeyboardMarkup()
        kb2.add(cBtn("❌ Bekor qilish", "admin_cancel", "danger"))
        bot.send_message(uid, text, parse_mode="Markdown", reply_markup=kb2)
        return True


    # admin_reply_to (4520-4538)
    if cdata.startswith("admin_reply_to_") and uid == ADMIN_ID:
        target_user_id = int(cdata[15:])
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        u["state"] = f"admin_waiting_reply_{target_user_id}"
        kb_cancel = InlineKeyboardMarkup()
        kb_cancel.add(cBtn("❌ Bekor qilish", "admin_cancel", "danger"))
        target_u  = load_user(target_user_id)
        sent_rp   = bot.send_message(
            uid,
            f"↩️ *{target_u.get('name','Foydalanuvchi')}* ga javob yozing:",
            parse_mode="Markdown",
            reply_markup=kb_cancel
        )
        u["reply_msg_id"] = sent_rp.message_id
        save_user(uid, u)
        return True


    # admin_confirm_ball (4563-4575)
    if cdata.startswith("admin_confirm_ball_") and uid == ADMIN_ID:
        bot.answer_callback_query(call.id, "✅")
        def del_admin_ball_msg(msg_id):
            time.sleep(5)
            try: bot.delete_message(ADMIN_ID, msg_id)
            except: pass
        threading.Thread(target=del_admin_ball_msg, args=(call.message.message_id,), daemon=True).start()
        return True

    if cdata == "noop":
        bot.answer_callback_query(call.id)
        return True


    return False
