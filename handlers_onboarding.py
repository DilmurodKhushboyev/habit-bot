#!/usr/bin/env python3
"""
Onboarding funksiyalari
"""

import random
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import load_user, save_user
from helpers import T, get_lang, today_uz5
from texts import LANGS
from motivation import MOTIVATSIYA
from bot_setup import (bot, send_main_menu, send_message_colored,
                       main_menu_dict, cBtn, ok_kb, kb_to_dict)


def send_onboarding(uid, name):
    """Yangi foydalanuvchi uchun jonli salomlashuv va birinchi odat yaratish"""
    u = load_user(uid)
    # 1-qadam: Salomlashuv
    text1 = (
        f"🎉 *Xush kelibsiz, {name}!*\n\n"
        f"Men sizga har kuni odatlaringizni bajarishda yordam beraman.\n\n"
        f"*Streak* — ketma-ket bajargan kunlaringiz.\n"
        f"*Ball* — har bajargan odatingiz +5 ball.\n"
        f"*Guruh* — do'stlar bilan birga, odatlar! 😄\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"Birinchi odatingizni *birga* qo'shaylikmi? 👇"
    )
    kb1 = InlineKeyboardMarkup()
    kb1.row(
        InlineKeyboardButton("✅ Ha, boshlaylik!", callback_data="onboard_start"),
        InlineKeyboardButton("⏭ O'tkazib yuborish", callback_data="onboard_skip")
    )
    sent = bot.send_message(uid, text1, parse_mode="Markdown", reply_markup=kb1)
    u["main_msg_id"] = sent.message_id
    u["onboarding"] = True
    save_user(uid, u)

def send_onboarding_habit_category(uid):
    """Onboarding: odat kategoriyasini tanlash"""
    try: bot.delete_message(uid, load_user(uid).get("main_msg_id"))
    except: pass
    text = (
        "🌱 *Qaysi sohadan boshlaysiz?*\n\n"
        "Eng ko'p foyda keltiradigan odatni tanlang:"
    )
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("💪 Sport / Sog'liq", callback_data="onboard_cat_sport"),
        InlineKeyboardButton("📚 O'qish / Bilim",  callback_data="onboard_cat_book")
    )
    kb.row(
        InlineKeyboardButton("🧘 Ruhiy salomatlik", callback_data="onboard_cat_mind"),
        InlineKeyboardButton("💼 Ish / Maqsad",     callback_data="onboard_cat_work")
    )
    kb.row(
        InlineKeyboardButton("✏️ O'zim yozaman",    callback_data="onboard_cat_custom")
    )
    sent = bot.send_message(uid, text, parse_mode="Markdown", reply_markup=kb)
    u = load_user(uid)
    u["main_msg_id"] = sent.message_id
    save_user(uid, u)

# Kategoriyaga tayyor misollar
ONBOARD_EXAMPLES = {
    "sport": [
        ("🏃 Ertalab yugurish — 20 daqiqa", "Ertalab yugurish — 20 daqiqa"),
        ("💪 Sport zali — 30 daqiqa",        "Sport zali — 30 daqiqa"),
        ("🚶 10,000 qadam",                  "10,000 qadam"),
    ],
    "book": [
        ("📖 Kitob o'qish — 20 bet",   "Kitob o'qish — 20 bet"),
        ("🎧 Audio kitob — 30 daqiqa", "Audio kitob — 30 daqiqa"),
        ("📝 Kundalik yozish",         "Kundalik yozish"),
    ],
    "mind": [
        ("🧘 Meditatsiya — 10 daqiqa", "Meditatsiya — 10 daqiqa"),
        ("🙏 Namoz",                   "Namoz"),
        ("😴 Erta uxlash",             "Erta uxlash"),
    ],
    "work": [
        ("🎯 Eng muhim vazifa — 1 ta", "Eng muhim vazifa — 1 ta"),
        ("💻 Dasturlash — 1 soat",     "Dasturlash — 1 soat"),
        ("📋 Reja tuzish",             "Reja tuzish"),
    ],
}

