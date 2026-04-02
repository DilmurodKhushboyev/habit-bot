#!/usr/bin/env python3
"""
2-menyu (guruhlar), obuna tekshirish, admin menyulari
"""

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import load_user, save_user, load_settings
from helpers import T
from bot_setup import (bot, send_message_colored, cBtn)


# ============================================================
#  2-MENYU (GURUHLAR MENYUSI)
# ============================================================
def menu2_dict(uid=None):
    """2-menyu — guruhlar bo'limi, asosiy menyuning ko'zgudagi aksi"""
    rows = []
    rows.append([
        {"text": "👥 Guruh yaratish",   "callback_data": "group_create", "style": "primary"},
        {"text": "🗑 Guruhni o'chirish", "callback_data": "group_delete", "style": "danger"},
    ])
    rows.append([
        {"text": "📊 Guruh statistika", "callback_data": "group_stats",  "style": "primary"},
        {"text": "🏆 Guruh reytingi",   "callback_data": "group_rating", "style": "primary"},
    ])
    rows.append([
        {"text": "🛒 Bozor",             "callback_data": "menu_bozor",     "style": "primary"},
        {"text": "⚙️ Sozlamalar",        "callback_data": "menu_settings",  "style": "primary"},
    ])
    rows.append([
        {"text": "🏠 Asosiy menyu",      "callback_data": "menu_main",      "style": "primary"},
    ])
    return {"inline_keyboard": rows}

def build_menu2_text(uid):
    u      = load_user(uid)
    groups = u.get("groups", [])
    text   = "👥 *Guruhlar menyusi*\n"
    text  += "━" * 16 + "\n"
    if not groups:
        text += "\nHali hech qanday guruhga a'zo emassiz.\n"
        text += "_Yangi guruh yarating yoki mavjudiga qo'shiling!_\n"
    else:
        text += f"\n*Guruhlaringiz:* {len(groups)} ta\n"
        for g in groups:
            member_count = len(g.get("members", []))
            text += f"\n👥 *{g['name']}* — {member_count} a'zo"
    text += "\n" + "━" * 16
    return text

def send_menu2(uid, text=None):
    u = load_user(uid)
    if text is None:
        text = build_menu2_text(uid)
    sent = send_message_colored(uid, text, menu2_dict(uid))
    if sent is None:
        kb = InlineKeyboardMarkup()
        kb.row(
            InlineKeyboardButton("👥 Guruh yaratish",    callback_data="group_create"),
            InlineKeyboardButton("🗑 Guruhni o'chirish", callback_data="group_delete")
        )
        kb.row(
            InlineKeyboardButton("📊 Guruh statistika",  callback_data="group_stats"),
            InlineKeyboardButton("🏆 Guruh reytingi",    callback_data="group_rating")
        )
        kb.add(InlineKeyboardButton("🛒 Bozor",          callback_data="menu_bozor"))
        kb.add(InlineKeyboardButton("🏠 1-menyu",        callback_data="menu_main"))
        sent = bot.send_message(uid, text, parse_mode="Markdown", reply_markup=kb)
    u["main_msg_id"] = sent.message_id
    ids = u.get("start_msg_ids", [])
    ids.append(sent.message_id)
    u["start_msg_ids"] = ids
    save_user(uid, u)


def check_subscription(user_id):
    settings = load_settings()
    channels = []
    for i in range(1, 4):
        ch = settings.get(f"required_channel_{i}", None)
        if ch:
            channels.append(ch)
    # Eski bitta kanal format bilan ham moslik
    old_ch = settings.get("required_channel", None)
    if old_ch and old_ch not in channels:
        channels.append(old_ch)
    if not channels:
        return True
    for channel in channels:
        try:
            member = bot.get_chat_member(channel, user_id)
            if member.status not in ("member", "administrator", "creator"):
                return False
        except Exception as e:
            print(f"[check_subscription] {channel} tekshirishda xato: {e}")
            return False
    return True

def send_sub_required(uid):
    u        = load_user(uid)
    settings = load_settings()
    channels = []
    for i in range(1, 4):
        ch    = settings.get(f"required_channel_{i}", None)
        title = settings.get(f"required_channel_title_{i}", ch)
        if ch:
            channels.append((ch, title))
    old_ch    = settings.get("required_channel", None)
    old_title = settings.get("required_channel_title", old_ch)
    if old_ch and old_ch not in [c[0] for c in channels]:
        channels.append((old_ch, old_title))
    kb = InlineKeyboardMarkup()
    for ch, title in channels:
        label = title if title else ch
        kb.add(InlineKeyboardButton(f"📢 {label}", url=f"https://t.me/{ch.lstrip('@')}"))
    kb.add(InlineKeyboardButton(T(uid, "btn_joined"), callback_data="check_sub"))
    old_msg_id = u.get("sub_msg_id")
    if old_msg_id:
        try:
            bot.delete_message(uid, old_msg_id)
        except Exception:
            pass
    sent = bot.send_message(uid, T(uid, "sub_required"), reply_markup=kb)
    u["sub_msg_id"] = sent.message_id
    save_user(uid, u)

def admin_menu():
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("📢 Habar yuborish",   callback_data="admin_broadcast"),
        InlineKeyboardButton("👥 Foydalanuvchilar", callback_data="admin_users")
    )
    kb.row(
        InlineKeyboardButton("🔗 Majburiy kanal", callback_data="admin_channel"),
        InlineKeyboardButton("📈 Statistika",     callback_data="admin_stats")
    )
    kb.row(
        InlineKeyboardButton("🎁 Ball berish",        callback_data="admin_give_points"),
        InlineKeyboardButton("🆕 Bot yangilandi xabari", callback_data="admin_notify_update")
    )
    kb.add(InlineKeyboardButton("🧪 Onboarding testlash", callback_data="admin_test_onboard"))
    kb.add(cBtn("🏠 Asosiy menyu", "admin_close", "primary"))
    return kb

def admin_broadcast_menu():
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("👤 Shaxsiy chatlar", callback_data="admin_bc_private"),
        InlineKeyboardButton("👥 Guruhlar",         callback_data="admin_bc_groups")
    )
    kb.add(InlineKeyboardButton("📣 Umumiy (hammasi)", callback_data="admin_bc_all"))
    kb.add(cBtn("❌ Bekor qilish", "admin_cancel", "danger"))
    return kb

def admin_stats_period_menu():
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("1 kun",   callback_data="admin_stats_1"),
        InlineKeyboardButton("1 hafta", callback_data="admin_stats_7"),
        InlineKeyboardButton("1 oy",    callback_data="admin_stats_30")
    )
    kb.row(
        InlineKeyboardButton("1 yil",  callback_data="admin_stats_365"),
        InlineKeyboardButton("Umumiy", callback_data="admin_stats_all")
    )
    kb.add(cBtn("❌ Bekor qilish", "admin_cancel", "danger"))
    return kb
