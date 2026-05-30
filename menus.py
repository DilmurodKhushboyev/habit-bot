#!/usr/bin/env python3
"""
Obuna tekshirish, admin menyulari
"""

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import load_user, save_user, load_settings
from helpers import T
from bot_setup import (bot, cBtn)


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
