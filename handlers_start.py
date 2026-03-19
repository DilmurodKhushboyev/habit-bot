"""
handlers_start.py
=================
/start buyrug'i, telefon raqam (contact), admin panel handlerlari.
Bu faylda: cmd_start, handle_contact, cmd_admin_panel va barcha start handlerlari.
Bog'liq fayllar: config.py, database.py, languages.py, keyboards.py
"""

import telebot
import os
import requests
import json
from datetime import datetime, date
from telebot.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from config import BOT_TOKEN, ADMIN_ID, mongo_col, groups_col
from database import load_user, save_user, load_settings, save_settings, load_group, count_users
from languages import T, get_lang, LANGS, lang_keyboard
from keyboards import (bot, main_menu, main_menu_dict, send_message_colored,
                       edit_message_colored, cBtn, ok_kb, kb_to_dict,
                       send_main_menu, build_main_text,
                       menu2_dict, build_menu2_text, send_menu2,
                       check_subscription, send_sub_required,
                       admin_menu, admin_broadcast_menu, admin_stats_period_menu)

# ============================================================
#  ADMIN PANEL
# ============================================================
@bot.message_handler(commands=["admin_panel"])
def cmd_admin_panel(msg):
    uid = msg.from_user.id
    try:
        bot.delete_message(uid, msg.message_id)
    except Exception:
        pass
    if uid != ADMIN_ID:
        def send_and_delete():
            sent = bot.send_message(uid, "🔒 Bu buyruq faqat adminlar uchun.")
            time.sleep(3)
            try:
                bot.delete_message(uid, sent.message_id)
            except Exception:
                pass
        threading.Thread(target=send_and_delete, daemon=True).start()
        return
    u = load_user(uid)
    # Eski admin panel va asosiy menyu xabarlarini o'chirish
    old_admin_msg = u.pop("admin_msg_id", None)
    old_main_msg  = u.pop("main_msg_id", None)
    save_user(uid, u)
    for mid in [old_admin_msg, old_main_msg]:
        if mid:
            try:
                bot.delete_message(uid, mid)
            except Exception:
                pass
    sent_admin = bot.send_message(uid, "🛠 *Admin panel | Maxfiy va muhim qism*", parse_mode="Markdown", reply_markup=admin_menu())
    u = load_user(uid)
    u["admin_msg_id"] = sent_admin.message_id
    save_user(uid, u)

# ============================================================
#  /start
# ============================================================

@bot.message_handler(commands=["test_onboard"])
def cmd_test_onboard(msg):
    """Faqat admin uchun — onboardingni qayta ko'rish"""
    uid = msg.from_user.id
    if uid != ADMIN_ID:
        return
    try: bot.delete_message(uid, msg.message_id)
    except: pass
    send_main_menu(uid)