def send_onboarding_examples(uid, cat):
    """Onboarding: tanlangan kategoriya misollari"""
    try: bot.delete_message(uid, load_user(uid).get("main_msg_id"))
    except: pass
    examples = ONBOARD_EXAMPLES.get(cat, [])
    text = "✨ *Mashhur odatlardan birini tanlang yoki o'zingiz yozing:*"
    kb = InlineKeyboardMarkup()
    for label, habit_name in examples:
        kb.add(InlineKeyboardButton(label, callback_data=f"onboard_habit_{habit_name}"))
    kb.add(InlineKeyboardButton("✏️ O'zim yozaman", callback_data="onboard_cat_custom"))
    kb.add(InlineKeyboardButton("⏭ O'tkazib yuborish", callback_data="onboard_skip"))
    sent = bot.send_message(uid, text, parse_mode="Markdown", reply_markup=kb)
    u = load_user(uid)
    u["main_msg_id"] = sent.message_id
    save_user(uid, u)

def send_onboarding_time(uid, habit_name):
    """Onboarding: vaqt tanlash"""
    try: bot.delete_message(uid, load_user(uid).get("main_msg_id"))
    except: pass
    u = load_user(uid)
    u["temp_onboard_habit"] = habit_name
    save_user(uid, u)
    text = (
        f"⏰ *\"{habit_name}\" uchun eslatma vaqtini tanlang:*\n\n"
        f"Qachon eslatma olishni xohlaysiz?"
    )
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("🌅 06:00 — Erta tong",  callback_data="onboard_time_06:00"),
        InlineKeyboardButton("☀️ 08:00 — Ertalab",    callback_data="onboard_time_08:00"),
    )
    kb.row(
        InlineKeyboardButton("🌞 12:00 — Tushlik",    callback_data="onboard_time_12:00"),
        InlineKeyboardButton("🌆 18:00 — Kechqurun",  callback_data="onboard_time_18:00"),
    )
    kb.row(
        InlineKeyboardButton("🌙 21:00 — Kech",       callback_data="onboard_time_21:00"),
        InlineKeyboardButton("🌃 23:00 — Kech kech",  callback_data="onboard_time_23:00"),
    )
    kb.row(
        InlineKeyboardButton("✏️ O'zim kiriting",      callback_data="onboard_time_custom"),
    )
    sent = bot.send_message(uid, text, parse_mode="Markdown", reply_markup=kb)
    u["main_msg_id"] = sent.message_id
    save_user(uid, u)

def finish_onboarding(uid, habit_name, habit_time):
    """Onboarding: odat saqlash va yakunlash"""
    import uuid
    try: bot.delete_message(uid, load_user(uid).get("main_msg_id"))
    except: pass
    u = load_user(uid)
    # Odat yaratamiz
    new_habit = {
        "id":         str(uuid.uuid4())[:8],
        "name":       habit_name,
        "time":       habit_time,
        "type":       "simple",
        "streak":     0,
        "total_done": 0,
        "last_done":  None,
        "created_at": today_uz5(),
    }
    habits = u.get("habits", [])
    habits.append(new_habit)
    u["habits"]     = habits
    u["onboarding"] = False
    u.pop("temp_onboard_habit", None)
    save_user(uid, u)
    # Eslatma o'rnatish
    try:
        from scheduler import schedule_habit
        schedule_habit(uid, new_habit)
    except Exception as _e: print(f"[warn] schedule_habit: {_e}")
    # Tabrik
    text = (
        f"🎊 *Zo'r! Birinchi odatingiz qo'shildi!*\n\n"
        f"📌 *{habit_name}*\n"
        f"⏰ Eslatma: *{habit_time}*\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"Bugun bajarsangiz — *streak boshlanadi* 🔥\n"
        f"7 kun ketma-ket → 🥉 medal\n"
        f"14 kun → 🥈 medal\n"
        f"30 kun → 🥇 medal\n\n"
        f"*Muvaffaqiyatlar!* 💪"
    )
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🏠 Asosiy menyuga", callback_data="menu_main"))
    sent = bot.send_message(uid, text, parse_mode="Markdown", reply_markup=kb)
    u = load_user(uid)
    u["main_msg_id"] = sent.message_id
    save_user(uid, u)