@bot.message_handler(commands=["start"])
def cmd_start(msg):
    uid  = msg.from_user.id
    name = msg.from_user.first_name

    # Admin broadcast state da bo'lsa /start ni e'tiborsiz qoldirish
    u_prev = load_user(uid)
    if uid == ADMIN_ID and u_prev.get("state") in ("admin_bc_private", "admin_bc_groups", "admin_bc_all"):
        return

    # Barcha oldingi xabarlarni o'chirish + holatni tozalash
    u_prev = load_user(uid)
    old_start_ids = list(u_prev.get("start_msg_ids", []))
    old_main = u_prev.get("main_msg_id")
    if old_main and old_main not in old_start_ids:
        old_start_ids.append(old_main)
    # Ro'yxatdan o'tish oraliq xabarlarini ham o'chirish
    for _key in ("lang_msg_id", "reg_msg_id", "sub_msg_id"):
        _mid = u_prev.get(_key)
        if _mid and _mid not in old_start_ids:
            old_start_ids.append(_mid)
        u_prev.pop(_key, None)
    # Eski /start buyruq xabarini o'chirish (faqat OLDINGI /start)
    old_start_cmd = u_prev.get("start_cmd_msg_id")
    if old_start_cmd and old_start_cmd not in old_start_ids:
        old_start_ids.append(old_start_cmd)
    # Yangi /start xabarini saqlash (keyingi /start kelganda o'chiriladi)
    u_prev["start_cmd_msg_id"] = msg.message_id
    u_prev["start_msg_ids"] = []
    u_prev["state"] = None
    u_prev.pop("temp_habit", None)
    u_prev.pop("temp_msg_id", None)
    save_user(uid, u_prev)
    def delete_old_starts(chat_id, ids):
        for mid in ids:
            try: bot.delete_message(chat_id, mid)
            except: pass
    threading.Thread(target=delete_old_starts, args=(uid, old_start_ids), daemon=True).start()

    # Referal parametr
    start_param = msg.text.split()[1] if len(msg.text.split()) > 1 else ""
    if start_param.startswith("ref_"):
        try:
            referrer_id = int(start_param[4:])
            if referrer_id != uid:
                u_check = load_user(uid)
                if not u_check.get("ref_used") and not u_check.get("phone"):
                    u_check["pending_referrer"] = referrer_id
                    save_user(uid, u_check)
        except Exception:
            pass

    # Guruhga qo'shilish parametri
    if start_param.startswith("grp_"):
        g_id = start_param[4:]
        u_check = load_user(uid)
        if u_check.get("phone"):
            g = load_group(g_id)
            if g and str(uid) not in [str(m) for m in g.get("members", [])] and str(uid) != str(g.get("admin_id","")):
                admin_id = g.get("admin_id")
                # Foydalanuvchiga: so'rov yuborildi
                sent_req = bot.send_message(uid,
                    f"📨 *{g['name']}* guruhiga qo'shilish so'rovingiz yuborildi!\n\n"
                    f"Guruh egasi tasdiqlashini kuting...",
                    parse_mode="Markdown"
                )
                def del_req(chat_id, mid):
                    time.sleep(5)
                    try: bot.delete_message(chat_id, mid)
                    except: pass
                threading.Thread(target=del_req, args=(uid, sent_req.message_id), daemon=True).start()
                # Adminga: tasdiqlash so'rovi
                if admin_id:
                    try:
                        joiner_name = u_check.get("name", "Foydalanuvchi")
                        kb_approve = InlineKeyboardMarkup()
                        kb_approve.row(
                            cBtn(f"✅ Qabul qilish", f"group_approve_{g_id}_{uid}", "success"),
                            cBtn(f"❌ Rad etish",    f"group_reject_{g_id}_{uid}",  "danger")
                        )
                        bot.send_message(int(admin_id),
                            f"👋 *{joiner_name}* guruhga qo'shilmoqchi!\n\n"
                            f"👥 *{g['name']}*\n"
                            f"📌 Odat: *{g.get('habit_name','—')}*",
                            parse_mode="Markdown",
                            reply_markup=kb_approve
                        )
                    except Exception as _e: print(f"[warn] xato: {_e}")
        else:
            # Ro'yxatdan o'tmagan — keyin qo'shamiz
            u_check["pending_group"] = g_id
            save_user(uid, u_check)

    is_new = not user_exists(uid)
    u = load_user(uid)

    if u.get("phone"):
        # Allaqachon ro'yxatdan o'tgan
        if not check_subscription(uid):
            send_sub_required(uid)
            return
        send_main_menu(uid)
        return

    # Yangi foydalanuvchi — tilni tekshirish
    if not u.get("lang"):
        kb_lang = lang_keyboard()
        # Yangi foydalanuvchi uchun btn_home yo'q - avval ro'yxatdan o'tish kerak
        sent_lang = bot.send_message(uid, "🌐 Tilni tanlang / Choose language / Выберите язык / Dil seçin:", reply_markup=kb_lang)
        u["lang_msg_id"] = sent_lang.message_id
        save_user(uid, u)
        return

    # Til tanlangan, telefon yo'q — ro'yxatdan o'tish
    u["state"] = "waiting_phone_reg"
    u["name"]  = name
    save_user(uid, u)
    kb_phone = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb_phone.add(KeyboardButton(T(uid, "share_phone"), request_contact=True))
    sent_reg = bot.send_message(uid, T(uid, "ask_phone"), reply_markup=kb_phone)
    u["reg_msg_id"] = sent_reg.message_id
    save_user(uid, u)

# ============================================================
#  CONTACT (telefon raqam)
# ============================================================
@bot.message_handler(content_types=["contact"])
def handle_contact(msg):
    uid = msg.from_user.id
    u   = load_user(uid)
    state = u.get("state")

    # Ma'lumotlarni yangilash — telefon
    if state in ("updating_info", "updating_phone"):
        u["phone"] = msg.contact.phone_number
        u["state"] = None
        info_msg_id = u.pop("info_msg_id", None)
        save_user(uid, u)
        try:
            bot.delete_message(uid, msg.message_id)
        except Exception:
            pass
        if info_msg_id:
            try:
                bot.delete_message(uid, info_msg_id)
            except Exception:
                pass
        sent_ok = bot.send_message(uid, "✅", reply_markup=ReplyKeyboardRemove())
        def back_to_settings(chat_id, ok_mid):
            time.sleep(3)
            try: bot.delete_message(chat_id, ok_mid)
            except: pass
            try:
                u2 = load_user(chat_id)
                kb_set = InlineKeyboardMarkup()
                kb_set.add(InlineKeyboardButton("⚙️ Odat sozlamalari",           callback_data="settings_habits_time"))
                kb_set.add(InlineKeyboardButton(T(chat_id, "btn_change_lang"),    callback_data="settings_lang"))
                kb_set.add(InlineKeyboardButton(T(chat_id, "btn_change_info"),    callback_data="settings_info"))
                kb_set.add(InlineKeyboardButton("💬 Dasturchiga habar",           callback_data="settings_contact_dev"))
                kb_set.add(cBtn(T(chat_id, "btn_home"), "menu_main", "primary"))
                sent = bot.send_message(chat_id, T(chat_id, "settings_title"), parse_mode="Markdown", reply_markup=kb_set)
                u2["main_msg_id"] = sent.message_id
                save_user(chat_id, u2)
            except Exception:
                pass
        threading.Thread(target=back_to_settings, args=(uid, sent_ok.message_id), daemon=True).start()
        return

    u["phone"] = msg.contact.phone_number
    reg_msg_id = u.pop("reg_msg_id", None)
    save_user(uid, u)
    # Oraliq xabarlarni TO'PLASH (yangi kontent ko'rsatilgandan KEYIN o'chiriladi)
    _cleanup_ids = []
    if reg_msg_id:
        _cleanup_ids.append(reg_msg_id)
    _cleanup_ids.append(msg.message_id)
    # Adminga yangi foydalanuvchi haqida xabar — subscription tekshirishdan OLDIN
    try:
        total_users = count_users()
        user_name   = msg.from_user.first_name or "Noma'lum"
        username    = f"@{msg.from_user.username}" if msg.from_user.username else "—"
        bot.send_message(
            ADMIN_ID,
            f"🆕 *Yangi Foydalanuvchi!*\n\n"
            f"Umumiy: *{total_users}*\n"
            f"Ismi: *{user_name}*\n"
            f"Username: {username}\n"
            f"ID: `{uid}`",
            parse_mode="Markdown", reply_markup=ok_kb()
        )
    except Exception:
        pass

    if not check_subscription(uid):
        sent_rm = bot.send_message(uid, "✅", reply_markup=ReplyKeyboardRemove())
        _cleanup_ids.append(sent_rm.message_id)
        send_sub_required(uid)
        # Yangi kontent ko'rsatilgandan KEYIN eski xabarlarni o'chirish
        def _del_batch_sub(cid, ids):
            time.sleep(1)
            for mid in ids:
                try: bot.delete_message(cid, mid)
                except: pass
        threading.Thread(target=_del_batch_sub, args=(uid, _cleanup_ids), daemon=True).start()
        return
    sent_reg = bot.send_message(uid, "✅", reply_markup=ReplyKeyboardRemove())
    _cleanup_ids.append(sent_reg.message_id)
    # Yangi kontent ko'rsatilgandan KEYIN eski xabarlarni o'chirish
    def _del_batch_reg(cid, ids):
        time.sleep(2)
        for mid in ids:
            try: bot.delete_message(cid, mid)
            except: pass
    threading.Thread(target=_del_batch_reg, args=(uid, list(_cleanup_ids)), daemon=True).start()

    # Referal bonus berish
    referrer_id = u.pop("pending_referrer", None)
    if referrer_id and not u.get("ref_used"):
        try:
            u["points"] = u.get("points", 0) + 25
            u["ref_used"] = True
            sent_ref = bot.send_message(uid,
                "🎁 *Do'st taklifi bonusi!*\n\n"
                "*⭐ +25 ball* hisobingizga qo'shildi!",
                parse_mode="Markdown")
            def _del_ref(cid, mid):
                time.sleep(5)
                try: bot.delete_message(cid, mid)
                except: pass
            threading.Thread(target=_del_ref, args=(uid, sent_ref.message_id), daemon=True).start()
        except Exception:
            pass
        try:
            u_ref = load_user(referrer_id)
            u_ref["points"] = u_ref.get("points", 0) + 50
            refs = u_ref.get("referrals", [])
            refs.append(uid)
            u_ref["referrals"] = refs
            milestone_msg = ""
            milestones = {5: "🛡 Streak himoyasi (1 ta) qo'shildi!", 10: "⭐ +100 ball bonus!", 20: "💎 VIP nishon qo'shildi!"}
            if len(refs) in milestones:
                milestone_msg = f"\n\n🏆 *Chegara bonusi:* {milestones[len(refs)]}"
                if len(refs) == 5:
                    u_ref["streak_shields"] = u_ref.get("streak_shields", 0) + 1
                elif len(refs) == 10:
                    u_ref["points"] = u_ref.get("points", 0) + 100
                elif len(refs) == 20:
                    u_ref["is_vip"] = True
            save_user(referrer_id, u_ref)
            bot.send_message(referrer_id,
                f"🎉 *Do'stingiz botga qo'shildi!*\n\n"
                f"*⭐ +50 ball* hisobingizga qo'shildi!\n"
                f"*👥 Jami taklif qilganlar:* {len(refs)} ta"
                + milestone_msg,
                parse_mode="Markdown", reply_markup=ok_kb())
        except Exception:
            pass

    # Pending guruh — ro'yxatdan o'tgach avtomatik qo'shilish
    pending_g = u.pop("pending_group", None)
    if pending_g:
        try:
            g = load_group(pending_g)
            if g and str(uid) not in [str(m) for m in g.get("members", [])]:
                g["members"].append(str(uid))
                save_group(pending_g, g)
                groups = u.get("groups", [])
                if not any(x.get("id") == pending_g for x in groups):
                    groups.append({"id": pending_g, "name": g["name"], "admin_id": g["admin_id"]})
                    u["groups"] = groups
                try:
                    admin_id = g.get("admin_id")
                    if admin_id and str(admin_id) != str(uid):
                        bot.send_message(int(admin_id),
                            f"👋 *{u.get('name','Yangi azo')}* guruhga qo'shildi!\n"
                            f"👥 *{g['name']}*",
                            parse_mode="Markdown"
                        )
                except Exception as _e: print(f"[warn] send_message: {_e}")
                sent_grp = bot.send_message(uid,
                    f"✅ *{g['name']}* guruhiga qo'shildingiz!\n"
                    f"📌 Odat: *{g.get('habit_name','—')}*",
                    parse_mode="Markdown", reply_markup=ok_kb()
                )
                def _del_grp(cid, mid):
                    time.sleep(5)
                    try: bot.delete_message(cid, mid)
                    except: pass
                threading.Thread(target=_del_grp, args=(uid, sent_grp.message_id), daemon=True).start()
        except Exception as e:
            print(f"[pending_group] xato: {e}")

    # Ro'yxatdan o'tdi — asosiy menyuga yo'naltirish
    u["name"]     = msg.from_user.first_name or "Do'stim"
    u["username"]  = (msg.from_user.username or "").lower()
    save_user(uid, u)
    send_main_menu(uid)

