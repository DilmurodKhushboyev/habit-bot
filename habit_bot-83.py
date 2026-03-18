#!/usr/bin/env python3
"""
Odatlar Shakllantirish Boti
============================
O'rnatish:
    pip install pyTelegramBotAPI schedule pymongo

Ishga tushurish:
    python habit_bot.py
"""

import telebot
import os
import requests
import json
import schedule
import time
import threading
import random
import io
from datetime import datetime, date
from PIL import Image, ImageDraw, ImageFont
from telebot.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from pymongo import MongoClient

# ============================================================
#  SOZLAMALAR
# ============================================================
BOT_TOKEN        = os.environ.get("BOT_TOKEN", "SHU_YERGA_TOKEN_QOYING")
ADMIN_ID         = int(os.environ.get("ADMIN_ID", 5071908808))
MONGO_URI        = os.environ.get("MONGO_URI", "mongodb+srv://habitbot:Habit2026@cluster0.i0jux9m.mongodb.net/?appName=Cluster0")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# ============================================================
#  MONGODB ULANISH
# ============================================================
mongo_client  = MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=3000,
    connectTimeoutMS=3000,
    socketTimeoutMS=5000,
    retryWrites=True,
    retryReads=True,
)
mongo_db      = mongo_client["habit_bot"]
mongo_col     = mongo_db["users"]
groups_col    = mongo_db["groups"]   # Guruhlar kolleksiyasi

# ── MongoDB indekslar (bot ishga tushganda bir marta) ──
try:
    from pymongo import ASCENDING, DESCENDING
    mongo_col.create_index([("points", DESCENDING)],  name="idx_points",  background=True)
    mongo_col.create_index([("streak", DESCENDING)],  name="idx_streak",  background=True)
    mongo_col.create_index([("name",   ASCENDING)],   name="idx_name",    background=True)
    groups_col.create_index([("members", ASCENDING)], name="idx_members", background=True)
except Exception as _e:
    print(f"[warn] MongoDB indeks yaratishda xato: {_e}")

# ============================================================
#  MA'LUMOTLAR BAZASI FUNKSIYALARI
# ============================================================
def load_user(user_id):
    uid = str(user_id)
    for _attempt in range(3):
        try:
            doc = mongo_col.find_one({"_id": uid})
            if doc:
                return {k: v for k, v in doc.items() if k != "_id"}
            return {"habits": [], "state": None, "joined_at": str(date.today())}
        except Exception as _e:
            if _attempt < 2:
                import time as _t; _t.sleep(0.5)
            else:
                print(f"[load_user] xato ({uid}): {_e}")
                return {"habits": [], "state": None, "joined_at": str(date.today())}

def save_user(user_id, udata):
    for _attempt in range(3):
        try:
            mongo_col.update_one(
                {"_id": str(user_id)},
                {"$set": udata},
                upsert=True
            )
            invalidate_users_cache()
            return
        except Exception as _e:
            if _attempt < 2:
                import time as _t; _t.sleep(0.5)
            else:
                print(f"[save_user] xato ({user_id}): {_e}")

def load_settings():
    doc = mongo_col.find_one({"_id": "_settings"})
    if doc:
        return {k: v for k, v in doc.items() if k != "_id"}
    return {}

def save_settings(settings):
    mongo_col.update_one(
        {"_id": "_settings"},
        {"$set": settings},
        upsert=True
    )

# ── load_all_users cache (TTL: 60 soniya) ──
import time as _cache_time
_all_users_cache      = None
_all_users_cache_time = 0.0
_ALL_USERS_TTL        = 60

def invalidate_users_cache():
    global _all_users_cache, _all_users_cache_time
    _all_users_cache      = None
    _all_users_cache_time = 0.0

def load_all_users(force=False):
    global _all_users_cache, _all_users_cache_time
    now = _cache_time.time()
    if not force and _all_users_cache is not None and (now - _all_users_cache_time) < _ALL_USERS_TTL:
        return _all_users_cache
    users = {}
    for doc in mongo_col.find({"_id": {"$not": {"$regex": "^_"}}}):
        uid = doc["_id"]
        users[uid] = {k: v for k, v in doc.items() if k != "_id"}
    _all_users_cache      = users
    _all_users_cache_time = now
    return users

def user_exists(user_id):
    return mongo_col.find_one({"_id": str(user_id)}) is not None

def count_users():
    return mongo_col.count_documents({"_id": {"$not": {"$regex": "^_"}}})

def load_group(group_id):
    doc = groups_col.find_one({"_id": str(group_id)})
    if doc:
        return {k: v for k, v in doc.items() if k != "_id"}
    return None

def save_group(group_id, gdata):
    groups_col.update_one(
        {"_id": str(group_id)},
        {"$set": gdata},
        upsert=True
    )

def delete_group(group_id):
    groups_col.delete_one({"_id": str(group_id)})

# ============================================================
#  KO'P TIL
# ============================================================
LANGS = {
    "uz": {
        "choose_lang":       "🌐 Tilni tanlang:",
        "lang_set":          "✅ Til o'zgartirildi!",
        "welcome_new":       "👋 Salom, *{name}*!\n\n🌱 *Odatlar Shakllantirish Boti*ga xush kelibsiz!\n\nBu bot sizga:\n• Odatlarni belgilash\n• Vaqtida eslatma olish\n• Streak va statistika kuzatish\nimkonini beradi.\n\nBoshlash uchun *➕ Odat qo'shish* tugmasini bosing!",
        "welcome_back":      "📊 *ODATLARINGIZ:*",
        "btn_add":           "➕ Odat qo'shish",
        "btn_delete":        "🗑 Odatni o'chirish",
        "btn_stats":         "📊 Statistika",
        "btn_rating":        "🏆 Reyting",
        "btn_home":          "🏠 Asosiy menyu",
        "btn_cancel":        "❌ Bekor qilish",
        "btn_yes":           "Ha ✅",
        "btn_no":            "Yo'q ❌",
        "ask_habit_name":    "📝 Odatning nomini yozing:\n\n_Masalan: Kitob o'qish, Sport, Suv ichish..._",
        "ask_habit_time":    "*✅ Odat:* {name}\n\n*⏰ Eslatma vaqtini yozing* (24 soat):\n\n_Masalan: 07:30 yoki 21:00_",
        "habit_added":       "🎉 *{name}* odati qo'shildi!\n\n*⏰ Eslatma:* {time} da keladi\n*🔥 Streak:* 0 kun\n\nHar kuni vaqtida bajaring!",
        "wrong_time":        "❌ Noto'g'ri format. HH:MM formatida yozing.\n_Masalan: 08:00_",
        "no_habits":         "📭 Hali odat qo'shilmagan.\n\n➕ Odat qo'shish tugmasini bosing!",
        "no_stats":          "📭 Hali odat yo'q.",
        "confirm_delete":    "⚠️ Haqiqatan ham *{name}* odatini o'chirishni xohlaysizmi?",
        "deleted":           "🗑 *{name}* o'chirildi.",
        "no_delete":         "📭 O'chirish uchun odat yo'q.",
        "done_today":        "✅ Bugun allaqachon bajardingiz!",
        "done_ok":           "*✅ {name}* — bajarildi!",
        "undone":            "*❌ {name}* — bekor qilindi!",
        "all_done":          "Bugungi barcha odatni bajardingiz, tabriklaymiz 🎉",
        "limit":             "⚠️ Odatlarni yaratish me'yori 15 ta!",
        "remind_title":      "⏰ *Eslatma!*\n\n*🎯 Odat:* {name}\n\n{motiv}",
        "btn_done":          "✅ Bajardim!",
        "btn_skip":          "❌ Bajarmadim",
        "stats_title":       "*📊 Statistika —* {page}/{total} sahifa",
        "stats_ball":        "*⭐ Jami ball:* {ball} ball",
        "stats_rank":        "*🎖 Daraja:* {rank}",
        "stats_streak":      "*🔥 Streak:* {streak} kun",
        "stats_time":        "*⏰ Vaqt:* {time}",
        "stats_ball2":       "⭐ Odat balli: {ball} ball",
        "stats_done":        "*✅ Jami bajarilgan:* {n} marta",
        "stats_missed":      "*❌ Jami bajarilmagan:* {n} marta",
        "stats_last":        "*📅 Oxirgi:* {d}",
        "rating_title":      "🏆 Top 10 Reyiting",
        "rating_empty":      "Hali hech kim ball to'plamagan.",
        "sub_required":      "⚠️ Botdan foydalanish uchun avvalo kanalga a'zo bo'ling!",
        "btn_join":          "📢 Kanalga o'tish",
        "btn_joined":        "✅ A'zo bo'ldim",
        "invalid_msg":       "⚠️ Sizning noaniq habarlaringiz qo'llab quvvatlanmaydi.",
        "nav_prev":          "⬅️ {n}-sahifa",
        "nav_next":          "{n}-sahifa ➡️",
        "ranks":             ["🌱 Yangi boshlovchi","🥉 Boshlang'ich","🥈 Tajribali","🥇 Professional","💎 Master","🏆 Legenda"],
        "btn_settings":      "⚙️ Sozlamalar",
        "settings_title":    "⚙️ *Muhim sozlamalar qismi.*",
        "btn_change_lang":   "🌐 Tilni o'zgartirish",
        "btn_change_info":   "📝 Ma'lumotlarni o'zgartirish",
        "change_info_text":  "📝 *Ma'lumotlarni o'zgartirish*\n\nNimani o'zgartirmoqchisiz?",
        "rating_no_link":    "username yo'q",
        "hint_toggle":       "Tugmalarni bosish orqali ham odatni tasdiqlashingiz mumkin!",
        "done_percent":      "*Bajarildi:* {p}%",
        "share_phone":       "📱 Telefon raqamni yuborish",
        "ask_phone":         "📱 Telefon raqamingizni yuboring yoki qo'lda kiriting:\n\n_Masalan: +998901234567_",
        "err_wrong_phone":   "⚠️ Noto'g'ri raqam. Masalan: *+998901234567*",
        "err_wrong_count":   "⚠️ Noto'g'ri son. 1 dan 20 gacha raqam kiriting:",
        "err_time_format":   "⚠️ Noto'g'ri format. Masalan: *HH:MM*",
        "err_time_value":    "⚠️ Noto'g'ri vaqt. Masalan: *HH:MM*",
        "err_min_chars":     "⚠️ Kamida 2 harf kiriting!",
        "err_positive_num":  "⚠️ Musbat son kiriting!",
        "err_only_digits":   "⚠️ Faqat raqam kiriting!",
        "err_enter_number":  "⚠️ Son kiriting. Masalan: 100 yoki -50",
        "err_user_not_found":"⚠️ Bu ID foydalanuvchi topilmadi.",
        "err_self_transfer": "⚠️ O'zingizga ball yubora olmaysiz!",
        "err_not_enough_pts":"⚠️ Sizda faqat *{points} ball* bor!",
        "err_max_groups":    "⚠️ Siz admin sifatida 3 tadan ko'p guruh yarata olmaysiz.",
        "set_dev_prompt":    "💬 *Dasturchiga habar yozing:*\n\nHabaringizni quyida kiriting:",
        "set_habit_settings":"⚙️ *Odat sozlamalari*",
        "set_all_notime":    "🔕 Barcha odatlar vaqtsiz holatga o'tkazildi!",
        "set_which_time":    "⏰ *Qaysi odatning vaqtini tahrirlash?*",
        "set_habit_notime":  "🔕 Odat vaqtsiz holatga o'tkazildi!",
        "set_edit_times":    "⏰ *Odatlar vaqtini tahrirlash*",
        "set_which_rename":  "✏️ *Qaysi odatning nomini o'zgartirmoqchisiz?*",
        "set_new_name":      "✏️ Yangi ismingizni yozing:",
        "set_all_time_ask":  "⏰ Barcha odatlar uchun umumiy vaqtni kiriting:\n\n_Masalan: 07:00_",
        "ok_time_updated":   "✅ Vaqt yangilandi!",
        "ok_all_times":      "✅ Barcha odatlar vaqti *{time}* ga o'zgartirildi!",
        "ok_name_changed":   "✅ Ism *{name}* ga o'zgartirildi!",
        "ok_habit_renamed":  "✅ Odat nomi *{name}* ga o'zgartirildi!",
        "ok_dev_sent":       "✅ Xabaringiz dasturchiga yuborildi!",
        "ok_transfer":       "✅ *{amount} ball* muvaffaqiyatli yuborildi!\n\n⭐ Qolgan ballingiz: {points}",
        "ok_points_reset":   "✅ Ballaringiz *0 ga* tushirildi.",
        "del_which_habit":   "🗑 *Qaysi odatni o'chirmoqchisiz?*",
        "add_more_habits":   "➕ *Yana odat qo'shing:*",
        "ok_self_deduct":    "✅ *{amount} ball* ayirib tashlandi.\n\n⭐ Qolgan ballingiz: {points}",
        "admin_gave_pts":    "🎁 Admin sizga *{amount} ball* berdi!\n\n⭐ Hisobingiz: {points} ball",
        "admin_reply":       "↩️ *Admin javobi:*\n\n{text}",
    },
    "en": {
        "choose_lang":       "🌐 Choose language:",
        "lang_set":          "✅ Language changed!",
        "welcome_new":       "👋 Hello, *{name}*!\n\n🌱 Welcome to *Habit Tracker Bot*!\n\nThis bot helps you:\n• Set habits\n• Get timely reminders\n• Track streaks & stats\n\nPress *➕ Add Habit* to start!",
        "welcome_back":      "📊 *YOUR HABITS:*",
        "btn_add":           "➕ Add Habit",
        "btn_delete":        "🗑 Delete Habit",
        "btn_stats":         "📊 Statistics",
        "btn_rating":        "🏆 Leaderboard",
        "btn_home":          "🏠 Main Menu",
        "btn_cancel":        "❌ Cancel",
        "btn_yes":           "Yes ✅",
        "btn_no":            "No ❌",
        "ask_habit_name":    "📝 Enter habit name:\n\n_Example: Reading, Exercise, Drink water..._",
        "ask_habit_time":    "*✅ Habit:* {name}\n\n*⏰ Enter reminder time* (24h):\n\n_Example: 07:30 or 21:00_",
        "habit_added":       "🎉 Habit *{name}* added!\n\n*⏰ Reminder:* {time}\n*🔥 Streak:* 0 days\n\nComplete it daily!",
        "wrong_time":        "❌ Wrong format. Use HH:MM.\n_Example: 08:00_",
        "no_habits":         "📭 No habits yet.\n\nPress ➕ Add Habit!",
        "no_stats":          "📭 No habits yet.",
        "confirm_delete":    "⚠️ Really delete *{name}*?",
        "deleted":           "🗑 *{name}* deleted.",
        "no_delete":         "📭 No habits to delete.",
        "done_today":        "✅ Already done today!",
        "done_ok":           "*✅ {name}* — done!",
        "undone":            "*❌ {name}* — undone!",
        "all_done":          "You completed all today's habits, congratulations 🎉",
        "limit":             "⚠️ Maximum 15 habits allowed!",
        "remind_title":      "⏰ *Reminder!*\n\n*🎯 Habit:* {name}\n\n{motiv}",
        "btn_done":          "✅ Done!",
        "btn_skip":          "❌ Not done",
        "stats_title":       "*📊 Statistics —* page {page}/{total}",
        "stats_ball":        "⭐ *Total points: {ball}*",
        "stats_rank":        "🎖 Rank: {rank}",
        "stats_streak":      "🔥 Streak: {streak} days",
        "stats_time":        "⏰ Time: {time}",
        "stats_ball2":       "⭐ Habit points: {ball}",
        "stats_done":        "✅ Total done: {n} times",
        "stats_missed":      "❌ Total missed: {n} times",
        "stats_last":        "📅 Last: {d}",
        "rating_title":      "🏆 Top 10 Leaderboard",
        "rating_empty":      "Nobody has points yet.",
        "sub_required":      "⚠️ Please join the channel to use the bot!",
        "btn_join":          "📢 Join Channel",
        "btn_joined":        "✅ I joined",
        "invalid_msg":       "⚠️ Unknown message, not supported.",
        "nav_prev":          "⬅️ Page {n}",
        "nav_next":          "Page {n} ➡️",
        "ranks":             ["🌱 Beginner","🥉 Novice","🥈 Experienced","🥇 Professional","💎 Master","🏆 Legend"],
        "btn_settings":      "⚙️ Settings",
        "settings_title":    "⚙️ *Settings*",
        "btn_change_lang":   "🌐 Change Language",
        "btn_change_info":   "📝 Change Profile",
        "change_info_text":  "📝 *Change Profile*\n\nWhat would you like to change?",
        "rating_no_link":    "no username",
        "hint_toggle":       "You can also confirm habits by pressing the buttons!",
        "done_percent":      "*Done:* {p}%",
        "share_phone":       "📱 Share phone number",
        "ask_phone":         "📱 Share your phone number or type it manually:\n\n_Example: +998901234567_",
        "err_wrong_phone":   "⚠️ Wrong number. Example: *+998901234567*",
        "err_wrong_count":   "⚠️ Wrong number. Enter 1 to 20:",
        "err_time_format":   "⚠️ Wrong format. Example: *HH:MM*",
        "err_time_value":    "⚠️ Wrong time. Example: *HH:MM*",
        "err_min_chars":     "⚠️ Enter at least 2 characters!",
        "err_positive_num":  "⚠️ Enter a positive number!",
        "err_only_digits":   "⚠️ Enter digits only!",
        "err_enter_number":  "⚠️ Enter a number. Example: 100 or -50",
        "err_user_not_found":"⚠️ User with this ID not found.",
        "err_self_transfer": "⚠️ You cannot send points to yourself!",
        "err_not_enough_pts":"⚠️ You only have *{points} points*!",
        "err_max_groups":    "⚠️ You can create a maximum of 3 groups as admin.",
        "set_dev_prompt":    "💬 *Write to the developer:*\n\nType your message below:",
        "set_habit_settings":"⚙️ *Habit settings*",
        "set_all_notime":    "🔕 All habits set to no-time mode!",
        "set_which_time":    "⏰ *Which habit time to edit?*",
        "set_habit_notime":  "🔕 Habit set to no-time mode!",
        "set_edit_times":    "⏰ *Edit habit times*",
        "set_which_rename":  "✏️ *Which habit to rename?*",
        "set_new_name":      "✏️ Enter your new name:",
        "set_all_time_ask":  "⏰ Enter a common time for all habits:\n\n_Example: 07:00_",
        "ok_time_updated":   "✅ Time updated!",
        "ok_all_times":      "✅ All habits time changed to *{time}*!",
        "ok_name_changed":   "✅ Name changed to *{name}*!",
        "ok_habit_renamed":  "✅ Habit renamed to *{name}*!",
        "ok_dev_sent":       "✅ Your message was sent to the developer!",
        "ok_transfer":       "✅ *{amount} points* sent successfully!\n\n⭐ Remaining: {points}",
        "ok_points_reset":   "✅ Your points have been reset to *0*.",
        "del_which_habit":   "🗑 *Which habit to delete?*",
        "add_more_habits":   "➕ *Add another habit:*",
        "ok_self_deduct":    "✅ *{amount} points* deducted.\n\n⭐ Remaining: {points}",
        "admin_gave_pts":    "🎁 Admin gave you *{amount} points*!\n\n⭐ Balance: {points} points",
        "admin_reply":       "↩️ *Admin reply:*\n\n{text}",
    },
    "ru": {
        "choose_lang":       "🌐 Выберите язык:",
        "lang_set":          "✅ Язык изменён!",
        "welcome_new":       "👋 Привет, *{name}*!\n\n🌱 Добро пожаловать в *Бот трекер привычек*!\n\nЭтот бот поможет вам:\n• Отслеживать привычки\n• Получать напоминания\n• Вести статистику\n\nНажмите *➕ Добавить привычку*!",
        "welcome_back":      "📊 *ВАШИ ПРИВЫЧКИ:*",
        "btn_add":           "➕ Добавить",
        "btn_delete":        "🗑 Удалить",
        "btn_stats":         "📊 Статистика",
        "btn_rating":        "🏆 Рейтинг",
        "btn_home":          "🏠 Главное меню",
        "btn_cancel":        "❌ Отмена",
        "btn_yes":           "Да ✅",
        "btn_no":            "Нет ❌",
        "ask_habit_name":    "📝 Введите название привычки:\n\n_Пример: Чтение, Спорт, Вода..._",
        "ask_habit_time":    "*✅ Привычка:* {name}\n\n*⏰ Введите время* (24ч):\n\n_Пример: 07:30 или 21:00_",
        "habit_added":       "🎉 Привычка *{name}* добавлена!\n\n*⏰ Напоминание:* {time}\n*🔥 Серия:* 0 дней\n\nВыполняйте каждый день!",
        "wrong_time":        "❌ Неверный формат. Используйте ЧЧ:ММ.\n_Пример: 08:00_",
        "no_habits":         "📭 Привычек пока нет.\n\nНажмите ➕ Добавить!",
        "no_stats":          "📭 Привычек пока нет.",
        "confirm_delete":    "⚠️ Удалить привычку *{name}*?",
        "deleted":           "🗑 *{name}* удалена.",
        "no_delete":         "📭 Нет привычек для удаления.",
        "done_today":        "✅ Уже выполнено сегодня!",
        "done_ok":           "*✅ {name}* — выполнено!",
        "undone":            "*❌ {name}* — отменено!",
        "all_done":          "Вы выполнили все привычки сегодня, поздравляем 🎉",
        "limit":             "⚠️ Максимум 15 привычек!",
        "remind_title":      "⏰ *Напоминание!*\n\n*🎯 Привычка:* {name}\n\n{motiv}",
        "btn_done":          "✅ Выполнено!",
        "btn_skip":          "❌ Не выполнено",
        "stats_title":       "📊 *Статистика* — стр. {page}/{total}",
        "stats_ball":        "⭐ *Всего очков: {ball}*",
        "stats_rank":        "🎖 Уровень: {rank}",
        "stats_streak":      "🔥 Серия: {streak} дней",
        "stats_time":        "⏰ Время: {time}",
        "stats_ball2":       "⭐ Очки за привычку: {ball}",
        "stats_done":        "✅ Всего выполнено: {n} раз",
        "stats_missed":      "❌ Всего пропущено: {n} раз",
        "stats_last":        "📅 Последнее: {d}",
        "rating_title":      "🏆 Топ 10",
        "rating_empty":      "Никто ещё не набрал очков.",
        "sub_required":      "⚠️ Подпишитесь на канал, чтобы использовать бота!",
        "btn_join":          "📢 Перейти на канал",
        "btn_joined":        "✅ Я подписался",
        "invalid_msg":       "⚠️ Неизвестное сообщение, не поддерживается.",
        "nav_prev":          "⬅️ Стр. {n}",
        "nav_next":          "Стр. {n} ➡️",
        "ranks":             ["🌱 Новичок","🥉 Начинающий","🥈 Опытный","🥇 Профессионал","💎 Мастер","🏆 Легенда"],
        "btn_settings":      "⚙️ Настройки",
        "settings_title":    "⚙️ *Настройки*",
        "btn_change_lang":   "🌐 Изменить язык",
        "btn_change_info":   "📝 Изменить профиль",
        "change_info_text":  "📝 *Изменить профиль*\n\nЧто хотите изменить?",
        "rating_no_link":    "нет username",
        "hint_toggle":       "Вы также можете подтверждать привычки нажатием кнопок!",
        "done_percent":      "*Выполнено:* {p}%",
        "share_phone":       "📱 Отправить номер телефона",
        "ask_phone":         "📱 Отправьте номер телефона или введите вручную:\n\n_Пример: +998901234567_",
        "err_wrong_phone":   "⚠️ Неверный номер. Пример: *+998901234567*",
        "err_wrong_count":   "⚠️ Неверное число. Введите от 1 до 20:",
        "err_time_format":   "⚠️ Неверный формат. Пример: *ЧЧ:ММ*",
        "err_time_value":    "⚠️ Неверное время. Пример: *ЧЧ:ММ*",
        "err_min_chars":     "⚠️ Введите минимум 2 символа!",
        "err_positive_num":  "⚠️ Введите положительное число!",
        "err_only_digits":   "⚠️ Введите только цифры!",
        "err_enter_number":  "⚠️ Введите число. Пример: 100 или -50",
        "err_user_not_found":"⚠️ Пользователь с таким ID не найден.",
        "err_self_transfer": "⚠️ Нельзя отправить баллы самому себе!",
        "err_not_enough_pts":"⚠️ У вас только *{points} баллов*!",
        "err_max_groups":    "⚠️ Как админ вы можете создать максимум 3 группы.",
        "set_dev_prompt":    "💬 *Напишите разработчику:*\n\nВведите сообщение ниже:",
        "set_habit_settings":"⚙️ *Настройки привычек*",
        "set_all_notime":    "🔕 Все привычки переведены в режим без времени!",
        "set_which_time":    "⏰ *Время какой привычки изменить?*",
        "set_habit_notime":  "🔕 Привычка переведена в режим без времени!",
        "set_edit_times":    "⏰ *Редактировать время привычек*",
        "set_which_rename":  "✏️ *Какую привычку переименовать?*",
        "set_new_name":      "✏️ Введите новое имя:",
        "set_all_time_ask":  "⏰ Введите общее время для всех привычек:\n\n_Пример: 07:00_",
        "ok_time_updated":   "✅ Время обновлено!",
        "ok_all_times":      "✅ Время всех привычек изменено на *{time}*!",
        "ok_name_changed":   "✅ Имя изменено на *{name}*!",
        "ok_habit_renamed":  "✅ Привычка переименована в *{name}*!",
        "ok_dev_sent":       "✅ Сообщение отправлено разработчику!",
        "ok_transfer":       "✅ *{amount} баллов* успешно отправлено!\n\n⭐ Остаток: {points}",
        "ok_points_reset":   "✅ Ваши баллы сброшены до *0*.",
        "del_which_habit":   "🗑 *Какую привычку удалить?*",
        "add_more_habits":   "➕ *Добавьте ещё привычку:*",
        "ok_self_deduct":    "✅ *{amount} баллов* списано.\n\n⭐ Остаток: {points}",
        "admin_gave_pts":    "🎁 Админ начислил вам *{amount} баллов*!\n\n⭐ Баланс: {points} баллов",
        "admin_reply":       "↩️ *Ответ админа:*\n\n{text}",
    },
    "tr": {
        "choose_lang":       "🌐 Dil seçin:",
        "lang_set":          "✅ Dil değiştirildi!",
        "welcome_new":       "👋 Merhaba, *{name}*!\n\n🌱 *Alışkanlık Takip Botu*'na hoş geldiniz!\n\nBu bot size:\n• Alışkanlık belirleme\n• Zamanında hatırlatma\n• İstatistik takibi\nimkanı verir.\n\n*➕ Alışkanlık Ekle*'ye basın!",
        "welcome_back":      "📊 *ALISKANLIKLARINIZ:*",
        "btn_add":           "➕ Alışkanlık Ekle",
        "btn_delete":        "🗑 Sil",
        "btn_stats":         "📊 İstatistik",
        "btn_rating":        "🏆 Sıralama",
        "btn_home":          "🏠 Ana Menü",
        "btn_cancel":        "❌ İptal",
        "btn_yes":           "Evet ✅",
        "btn_no":            "Hayır ❌",
        "ask_habit_name":    "📝 Alışkanlık adını yazın:\n\n_Örnek: Kitap okuma, Spor, Su içme..._",
        "ask_habit_time":    "*✅ Alışkanlık:* {name}\n\n*⏰ Hatırlatma saatini girin* (24 saat):\n\n_Örnek: 07:30 veya 21:00_",
        "habit_added":       "🎉 *{name}* alışkanlığı eklendi!\n\n⏰ Hatırlatma: *{time}*\n🔥 Seri: 0 gün\n\nHer gün yapın!",
        "wrong_time":        "❌ Yanlış format. SS:DD formatında girin.\n_Örnek: 08:00_",
        "no_habits":         "📭 Henüz alışkanlık yok.\n\n➕ Ekle butonuna basın!",
        "no_stats":          "📭 Henüz alışkanlık yok.",
        "confirm_delete":    "⚠️ *{name}* alışkanlığını silmek istiyor musunuz?",
        "deleted":           "🗑 *{name}* silindi.",
        "no_delete":         "📭 Silinecek alışkanlık yok.",
        "done_today":        "✅ Bugün zaten yapıldı!",
        "done_ok":           "*✅ {name}* — yapıldı!",
        "undone":            "*❌ {name}* — geri alındı!",
        "all_done":          "Bugünkü tüm alışkanlıkları tamamladınız, tebrikler 🎉",
        "limit":             "⚠️ Maksimum 15 alışkanlık!",
        "remind_title":      "⏰ *Hatırlatma!*\n\n*🎯 Alışkanlık:* {name}\n\n{motiv}",
        "btn_done":          "✅ Yaptım!",
        "btn_skip":          "❌ Yapmadım",
        "stats_title":       "📊 *İstatistik* — {page}/{total}. sayfa",
        "stats_ball":        "⭐ *Toplam puan: {ball}*",
        "stats_rank":        "🎖 Seviye: {rank}",
        "stats_streak":      "🔥 Seri: {streak} gün",
        "stats_time":        "⏰ Saat: {time}",
        "stats_ball2":       "⭐ Alışkanlık puanı: {ball}",
        "stats_done":        "✅ Toplam yapılan: {n} kez",
        "stats_missed":      "❌ Toplam kaçırılan: {n} kez",
        "stats_last":        "📅 Son: {d}",
        "rating_title":      "🏆 İlk 10",
        "rating_empty":      "Henüz kimse puan kazanmadı.",
        "sub_required":      "⚠️ Botu kullanmak için kanala katılın!",
        "btn_join":          "📢 Kanala Git",
        "btn_joined":        "✅ Katıldım",
        "invalid_msg":       "⚠️ Bilinmeyen mesaj, desteklenmiyor.",
        "nav_prev":          "⬅️ {n}. sayfa",
        "nav_next":          "{n}. sayfa ➡️",
        "ranks":             ["🌱 Başlangıç","🥉 Acemi","🥈 Deneyimli","🥇 Profesyonel","💎 Usta","🏆 Efsane"],
        "btn_settings":      "⚙️ Ayarlar",
        "settings_title":    "⚙️ *Ayarlar*",
        "btn_change_lang":   "🌐 Dil Değiştir",
        "btn_change_info":   "📝 Profili Düzenle",
        "change_info_text":  "📝 *Profili Düzenle*\n\nNeyi değiştirmek istersiniz?",
        "rating_no_link":    "username yok",
        "hint_toggle":       "Butonlara basarak da alışkanlıkları onaylayabilirsiniz!",
        "done_percent":      "*Tamamlandı:* {p}%",
        "share_phone":       "📱 Telefon numarasını paylaş",
        "ask_phone":         "📱 Telefon numaranızı gönderin veya elle girin:\n\n_Örnek: +998901234567_",
    },
    "kk": {
        "choose_lang":       "🌐 Тілді таңдаңыз:",
        "lang_set":          "✅ Тіл өзгертілді!",
        "welcome_new":       "👋 Сәлем, *{name}*!\n\n🌱 *Дағды бақылау ботына* қош келдіңіз!\n\nБот сізге:\n• Дағдыларды белгілеу\n• Уақтылы еске салу\n• Статистика жүргізу\nмүмкіндігін береді.\n\n*➕ Дағды қосу* түймесін басыңыз!",
        "welcome_back":      "📊 *ДАҒДЫЛАРЫҢЫЗ:*",
        "btn_add":           "➕ Дағды қосу",
        "btn_delete":        "🗑 Жою",
        "btn_stats":         "📊 Статистика",
        "btn_rating":        "🏆 Рейтинг",
        "btn_home":          "🏠 Басты мәзір",
        "btn_cancel":        "❌ Болдырмау",
        "btn_yes":           "Иә ✅",
        "btn_no":            "Жоқ ❌",
        "ask_habit_name":    "📝 Дағды атауын жазыңыз:\n\n_Мысалы: Кітап оқу, Спорт, Су ішу..._",
        "ask_habit_time":    "*✅ Дағды:* {name}\n\n*⏰ Еске салу уақытын енгізіңіз* (24 сағ):\n\n_Мысалы: 07:30 немесе 21:00_",
        "habit_added":       "🎉 *{name}* дағдысы қосылды!\n\n⏰ Еске салу: *{time}*\n🔥 Streak: 0 күн\n\nКүн сайын орындаңыз!",
        "wrong_time":        "❌ Қате формат. СС:ММ форматында жазыңыз.\n_Мысалы: 08:00_",
        "no_habits":         "📭 Әлі дағды жоқ.\n\n➕ Дағды қосыңыз!",
        "no_stats":          "📭 Әлі дағды жоқ.",
        "confirm_delete":    "⚠️ *{name}* дағдысын жоюды растайсыз ба?",
        "deleted":           "🗑 *{name}* жойылды.",
        "no_delete":         "📭 Жоятын дағды жоқ.",
        "done_today":        "✅ Бүгін орындалды!",
        "done_ok":           "*✅ {name}* — орындалды!",
        "undone":            "*❌ {name}* — болдырылмады!",
        "all_done":          "Бүгінгі барлық дағдыны орындадыңыз, құттықтаймыз 🎉",
        "limit":             "⚠️ Максимум 15 дағды!",
        "remind_title":      "⏰ *Еске салу!*\n\n🎯 Дағды: *{name}*\n\n{motiv}",
        "btn_done":          "✅ Орындадым!",
        "btn_skip":          "❌ Орындамадым",
        "stats_title":       "📊 *Статистика* — {page}/{total} бет",
        "stats_ball":        "⭐ *Жалпы ұпай: {ball}*",
        "stats_rank":        "🎖 Деңгей: {rank}",
        "stats_streak":      "🔥 Streak: {streak} күн",
        "stats_time":        "⏰ Уақыт: {time}",
        "stats_ball2":       "⭐ Дағды ұпайы: {ball}",
        "stats_done":        "✅ Барлығы орындалды: {n} рет",
        "stats_missed":      "❌ Барлығы өткізілді: {n} рет",
        "stats_last":        "📅 Соңғы: {d}",
        "rating_title":      "🏆 Топ 10",
        "rating_empty":      "Ешкім ұпай жинаған жоқ.",
        "sub_required":      "⚠️ Ботты пайдалану үшін арнаға жазылыңыз!",
        "btn_join":          "📢 Арнаға өту",
        "btn_joined":        "✅ Жазылдым",
        "invalid_msg":       "⚠️ Белгісіз хабар, қолданылмайды.",
        "nav_prev":          "⬅️ {n}-бет",
        "nav_next":          "{n}-бет ➡️",
        "ranks":             ["🌱 Жаңадан бастаушы","🥉 Бастаушы","🥈 Тәжірибелі","🥇 Кәсіби","💎 Шебер","🏆 Легенда"],
        "btn_settings":      "⚙️ Параметрлер",
        "settings_title":    "⚙️ *Параметрлер*",
        "btn_change_lang":   "🌐 Тілді өзгерту",
        "btn_change_info":   "📝 Деректерді өзгерту",
        "change_info_text":  "📝 *Деректерді өзгерту*\n\nНені өзгерткіңіз келеді?",
        "rating_no_link":    "username жоқ",
        "hint_toggle":       "Дағдыны түймелер арқылы да растауға болады!",
        "done_percent":      "*Орындалды:* {p}%",
        "share_phone":       "📱 Телефон нөмірін жіберу",
        "ask_phone":         "📱 Телефон нөміріңізді жіберіңіз:\n\n_Мысалы: +998901234567_",
    },
    "tg": {
        "choose_lang":       "🌐 Забонро интихоб кунед:",
        "lang_set":          "✅ Забон тағйир ёфт!",
        "welcome_new":       "👋 Салом, *{name}*!\n\n🌱 Ба *Боти пайгирии одат* хуш омадед!\n\nИн бот ба шумо:\n• Муайян кардани одатҳо\n• Огоҳии саривақтӣ\n• Назорати оморӣ\nимкон медиҳад.\n\n*➕ Илова кардани одат* -ро пахш кунед!",
        "welcome_back":      "📊 *ОДАТҲОИ ШУМО:*",
        "btn_add":           "➕ Илова кардан",
        "btn_delete":        "🗑 Нест кардан",
        "btn_stats":         "📊 Омор",
        "btn_rating":        "🏆 Рейтинг",
        "btn_home":          "🏠 Менюи асосӣ",
        "btn_cancel":        "❌ Бекор кардан",
        "btn_yes":           "Бале ✅",
        "btn_no":            "Не ❌",
        "ask_habit_name":    "📝 Номи одатро нависед:\n\n_Масалан: Китобхонӣ, Варзиш, Нӯшидани об..._",
        "ask_habit_time":    "*✅ Одат:* {name}\n\n*⏰ Вақти огоҳиро ворид кунед* (24 соат):\n\n_Масалан: 07:30 ё 21:00_",
        "habit_added":       "🎉 Одати *{name}* илова шуд!\n\n⏰ Огоҳӣ: *{time}*\n🔥 Streak: 0 рӯз\n\nҲар рӯз иҷро кунед!",
        "wrong_time":        "❌ Формати нодуруст. СС:ДД навишта шавад.\n_Масалан: 08:00_",
        "no_habits":         "📭 Ҳоло одате нест.\n\n➕ Одат илова кунед!",
        "no_stats":          "📭 Ҳоло одате нест.",
        "confirm_delete":    "⚠️ Воқеан одати *{name}* -ро нест кардан мехоҳед?",
        "deleted":           "🗑 *{name}* нест шуд.",
        "no_delete":         "📭 Одате барои нест кардан нест.",
        "done_today":        "✅ Имрӯз аллакай иҷро шуд!",
        "done_ok":           "*✅ {name}* — иҷро шуд!",
        "undone":            "*❌ {name}* — бекор шуд!",
        "all_done":          "Шумо ҳамаи одатҳои имрӯзро иҷро кардед, табрик 🎉",
        "limit":             "⚠️ Ҳадди аксар 15 одат!",
        "remind_title":      "⏰ *Огоҳӣ!*\n\n🎯 Одат: *{name}*\n\n{motiv}",
        "btn_done":          "✅ Иҷро кардам!",
        "btn_skip":          "❌ Иҷро накардам",
        "stats_title":       "📊 *Омор* — {page}/{total} саҳифа",
        "stats_ball":        "⭐ *Ҷамъи хол: {ball}*",
        "stats_rank":        "🎖 Дараҷа: {rank}",
        "stats_streak":      "🔥 Streak: {streak} рӯз",
        "stats_time":        "⏰ Вақт: {time}",
        "stats_ball2":       "⭐ Холи одат: {ball}",
        "stats_done":        "✅ Ҷамъан иҷро шуд: {n} маротиба",
        "stats_missed":      "❌ Ҷамъан иҷро нашуд: {n} маротиба",
        "stats_last":        "📅 Охирин: {d}",
        "rating_title":      "🏆 Топ 10",
        "rating_empty":      "Ҳоло ҳеҷ кас хол ҷамъ накардааст.",
        "sub_required":      "⚠️ Барои истифодаи бот ба канал обуна шавед!",
        "btn_join":          "📢 Рафтан ба канал",
        "btn_joined":        "✅ Обуна шудам",
        "invalid_msg":       "⚠️ Паёми номаълум дастгирӣ намешавад.",
        "nav_prev":          "⬅️ Саҳифаи {n}",
        "nav_next":          "Саҳифаи {n} ➡️",
        "ranks":             ["🌱 Тозакор","🥉 Иштидоӣ","🥈 Ботаҷриба","🥇 Касбӣ","💎 Устод","🏆 Афсона"],
        "btn_settings":      "⚙️ Танзимот",
        "settings_title":    "⚙️ *Танзимот*",
        "btn_change_lang":   "🌐 Иваз кардани забон",
        "btn_change_info":   "📝 Иваз кардани маълумот",
        "change_info_text":  "📝 *Иваз кардани маълумот*\n\nЧиро иваз кардан мехоҳед?",
        "rating_no_link":    "username нест",
        "hint_toggle":       "Тавассути тугмаҳо низ одатро тасдиқ кардан мумкин!",
        "done_percent":      "*Иҷро шуд:* {p}%",
        "share_phone":       "📱 Рақами телефонро фиристед",
        "ask_phone":         "📱 Рақами телефонро фиристед:\n\n_Масалан: +998901234567_",
    },
    "tk": {
        "choose_lang":       "🌐 Dili saýlaň:",
        "lang_set":          "✅ Dil üýtgedildi!",
        "welcome_new":       "👋 Salam, *{name}*!\n\n🌱 *Endik yzarlaýjy bota* hoş geldiňiz!\n\nBu bot size:\n• Endikleri belgelemek\n• Wagtynda ýatlatma almak\n• Statistika ýöretmek\nmümkinçiligini berýär.\n\n*➕ Endik goşmak* düwmesine basyň!",
        "welcome_back":      "📊 *ENDIKLERIŇIZ:*",
        "btn_add":           "➕ Endik goşmak",
        "btn_delete":        "🗑 Pozmak",
        "btn_stats":         "📊 Statistika",
        "btn_rating":        "🏆 Reýting",
        "btn_home":          "🏠 Baş menýu",
        "btn_cancel":        "❌ Ýatyr",
        "btn_yes":           "Hawa ✅",
        "btn_no":            "Ýok ❌",
        "ask_habit_name":    "📝 Endigiň adyny ýazyň:\n\n_Mysal: Kitap okamak, Sport, Suw içmek..._",
        "ask_habit_time":    "*✅ Endik:* {name}\n\n*⏰ Ýatlatma wagtyny giriziň* (24 sagat):\n\n_Mysal: 07:30 ýa-da 21:00_",
        "habit_added":       "🎉 *{name}* endigi goşuldy!\n\n⏰ Ýatlatma: *{time}*\n🔥 Streak: 0 gün\n\nHer gün ýerine ýetiriň!",
        "wrong_time":        "❌ Nädogry format. SS:MM formatynda ýazyň.\n_Mysal: 08:00_",
        "no_habits":         "📭 Entek endik ýok.\n\n➕ Endik goşuň!",
        "no_stats":          "📭 Entek endik ýok.",
        "confirm_delete":    "⚠️ *{name}* endigi pozmak isleýärsiňizmi?",
        "deleted":           "🗑 *{name}* pozuldy.",
        "no_delete":         "📭 Pozmak üçin endik ýok.",
        "done_today":        "✅ Şu gün eýýäm edildi!",
        "done_ok":           "*✅ {name}* — edildi!",
        "undone":            "*❌ {name}* — ýatyryldy!",
        "all_done":          "Şu günki ähli endikleri tamamladyňyz, gutlaýarys 🎉",
        "limit":             "⚠️ Iň köp 15 endik!",
        "remind_title":      "⏰ *Ýatlatma!*\n\n🎯 Endik: *{name}*\n\n{motiv}",
        "btn_done":          "✅ Etdim!",
        "btn_skip":          "❌ Etmedim",
        "stats_title":       "📊 *Statistika* — {page}/{total} sahypa",
        "stats_ball":        "⭐ *Jemi bal: {ball}*",
        "stats_rank":        "🎖 Dereje: {rank}",
        "stats_streak":      "🔥 Streak: {streak} gün",
        "stats_time":        "⏰ Wagt: {time}",
        "stats_ball2":       "⭐ Endik baly: {ball}",
        "stats_done":        "✅ Jemi edildi: {n} gezek",
        "stats_missed":      "❌ Jemi edilmedi: {n} gezek",
        "stats_last":        "📅 Soňky: {d}",
        "rating_title":      "🏆 Iň gowy 10",
        "rating_empty":      "Entek hiç kim bal ýygnamandy.",
        "sub_required":      "⚠️ Boty ulanmak üçin kanala agza boluň!",
        "btn_join":          "📢 Kanala geç",
        "btn_joined":        "✅ Agza boldum",
        "invalid_msg":       "⚠️ Näbelli habar, goldanmaýar.",
        "nav_prev":          "⬅️ {n}-sahypa",
        "nav_next":          "{n}-sahypa ➡️",
        "ranks":             ["🌱 Täze başlaýan","🥉 Başlangyç","🥈 Tejribeli","🥇 Hünärmen","💎 Usta","🏆 Rowaýat"],
        "btn_settings":      "⚙️ Sazlamalar",
        "settings_title":    "⚙️ *Sazlamalar*",
        "btn_change_lang":   "🌐 Dili üýtgetmek",
        "btn_change_info":   "📝 Maglumaty üýtgetmek",
        "change_info_text":  "📝 *Maglumaty üýtgetmek*\n\nNäme üýtgetmek isleýärsiňiz?",
        "rating_no_link":    "username ýok",
        "hint_toggle":       "Düwmelere basyp hem endiki tassyklap bilersiňiz!",
        "done_percent":      "*Edildi:* {p}%",
        "share_phone":       "📱 Telefon belgisini paýlaş",
        "ask_phone":         "📱 Telefon belgiňizi iberiň:\n\n_Mysal: +998901234567_",
    },
    "ky": {
        "choose_lang":       "🌐 Тилди тандаңыз:",
        "lang_set":          "✅ Тил өзгөртүлдү!",
        "welcome_new":       "👋 Салам, *{name}*!\n\n🌱 *Адат трекер ботуна* кош келиңиз!\n\nБул бот сизге:\n• Адаттарды белгилөө\n• Убагында эстетме алуу\n• Статистиканы жүргүзүү\nмүмкүнчүлүгүн берет.\n\n*➕ Адат кошуу* баскычын басыңыз!",
        "welcome_back":      "📊 *АДАТТАРЫҢЫЗ:*",
        "btn_add":           "➕ Адат кошуу",
        "btn_delete":        "🗑 Жою",
        "btn_stats":         "📊 Статистика",
        "btn_rating":        "🏆 Рейтинг",
        "btn_home":          "🏠 Башкы меню",
        "btn_cancel":        "❌ Жокко чыгаруу",
        "btn_yes":           "Ооба ✅",
        "btn_no":            "Жок ❌",
        "ask_habit_name":    "📝 Адаттын атын жазыңыз:\n\n_Мисалы: Китеп окуу, Спорт, Суу ичүү..._",
        "ask_habit_time":    "*✅ Адат:* {name}\n\n*⏰ Эстетме убагын киргизиңиз* (24 саат):\n\n_Мисалы: 07:30 же 21:00_",
        "habit_added":       "🎉 *{name}* адаты кошулду!\n\n⏰ Эстетме: *{time}*\n🔥 Streak: 0 күн\n\nКүн сайын аткарыңыз!",
        "wrong_time":        "❌ Туура эмес формат. СС:ММ форматында жазыңыз.\n_Мисалы: 08:00_",
        "no_habits":         "📭 Азырынча адат жок.\n\n➕ Адат кошуңуз!",
        "no_stats":          "📭 Азырынча адат жок.",
        "confirm_delete":    "⚠️ *{name}* адатын чындап жоюуну каалайсызбы?",
        "deleted":           "🗑 *{name}* жойулду.",
        "no_delete":         "📭 Жоюу үчүн адат жок.",
        "done_today":        "✅ Бүгүн буга чейин аткарылды!",
        "done_ok":           "*✅ {name}* — аткарылды!",
        "undone":            "*❌ {name}* — жокко чыгарылды!",
        "all_done":          "Бүгүнкү бардык адатты аткардыңыз, куттуктайбыз 🎉",
        "limit":             "⚠️ Максималдуу 15 адат!",
        "remind_title":      "⏰ *Эстетме!*\n\n🎯 Адат: *{name}*\n\n{motiv}",
        "btn_done":          "✅ Аткардым!",
        "btn_skip":          "❌ Аткарган жокмун",
        "stats_title":       "📊 *Статистика* — {page}/{total} барак",
        "stats_ball":        "⭐ *Жалпы упай: {ball}*",
        "stats_rank":        "🎖 Деңгээл: {rank}",
        "stats_streak":      "🔥 Streak: {streak} күн",
        "stats_time":        "⏰ Убакыт: {time}",
        "stats_ball2":       "⭐ Адат упайы: {ball}",
        "stats_done":        "✅ Жалпы аткарылды: {n} жолу",
        "stats_missed":      "❌ Жалпы өткөрүлдү: {n} жолу",
        "stats_last":        "📅 Акыркы: {d}",
        "rating_title":      "🏆 Топ 10",
        "rating_empty":      "Азырынча эч ким упай чогулткан жок.",
        "sub_required":      "⚠️ Ботту колдонуу үчүн каналга жазылыңыз!",
        "btn_join":          "📢 Каналга өтүү",
        "btn_joined":        "✅ Жазылдым",
        "invalid_msg":       "⚠️ Белгисиз билдирүү, колдоого алынбайт.",
        "nav_prev":          "⬅️ {n}-барак",
        "nav_next":          "{n}-барак ➡️",
        "ranks":             ["🌱 Жаңы баштоочу","🥉 Башталгыч","🥈 Тажрыйбалуу","🥇 Профессионал","💎 Чебер","🏆 Легенда"],
        "btn_settings":      "⚙️ Жөндөөлөр",
        "settings_title":    "⚙️ *Жөндөөлөр*",
        "btn_change_lang":   "🌐 Тилди өзгөртүү",
        "btn_change_info":   "📝 Маалыматты өзгөртүү",
        "change_info_text":  "📝 *Маалыматты өзгөртүү*\n\nЭмнени өзгөрткүңүз келет?",
        "rating_no_link":    "username жок",
        "hint_toggle":       "Баскычтарды басуу аркылуу да адатты ырастасаңыз болот!",
        "done_percent":      "*Аткарылды:* {p}%",
        "share_phone":       "📱 Телефон номерин жөнөт",
        "ask_phone":         "📱 Телефон номериңизди жөнөтүңүз:\n\n_Мисалы: +998901234567_",
    },
    "de": {
        "choose_lang":       "🌐 Sprache wählen:",
        "lang_set":          "✅ Sprache geändert!",
        "welcome_new":       "👋 Hallo, *{name}*!\n\n🌱 Willkommen beim *Gewohnheits-Tracker-Bot*!\n\nDieser Bot hilft dir:\n• Gewohnheiten verfolgen\n• Erinnerungen erhalten\n• Statistiken führen\n\nDrücke *➕ Gewohnheit hinzufügen*!",
        "welcome_back":      "📊 *DEINE GEWOHNHEITEN:*",
        "btn_add":           "➕ Hinzufügen",
        "btn_delete":        "🗑 Löschen",
        "btn_stats":         "📊 Statistik",
        "btn_rating":        "🏆 Rangliste",
        "btn_home":          "🏠 Hauptmenü",
        "btn_cancel":        "❌ Abbrechen",
        "btn_yes":           "Ja ✅",
        "btn_no":            "Nein ❌",
        "ask_habit_name":    "📝 Gewohnheitsname eingeben:\n\n_Beispiel: Lesen, Sport, Wasser trinken..._",
        "ask_habit_time":    "*✅ Gewohnheit:* {name}\n\n*⏰ Erinnerungszeit eingeben* (24h):\n\n_Beispiel: 07:30 oder 21:00_",
        "habit_added":       "🎉 Gewohnheit *{name}* hinzugefügt!\n\n⏰ Erinnerung: *{time}*\n🔥 Serie: 0 Tage\n\nTäglich ausführen!",
        "wrong_time":        "❌ Falsches Format. Bitte HH:MM verwenden.\n_Beispiel: 08:00_",
        "no_habits":         "📭 Noch keine Gewohnheiten.\n\n➕ Füge eine hinzu!",
        "no_stats":          "📭 Noch keine Gewohnheiten.",
        "confirm_delete":    "⚠️ Gewohnheit *{name}* wirklich löschen?",
        "deleted":           "🗑 *{name}* gelöscht.",
        "no_delete":         "📭 Keine Gewohnheit zum Löschen.",
        "done_today":        "✅ Heute bereits erledigt!",
        "done_ok":           "*✅ {name}* — erledigt!",
        "undone":            "*❌ {name}* — rückgängig!",
        "all_done":          "Alle heutigen Gewohnheiten erledigt, Glückwunsch 🎉",
        "limit":             "⚠️ Maximal 15 Gewohnheiten!",
        "remind_title":      "⏰ *Erinnerung!*\n\n🎯 Gewohnheit: *{name}*\n\n{motiv}",
        "btn_done":          "✅ Erledigt!",
        "btn_skip":          "❌ Nicht erledigt",
        "stats_title":       "📊 *Statistik* — Seite {page}/{total}",
        "stats_ball":        "⭐ *Gesamtpunkte: {ball}*",
        "stats_rank":        "🎖 Level: {rank}",
        "stats_streak":      "🔥 Serie: {streak} Tage",
        "stats_time":        "⏰ Zeit: {time}",
        "stats_ball2":       "⭐ Gewohnheitspunkte: {ball}",
        "stats_done":        "✅ Gesamt erledigt: {n} Mal",
        "stats_missed":      "❌ Gesamt verpasst: {n} Mal",
        "stats_last":        "📅 Letztes: {d}",
        "rating_title":      "🏆 Top 10",
        "rating_empty":      "Noch niemand hat Punkte gesammelt.",
        "sub_required":      "⚠️ Abonniere den Kanal um den Bot zu nutzen!",
        "btn_join":          "📢 Zum Kanal",
        "btn_joined":        "✅ Abonniert",
        "invalid_msg":       "⚠️ Unbekannte Nachricht, nicht unterstützt.",
        "nav_prev":          "⬅️ Seite {n}",
        "nav_next":          "Seite {n} ➡️",
        "ranks":             ["🌱 Anfänger","🥉 Einsteiger","🥈 Erfahren","🥇 Profi","💎 Meister","🏆 Legende"],
        "btn_settings":      "⚙️ Einstellungen",
        "settings_title":    "⚙️ *Einstellungen*",
        "btn_change_lang":   "🌐 Sprache ändern",
        "btn_change_info":   "📝 Profil bearbeiten",
        "change_info_text":  "📝 *Profil bearbeiten*\n\nWas möchten Sie ändern?",
        "rating_no_link":    "kein username",
        "hint_toggle":       "Sie können Gewohnheiten auch per Schaltfläche bestätigen!",
        "done_percent":      "*Erledigt:* {p}%",
        "share_phone":       "📱 Telefonnummer senden",
        "ask_phone":         "📱 Senden Sie Ihre Telefonnummer:\n\n_Beispiel: +998901234567_",
    },
    "fr": {
        "choose_lang":       "🌐 Choisissez la langue:",
        "lang_set":          "✅ Langue modifiée!",
        "welcome_new":       "👋 Bonjour, *{name}*!\n\n🌱 Bienvenue sur le *Bot de suivi des habitudes*!\n\nCe bot vous aide à:\n• Définir des habitudes\n• Recevoir des rappels\n• Suivre vos statistiques\n\nAppuyez sur *➕ Ajouter une habitude*!",
        "welcome_back":      "📊 *VOS HABITUDES:*",
        "btn_add":           "➕ Ajouter",
        "btn_delete":        "🗑 Supprimer",
        "btn_stats":         "📊 Statistiques",
        "btn_rating":        "🏆 Classement",
        "btn_home":          "🏠 Menu principal",
        "btn_cancel":        "❌ Annuler",
        "btn_yes":           "Oui ✅",
        "btn_no":            "Non ❌",
        "ask_habit_name":    "📝 Entrez le nom de l'habitude:\n\n_Exemple: Lecture, Sport, Boire de l'eau..._",
        "ask_habit_time":    "*✅ Habitude:* {name}\n\n*⏰ Entrez l'heure du rappel* (24h):\n\n_Exemple: 07:30 ou 21:00_",
        "habit_added":       "🎉 Habitude *{name}* ajoutée!\n\n⏰ Rappel: *{time}*\n🔥 Série: 0 jours\n\nFaites-le chaque jour!",
        "wrong_time":        "❌ Format incorrect. Utilisez HH:MM.\n_Exemple: 08:00_",
        "no_habits":         "📭 Pas encore d'habitudes.\n\nAppuyez sur ➕ Ajouter!",
        "no_stats":          "📭 Pas encore d'habitudes.",
        "confirm_delete":    "⚠️ Supprimer l'habitude *{name}*?",
        "deleted":           "🗑 *{name}* supprimée.",
        "no_delete":         "📭 Aucune habitude à supprimer.",
        "done_today":        "✅ Déjà fait aujourd'hui!",
        "done_ok":           "*✅ {name}* — fait!",
        "undone":            "*❌ {name}* — annulé!",
        "all_done":          "Toutes les habitudes du jour accomplies, félicitations 🎉",
        "limit":             "⚠️ Maximum 15 habitudes!",
        "remind_title":      "⏰ *Rappel!*\n\n🎯 Habitude: *{name}*\n\n{motiv}",
        "btn_done":          "✅ Fait!",
        "btn_skip":          "❌ Non fait",
        "stats_title":       "📊 *Statistiques* — page {page}/{total}",
        "stats_ball":        "⭐ *Total points: {ball}*",
        "stats_rank":        "🎖 Niveau: {rank}",
        "stats_streak":      "🔥 Série: {streak} jours",
        "stats_time":        "⏰ Heure: {time}",
        "stats_ball2":       "⭐ Points habitude: {ball}",
        "stats_done":        "✅ Total accompli: {n} fois",
        "stats_missed":      "❌ Total manqué: {n} fois",
        "stats_last":        "📅 Dernier: {d}",
        "rating_title":      "🏆 Top 10",
        "rating_empty":      "Personne n'a encore marqué de points.",
        "sub_required":      "⚠️ Abonnez-vous à la chaîne pour utiliser le bot!",
        "btn_join":          "📢 Aller à la chaîne",
        "btn_joined":        "✅ Abonné",
        "invalid_msg":       "⚠️ Message inconnu, non supporté.",
        "nav_prev":          "⬅️ Page {n}",
        "nav_next":          "Page {n} ➡️",
        "ranks":             ["🌱 Débutant","🥉 Novice","🥈 Expérimenté","🥇 Professionnel","💎 Maître","🏆 Légende"],
        "btn_settings":      "⚙️ Paramètres",
        "settings_title":    "⚙️ *Paramètres*",
        "btn_change_lang":   "🌐 Changer la langue",
        "btn_change_info":   "📝 Modifier le profil",
        "change_info_text":  "📝 *Modifier le profil*\n\nQue souhaitez-vous modifier?",
        "rating_no_link":    "pas de username",
        "hint_toggle":       "Vous pouvez aussi confirmer les habitudes en appuyant sur les boutons!",
        "done_percent":      "*Accompli:* {p}%",
        "share_phone":       "📱 Envoyer le numéro de téléphone",
        "ask_phone":         "📱 Envoyez votre numéro de téléphone:\n\n_Exemple: +998901234567_",
    },
}


def get_lang(uid):
    u = load_user(uid)
    return u.get("lang", "uz")

def today_uz5():
    """UTC+5 (Toshkent) bo'yicha bugungi sana"""
    from datetime import timezone, timedelta
    tz_uz = timezone(timedelta(hours=5))
    return datetime.now(tz_uz).strftime("%Y-%m-%d")

def T(uid, key, **kwargs):
    lang = get_lang(uid)
    text = LANGS.get(lang, LANGS["uz"]).get(key, LANGS["uz"].get(key, key))
    return text.format(**kwargs) if kwargs else text

def get_rank(uid, points):
    lang   = get_lang(uid)
    ranks  = LANGS.get(lang, LANGS["uz"])["ranks"]
    if points >= 500: rank = ranks[5]
    elif points >= 200: rank = ranks[4]
    elif points >= 100: rank = ranks[3]
    elif points >= 50:  rank = ranks[2]
    elif points >= 20:  rank = ranks[1]
    else: rank = ranks[0]
    # VIP nishon
    u = load_user(uid)
    if u.get("is_vip"):
        rank = "💎 VIP | " + rank
    return rank

def lang_keyboard():
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("🇺🇿 O'zbek",   callback_data="set_lang_uz"),
        InlineKeyboardButton("🇬🇧 English",  callback_data="set_lang_en"),
    )
    kb.row(
        InlineKeyboardButton("🇷🇺 Русский",  callback_data="set_lang_ru"),
    )
    return kb

# ============================================================
#  MOTIVATSIYA
# ============================================================
MOTIVATSIYA = {
    "uz": [
        "🚀 Siz qila olasiz! Motivatsiya boshlashga yordam beradi, odat esa davom etishga.",
        "🚀 Siz qila olasiz! Biz nimaniki muntazam qilsak, o'shanga aylanib boramiz. Muvaffaqiyat bu tasodif emas, odatdir.",
        "🚀 Siz qila olasiz! Dastlab biz odatlarimizni shakllantiramiz, so'ngra odatlarimiz bizni.",
        "🚀 Siz qila olasiz! Har kungi 1 foizlik o'sish bir yildan so'ng 37 barobar kuchliroq bo'lishingizni ta'minlaydi.",
        "🚀 Siz qila olasiz! Muvaffaqiyat — bir martalik mo'jiza emas, har kungi kichik odatlar mahsulidir.",
        "🚀 Siz qila olasiz! Intizom motivatsiyadan kuchliroq. Kayfiyatga qarab emas, maqsadga qarab harakat qiling.",
        "🚀 Siz qila olasiz! Maqsadlaringiz darajasiga ko'tarilmaysiz, odatlaringiz darajasiga tushib qolasiz.",
        "🚀 Siz qila olasiz! Eng qiyini — birinchi qadamni tashlash. Shunchaki boshlang.",
        "🚀 Siz qila olasiz! Katta o'ylang, lekin juda kichik qadamdan boshlang.",
        "🚀 Siz qila olasiz! Ketma-ket ikki marta o'tkazib yubormang. Birinchi xato — tasodif, ikkinchisi — yomon odatning boshlanishi.",
        "🚀 Siz qila olasiz! Barqarorlik — har qanday muvaffaqiyatning asosiy kalitidir.",
        "🚀 Siz qila olasiz! Mukammallikka intilmang, doimiy o'sishga intiling.",
        "🚀 Siz qila olasiz! Yomon odatni shunchaki tashlab bo'lmaydi, uni yaxshisi bilan almashtirish kerak.",
        "🚀 Siz qila olasiz! Natijaga emas, o'sha natijaga munosib insonga aylanishingizga e'tibor bering.",
        "🚀 Siz qila olasiz! Odat — yengib o'tiladigan marra emas, yashash tarzidir.",
        "🚀 Siz qila olasiz! Hatto kayfiyatingiz yo'q kunlari ham, qoida uchun ozgina bo'lsa-da harakat qiling.",
        "🚀 Siz qila olasiz! Irodangizga tayanmang, atrof-muhitni o'z odatlaringizga moslashtiring.",
        "🚀 Siz qila olasiz! To'g'ri ishni bajarishni osonlashtiring, chalg'ituvchi narsalarni uzoqlashtiring.",
        "🚀 Siz qila olasiz! Kutib o'tirmang, harakat qilsangiz motivatsiya o'z-o'zidan keladi.",
        "🚀 Siz qila olasiz! Bugun qilgan harakatingiz butun kelajagingizni yaxshilashi mumkin.",
        "🚀 Siz qila olasiz! Vaqt yaxshi odatlarni do'stingizga, yomonlarini dushmaningizga aylantiradi.",
        "🚀 Siz qila olasiz! O'zingizga qilingan har kungi kichik sarmoya kelajakda eng katta foyda keltiradi.",
        "🚀 Siz qila olasiz! Buyuk ishlar bir kunda qilinmaydi, sabrli bo'ling.",
        "🚀 Siz qila olasiz! Zanjirni uzib qo'ymang: uzluksizlik natijani kafolatlaydi.",
        "🚀 Siz qila olasiz! Natijani ko'rmayotgan bo'lsangiz ham to'xtamang; ildiz doim tuproq ostida o'sadi.",
        "🚀 Siz qila olasiz! Sizning bugungi hayotingiz — o'tmishdagi odatlaringizning yig'indisi xolos.",
        "🚀 Siz qila olasiz! Ertalabki birinchi g'alaba (odat) butun kuningizni belgilab beradi.",
        "🚀 Siz qila olasiz! Qiyinchiliklar o'sish jarayonining bir qismidir, qochmang, yuzlaning.",
        "🚀 Siz qila olasiz! Qayd etilgan narsa o'sadi: odatlaringizni kuzatib boring.",
        "🚀 Siz qila olasiz! Siz bu ishlarni \"qilishga majbur emassiz\", balki \"qilish imkoniyatiga egasiz\".",
    ],
    "en": [
        "🚀 You can do it! Motivation helps you start, but habit keeps you going.",
        "🚀 You can do it! We become what we repeatedly do. Excellence is not an accident, it is a habit.",
        "🚀 You can do it! First we shape our habits, then our habits shape us.",
        "🚀 You can do it! A 1% daily improvement makes you 37 times stronger in a year.",
        "🚀 You can do it! Success is not a one-time miracle, it is the product of daily small habits.",
        "🚀 You can do it! Discipline is stronger than motivation. Act based on your goal, not your mood.",
        "🚀 You can do it! You do not rise to the level of your goals, you fall to the level of your habits.",
        "🚀 You can do it! The hardest part is taking the first step. Just start.",
        "🚀 You can do it! Think big, but start with a tiny step.",
        "🚀 You can do it! Never miss twice in a row. The first miss is an accident, the second is the start of a bad habit.",
        "🚀 You can do it! Consistency is the key to any success.",
        "🚀 You can do it! Do not strive for perfection, strive for constant growth.",
        "🚀 You can do it! You cannot just quit a bad habit, you need to replace it with a better one.",
        "🚀 You can do it! Focus not on the result, but on becoming the person worthy of that result.",
        "🚀 You can do it! A habit is not a finish line to cross, it is a way of life.",
        "🚀 You can do it! Even on days when you feel low, do at least a little to keep the rule.",
        "🚀 You can do it! Do not rely on willpower, adapt your environment to your habits.",
        "🚀 You can do it! Make the right thing easy to do, and distractions hard to reach.",
        "🚀 You can do it! Do not wait for motivation, start acting and it will come.",
        "🚀 You can do it! What you do today can improve your entire future.",
        "🚀 You can do it! Time turns good habits into your friend and bad ones into your enemy.",
        "🚀 You can do it! Every small daily investment in yourself brings the greatest return in the future.",
        "🚀 You can do it! Great things are not done in a day, be patient.",
        "🚀 You can do it! Do not break the chain: consistency guarantees results.",
        "🚀 You can do it! Even if you do not see results yet, keep going. Roots always grow underground.",
        "🚀 You can do it! Your life today is simply the sum of your past habits.",
        "🚀 You can do it! Your first morning victory (habit) sets the tone for your entire day.",
        "🚀 You can do it! Challenges are part of the growth process. Do not run, face them.",
        "🚀 You can do it! What gets tracked gets improved: keep monitoring your habits.",
        "🚀 You can do it! You do not have to do this, you get to do this.",
    ],
    "ru": [
        "🚀 Ты справишься! Мотивация помогает начать, а привычка помогает продолжать.",
        "🚀 Ты справишься! Мы становимся тем, что делаем регулярно. Успех — не случайность, а привычка.",
        "🚀 Ты справишься! Сначала мы формируем привычки, а потом привычки формируют нас.",
        "🚀 Ты справишься! Ежедневный рост на 1% за год сделает тебя в 37 раз сильнее.",
        "🚀 Ты справишься! Успех — не разовое чудо, а результат ежедневных маленьких привычек.",
        "🚀 Ты справишься! Дисциплина сильнее мотивации. Действуй ради цели, а не по настроению.",
        "🚀 Ты справишься! Ты не поднимаешься до уровня целей, а опускаешься до уровня привычек.",
        "🚀 Ты справишься! Самое сложное — сделать первый шаг. Просто начни.",
        "🚀 Ты справишься! Думай масштабно, но начинай с крошечного шага.",
        "🚀 Ты справишься! Не пропускай дважды подряд. Первый пропуск — случайность, второй — начало плохой привычки.",
        "🚀 Ты справишься! Постоянство — ключ к любому успеху.",
        "🚀 Ты справишься! Не стремись к совершенству, стремись к постоянному росту.",
        "🚀 Ты справишься! Плохую привычку нельзя просто бросить, её нужно заменить хорошей.",
        "🚀 Ты справишься! Фокусируйся не на результате, а на том, чтобы стать достойным этого результата.",
        "🚀 Ты справишься! Привычка — это не финиш, а образ жизни.",
        "🚀 Ты справишься! Даже в плохие дни делай хотя бы немного, чтобы сохранить правило.",
        "🚀 Ты справишься! Не полагайся на силу воли, адаптируй среду под свои привычки.",
        "🚀 Ты справишься! Сделай правильное действие лёгким, а отвлекающее — трудным.",
        "🚀 Ты справишься! Не жди мотивацию, начни действовать — она придёт сама.",
        "🚀 Ты справишься! То, что ты делаешь сегодня, может улучшить всё твоё будущее.",
        "🚀 Ты справишься! Время превращает хорошие привычки в друга, а плохие — во врага.",
        "🚀 Ты справишься! Каждая маленькая ежедневная инвестиция в себя даёт самую большую отдачу.",
        "🚀 Ты справишься! Великие дела не делаются за один день, будь терпелив.",
        "🚀 Ты справишься! Не разрывай цепочку: непрерывность гарантирует результат.",
        "🚀 Ты справишься! Даже если не видишь результат, не останавливайся. Корни всегда растут под землёй.",
        "🚀 Ты справишься! Твоя сегодняшняя жизнь — это просто сумма прошлых привычек.",
        "🚀 Ты справишься! Первая утренняя победа (привычка) задаёт тон всему дню.",
        "🚀 Ты справишься! Трудности — часть роста. Не убегай, встречай их лицом.",
        "🚀 Ты справишься! То, что отслеживается — улучшается. Следи за своими привычками.",
        "🚀 Ты справишься! Ты не обязан это делать — у тебя есть возможность это делать.",
    ],
    "tr": ["💪 Her gün yeni bir fırsat!", "🔥 Seriyi bozma!", "🌟 Küçük adımlar büyük başarıya!", "🚀 Yapabilirsin!", "🎯 Hedefe bir adım daha!"],
    "kk": ["💪 Әр күн — жаңа мүмкіндік!", "🔥 Қатарыңызды үзбеңіз!", "🌟 Кіші қадамдар үлкен жетістікке!", "🚀 Сіз жасай аласыз!", "🎯 Мақсатқа бір қадам!"],
    "tg": ["💪 Ҳар рӯз имкони нав аст!", "🔥 Пайдаро нашикон!", "🌟 Қадамҳои хурд ба муваффақияти бузург!", "🚀 Шумо метавонед!", "🎯 Як қадам ба ҳадаф!"],
    "tk": ["💪 Her gün täze mümkinçilik!", "🔥 Yzygiderliligiňizi bozmaň!", "🌟 Kiçi ädimler uly üstünlige!", "🚀 Siz edip bilersiňiz!", "🎯 Maksada bir ädim!"],
    "ky": ["💪 Ар бир күн жаңы мүмкүнчүлүк!", "🔥 Катарыңызды үзбөңүз!", "🌟 Кичи кадамдар чоң ийгиликке!", "🚀 Сиз жасай аласыз!", "🎯 Максатка бир кадам!"],
    "de": ["💪 Jeder Tag ist eine neue Chance!", "🔥 Brich die Serie nicht!", "🌟 Kleine Schritte führen zu großem Erfolg!", "🚀 Du schaffst das!", "🎯 Einen Schritt näher am Ziel!"],
    "fr": ["💪 Chaque jour est une nouvelle chance!", "🔥 Ne brisez pas la série!", "🌟 Les petits pas mènent au grand succès!", "🚀 Vous pouvez le faire!", "🎯 Un pas de plus vers votre objectif!"],
}

# ============================================================
#  BOT
# ============================================================
bot = telebot.TeleBot(BOT_TOKEN)

# Bot username — bir marta yuklanadi, keyingi murojaatlarda qayta so'ralmasin
_BOT_USERNAME = None

def get_bot_username():
    """Bot username'ini qaytaradi — birinchi chaqiruvda yuklanadi, keyin cache'dan."""
    global _BOT_USERNAME
    if not _BOT_USERNAME:
        try:
            _BOT_USERNAME = bot.get_me().username
        except Exception:
            _BOT_USERNAME = "Super_habits_bot"
    return _BOT_USERNAME

def send_message_colored(chat_id, text, reply_markup_dict, parse_mode="Markdown"):
    """Bot API 9.4 style (rangli tugmalar) uchun to'g'ridan HTTP so'rov"""
    url  = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id":      chat_id,
        "text":         text,
        "parse_mode":   parse_mode,
        "reply_markup": reply_markup_dict,
    }
    resp = requests.post(url, json=payload)
    result = resp.json()
    if result.get("ok"):
        class FakeMsg:
            def __init__(self, msg_id):
                self.message_id = msg_id
        return FakeMsg(result["result"]["message_id"])
    print(f"[send_message_colored] XATO: {result.get('description')}")
    return None

def cBtn(text, callback_data, style=None):
    """Rangli InlineKeyboardButton - style atributini qo'shadi"""
    btn = InlineKeyboardButton(text, callback_data=callback_data)
    if style:
        btn.style = style
    return btn

def ok_kb():
    """'✅ Tushunarli' tugmasi — bosish bilan xabar o'chadi"""
    kb = InlineKeyboardMarkup()
    kb.add(cBtn("✅ Tushunarli", "ack_delete_msg", "success"))
    return kb

def kb_to_dict(kb):
    """InlineKeyboardMarkup ni dict formatiga o'tkazish (rangli tugmalar uchun)"""
    rows = []
    for row in kb.keyboard:
        r = []
        for btn in row:
            d = {"text": btn.text, "callback_data": btn.callback_data or ""}
            if hasattr(btn, "style") and btn.style:
                d["style"] = btn.style
            r.append(d)
        rows.append(r)
    return {"inline_keyboard": rows}

def edit_message_colored(chat_id, message_id, text, reply_markup_dict, parse_mode="Markdown"):
    """Bot API 9.4 style (rangli tugmalar) uchun xabarni tahrirlash"""
    url  = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
    payload = {
        "chat_id":      chat_id,
        "message_id":   message_id,
        "text":         text,
        "parse_mode":   parse_mode,
        "reply_markup": reply_markup_dict,
    }
    requests.post(url, json=payload)

def main_menu_dict(uid=None, page=1):
    """Faqat Web App tugmasi"""
    webapp_url = os.environ.get("WEBAPP_URL", "https://worker-production-3492.up.railway.app")
    return {"inline_keyboard": [[
        {"text": "📃 Kirish", "web_app": {"url": webapp_url}}
    ]]}

def main_menu(uid=None, page=1):
    """Eski kod bilan moslik uchun (ba'zi joylarda hali ishlatiladi)"""
    from telebot.types import WebAppInfo
    d = main_menu_dict(uid, page)
    kb = InlineKeyboardMarkup()
    for row in d["inline_keyboard"]:
        btns = []
        for b in row:
            if "web_app" in b:
                btns.append(InlineKeyboardButton(b["text"], web_app=WebAppInfo(url=b["web_app"]["url"])))
            else:
                btns.append(InlineKeyboardButton(b["text"], callback_data=b.get("callback_data", "")))
        if len(btns) == 1:
            kb.add(btns[0])
        else:
            kb.row(*btns)
    return kb

def done_keyboard(uid, habit_id):
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton(T(uid, "btn_done"), callback_data=f"done_{habit_id}"),
        InlineKeyboardButton(T(uid, "btn_skip"),  callback_data=f"skip_{habit_id}")
    )
    return kb

def build_main_text(uid):
    u    = load_user(uid)
    name = u.get("name", "ism")
    return (
        f"👋 *Assalomu alaykum, {name}!*\n\n"
        f"🌱 Odatlaringizni barpo etish, rivojlantirish, "
        f"kuzatib borish, qiziqarli raqobat, oson va tez "
        f"shakllantirish uchun, eng to\'g\'ri joydasiz!\n\n"
        f"Ushbu sayohatni boshlash uchun:\n"
        f"« 📃 *Kirish*» tugmasini bosing! 👇"
    )


def send_main_menu(uid, text=None):
    u = load_user(uid)
    if text is None:
        text = build_main_text(uid)
    sent = send_message_colored(uid, text, main_menu_dict(uid))
    if sent is None:
        sent = bot.send_message(uid, text, parse_mode="Markdown", reply_markup=main_menu(uid))
    u["main_msg_id"] = sent.message_id
    ids = u.get("start_msg_ids", [])
    ids.append(sent.message_id)
    u["start_msg_ids"] = ids
    save_user(uid, u)


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
        except Exception:
            pass
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

# ============================================================
#  ONBOARDING
# ============================================================
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

# ============================================================
#  REYITING
# ============================================================

# ============================================================
#  REYTING RASM GENERATSIYASI
# ============================================================
def generate_rating_image(top10_data):
    """
    top10_data: list of (name, points, jon_val, is_vip, user_id)
    Returns: BytesIO rasm — Top 10 + 7 kunlik done_log grid
    """
    from datetime import timezone, timedelta
    FONT   = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    FONT_R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

    DAYS    = 7
    W       = 1080
    ROW_H   = 98
    HDR_H   = 175
    FTR_H   = 60
    H       = HDR_H + ROW_H * 10 + FTR_H + 8

    img  = Image.new("RGB", (W, H), (10, 10, 18))
    draw = ImageDraw.Draw(img)

    try:
        f_title = ImageFont.truetype(FONT,   48)
        f_sub   = ImageFont.truetype(FONT_R, 20)
        f_rank  = ImageFont.truetype(FONT,   26)
        f_name  = ImageFont.truetype(FONT,   28)
        f_small = ImageFont.truetype(FONT_R, 19)
        f_pts   = ImageFont.truetype(FONT,   26)
        f_day   = ImageFont.truetype(FONT_R, 16)
        f_label = ImageFont.truetype(FONT_R, 16)
    except Exception:
        f_title = f_sub = f_rank = f_name = f_small = f_pts = f_day = f_label = ImageFont.load_default()

    # ── HEADER ──
    for y in range(HDR_H):
        t = y / HDR_H
        draw.line([(0,y),(W,y)], fill=(int(12+t*8), int(12+t*8), int(28+t*22)))
    draw.rectangle([(0, HDR_H-3),(W, HDR_H)], fill=(200,160,0))
    draw.text((W//2, 68),  "REYTING  TOP-10",              font=f_title, fill=(255,215,0),   anchor="mm")
    tw = int(f_title.getlength("REYTING  TOP-10"))
    draw.rectangle([(W//2-tw//2, 92),(W//2+tw//2, 95)], fill=(180,140,0))
    draw.text((W//2, 128), "Super Habits Bot  •  @Super_habits_bot", font=f_sub, fill=(120,120,165), anchor="mm")

    # Ustun sarlavhalari
    draw.text((90,  153), "O'RIN / ISM", font=f_label, fill=(70,70,105), anchor="lm")
    draw.text((560, 153), "7 KUN",       font=f_label, fill=(70,70,105), anchor="lm")
    draw.text((930, 153), "BALL",        font=f_label, fill=(70,70,105), anchor="rm")

    # 7 kunlik sana sarlavhalari
    tz_uz = timezone(timedelta(hours=5))
    today = datetime.now(tz_uz).date()
    days  = [(today - timedelta(days=6-i)) for i in range(7)]
    days_str = [d.strftime("%d") for d in days]

    GRID_X = 545
    CELL   = 48
    for di, ds in enumerate(days_str):
        cx = GRID_X + di * CELL + CELL // 2
        draw.text((cx, 155), ds, font=f_day, fill=(80,80,115), anchor="mm")

    # ── ROW RANGLAR ──
    top3_bg     = [(40,34,8),   (22,22,44),  (42,26,8)  ]
    top3_accent = [(255,215,0), (180,185,205),(215,130,45)]
    top3_name   = [(255,228,60),(210,210,255),(255,195,120)]
    top3_bar    = [(255,215,0), (150,150,255),(255,140,50)]

    for i,(name,points,jon_val,is_vip,uid_str) in enumerate(top10_data):
        y  = HDR_H + i * ROW_H
        cy = y + ROW_H // 2

        bg = top3_bg[i] if i<3 else ((18,18,30) if i%2==0 else (22,22,34))
        draw.rectangle([(0,y),(W,y+ROW_H)], fill=bg)

        ac = top3_accent[i] if i<3 else (45,55,110)
        draw.rectangle([(0,y),(5,y+ROW_H)], fill=ac)

        # Rank badge
        try:
            f_rn = _tf(FONT, 26 if i==0 else 24 if i<3 else 21)
        except:
            f_rn = f_rank
        if i == 0:
            draw.ellipse([(18,cy-28),(72,cy+28)], fill=(160,120,0))
            draw.ellipse([(22,cy-24),(68,cy+24)], fill=(255,215,0))
            draw.text((45,cy), "1", font=f_rn, fill=(80,50,0), anchor="mm")
        elif i == 1:
            draw.ellipse([(22,cy-24),(68,cy+24)], fill=(130,135,148))
            draw.ellipse([(26,cy-20),(64,cy+20)], fill=(210,215,228))
            draw.text((45,cy), "2", font=f_rn, fill=(50,52,60), anchor="mm")
        elif i == 2:
            draw.ellipse([(22,cy-24),(68,cy+24)], fill=(148,90,28))
            draw.ellipse([(26,cy-20),(64,cy+20)], fill=(220,145,55))
            draw.text((45,cy), "3", font=f_rn, fill=(80,40,8), anchor="mm")
        else:
            draw.ellipse([(26,cy-20),(64,cy+20)], fill=(28,32,55))
            draw.text((45,cy), str(i+1), font=f_rn, fill=(80,110,200), anchor="mm")

        # Separator
        draw.rectangle([(82,y+16),(84,y+ROW_H-16)], fill=(35,38,58))

        # Ism
        nc = top3_name[i] if i<3 else (185,188,215)
        display = name[:14]
        draw.text((96, cy-12), display, font=f_name, fill=nc, anchor="lm")

        # VIP
        if is_vip:
            nx = 96 + int(f_name.getlength(display)) + 12
            s  = 8
            draw.polygon([(nx,cy-20),(nx+s,cy-12),(nx,cy-4),(nx-s,cy-12)], fill=(100,190,255))

        # Jon foizi
        if jon_val>=80:   jc=(245,70,70)
        elif jon_val>=50: jc=(245,148,40)
        elif jon_val>=20: jc=(240,205,40)
        else:             jc=(100,100,100)
        draw.ellipse([(96,cy+10),(106,cy+20)], fill=jc)
        draw.text((112, cy+21), f"{jon_val}%", font=f_small, fill=jc, anchor="lm")

        # ── 7 KUNLIK GRID ──
        users_all = load_all_users(force=True)
        udata     = users_all.get(str(uid_str), {})
        done_log  = udata.get("done_log", {})

        for di, d in enumerate(days):
            cx   = GRID_X + di * CELL + CELL // 2
            ds   = d.strftime("%Y-%m-%d")
            r    = 16
            if ds > today.strftime("%Y-%m-%d"):
                # Kelmagan kun — bo'sh
                draw.ellipse([(cx-r,cy-r),(cx+r,cy+r)], fill=(30,30,48))
            elif done_log.get(ds):
                # Bajarilgan — yashil
                draw.ellipse([(cx-r,cy-r),(cx+r,cy+r)], fill=(20,160,80))
                draw.ellipse([(cx-r+2,cy-r+2),(cx+r-2,cy-r+2+8)], fill=(40,200,110))
            else:
                # Bajarilmagan — qizil
                draw.ellipse([(cx-r,cy-r),(cx+r,cy+r)], fill=(180,40,40))
                draw.ellipse([(cx-r+2,cy-r+2),(cx+r-2,cy-r+2+8)], fill=(220,70,70))

        # Ball
        draw.text((932, cy-12), f"{points}", font=f_pts,   fill=(220,220,242), anchor="rm")
        draw.text((932, cy+10), "ball",      font=f_small, fill=(95,95,132),   anchor="rm")

        # Row chiziq
        draw.rectangle([(5,y+ROW_H),(W-5,y+ROW_H+1)], fill=(25,25,40))

    # ── LEGEND ──
    fy = HDR_H + 10 * ROW_H + 5
    draw.rectangle([(0,fy),(W,H)], fill=(14,14,24))
    draw.rectangle([(0,fy),(W,fy+2)], fill=(140,110,0))

    lx = 60
    ly = fy + FTR_H // 2
    draw.ellipse([(lx-8,ly-8),(lx+8,ly+8)], fill=(20,160,80))
    draw.text((lx+14, ly+1), "Bajarildi", font=f_label, fill=(100,180,120), anchor="lm")
    draw.ellipse([(lx+130-8,ly-8),(lx+130+8,ly+8)], fill=(180,40,40))
    draw.text((lx+144, ly+1), "Bajarilmadi", font=f_label, fill=(180,100,100), anchor="lm")
    draw.ellipse([(lx+270-8,ly-8),(lx+270+8,ly+8)], fill=(30,30,48))
    draw.text((lx+284, ly+1), "Ma'lumot yo'q", font=f_label, fill=(80,80,110), anchor="lm")

    draw.text((W-60, ly+1), "Bugun yangilangan", font=f_label, fill=(70,70,105), anchor="rm")

    buf = io.BytesIO()
    buf.name = "reyting.png"
    img.save(buf, format="PNG", optimize=False, compress_level=1)
    buf.seek(0)
    return buf
def _tf(path, size):
    """Font topish - har xil serverlarda ishlaydi"""
    import os
    bold_fallbacks = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
    ]
    regular_fallbacks = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
    ]
    candidates = [path] if path else []
    for fp in bold_fallbacks + regular_fallbacks:
        if fp not in candidates:
            candidates.append(fp)
    for fp in candidates:
        if fp and os.path.exists(fp):
            try: return ImageFont.truetype(fp, size)
            except: continue
    return ImageFont.load_default()


def generate_rating_grid(top10_users, all_users):
    """
    top10_users: [(name, points, username, user_id), ...]
    all_users:   {user_id: udata, ...}
    Returns: BytesIO rasm
    """
    from datetime import timezone, timedelta
    tz_uz     = timezone(timedelta(hours=5))
    today_dt  = datetime.now(tz_uz)
    today_str = today_dt.strftime("%Y-%m-%d")
    days      = [(today_dt - timedelta(days=6-i)).strftime("%Y-%m-%d") for i in range(7)]
    day_lbls  = [(today_dt - timedelta(days=6-i)).strftime("%d") for i in range(7)]

    # Font — _tf() barcha serverlarda ishlaydi (fallback bilan)
    FB = None  # bold
    FR = None  # regular
    for p in ["/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
              "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf"]:
        if os.path.exists(p): FB = p; break
    for p in ["/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
              "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf"]:
        if os.path.exists(p): FR = p; break

    def _f(path, size):
        if path:
            try: return ImageFont.truetype(path, size)
            except: pass
        return ImageFont.load_default()

    # O'lchamlar
    W       = 780
    ROW_H   = 72
    HDR_H   = 108
    FTR_H   = 48
    COL_W   = 56
    NAME_W  = 240
    PAD_L   = 16
    CELL_R  = 22
    ROWS    = len(top10_users)
    H       = HDR_H + ROW_H * ROWS + FTR_H

    F_TITLE = _f(FB, 28)
    F_SUB   = _f(FR, 16)
    F_NAME  = _f(FB, 22)
    F_PTS   = _f(FR, 15)
    F_RANK  = _f(FB, 20)
    F_DAY   = _f(FR, 14)
    F_LEG   = _f(FR, 14)

    img  = Image.new("RGB", (W, H), (13, 13, 22))
    draw = ImageDraw.Draw(img)

    # Header
    for y in range(HDR_H):
        t = y / HDR_H
        r = int(13 + t * 8); b = int(22 + t * 16)
        draw.line([(0,y),(W,y)], fill=(r, r, b))
    draw.rectangle([(0, HDR_H-2),(W, HDR_H)], fill=(180,140,0))
    draw.text((W//2, int(HDR_H*0.38)), "TOP-10  •  7 KUNLIK FAOLLIK",
              font=F_TITLE, fill=(255,215,0), anchor="mm")
    draw.text((W//2, int(HDR_H*0.72)), "Super Habits Bot  •  @Super_habits_bot",
              font=F_SUB, fill=(120,120,165), anchor="mm")

    oy_uzb = ["","Yan","Fev","Mar","Apr","May","Iyn","Iyl","Avg","Sen","Okt","Noy","Dek"]
    for j in range(7):
        cx     = PAD_L + NAME_W + j * COL_W + COL_W // 2
        dt_obj = today_dt - timedelta(days=6-j)
        draw.text((cx, HDR_H - 10), day_lbls[j], font=F_DAY, fill=(180,180,210), anchor="mb")
        if j == 0 or dt_obj.day == 1:
            draw.text((cx, HDR_H - 26), oy_uzb[dt_obj.month], font=F_DAY, fill=(100,100,145), anchor="mb")

    rank_colors = [(255,215,0),(200,205,220),(215,135,55)] + [(80,110,195)]*7
    bg_colors   = [(38,34,10),(20,20,34),(24,24,40),(20,20,34),(24,24,40),
                   (20,20,34),(24,24,40),(20,20,34),(24,24,40),(20,20,34)]

    for i, (name, points, username, target_uid) in enumerate(top10_users):
        y  = HDR_H + i * ROW_H
        cy = y + ROW_H // 2
        rc = rank_colors[i]
        draw.rectangle([(0,y),(W, y+ROW_H)], fill=bg_colors[i])
        draw.rectangle([(0,y),(4, y+ROW_H)], fill=rc)

        rr = ROW_H // 2 - 8
        draw.ellipse([(PAD_L+2, cy-rr),(PAD_L+2+rr*2, cy+rr)], fill=(24,28,52))
        draw.text((PAD_L+2+rr, cy), str(i+1), font=F_RANK, fill=rc, anchor="mm")

        tx = PAD_L + 2 + rr*2 + 10
        draw.text((tx, cy - 12), name[:15], font=F_NAME, fill=(215,215,245), anchor="lm")
        draw.text((tx, cy + 12), f"{points} ball", font=F_PTS, fill=(110,110,155), anchor="lm")

        udata     = all_users.get(str(target_uid), {})
        done_log  = udata.get("done_log", {})
        bot_start = min(done_log.keys()) if done_log else today_str

        for j, dstr in enumerate(days):
            cx = PAD_L + NAME_W + j * COL_W + COL_W // 2
            r  = CELL_R
            if dstr > today_str or dstr < bot_start:
                draw.ellipse([(cx-r,cy-r),(cx+r,cy+r)], outline=(45,45,68), width=2)
            elif done_log.get(dstr):
                draw.ellipse([(cx-r,cy-r),(cx+r,cy+r)], fill=(22,145,62))
                draw.ellipse([(cx-r+4,cy-r+4),(cx+r-4,cy+r-4)], fill=(40,200,82))
            else:
                draw.ellipse([(cx-r,cy-r),(cx+r,cy+r)], fill=(145,25,25))
                draw.ellipse([(cx-r+4,cy-r+4),(cx+r-4,cy+r-4)], fill=(195,48,48))

        draw.rectangle([(4,y+ROW_H-1),(W-4, y+ROW_H)], fill=(28,28,44))

    fy = HDR_H + ROWS * ROW_H
    draw.rectangle([(0,fy),(W,H)], fill=(14,14,24))
    draw.rectangle([(0,fy),(W,fy+2)], fill=(120,95,0))
    lx = PAD_L + 8; ly = fy + FTR_H // 2; r2 = 8
    draw.ellipse([(lx,       ly-r2),(lx+r2*2,       ly+r2)], fill=(40,200,82))
    draw.text((lx+r2*2+6,         ly), "Bajarildi",      font=F_LEG, fill=(150,150,180), anchor="lm")
    draw.ellipse([(lx+130,   ly-r2),(lx+130+r2*2,   ly+r2)], fill=(195,48,48))
    draw.text((lx+130+r2*2+6,     ly), "Bajarilmadi",    font=F_LEG, fill=(150,150,180), anchor="lm")
    draw.ellipse([(lx+280,   ly-r2),(lx+280+r2*2,   ly+r2)], outline=(45,45,68), width=2)
    draw.text((lx+280+r2*2+6,     ly), "Ma'lumot yo'q", font=F_LEG, fill=(95,95,125), anchor="lm")

    buf = io.BytesIO()
    buf.name = "reyting.png"
    img.save(buf, format="PNG", optimize=False, compress_level=1)
    buf.seek(0)
    return buf

def show_rating(uid):
    from datetime import timezone, timedelta
    users   = load_all_users(force=True)
    ranking = []
    for user_id, udata in users.items():
        ranking.append((
            udata.get("name", "?"),
            udata.get("points", 0),
            udata.get("username", ""),
            user_id
        ))
    ranking.sort(key=lambda x: x[1], reverse=True)
    top10  = ranking[:10]
    kb     = InlineKeyboardMarkup()
    webapp_url = os.environ.get("WEBAPP_URL", "")
    if webapp_url:
        from telebot.types import WebAppInfo
        kb.add(InlineKeyboardButton("🌐 To'liq ko'rish", web_app=WebAppInfo(url=webapp_url)))
    kb.add(cBtn(T(uid, "btn_home"), "menu_main", "primary"))
    u = load_user(uid)
    if not top10:
        sent = bot.send_message(uid, T(uid, "rating_empty"), parse_mode="Markdown", reply_markup=kb)
        u["main_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    medals  = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    text    = "🏆 *Reyting — Top 10*\n" + "▬" * 12 + "\n\n"
    for i, (name, points, username, target_uid) in enumerate(top10):
        udata   = users.get(str(target_uid), {})
        jon_val = max(0, min(100, udata.get("jon", 100)))
        je      = "❤️" if jon_val>=80 else "🧡" if jon_val>=50 else "💛" if jon_val>=20 else "🖤"
        vip_b   = " 💎" if udata.get("is_vip") else ""
        uname   = username.lstrip("@") if username and username != "—" else ""
        link    = f"[{name}](https://t.me/{uname})" if uname else f"[{name}](tg://user?id={target_uid})"
        text   += f"{medals[i]} {link}{vip_b} — *{points}* ball  {je} {jon_val}%\n"

    sent = bot.send_message(uid, text, parse_mode="Markdown", reply_markup=kb,
                            disable_web_page_preview=True)
    u["main_msg_id"] = sent.message_id
    save_user(uid, u)


# ============================================================
#  STATISTIKA
# ============================================================
def show_stats(uid, page=1):
    u      = load_user(uid)
    habits = u.get("habits", [])
    if not habits:
        send_main_menu(uid, T(uid, "no_stats"))
        return
    total_points = u.get("points", 0)
    per_page     = 5
    total_pages  = (len(habits) + per_page - 1) // per_page
    page         = max(1, min(page, total_pages))
    page_habits  = habits[(page - 1) * per_page : page * per_page]

    text  = T(uid, "stats_title", page=page, total=total_pages) + "\n"
    text += "▬" * 16 + "\n"
    text += T(uid, "stats_ball", ball=total_points) + "\n"
    text += T(uid, "stats_rank", rank=get_rank(uid, total_points)) + "\n"
    text += "▬" * 16 + "\n\n"

    for h in page_habits:
        streak  = h.get("streak", 0)
        total   = h.get("total_done", 0)
        started = h.get("started_at", "—")
        if streak >= 30:   medal = "🥇"
        elif streak >= 14: medal = "🥈"
        elif streak >= 7:  medal = "🥉"
        else:              medal = "🌱"
        text += f"{medal} *{h['name']}*\n"
        text += "   " + T(uid, "stats_time",   time=h.get("time","—")) + "\n"
        text += "   " + T(uid, "stats_streak", streak=streak) + "\n"
        text += "   " + T(uid, "stats_done",   n=total) + "\n"
        text += "   " + T(uid, "stats_missed", n=h.get("total_missed",0)) + "\n"
        text += f"   *📅 Boshlangan:* {started}\n\n"

    kb_stats = InlineKeyboardMarkup()
    nav_row  = []
    if page > 1:
        nav_row.append(cBtn(T(uid, "nav_prev", n=page-1), f"stats_page_{page-1}", "primary"))
    if page < total_pages:
        nav_row.append(cBtn(T(uid, "nav_next", n=page+1), f"stats_page_{page+1}", "primary"))
    if nav_row:
        kb_stats.row(*nav_row)
    kb_stats.add(InlineKeyboardButton("📅 Haftalik hisobotlar", callback_data="weekly_reports_list"))
    kb_stats.add(InlineKeyboardButton("📆 Oylik hisobotlar",    callback_data="monthly_reports_list"))
    kb_stats.add(InlineKeyboardButton("🗓 Yillik hisobotlar",   callback_data="yearly_reports_list"))
    kb_stats.add(cBtn(T(uid, "btn_home"), "menu_main", "primary"))
    sent = bot.send_message(uid, text, parse_mode="Markdown", reply_markup=kb_stats)
    u["main_msg_id"] = sent.message_id
    save_user(uid, u)

# ============================================================
#  HAFTALIK HISOBOT
# ============================================================
def build_weekly_report_text(uid, report):
    week_label   = report.get("week_label", "—")
    done_pct     = report.get("done_pct", 0)
    jon_start    = report.get("jon_start", 100)
    jon_end      = report.get("jon_end", 100)
    jon_change   = round(jon_end - jon_start, 1)
    jon_sign     = "+" if jon_change >= 0 else ""
    best_streak  = report.get("best_streak", 0)
    balls_earned = report.get("balls_earned", 0)
    best_habit   = report.get("best_habit", "—")
    worst_habit  = report.get("worst_habit", "—")

    if done_pct >= 80:   grade = "🏆 Ajoyib hafta!"
    elif done_pct >= 60: grade = "✅ Yaxshi hafta"
    elif done_pct >= 40: grade = "💪 O'rtacha hafta"
    else:                grade = "⚠️ Qiyin hafta"

    if jon_end >= 80:   je = "❤️"
    elif jon_end >= 50: je = "🧡"
    elif jon_end >= 20: je = "💛"
    else:               je = "🖤"

    text  = f"📅 *{week_label}*\n"
    text += "▬" * 16 + "\n\n"
    text += f"{grade}\n\n"
    text += f"*🎯 Bajarildi:* {done_pct}%\n"
    text += f"*{je} Jon:* {jon_start}% → {jon_end}% ({jon_sign}{jon_change}%)\n"
    text += f"*🔥 Eng uzun streak:* {best_streak} kun\n"
    best_day = report.get("best_day", "—")
    text += f"*⭐ Yig'ilgan ball:* +{balls_earned}\n"
    text += f"*📆 Eng faol kun:* {best_day}\n\n"
    text += "▬" * 16 + "\n"
    text += f"*🏆 Eng yaxshi odat:* {best_habit}\n"
    text += f"*⚠️ Eng kam bajarilgan:* {worst_habit}\n"
    return text

def send_weekly_reports():
    from datetime import timezone, timedelta
    tz_uz    = timezone(timedelta(hours=5))
    now      = datetime.now(tz_uz)
    today    = now.date()
    days_since_monday = today.weekday()
    week_start = today - timedelta(days=days_since_monday + 7)
    week_end   = week_start + timedelta(days=6)
    week_label = f"{week_start.strftime('%d.%m')} – {week_end.strftime('%d.%m.%Y')}"
    users = load_all_users(force=True)
    print(f"[weekly_report] {len(users)} foydalanuvchiga hisobot yuborilmoqda...")
    for uid_str, udata in users.items():
        try:
            habits = udata.get("habits", [])
            if not habits:
                continue
            uid_int  = int(uid_str)
            jon_end  = round(udata.get("jon", 100))
            # O'tgan hafta boshlanish jonini history dan topamiz
            _h_hist = udata.get("history", {})
            _w_jon_vals = []
            for _wi in range(7, 0, -1):
                _wd = (now - timedelta(days=_wi)).strftime("%Y-%m-%d")
                _wd_data = _h_hist.get(_wd, {})
                if "jon" in _wd_data:
                    _w_jon_vals.append(_wd_data["jon"])
            jon_start = round(_w_jon_vals[0]) if _w_jon_vals else max(0, min(100, round(jon_end - (jon_end - 50) * 0.1)))
            # O'tgan 7 kunni history dan hisoblash
            total_possible = 0
            total_done_w   = 0
            habit_scores   = []
            best_streak    = 0
            best_day_count = 0
            best_day_label = "—"
            _day_names = ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"]
            for h in habits:
                rep  = h.get("repeat_count", 1) if h.get("type") == "repeat" else 1
                done_w = 0
                for _wi in range(6, -1, -1):
                    _wd = (now - timedelta(days=_wi)).strftime("%Y-%m-%d")
                    if _h_hist.get(_wd, {}).get("habits", {}).get(h["id"]):
                        done_w += 1
                poss = rep * 7
                total_possible += poss
                total_done_w   += done_w
                score = round(done_w / poss * 100) if poss else 0
                habit_scores.append((h["name"], score))
                if h.get("streak", 0) > best_streak:
                    best_streak = h.get("streak", 0)
            # Eng faol kun — o'tgan 7 kundagi eng ko'p odat bajarilgan kun
            for _wi in range(6, -1, -1):
                _wd = (now - timedelta(days=_wi)).strftime("%Y-%m-%d")
                _d_done = _h_hist.get(_wd, {}).get("done", 0)
                if _d_done > best_day_count:
                    best_day_count = _d_done
                    _wd_obj = now - timedelta(days=_wi)
                    best_day_label = f"{_day_names[_wd_obj.weekday()]} ({_wd_obj.strftime('%d.%m')})"
            done_pct     = round(total_done_w / total_possible * 100) if total_possible else 0
            balls_earned = total_done_w * 5
            habit_scores.sort(key=lambda x: x[1], reverse=True)
            best_habit  = habit_scores[0][0]  if habit_scores else "—"
            worst_habit = habit_scores[-1][0] if habit_scores else "—"
            report = {
                "week_label":   week_label,
                "week_start":   str(week_start),
                "done_pct":     done_pct,
                "jon_start":    jon_start,
                "jon_end":      jon_end,
                "best_streak":  best_streak,
                "balls_earned": balls_earned,
                "best_habit":   best_habit,
                "worst_habit":  worst_habit,
                "best_day":     best_day_label,
            }
            try:
                # BUG FIX: _id har doim string saqlanadi, uid_int emas uid_str ishlatish kerak
                mongo_col.update_one(
                    {"_id": uid_str},
                    {"$push": {"weekly_reports": report}},
                    upsert=False
                )
            except Exception as e:
                print(f"[weekly_report] MongoDB saqlash xato {uid_str}: {e}")
            text = "📊 *Haftalik hisobotingiz tayyor!*\n\n"
            text += build_weekly_report_text(uid_int, report)
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"weekly_confirm_{uid_str}"))
            bot.send_message(uid_int, text, parse_mode="Markdown", reply_markup=kb)
            time.sleep(0.05)
        except Exception as e:
            print(f"[weekly_report] Xato {uid_str}: {e}")
    print("[weekly_report] Yuborildi.")

# ============================================================
#  ODAT O'CHIRISH
# ============================================================
def delete_habit_menu(uid):
    u      = load_user(uid)
    habits = u.get("habits", [])
    if not habits:
        _s = send_message_colored(uid, T(uid, "no_delete"), main_menu_dict(uid))
        if _s is None:
            bot.send_message(uid, T(uid, "no_delete"), reply_markup=main_menu(uid))
        return
    # Vaqt bo'yicha tartiblash
    def _sort_key(h):
        t = h.get("time", "23:59")
        try:
            hh, mm = t.split(":")
            return int(hh) * 60 + int(mm)
        except:
            return 9999
    sorted_habits = sorted(habits, key=_sort_key)
    kb = InlineKeyboardMarkup()
    for h in sorted_habits:
        kb.add(InlineKeyboardButton(f"🗑 {h['name']} ({h['time']})", callback_data=f"delete_{h['id']}"))
    kb.row(
        cBtn(T(uid, "btn_home"), "menu_main", "primary")
    )
    sent = bot.send_message(uid, T(uid, "del_which_habit"), parse_mode="Markdown", reply_markup=kb)
    u["main_msg_id"] = sent.message_id
    save_user(uid, u)

# ============================================================
#  CALLBACK HANDLER
# ============================================================
@bot.callback_query_handler(func=lambda c: True)
def callback_handler(call):
    uid   = call.from_user.id
    cdata = call.data
    u     = load_user(uid)

    # Kechki eslatma — "Tushundim" tugmasi
    if cdata == "evening_dismiss":
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

    if cdata == "admin_test_onboard":
        if uid != ADMIN_ID:
            return
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        send_main_menu(uid)
        return

    if cdata == "admin_close":
        if uid != ADMIN_ID:
            return
        u["state"] = None
        save_user(uid, u)
        bot.answer_callback_query(call.id)
        try:
            bot.delete_message(uid, call.message.message_id)
        except Exception:
            pass
        send_main_menu(uid)
        return

    if cdata == "bc_user_ack":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        return

    if cdata == "bc_confirm":
        if uid != ADMIN_ID:
            return
        bot.answer_callback_query(call.id, "✅ Tasdiqlandi")
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        try: bot.send_message(uid, "🛠 *Admin panel*", parse_mode="Markdown", reply_markup=admin_menu())
        except: pass
        return

    if cdata == "bc_detail":
        if uid != ADMIN_ID:
            return
        failed_list = u.get("bc_failed_list", [])
        if not failed_list:
            bot.answer_callback_query(call.id, "Bloklagan foydalanuvchi yo'q", show_alert=True)
            return
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
        return

    if cdata == "bc_detail_confirm":
        if uid != ADMIN_ID:
            return
        bot.answer_callback_query(call.id, "✅ Tasdiqlandi")
        u.pop("bc_failed_list", None)
        save_user(uid, u)
        def del_bc_detail(chat_id, mid):
            time.sleep(5)
            try: bot.delete_message(chat_id, mid)
            except: pass
        threading.Thread(target=del_bc_detail, args=(uid, call.message.message_id), daemon=True).start()
        return

    if cdata == "admin_cancel":
        if uid != ADMIN_ID:
            return
        u["state"] = None
        save_user(uid, u)
        bot.answer_callback_query(call.id, "Bekor qilindi")
        try:
            bot.delete_message(uid, call.message.message_id)
        except Exception:
            pass
        bot.send_message(uid, "🛠 *Admin panel | Maxfiy va muhim qism*", parse_mode="Markdown", reply_markup=admin_menu())
        return

    if cdata == "admin_notify_update":
        if uid != ADMIN_ID:
            return
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
        return

    if cdata == "admin_notify_confirm":
        if uid != ADMIN_ID:
            return
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
        return

    if cdata == "admin_give_points":
        if uid != ADMIN_ID:
            return
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
        return

    if cdata == "admin_broadcast":
        if uid != ADMIN_ID:
            return
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        bot.send_message(uid, "📢 *Habar yuborish*\n\nQayerga yubormoqchisiz?", parse_mode="Markdown", reply_markup=admin_broadcast_menu())
        return

    if cdata in ("admin_bc_private", "admin_bc_groups", "admin_bc_all"):
        if uid != ADMIN_ID:
            return
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
        return

    if cdata == "admin_users" or cdata.startswith("admin_users_page_"):
        if uid != ADMIN_ID:
            return
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        users = load_all_users(force=True)
        if not users:
            bot.send_message(uid, "👥 Foydalanuvchilar yo'q.", reply_markup=admin_menu())
            return
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
        return

    if cdata == "admin_channel":
        if uid != ADMIN_ID:
            return
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
        return

    if cdata.startswith("admin_ch_edit_"):
        if uid != ADMIN_ID:
            return
        slot = int(cdata[14:])
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        u["state"] = f"admin_waiting_channel_{slot}"
        kb2 = InlineKeyboardMarkup()
        kb2.add(cBtn("❌ Bekor qilish", "admin_cancel", "danger"))
        sent_ch = bot.send_message(
            uid,
            f"🔗 {slot}-kanal username yozing:\n\n_Masalan: @mening_kanalim_",
            parse_mode="Markdown",
            reply_markup=kb2
        )
        u["channel_msg_id"] = sent_ch.message_id
        save_user(uid, u)
        return

    if cdata.startswith("admin_ch_del_"):
        if uid != ADMIN_ID:
            return
        slot = int(cdata[13:])
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        settings = load_settings()
        settings.pop(f"required_channel_{slot}", None)
        settings.pop(f"required_channel_title_{slot}", None)
        save_settings(settings)
        bot.send_message(uid, f"✅ {slot}-kanal o'chirildi.", reply_markup=admin_menu())
        return

    if cdata == "admin_stats":
        if uid != ADMIN_ID:
            return
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        bot.send_message(uid, "📈 *Statistika — davr tanlang:*", parse_mode="Markdown", reply_markup=admin_stats_period_menu())
        return

    if cdata.startswith("admin_stats_"):
        if uid != ADMIN_ID:
            return
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
        return

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
        return

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
        return

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
        return

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
        return

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
            return
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
        return

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
        return

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
        return

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
            return
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
        return

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
        return

    # --- Vaqtni tahrirlash boshlash ---
    if cdata.startswith("edit_htime_start_"):
        habit_id = cdata[17:]
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        h = next((x for x in u.get("habits", []) if x["id"] == habit_id), None)
        if not h:
            send_main_menu(uid)
            return
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
        return

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
            return
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
        return

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
        return

    if cdata.startswith("rename_habit_"):
        habit_id = cdata[len("rename_habit_"):]
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        # Odatni topib nomini saqlash
        habit = next((h for h in u.get("habits", []) if h["id"] == habit_id), None)
        if not habit:
            send_main_menu(uid)
            return
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
        return

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
        return

    if cdata == "menu_add":
        # BUG FIX: Limit 10 emas 15 bo'lishi kerak (LANGS da "15 ta" deyilgan)
        if len(u.get("habits", [])) >= 15:
            bot.answer_callback_query(call.id)
            sent_limit = bot.send_message(
                uid,
                T(uid, "limit"),
                parse_mode="Markdown"
            )
            def del_limit(chat_id, msg_id):
                time.sleep(3)
                try: bot.delete_message(chat_id, msg_id)
                except: pass
            threading.Thread(target=del_limit, args=(uid, sent_limit.message_id), daemon=True).start()
            send_main_menu(uid)
            return
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        # Odat turini tanlash
        kb_type = InlineKeyboardMarkup()
        kb_type.row(
            InlineKeyboardButton("📌 Oddiy",          callback_data="habit_type_simple"),
            InlineKeyboardButton("🔁 Takrorlanuvchi", callback_data="habit_type_repeat")
        )
        kb_type.add(cBtn(T(uid, "btn_cancel"), "cancel", "danger"))
        sent = bot.send_message(
            uid,
            "📋 *Odat turini tanlang:*\n\n"
            "📌 *Oddiy* — kuniga 1 marta\n"
            "🔁 *Takrorlanuvchi* — kuniga bir necha marta (masalan: 5 vaqt namoz)",
            parse_mode="Markdown", reply_markup=kb_type
        )
        u["temp_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    if cdata == "habit_type_simple":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        u["state"] = "waiting_habit_name"
        u["temp_habit"] = {"type": "simple"}
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.add(cBtn(T(uid, "btn_cancel"), "cancel", "danger"))
        sent = bot.send_message(uid, T(uid, "ask_habit_name"), parse_mode="Markdown", reply_markup=cancel_kb)
        u["temp_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    if cdata == "habit_type_repeat":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        # Avval necha marta takrorlanishi so'ralinsin
        u["temp_habit"] = {"type": "repeat"}
        u["state"] = "waiting_repeat_count"
        save_user(uid, u)
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.add(cBtn(T(uid, "btn_cancel"), "cancel", "danger"))
        sent = bot.send_message(
            uid,
            "🔁 *Takrorlanuvchi odat*\n\n"
            "Kuniga necha marta bajarasiz?\n"
            "_Masalan: 2, 3, 5_",
            parse_mode="Markdown", reply_markup=cancel_kb
        )
        u["temp_msg_id"] = sent.message_id
        save_user(uid, u)
        return



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
        return

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
        return

    if cdata.startswith("shield_use_"):
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
                    parse_mode="Markdown"
                )
            except Exception:
                pass
        else:
            try: bot.delete_message(uid, call.message.message_id)
            except: pass
        return

    if cdata.startswith("shield_skip_"):
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
                parse_mode="Markdown"
            )
        except Exception:
            pass
        return

    if cdata.startswith("weekly_confirm_"):
        bot.answer_callback_query(call.id, "✅ Tasdiqlandi!")
        try:
            bot.delete_message(uid, call.message.message_id)
        except Exception:
            pass
        return

    if cdata == "weekly_reports_list":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        reports = u.get("weekly_reports", [])
        if not reports:
            sent_e = bot.send_message(
                uid,
                "📅 *Haftalik hisobotlar*\n\nHali hisobot yo'q.\nHar dushanba avtomatik yuboriladi!",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup().add(cBtn(T(uid, "btn_home"), "menu_main", "primary"))
            )
            u["main_msg_id"] = sent_e.message_id
            save_user(uid, u)
            return
        # Ro'yxat — oxiridan boshiga (eng yangi avval)
        kb_wr = InlineKeyboardMarkup()
        for i, rep in enumerate(reversed(reports)):
            label = rep.get("week_label", f"{i+1}-hafta")
            pct   = rep.get("done_pct", 0)
            if pct >= 80:   emoji = "🏆"
            elif pct >= 60: emoji = "✅"
            elif pct >= 40: emoji = "💪"
            else:           emoji = "⚠️"
            kb_wr.add(InlineKeyboardButton(
                f"{emoji} {label} — {pct}%",
                callback_data=f"weekly_view_{len(reports)-1-i}"
            ))
        kb_wr.add(cBtn(T(uid, "btn_home"), "menu_main", "primary"))
        sent_wr = bot.send_message(
            uid,
            "📅 *Haftalik hisobotlar arxivi*\n\nQaysi haftani ko'rmoqchisiz?",
            parse_mode="Markdown",
            reply_markup=kb_wr
        )
        u["main_msg_id"] = sent_wr.message_id
        save_user(uid, u)
        return

    if cdata.startswith("weekly_view_"):
        idx_r = int(cdata[len("weekly_view_"):])
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        reports = u.get("weekly_reports", [])
        if idx_r < 0 or idx_r >= len(reports):
            send_main_menu(uid)
            return
        report = reports[idx_r]
        text   = build_weekly_report_text(uid, report)
        kb_back = InlineKeyboardMarkup()
        kb_back.row(
            cBtn("⬅️ Orqaga", "weekly_reports_list", "primary"),
            cBtn(T(uid, "btn_home"), "menu_main", "primary")
        )
        sent_v = bot.send_message(uid, text, parse_mode="Markdown", reply_markup=kb_back)
        u["main_msg_id"] = sent_v.message_id
        save_user(uid, u)
        return


    if cdata == "monthly_reports_list":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        reports = u.get("monthly_reports", [])
        if not reports:
            sent_e = bot.send_message(
                uid,
                "📆 *Oylik hisobotlar*\n\nHali hisobot yo'q.\nHar oyning 1-kuni avtomatik yuboriladi!",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup().add(cBtn(T(uid, "btn_home"), "menu_main", "primary"))
            )
            u["main_msg_id"] = sent_e.message_id
            save_user(uid, u)
            return
        kb_mr = InlineKeyboardMarkup()
        for i, rep in enumerate(reversed(reports)):
            label = rep.get("month_label", f"{i+1}-oy")
            pct   = rep.get("done_pct", 0)
            if pct >= 80:   emoji = "🏆"
            elif pct >= 60: emoji = "✅"
            elif pct >= 40: emoji = "💪"
            else:           emoji = "⚠️"
            kb_mr.add(InlineKeyboardButton(
                f"{emoji} {label} — {pct}%",
                callback_data=f"monthly_view_{len(reports)-1-i}"
            ))
        kb_mr.add(cBtn(T(uid, "btn_home"), "menu_main", "primary"))
        sent_mr = bot.send_message(
            uid,
            "📆 *Oylik hisobotlar arxivi*\n\nQaysi oyni ko'rmoqchisiz?",
            parse_mode="Markdown",
            reply_markup=kb_mr
        )
        u["main_msg_id"] = sent_mr.message_id
        save_user(uid, u)
        return

    if cdata.startswith("monthly_view_"):
        idx_m = int(cdata[len("monthly_view_"):])
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        reports = u.get("monthly_reports", [])
        if idx_m < 0 or idx_m >= len(reports):
            send_main_menu(uid)
            return
        report = reports[idx_m]
        text   = build_monthly_report_text(uid, report)
        kb_back = InlineKeyboardMarkup()
        kb_back.row(
            cBtn("⬅️ Orqaga", "monthly_reports_list", "primary"),
            cBtn(T(uid, "btn_home"), "menu_main", "primary")
        )
        sent_v = bot.send_message(uid, text, parse_mode="Markdown", reply_markup=kb_back)
        u["main_msg_id"] = sent_v.message_id
        save_user(uid, u)
        return

    if cdata == "yearly_reports_list":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        reports = u.get("yearly_reports", [])
        if not reports:
            sent_e = bot.send_message(
                uid,
                "🗓 *Yillik hisobotlar*\n\nHali hisobot yo'q.\nHar yilning 1-yanvarida avtomatik yuboriladi!",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup().add(cBtn(T(uid, "btn_home"), "menu_main", "primary"))
            )
            u["main_msg_id"] = sent_e.message_id
            save_user(uid, u)
            return
        kb_yr = InlineKeyboardMarkup()
        for i, rep in enumerate(reversed(reports)):
            label = rep.get("year_label", f"{i+1}-yil")
            pct   = rep.get("done_pct", 0)
            if pct >= 80:   emoji = "🏆"
            elif pct >= 60: emoji = "✅"
            elif pct >= 40: emoji = "💪"
            else:           emoji = "⚠️"
            kb_yr.add(InlineKeyboardButton(
                f"{emoji} {label} — {pct}%",
                callback_data=f"yearly_view_{len(reports)-1-i}"
            ))
        kb_yr.add(cBtn(T(uid, "btn_home"), "menu_main", "primary"))
        sent_yr = bot.send_message(
            uid,
            "🗓 *Yillik hisobotlar arxivi*\n\nQaysi yilni ko'rmoqchisiz?",
            parse_mode="Markdown",
            reply_markup=kb_yr
        )
        u["main_msg_id"] = sent_yr.message_id
        save_user(uid, u)
        return

    if cdata.startswith("yearly_view_"):
        idx_y = int(cdata[len("yearly_view_"):])
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        reports = u.get("yearly_reports", [])
        if idx_y < 0 or idx_y >= len(reports):
            send_main_menu(uid)
            return
        report = reports[idx_y]
        text   = build_yearly_report_text(uid, report)
        kb_back = InlineKeyboardMarkup()
        kb_back.row(
            cBtn("⬅️ Orqaga", "yearly_reports_list", "primary"),
            cBtn(T(uid, "btn_home"), "menu_main", "primary")
        )
        sent_v = bot.send_message(uid, text, parse_mode="Markdown", reply_markup=kb_back)
        u["main_msg_id"] = sent_v.message_id
        save_user(uid, u)
        return


    # ── ONBOARDING callbacklar ──
    if cdata == "onboard_start":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        send_onboarding_habit_category(uid)
        return

    if cdata == "onboard_skip":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        u["onboarding"] = False
        save_user(uid, u)
        send_main_menu(uid)
        return

    if cdata.startswith("onboard_cat_"):
        cat = cdata[len("onboard_cat_"):]
        bot.answer_callback_query(call.id)
        if cat == "custom":
            # Foydalanuvchi o'zi yozsin
            try: bot.delete_message(uid, call.message.message_id)
            except: pass
            u["state"] = "onboard_waiting_name"
            save_user(uid, u)
            kb_cancel = InlineKeyboardMarkup()
            kb_cancel.add(InlineKeyboardButton("⏭ O'tkazib yuborish", callback_data="onboard_skip"))
            sent = bot.send_message(
                uid,
                "✏️ *Odatingiz nomini yozing:*\n\n"
                "_Masalan: Ertalab yugurish, Kitob o'qish, Namoz..._",
                parse_mode="Markdown", reply_markup=kb_cancel
            )
            u["main_msg_id"] = sent.message_id
            save_user(uid, u)
        else:
            send_onboarding_examples(uid, cat)
        return

    if cdata.startswith("onboard_habit_"):
        habit_name = cdata[len("onboard_habit_"):]
        bot.answer_callback_query(call.id)
        send_onboarding_time(uid, habit_name)
        return

    if cdata.startswith("onboard_time_"):
        time_val = cdata[len("onboard_time_"):]
        bot.answer_callback_query(call.id)
        if time_val == "custom":
            try: bot.delete_message(uid, call.message.message_id)
            except: pass
            u["state"] = "onboard_waiting_time"
            save_user(uid, u)
            kb_cancel = InlineKeyboardMarkup()
            kb_cancel.add(InlineKeyboardButton("⏭ O'tkazib yuborish", callback_data="onboard_skip"))
            sent = bot.send_message(
                uid,
                "⏰ *Vaqtni kiriting:*\n\n"
                "_Format: HH:MM (masalan: 07:30)_",
                parse_mode="Markdown", reply_markup=kb_cancel
            )
            u["main_msg_id"] = sent.message_id
            save_user(uid, u)
        else:
            habit_name = u.get("temp_onboard_habit", "Odat")
            finish_onboarding(uid, habit_name, time_val)
        return

    if cdata == "menu_list":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        # show_habits = statistika bilan bir xil, send_main_menu ishlatamiz
        u2 = load_user(uid)
        habits = u2.get("habits", [])
        if not habits:
            sent_e = bot.send_message(uid, T(uid, "no_habits"), parse_mode="Markdown",
                                      reply_markup=InlineKeyboardMarkup().add(
                                          cBtn(T(uid, "btn_home"), "menu_main", "primary")))
            u2["main_msg_id"] = sent_e.message_id
            save_user(uid, u2)
            return
        # Barcha odatlarni ro'yxat sifatida ko'rsatish
        today = today_uz5()
        text  = "📋 *Odatlarim ro'yxati*" + "\n" + "▬" * 16 + "\n\n"
        def _sk(h):
            t = h.get("time", "23:59")
            try: hh, mm = t.split(":"); return int(hh)*60+int(mm)
            except: return 9999
        for h in sorted(habits, key=_sk):
            hab_type  = h.get("type", "simple")
            rep_count = h.get("repeat_count", 1)
            streak    = h.get("streak", 0)
            if hab_type == "repeat":
                done_c  = h.get("done_today_count", 0)
                status  = "☑️" if done_c >= rep_count else f"🔄 {done_c}/{rep_count}"
                times_s = ", ".join(h.get("repeat_times", [h.get("time", "—")]))
                text += f"{status} *{h['name']}*\n   🔁 {times_s} | 🔥 {streak} kun\n\n"
            else:
                is_done = h.get("last_done") == today
                status  = "☑️" if is_done else "⬜"
                time_s  = h.get("time", "vaqtsiz")
                text += f"{status} *{h['name']}*\n   ⏰ {time_s} | 🔥 {streak} kun\n\n"
        kb_list = InlineKeyboardMarkup()
        kb_list.add(cBtn(T(uid, "btn_home"), "menu_main", "primary"))
        sent = bot.send_message(uid, text, parse_mode="Markdown", reply_markup=kb_list)
        u2["main_msg_id"] = sent.message_id
        save_user(uid, u2)
        return

    if cdata == "menu_stats":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        show_stats(uid)
        return

    if cdata.startswith("stats_page_"):
        page = int(cdata[11:])
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        show_stats(uid, page=page)
        return

    if cdata == "menu_delete":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        delete_habit_menu(uid)
        return

    if cdata == "menu_rating":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        show_rating(uid)
        return

    if cdata == "menu_main":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        send_main_menu(uid)
        return

    # ============================================================
    #  2-MENYU (GURUHLAR)
    # ============================================================
    if cdata == "menu2_open":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        send_menu2(uid)
        return

    if cdata == "group_create":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        u["state"] = "group_waiting_name"
        u["temp_group"] = {}
        save_user(uid, u)
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.add(cBtn("⬅️ Orqaga", "menu2_open", "primary"))
        sent = bot.send_message(
            uid,
            "👥 *Yangi guruh yaratish*\n\n"
            "1️⃣ Guruh nomini kiriting:\n"
            "_Masalan: Kitob o'qish klubi_",
            parse_mode="Markdown", reply_markup=cancel_kb
        )
        u["temp_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    if cdata == "group_create_no_time":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        temp = u.get("temp_group", {})
        temp["time"] = "vaqtsiz"
        u["temp_group"] = temp
        u["state"] = None
        save_user(uid, u)
        _save_new_group(uid, u)
        return

    if cdata == "group_delete":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        my_groups = [g for g in u.get("groups", []) if str(g.get("admin_id","")) == str(uid)]
        if not my_groups:
            sent_e = bot.send_message(uid,
                "🗑 *Guruhni o'chirish*\n\nSiz admin bo'lgan guruh yo'q.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup().add(cBtn("⬅️ Orqaga", "menu2_open", "primary"))
            )
            u["main_msg_id"] = sent_e.message_id
            save_user(uid, u)
            return
        kb_del = InlineKeyboardMarkup()
        for g in my_groups:
            kb_del.add(InlineKeyboardButton(
                f"🗑 {g['name']}", callback_data=f"group_delete_confirm_{g['id']}"
            ))
        kb_del.add(cBtn("⬅️ Orqaga", "menu2_open", "primary"))
        sent = bot.send_message(uid,
            "🗑 *Qaysi guruhni o'chirmoqchisiz?*",
            parse_mode="Markdown", reply_markup=kb_del
        )
        u["main_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    if cdata.startswith("group_delete_confirm_"):
        g_id = cdata[len("group_delete_confirm_"):]
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        kb_confirm = InlineKeyboardMarkup()
        kb_confirm.row(
            cBtn("✅ Ha, o'chir", f"group_delete_yes_{g_id}", "danger"),
            cBtn("❌ Yo'q",       "group_delete", "primary")
        )
        bot.send_message(uid,
            "⚠️ *Guruhni o'chirishni tasdiqlaysizmi?*\n\n"
            "Barcha a'zolar guruhdan chiqariladi!",
            parse_mode="Markdown", reply_markup=kb_confirm
        )
        return

    if cdata.startswith("group_delete_yes_"):
        g_id = cdata[len("group_delete_yes_"):]
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        g = load_group(g_id)
        if g and str(g.get("admin_id","")) == str(uid):
            # A'zolarni guruhdan chiqarish
            for member_id in g.get("members", []):
                try:
                    mu = load_user(member_id)
                    mu["groups"] = [x for x in mu.get("groups", []) if x.get("id") != g_id]
                    save_user(member_id, mu)
                    if str(member_id) != str(uid):
                        bot.send_message(int(member_id),
                            f"ℹ️ *{g['name']}* guruhi admin tomonidan o'chirildi.",
                            parse_mode="Markdown", reply_markup=ok_kb()
                        )
                except Exception as _e: print(f"[warn] send_message: {_e}")
            delete_group(g_id)
        send_menu2(uid)
        return

    if cdata == "group_stats":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        groups = u.get("groups", [])
        if not groups:
            sent_e = bot.send_message(uid,
                "📊 *Guruh statistika*\n\nHali hech qanday guruhga a'zo emassiz.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup().add(cBtn("⬅️ Orqaga", "menu2_open", "primary"))
            )
            u["main_msg_id"] = sent_e.message_id
            save_user(uid, u)
            return
        text = "📊 *Guruh statistika*\n\n"
        for g_info in groups:
            g = load_group(g_info["id"])
            if not g: continue
            members   = g.get("members", [])
            streak    = g.get("streak", 0)
            text += f"👥 *{g['name']}*\n"
            text += f"   A'zolar: {len(members)} ta\n"
            text += f"   Odat: {g.get('habit_name','—')}\n"
            text += f"   🔥 Streak: {streak} kun\n\n"
        kb_back = InlineKeyboardMarkup()
        kb_back.add(cBtn("⬅️ Orqaga", "menu2_open", "primary"))
        sent = bot.send_message(uid, text, parse_mode="Markdown", reply_markup=kb_back)
        u["main_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    if cdata == "group_rating":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        groups = u.get("groups", [])
        if not groups:
            sent_e = bot.send_message(uid,
                "🏆 *Guruh reytingi*\n\nHali hech qanday guruhga a'zo emassiz.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup().add(cBtn("⬅️ Orqaga", "menu2_open", "primary"))
            )
            u["main_msg_id"] = sent_e.message_id
            save_user(uid, u)
            return
        # Bir necha guruh bo'lsa — tanlash
        if len(groups) == 1:
            target_g_id = groups[0]["id"]
            bot.answer_callback_query(call.id)
            # To'g'ridan group_rating_show ga o'tish
            g = load_group(target_g_id)
            if not g:
                send_menu2(uid)
                return
            text, kb = _build_group_rating(uid, g, target_g_id, "week")
            sent = bot.send_message(uid, text, parse_mode="Markdown", reply_markup=kb)
            u["main_msg_id"] = sent.message_id
            save_user(uid, u)
        else:
            # Guruhni tanlash menyusi
            kb_sel = InlineKeyboardMarkup()
            for g_info in groups:
                kb_sel.add(InlineKeyboardButton(
                    f"👥 {g_info['name']}", callback_data=f"group_rating_show_{g_info['id']}_week"
                ))
            kb_sel.add(cBtn("⬅️ Orqaga", "menu2_open", "primary"))
            sent = bot.send_message(uid,
                "🏆 *Guruh reytingi*\n\nQaysi guruhni ko'rmoqchisiz?",
                parse_mode="Markdown", reply_markup=kb_sel
            )
            u["main_msg_id"] = sent.message_id
            save_user(uid, u)
        return

    if cdata.startswith("group_rating_show_"):
        # group_rating_show_{g_id}_{period}
        parts  = cdata[len("group_rating_show_"):].rsplit("_", 1)
        g_id   = parts[0]
        period = parts[1] if len(parts) > 1 else "week"
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        g = load_group(g_id)
        if not g:
            send_menu2(uid)
            return
        text, kb = _build_group_rating(uid, g, g_id, period)
        sent = bot.send_message(uid, text, parse_mode="Markdown", reply_markup=kb)
        u["main_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    if cdata.startswith("group_view_"):
        g_id = cdata[len("group_view_"):]
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        g = load_group(g_id)
        if not g:
            send_menu2(uid)
            return
        sent = _send_group_view(uid, u, g, g_id)
        u["main_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    if cdata.startswith("group_done_"):
        # format: group_done_{g_id}_{h_id}
        rest   = cdata[len("group_done_"):]
        parts  = rest.rsplit("_", 1)
        g_id   = parts[0]
        h_id   = parts[1] if len(parts) > 1 else "main"
        g = load_group(g_id)
        if not g:
            bot.answer_callback_query(call.id)
            return
        members = g.get("members", [])
        today   = today_uz5()
        if g.get("done_date") != today:
            g["done_today"] = {}
            g["done_date"]  = today
        done_today = g.get("done_today", {})
        uid_str    = str(uid)
        # done_today: {uid_str: {h_id: True/False}}
        if uid_str not in done_today or not isinstance(done_today[uid_str], dict):
            done_today[uid_str] = {}
        already_done = done_today[uid_str].get(h_id, False)
        if already_done:
            # Toggle: bekor qilish
            bot.answer_callback_query(call.id, "↩️ Bekor qilindi")
            done_today[uid_str][h_id] = False
            g["done_today"] = done_today
            done_log = g.get("member_done_log", {})
            if uid_str in done_log:
                done_log[uid_str].pop(today + "_" + h_id, None)
            g["member_done_log"] = done_log
            save_group(g_id, g)
            # Ball ayirish
            u["points"] = max(0, u.get("points", 0) - 5)
            save_user(uid, u)
            main_msg_id = u.get("main_msg_id")
            if main_msg_id:
                try:
                    edit_message_colored(uid, main_msg_id, build_main_text(uid), main_menu_dict(uid))
                except Exception as _e: print(f"[warn] edit_message: {_e}")
            return
        bot.answer_callback_query(call.id, "✅ Bajarildi!")
        done_today[uid_str][h_id] = True
        g["done_today"] = done_today
        done_count = sum(1 for v in done_today.values() if (v is True or (isinstance(v, dict) and True in v.values())))
        u_name = u.get("name", "Foydalanuvchi")
        all_done = done_count == len(members)
        if all_done:
            # Guruh streaki — faqat bugun birinchi marta all_done bo'lganda +1
            if g.get("streak_date") != today:
                g["streak"]      = g.get("streak", 0) + 1
                g["streak_date"] = today
        # member_done_log: {uid_str: {date_str: True}}
        done_log = g.get("member_done_log", {})
        if uid_str not in done_log:
            done_log[uid_str] = {}
        # Streak faqat bugun BIRINCHI marta bajarilganda oshsin
        already_logged_today = done_log[uid_str].get(today, False)
        done_log[uid_str][today] = True
        g["member_done_log"] = done_log
        # member_streaks: {uid_str: int} — faqat birinchi marta
        if not already_logged_today:
            m_streaks   = g.get("member_streaks", {})
            from datetime import timezone, timedelta as _td
            tz_uz       = timezone(_td(hours=5))
            yesterday_s = (datetime.now(tz_uz) - _td(days=1)).strftime("%Y-%m-%d")
            if done_log[uid_str].get(yesterday_s):
                m_streaks[uid_str] = m_streaks.get(uid_str, 0) + 1
            else:
                m_streaks[uid_str] = 1
            g["member_streaks"] = m_streaks
        save_group(g_id, g)
        # Foydalanuvchiga: ball + streak xabari
        h_name_display = next((h["name"] for h in g.get("habits",[])
                               if h["id"] == h_id), g.get("habit_name","Odat"))
        u["points"] = u.get("points", 0) + 5
        save_user(uid, u)
        m_streak_val = g.get("member_streaks", {}).get(uid_str, 1)
        if m_streak_val >= 30:   s_extra = f"\n🔥 Streak: {m_streak_val} kun 🏆"
        elif m_streak_val >= 14: s_extra = f"\n🔥 Streak: {m_streak_val} kun 🌟"
        elif m_streak_val >= 7:  s_extra = f"\n🔥 Streak: {m_streak_val} kun 🔥"
        else:                    s_extra = f"\n🔥 Streak: {m_streak_val} kun"
        sent_msg = bot.send_message(uid,
            f"*✅ {h_name_display}* — bajarildi! *+5 ⭐ ball*" + s_extra,
            parse_mode="Markdown"
        )
        def del_grp_msg(chat_id, msg_id):
            time.sleep(3)
            try: bot.delete_message(chat_id, msg_id)
            except: pass
        threading.Thread(target=del_grp_msg, args=(uid, sent_msg.message_id), daemon=True).start()
        # Boshqa a'zolarga bildirishnoma
        for mid in members:
            if mid == uid:
                continue
            try:
                if all_done:
                    bot.send_message(mid,
                        f"🎉 *{g['name']}*\n\n"
                        f"Bugun barchangiz bajardingiz!\n"
                        f"🔥 *Streak: {g['streak']} kun!*",
                        parse_mode="Markdown", reply_markup=ok_kb()
                    )
                else:
                    bot.send_message(mid,
                        f"✅ *{u_name}* bajardi!\n"
                        f"👥 *{g['name']}:* {done_count}/{len(members)} a'zo",
                        parse_mode="Markdown", reply_markup=ok_kb()
                    )
            except Exception as _e: print(f"[warn] send_message: {_e}")
        # Asosiy menyuni yangilash — xuddi toggle_ kabi
        main_msg_id = u.get("main_msg_id")
        if main_msg_id:
            try:
                edit_message_colored(uid, main_msg_id, build_main_text(uid), main_menu_dict(uid))
            except Exception as _e: print(f"[warn] edit_message: {_e}")
        return

    if cdata.startswith("group_habit_add_"):
        g_id = cdata[len("group_habit_add_"):]
        bot.answer_callback_query(call.id)
        g = load_group(g_id)
        if not g or str(g.get("admin_id","")) != str(uid):
            return
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        u["state"]      = "group_habit_waiting_name"
        u["temp_group_habit"] = {"g_id": g_id}
        save_user(uid, u)
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.add(cBtn("⬅️ Orqaga", f"group_view_{g_id}", "primary"))
        sent = bot.send_message(uid,
            f"➕ *{g['name']}* — yangi odat\n\n"
            "Odat nomini kiriting:\n"
            "_Masalan: Meditatsiya_",
            parse_mode="Markdown", reply_markup=cancel_kb
        )
        u["temp_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    if cdata.startswith("group_habit_del_"):
        g_id = cdata[len("group_habit_del_"):]
        bot.answer_callback_query(call.id)
        g = load_group(g_id)
        if not g or str(g.get("admin_id","")) != str(uid):
            return
        habits = g.get("habits", [])
        if not habits and g.get("habit_name"):
            habits = [{"id": "main", "name": g["habit_name"]}]
        if not habits:
            bot.answer_callback_query(call.id, "O'chiradigan odat yo'q!")
            return
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        kb_del = InlineKeyboardMarkup()
        for h in habits:
            kb_del.add(InlineKeyboardButton(
                f"🗑 {h['name']}", callback_data=f"group_habit_del_confirm_{g_id}_{h['id']}"
            ))
        kb_del.add(cBtn("⬅️ Orqaga", f"group_view_{g_id}", "primary"))
        sent = bot.send_message(uid,
            f"🗑 *{g['name']}* — qaysi odatni o'chirmoqchisiz?",
            parse_mode="Markdown", reply_markup=kb_del
        )
        u["main_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    if cdata.startswith("group_habit_del_confirm_"):
        rest  = cdata[len("group_habit_del_confirm_"):]
        # format: g_id_h_id — h_id 6 belgi
        g_id  = rest[:-7]   # oxirgi _h_id (7 belgi: _+6)
        h_id  = rest[-6:]
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        g = load_group(g_id)
        if not g or str(g.get("admin_id","")) != str(uid):
            return
        habits = g.get("habits", [])
        if not habits and g.get("habit_name") and h_id == "main":
            g["habit_name"] = None
            save_group(g_id, g)
        else:
            g["habits"] = [h for h in habits if h["id"] != h_id]
            save_group(g_id, g)
        # A'zolarga xabar
        del_name = next((h["name"] for h in habits if h["id"] == h_id), "Odat")
        for mid in g.get("members", []):
            try:
                if str(mid) != str(uid):
                    bot.send_message(int(mid),
                        f"🗑 *{g['name']}* guruhidan *{del_name}* odati o'chirildi.",
                        parse_mode="Markdown", reply_markup=ok_kb()
                    )
            except Exception as _e: print(f"[warn] send_message: {_e}")
        sent = _send_group_view(uid, u, g, g_id)
        u["main_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    if cdata.startswith("group_habit_no_time_"):
        g_id = cdata[len("group_habit_no_time_"):]
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        old_mid = u.pop("temp_msg_id", None)
        if old_mid:
            try: bot.delete_message(uid, old_mid)
            except: pass
        temp = u.get("temp_group_habit", {})
        temp["time"] = "vaqtsiz"
        u["temp_group_habit"] = temp
        u["state"] = None
        save_user(uid, u)
        _save_group_habit(uid, u)
        return

    if cdata.startswith("group_approve_"):
        # group_approve_{g_id}_{joiner_uid}
        rest      = cdata[len("group_approve_"):]
        parts     = rest.rsplit("_", 1)
        g_id      = parts[0]
        joiner_id = int(parts[1])
        bot.answer_callback_query(call.id, "✅ Qabul qilindi!")
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        g = load_group(g_id)
        if not g:
            return
        # Guruhga qo'shish
        if str(joiner_id) not in [str(m) for m in g.get("members", [])]:
            g["members"].append(str(joiner_id))
            save_group(g_id, g)
        ju = load_user(joiner_id)
        groups = ju.get("groups", [])
        if not any(x.get("id") == g_id for x in groups):
            groups.append({"id": g_id, "name": g["name"], "admin_id": g["admin_id"]})
            ju["groups"] = groups
            save_user(joiner_id, ju)
        # Adminga: tasdiq xabari (5s dan keyin o'chadi)
        admin_name = u.get("name", "Admin")
        bot.send_message(uid,
            f"✅ *{ju.get('name','Foydalanuvchi')}* guruhga qo'shildi!\n"
            f"👥 *{g['name']}*",
            parse_mode="Markdown", reply_markup=ok_kb()
        )
        # Qo'shiluvchiga: so'rov qabul qilindi xabari + tasdiqlash tugmasi
        try:
            kb_confirm = InlineKeyboardMarkup()
            kb_confirm.add(cBtn("✅ Tushunarli!", f"group_join_ack_{g_id}", "success"))
            bot.send_message(joiner_id,
                f"🎉 *{g['name']}* guruhiga qo'shilish so'rovingiz qabul qilindi!\n\n"
                f"📌 Odat: *{g.get('habit_name','—')}*\n"
                f"⏰ Vaqt: *{g.get('habit_time','vaqtsiz')}*",
                parse_mode="Markdown",
                reply_markup=kb_confirm
            )
        except Exception as _e: print(f"[warn] xato: {_e}")
        return

    if cdata.startswith("group_join_ack_"):
        # Foydalanuvchi "Tushunarli!" ni bosdi — xabar 5s dan keyin o'chadi
        bot.answer_callback_query(call.id, "✅ Tabriklaymiz!")
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        return

    if cdata.startswith("group_reject_"):
        # group_reject_{g_id}_{joiner_uid}
        rest      = cdata[len("group_reject_"):]
        parts     = rest.rsplit("_", 1)
        g_id      = parts[0]
        joiner_id = int(parts[1])
        bot.answer_callback_query(call.id, "❌ Rad etildi")
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        g = load_group(g_id)
        # Qo'shiluvchiga: rad xabari
        try:
            bot.send_message(joiner_id,
                f"❌ *{g['name'] if g else 'Guruh'}* guruhiga qo'shilish so'rovingiz rad etildi.",
                parse_mode="Markdown", reply_markup=ok_kb()
            )
        except Exception as _e: print(f"[warn] send_message: {_e}")
        return

    if cdata.startswith("group_invite_"):
        g_id = cdata[len("group_invite_"):]
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        g = load_group(g_id)
        if not g:
            return
        inv_link = f"https://t.me/{get_bot_username()}?start=grp_{g_id}"
        sent = bot.send_message(uid,
            f"🔗 *{g['name']} — Invite link:*\n\n`{inv_link}`\n\n"
            f"_Ushbu linkni do'stlaringizga yuboring!_",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup().add(cBtn("⬅️ Orqaga", f"group_view_{g_id}", "primary"))
        )
        u["main_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    if cdata.startswith("group_leave_"):
        g_id = cdata[len("group_leave_"):]
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        g = load_group(g_id)
        if g:
            members = g.get("members", [])
            uid_str = str(uid)
            members = [m for m in members if str(m) != uid_str]
            g["members"] = members
            save_group(g_id, g)
            u["groups"] = [x for x in u.get("groups", []) if x.get("id") != g_id]
            save_user(uid, u)
            try:
                admin_id = g.get("admin_id")
                if admin_id and str(admin_id) != uid_str:
                    admin_u = load_user(admin_id)
                    bot.send_message(int(admin_id),
                        f"ℹ️ *{u.get('name','Foydalanuvchi')}* guruhdan chiqdi.",
                        parse_mode="Markdown", reply_markup=ok_kb()
                    )
            except Exception as _e: print(f"[warn] send_message: {_e}")
        send_menu2(uid)
        return

    # ============================================================
    #  BOZOR
    # ============================================================
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
        return

    if cdata == "bozor_buy_jon":
        bot.answer_callback_query(call.id)
        balls = u.get("points", 0)
        jon_val = round(u.get("jon", 100.0))
        if jon_val > 20:
            bot.send_message(uid,
                f"❤️ *Jon sotib olish mumkin emas!*\n\n"
                f"Jon faqat *20% va undan kam* bo'lganda sotib olinadi.\n"
                f"Hozirgi joningiz: *{jon_val}%*",
                parse_mode="Markdown"
            )
            return
        if balls < 50:
            bot.send_message(uid,
                f"⭐ *Balingiz yetarli emas!*\n\nJon sotib olish uchun *50 ball* kerak.\n"
                f"Sizda hozir: *{balls} ball*\n\n"
                "Har kuni odatlarni bajaring — ball to'playsiz! 💪",
                parse_mode="Markdown"
            )
            return
        u["points"] = balls - 50
        u["jon"]    = 100.0
        save_user(uid, u)
        bot.send_message(uid,
            "❤️ *Jon tiklandi!*\n\n"
            "50 ball sarflandi — joningiz *100%* ga qaytdi!\n"
            "Endi odatlarni davom ettiring! 💪",
            parse_mode="Markdown"
        )
        return

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
        return

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
        return

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
        return

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
        return

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
        return

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
        return

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
        return

    if cdata == "dismiss_ball_notif":
        bot.answer_callback_query(call.id, "✅")
        # Foydalanuvchi ma'lumotini olish
        u2 = load_user(uid)
        user_name = u2.get("name", "Noma'lum")
        # Adminga xabar yuborish - admin tasdiqlasin
        try:
            kb_admin_confirm = InlineKeyboardMarkup()
            kb_admin_confirm.add(InlineKeyboardButton(
                "✅ Tasdiqlash", callback_data=f"admin_confirm_ball_{uid}"
            ))
            bot.send_message(
                ADMIN_ID,
                f"✅ *{user_name}* (ID: `{uid}`) ballni olganini tasdiqladi!",
                parse_mode="Markdown",
                reply_markup=kb_admin_confirm
            )
        except Exception:
            pass
        # Foydalanuvchidagi xabarni darhol o'chirish
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        return

    if cdata.startswith("admin_confirm_ball_") and uid == ADMIN_ID:
        bot.answer_callback_query(call.id, "✅")
        def del_admin_ball_msg(msg_id):
            time.sleep(5)
            try: bot.delete_message(ADMIN_ID, msg_id)
            except: pass
        threading.Thread(target=del_admin_ball_msg, args=(call.message.message_id,), daemon=True).start()
        return

    if cdata == "noop":
        bot.answer_callback_query(call.id)
        return

    if cdata == "ack_delete_msg":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        return

    # ── Vaqtsiz odat qo'shish ──
    if cdata == "habit_no_time":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        u["temp_habit"]["time"] = "vaqtsiz"
        u.pop("temp_msg_id", None)
        save_user(uid, u)
        _save_new_habit(uid, u)
        return

    # ── Repeat odat: qo'shimcha vaqt qo'shish ──
    if cdata == "repeat_add_more":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        collected = u.get("temp_habit", {}).get("times_collected", [])
        u["state"] = "waiting_habit_time"
        save_user(uid, u)
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.add(cBtn(T(uid, "btn_cancel"), "cancel", "danger"))
        sent = bot.send_message(
            uid,
            f"⏰ *{len(collected)+1}-vaqtni* kiriting:\n_Masalan: 12:00_",
            parse_mode="Markdown", reply_markup=cancel_kb
        )
        u["temp_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    # ── Repeat odat: yakunlash ──
    if cdata == "repeat_done":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        u.pop("temp_msg_id", None)
        save_user(uid, u)
        _save_new_habit(uid, u)
        return

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
        return

    if cdata.startswith("delete_"):
        habit_id   = cdata[7:]
        u          = load_user(uid)
        habits     = u.get("habits", [])
        habit_name = next((h["name"] for h in habits if h["id"] == habit_id), "")
        bot.answer_callback_query(call.id)
        if not habit_name:
            send_main_menu(uid)
            return
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
        return

    if cdata.startswith("confirm_delete_"):
        habit_id   = cdata[15:]
        u          = load_user(uid)
        habits     = u.get("habits", [])
        habit_name = next((h["name"] for h in habits if h["id"] == habit_id), "")
        # Schedule dan o'chirish
        schedule.clear(f"{uid}_{habit_id}")
        u["habits"] = [h for h in habits if h["id"] != habit_id]
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
        return

    if cdata == "cancel_delete":
        bot.answer_callback_query(call.id)
        try:
            bot.delete_message(uid, call.message.message_id)
        except Exception:
            pass
        delete_habit_menu(uid)
        return

    # --- toggle_ ---
    if cdata.startswith("toggle_"):
        habit_id = cdata[7:]
        today    = today_uz5()
        from datetime import timezone, timedelta
        tz_uz     = timezone(timedelta(hours=5))
        yesterday = (datetime.now(tz_uz) - timedelta(days=1)).strftime("%Y-%m-%d")
        u        = load_user(uid)
        for h in u.get("habits", []):
            if h["id"] == habit_id:
                hab_type  = h.get("type", "simple")
                rep_count = h.get("repeat_count", 1)

                if hab_type == "repeat" and rep_count > 1:
                    # Takrorlanuvchi odat: done_today_count bilan ishlash
                    done_today_count = h.get("done_today_count", 0)
                    if h.get("done_date") != today:
                        done_today_count = 0
                    fully_done       = done_today_count >= rep_count

                    if fully_done:
                        # Bekor qilish: to'liq bajarilganidan qaytarish
                        h["done_today_count"] = 0
                        h["last_done"]  = None
                        h["streak"]     = max(0, h.get("streak", 0) - 1)
                        h["total_done"] = max(0, h.get("total_done", 0) - 1)
                        # Bonus multiplier (api_checkin bilan bir xil)
                        _undo_base = 5
                        if u.get("bonus_3x_active") and u.get("bonus_3x_date") == today:
                            _undo_base = 15
                        elif u.get("bonus_2x_active") and u.get("bonus_2x_date") == today:
                            _undo_base = 10
                        if u.get("xp_booster_days", 0) > 0:
                            _undo_base = round(_undo_base * 1.1)
                        u["points"] = max(0, u.get("points", 0) - _undo_base)
                        # Global streak: faqat bugun boshqa odat bajarilmagan bo'lsa kamaytir
                        _still_done = any(hh.get("last_done") == today for hh in u.get("habits", []) if hh["id"] != habit_id)
                        if not _still_done and u.get("streak_last_date") == today:
                            u["streak"] = max(0, u.get("streak", 0) - 1)
                            u["streak_last_date"] = ""
                        # done_log: boshqa odat bajarilmagan bo'lsa o'chirish
                        if not _still_done:
                            done_log = u.get("done_log", {})
                            done_log.pop(today, None)
                            u["done_log"] = done_log
                        # History yangilash (undo)
                        history = u.get("history", {})
                        day_data = history.get(today, {})
                        done_count_now = sum(1 for hh in u.get("habits", []) if hh.get("last_done") == today)
                        hab_map = day_data.get("habits", {})
                        hab_map[habit_id] = False
                        day_data["done"] = done_count_now
                        day_data["total"] = len(u.get("habits", []))
                        day_data["habits"] = hab_map
                        history[today] = day_data
                        u["history"] = history
                        save_user(uid, u)
                        schedule_habit(uid, h)
                        bot.answer_callback_query(call.id, f"↩️ 0/{rep_count}")
                    else:
                        # Bir bosish = progress +1, lekin ball YO'Q
                        done_today_count += 1
                        h["done_today_count"] = done_today_count
                        h["done_date"] = today
                        if done_today_count >= rep_count:
                            # To'liq bajarildi — faqat shu yerda ball beriladi
                            # BUG FIX: last_done yangilashdan OLDIN yesterday bilan solishtirish kerak
                            h["streak"]     = h.get("streak", 0) + 1 if h.get("last_done") == yesterday else 1
                            h["last_done"]  = today
                            h["total_done"] = h.get("total_done", 0) + 1
                            # Bonus multiplier (api_checkin bilan bir xil)
                            _base = 5
                            if u.get("bonus_3x_active") and u.get("bonus_3x_date") == today:
                                _base = 15
                            elif u.get("bonus_2x_active") and u.get("bonus_2x_date") == today:
                                _base = 10
                            if u.get("xp_booster_days", 0) > 0:
                                _base = round(_base * 1.1)
                            u["points"] = u.get("points", 0) + _base
                            # Global streak: kuniga bir marta oshsin
                            if u.get("streak_last_date") != today:
                                u["streak"] = u.get("streak", 0) + 1
                                u["streak_last_date"] = today
                                if u["streak"] > u.get("best_streak", 0):
                                    u["best_streak"] = u["streak"]
                                    u["best_streak_date"] = today
                                threading.Thread(target=_check_streak_milestone, args=(uid, u["streak"]), daemon=True).start()
                            # done_log: kunlik bajarilish tarixi
                            done_log = u.get("done_log", {})
                            done_log[today] = True
                            u["done_log"] = done_log
                            # history yangilash (statistika uchun)
                            history = u.get("history", {})
                            day_data = history.get(today, {})
                            done_count_now = sum(1 for hh in u.get("habits", []) if hh.get("last_done") == today)
                            hab_map = day_data.get("habits", {})
                            hab_map[habit_id] = True
                            day_data["done"]   = done_count_now
                            day_data["total"]  = len(u.get("habits", []))
                            day_data["habits"] = hab_map
                            history[today] = day_data
                            u["history"] = history
                            # XP booster kunini kamaytirish (kuniga bir marta)
                            if u.get("xp_booster_days", 0) > 0:
                                if u.get("xp_booster_last_day", "") != today:
                                    u["xp_booster_days"] = max(0, u["xp_booster_days"] - 1)
                                    u["xp_booster_last_day"] = today
                            unschedule_habit_today(uid, habit_id)
                            save_user(uid, u)
                            # Achievements tekshirish
                            try:
                                check_achievements_toplevel(uid, u)
                            except Exception as _ae:
                                print(f"[warn] check_achievements toggle_repeat: {_ae}")
                            bot.answer_callback_query(call.id)
                            streak_r = h.get("streak", 1)
                            if streak_r >= 30:   s_extra_r = f"\n🔥 Streak: {streak_r} kun 🏆"
                            elif streak_r >= 14: s_extra_r = f"\n🔥 Streak: {streak_r} kun 🌟"
                            elif streak_r >= 7:  s_extra_r = f"\n🔥 Streak: {streak_r} kun 🔥"
                            else:                s_extra_r = f"\n🔥 Streak: {streak_r} kun"
                            sent_msg = bot.send_message(
                                uid,
                                T(uid, "done_ok", name=h["name"]) + f" *+{_base} ⭐ ball*" + s_extra_r,
                                parse_mode="Markdown"
                            )
                        else:
                            save_user(uid, u)
                            bot.answer_callback_query(call.id, f"✅ {done_today_count}/{rep_count}")
                            sent_msg = bot.send_message(
                                uid,
                                f"✅ *{h['name']}* — *{done_today_count}/{rep_count}* bajarildi!",
                                parse_mode="Markdown"
                            )
                        def del_msg_rep(chat_id, msg_id):
                            time.sleep(3)
                            try: bot.delete_message(chat_id, msg_id)
                            except: pass
                        threading.Thread(target=del_msg_rep, args=(uid, sent_msg.message_id), daemon=True).start()
                        # Barcha odat bajarildi?
                        all_done = all(
                            (hh.get("last_done") == today if hh.get("type","simple") != "repeat"
                             else hh.get("done_today_count",0) >= hh.get("repeat_count",1))
                            for hh in u.get("habits", [])
                        )
                        if all_done and done_today_count >= rep_count:
                            sent_c = bot.send_message(uid, T(uid, "all_done"))
                            def del_c_rep(chat_id, msg_id):
                                time.sleep(5)
                                try: bot.delete_message(chat_id, msg_id)
                                except: pass
                            threading.Thread(target=del_c_rep, args=(uid, sent_c.message_id), daemon=True).start()

                else:
                    # Oddiy odat
                    if h.get("last_done") == today:
                        # Bekor qilish
                        h["last_done"]  = None
                        h["streak"]     = max(0, h.get("streak", 0) - 1)
                        h["total_done"] = max(0, h.get("total_done", 0) - 1)
                        # Bonus multiplier (api_checkin bilan bir xil)
                        _undo_base = 5
                        if u.get("bonus_3x_active") and u.get("bonus_3x_date") == today:
                            _undo_base = 15
                        elif u.get("bonus_2x_active") and u.get("bonus_2x_date") == today:
                            _undo_base = 10
                        if u.get("xp_booster_days", 0) > 0:
                            _undo_base = round(_undo_base * 1.1)
                        u["points"] = max(0, u.get("points", 0) - _undo_base)
                        # Global streak: faqat bugun boshqa odat bajarilmagan bo'lsa kamaytir
                        _still_done = any(hh.get("last_done") == today for hh in u.get("habits", []) if hh["id"] != habit_id)
                        if not _still_done and u.get("streak_last_date") == today:
                            u["streak"] = max(0, u.get("streak", 0) - 1)
                            u["streak_last_date"] = ""
                        # done_log: boshqa odat bajarilmagan bo'lsa o'chirish
                        if not _still_done:
                            done_log = u.get("done_log", {})
                            done_log.pop(today, None)
                            u["done_log"] = done_log
                        # History yangilash (undo)
                        history = u.get("history", {})
                        day_data = history.get(today, {})
                        done_count_now = sum(1 for hh in u.get("habits", []) if hh.get("last_done") == today)
                        hab_map = day_data.get("habits", {})
                        hab_map[habit_id] = False
                        day_data["done"] = done_count_now
                        day_data["total"] = len(u.get("habits", []))
                        day_data["habits"] = hab_map
                        history[today] = day_data
                        u["history"] = history
                        save_user(uid, u)
                        schedule_habit(uid, h)
                        bot.answer_callback_query(call.id)
                        sent_msg = bot.send_message(uid, T(uid, "undone", name=h["name"]), parse_mode="Markdown")
                        def del_msg1(chat_id, msg_id):
                            time.sleep(3)
                            try: bot.delete_message(chat_id, msg_id)
                            except: pass
                        threading.Thread(target=del_msg1, args=(uid, sent_msg.message_id), daemon=True).start()
                    else:
                        # Bajarildi
                        # BUG FIX: last_done yangilashdan OLDIN yesterday bilan solishtirish kerak
                        h["streak"]     = h.get("streak", 0) + 1 if h.get("last_done") == yesterday else 1
                        h["last_done"]  = today
                        h["total_done"] = h.get("total_done", 0) + 1
                        # Bonus multiplier (api_checkin bilan bir xil)
                        _base = 5
                        if u.get("bonus_3x_active") and u.get("bonus_3x_date") == today:
                            _base = 15
                        elif u.get("bonus_2x_active") and u.get("bonus_2x_date") == today:
                            _base = 10
                        if u.get("xp_booster_days", 0) > 0:
                            _base = round(_base * 1.1)
                        u["points"] = u.get("points", 0) + _base
                        # Global streak: kuniga bir marta oshsin
                        if u.get("streak_last_date") != today:
                            u["streak"] = u.get("streak", 0) + 1
                            u["streak_last_date"] = today
                            if u["streak"] > u.get("best_streak", 0):
                                u["best_streak"] = u["streak"]
                                u["best_streak_date"] = today
                            threading.Thread(target=_check_streak_milestone, args=(uid, u["streak"]), daemon=True).start()
                        # done_log: kunlik bajarilgan kun
                        done_log = u.get("done_log", {})
                        done_log[today] = True
                        u["done_log"] = done_log
                        # history yangilash (statistika uchun)
                        history = u.get("history", {})
                        day_data = history.get(today, {})
                        done_count_now = sum(1 for hh in u.get("habits", []) if hh.get("last_done") == today)
                        hab_map = day_data.get("habits", {})
                        hab_map[habit_id] = True
                        day_data["done"]   = done_count_now
                        day_data["total"]  = len(u.get("habits", []))
                        day_data["habits"] = hab_map
                        history[today] = day_data
                        u["history"] = history
                        # XP booster kunini kamaytirish (kuniga bir marta)
                        if u.get("xp_booster_days", 0) > 0:
                            if u.get("xp_booster_last_day", "") != today:
                                u["xp_booster_days"] = max(0, u["xp_booster_days"] - 1)
                                u["xp_booster_last_day"] = today
                        save_user(uid, u)
                        # Achievements tekshirish
                        try:
                            check_achievements_toplevel(uid, u)
                        except Exception as _ae:
                            print(f"[warn] check_achievements toggle: {_ae}")
                        unschedule_habit_today(uid, habit_id)
                        bot.answer_callback_query(call.id)
                        streak_s = h.get("streak", 1)
                        if streak_s >= 30:   s_extra_s = f"\n🔥 Streak: {streak_s} kun 🏆"
                        elif streak_s >= 14: s_extra_s = f"\n🔥 Streak: {streak_s} kun 🌟"
                        elif streak_s >= 7:  s_extra_s = f"\n🔥 Streak: {streak_s} kun 🔥"
                        else:                s_extra_s = f"\n🔥 Streak: {streak_s} kun"
                        sent_msg = bot.send_message(uid, T(uid, "done_ok", name=h["name"]) + f" *+{_base} ⭐ ball*" + s_extra_s, parse_mode="Markdown")
                        def del_msg2(chat_id, msg_id):
                            time.sleep(3)
                            try: bot.delete_message(chat_id, msg_id)
                            except: pass
                        threading.Thread(target=del_msg2, args=(uid, sent_msg.message_id), daemon=True).start()
                        # Barcha odat bajarildi?
                        all_done = all(
                            (hh.get("last_done") == today if hh.get("type","simple") != "repeat"
                             else hh.get("done_today_count",0) >= hh.get("repeat_count",1))
                            for hh in u.get("habits", [])
                        )
                        if all_done:
                            sent_c = bot.send_message(uid, T(uid, "all_done"))
                            def del_c(chat_id, msg_id):
                                time.sleep(5)
                                try: bot.delete_message(chat_id, msg_id)
                                except: pass
                            threading.Thread(target=del_c, args=(uid, sent_c.message_id), daemon=True).start()

                # Menyu yangilash
                main_msg_id = u.get("main_msg_id")
                if main_msg_id:
                    try:
                        edit_message_colored(uid, main_msg_id, build_main_text(uid), main_menu_dict(uid))
                    except Exception:
                        pass
                return

        # toggle_ - habit topilmadi (o'chirilgan bo'lishi mumkin)
        bot.answer_callback_query(call.id)
        send_main_menu(uid)

    # --- done_ (bildirishnomadan) ---
    if cdata.startswith("skip_"):
        habit_id = cdata[5:]
        bot.answer_callback_query(call.id)
        try:
            bot.delete_message(uid, call.message.message_id)
        except: pass
        return

    if cdata.startswith("done_"):
        habit_id = cdata[5:]
        today    = today_uz5()
        from datetime import timezone, timedelta
        tz_uz     = timezone(timedelta(hours=5))
        yesterday = (datetime.now(tz_uz) - timedelta(days=1)).strftime("%Y-%m-%d")
        u        = load_user(uid)
        for h in u.get("habits", []):
            if h["id"] == habit_id:
                hab_type  = h.get("type", "simple")
                rep_count = h.get("repeat_count", 1)

                if hab_type == "repeat" and rep_count > 1:
                    # Repeat odat: progress +1
                    done_today_count = h.get("done_today_count", 0)
                    if h.get("done_date") != today:
                        done_today_count = 0
                    if h.get("last_done") == today:
                        bot.answer_callback_query(call.id, T(uid, "done_today"))
                        return
                    done_today_count += 1
                    h["done_today_count"] = done_today_count
                    h["done_date"] = today
                    if done_today_count >= rep_count:
                        # To'liq bajarildi
                        h["streak"] = h.get("streak", 0) + 1 if h.get("last_done") == yesterday else 1
                        h["last_done"] = today
                        h["total_done"] = h.get("total_done", 0) + 1
                        if u.get("streak_last_date") != today:
                            u["streak"] = u.get("streak", 0) + 1
                            u["streak_last_date"] = today
                            if u["streak"] > u.get("best_streak", 0):
                                u["best_streak"] = u["streak"]
                                u["best_streak_date"] = today
                            threading.Thread(target=_check_streak_milestone, args=(uid, u["streak"]), daemon=True).start()
                        _base = 5
                        if u.get("bonus_3x_active") and u.get("bonus_3x_date") == today:
                            _base = 15
                        elif u.get("bonus_2x_active") and u.get("bonus_2x_date") == today:
                            _base = 10
                        if u.get("xp_booster_days", 0) > 0:
                            _base = round(_base * 1.1)
                        u["points"] = u.get("points", 0) + _base
                        done_log = u.get("done_log", {})
                        done_log[today] = True
                        u["done_log"] = done_log
                        save_user(uid, u)
                        try:
                            check_achievements_toplevel(uid, u)
                        except Exception: pass
                        unschedule_habit_today(uid, habit_id)
                        bot.answer_callback_query(call.id, "✅")
                        try:
                            bot.edit_message_text(
                                f"{T(uid, 'done_ok', name=h['name'])} *+{_base} ⭐ ball*\n\n🔥 Streak: {h['streak']} kun",
                                uid, call.message.message_id, parse_mode="Markdown"
                            )
                        except Exception: pass
                    else:
                        # Hali to'liq emas — progress ko'rsatish
                        save_user(uid, u)
                        bot.answer_callback_query(call.id, f"✅ {done_today_count}/{rep_count}")
                        try:
                            bot.edit_message_text(
                                f"✅ *{h['name']}* — *{done_today_count}/{rep_count}* bajarildi!",
                                uid, call.message.message_id, parse_mode="Markdown"
                            )
                        except Exception: pass
                    def del_remind_r(chat_id, message_id):
                        time.sleep(3)
                        try: bot.delete_message(chat_id, message_id)
                        except: pass
                    threading.Thread(target=del_remind_r, args=(uid, call.message.message_id), daemon=True).start()
                    main_msg_id = u.get("main_msg_id")
                    if main_msg_id:
                        try: edit_message_colored(uid, main_msg_id, build_main_text(uid), main_menu_dict(uid))
                        except Exception: pass
                    return

                # Oddiy (simple) odat
                if h.get("last_done") == today:
                    bot.answer_callback_query(call.id, T(uid, "done_today"))
                    return
                h["streak"] = h.get("streak", 0) + 1 if h.get("last_done") == yesterday else 1
                h["last_done"]  = today
                h["total_done"] = h.get("total_done", 0) + 1
                # Global streak: kuniga bir marta oshsin
                if u.get("streak_last_date") != today:
                    u["streak"] = u.get("streak", 0) + 1
                    u["streak_last_date"] = today
                    if u["streak"] > u.get("best_streak", 0):
                        u["best_streak"] = u["streak"]
                        u["best_streak_date"] = today
                    threading.Thread(target=_check_streak_milestone, args=(uid, u["streak"]), daemon=True).start()
                # Bonus multiplier hisoblash (WebApp api_checkin bilan bir xil)
                _base = 5
                if u.get("bonus_3x_active") and u.get("bonus_3x_date") == today:
                    _base = 15
                elif u.get("bonus_2x_active") and u.get("bonus_2x_date") == today:
                    _base = 10
                if u.get("xp_booster_days", 0) > 0:
                    _base = round(_base * 1.1)
                u["points"]     = u.get("points", 0) + _base
                # done_log: kunlik bajarilgan kunlarni saqlash
                done_log = u.get("done_log", {})
                done_log[today] = True
                u["done_log"] = done_log
                # History yangilash (statistika/heatmap uchun)
                habits_list = u.get("habits", [])
                history = u.get("history", {})
                day_data = history.get(today, {})
                done_count_now = sum(1 for hh in habits_list if hh.get("last_done") == today)
                total_now = len(habits_list)
                hab_map = day_data.get("habits", {})
                hab_map[habit_id] = True
                day_data["done"]   = done_count_now
                day_data["total"]  = total_now
                day_data["habits"] = hab_map
                history[today] = day_data
                u["history"] = history
                # XP booster kunini kamaytirish (kuniga bir marta)
                if u.get("xp_booster_days", 0) > 0:
                    last_boost = u.get("xp_booster_last_day", "")
                    if last_boost != today:
                        u["xp_booster_days"] = max(0, u["xp_booster_days"] - 1)
                        u["xp_booster_last_day"] = today
                save_user(uid, u)
                # Achievements tekshirish (top-level funksiya orqali)
                try:
                    check_achievements_toplevel(uid, u)
                except Exception as _ae:
                    print(f"[warn] check_achievements: {_ae}")
                unschedule_habit_today(uid, habit_id)
                streak = h["streak"]
                if streak >= 30:   msg_extra = f"🔥 Streak: {streak} kun 🏆"
                elif streak >= 14: msg_extra = f"🔥 Streak: {streak} kun 🌟"
                elif streak >= 7:  msg_extra = f"🔥 Streak: {streak} kun 🔥"
                else:              msg_extra = f"🔥 Streak: {streak} kun"
                bot.answer_callback_query(call.id, "✅")
                try:
                    bot.edit_message_text(
                        f"{T(uid, 'done_ok', name=h['name'])} *+{_base} ⭐ ball*\n\n{msg_extra}",
                        uid, call.message.message_id, parse_mode="Markdown"
                    )
                except Exception:
                    pass
                def del_remind(chat_id, message_id):
                    time.sleep(3)
                    try: bot.delete_message(chat_id, message_id)
                    except: pass
                threading.Thread(target=del_remind, args=(uid, call.message.message_id), daemon=True).start()
                main_msg_id = u.get("main_msg_id")
                if main_msg_id:
                    try:
                        edit_message_colored(uid, main_msg_id, build_main_text(uid), main_menu_dict(uid))
                    except Exception:
                        pass
                return
        # Odat topilmadi
        bot.answer_callback_query(call.id)
        return

    # ── Fallback: agar hech bir handler mos kelmasa ──
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass


# ============================================================
#  OYLIK HISOBOT
# ============================================================
def build_monthly_report_text(uid, report):
    month_label  = report.get("month_label", "—")
    done_pct     = report.get("done_pct", 0)
    jon_start    = report.get("jon_start", 100)
    jon_end      = report.get("jon_end", 100)
    jon_change   = round(jon_end - jon_start, 1)
    jon_sign     = "+" if jon_change >= 0 else ""
    best_streak  = report.get("best_streak", 0)
    balls_earned = report.get("balls_earned", 0)
    best_habit   = report.get("best_habit", "—")
    worst_habit  = report.get("worst_habit", "—")
    weeks_count  = report.get("weeks_count", 4)

    if done_pct >= 80:   grade = "🏆 Ajoyib oy!"
    elif done_pct >= 60: grade = "✅ Yaxshi oy"
    elif done_pct >= 40: grade = "💪 O'rtacha oy"
    else:                grade = "⚠️ Qiyin oy"

    if jon_end >= 80:   je = "❤️"
    elif jon_end >= 50: je = "🧡"
    elif jon_end >= 20: je = "💛"
    else:               je = "🖤"

    text  = f"📆 *{month_label}*\n"
    text += "▬" * 16 + "\n\n"
    text += f"{grade}\n\n"
    text += f"*🎯 Bajarildi:* {done_pct}%\n"
    text += f"*{je} Jon:* {jon_start}% → {jon_end}% ({jon_sign}{jon_change}%)\n"
    text += f"*🔥 Eng uzun streak:* {best_streak} kun\n"
    text += f"*⭐ Yig'ilgan ball:* +{balls_earned}\n"
    text += f"*📅 Jami hafta:* {weeks_count} ta\n\n"
    text += "▬" * 16 + "\n"
    text += f"*🏆 Eng yaxshi odat:* {best_habit}\n"
    text += f"*⚠️ Eng kam bajarilgan:* {worst_habit}\n"
    return text

def send_monthly_reports():
    from datetime import timezone, timedelta
    tz_uz   = timezone(timedelta(hours=5))
    now     = datetime.now(tz_uz)
    # O'tgan oy
    first_this = now.date().replace(day=1)
    last_month = first_this - timedelta(days=1)
    month_label = last_month.strftime("%B %Y")
    import calendar
    days_in_month = calendar.monthrange(last_month.year, last_month.month)[1]
    weeks_count = round(days_in_month / 7)
    users = load_all_users(force=True)
    print(f"[monthly_report] {len(users)} foydalanuvchiga yuborilmoqda...")
    for uid_str, udata in users.items():
        try:
            habits = udata.get("habits", [])
            if not habits:
                continue
            uid_int   = int(uid_str)
            jon_end   = udata.get("jon", 100)
            jon_start = max(0, min(100, round(jon_end - (jon_end - 50) * 0.3)))
            total_possible = 0
            total_done_m   = 0
            habit_scores   = []
            best_streak    = 0
            for h in habits:
                rep  = h.get("repeat_count", 1) if h.get("type") == "repeat" else 1
                done = min(h.get("total_done", 0), rep * days_in_month)
                poss = rep * days_in_month
                total_possible += poss
                total_done_m   += done
                score = round(done / poss * 100) if poss else 0
                habit_scores.append((h["name"], score))
                if h.get("streak", 0) > best_streak:
                    best_streak = h.get("streak", 0)
            done_pct     = round(total_done_m / total_possible * 100) if total_possible else 0
            balls_earned = total_done_m * 5
            habit_scores.sort(key=lambda x: x[1], reverse=True)
            best_habit  = habit_scores[0][0]  if habit_scores else "—"
            worst_habit = habit_scores[-1][0] if habit_scores else "—"
            report = {
                "month_label":  month_label,
                "done_pct":     done_pct,
                "jon_start":    jon_start,
                "jon_end":      jon_end,
                "best_streak":  best_streak,
                "balls_earned": balls_earned,
                "best_habit":   best_habit,
                "worst_habit":  worst_habit,
                "weeks_count":  weeks_count,
            }
            try:
                mongo_col.update_one(
                    {"_id": uid_str},
                    {"$push": {"monthly_reports": report}},
                    upsert=False
                )
            except Exception as e:
                print(f"[monthly_report] MongoDB xato {uid_str}: {e}")
            text = "📊 *Oylik hisobotingiz tayyor!*\n\n"
            text += build_monthly_report_text(uid_int, report)
            bot.send_message(uid_int, text, parse_mode="Markdown", reply_markup=ok_kb())
            time.sleep(0.05)
        except Exception as e:
            print(f"[monthly_report] Xato {uid_str}: {e}")
    print("[monthly_report] Yuborildi.")

# ============================================================
#  YILLIK HISOBOT
# ============================================================
def build_yearly_report_text(uid, report):
    year_label   = report.get("year_label", "—")
    done_pct     = report.get("done_pct", 0)
    jon_start    = report.get("jon_start", 100)
    jon_end      = report.get("jon_end", 100)
    jon_change   = round(jon_end - jon_start, 1)
    jon_sign     = "+" if jon_change >= 0 else ""
    best_streak  = report.get("best_streak", 0)
    balls_total  = report.get("balls_total", 0)
    best_habit   = report.get("best_habit", "—")
    worst_habit  = report.get("worst_habit", "—")
    best_month   = report.get("best_month", "—")

    if done_pct >= 80:   grade = "🏆 Zo'r yil!"
    elif done_pct >= 60: grade = "✅ Yaxshi yil"
    elif done_pct >= 40: grade = "💪 O'rtacha yil"
    else:                grade = "⚠️ Qiyin yil"

    if jon_end >= 80:   je = "❤️"
    elif jon_end >= 50: je = "🧡"
    elif jon_end >= 20: je = "💛"
    else:               je = "🖤"

    text  = f"🗓 *{year_label}*\n"
    text += "▬" * 16 + "\n\n"
    text += f"{grade}\n\n"
    text += f"*🎯 Bajarildi:* {done_pct}%\n"
    text += f"*{je} Jon:* {jon_start}% → {jon_end}% ({jon_sign}{jon_change}%)\n"
    text += f"*🔥 Eng uzun streak:* {best_streak} kun\n"
    text += f"*⭐ Jami ball:* {balls_total:,}\n"
    text += f"*📅 Jami hafta:* 52 ta\n"
    text += f"*📆 Jami oy:* 12 ta\n\n"
    text += "▬" * 16 + "\n"
    text += f"*🏆 Eng yaxshi odat:* {best_habit}\n"
    text += f"*⚠️ Eng kam bajarilgan:* {worst_habit}\n"
    text += f"*🌟 Eng yaxshi oy:* {best_month}\n"
    return text

def send_yearly_reports():
    from datetime import timezone, timedelta
    tz_uz    = timezone(timedelta(hours=5))
    now      = datetime.now(tz_uz)
    last_year = now.year - 1
    year_label = f"{last_year}-yil"
    users = load_all_users(force=True)
    print(f"[yearly_report] {len(users)} foydalanuvchiga yuborilmoqda...")
    for uid_str, udata in users.items():
        try:
            habits = udata.get("habits", [])
            if not habits:
                continue
            uid_int   = int(uid_str)
            jon_end   = udata.get("jon", 100)
            jon_start = max(0, min(100, round(jon_end - (jon_end - 50) * 0.5)))
            total_possible = 0
            total_done_y   = 0
            habit_scores   = []
            best_streak    = 0
            for h in habits:
                rep  = h.get("repeat_count", 1) if h.get("type") == "repeat" else 1
                done = min(h.get("total_done", 0), rep * 365)
                poss = rep * 365
                total_possible += poss
                total_done_y   += done
                score = round(done / poss * 100) if poss else 0
                habit_scores.append((h["name"], score))
                if h.get("streak", 0) > best_streak:
                    best_streak = h.get("streak", 0)
            done_pct    = round(total_done_y / total_possible * 100) if total_possible else 0
            balls_total = udata.get("points", 0)
            habit_scores.sort(key=lambda x: x[1], reverse=True)
            best_habit  = habit_scores[0][0]  if habit_scores else "—"
            worst_habit = habit_scores[-1][0] if habit_scores else "—"
            # Eng yaxshi oy — monthly_reports dan topamiz
            monthly_reps = udata.get("monthly_reports", [])
            if monthly_reps:
                best_m = max(monthly_reps, key=lambda r: r.get("done_pct", 0))
                best_month = best_m.get("month_label", "—")
            else:
                best_month = "—"
            report = {
                "year_label":  year_label,
                "done_pct":    done_pct,
                "jon_start":   jon_start,
                "jon_end":     jon_end,
                "best_streak": best_streak,
                "balls_total": balls_total,
                "best_habit":  best_habit,
                "worst_habit": worst_habit,
                "best_month":  best_month,
            }
            try:
                mongo_col.update_one(
                    {"_id": uid_str},
                    {"$push": {"yearly_reports": report}},
                    upsert=False
                )
            except Exception as e:
                print(f"[yearly_report] MongoDB xato {uid_str}: {e}")
            text = "📊 *Yillik hisobotingiz tayyor!*\n\n"
            text += build_yearly_report_text(uid_int, report)
            bot.send_message(uid_int, text, parse_mode="Markdown", reply_markup=ok_kb())
            time.sleep(0.05)
        except Exception as e:
            print(f"[yearly_report] Xato {uid_str}: {e}")
    print("[yearly_report] Yuborildi.")

# ============================================================
#  ESLATMA
# ============================================================
def send_reminder(user_id, habit):
    u      = load_user(user_id)
    habits = u.get("habits", [])
    exists = False
    today  = today_uz5()
    from datetime import timezone, timedelta
    tz_uz     = timezone(timedelta(hours=5))
    yesterday = (datetime.now(tz_uz) - timedelta(days=1)).strftime("%Y-%m-%d")
    current_habit = None
    for h in habits:
        if h["id"] == habit["id"]:
            exists = True
            current_habit = h
            # Bugun allaqachon bajarilgan bo'lsa — eslatma yubormaymiz
            if h.get("last_done") == today:
                return
            # total_missed bu yerda EMAS — daily_reset() da hisoblanadi (qo'sh hisoblashni oldini olish)
            break
    if not exists:
        return
    save_user(user_id, u)

    # Shaxsiy ma'lumotlar
    name       = u.get("name", "").split()[0] if u.get("name") else ""
    streak     = current_habit.get("streak", 0) if current_habit else 0
    lang       = get_lang(user_id)
    motiv      = random.choice(MOTIVATSIYA.get(lang, MOTIVATSIYA["uz"]))
    habit_name = current_habit.get("name", habit["name"])

    # Streak ga qarab jonli xabar
    if streak == 0:
        streak_line = f"🌱 Bugun birinchi qadam — eng muhimi shu!"
    elif streak == 1:
        streak_line = f"✨ Kecha boshladingiz — davom eting!"
    elif streak < 7:
        streak_line = f"🔥 {streak} kun ketma-ket! Ajoyib start!"
    elif streak < 14:
        streak_line = f"⚡ {streak} kunlik streak! Haftani yoping!"
    elif streak < 30:
        streak_line = f"💪 {streak} kun! Odat shakllanmoqda — to'xtamang!"
    elif streak < 100:
        streak_line = f"🏆 {streak} kunlik streak! Siz mashinasiz!"
    else:
        streak_line = f"👑 {streak} kun! Siz — odatlar ustasisiz!"

    # Xabar matni
    greeting = f"*{name},* " if name else ""
    text = (
        f"⏰ {greeting}*{habit_name}* vaqti!\n\n"
        f"{streak_line}\n\n"
        f"_{motiv}_"
    )

    try:
        bot.send_message(
            user_id,
            text,
            parse_mode="Markdown",
            reply_markup=done_keyboard(user_id, habit["id"])
        )
    except Exception as e:
        print(f"[reminder] xato: {e}")

STREAK_MILESTONES = {
    7:   {"emoji": "🔥", "bonus": 20,  "title": "7 kunlik streak!"},
    14:  {"emoji": "⚡", "bonus": 35,  "title": "2 haftalik streak!"},
    21:  {"emoji": "💪", "bonus": 50,  "title": "21 kunlik streak!"},
    30:  {"emoji": "💎", "bonus": 100, "title": "Oylik ustoz!"},
    60:  {"emoji": "🏆", "bonus": 200, "title": "60 kunlik streak!"},
    100: {"emoji": "👑", "bonus": 500, "title": "100 kun shohi!"},
    365: {"emoji": "🌟", "bonus": 1000, "title": "1 yillik streak!"},
}

def _check_streak_milestone(uid, new_streak):
    """Global streak milestone bo'lsa — Telegram xabari yuboradi va bonus ball beradi.
    Qayta yuborishni oldini olish uchun u['streak_milestones_sent'] listidan foydalanadi."""
    ms = STREAK_MILESTONES.get(new_streak)
    if not ms:
        return
    u = load_user(uid)
    sent_list = u.get("streak_milestones_sent", [])
    if new_streak in sent_list:
        return
    # Bonus ball qo'shamiz
    u["points"] = u.get("points", 0) + ms["bonus"]
    sent_list.append(new_streak)
    u["streak_milestones_sent"] = sent_list
    save_user(uid, u)
    lang = get_lang(uid)
    if lang == "ru":
        text = (
            f"{ms['emoji']} *{ms['title']}*\n\n"
            f"Pozdravlyaem! Vy podderzhivaete seriyu *{new_streak} dnej* podryad!\n\n"
            f"\U0001f381 *Bonus:* +{ms['bonus']} \u2b50 ballov dobavleno!"
        )
    elif lang == "en":
        text = (
            f"{ms['emoji']} *{ms['title']}*\n\n"
            f"Congratulations! You've kept a *{new_streak}-day* streak!\n\n"
            f"\U0001f381 *Bonus:* +{ms['bonus']} \u2b50 points added!"
        )
    else:
        text = (
            f"{ms['emoji']} *{ms['title']}*\n\n"
            f"Tabriklaymiz! Siz *{new_streak} kun* ketma-ket odat bajardingiz!\n\n"
            f"\U0001f381 *Bonus:* +{ms['bonus']} \u2b50 ball qo'shildi!"
        )
    try:
        bot.send_message(uid, text, parse_mode="Markdown")
    except Exception as e:
        print(f"[milestone] xato {uid}: {e}")

def schedule_habit(user_id, habit):
    # Avval eski jadval bo'lsa o'chiramiz (dublikat bo'lmasligi uchun)
    schedule.clear(f"{user_id}_{habit['id']}")
    # Vaqtsiz odatni rejalashtirmaymiz
    t = habit.get("time", "vaqtsiz")
    if not t or t in ("vaqtsiz", "—", "", None):
        return
    # Foydalanuvchi UTC+5 da vaqt kiritadi, Railway UTC da ishlaydi
    try:
        h, m = map(int, t.split(":"))
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError
        total    = h * 60 + m - 5 * 60
        total    = total % (24 * 60)
        utc_h    = total // 60
        utc_m    = total % 60
        utc_time = f"{utc_h:02d}:{utc_m:02d}"
    except Exception:
        print(f"[schedule] {habit['name']} — noto'g'ri vaqt: '{t}', o'tkazib yuborildi")
        return

    schedule.every().day.at(utc_time).do(
        send_reminder, user_id=user_id, habit=habit
    ).tag(f"{user_id}_{habit['id']}")
    print(f"[schedule] {habit['name']} — {t} (UTC: {utc_time})")

def unschedule_habit_today(user_id, habit_id):
    """Bugun uchun eslatmani to'xtatish — ertaga avtomatik ishlaydi"""
    schedule.clear(f"{user_id}_{habit_id}")
    print(f"[schedule] {user_id}_{habit_id} — bugunlik to'xtatildi")

def _is_member_done(val):
    """done_today[uid_str] qiymatini to'g'ri tekshiradi (True, {"main": True}, {"main": False})."""
    if val is True:
        return True
    if isinstance(val, dict):
        return True in val.values()
    return False

def group_daily_reset():
    """Har kuni 00:00 (UTC+5) da guruh progressini tozalash va eslatma yuborish"""
    print("[group_reset] Guruh progresslari tozalanmoqda...")
    from datetime import timezone, timedelta
    tz_uz     = timezone(timedelta(hours=5))
    yesterday = (datetime.now(tz_uz) - timedelta(days=1)).strftime("%Y-%m-%d")
    try:
        for g_doc in groups_col.find({}):
            g_id  = g_doc["_id"]
            g     = {k: v for k, v in g_doc.items() if k != "_id"}
            members    = g.get("members", [])
            done_today = g.get("done_today", {})
            done_date  = g.get("done_date", "")
            # Kecha hamma bajardimi?
            if done_date == yesterday:
                all_done = all(_is_member_done(done_today.get(str(mid), False)) for mid in members)
                if all_done and members:
                    g["streak"] = g.get("streak", 0) + 1
                elif members:
                    # Bajarmagan a'zolarga eslatma
                    for mid in members:
                        if not _is_member_done(done_today.get(str(mid), False)):
                            try:
                                mu = load_user(mid)
                                bot.send_message(
                                    int(mid),
                                    f"😔 *{g['name']}*\n\n"
                                    f"Kecha odatni bajarmadingiz.\n"
                                    f"📌 *{g.get('habit_name','—')}*\n\n"
                                    f"Bugun davom eting! 💪",
                                    parse_mode="Markdown"
                                )
                            except Exception as _e: print(f"[warn] xato: {_e}")
            # Progressni tozalash
            g["done_today"] = {}
            g["done_date"]  = ""
            save_group(g_id, g)
    except Exception as e:
        print(f"[group_reset] Xato: {e}")

def daily_reset():
    """Har kuni 00:00 (UTC+5) da barcha jadvallarni qayta yuklash"""
    from datetime import timezone, timedelta
    tz_uz     = timezone(timedelta(hours=5))
    today_str = datetime.now(tz_uz).strftime("%Y-%m-%d")
    # Bugun allaqachon ishlagan bo'lsa — qayta ishlatma
    try:
        settings_doc = mongo_col.find_one({"_id": "_settings"}) or {}
        if settings_doc.get("last_reset_date") == today_str:
            print(f"[daily_reset] Bugun allaqachon ishlagan ({today_str}) — o'tkazib yuborildi")
            return
        mongo_col.update_one({"_id": "_settings"}, {"$set": {"last_reset_date": today_str}}, upsert=True)
    except Exception as e:
        print(f"[daily_reset] Settings xatosi: {e}")
    print("[daily_reset] Barcha jadvallar qayta yuklanmoqda...")
    yesterday = (datetime.now(tz_uz) - timedelta(days=1)).strftime("%Y-%m-%d")
    users = load_all_users(force=True)
    for uid, udata in users.items():
        changed = False
        for habit in udata.get("habits", []):
            hab_type = habit.get("type", "simple")
            if hab_type == "repeat":
                # Repeat: done_today_count tozalash + bajarilmasa missed++
                fully_done = habit.get("last_done") == yesterday
                if not fully_done:
                    # Kecha to'liq bajarilmagan — missed++
                    if habit.get("total_done", 0) > 0 or habit.get("done_today_count", 0) > 0:
                        habit["total_missed"] = habit.get("total_missed", 0) + 1
                    # Streak nollash (simple habit kabi shield tekshiruvi bilan)
                    if habit.get("streak", 0) > 0:
                        shields = udata.get("streak_shields", 0)
                        if shields > 0:
                            streak_val = habit.get("streak", 0)
                            habit["streak"] = 0
                            pending = udata.get("pending_shield", {})
                            pending[habit["id"]] = streak_val
                            udata["pending_shield"] = pending
                            try:
                                kb_sh = InlineKeyboardMarkup()
                                kb_sh.row(
                                    InlineKeyboardButton("✅ Ha, ishlatish",    callback_data=f"shield_use_{habit['id']}"),
                                    InlineKeyboardButton("❌ Yo'q, nollansin", callback_data=f"shield_skip_{habit['id']}")
                                )
                                bot.send_message(
                                    int(uid),
                                    f"⚠️ *Streakingiz xavf ostida!*\n\n"
                                    f"*🔥 Streak:* {streak_val} kun\n"
                                    f"*📌 Odat:* {habit['name']}\n\n"
                                    f"*🛡 Himoyangiz bor* — ishlatinmi?\n"
                                    f"_(Yo'q desangiz himoya saqlanib qoladi)_",
                                    parse_mode="Markdown",
                                    reply_markup=kb_sh
                                )
                            except Exception:
                                pass
                        else:
                            habit["streak"] = 0
                # done_today_count tozalash — lekin last_done ni faqat bajarilmagan bo'lsa nollash
                habit["done_today_count"] = 0
                if not fully_done:
                    habit["last_done"] = None
                changed = True
            else:
                # Oddiy: kecha ham, bugun ham bajarilmagan bo'lsa missed++ va streak nollanadi
                missed_today = False
                last_done = habit.get("last_done")
                if last_done not in (yesterday, today_str, None):
                    habit["total_missed"] = habit.get("total_missed", 0) + 1
                    missed_today = True
                    changed = True
                elif last_done is None and habit.get("total_done", 0) > 0:
                    habit["total_missed"] = habit.get("total_missed", 0) + 1
                    missed_today = True
                    changed = True
                # Streak himoyasi
                if missed_today and habit.get("streak", 0) > 0:
                    shields = udata.get("streak_shields", 0)
                    if shields > 0:
                        # Himoya bor — foydalanuvchiga xabar yuborib qaror qildirish
                        streak_val = habit.get("streak", 0)
                        habit["streak"] = 0  # Hozircha nollanadi
                        changed = True
                        # pending_shield saqlaymiz — Ha bosilsa tiklanadi
                        pending = udata.get("pending_shield", {})
                        pending[habit["id"]] = streak_val
                        udata["pending_shield"] = pending
                        try:
                            kb_sh = InlineKeyboardMarkup()
                            kb_sh.row(
                                InlineKeyboardButton("✅ Ha, ishlatish",      callback_data=f"shield_use_{habit['id']}"),
                                InlineKeyboardButton("❌ Yo'q, nollansin",   callback_data=f"shield_skip_{habit['id']}")
                            )
                            bot.send_message(
                                int(uid),
                                f"⚠️ *Streakingiz xavf ostida!*\n\n"
                                f"*🔥 Streak:* {streak_val} kun\n"
                                f"*📌 Odat:* {habit['name']}\n\n"
                                f"*🛡 Himoyangiz bor* — ishlatinmi?\n"
                                f"_(Yo'q desangiz himoya saqlanib qoladi)_",
                                parse_mode="Markdown",
                                reply_markup=kb_sh
                            )
                        except Exception:
                            pass
                    else:
                        # Himoya yo'q — streak nollanadi
                        habit["streak"] = 0
        # Jon hisoblash
        habits_list = udata.get("habits", [])
        n = len(habits_list)
        if n > 0:
            d = 0
            for h in habits_list:
                # Har ikkala tur uchun ham last_done == yesterday tekshiramiz
                # (repeat uchun done_today_count allaqachon tozalangan bo'ladi)
                if h.get("last_done") == yesterday:
                    d += 1
            # Har bir odat teng ulushga ega: 10% / n
            # Masalan: 3 odat => har biri 3.33%
            jon_before   = udata.get("jon", 100.0)
            step_per_one = 10.0 / n       # har 1 odat uchun ulush
            change       = (d - (n - d)) * step_per_one  # bajarilgan - bajarilmagan
            jon          = round(min(100.0, max(0.0, jon_before + change)), 1)
            udata["jon"] = jon
            changed = True
            # Jon 0% ga yetsa — ogohlantirish xabari yuborish
            if jon <= 0 and jon_before > 0:
                try:
                    user_id_int = int(uid)
                    kb_jon = InlineKeyboardMarkup()
                    kb_jon.add(InlineKeyboardButton("❤️ Bozordan jon sotib olish (50 ball)", callback_data="bozor_buy_jon"))
                    bot.send_message(
                        user_id_int,
                        "*💀 Joningiz 0% ga yetdi!*\n\n"
                        "Kecha barcha odatlaringiz bajarilmadi.\n\n"
                        "Bugun barcha odatlaringizni bajarsangiz jon tiklanadi!\n"
                        "Yoki bozordan *50 ball* evaziga jonni tiklashingiz mumkin.",
                        parse_mode="Markdown",
                        reply_markup=kb_jon
                    )
                except Exception:
                    pass

        if changed:
            try:
                update_data = {
                    "habits":         udata["habits"],
                    "jon":            udata.get("jon", 100),
                    "pending_shield": udata.get("pending_shield", {}),
                    "streak_shields": udata.get("streak_shields", 0),
                }
                mongo_col.update_one({"_id": uid}, {"$set": update_data})
            except Exception:
                pass
    # ── Guruhlar: daily reset ──
    try:
        for gdoc in groups_col.find({}):
            g_id = gdoc["_id"]
            g    = {k: v for k, v in gdoc.items() if k != "_id"}
            # Kecha bajarmagan a'zolarga eslatma yuborish
            done_today = g.get("done_today", {})
            members    = g.get("members", [])
            not_done   = [mid for mid in members if not _is_member_done(done_today.get(str(mid), False))]
            if not_done and done_today:  # Kamida 1 kishi bajariganida
                for mid in not_done:
                    try:
                        bot.send_message(
                            int(mid),
                            f"⏰ *{g['name']}*\n\n"
                            f"Kecha *{g.get('habit_name','—')}* odatini bajarmaganingiz streak uzilishiga olib keldi!\n"
                            f"Bugun bajaring! 💪",
                            parse_mode="Markdown", reply_markup=ok_kb()
                        )
                    except Exception as _e: print(f"[warn] xato: {_e}")
            # Streak: agar hammasi bajargan bo'lsa allaqachon +1 bo'lgan
            # Agar hammasi bajarmaganligi bo'lsa streak nollanadi
            done_count = sum(1 for v in done_today.values() if (v is True or (isinstance(v, dict) and True in v.values())))
            if done_count < len(members) and g.get("streak", 0) > 0:
                g["streak"] = 0
            # Yangi kun uchun tozalash
            g["done_today"] = {}
            g["done_date"]  = today_str
            groups_col.update_one({"_id": g_id}, {"$set": g})
    except Exception as e:
        print(f"[daily_reset] guruh reset xatosi: {e}")

    # daily_reset ni saqlab, faqat habit jadvallarini tozalash
    all_jobs = schedule.get_jobs()
    for job in all_jobs:
        if "daily_reset" not in job.tags:
            schedule.cancel_job(job)
    load_all_schedules()

def load_all_schedules():
    users = load_all_users(force=True)
    for uid, udata in users.items():
        try:
            user_id = int(uid)
        except ValueError:
            continue
        today = today_uz5()
        for habit in udata.get("habits", []):
            # Bugun allaqachon bajarilgan bo'lsa — rejalashtirmaymiz
            if habit.get("last_done") == today:
                continue
            schedule_habit(user_id, habit)

def send_evening_reminders():
    """Har kuni 21:00 (UTC+5) da — evening_notify=True foydalanuvchilarga bajarilmagan odatlar haqida eslatma."""
    from datetime import timezone, timedelta
    tz_uz = timezone(timedelta(hours=5))
    today = datetime.now(tz_uz).strftime("%Y-%m-%d")
    try:
        users = load_all_users(force=True)
    except Exception as e:
        print(f"[evening] load_all_users xatosi: {e}")
        return
    for uid_str, udata in users.items():
        try:
            if not udata.get("evening_notify", False):
                continue
            habits = udata.get("habits", [])
            undone = [h for h in habits if h.get("last_done") != today]
            if not undone:
                continue
            lang = udata.get("lang", "uz")
            if lang == "ru":
                lines = ["*🌙 Вечернее напоминание*\n\nСегодня ещё не выполнены:"]
                for h in undone:
                    lines.append(f"  {h.get('icon','✅')} {h.get('name','')}")
                lines.append("\n_Ещё есть время! 💪_")
            elif lang == "en":
                lines = ["*🌙 Evening reminder*\n\nNot done yet today:"]
                for h in undone:
                    lines.append(f"  {h.get('icon','✅')} {h.get('name','')}")
                lines.append("\n_You still have time! 💪_")
            else:
                lines = ["*🌙 Kechki eslatma*\n\nBugun hali bajarilmagan odatlar:"]
                for h in undone:
                    lines.append(f"  {h.get('icon','✅')} {h.get('name','')}")
                lines.append("\n_Vaqt bor, ulguring! 💪_")
            text = "\n".join(lines)
            if lang == "ru":
                btn_label = "✅ Понятно"
            elif lang == "en":
                btn_label = "✅ Got it"
            else:
                btn_label = "✅ Tushundim"
            import json as _json
            kb_json = _json.dumps({"inline_keyboard": [[{
                "text": btn_label,
                "callback_data": "evening_dismiss",
                "style": "success"
            }]]})
            bot.send_message(int(uid_str), text, parse_mode="Markdown", reply_markup=kb_json)
        except Exception as e:
            print(f"[evening] uid={uid_str} xato: {e}")

def send_habit_health_warnings():
    """Har juma 11:00 (UTC+5) da — oxirgi 7 kunda foizi past (<30%) odatlar haqida ogohlantirish."""
    from datetime import timezone, timedelta
    tz_uz    = timezone(timedelta(hours=5))
    now_uz   = datetime.now(tz_uz)
    today    = now_uz.strftime("%Y-%m-%d")
    # Faqat juma kuni ishlaydi (weekday 4 = juma)
    if now_uz.weekday() != 4:
        return
    try:
        users = load_all_users(force=True)
    except Exception as e:
        print(f"[health] load_all_users xatosi: {e}")
        return
    warned_count = 0
    for uid_str, udata in users.items():
        try:
            habits = udata.get("habits", [])
            if not habits:
                continue
            # Bugun allaqachon yuborilganmi?
            if udata.get("habit_health_warned") == today:
                continue
            history = udata.get("history", {})
            lang    = udata.get("lang", "uz")
            weak_habits = []
            for h in habits:
                done_7 = sum(
                    1 for i in range(7)
                    if history.get(
                        (now_uz - timedelta(days=i)).strftime("%Y-%m-%d"), {}
                    ).get("habits", {}).get(h["id"])
                )
                pct = round(done_7 / 7 * 100)
                if pct < 30:
                    weak_habits.append((h.get("icon", "✅"), h.get("name", ""), pct))
            if not weak_habits:
                continue
            # Xabar tuzish
            if lang == "ru":
                lines = ["*⚠️ Слабые привычки на этой неделе:*\n"]
                for icon, name, pct in weak_habits:
                    bar = "█" * round(pct / 10) + "░" * (10 - round(pct / 10))
                    lines.append(f"  {icon} *{name}*\n  {bar} {pct}%\n")
                lines.append("_Уделите им больше внимания на следующей неделе! 💪_")
            elif lang == "en":
                lines = ["*⚠️ Weak habits this week:*\n"]
                for icon, name, pct in weak_habits:
                    bar = "█" * round(pct / 10) + "░" * (10 - round(pct / 10))
                    lines.append(f"  {icon} *{name}*\n  {bar} {pct}%\n")
                lines.append("_Give them more attention next week! 💪_")
            else:
                lines = ["*⚠️ Bu hafta zaif odatlar:*\n"]
                for icon, name, pct in weak_habits:
                    bar = "█" * round(pct / 10) + "░" * (10 - round(pct / 10))
                    lines.append(f"  {icon} *{name}*\n  {bar} {pct}%\n")
                lines.append("_Keyingi haftada ularga ko'proq e'tibor bering! 💪_")
            text = "\n".join(lines)
            bot.send_message(int(uid_str), text, parse_mode="Markdown")
            # Bugun yuborildi — belgilash
            mongo_col.update_one(
                {"_id": uid_str},
                {"$set": {"habit_health_warned": today}},
                upsert=False
            )
            warned_count += 1
            time.sleep(0.05)
        except Exception as e:
            print(f"[health] uid={uid_str} xato: {e}")
    print(f"[health] {warned_count} foydalanuvchiga ogohlantirish yuborildi.")

def resolve_expired_challenges():
    """Muddati o'tgan challengelarni hal qilish — har kuni ishlaydi."""
    import datetime as _dt
    from datetime import timezone, timedelta as _td
    tz_uz     = timezone(_td(hours=5))
    today_str = datetime.now(tz_uz).strftime("%Y-%m-%d")
    yesterday = (datetime.now(tz_uz) - _td(days=1)).strftime("%Y-%m-%d")
    try:
        challenges_col = mongo_db["challenges"]
    except Exception as e:
        print(f"[resolve_challenges] DB xatosi: {e}")
        return

    # ── 1. Pending → expired (3+ kundan beri qabul qilinmagan) ──
    try:
        three_days_ago = (datetime.now(tz_uz) - _td(days=3)).strftime("%Y-%m-%d")
        expired_pending = list(challenges_col.find({
            "status":     "pending",
            "created_at": {"$lte": three_days_ago}
        }))
        for c in expired_pending:
            challenges_col.update_one(
                {"_id": c["_id"]},
                {"$set": {"status": "expired"}}
            )
            # Yuboruvchiga xabar
            try:
                bot.send_message(
                    int(c["from_uid"]),
                    f"⏰ *Challenge muddati o'tdi*\n\n"
                    f"📌 Odat: *{c.get('habit_name','')}*\n"
                    f"Qabul qilinmadi — challenge bekor qilindi.",
                    parse_mode="Markdown"
                )
            except Exception:
                pass
        if expired_pending:
            print(f"[resolve_challenges] {len(expired_pending)} ta pending challenge expired qilindi")
    except Exception as e:
        print(f"[resolve_challenges] Pending expiry xatosi: {e}")

    # ── 2. Active → completed (expires_at <= yesterday) ──
    try:
        expired_active = list(challenges_col.find({
            "status":     "active",
            "expires_at": {"$lte": yesterday}
        }))
        for c in expired_active:
            from_uid    = c.get("from_uid", "")
            to_uid      = c.get("to_uid", "")
            bet         = c.get("bet", 50)
            accepted_at = c.get("accepted_at", c.get("created_at", ""))
            expires_at  = c.get("expires_at", yesterday)

            # done_log kunlarini hisoblash (accepted_at dan expires_at gacha)
            def count_done(uid_str):
                try:
                    u = load_user(int(uid_str))
                    if not u:
                        return 0
                    dl = u.get("done_log", {})
                    return sum(1 for d, v in dl.items() if v and accepted_at <= d <= expires_at)
                except Exception:
                    return 0

            from_score = count_done(from_uid)
            to_score   = count_done(to_uid)

            # G'olib aniqlash
            if from_score > to_score:
                winner_uid, loser_uid = from_uid, to_uid
                winner_score, loser_score = from_score, to_score
            elif to_score > from_score:
                winner_uid, loser_uid = to_uid, from_uid
                winner_score, loser_score = to_score, from_score
            else:
                winner_uid = None  # Durrang

            if winner_uid:
                # G'olib bet*2 oladi
                try:
                    u_w = load_user(int(winner_uid))
                    u_l = load_user(int(loser_uid))
                    if u_w:
                        u_w["points"] = u_w.get("points", 0) + bet * 2
                        save_user(int(winner_uid), u_w)
                    # G'olib xabari
                    w_name = u_w.get("name", "G'olib") if u_w else "G'olib"
                    l_name = u_l.get("name", "Raqib") if u_l else "Raqib"
                    try:
                        bot.send_message(
                            int(winner_uid),
                            f"🏆 *Challenge tugadi — Siz g'olib bo'ldingiz!*\n\n"
                            f"📌 Odat: *{c.get('habit_name','')}*\n"
                            f"📊 Natija: *{winner_score}* kun vs {loser_score} kun\n"
                            f"💰 *+{bet * 2} ball* hisobingizga qo'shildi!",
                            parse_mode="Markdown"
                        )
                    except Exception:
                        pass
                    try:
                        bot.send_message(
                            int(loser_uid),
                            f"😔 *Challenge tugadi — {w_name} g'olib bo'ldi*\n\n"
                            f"📌 Odat: *{c.get('habit_name','')}*\n"
                            f"📊 Natija: {loser_score} kun vs *{winner_score}* kun\n"
                            f"Keyingi safar omad! 💪",
                            parse_mode="Markdown"
                        )
                    except Exception:
                        pass
                except Exception as e:
                    print(f"[resolve_challenges] Winner reward xatosi: {e}")
            else:
                # Durrang — ikkalasi ham bet qaytariladi
                for ruid in [from_uid, to_uid]:
                    try:
                        u_r = load_user(int(ruid))
                        if u_r:
                            u_r["points"] = u_r.get("points", 0) + bet
                            save_user(int(ruid), u_r)
                        bot.send_message(
                            int(ruid),
                            f"🤝 *Challenge durrang tugadi!*\n\n"
                            f"📌 Odat: *{c.get('habit_name','')}*\n"
                            f"📊 Natija: {from_score} kun vs {to_score} kun\n"
                            f"💰 *+{bet} ball* (garov qaytarildi)",
                            parse_mode="Markdown"
                        )
                    except Exception:
                        pass

            challenges_col.update_one(
                {"_id": c["_id"]},
                {"$set": {
                    "status":       "completed",
                    "resolved_at":  today_str,
                    "from_score":   from_score,
                    "to_score":     to_score,
                    "winner_uid":   winner_uid or "tie",
                }}
            )
        if expired_active:
            print(f"[resolve_challenges] {len(expired_active)} ta active challenge hal qilindi")
    except Exception as e:
        print(f"[resolve_challenges] Active resolve xatosi: {e}")

def scheduler_loop():
    from datetime import timezone, timedelta
    tz_uz = timezone(timedelta(hours=5))
    # Bot ishga tushganda: agar bugun hali daily_reset ishlamagan bo'lsa — darhol ishlat
    last_reset_date = None
    now_uz = datetime.now(tz_uz)
    today_str = now_uz.strftime("%Y-%m-%d")
    # daily_reset ni birinchi marta sinxron ishlatish (kechagi reset o'tkazib yuborilgan bo'lsa)
    try:
        # Istalgan foydalanuvchidan bitta repeat odatni olib tekshirish
        users = load_all_users(force=True)
        needs_reset = False
        for uid, udata in users.items():
            for h in udata.get("habits", []):
                if h.get("type") == "repeat" and h.get("done_today_count", 0) > 0:
                    # done_today_count > 0 lekin last_done bugun emas — reset kerak
                    if h.get("last_done") != today_str:
                        needs_reset = True
                        break
            if needs_reset:
                break
        if needs_reset:
            print("[scheduler_loop] O'tkazib yuborilgan reset topildi — darhol daily_reset ishlatilmoqda")
            daily_reset()
    except Exception as e:
        print(f"[scheduler_loop] Startup reset xatosi: {e}")

    load_all_schedules()
    # Har kuni 00:00 (UTC+5 = 19:00 UTC) da reset
    schedule.every().day.at("19:00").do(daily_reset).tag("daily_reset")
    # Har kuni 21:00 (UTC+5 = 16:00 UTC) da kechki eslatma
    schedule.every().day.at("16:00").do(send_evening_reminders).tag("evening_reminder")
    schedule.every().day.at("19:00").do(group_daily_reset).tag("group_daily_reset")
    # Har kuni 00:05 (UTC+5 = 19:05 UTC) da muddati o'tgan challengelar hal qilinadi
    schedule.every().day.at("19:05").do(resolve_expired_challenges).tag("challenge_resolve")
    # Har juma 11:00 (UTC+5 = 06:00 UTC) da odat sog'liqligi tekshiruvi
    schedule.every().friday.at("06:00").do(send_habit_health_warnings).tag("habit_health")
    # Har dushanba 09:00 (UTC+5 = 04:00 UTC) da haftalik hisobot
    schedule.every().monday.at("04:00").do(send_weekly_reports).tag("weekly_report")
    # Har oyning 1-kuni 09:00 (UTC+5 = 04:00 UTC) da oylik hisobot
    schedule.every().day.at("04:01").do(
        lambda: send_monthly_reports() if __import__('datetime').datetime.now(
            __import__('datetime').timezone(__import__('datetime').timedelta(hours=5))
        ).day == 1 else None
    ).tag("monthly_report")
    # Har yilning 1-yanvari 09:00 (UTC+5 = 04:00 UTC) da yillik hisobot
    schedule.every().day.at("04:02").do(
        lambda: send_yearly_reports() if (
            __import__('datetime').datetime.now(
                __import__('datetime').timezone(__import__('datetime').timedelta(hours=5))
            ).month == 1 and
            __import__('datetime').datetime.now(
                __import__('datetime').timezone(__import__('datetime').timedelta(hours=5))
            ).day == 1
        ) else None
    ).tag("yearly_report")
    while True:
        schedule.run_pending()
        time.sleep(30)

# ============================================================
#  YANGI ODAT SAQLASH (markaziy funksiya)
# ============================================================
def _save_new_habit(uid, u):
    """Yangi odat yaratib saqlash va jadval o'rnatish"""
    import uuid
    temp = u.get("temp_habit", {})
    name = temp.get("name", "").strip()
    if not name:
        send_main_menu(uid)
        return
    hab_type  = temp.get("type", "simple")
    time_val  = temp.get("time", "vaqtsiz")
    today_str = today_uz5()

    if hab_type == "repeat":
        times_list  = temp.get("times_collected", [time_val])
        rep_count   = len(times_list)
        main_time   = times_list[0] if times_list else "vaqtsiz"
        new_habit = {
            "id":              str(uuid.uuid4())[:8],
            "name":            name,
            "type":            "repeat",
            "repeat_count":    rep_count,
            "repeat_times":    times_list,
            "time":            main_time,
            "streak":          0,
            "total_done":      0,
            "total_missed":    0,
            "done_today_count":0,
            "last_done":       None,
            "started_at":      today_str,
        }
    else:
        new_habit = {
            "id":           str(uuid.uuid4())[:8],
            "name":         name,
            "type":         "simple",
            "time":         time_val,
            "streak":       0,
            "total_done":   0,
            "total_missed": 0,
            "last_done":    None,
            "started_at":   today_str,
        }

    habits = u.get("habits", [])
    habits.append(new_habit)
    u["habits"] = habits
    u["state"]  = None
    u.pop("temp_habit", None)
    u.pop("temp_msg_id", None)
    save_user(uid, u)

    if time_val != "vaqtsiz":
        schedule_habit(uid, new_habit)

    time_show = time_val if time_val != "vaqtsiz" else "—"
    sent = bot.send_message(
        uid,
        T(uid, "habit_added", name=name, time=time_show),
        parse_mode="Markdown"
    )
    def del_and_back(chat_id, mid):
        time.sleep(5)
        try: bot.delete_message(chat_id, mid)
        except: pass
        # Odat qo'shish menyusiga qaytish
        u2 = load_user(chat_id)
        menu_dict = {
            "inline_keyboard": [
                [{"text": "📌 Oddiy", "callback_data": "habit_type_simple"},
                 {"text": "🔁 Takrorlanuvchi", "callback_data": "habit_type_repeat"}],
                [{"text": T(chat_id, "btn_home"), "callback_data": "menu_main", "style": "primary"}]
            ]
        }
        s = send_message_colored(chat_id, T(chat_id, "add_more_habits"), menu_dict)
        if s is None:
            kb = InlineKeyboardMarkup()
            kb.row(
                InlineKeyboardButton("📌 Oddiy", callback_data="habit_type_simple"),
                InlineKeyboardButton("🔁 Takrorlanuvchi", callback_data="habit_type_repeat")
            )
            kb.add(cBtn(T(chat_id, "btn_home"), "menu_main", "primary"))
            s = bot.send_message(chat_id, T(chat_id, "add_more_habits"), parse_mode="Markdown", reply_markup=kb)
        u2["main_msg_id"] = s.message_id
        save_user(chat_id, u2)
    threading.Thread(target=del_and_back, args=(uid, sent.message_id), daemon=True).start()

# ============================================================
#  GURUH VIEW YORDAMCHI FUNKSIYA
# ============================================================
def _send_group_view(uid, u, g, g_id):
    """Guruh ichki menyusini ko'rsatish"""
    members    = g.get("members", [])
    today      = today_uz5()
    done_today = g.get("done_today", {})
    if g.get("done_date") != today:
        done_today = {}
    is_admin   = (str(g.get("admin_id","")) == str(uid))
    habits     = g.get("habits", [])

    # Agar eski tizim — bitta odat (habit_name) ni ham ko'rsatamiz
    if not habits and g.get("habit_name"):
        habits = [{"id": "main", "name": g["habit_name"], "time": g.get("habit_time","vaqtsiz")}]

    # Matn: sarlavha
    text  = f"👥 *{g['name']}*\n"
    text += "━" * 16 + "\n"
    text += f"🔥 Streak: *{g.get('streak',0)} kun*   👤 *{len(members)} a'zo*\n\n"

    # Odatlar va progress
    text += "━" * 16 + "\n"
    for h in habits:
        h_id       = h["id"]
        h_name     = h["name"]
        h_time     = h.get("time","vaqtsiz")
        done_count = 0
        for mid in members:
            dt_val = done_today.get(str(mid), {})
            if isinstance(dt_val, dict):
                if dt_val.get(h_id, False):
                    done_count += 1
            else:
                if bool(dt_val) and h_id == "main":
                    done_count += 1
        text += f"\n📌 *{h_name}*"
        if h_time != "vaqtsiz":
            text += f"  ⏰ {h_time}"
        text += f"\n👥 Progress: {done_count}/{len(members)}\n"
        # A'zolar holati
        for mid in members:
            mu     = load_user(mid)
            m_name = mu.get("name","?")
            dt_val = done_today.get(str(mid), {})
            if isinstance(dt_val, dict):
                m_done = dt_val.get(h_id, False)
            else:
                m_done = bool(dt_val) if h_id == "main" else False
            status = "✅" if m_done else "⬜"
            you    = " *(siz)*" if mid == uid else ""
            text  += f"  {status} {m_name}{you}\n"
    text += "━" * 16

    # Tugmalar
    kb_g = InlineKeyboardMarkup()

    # 1-qator: Odat qo'shish | Odat o'chirish (faqat admin)
    if is_admin:
        kb_g.row(
            cBtn("➕ Odat qo'shish",  f"group_habit_add_{g_id}", "primary"),
            cBtn("🗑 Odat o'chirish", f"group_habit_del_{g_id}", "danger")
        )

    # Odatlar — har biri alohida qatorda
    for h in habits:
        h_id   = h["id"]
        h_name = h["name"]
        dt_val = done_today.get(str(uid), {})
        if isinstance(dt_val, dict):
            i_done = dt_val.get(h_id, False)
        else:
            i_done = bool(dt_val) if h_id == "main" else False
        if i_done:
            kb_g.add(InlineKeyboardButton(f"☑️ {h_name}", callback_data=f"group_done_{g_id}_{h_id}"))
        else:
            kb_g.add(cBtn(f"✅ {h_name}", f"group_done_{g_id}_{h_id}", "success"))

    # Taklif havolasi | Guruhni o'chirish (admin) yoki Guruhdan chiqish (a'zo)
    if is_admin:
        kb_g.row(
            cBtn("🔗 Taklif havolasi", f"group_invite_{g_id}",         "primary"),
            cBtn("🗑 Guruhni o'chirish", f"group_delete_confirm_{g_id}", "danger")
        )
    else:
        kb_g.row(
            cBtn("🔗 Taklif havolasi", f"group_invite_{g_id}", "primary"),
            cBtn("🚪 Guruhdan chiqish", f"group_leave_{g_id}", "danger")
        )

    kb_g.add(cBtn("🏠 Asosiy menyu", "menu_main", "primary"))
    return bot.send_message(uid, text, parse_mode="Markdown", reply_markup=kb_g)

# ============================================================
#  GURUH REYTING YORDAMCHI FUNKSIYA
# ============================================================
def _build_group_rating(uid, g, g_id, period="week"):
    """Guruh reytingini qurish — haftalik yoki oylik"""
    from datetime import timezone, timedelta
    tz_uz   = timezone(timedelta(hours=5))
    today   = datetime.now(tz_uz)
    members = g.get("members", [])

    # Har bir a'zo uchun statistika
    members_data = []
    for mid in members:
        mu       = load_user(mid)
        m_name   = mu.get("name", "?")
        done_log = g.get("member_done_log", {}).get(str(mid), {})
        # done_log = {date_str: True, ...}

        if period == "week":
            # Oxirgi 7 kun
            days   = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
            label  = "Haftalik"
            max_d  = 7
        else:
            # Oxirgi 30 kun
            days   = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(30)]
            label  = "Oylik"
            max_d  = 30

        done_count = sum(1 for d in days if done_log.get(d, False))
        streak     = g.get("member_streaks", {}).get(str(mid), 0)
        is_me      = (mid == uid)
        today_done = g.get("done_today", {}).get(str(mid), False)
        members_data.append({
            "name":       m_name,
            "done":       done_count,
            "streak":     streak,
            "is_me":      is_me,
            "today_done": today_done,
            "max":        max_d,
        })

    members_data.sort(key=lambda x: x["done"], reverse=True)

    text  = f"🏆 *{g['name']} — {label} Reyting*\n"
    text += f"📌 _{g.get('habit_name','—')}_\n"
    text += "━" * 16 + "\n\n"

    for i, m in enumerate(members_data, 1):
        medal  = "🥇" if i==1 else "🥈" if i==2 else "🥉" if i==3 else f"{i}."
        you    = " _(siz)_" if m["is_me"] else ""
        today_s = "✅" if m["today_done"] else "⬜"
        bar_len = round((m["done"] / m["max"]) * 8) if m["max"] > 0 else 0
        bar     = "█" * bar_len + "░" * (8 - bar_len)
        text   += f"{medal} *{m['name']}*{you}\n"
        text   += f"   {today_s} Bugun | 🔥{m['streak']} kun streak\n"
        text   += f"   `{bar}` {m['done']}/{m['max']}\n\n"

    text += "━" * 16

    # Tugmalar: haftalik/oylik filter + orqaga
    other_period = "month" if period == "week" else "week"
    other_label  = "📅 Oylik" if period == "week" else "📅 Haftalik"
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(other_label, callback_data=f"group_rating_show_{g_id}_{other_period}"))
    kb.add(cBtn("⬅️ Orqaga", "menu2_open", "primary"))
    return text, kb

# ============================================================
#  GURUH YARATISH SAQLASH
# ============================================================
def _save_new_group(uid, u):
    """Yangi guruh yaratib saqlash"""
    import uuid
    temp       = u.get("temp_group", {})
    name       = temp.get("name", "").strip()
    habit_name = temp.get("habit_name", "").strip()
    habit_time = temp.get("time", "vaqtsiz")
    if not name or not habit_name:
        send_menu2(uid)
        return
    admin_groups = [g for g in u.get("groups", []) if str(g.get("admin_id", "")) == str(uid)]
    if len(admin_groups) >= 3:
        bot.send_message(uid, T(uid, "err_max_groups"), parse_mode="Markdown")
        send_menu2(uid)
        return
    g_id = str(uuid.uuid4())[:8]
    group = {
        "id":          g_id,
        "name":        name,
        "habit_name":  habit_name,
        "habit_time":  habit_time,
        "admin_id":    str(uid),
        "members":     [str(uid)],
        "streak":      0,
        "created_at":  today_uz5(),
    }
    save_group(g_id, group)
    # Foydalanuvchi guruhlar ro'yxatiga qo'shish
    groups = u.get("groups", [])
    groups.append({"id": g_id, "name": name, "admin_id": str(uid)})
    u["groups"] = groups
    u.pop("temp_group", None)
    u["state"] = None
    save_user(uid, u)
    # Muvaffaqiyat xabari
    inv_link = f"https://t.me/{get_bot_username()}?start=grp_{g_id}"
    sent = bot.send_message(
        uid,
        f"✅ *Guruh yaratildi!*\n\n"
        f"👥 *{name}*\n"
        f"📌 Odat: *{habit_name}*\n"
        f"⏰ Vaqt: *{habit_time}*\n\n"
        f"🔗 *Invite link:*\n`{inv_link}`\n\n"
        f"_Do'stlaringizga linkni yuboring!_",
        parse_mode="Markdown"
    )
    def del_and_go(chat_id, mid):
        time.sleep(5)
        try: bot.delete_message(chat_id, mid)
        except: pass
        send_menu2(chat_id)
    threading.Thread(target=del_and_go, args=(uid, sent.message_id), daemon=True).start()

def _save_group_habit(uid, u):
    """Guruhga yangi odat qo'shish"""
    import uuid
    temp   = u.get("temp_group_habit", {})
    g_id   = temp.get("g_id")
    h_name = temp.get("name","").strip()
    h_time = temp.get("time","vaqtsiz")
    if not g_id or not h_name:
        return
    g = load_group(g_id)
    if not g or str(g.get("admin_id","")) != str(uid):
        return
    habits = g.get("habits", [])
    # Eski tizim (bitta habit_name) ni ham habits ga ko'chiramiz
    if not habits and g.get("habit_name"):
        habits = [{"id": "main", "name": g["habit_name"], "time": g.get("habit_time","vaqtsiz")}]
    new_h = {"id": str(uuid.uuid4())[:6], "name": h_name, "time": h_time}
    habits.append(new_h)
    g["habits"] = habits
    u.pop("temp_group_habit", None)
    save_user(uid, u)
    save_group(g_id, g)
    # Barcha a'zolarga xabar
    for mid in g.get("members", []):
        try:
            if str(mid) != str(uid):
                bot.send_message(int(mid),
                    f"➕ *{g['name']}* guruhiga yangi odat qo'shildi!\n\n"
                    f"📌 *{h_name}*" + (f"  ⏰ {h_time}" if h_time != "vaqtsiz" else ""),
                    parse_mode="Markdown"
                )
        except Exception as _e: print(f"[warn] send_message: {_e}")
    sent = _send_group_view(uid, u, g, g_id)
    u2 = load_user(uid)
    u2["main_msg_id"] = sent.message_id
    save_user(uid, u2)

# ============================================================
#  MATN HANDLER
# ============================================================
@bot.message_handler(func=lambda m: not (m.text and m.text.startswith("/")), content_types=["text", "photo", "document", "video", "audio", "voice", "sticker", "animation"])
def handle_text(msg):
    import re
    uid   = msg.from_user.id
    text  = msg.text or msg.caption or ""
    u     = load_user(uid)
    state = u.get("state")

    # ── Telefon raqamni matn sifatida kiritish (ro'yxatdan o'tish) ──
    if state == "waiting_phone_reg":
        phone_text = text.strip()
        phone_clean = re.sub(r"[^\d+]", "", phone_text)
        if len(phone_clean) >= 9:
            u["phone"] = phone_clean
            u["state"] = None
            reg_msg_id = u.pop("reg_msg_id", None)
            save_user(uid, u)
            try: bot.delete_message(uid, msg.message_id)
            except: pass
            if reg_msg_id:
                try: bot.delete_message(uid, reg_msg_id)
                except: pass
            # Adminga yangi foydalanuvchi haqida xabar
            try:
                total_users = count_users()
                user_name   = msg.from_user.first_name or "Noma'lum"
                username_str = f"@{msg.from_user.username}" if msg.from_user.username else "—"
                bot.send_message(
                    ADMIN_ID,
                    f"🆕 *Yangi Foydalanuvchi!*\n\n"
                    f"Umumiy: *{total_users}*\n"
                    f"Ismi: *{user_name}*\n"
                    f"Username: {username_str}\n"
                    f"ID: `{uid}`",
                    parse_mode="Markdown", reply_markup=ok_kb()
                )
            except Exception:
                pass
            if not check_subscription(uid):
                sent_rm = bot.send_message(uid, "✅", reply_markup=ReplyKeyboardRemove())
                def _del_rm_sub_t(cid, mid):
                    time.sleep(2)
                    try: bot.delete_message(cid, mid)
                    except: pass
                threading.Thread(target=_del_rm_sub_t, args=(uid, sent_rm.message_id), daemon=True).start()
                send_sub_required(uid)
                return
            sent_ok = bot.send_message(uid, "✅", reply_markup=ReplyKeyboardRemove())
            def _del_ok_t(cid, mid):
                time.sleep(3)
                try: bot.delete_message(cid, mid)
                except: pass
            threading.Thread(target=_del_ok_t, args=(uid, sent_ok.message_id), daemon=True).start()
            # Referal bonus berish
            referrer_id = u.pop("pending_referrer", None)
            if referrer_id and not u.get("ref_used"):
                try:
                    u["points"] = u.get("points", 0) + 25
                    u["ref_used"] = True
                    sent_ref = bot.send_message(uid,
                        "🎁 *Do\'st taklifi bonusi!*\n\n"
                        "*⭐ +25 ball* hisobingizga qo\'shildi!",
                        parse_mode="Markdown")
                    def _del_ref_t(cid, mid):
                        time.sleep(5)
                        try: bot.delete_message(cid, mid)
                        except: pass
                    threading.Thread(target=_del_ref_t, args=(uid, sent_ref.message_id), daemon=True).start()
                except Exception:
                    pass
                try:
                    u_ref = load_user(referrer_id)
                    u_ref["points"] = u_ref.get("points", 0) + 50
                    refs = u_ref.get("referrals", [])
                    refs.append(uid)
                    u_ref["referrals"] = refs
                    milestone_msg = ""
                    milestones = {5: "🛡 Streak himoyasi (1 ta) qo\'shildi!", 10: "⭐ +100 ball bonus!", 20: "💎 VIP nishon qo\'shildi!"}
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
                        f"🎉 *Do\'stingiz botga qo\'shildi!*\n\n"
                        f"*⭐ +50 ball* hisobingizga qo\'shildi!\n"
                        f"*👥 Jami taklif qilganlar:* {len(refs)} ta"
                        + milestone_msg,
                        parse_mode="Markdown", reply_markup=ok_kb())
                except Exception:
                    pass
            # Pending guruh
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
                            g_admin_id = g.get("admin_id")
                            if g_admin_id and str(g_admin_id) != str(uid):
                                bot.send_message(int(g_admin_id),
                                    f"👋 *{u.get('name','Yangi azo')}* guruhga qo\'shildi!\n"
                                    f"👥 *{g['name']}*",
                                    parse_mode="Markdown"
                                )
                        except Exception as _e: print(f"[warn] send_message: {_e}")
                        sent_grp = bot.send_message(uid,
                            f"✅ *{g['name']}* guruhiga qo\'shildingiz!\n"
                            f"📌 Odat: *{g.get('habit_name','—')}*",
                            parse_mode="Markdown", reply_markup=ok_kb()
                        )
                        def _del_grp_t(cid, mid):
                            time.sleep(5)
                            try: bot.delete_message(cid, mid)
                            except: pass
                        threading.Thread(target=_del_grp_t, args=(uid, sent_grp.message_id), daemon=True).start()
                except Exception as e:
                    print(f"[pending_group] xato: {e}")
            # Ism va username saqlash
            u["name"]     = msg.from_user.first_name or "Do'stim"
            u["username"]  = (msg.from_user.username or "").lower()
            save_user(uid, u)
            send_main_menu(uid)
        else:
            try: bot.delete_message(uid, msg.message_id)
            except: pass
            sent_err = bot.send_message(uid, T(uid, "err_wrong_phone"), parse_mode="Markdown")
            def _del_err(cid, mid):
                time.sleep(4)
                try: bot.delete_message(cid, mid)
                except: pass
            threading.Thread(target=_del_err, args=(uid, sent_err.message_id), daemon=True).start()
        return

    # ── Takrorlanuvchi odat - necha marta so'rash ──
    if state == "waiting_repeat_count":
        import re as _re2
        count_text = text.strip()
        try: bot.delete_message(uid, msg.message_id)
        except: pass
        try:
            count = int(count_text)
            if count < 1 or count > 20:
                raise ValueError
        except:
            bot.send_message(uid, T(uid, "err_wrong_count"), parse_mode="Markdown")
            return
        old_msg_id = u.pop("temp_msg_id", None)
        if old_msg_id:
            try: bot.delete_message(uid, old_msg_id)
            except: pass
        if not u.get("temp_habit"):
            u["state"] = None
            save_user(uid, u)
            send_main_menu(uid)
            return
        u["temp_habit"]["repeat_count"] = count
        u["state"] = "waiting_habit_name"
        save_user(uid, u)
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.add(cBtn(T(uid, "btn_cancel"), "cancel", "danger"))
        sent = bot.send_message(uid, T(uid, "ask_habit_name"), parse_mode="Markdown", reply_markup=cancel_kb)
        u["temp_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    # ── Odat nomi ──
    if state == "waiting_habit_name":
        # temp_habit yo'q bo'lsa — xavfsiz holda asosiy menyuga qaytish
        if not u.get("temp_habit"):
            u["state"] = None
            save_user(uid, u)
            send_main_menu(uid)
            return
        habit_name = text.strip()
        if not habit_name:
            return
        old_msg_id = u.pop("temp_msg_id", None)
        try: bot.delete_message(uid, msg.message_id)
        except: pass
        if old_msg_id:
            try: bot.delete_message(uid, old_msg_id)
            except: pass
        u["temp_habit"]["name"] = habit_name
        hab_type = u["temp_habit"].get("type", "simple")
        u["state"] = "waiting_habit_time"
        save_user(uid, u)
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.add(InlineKeyboardButton("⏩ Vaqtsiz qo'shish", callback_data="habit_no_time"))
        cancel_kb.add(cBtn(T(uid, "btn_cancel"), "cancel", "danger"))
        if hab_type == "repeat":
            prompt = (
                f"✅ *{habit_name}*\n\n"
                "🔁 Bu takrorlanuvchi odat.\n"
                "⏰ *1-vaqtni* kiriting:\n_Masalan: 06:00_\n\nYoki vaqtsiz qo'shing:"
            )
        else:
            prompt = (
                f"✅ *{habit_name}*\n\n"
                "⏰ Vaqtini kiriting:\n_Masalan: 07:00, 18:30_\n\nYoki vaqtsiz qo'shing:"
            )
        sent = bot.send_message(uid, prompt, parse_mode="Markdown", reply_markup=cancel_kb)
        u["temp_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    # ── Odat vaqti (oddiy yoki repeat birinchi vaqt) ──
    if state == "waiting_habit_time":
        time_text = text.strip()
        if not re.match(r'^\d{1,2}:\d{2}$', time_text):
            bot.send_message(uid, T(uid, "err_time_format"), parse_mode="Markdown")
            return
        try:
            hh, mm = time_text.split(":")
            if not (0 <= int(hh) <= 23 and 0 <= int(mm) <= 59):
                raise ValueError
            time_text = f"{int(hh):02d}:{int(mm):02d}"
        except:
            bot.send_message(uid, T(uid, "err_time_value"), parse_mode="Markdown")
            return
        old_msg_id = u.pop("temp_msg_id", None)
        try: bot.delete_message(uid, msg.message_id)
        except: pass
        if old_msg_id:
            try: bot.delete_message(uid, old_msg_id)
            except: pass

        hab_type = u.get("temp_habit", {}).get("type", "simple")
        if hab_type == "repeat":
            # temp_habit yo'q bo'lsa xavfsiz fallback
            if not u.get("temp_habit"):
                u["state"] = None
                save_user(uid, u)
                send_main_menu(uid)
                return
            collected = u["temp_habit"].get("times_collected", [])
            collected.append(time_text)
            u["temp_habit"]["times_collected"] = collected
            rep_count = u["temp_habit"].get("repeat_count", len(collected))
            if len(collected) < rep_count:
                # Yana vaqt kerak
                save_user(uid, u)
                cancel_kb = InlineKeyboardMarkup()
                cancel_kb.add(cBtn(T(uid, "btn_cancel"), "cancel", "danger"))
                sent = bot.send_message(
                    uid,
                    f"⏰ *{len(collected)+1}/{rep_count}* — Keyingi vaqtni kiriting:\n_Masalan: 18:00_",
                    parse_mode="Markdown", reply_markup=cancel_kb
                )
                u["temp_msg_id"] = sent.message_id
                save_user(uid, u)
            else:
                # Barcha vaqtlar to'plandi - saqlash
                save_user(uid, u)
                _save_new_habit(uid, u)
        else:
            u["temp_habit"]["time"] = time_text
            _save_new_habit(uid, u)
        return

    # ── Odat vaqtini tahrirlash (sozlamalar) ──
    if state == "editing_habit_time":
        time_text = text.strip()
        if not re.match(r'^\d{1,2}:\d{2}$', time_text):
            bot.send_message(uid, T(uid, "err_time_format"), parse_mode="Markdown")
            return
        try:
            hh, mm = time_text.split(":")
            if not (0 <= int(hh) <= 23 and 0 <= int(mm) <= 59):
                raise ValueError
            time_text = f"{int(hh):02d}:{int(mm):02d}"
        except:
            bot.send_message(uid, T(uid, "err_time_value"), parse_mode="Markdown")
            return
        try: bot.delete_message(uid, msg.message_id)
        except: pass
        old_msg_id = u.pop("temp_msg_id", None)
        if old_msg_id:
            try: bot.delete_message(uid, old_msg_id)
            except: pass

        habit_id = u.get("editing_habit_id")
        h_type   = u.get("editing_habit_type", "simple")
        if h_type == "repeat":
            collected = u.get("editing_habit_times_collected", [])
            collected.append(time_text)
            rep_count = u.get("editing_habit_rep_count", 1)
            u["editing_habit_times_collected"] = collected
            if len(collected) < rep_count:
                save_user(uid, u)
                cancel_kb = InlineKeyboardMarkup()
                cancel_kb.add(cBtn(T(uid, "btn_cancel"), "settings_habits_time", "danger"))
                sent = bot.send_message(
                    uid,
                    f"⏰ *{len(collected)+1}/{rep_count}* vaqtni kiriting:\n_Masalan: 06:00_",
                    parse_mode="Markdown", reply_markup=cancel_kb
                )
                u["temp_msg_id"] = sent.message_id
                save_user(uid, u)
                return
            # To'liq to'plandi
            for h in u.get("habits", []):
                if h["id"] == habit_id:
                    schedule.clear(f"{uid}_{habit_id}")
                    h["repeat_times"] = collected
                    h["time"]         = collected[0]
                    h["repeat_count"] = rep_count
                    schedule_habit(uid, h)
                    break
        else:
            if habit_id == "ALL":
                for h in u.get("habits", []):
                    schedule.clear(f"{uid}_{h['id']}")
                    h["time"] = time_text
                    schedule_habit(uid, h)
            else:
                for h in u.get("habits", []):
                    if h["id"] == habit_id:
                        schedule.clear(f"{uid}_{habit_id}")
                        h["time"] = time_text
                        schedule_habit(uid, h)
                        break
        u["state"] = None
        u.pop("editing_habit_id", None)
        u.pop("editing_habit_times_collected", None)
        save_user(uid, u)
        sent_ok = bot.send_message(uid, T(uid, "ok_time_updated"))
        def del_ok_time(chat_id, mid):
            time.sleep(2)
            try: bot.delete_message(chat_id, mid)
            except: pass
            send_main_menu(chat_id)
        threading.Thread(target=del_ok_time, args=(uid, sent_ok.message_id), daemon=True).start()
        return

    # ── Barcha odatlar uchun umumiy vaqt ──
    if state == "editing_all_habits_time":
        time_text = text.strip()
        if not re.match(r'^\d{1,2}:\d{2}$', time_text):
            bot.send_message(uid, T(uid, "err_time_format"), parse_mode="Markdown")
            return
        try:
            hh, mm = time_text.split(":")
            if not (0 <= int(hh) <= 23 and 0 <= int(mm) <= 59):
                raise ValueError
            time_text = f"{int(hh):02d}:{int(mm):02d}"
        except:
            bot.send_message(uid, T(uid, "err_time_value"), parse_mode="Markdown")
            return
        try: bot.delete_message(uid, msg.message_id)
        except: pass
        old_msg_id = u.pop("temp_msg_id", None)
        if old_msg_id:
            try: bot.delete_message(uid, old_msg_id)
            except: pass
        for h in u.get("habits", []):
            schedule.clear(f"{uid}_{h['id']}")
            h["time"] = time_text
            schedule_habit(uid, h)
        u["state"] = None
        save_user(uid, u)
        sent_ok = bot.send_message(uid, T(uid, "ok_all_times", time=time_text), parse_mode="Markdown")
        def del_ok_all_time(chat_id, mid):
            time.sleep(2)
            try: bot.delete_message(chat_id, mid)
            except: pass
            send_main_menu(chat_id)
        threading.Thread(target=del_ok_all_time, args=(uid, sent_ok.message_id), daemon=True).start()
        return

    # ── Ismni yangilash ──
    if state == "updating_name":
        new_name = text.strip()
        if not new_name:
            return
        try: bot.delete_message(uid, msg.message_id)
        except: pass
        info_msg_id = u.pop("info_msg_id", None)
        if info_msg_id:
            try: bot.delete_message(uid, info_msg_id)
            except: pass
        u["name"]  = new_name
        u["state"] = None
        save_user(uid, u)
        sent_ok = bot.send_message(uid, T(uid, "ok_name_changed", name=new_name), parse_mode="Markdown")
        def del_ok_name(chat_id, mid):
            time.sleep(2)
            try: bot.delete_message(chat_id, mid)
            except: pass
            send_main_menu(chat_id)
        threading.Thread(target=del_ok_name, args=(uid, sent_ok.message_id), daemon=True).start()
        return

    # ── Odat nomini o'zgartirish ──
    if state == "renaming_habit":
        new_name = text.strip()
        if not new_name:
            return
        try: bot.delete_message(uid, msg.message_id)
        except: pass
        info_msg_id = u.pop("info_msg_id", None)
        if info_msg_id:
            try: bot.delete_message(uid, info_msg_id)
            except: pass
        habit_id = u.pop("renaming_habit_id", None)
        for h in u.get("habits", []):
            if h["id"] == habit_id:
                old_name = h["name"]
                h["name"] = new_name
                break
        u["state"] = None
        save_user(uid, u)
        sent_ok = bot.send_message(uid, T(uid, "ok_habit_renamed", name=new_name), parse_mode="Markdown")
        def del_ok_rename(chat_id, mid):
            time.sleep(2)
            try: bot.delete_message(chat_id, mid)
            except: pass
            send_main_menu(chat_id)
        threading.Thread(target=del_ok_rename, args=(uid, sent_ok.message_id), daemon=True).start()
        return

    # ── Dasturchiga xabar ──
    if state == "waiting_dev_message":
        dev_msg_id = u.pop("dev_msg_id", None)
        try: bot.delete_message(uid, msg.message_id)
        except: pass
        if dev_msg_id:
            try: bot.delete_message(uid, dev_msg_id)
            except: pass
        u["state"] = None
        save_user(uid, u)
        user_name = u.get("name", "Noma'lum")
        try:
            kb_reply = InlineKeyboardMarkup()
            kb_reply.add(InlineKeyboardButton("↩️ Javob berish", callback_data=f"admin_reply_to_{uid}"))
            bot.send_message(
                ADMIN_ID,
                f"💬 *{user_name}* (ID: `{uid}`) dan xabar:\n\n{text}",
                parse_mode="Markdown", reply_markup=kb_reply
            )
        except Exception:
            pass
        sent_ok = bot.send_message(uid, T(uid, "ok_dev_sent"))
        def del_ok_dev(chat_id, mid):
            time.sleep(3)
            try: bot.delete_message(chat_id, mid)
            except: pass
            send_main_menu(chat_id)
        threading.Thread(target=del_ok_dev, args=(uid, sent_ok.message_id), daemon=True).start()
        return

    # ── Bozor: ball transfer — ID kiritish ──
    if state == "bozor_waiting_transfer_id":
        target_id_text = text.strip()
        try: bot.delete_message(uid, msg.message_id)
        except: pass
        try:
            target_id = int(target_id_text)
            if target_id == uid:
                bot.send_message(uid, T(uid, "err_self_transfer"))
                return
            if not user_exists(target_id):
                bot.send_message(uid, T(uid, "err_user_not_found"))
                return
        except ValueError:
            bot.send_message(uid, T(uid, "err_only_digits"), parse_mode="Markdown")
            return
        u["state"]             = "bozor_waiting_transfer_amount"
        u["transfer_target_id"] = target_id
        old_msg_id = u.pop("temp_msg_id", None)
        if old_msg_id:
            try: bot.delete_message(uid, old_msg_id)
            except: pass
        save_user(uid, u)
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.row(
            cBtn("⬅️ Orqaga", "menu_bozor", "primary"),
            cBtn(T(uid, "btn_home"), "menu_main", "primary")
        )
        target_u = load_user(target_id)
        sent = bot.send_message(
            uid,
            f"💸 *{target_u.get('name', str(target_id))}* ga necha ball yuborasiz?\n\n"
            f"⭐ Sizda: *{u.get('points', 0)} ball*",
            parse_mode="Markdown", reply_markup=cancel_kb
        )
        u["temp_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    # ── Bozor: ball transfer — miqdor kiritish ──
    if state == "bozor_waiting_transfer_amount":
        try: bot.delete_message(uid, msg.message_id)
        except: pass
        try:
            amount = int(text.strip())
            if amount <= 0:
                raise ValueError
        except ValueError:
            bot.send_message(uid, T(uid, "err_positive_num"), parse_mode="Markdown")
            return
        my_points  = u.get("points", 0)
        target_id  = u.get("transfer_target_id")
        if amount > my_points:
            bot.send_message(uid, T(uid, "err_not_enough_pts", points=my_points), parse_mode="Markdown")
            return
        old_msg_id = u.pop("temp_msg_id", None)
        if old_msg_id:
            try: bot.delete_message(uid, old_msg_id)
            except: pass
        target_u = load_user(target_id)
        u["points"] = my_points - amount
        u["state"]  = None
        u.pop("transfer_target_id", None)
        save_user(uid, u)
        target_u["points"] = target_u.get("points", 0) + amount
        save_user(target_id, target_u)
        try:
            bot.send_message(
                target_id,
                f"🎁 *{u.get('name','Kimdir')}* sizga *{amount} ball* yubordi!\n\n⭐ Hisobingiz: {target_u['points']} ball",
                parse_mode="Markdown"
            )
        except Exception:
            pass
        sent_ok = bot.send_message(uid, T(uid, "ok_transfer", amount=amount, points=u["points"]), parse_mode="Markdown")
        def del_ok_transfer(chat_id, mid):
            time.sleep(3)
            try: bot.delete_message(chat_id, mid)
            except: pass
            send_main_menu(chat_id)
        threading.Thread(target=del_ok_transfer, args=(uid, sent_ok.message_id), daemon=True).start()
        return

    # ── Bozor: ballarni ayirish ──
    if state == "bozor_waiting_subtract":
        try: bot.delete_message(uid, msg.message_id)
        except: pass
        old_msg_id = u.pop("temp_msg_id", None)
        if old_msg_id:
            try: bot.delete_message(uid, old_msg_id)
            except: pass
        try:
            amount = int(text.strip())
            if amount <= 0:
                raise ValueError
        except ValueError:
            bot.send_message(uid, T(uid, "err_positive_num"), parse_mode="Markdown")
            return
        my_points = u.get("points", 0)
        deducted  = min(amount, my_points)
        u["points"] = my_points - deducted
        u["state"]  = None
        save_user(uid, u)
        sent_ok = bot.send_message(uid, T(uid, "ok_self_deduct", amount=deducted, points=u['points']), parse_mode="Markdown")
        def del_ok_subtract(chat_id, mid):
            time.sleep(3)
            try: bot.delete_message(chat_id, mid)
            except: pass
            send_main_menu(chat_id)
        threading.Thread(target=del_ok_subtract, args=(uid, sent_ok.message_id), daemon=True).start()
        return

    # ── Admin: foydalanuvchiga ball berish — ID ──
    if state == "admin_waiting_points_id" and uid == ADMIN_ID:
        try: bot.delete_message(uid, msg.message_id)
        except: pass
        try:
            target_id = int(text.strip())
            if not user_exists(target_id):
                bot.send_message(uid, T(uid, "err_user_not_found"))
                return
        except ValueError:
            bot.send_message(uid, T(uid, "err_only_digits"))
            return
        u["state"] = "admin_waiting_points_amount"
        u["give_target_id"] = target_id
        save_user(uid, u)
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.add(cBtn("❌ Bekor qilish", "admin_cancel", "danger"))
        target_u = load_user(target_id)
        sent = bot.send_message(
            uid,
            f"🎁 *{target_u.get('name', str(target_id))}* ga necha ball berish yoki ayirish?\n\n"
            "_Minus qo'yish uchun: -50, qo'shish uchun: 100_",
            parse_mode="Markdown", reply_markup=cancel_kb
        )
        u["give_points_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    # ── Admin: foydalanuvchiga ball berish — miqdor ──
    if state == "admin_waiting_points_amount" and uid == ADMIN_ID:
        try: bot.delete_message(uid, msg.message_id)
        except: pass
        try:
            amount = int(text.strip())
        except ValueError:
            bot.send_message(uid, T(uid, "err_enter_number"))
            return
        target_id = u.pop("give_target_id", None)
        if not target_id:
            send_main_menu(uid)
            return
        target_u = load_user(target_id)
        target_u["points"] = max(0, target_u.get("points", 0) + amount)
        save_user(target_id, target_u)
        u["state"] = None
        save_user(uid, u)
        sign = "+" if amount >= 0 else ""
        try:
            bot.send_message(
                target_id,
                T(target_id, "admin_gave_pts", amount=f"{sign}{amount}", points=target_u['points']),
                parse_mode="Markdown"
            )
        except Exception:
            pass
        sent_ok = bot.send_message(uid, f"✅ {sign}{amount} ball berildi. Jami: {target_u['points']}")
        def del_ok_admin_pts(chat_id, mid):
            time.sleep(3)
            try: bot.delete_message(chat_id, mid)
            except: pass
            bot.send_message(chat_id, "🛠 *Admin panel*", parse_mode="Markdown", reply_markup=admin_menu())
        threading.Thread(target=del_ok_admin_pts, args=(uid, sent_ok.message_id), daemon=True).start()
        return

    # ── Admin: kanal o'rnatish ──
    if state and state.startswith("admin_waiting_channel_") and uid == ADMIN_ID:
        try: bot.delete_message(uid, msg.message_id)
        except: pass
        slot = int(state.split("_")[-1])
        channel = text.strip()
        if not channel.startswith("@"):
            channel = "@" + channel
        settings = load_settings()
        settings[f"required_channel_{slot}"] = channel
        try:
            chat_info = bot.get_chat(channel)
            settings[f"required_channel_title_{slot}"] = chat_info.title or channel
        except Exception:
            settings[f"required_channel_title_{slot}"] = channel
        save_settings(settings)
        u["state"] = None
        save_user(uid, u)
        sent_ok = bot.send_message(uid, f"✅ {slot}-kanal *{channel}* sifatida o'rnatildi!", parse_mode="Markdown")
        def del_ok_ch(chat_id, mid):
            time.sleep(2)
            try: bot.delete_message(chat_id, mid)
            except: pass
            bot.send_message(chat_id, "🛠 *Admin panel*", parse_mode="Markdown", reply_markup=admin_menu())
        threading.Thread(target=del_ok_ch, args=(uid, sent_ok.message_id), daemon=True).start()
        return

    # ── Admin: foydalanuvchiga javob ──
    if state and state.startswith("admin_waiting_reply_") and uid == ADMIN_ID:
        try: bot.delete_message(uid, msg.message_id)
        except: pass
        target_id = int(state.split("_")[-1])
        reply_msg_id = u.pop("reply_msg_id", None)
        if reply_msg_id:
            try: bot.delete_message(uid, reply_msg_id)
            except: pass
        u["state"] = None
        save_user(uid, u)
        try:
            bot.send_message(target_id, T(target_id, "admin_reply", text=text), parse_mode="Markdown")
            bot.send_message(uid, "✅ Javob yuborildi.")
        except Exception as e:
            bot.send_message(uid, f"❌ Xato: {e}")
        return

    # ── Guruh yaratish: nom ──
    if state == "group_waiting_name":
        group_name = text.strip()
        if not group_name:
            return
        try: bot.delete_message(uid, msg.message_id)
        except: pass
        old_mid = u.pop("temp_msg_id", None)
        if old_mid:
            try: bot.delete_message(uid, old_mid)
            except: pass
        u["temp_group"]["name"] = group_name
        u["state"] = "group_waiting_habit"
        save_user(uid, u)
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.add(cBtn("⬅️ Orqaga", "menu2_open", "primary"))
        sent = bot.send_message(uid,
            f"✅ Guruh nomi: *{group_name}*\n\n"
            "2️⃣ Umumiy odat nomini kiriting:\n"
            "_Masalan: Har kuni 30 bet kitob o'qish_",
            parse_mode="Markdown", reply_markup=cancel_kb
        )
        u["temp_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    # ── Guruh yaratish: odat nomi ──
    if state == "group_waiting_habit":
        habit_name = text.strip()
        if not habit_name:
            return
        try: bot.delete_message(uid, msg.message_id)
        except: pass
        old_mid = u.pop("temp_msg_id", None)
        if old_mid:
            try: bot.delete_message(uid, old_mid)
            except: pass
        u["temp_group"]["habit_name"] = habit_name
        u["state"] = "group_waiting_time"
        save_user(uid, u)
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.add(InlineKeyboardButton("⏩ Vaqtsiz", callback_data="group_create_no_time"))
        cancel_kb.add(cBtn("⬅️ Orqaga", "menu2_open", "primary"))
        sent = bot.send_message(uid,
            f"✅ Odat: *{habit_name}*\n\n"
            "3️⃣ Eslatma vaqtini kiriting:\n"
            "_Masalan: 21:00_\n\n"
            "_Yoki vaqtsiz qo'shish uchun tugmani bosing_",
            parse_mode="Markdown", reply_markup=cancel_kb
        )
        u["temp_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    # ── Guruh yaratish: vaqt ──
    if state == "group_waiting_time":
        import re as _re_g
        time_text = text.strip()
        if not _re_g.match(r'^\d{1,2}:\d{2}$', time_text):
            bot.send_message(uid, T(uid, "err_time_format"), parse_mode="Markdown")
            return
        try:
            hh, mm = time_text.split(":")
            if not (0 <= int(hh) <= 23 and 0 <= int(mm) <= 59):
                raise ValueError
            time_text = f"{int(hh):02d}:{int(mm):02d}"
        except:
            bot.send_message(uid, T(uid, "err_time_value"), parse_mode="Markdown")
            return
        try: bot.delete_message(uid, msg.message_id)
        except: pass
        old_mid = u.pop("temp_msg_id", None)
        if old_mid:
            try: bot.delete_message(uid, old_mid)
            except: pass
        u["temp_group"]["time"] = time_text
        u["state"] = None
        save_user(uid, u)
        _save_new_group(uid, u)
        return

    # ── Guruh odati: nom ──
    if state == "group_habit_waiting_name":
        h_name = text.strip()
        if not h_name:
            return
        try: bot.delete_message(uid, msg.message_id)
        except: pass
        old_mid = u.pop("temp_msg_id", None)
        if old_mid:
            try: bot.delete_message(uid, old_mid)
            except: pass
        u["temp_group_habit"]["name"] = h_name
        u["state"] = "group_habit_waiting_time"
        save_user(uid, u)
        g_id      = u["temp_group_habit"]["g_id"]
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.add(InlineKeyboardButton("⏩ Vaqtsiz", callback_data=f"group_habit_no_time_{g_id}"))
        cancel_kb.add(cBtn("⬅️ Orqaga", f"group_view_{g_id}", "primary"))
        sent = bot.send_message(uid,
            f"✅ Odat: *{h_name}*\n\n"
            "Eslatma vaqtini kiriting:\n"
            "_Masalan: 08:00_",
            parse_mode="Markdown", reply_markup=cancel_kb
        )
        u["temp_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    # ── Guruh odati: vaqt ──
    if state == "group_habit_waiting_time":
        import re as _re_gh
        time_text = text.strip()
        if not _re_gh.match(r'^\d{1,2}:\d{2}$', time_text):
            bot.send_message(uid, T(uid, "err_time_format"), parse_mode="Markdown")
            return
        try:
            hh, mm = time_text.split(":")
            if not (0 <= int(hh) <= 23 and 0 <= int(mm) <= 59):
                raise ValueError
            time_text = f"{int(hh):02d}:{int(mm):02d}"
        except:
            bot.send_message(uid, T(uid, "err_time_value"), parse_mode="Markdown")
            return
        try: bot.delete_message(uid, msg.message_id)
        except: pass
        old_mid = u.pop("temp_msg_id", None)
        if old_mid:
            try: bot.delete_message(uid, old_mid)
            except: pass
        u["temp_group_habit"]["time"] = time_text
        u["state"] = None
        save_user(uid, u)
        _save_group_habit(uid, u)
        return

    # ── Onboarding — odat nomini yozish ──
    if state == "onboard_waiting_name":
        habit_name = text.strip()
        if len(habit_name) < 2:
            bot.send_message(uid, T(uid, "err_min_chars"))
            return
        u["state"] = None
        save_user(uid, u)
        send_onboarding_time(uid, habit_name)
        return

    # ── Onboarding — vaqtni yozish ──
    if state == "onboard_waiting_time":
        import re as _re_ob
        t = text.strip()
        if _re_ob.match(r"^\d{1,2}:\d{2}$", t):
            parts = t.split(":")
            h, m = int(parts[0]), int(parts[1])
            if 0 <= h <= 23 and 0 <= m <= 59:
                habit_name = u.get("temp_onboard_habit", "Odat")
                u["state"] = None
                save_user(uid, u)
                finish_onboarding(uid, habit_name, f"{h:02d}:{m:02d}")
                return
        bot.send_message(uid, T(uid, "err_time_format"), parse_mode="Markdown")
        return

    # ── Broadcast matn/media (admin) ──
    if state in ("admin_bc_private", "admin_bc_groups", "admin_bc_all") and uid == ADMIN_ID:
        bc_chat_id   = msg.chat.id
        media_grp_id = msg.media_group_id
        if media_grp_id:
            if not hasattr(bot, '_bc_album_buffer'):
                bot._bc_album_buffer = {}
            if media_grp_id not in bot._bc_album_buffer:
                bot._bc_album_buffer[media_grp_id] = {"ids": [], "processing": False}
            buf = bot._bc_album_buffer[media_grp_id]
            buf["ids"].append(msg.message_id)
            if buf["processing"]:
                return
            buf["processing"] = True
            bc_state_cap = state
            bc_uid_cap   = uid
            bc_chat_cap  = bc_chat_id
            def _do_album_broadcast():
                time.sleep(1.5)
                final_ids = bot._bc_album_buffer.pop(media_grp_id, {}).get("ids", [msg.message_id])
                _run_broadcast(bc_uid_cap, bc_chat_cap, final_ids, bc_state_cap)
            threading.Thread(target=_do_album_broadcast, daemon=True).start()
        else:
            threading.Thread(
                target=_run_broadcast,
                args=(uid, msg.chat.id, [msg.message_id], state),
                daemon=True
            ).start()
        return




@bot.pre_checkout_query_handler(func=lambda q: True)
def handle_pre_checkout(query):
    """Telegram Stars to'lovini tasdiqlash"""
    bot.answer_pre_checkout_query(query.id, ok=True)

@bot.message_handler(content_types=["successful_payment"])
def handle_successful_payment(msg):
    """Stars to'lovi muvaffaqiyatli — itemni berish"""
    uid = msg.from_user.id
    payload = msg.successful_payment.invoice_payload  # "stars_gift_box" formatida
    try:
        item_id = payload.replace("stars_", "", 1)
        u = load_user(uid)
        raw_inv = u.get("inventory", {})
        if isinstance(raw_inv, list):
            inventory = {i: 1 for i in raw_inv}
        else:
            inventory = dict(raw_inv)
        # gift_box — tasodifiy mukofot
        if item_id == "gift_box":
            import random as _rnd
            gifts = [
                ("points", 100), ("points", 200), ("points", 500),
                ("streak_shields", 1), ("xp_booster_days", 3),
            ]
            gift_type, gift_val = _rnd.choice(gifts)
            if gift_type == "points":
                u["points"] = u.get("points", 0) + gift_val
                msg_text = f"🎁 *Sovga qutisi ochildi!*\n\n🎉 *+{gift_val} ball* qo'shildi!"
            elif gift_type == "streak_shields":
                u["streak_shields"] = u.get("streak_shields", 0) + gift_val
                msg_text = f"🎁 *Sovga qutisi ochildi!*\n\n🛡 *{gift_val} ta streak himoyasi* qo'shildi!"
            elif gift_type == "xp_booster_days":
                u["xp_booster_days"] = u.get("xp_booster_days", 0) + gift_val
                msg_text = f"🎁 *Sovga qutisi ochildi!*\n\n💎 *XP Booster {gift_val} kun* qo'shildi!"
            else:
                msg_text = "🎁 Sovga qutisi ochildi!"
        else:
            inventory[item_id] = inventory.get(item_id, 0) + 1
            msg_text = f"✅ *{item_id}* muvaffaqiyatli olindi!"
        u["inventory"] = inventory
        save_user(uid, u)
        bot.send_message(uid, msg_text, parse_mode="Markdown")
    except Exception as e:
        print(f"[stars] successful_payment xatosi: {e}")


def _run_broadcast(admin_uid, bc_chat_id, msg_ids, state):
    """Broadcast yuborish — matn va album uchun umumiy funksiya"""
    # State ni darhol tozalaymiz — restart bo'lsa ham qotib qolmasin
    try:
        u0 = load_user(admin_uid)
        u0["state"] = None
        save_user(admin_uid, u0)
    except Exception:
        pass
    try:
        users      = load_all_users(force=True)
        sent_count = 0
        failed     = 0
        failed_ids = []
        prog_msg = bot.send_message(admin_uid, f"⏳ Yuborilmoqda... (0/{len(users)} ta)")
        for target_uid_str in users:
            try:
                target_uid_int = int(target_uid_str)
            except (ValueError, TypeError):
                continue
            if target_uid_int == admin_uid:
                continue
            try:
                kb_user = InlineKeyboardMarkup()
                kb_user.add(InlineKeyboardButton("▶️ Start", url=f"https://t.me/{get_bot_username()}?start=bc"))
                for i_mid, mid in enumerate(msg_ids):
                    # Tugmani faqat oxirgi xabarga biriktirish
                    if i_mid == len(msg_ids) - 1:
                        bot.copy_message(
                            chat_id=target_uid_int,
                            from_chat_id=bc_chat_id,
                            message_id=mid,
                            reply_markup=kb_user
                        )
                    else:
                        bot.copy_message(
                            chat_id=target_uid_int,
                            from_chat_id=bc_chat_id,
                            message_id=mid
                        )
                sent_count += 1
                time.sleep(0.05)
            except Exception as e:
                err_str = str(e)
                failed += 1
                if "blocked" not in err_str.lower():
                    failed_ids.append(f"{target_uid_str} ({err_str[:40]})")
                print(f"[broadcast] {target_uid_str} ga yuborib bo'lmadi: {e}")
        try: bot.delete_message(admin_uid, prog_msg.message_id)
        except: pass
        result = f"📢 Xabar yuborildi!\n✅ {sent_count} ta muvaffaqiyatli."
        if failed:
            result += f"\n❌ {failed} ta foydalanuvchiga yetmadi."
        kb_bc = InlineKeyboardMarkup()
        if failed_ids:
            kb_bc.add(InlineKeyboardButton("🔍 Batafsil", callback_data="bc_detail"))
        kb_bc.add(InlineKeyboardButton("✅ Tushunarli", callback_data="bc_confirm"))
        bot.send_message(admin_uid, result, reply_markup=kb_bc)
    except Exception as fatal_e:
        print(f"[broadcast FATAL] {fatal_e}")
        try:
            bot.send_message(admin_uid, f"❌ Broadcast xatolik bilan to'xtadi: {fatal_e}")
        except Exception as _e: print(f"[warn] send_message: {_e}")
    finally:
        u = load_user(admin_uid)
        u["state"] = None
        if failed_ids:
            u["bc_failed_list"] = failed_ids
        save_user(admin_uid, u)


# ============================================================
#  WEB APP API SERVER (Flask)
# ============================================================

# Top-level achievements (bot callback'dan ham chaqirish uchun)
_ACHIEVEMENTS = [
    {"id":"streak_3",   "cat":"streak",  "icon":"🔥", "title":"Ilk olov",        "req":3,    "field":"streak"},
    {"id":"streak_7",   "cat":"streak",  "icon":"🌟", "title":"Haftalik qahramon","req":7,    "field":"streak"},
    {"id":"streak_30",  "cat":"streak",  "icon":"💎", "title":"Oylik ustoz",      "req":30,   "field":"streak"},
    {"id":"streak_100", "cat":"streak",  "icon":"👑", "title":"100 kun shohi",    "req":100,  "field":"streak"},
    {"id":"pts_100",    "cat":"ball",    "icon":"⭐", "title":"Birinchi yulduz",  "req":100,  "field":"points"},
    {"id":"pts_500",    "cat":"ball",    "icon":"🌠", "title":"Yulduz yomg'iri",  "req":500,  "field":"points"},
    {"id":"pts_1000",   "cat":"ball",    "icon":"🏆", "title":"Ming ball",        "req":1000, "field":"points"},
    {"id":"pts_5000",   "cat":"ball",    "icon":"💰", "title":"Ball millioneri",  "req":5000, "field":"points"},
    {"id":"hab_1",      "cat":"odat",    "icon":"🌱", "title":"Birinchi qadam",   "req":1,    "field":"habits_count"},
    {"id":"hab_5",      "cat":"odat",    "icon":"🌿", "title":"To'plam",          "req":5,    "field":"habits_count"},
    {"id":"hab_10",     "cat":"odat",    "icon":"🌳", "title":"Bog'bon",          "req":10,   "field":"habits_count"},
    {"id":"done_10",    "cat":"faollik", "icon":"✅", "title":"O'n marta",        "req":10,   "field":"total_done"},
    {"id":"done_50",    "cat":"faollik", "icon":"🎯", "title":"Ellik marta",      "req":50,   "field":"total_done"},
    {"id":"done_100",   "cat":"faollik", "icon":"🚀", "title":"Yuz marta",        "req":100,  "field":"total_done"},
    {"id":"done_500",   "cat":"faollik", "icon":"⚡", "title":"Besh yuz",         "req":500,  "field":"total_done"},
    {"id":"friend_1",   "cat":"ijtimoiy","icon":"🤝", "title":"Birinchi do'st",   "req":1,    "field":"friends_count"},
    {"id":"friend_5",   "cat":"ijtimoiy","icon":"👥", "title":"Jamoatchi",        "req":5,    "field":"friends_count"},
]

def check_achievements_toplevel(uid, u):
    """Bot callback'dan chaqirish uchun top-level achievements tekshiruvi."""
    earned_ids = {a["id"] for a in u.get("achievements", []) if isinstance(a, dict)}
    field_vals = {
        "streak":        u.get("streak", 0),
        "points":        u.get("points", 0),
        "habits_count":  len(u.get("habits", [])),
        "total_done":    sum(h.get("total_done", 0) for h in u.get("habits", [])),
        "friends_count": len(u.get("friends", [])),
    }
    new_ach = []
    ach_list = list(u.get("achievements", []))
    changed = False
    for ach in _ACHIEVEMENTS:
        if ach["id"] in earned_ids:
            continue
        if field_vals.get(ach["field"], 0) >= ach["req"]:
            ach_list.append({"id": ach["id"], "earned_at": today_uz5()})
            new_ach.append(ach)
            changed = True
    if changed:
        u["achievements"] = ach_list
        save_user(uid, u)
    return new_ach

try:
    from flask import Flask, jsonify, request

    api_app = Flask(__name__)

    # ── Simple in-memory rate limiter ──
    import collections
    _rl_buckets = collections.defaultdict(list)  # key -> [timestamp, ...]
    _rl_lock    = __import__('threading').Lock()

    def _rate_limit(key: str, limit: int, window: int = 60) -> bool:
        """True = ruxsat, False = limit oshdi. window=soniya, limit=max so'rov."""
        now = _time.time()
        with _rl_lock:
            bucket = _rl_buckets[key]
            # Eskilarni tozala
            _rl_buckets[key] = [t for t in bucket if now - t < window]
            if len(_rl_buckets[key]) >= limit:
                return False
            _rl_buckets[key].append(now)
            return True

    def rate_limit_check(uid=None, limit=60, window=60):
        """Decorator emas, to'g'ridan-to'g'ri chaqiriladigan tekshirish."""
        key = f"uid:{uid}" if uid else f"ip:{request.remote_addr}"
        if not _rate_limit(key, limit, window):
            return jsonify({"ok": False, "error": "Too many requests"}), 429
        return None


    @api_app.after_request
    def add_cors(response):
        response.headers["Access-Control-Allow-Origin"]  = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        return response

    @api_app.route("/api/rating", methods=["OPTIONS"])
    @api_app.route("/api/profile/<int:uid>", methods=["OPTIONS"])
    @api_app.route("/api/groups/<int:uid>", methods=["OPTIONS"])
    def options_preflight(**kwargs):
        return jsonify({}), 200

    # ── Telegram WebApp initData tekshirish ──
    import hmac, hashlib, urllib.parse, time as _time

    def verify_init_data(init_data_raw: str) -> int | None:
        """
        Telegram WebApp initData ni HMAC-SHA256 bilan tekshiradi.
        Muvaffaqiyatli bo'lsa user_id qaytaradi, aks holda None.
        """
        if not init_data_raw:
            print("[auth] FAIL: init_data_raw bo'sh")
            return None
        try:
            params = dict(urllib.parse.parse_qsl(init_data_raw, keep_blank_values=True))
            received_hash = params.pop("hash", None)
            if not received_hash:
                print("[auth] FAIL: hash yo'q")
                return None
            data_check_string = "\n".join(
                f"{k}={v}" for k, v in sorted(params.items())
            )
            secret_key = hmac.new(BOT_TOKEN.encode(), b"WebAppData", hashlib.sha256).digest()
            computed   = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(computed, received_hash):
                print(f"[auth] FAIL: hash mos kelmadi. computed={computed[:10]}... received={received_hash[:10]}...")
                return None
            auth_date = int(params.get("auth_date", 0))
            age = int(_time.time() - auth_date)
            if age > 604800:
                print(f"[auth] FAIL: auth_date eskirgan ({age} soniya oldin)")
                return None
            import json as _json
            user_obj = _json.loads(params.get("user", "{}"))
            uid = int(user_obj.get("id", 0)) or None
            if uid:
                print(f"[auth] OK: uid={uid}, age={age}s")
            else:
                print("[auth] FAIL: user id topilmadi")
            return uid
        except Exception as e:
            print(f"[auth] EXCEPTION: {e}")
            return None

    def require_auth(f):
        """Decorator: X-User-Id header orqali uid tekshiradi."""
        from functools import wraps
        @wraps(f)
        def decorated(*args, **kwargs):
            if request.method == "OPTIONS":
                return f(*args, **kwargs)
            uid_in_route = kwargs.get("uid")
            try:
                header_uid = int(request.headers.get("X-User-Id", 0))
            except Exception:
                header_uid = 0
            if not header_uid:
                print(f"[auth] FAIL: X-User-Id yo'q. endpoint={request.path}")
                return jsonify({"ok": False, "error": "Unauthorized"}), 401
            if uid_in_route is not None and header_uid != uid_in_route:
                print(f"[auth] FAIL: uid mos kelmadi. header={header_uid}, route={uid_in_route}")
                return jsonify({"ok": False, "error": "Forbidden"}), 403
            rl_err = rate_limit_check(uid=header_uid, limit=60, window=60)
            if rl_err:
                return rl_err
            return f(*args, **kwargs)
        return decorated

    def _tz_today():
        from datetime import timezone, timedelta
        tz_uz = timezone(timedelta(hours=5))
        return datetime.now(tz_uz)

    def _is_done_today(uid_done):
        """done_today[uid_str] qiymatidan foydalanuvchi bajardimi yoki yo'qligini qaytaradi."""
        if isinstance(uid_done, bool):
            return uid_done
        if isinstance(uid_done, dict):
            return True in uid_done.values()
        return False

    def _calc_best_streak(u):
        """Foydalanuvchining eng uzun streakini qaytaradi (saqlangan yoki joriy habitlardan kattasi)."""
        return max(u.get("best_streak", 0), max((h.get("streak", 0) for h in u.get("habits", [])), default=0))

    @api_app.route("/api/rating")
    def api_rating():
        # Rate limit: 30 so'rov/daqiqa per IP (ochiq endpoint)
        rl_err = rate_limit_check(uid=None, limit=30, window=60)
        if rl_err:
            return rl_err
        from datetime import timedelta
        sort_by = request.args.get("sort", "points")   # points | streak | score
        period  = request.args.get("period", "month")  # month | week | all
        uid_arg = request.args.get("uid", "0")

        today_dt  = _tz_today()
        today_str = today_dt.strftime("%Y-%m-%d")
        days      = [(today_dt - timedelta(days=6-i)).strftime("%Y-%m-%d") for i in range(7)]
        day_lbls  = [(today_dt - timedelta(days=6-i)).strftime("%d") for i in range(7)]

        all_users = load_all_users()
        total_users = len(all_users)

        entries = []
        for uid, udata in all_users.items():
            done_log  = udata.get("done_log", {})
            bot_start = min(done_log.keys()) if done_log else today_str
            # score = oxirgi 30 kunda faol kunlar soni
            score = sum(1 for d, v in done_log.items() if v and d >= (today_dt - timedelta(days=30)).strftime("%Y-%m-%d"))
            # Faol itemlarni yig'amiz (reyting'da ko'rsatish uchun)
            _ITEM_EMOJI = {
                "pet_cat": "🐱", "pet_dog": "🐶", "pet_rabbit": "🐰",
                "badge_fire": "🔥", "badge_star": "⭐", "badge_secret": "👑",
                "car_sport": "🏎️",
            }
            _items = []
            _shown_ids = set()
            if udata.get("active_pet"):
                _items.append(_ITEM_EMOJI.get(udata["active_pet"], udata["active_pet"]))
                _shown_ids.add(udata["active_pet"])
            if udata.get("active_badge"):
                _items.append(_ITEM_EMOJI.get(udata["active_badge"], udata["active_badge"]))
                _shown_ids.add(udata["active_badge"])
            if udata.get("active_car"):
                _items.append(_ITEM_EMOJI.get(udata["active_car"], udata["active_car"]))
                _shown_ids.add(udata["active_car"])
            raw_inv = udata.get("inventory", {})
            if isinstance(raw_inv, list):
                inv_dict = {i: 1 for i in raw_inv}
            else:
                inv_dict = dict(raw_inv)
            for iid, qty in inv_dict.items():
                if qty > 0 and iid not in _shown_ids and iid in _ITEM_EMOJI:
                    _items.append(_ITEM_EMOJI[iid])
                    _shown_ids.add(iid)
            if udata.get("streak_shields", 0) > 0: _items.append("🛡")
            if udata.get("bonus_2x_active") and udata.get("bonus_2x_date") == today_str: _items.append("⚡")
            if udata.get("bonus_3x_active") and udata.get("bonus_3x_date") == today_str: _items.append("🚀")
            if udata.get("xp_booster_days", 0) > 0: _items.append("💎")
            entries.append({
                "uid":          uid,
                "name":         udata.get("name", "?"),
                "points":       udata.get("points", 0),
                "streak":       udata.get("streak", 0),
                "score":        score,
                "photo_url":    udata.get("photo_url", ""),
                "done_log":     done_log,
                "bot_start":    bot_start,
                "habits_count": len(udata.get("habits", [])),
                "jon":          round(udata.get("jon", 100)),
                "active_items": " ".join(_items),
            })

        # Saralash
        if sort_by == "streak":
            entries.sort(key=lambda x: x["streak"], reverse=True)
        elif sort_by in ("score", "active"):
            entries.sort(key=lambda x: x["score"], reverse=True)
        else:
            entries.sort(key=lambda x: x["points"], reverse=True)

        top = entries[:10]

        # Caller entry
        caller_entry = None
        try:
            caller_uid = str(int(uid_arg))
            caller_idx = next((i for i, e in enumerate(entries) if e["uid"] == caller_uid), None)
            if caller_idx is not None:
                caller_entry = dict(entries[caller_idx])
                caller_entry["rank"] = caller_idx + 1
        except Exception:
            pass

        return jsonify({
            "today":        today_str,
            "days":         days,
            "day_labels":   day_lbls,
            "users":        top,
            "total_users":  total_users,
            "sort_by":      sort_by,
            "period":       period,
            "caller_entry": caller_entry,
        })

    @api_app.route("/api/profile/<int:uid>")
    @require_auth
    def api_profile(uid):
        u = load_user(uid)
        # Rank: load_all_users o'rniga tez MongoDB so'rov
        my_points  = u.get("points", 0)
        rank       = mongo_col.count_documents({
            "_id":    {"$not": {"$regex": "^_"}},
            "points": {"$gt": my_points}
        }) + 1
        total_users = mongo_col.count_documents({"_id": {"$not": {"$regex": "^_"}}})
        habits = []
        for h in u.get("habits", []):
            habits.append({
                "name":   h.get("name",""),
                "icon":   h.get("icon","✅"),
                "streak": h.get("streak",0),
            })

        # best_streak va total_done_all hisoblash
        best_streak    = _calc_best_streak(u)
        total_done_all = sum(h.get("total_done", 0) for h in u.get("habits", []))

        today_str = _tz_today().strftime("%Y-%m-%d")
        return jsonify({
            "name":             u.get("name","?"),
            "points":           u.get("points",0),
            "streak":           u.get("streak",0),
            "jon":              u.get("jon",100),
            "is_vip":           u.get("is_vip",False),
            "rank":             rank,
            "total_users":      total_users,
            "joined_at":        u.get("joined_at",""),
            "best_streak":      best_streak,
            "best_streak_date": u.get("best_streak_date", ""),
            "total_done_all":   total_done_all,
            "habits":           habits,
            "xp_booster_days":  u.get("xp_booster_days", 0),
            "active_pet":       {"pet_cat":"🐱","pet_dog":"🐶","pet_rabbit":"🐰"}.get(u.get("active_pet",""), u.get("active_pet","")),
            "active_badge":     {"badge_fire":"🔥","badge_star":"⭐","badge_secret":"👑"}.get(u.get("active_badge",""), u.get("active_badge","")),
            "active_car":       {"car_sport":"🏎️"}.get(u.get("active_car",""), u.get("active_car","")),
            "streak_shields":   u.get("streak_shields", 0),
            "bonus_2x_active":  u.get("bonus_2x_active", False) and u.get("bonus_2x_date","") == today_str,
            "bonus_3x_active":  u.get("bonus_3x_active", False) and u.get("bonus_3x_date","") == today_str,
            "dark_mode":        u.get("dark_mode", False),
            "earned_ach":       len([a for a in u.get("achievements", []) if isinstance(a, dict)]),
            "total_ach":        len(ACHIEVEMENTS),
            "display_name":     u.get("display_name", ""),
            "photo_url":        u.get("photo_url", ""),
            "evening_notify":   u.get("evening_notify", True),
            "lang":             u.get("lang", "uz"),
            "phone":            u.get("phone", ""),
            "ref_count":        len(u.get("referrals", [])),
            "ref_link":         f"https://t.me/{get_bot_username()}?start=ref_{uid}",
        })

    @api_app.route("/api/habits/<int:uid>", methods=["GET"])
    @require_auth
    def api_habits_get(uid):
        u = load_user(uid)
        habits = []
        for h in u.get("habits", []):
            habits.append({
                "id":           h.get("id",""),
                "name":         h.get("name",""),
                "icon":         h.get("icon","✅"),
                "time":         h.get("time","vaqtsiz"),
                "type":         h.get("type","simple"),
                "repeat_count": h.get("repeat_count",1),
                "streak":       h.get("streak",0),
                "total_done":   h.get("total_done",0),
            })
        return jsonify({"habits": habits, "jon": round(u.get("jon", 100))})

    @api_app.route("/api/habits/<int:uid>", methods=["POST"])
    @require_auth
    def api_habits_add(uid):
        import uuid, re as _re
        data  = request.get_json() or {}
        name  = (data.get("name") or "").strip()
        icon  = (data.get("icon") or "✅").strip()
        time_ = (data.get("time") or "vaqtsiz").strip()
        hab_type     = data.get("type", "simple")
        try:
            repeat_count = max(1, min(int(data.get("repeat_count", 1)), 100))
        except (ValueError, TypeError):
            repeat_count = 1
        if not name:
            return jsonify({"ok": False, "error": "Nom bo'sh"}), 400
        if len(name) > 100:
            return jsonify({"ok": False, "error": "Nom 100 belgidan oshmasin"}), 400
        if len(icon) > 10:
            icon = "✅"
        if hab_type not in ("simple", "repeat"):
            hab_type = "simple"
        if time_ != "vaqtsiz" and not _re.match(r"^\d{2}:\d{2}$", time_):
            time_ = "vaqtsiz"
        u = load_user(uid)
        if len(u.get("habits", [])) >= 15:
            return jsonify({"ok": False, "error": "Odatlar soni 15 tadan oshmasin"}), 400
        new_habit = {
            "id":           str(uuid.uuid4())[:8],
            "name":         name,
            "icon":         icon,
            "time":         time_,
            "type":         "repeat" if hab_type == "repeat" else "simple",
            "repeat_count": repeat_count if hab_type == "repeat" else 1,
            "streak":       0,
            "total_done":   0,
            "done_today_count": 0,
            "last_done":    None,
            "created_at":   today_uz5(),
        }
        habits = u.get("habits", [])
        habits.append(new_habit)
        u["habits"] = habits
        save_user(uid, u)
        try:
            schedule_habit(uid, new_habit)
        except Exception as _e: print(f"[warn] schedule_habit: {_e}")
        return jsonify({"ok": True, "habit": new_habit})

    @api_app.route("/api/habits/<int:uid>/<hid>", methods=["PUT"])
    @require_auth
    def api_habits_edit(uid, hid):
        import re as _re
        data  = request.get_json() or {}
        name  = (data.get("name") or "").strip()
        icon  = (data.get("icon") or "✅").strip()
        time_ = (data.get("time") or "vaqtsiz").strip()
        type_ = (data.get("type") or "simple").strip()
        try:
            repeat_count = max(1, min(int(data.get("repeat_count") or 1), 100))
        except (ValueError, TypeError):
            repeat_count = 1
        if not name:
            return jsonify({"ok": False, "error": "Nom bo'sh"}), 400
        if len(name) > 100:
            return jsonify({"ok": False, "error": "Nom 100 belgidan oshmasin"}), 400
        if len(icon) > 10:
            icon = "✅"
        if type_ not in ("simple", "repeat"):
            type_ = "simple"
        if time_ != "vaqtsiz" and not _re.match(r"^\d{2}:\d{2}$", time_):
            time_ = "vaqtsiz"
        u = load_user(uid)
        habits = u.get("habits", [])
        for h in habits:
            if h.get("id") == hid:
                h["name"] = name
                h["icon"] = icon
                h["time"] = time_
                h["type"] = type_
                h["repeat_count"] = repeat_count if type_ == "repeat" else 1
                break
        else:
            return jsonify({"ok": False, "error": "Topilmadi"}), 404
        u["habits"] = habits
        save_user(uid, u)
        # Yangi vaqt bilan qayta rejalashtirish
        edited_h = next((h for h in habits if h.get("id") == hid), None)
        if edited_h:
            try:
                schedule_habit(uid, edited_h)
            except Exception as _e:
                print(f"[warn] schedule_habit edit: {_e}")
        return jsonify({"ok": True})

    @api_app.route("/api/habits/<int:uid>/<hid>", methods=["DELETE"])
    @require_auth
    def api_habits_delete(uid, hid):
        u = load_user(uid)
        habits = u.get("habits", [])
        new_habits = [h for h in habits if h.get("id") != hid]
        if len(new_habits) == len(habits):
            return jsonify({"ok": False, "error": "Topilmadi"}), 404
        u["habits"] = new_habits
        save_user(uid, u)
        try:
            unschedule_habit_today(uid, hid)
        except Exception as _e:
            print(f"[warn] unschedule_habit_today delete: {_e}")
        return jsonify({"ok": True})

    @api_app.route("/api/groups/<int:uid>", methods=["GET", "POST"])
    @require_auth
    def api_groups(uid):
        if request.method == "POST":
            import uuid as _uuid
            data       = request.get_json(force=True, silent=True) or {}
            name       = (data.get("name") or "").strip()
            habit_name = (data.get("habit_name") or "").strip()
            habit_time = (data.get("habit_time") or "vaqtsiz").strip()
            if not name or not habit_name:
                return jsonify({"ok": False, "error": "Ism va odat nomi kerak"})
            u = load_user(uid)
            admin_groups = [g for g in u.get("groups", []) if str(g.get("admin_id", "")) == str(uid)]
            if len(admin_groups) >= 3:
                return jsonify({"ok": False, "error": "Siz admin sifatida 3 tadan ko'p guruh yarata olmaysiz"})
            g_id = str(_uuid.uuid4())[:8]
            group = {
                "id":         g_id,
                "name":       name,
                "habit_name": habit_name,
                "habit_time": habit_time,
                "admin_id":   str(uid),
                "members":    [str(uid)],
                "streak":     0,
                "created_at": today_uz5(),
            }
            save_group(g_id, group)
            groups = u.get("groups", [])
            groups.append({"id": g_id, "name": name, "admin_id": str(uid)})
            u["groups"] = groups
            save_user(uid, u)
            inv_link = f"https://t.me/{get_bot_username()}?start=grp_{g_id}"
            return jsonify({"ok": True, "gid": g_id, "invite_link": inv_link})
        # GET
        try:
            all_groups = list(mongo_db["groups"].find({"members": str(uid)}))
        except Exception:
            all_groups = []
        result = []
        today_grp = today_uz5()
        for g in all_groups:
            members_raw = g.get("members", [])
            members = []
            for mid in members_raw[:10]:
                mu = load_user(int(mid))
                members.append({"name": mu.get("name","?"), "points": mu.get("points",0)})
            members.sort(key=lambda x: x["points"], reverse=True)
            # done_today_me: foydalanuvchi bugun bajardimi?
            done_today = g.get("done_today", {}) if g.get("done_date") == today_grp else {}
            uid_done = done_today.get(str(uid), {})
            done_today_me = _is_done_today(uid_done)
            # Haftalik maqsad progress hisoblash
            from datetime import timezone as _tz_wg, timedelta as _td_wg
            _tz_uz_wg  = _tz_wg(_td_wg(hours=5))
            _now_wg    = datetime.now(_tz_uz_wg)
            # Haftaning dushanbasi
            _week_start = (_now_wg - _td_wg(days=_now_wg.weekday())).strftime("%Y-%m-%d")
            _week_days  = [(_now_wg - _td_wg(days=_now_wg.weekday()-i)).strftime("%Y-%m-%d") for i in range(7)]
            _done_log   = g.get("member_done_log", {})
            _weekly_done = 0
            for _mid in members_raw:
                _mid_log = _done_log.get(str(_mid), {})
                for _wd in _week_days:
                    if _mid_log.get(_wd):
                        _weekly_done += 1
            _weekly_total  = len(members_raw) * 7  # maksimal mumkin
            _weekly_goal   = g.get("weekly_goal", 0)
            result.append({
                "gid":          g.get("id", str(g.get("_id", ""))),
                "name":         g.get("name","Guruh"),
                "habit_name":   g.get("habit_name", "—"),
                "member_count": len(members_raw),
                "members":      members[:5],
                "streak":       g.get("streak", 0),
                "is_admin":     g.get("admin_id") == str(uid),
                "invite_link":  f"https://t.me/{get_bot_username()}?start=grp_{g.get('id','')}",  # barcha a'zolarga
                "done_today_me": done_today_me,
                "weekly_goal":  _weekly_goal,
                "weekly_done":  _weekly_done,
                "weekly_total": _weekly_total,
            })
        return jsonify({"groups": result})

    @api_app.route("/api/groups/<int:uid>/<gid>/checkin", methods=["POST"])
    @require_auth
    def api_groups_checkin(uid, gid):
        try:
            g = mongo_db["groups"].find_one({"id": gid})
        except Exception:
            return jsonify({"ok": False, "error": "Guruh topilmadi"})
        if not g:
            return jsonify({"ok": False, "error": "Guruh topilmadi"})
        members = g.get("members", [])
        if str(uid) not in [str(m) for m in members]:
            return jsonify({"ok": False, "error": "Siz bu guruh a'zosi emassiz"})
        today = today_uz5()
        if g.get("done_date") != today:
            g["done_today"] = {}
            g["done_date"]  = today
        done_today = g.get("done_today", {})
        uid_str = str(uid)
        # Toggle: allaqachon bajarilgan bo'lsa — bekor qilish
        uid_done = done_today.get(uid_str, {})
        already_done = _is_done_today(uid_done)
        u = load_user(uid)
        if already_done:
            done_today[uid_str] = False
            g["done_today"] = done_today
            # member_done_log dan bugungi yozuvni olib tashlash
            done_log = g.get("member_done_log", {})
            if uid_str in done_log:
                done_log[uid_str].pop(today, None)
            g["member_done_log"] = done_log
            mongo_db["groups"].replace_one({"id": gid}, g)
            u["points"] = max(0, u.get("points", 0) - 5)
            save_user(uid, u)
            return jsonify({"ok": True, "done": False, "points": u.get("points", 0)})
        # Bajarildi
        done_today[uid_str] = {"main": True}
        g["done_today"] = done_today
        done_count = sum(1 for v in done_today.values() if (v is True or (isinstance(v, dict) and True in v.values())))
        all_done = done_count == len(members)
        if all_done and g.get("streak_date") != today:
            g["streak"]      = g.get("streak", 0) + 1
            g["streak_date"] = today
        # member_done_log
        done_log = g.get("member_done_log", {})
        if uid_str not in done_log:
            done_log[uid_str] = {}
        already_logged_today = done_log[uid_str].get(today, False)
        done_log[uid_str][today] = True
        g["member_done_log"] = done_log
        # member_streaks
        if not already_logged_today:
            from datetime import timezone, timedelta as _td
            _tz = timezone(_td(hours=5))
            yesterday_s = (datetime.now(_tz) - _td(days=1)).strftime("%Y-%m-%d")
            m_streaks = g.get("member_streaks", {})
            if done_log[uid_str].get(yesterday_s):
                m_streaks[uid_str] = m_streaks.get(uid_str, 0) + 1
            else:
                m_streaks[uid_str] = 1
            g["member_streaks"] = m_streaks
        mongo_db["groups"].replace_one({"id": gid}, g)
        u["points"] = u.get("points", 0) + 5
        save_user(uid, u)
        m_streak_val = g.get("member_streaks", {}).get(uid_str, 1)
        return jsonify({
            "ok":       True,
            "done":     True,
            "points":   u.get("points", 0),
            "streak":   m_streak_val,
            "all_done": all_done,
        })

    @api_app.route("/api/groups/<int:uid>/<gid>/goal", methods=["PUT"])
    @require_auth
    def api_groups_set_goal(uid, gid):
        """Admin haftalik guruh maqsadini belgilaydi."""
        data = request.get_json(force=True, silent=True) or {}
        try:
            g = mongo_db["groups"].find_one({"id": gid})
        except Exception:
            return jsonify({"ok": False, "error": "Guruh topilmadi"})
        if not g:
            return jsonify({"ok": False, "error": "Guruh topilmadi"})
        if g.get("admin_id") != str(uid):
            return jsonify({"ok": False, "error": "Faqat admin maqsad belgilaydi"})
        try:
            goal = int(data.get("goal", 0))
            if goal < 0 or goal > 9999:
                raise ValueError
        except (ValueError, TypeError):
            return jsonify({"ok": False, "error": "Noto'g'ri qiymat"})
        g["weekly_goal"] = goal
        mongo_db["groups"].replace_one({"id": gid}, g)
        return jsonify({"ok": True, "weekly_goal": goal})

    @api_app.route("/api/groups/<int:uid>/<gid>", methods=["DELETE"])
    @require_auth
    def api_groups_delete(uid, gid):
        try:
            g = mongo_db["groups"].find_one({"id": gid})
        except Exception:
            return jsonify({"ok": False, "error": "Guruh topilmadi"})
        if not g:
            return jsonify({"ok": False, "error": "Guruh topilmadi"})
        if g.get("admin_id") != str(uid):
            return jsonify({"ok": False, "error": "Faqat admin o'chira oladi"})
        try:
            mongo_db["groups"].delete_one({"id": gid})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)})
        # Barcha a'zolar user profilidan ham o'chirish
        for mid in g.get("members", []):
            try:
                mu = load_user(int(mid))
                mu["groups"] = [gg for gg in mu.get("groups", []) if gg.get("id") != gid]
                save_user(int(mid), mu)
            except Exception:
                pass
        return jsonify({"ok": True})

    @api_app.route("/api/today/<int:uid>")
    @require_auth
    def api_today(uid):
        u = load_user(uid)
        today = today_uz5()
        habits = u.get("habits", [])
        result = []
        done_count = 0
        for h in habits:
            hab_type  = h.get("type", "simple")
            rep_count = h.get("repeat_count", 1)
            today_count = 0
            if hab_type == "repeat" and rep_count > 1:
                if h.get("done_date") == today:
                    today_count = h.get("done_today_count", 0)
                is_done = today_count >= rep_count
            else:
                is_done = h.get("last_done") == today
            if is_done:
                done_count += 1
            result.append({
                "id":           h["id"],
                "name":         h["name"],
                "icon":         h.get("icon", "✅"),
                "time":         h.get("time", "vaqtsiz"),
                "done":         is_done,
                "streak":       h.get("streak", 0),
                "repeat_count": rep_count,
                "today_count":  today_count,
                "type":         hab_type,
            })
        total = len(habits)
        percent = round(done_count / total * 100) if total else 0
        jon_pct = min(100, max(0, u.get("jon", 100)))
        return jsonify({
            "habits":     result,
            "today":      today,
            "done_count": done_count,
            "total":      total,
            "percent":    percent,
            "jon":        jon_pct,
            "points":     u.get("points", 0),
            "streak":     u.get("streak", 0),
            "lang":       get_lang(uid),
        })

    @api_app.route("/api/checkin/<int:uid>/<hid>", methods=["POST"])
    @require_auth
    def api_checkin(uid, hid):
        u = load_user(uid)
        today = today_uz5()
        habits = u.get("habits", [])
        points_before = u.get("points", 0)
        found_h = None
        for h in habits:
            if h["id"] == hid:
                found_h = h
                hab_type  = h.get("type", "simple")
                rep_count = h.get("repeat_count", 1)
                if hab_type == "repeat" and rep_count > 1:
                    done = h.get("done_today_count", 0)
                    if h.get("done_date") != today:
                        done = 0
                    if done >= rep_count:
                        # Allaqachon to'liq bajarilgan — bekor qilish (0 ga tushirish)
                        done = 0
                        h["last_done"] = None
                        h["streak"] = max(0, h.get("streak", 0) - 1)
                        _undo_base = 5
                        if u.get("bonus_3x_active") and u.get("bonus_3x_date") == today:
                            _undo_base = 15
                        elif u.get("bonus_2x_active") and u.get("bonus_2x_date") == today:
                            _undo_base = 10
                        if u.get("xp_booster_days", 0) > 0:
                            _undo_base = round(_undo_base * 1.1)
                        u["points"] = max(0, u.get("points", 0) - _undo_base)
                        # Global streak: faqat bugun boshqa birorta odat bajarilmagan bo'lsa kamaytir
                        _still_done = any(hh.get("last_done") == today for hh in habits if hh["id"] != hid)
                        if not _still_done and u.get("streak_last_date") == today:
                            u["streak"] = max(0, u.get("streak", 0) - 1)
                            u["streak_last_date"] = ""
                    else:
                        done += 1
                        if done >= rep_count:
                            h["last_done"] = today
                            h["streak"] = h.get("streak", 0) + 1
                            # Global streak: kuniga bir marta oshsin
                            if u.get("streak_last_date") != today:
                                u["streak"] = u.get("streak", 0) + 1
                                u["streak_last_date"] = today
                                if u["streak"] > u.get("best_streak", 0):
                                    u["best_streak"] = u["streak"]
                                    u["best_streak_date"] = today
                            _base = 5
                            if u.get("bonus_3x_active") and u.get("bonus_3x_date") == today:
                                _base = 15
                            elif u.get("bonus_2x_active") and u.get("bonus_2x_date") == today:
                                _base = 10
                            if u.get("xp_booster_days", 0) > 0:
                                _base = round(_base * 1.1)
                            u["points"] = u.get("points", 0) + _base
                    h["done_today_count"] = done
                    h["done_date"] = today
                    is_done = done >= rep_count
                    today_count = done
                else:
                    if h.get("last_done") == today:
                        h["last_done"] = None
                        h["streak"] = max(0, h.get("streak", 0) - 1)
                        _undo_base = 5
                        if u.get("bonus_3x_active") and u.get("bonus_3x_date") == today:
                            _undo_base = 15
                        elif u.get("bonus_2x_active") and u.get("bonus_2x_date") == today:
                            _undo_base = 10
                        if u.get("xp_booster_days", 0) > 0:
                            _undo_base = round(_undo_base * 1.1)
                        u["points"] = max(0, u.get("points", 0) - _undo_base)
                        # Global streak: faqat bugun boshqa birorta odat bajarilmagan bo'lsa kamaytir
                        _still_done = any(hh.get("last_done") == today for hh in habits if hh["id"] != hid)
                        if not _still_done and u.get("streak_last_date") == today:
                            u["streak"] = max(0, u.get("streak", 0) - 1)
                            u["streak_last_date"] = ""
                        is_done = False
                    else:
                        from datetime import timezone, timedelta as _td
                        _tz = timezone(_td(hours=5))
                        _yesterday = (datetime.now(_tz) - _td(days=1)).strftime("%Y-%m-%d")
                        h["streak"] = h.get("streak", 0) + 1 if h.get("last_done") == _yesterday else 1
                        h["last_done"] = today
                        _base = 5
                        if u.get("bonus_3x_active") and u.get("bonus_3x_date") == today:
                            _base = 15
                        elif u.get("bonus_2x_active") and u.get("bonus_2x_date") == today:
                            _base = 10
                        if u.get("xp_booster_days", 0) > 0:
                            _base = round(_base * 1.1)
                        u["points"] = u.get("points", 0) + _base
                        # Global streak: kuniga bir marta oshsin
                        if u.get("streak_last_date") != today:
                            u["streak"] = u.get("streak", 0) + 1
                            u["streak_last_date"] = today
                            if u["streak"] > u.get("best_streak", 0):
                                u["best_streak"] = u["streak"]
                                u["best_streak_date"] = today
                        is_done = True
                    today_count = 1 if is_done else 0
                break
        u["habits"] = habits
        # History yangilash (statistika uchun)
        history = u.get("history", {})
        day_data = history.get(today, {})
        done_count_now = sum(1 for hh in habits if hh.get("last_done") == today)
        total_now = len(habits)
        # Har bir odat holatini ham saqlash
        hab_map = day_data.get("habits", {})
        if found_h:
            hab_map[hid] = found_h.get("last_done") == today
        day_data["done"]   = done_count_now
        day_data["total"]  = total_now
        day_data["habits"] = hab_map
        # Smart reminder uchun checkin vaqtini saqlash
        _ctimes = day_data.get("checkin_times", {})
        if found_h:
            if is_done:
                from datetime import datetime as _dt_sr, timedelta as _td_sr
                _ctimes[hid] = (_dt_sr.now() + _td_sr(hours=5)).strftime("%H:%M")
            else:
                _ctimes.pop(hid, None)
        day_data["checkin_times"] = _ctimes
        history[today] = day_data
        u["history"] = history
        # done_log yangilash (rating score uchun — 30 kunlik faollik)
        if is_done:
            done_log = u.get("done_log", {})
            done_log[today] = True
            u["done_log"] = done_log
        elif not is_done and found_h:
            # Undo: agar bugun hech bir odat bajarilmagan bo'lsa — done_log dan o'chirish
            still_any_done = any(hh.get("last_done") == today for hh in habits if hh["id"] != hid)
            if not still_any_done:
                done_log = u.get("done_log", {})
                done_log.pop(today, None)
                u["done_log"] = done_log
        # total_done yangilash (achievements uchun)
        if found_h:
            if is_done and found_h.get("last_done") == today:
                found_h["total_done"] = found_h.get("total_done", 0) + 1
            elif not is_done:
                found_h["total_done"] = max(0, found_h.get("total_done", 0) - 1)
        # XP booster kunini kamaytirish (kuniga bir marta)
        if u.get("xp_booster_days", 0) > 0:
            last_boost = u.get("xp_booster_last_day", "")
            if last_boost != today:
                u["xp_booster_days"] = max(0, u["xp_booster_days"] - 1)
                u["xp_booster_last_day"] = today
        save_user(uid, u)
        if not found_h:
            return jsonify({"ok": False, "error": "Odat topilmadi"})
        # done_count hisoblash
        done_count = sum(1 for hh in habits if hh.get("last_done") == today)
        total = len(habits)
        all_done = done_count == total and total > 0
        # Yutuqlarni tekshir
        new_ach = check_achievements(uid, u)
        new_badges = [{"id": a["id"], "icon": a["icon"], "title": a["title"]} for a in new_ach]
        # Streak milestone tekshiruvi (WebApp uchun — bot xabar yubormasdan, faqat response orqali)
        streak_milestone = None
        new_global_streak = u.get("streak", 0)
        if is_done and new_global_streak in STREAK_MILESTONES:
            ms = STREAK_MILESTONES[new_global_streak]
            sent_list = u.get("streak_milestones_sent", [])
            if new_global_streak not in sent_list:
                u["points"] = u.get("points", 0) + ms["bonus"]
                sent_list.append(new_global_streak)
                u["streak_milestones_sent"] = sent_list
                save_user(uid, u)
                streak_milestone = {
                    "streak": new_global_streak,
                    "emoji":  ms["emoji"],
                    "title":  ms["title"],
                    "bonus":  ms["bonus"],
                }
        return jsonify({
            "ok":              True,
            "done":            is_done,
            "streak":          found_h.get("streak", 0),
            "repeat_count":    found_h.get("repeat_count", 1),
            "today_count":     today_count,
            "points":          u.get("points", 0),
            "earned":          u.get("points", 0) - points_before,
            "all_done":        all_done,
            "done_count":      done_count,
            "total":           total,
            "new_badges":      new_badges,
            "streak_milestone": streak_milestone,
        })

    def _calc_trend(history, habits, now_uz, total):
        """Joriy hafta vs oldingi hafta bajarilish foizini solishtiradi."""
        from datetime import timedelta
        def week_pct(offset_start, offset_end):
            scores = []
            for i in range(offset_start, offset_end, -1):
                d = (now_uz - timedelta(days=i)).strftime("%Y-%m-%d")
                day_data = history.get(d, {})
                done  = day_data.get("done", 0)
                tot   = day_data.get("total", 0) or total
                if tot > 0:
                    scores.append(done / tot * 100)
                else:
                    scores.append(0)
            return round(sum(scores) / len(scores)) if scores else 0

        this_week = week_pct(6,  -1)   # oxirgi 7 kun (0..6)
        prev_week = week_pct(13,  6)   # undan oldingi 7 kun (7..13)
        diff = this_week - prev_week
        if diff > 5:
            direction = "up"
        elif diff < -5:
            direction = "down"
        else:
            direction = "same"
        return {
            "this_week": this_week,
            "prev_week": prev_week,
            "diff":      diff,
            "direction": direction,
        }

    @api_app.route("/api/stats/<int:uid>")
    @require_auth
    def api_stats(uid):
        from datetime import datetime, timedelta
        u = load_user(uid)
        habits = u.get("habits", [])
        today = today_uz5()
        now_uz = datetime.now() + timedelta(hours=5)
        done_today = sum(1 for h in habits if h.get("last_done") == today)
        total = len(habits)
        history = u.get("history", {})
        # 30 kunlik sanalar
        days_30 = []
        for i in range(29, -1, -1):
            d = (now_uz - timedelta(days=i)).strftime("%Y-%m-%d")
            days_30.append(d)
        # Heatmap
        # Bugungi holat uchun habits.last_done dan to'ldirish
        if not history.get(today, {}).get("done"):
            done_today_count = sum(1 for h in habits if h.get("last_done") == today)
            if done_today_count > 0:
                td = history.get(today, {})
                if not td.get("habits"):
                    td["habits"] = {h["id"]: (h.get("last_done") == today) for h in habits}
                td["done"]  = done_today_count
                td["total"] = total
                history[today] = td
        heatmap = {}
        for d in days_30:
            day_data = history.get(d, {})
            heatmap[d] = day_data.get("done", 0) > 0
        # Haftalik (oxirgi 7 kun)
        weekly = []
        for i in range(6, -1, -1):
            d = (now_uz - timedelta(days=i)).strftime("%Y-%m-%d")
            day_data = history.get(d, {})
            w_count = day_data.get("done", 0)
            w_total = day_data.get("total", 0)
            if w_count == 0 and w_total == 0:
                w_count = sum(1 for h in habits if h.get("last_done") == d)
                w_total = total
            weekly.append({
                "date":  d,
                "count": w_count,
                "total": w_total or total,
            })
        # Oylik (oxirgi 30 kun)
        monthly = []
        for i in range(29, -1, -1):
            d = (now_uz - timedelta(days=i)).strftime("%Y-%m-%d")
            day_data = history.get(d, {})
            hist_count = day_data.get("done", 0)
            hist_total = day_data.get("total", 0)
            # history bo'sh bo'lsa — habits dagi last_done dan hisoblash
            if hist_count == 0 and hist_total == 0:
                hist_count = sum(1 for h in habits if h.get("last_done") == d)
                hist_total = total
            monthly.append({
                "date":  d,
                "count": hist_count,
                "total": hist_total or total,
            })
        # Faol kunlar (30)
        active_days_30 = sum(1 for d in days_30 if heatmap.get(d))
        # Har bir odat statistikasi
        habit_stats = []
        for h in habits:
            # history dan hisoblash (yangi ma'lumotlar)
            done_7_hist  = sum(1 for i in range(7)  if history.get((now_uz-timedelta(days=i)).strftime("%Y-%m-%d"),{}).get("habits",{}).get(h["id"]))
            done_30_hist = sum(1 for i in range(30) if history.get((now_uz-timedelta(days=i)).strftime("%Y-%m-%d"),{}).get("habits",{}).get(h["id"]))
            week_dots = [bool(history.get((now_uz-timedelta(days=6-i)).strftime("%Y-%m-%d"),{}).get("habits",{}).get(h["id"])) for i in range(7)]
            # Agar history bo'sh bo'lsa (eski foydalanuvchilar) — streak va total_done dan foydalanish
            total_done_saved = h.get("total_done", 0)
            streak_val = h.get("streak", 0)
            # done_7: history mavjud bo'lsa undan, yo'qsa streak dan taxminan
            done_7  = done_7_hist  if done_7_hist  > 0 else min(streak_val, 7)
            done_30 = done_30_hist if done_30_hist > 0 else min(total_done_saved, 30)
            # done_all: total_done field eng ishonchli
            done_all = total_done_saved if total_done_saved > 0 else done_30_hist
            # week_dots: history bo'sh bo'lsa last_done asosida bugungi katakni to'ldirish
            if not any(week_dots) and h.get("last_done") == today:
                week_dots[-1] = True
            # percent: done_30 asosida
            percent = round(done_30 / 30 * 100)
            # 66 kun kalkulyatori
            from datetime import datetime as _dt66
            _created = h.get("created_at", "")
            _days_since = 0
            if _created:
                try:
                    _days_since = (now_uz.date() - _dt66.fromisoformat(_created).date()).days + 1
                except Exception:
                    _days_since = 0
            _days_66 = min(66, max(_days_since, done_all, streak_val))
            _days_66_done = min(done_all, 66)
            habit_stats.append({
                "id":         h["id"],
                "name":       h["name"],
                "icon":       h.get("icon", "✅"),
                "streak":     streak_val,
                "percent":    percent,
                "done_7":     done_7,
                "done_30":    done_30,
                "total_done": done_all,
                "week_dots":  week_dots,
                "days_66":      _days_66,
                "days_66_done": _days_66_done,
            })
        return jsonify({
            "today":   today,
            "summary": {
                "streak":        u.get("streak", 0),
                "points":        u.get("points", 0),
                "active_days_30": active_days_30,
                "total_habits":  total,
                "best_streak":   _calc_best_streak(u),
            },
            "weekly":      weekly,
            "monthly":     monthly,
            "heatmap":     heatmap,
            "days_30":     days_30,
            "habit_stats": habit_stats,
            "points":      u.get("points", 0),
            "streak":      u.get("streak", 0),
            "trend":       _calc_trend(history, habits, now_uz, total),
        })


    # ── Yutuqlar (Achievements) ──
    ACHIEVEMENTS = [
        # Streak
        {"id":"streak_3",    "cat":"streak",  "icon":"🔥", "title":"Ilk olov",       "desc":"3 kun ketma-ket bajaring",     "req":3,    "field":"streak"},
        {"id":"streak_7",    "cat":"streak",  "icon":"🌟", "title":"Haftalik qahramon","desc":"7 kun ketma-ket bajaring",    "req":7,    "field":"streak"},
        {"id":"streak_30",   "cat":"streak",  "icon":"💎", "title":"Oylik ustoz",     "desc":"30 kun ketma-ket bajaring",   "req":30,   "field":"streak"},
        {"id":"streak_100",  "cat":"streak",  "icon":"👑", "title":"100 kun shohi",   "desc":"100 kun ketma-ket bajaring",  "req":100,  "field":"streak"},
        # Ball
        {"id":"pts_100",     "cat":"ball",    "icon":"⭐", "title":"Birinchi yulduz", "desc":"100 ball to'plang",           "req":100,  "field":"points"},
        {"id":"pts_500",     "cat":"ball",    "icon":"🌠", "title":"Yulduz yomg'iri","desc":"500 ball to'plang",           "req":500,  "field":"points"},
        {"id":"pts_1000",    "cat":"ball",    "icon":"🏆", "title":"Ming ball",       "desc":"1000 ball to'plang",          "req":1000, "field":"points"},
        {"id":"pts_5000",    "cat":"ball",    "icon":"💰", "title":"Ball millioneri", "desc":"5000 ball to'plang",          "req":5000, "field":"points"},
        # Odat soni
        {"id":"hab_1",       "cat":"odat",    "icon":"🌱", "title":"Birinchi qadam",  "desc":"1 ta odat qo'shing",          "req":1,    "field":"habits_count"},
        {"id":"hab_5",       "cat":"odat",    "icon":"🌿", "title":"To'plam",         "desc":"5 ta odat qo'shing",          "req":5,    "field":"habits_count"},
        {"id":"hab_10",      "cat":"odat",    "icon":"🌳", "title":"Bog'bon",         "desc":"10 ta odat qo'shing",         "req":10,   "field":"habits_count"},
        # Jami bajarilgan
        {"id":"done_10",     "cat":"faollik", "icon":"✅", "title":"O'n marta",       "desc":"Jami 10 ta odat bajaring",    "req":10,   "field":"total_done"},
        {"id":"done_50",     "cat":"faollik", "icon":"🎯", "title":"Ellik marta",     "desc":"Jami 50 ta odat bajaring",    "req":50,   "field":"total_done"},
        {"id":"done_100",    "cat":"faollik", "icon":"🚀", "title":"Yuz marta",       "desc":"Jami 100 ta odat bajaring",   "req":100,  "field":"total_done"},
        {"id":"done_500",    "cat":"faollik", "icon":"⚡", "title":"Besh yuz",        "desc":"Jami 500 ta odat bajaring",   "req":500,  "field":"total_done"},
        # Do'stlar
        {"id":"friend_1",    "cat":"ijtimoiy","icon":"🤝", "title":"Birinchi do'st",  "desc":"1 ta do'st qo'shing",         "req":1,    "field":"friends_count"},
        {"id":"friend_5",    "cat":"ijtimoiy","icon":"👥", "title":"Jamoatchi",       "desc":"5 ta do'st qo'shing",         "req":5,    "field":"friends_count"},
    ]

    CAT_LABELS = {
        "streak":  {"uz":"Streak","ru":"Streak","en":"Streak"},
        "ball":    {"uz":"Ball","ru":"Очки","en":"Points"},
        "odat":    {"uz":"Odat","ru":"Привычки","en":"Habits"},
        "faollik": {"uz":"Faollik","ru":"Активность","en":"Activity"},
        "ijtimoiy":{"uz":"Ijtimoiy","ru":"Социальные","en":"Social"},
    }

    def check_achievements(uid, u):
        """Yangi qozonilgan yutuqlarni tekshiradi, qaytaradi: list of new achievement dicts"""
        earned_ids = {a["id"] for a in u.get("achievements", []) if isinstance(a, dict)}
        streak      = u.get("streak", 0)
        points      = u.get("points", 0)
        habits      = u.get("habits", [])
        total_done  = sum(h.get("total_done", 0) for h in habits)
        friends_cnt = len(u.get("friends", []))
        habits_cnt  = len(habits)

        field_vals = {
            "streak":       streak,
            "points":       points,
            "habits_count": habits_cnt,
            "total_done":   total_done,
            "friends_count":friends_cnt,
        }

        new_ach = []
        ach_list = list(u.get("achievements", []))
        changed = False
        for ach in ACHIEVEMENTS:
            if ach["id"] in earned_ids:
                continue
            val = field_vals.get(ach["field"], 0)
            if val >= ach["req"]:
                ach_list.append({"id": ach["id"], "earned_at": today_uz5()})
                new_ach.append(ach)
                changed = True
        if changed:
            u["achievements"] = ach_list
            save_user(uid, u)
        return new_ach

    @api_app.route("/api/achievements/<int:uid>")
    @require_auth
    def api_achievements(uid):
        u    = load_user(uid)
        lang = u.get("lang", "uz")
        earned_ids = {a["id"] for a in u.get("achievements", []) if isinstance(a, dict)}
        streak      = u.get("streak", 0)
        points      = u.get("points", 0)
        habits      = u.get("habits", [])
        total_done  = sum(h.get("total_done", 0) for h in habits)
        friends_cnt = len(u.get("friends", []))
        habits_cnt  = len(habits)
        field_vals  = {
            "streak":       streak,
            "points":       points,
            "habits_count": habits_cnt,
            "total_done":   total_done,
            "friends_count":friends_cnt,
        }
        result = []
        cats_seen = {}
        for ach in ACHIEVEMENTS:
            earned = ach["id"] in earned_ids
            current = min(field_vals.get(ach["field"], 0), ach["req"])
            cat_id  = ach["cat"]
            if cat_id not in cats_seen:
                label = CAT_LABELS.get(cat_id, {}).get(lang, cat_id)
                cats_seen[cat_id] = {"id": cat_id, "label": label}
            result.append({
                "id":      ach["id"],
                "cat":     cat_id,
                "icon":    ach["icon"],
                "title":   ach["title"],
                "desc":    ach["desc"],
                "req":     ach["req"],
                "current": current,
                "earned":  1 if earned else 0,
            })
        earned_count = sum(1 for a in result if a["earned"])
        return jsonify({
            "achievements": result,
            "cats":         list(cats_seen.values()),
            "earned_count": earned_count,
            "total_count":  len(result),
        })

    @api_app.route("/api/shop/<int:uid>")
    @require_auth
    def api_shop(uid):
        u = load_user(uid)
        shop_items = [
            {"id": "shield_1",    "name": "Streak himoyasi",  "cat": "protection", "emoji": "🛡",  "price_ball": 100,  "price_stars": 0, "desc": "1 kunlik streak himoyasi"},
            {"id": "shield_3",    "name": "3x Streak freeze", "cat": "protection", "emoji": "🧊",  "price_ball": 250,  "price_stars": 0, "desc": "3 kunlik streak himoyasi"},
            {"id": "bonus_2x",    "name": "2x Ball bonus",    "cat": "bonus",      "emoji": "⚡",  "price_ball": 150,  "price_stars": 0, "desc": "1 kun uchun 2x ball"},
            {"id": "bonus_3x",    "name": "3x Ball bonus",    "cat": "bonus",      "emoji": "🚀",  "price_ball": 300,  "price_stars": 0, "desc": "1 kun uchun 3x ball"},
            {"id": "xp_booster",  "name": "XP Booster",       "cat": "bonus",      "emoji": "💎",  "price_ball": 400,  "price_stars": 0, "desc": "7 kun davomida +10% qo'shimcha ball"},
            {"id": "badge_fire",  "name": "Olov badge",       "cat": "badge",      "emoji": "🔥",  "price_ball": 200,  "price_stars": 0, "desc": "Profilda ko'rsatiladi"},
            {"id": "badge_star",  "name": "Yulduz badge",     "cat": "badge",      "emoji": "⭐",  "price_ball": 250,  "price_stars": 0, "desc": "Profilda ko'rsatiladi"},
            {"id": "badge_secret","name": "Maxfiy badge",     "cat": "badge",      "emoji": "👑",  "price_ball": 600,  "price_stars": 0, "desc": "Noyob toj — faqat bozordan"},
            {"id": "pet_cat",     "name": "Mushuk",           "cat": "pet",        "emoji": "🐱",  "price_ball": 300,  "price_stars": 0, "desc": "Sevimli mushukcha"},
            {"id": "pet_dog",     "name": "It",               "cat": "pet",        "emoji": "🐶",  "price_ball": 350,  "price_stars": 0, "desc": "Sodiq do'st"},
            {"id": "pet_rabbit",  "name": "Quyon",            "cat": "pet",        "emoji": "🐰",  "price_ball": 300,  "price_stars": 0, "desc": "Tez-tez sakrashi"},
            {"id": "car_sport",   "name": "Sport mashina",    "cat": "car",        "emoji": "🏎️", "price_ball": 500,  "price_stars": 0, "desc": "Tez mashina"},
            {"id": "jon_restore", "name": "Jon tiklash",      "cat": "bonus",      "emoji": "❤️", "price_ball": 25,   "price_stars": 0, "desc": "Jonni 100% ga tiklash (faqat 20% va kam holda)"},
            {"id": "gift_box",    "name": "Sovga qutisi",     "cat": "gift",       "emoji": "🎁",  "price_ball": 0,    "price_stars": 5, "desc": "Tasodifiy mukofot"},
        ]
        raw_inventory = u.get("inventory", [])
        # inventory: list -> dict formatiga
        if isinstance(raw_inventory, list):
            inventory = {item_id: 1 for item_id in raw_inventory}
        else:
            inventory = raw_inventory
        active_pet   = u.get("active_pet", "")
        active_badge = u.get("active_badge", "")
        active_car   = u.get("active_car", "")
        # can_buy va owned fieldlarini har bir item ga qo'shish
        one_time = ["badge_fire","badge_star","badge_secret","pet_cat","pet_dog","pet_rabbit","car_sport"]
        # Counter fieldlardan owned miqdorini to'ldirish
        _counter_owned = {
            "shield_1":  min(u.get("streak_shields", 0), 1) if u.get("streak_shields", 0) > 0 else 0,
            "shield_3":  max(0, u.get("streak_shields", 0) - 1) if u.get("streak_shields", 0) > 1 else 0,
            "bonus_2x":  1 if (u.get("bonus_2x_active") and u.get("bonus_2x_date") == today_uz5()) else 0,
            "bonus_3x":  1 if (u.get("bonus_3x_active") and u.get("bonus_3x_date") == today_uz5()) else 0,
            "xp_booster": u.get("xp_booster_days", 0),
        }
        for item in shop_items:
            if item["id"] in _counter_owned:
                owned_qty = _counter_owned[item["id"]]
            else:
                owned_qty = inventory.get(item["id"], 0)
            item["owned"] = owned_qty
            # Bir martalik narsalar: allaqachon olingan bo'lsa can_buy=False
            if item["id"] in one_time:
                item["can_buy"] = owned_qty == 0
            else:
                item["can_buy"] = True
        return jsonify({
            "points":       u.get("points", 0),
            "items":        shop_items,
            "inventory":    inventory,
            "active_pet":   active_pet,
            "active_badge": active_badge,
            "active_car":   active_car,
        })

    @api_app.route("/api/shop/<int:uid>/buy", methods=["POST"])
    @require_auth
    def api_shop_buy(uid):
        data = request.get_json() or {}
        item_id   = data.get("item_id", "")
        pay_type  = data.get("type", "ball")  # "ball" yoki "stars"
        prices = {
            "shield_1": 100, "shield_3": 250,
            "bonus_2x": 150, "bonus_3x": 300, "xp_booster": 400,
            "badge_fire": 200, "badge_star": 250, "badge_secret": 600,
            "pet_cat": 300, "pet_dog": 350, "pet_rabbit": 300, "car_sport": 500,
            "jon_restore": 25,
        }
        price = prices.get(item_id, 0)
        if not price and item_id != "gift_box":
            return jsonify({"ok": False, "error": "Noma'lum mahsulot"})
        u = load_user(uid)
        raw_inv = u.get("inventory", [])
        if isinstance(raw_inv, list):
            inventory = {i: 1 for i in raw_inv}
        else:
            inventory = raw_inv
        # Faqat badge/pet/car bir marta sotib olinadi
        one_time = ["badge_fire","badge_star","badge_secret","pet_cat","pet_dog","pet_rabbit","car_sport"]
        if item_id in one_time and inventory.get(item_id, 0) > 0:
            return jsonify({"ok": False, "error": "Allaqachon sotib olingan"})
        if item_id == "jon_restore":
            jon_val = round(u.get("jon", 100.0))
            if jon_val > 20:
                return jsonify({"ok": False, "error": f"Jon faqat 20% va undan kam bo'lganda tiklanadi. Hozir: {jon_val}%"})
            if u.get("points", 0) < 25:
                return jsonify({"ok": False, "error": "Ball yetarli emas"})
            u["points"] = u.get("points", 0) - 25
            u["jon"] = 100.0
            save_user(uid, u)
            return jsonify({"ok": True, "points": u["points"]})
        if item_id == "shield_1":
            if u.get("points", 0) < 100:
                return jsonify({"ok": False, "error": "Ball yetarli emas"})
            u["points"] = u.get("points", 0) - 100
            u["streak_shields"] = u.get("streak_shields", 0) + 1
            save_user(uid, u)
            return jsonify({"ok": True, "points": u["points"], "streak_shields": u["streak_shields"]})
        if item_id == "shield_3":
            if u.get("points", 0) < 250:
                return jsonify({"ok": False, "error": "Ball yetarli emas"})
            u["points"] = u.get("points", 0) - 250
            u["streak_shields"] = u.get("streak_shields", 0) + 3
            save_user(uid, u)
            return jsonify({"ok": True, "points": u["points"], "streak_shields": u["streak_shields"]})
        if item_id == "bonus_2x":
            if u.get("points", 0) < 150:
                return jsonify({"ok": False, "error": "Ball yetarli emas"})
            if u.get("bonus_2x_active") and u.get("bonus_2x_date") == today_uz5():
                return jsonify({"ok": False, "error": "Bugun 2x bonus allaqachon aktiv"})
            u["points"] = u.get("points", 0) - 150
            u["bonus_2x_active"] = True
            u["bonus_2x_date"] = today_uz5()
            save_user(uid, u)
            return jsonify({"ok": True, "points": u["points"]})
        if item_id == "bonus_3x":
            if u.get("points", 0) < 300:
                return jsonify({"ok": False, "error": "Ball yetarli emas"})
            if u.get("bonus_3x_active") and u.get("bonus_3x_date") == today_uz5():
                return jsonify({"ok": False, "error": "Bugun 3x bonus allaqachon aktiv"})
            u["points"] = u.get("points", 0) - 300
            u["bonus_3x_active"] = True
            u["bonus_3x_date"] = today_uz5()
            save_user(uid, u)
            return jsonify({"ok": True, "points": u["points"]})
        if item_id == "xp_booster":
            if u.get("points", 0) < 400:
                return jsonify({"ok": False, "error": "Ball yetarli emas"})
            u["points"] = u.get("points", 0) - 400
            u["xp_booster_days"] = u.get("xp_booster_days", 0) + 7
            save_user(uid, u)
            return jsonify({"ok": True, "points": u["points"], "xp_booster_days": u["xp_booster_days"]})
        if pay_type == "ball":
            if u.get("points", 0) < price:
                return jsonify({"ok": False, "error": "Ball yetarli emas"})
            u["points"] = u.get("points", 0) - price
        inventory[item_id] = inventory.get(item_id, 0) + 1
        u["inventory"] = inventory
        save_user(uid, u)
        return jsonify({"ok": True, "points": u["points"]})

    @api_app.route("/api/shop/<int:uid>/stars_invoice", methods=["POST"])
    @require_auth
    def api_shop_stars_invoice(uid):
        data    = request.get_json(force=True, silent=True) or {}
        item_id = data.get("item_id", "")
        stars_prices = {"gift_box": 5}
        price = stars_prices.get(item_id)
        if not price:
            return jsonify({"ok": False, "error": "Stars bilan sotib bo'lmaydigan mahsulot"})
        item_names = {"gift_box": "Sovga qutisi"}
        item_descs = {"gift_box": "Tasodifiy mukofot: ball, streak himoya yoki XP booster"}
        try:
            from telebot.types import LabeledPrice as _LP
            bot.send_invoice(
                chat_id=uid,
                title=item_names.get(item_id, item_id),
                description=item_descs.get(item_id, ""),
                invoice_payload=f"stars_{item_id}",
                provider_token="",
                currency="XTR",
                prices=[_LP(item_names.get(item_id, item_id), price)],
            )
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)})

    @api_app.route("/api/shop/<int:uid>/activate", methods=["POST"])
    @require_auth
    def api_shop_activate(uid):
        data = request.get_json() or {}
        item_id  = data.get("item_id", "")
        deactive = data.get("deactivate", False)
        u = load_user(uid)
        if item_id.startswith("pet_"):
            u["active_pet"]   = "" if deactive else item_id
        elif item_id.startswith("badge_"):
            u["active_badge"] = "" if deactive else item_id
        elif item_id.startswith("car_"):
            u["active_car"]   = "" if deactive else item_id
        save_user(uid, u)
        return jsonify({"ok": True})

    @api_app.route("/api/shop/<int:uid>/sell", methods=["POST"])
    @require_auth
    def api_shop_sell(uid):
        """Inventardagi narsani 50% narxiga sotish."""
        data    = request.get_json() or {}
        item_id = data.get("item_id", "")
        # Sotish narxlari (asl narxning 50%)
        sell_prices = {
            "badge_fire":   100, "badge_star":  125, "badge_secret": 300,
            "pet_cat":      150, "pet_dog":     175, "pet_rabbit":   150,
            "car_sport":    250,
            "shield_1":      50, "shield_3":    125,
            "bonus_2x":      75, "bonus_3x":    150,
            "xp_booster":   200,
        }
        refund = sell_prices.get(item_id)
        if refund is None:
            return jsonify({"ok": False, "error": "Bu narsa sotilmaydi"})
        u = load_user(uid)
        today = today_uz5()
        # Counter fieldlar uchun alohida tekshirish
        if item_id in ("shield_1", "shield_3"):
            raw_inv_s = u.get("inventory", [])
            inv_s = {i: 1 for i in raw_inv_s} if isinstance(raw_inv_s, list) else dict(raw_inv_s)
            shields = u.get("streak_shields", 0)
            in_inv  = inv_s.get(item_id, 0) >= 1
            if shields < 1 and not in_inv:
                return jsonify({"ok": False, "error": "Inventarda topilmadi"})
            if shields >= 1:
                sell_qty = min(shields, 3) if item_id == "shield_3" else 1
                actual_refund = refund * sell_qty // 3 if item_id == "shield_3" else refund
                u["streak_shields"] = max(0, shields - sell_qty)
            else:
                actual_refund = refund
                inv_s[item_id] = inv_s.get(item_id, 0) - 1
                if inv_s[item_id] <= 0:
                    del inv_s[item_id]
                u["inventory"] = inv_s
            u["points"] = u.get("points", 0) + actual_refund
            save_user(uid, u)
            return jsonify({"ok": True, "points": u["points"], "refund": actual_refund})
        if item_id == "bonus_2x":
            if not (u.get("bonus_2x_active") and u.get("bonus_2x_date") == today):
                return jsonify({"ok": False, "error": "Aktiv bonus topilmadi"})
            u["bonus_2x_active"] = False
            u["points"] = u.get("points", 0) + refund
            save_user(uid, u)
            return jsonify({"ok": True, "points": u["points"], "refund": refund})
        if item_id == "bonus_3x":
            if not (u.get("bonus_3x_active") and u.get("bonus_3x_date") == today):
                return jsonify({"ok": False, "error": "Aktiv bonus topilmadi"})
            u["bonus_3x_active"] = False
            u["points"] = u.get("points", 0) + refund
            save_user(uid, u)
            return jsonify({"ok": True, "points": u["points"], "refund": refund})
        if item_id == "xp_booster":
            if u.get("xp_booster_days", 0) < 1:
                return jsonify({"ok": False, "error": "Inventarda topilmadi"})
            days_left = u["xp_booster_days"]
            actual_refund = round(refund * days_left / 7)
            u["xp_booster_days"] = 0
            u["points"] = u.get("points", 0) + actual_refund
            save_user(uid, u)
            return jsonify({"ok": True, "points": u["points"], "refund": actual_refund})
        # Inventory narsalar (badge/pet/car)
        raw_inv = u.get("inventory", [])
        if isinstance(raw_inv, list):
            inventory = {i: 1 for i in raw_inv}
        else:
            inventory = dict(raw_inv)
        if inventory.get(item_id, 0) < 1:
            return jsonify({"ok": False, "error": "Inventarda topilmadi"})
        inventory[item_id] = inventory.get(item_id, 0) - 1
        if inventory[item_id] <= 0:
            del inventory[item_id]
        u["inventory"] = inventory
        if item_id.startswith("pet_")   and u.get("active_pet")   == item_id:
            u["active_pet"]   = ""
        if item_id.startswith("badge_") and u.get("active_badge") == item_id:
            u["active_badge"] = ""
        if item_id.startswith("car_")   and u.get("active_car")   == item_id:
            u["active_car"]   = ""
        u["points"] = u.get("points", 0) + refund
        save_user(uid, u)
        return jsonify({"ok": True, "points": u["points"], "refund": refund})

    @api_app.route("/api/friends/<int:uid>")
    @require_auth
    def api_friends(uid):
        u = load_user(uid)
        friends_ids = u.get("friends", [])
        today = today_uz5()
        friends = []
        for fid in friends_ids[:20]:
            fu = load_user(fid)
            if fu:
                # done_today: bugun kamida bitta odat bajarilganmi
                fhabits = fu.get("habits", [])
                f_done_today = any(h.get("last_done") == today for h in fhabits)
                friends.append({
                    "id":           fid,
                    "name":         fu.get("name", "?"),
                    "points":       fu.get("points", 0),
                    "streak":       fu.get("streak", 0),
                    "photo":        fu.get("photo_url", ""),
                    "done_today":   f_done_today,
                    "mutual_streak": min(u.get("streak", 0), fu.get("streak", 0)),
                })
        # Invite link
        invite_link = f"https://t.me/{get_bot_username()}?start=ref_{uid}"
        return jsonify({"friends": friends, "invite_link": invite_link})

    @api_app.route("/api/friends/<int:uid>/search")
    @require_auth
    def api_friends_search(uid):
        q = (request.args.get("q") or "").strip().lower().lstrip("@")
        if len(q) < 2:
            return jsonify({"ok": False, "error": "Kamida 2 harf kiriting"}), 400
        u = load_user(uid)
        my_friends = set(str(f) for f in u.get("friends", []))
        results = []
        all_users = load_all_users()
        for fid_str, udata in all_users.items():
            if str(fid_str) == str(uid):
                continue
            uname = (udata.get("username") or "").lower()
            uname_display = (udata.get("name") or "").lower()
            if q in uname or q in uname_display:
                results.append({
                    "id":        int(fid_str),
                    "name":      udata.get("name", "?"),
                    "username":  udata.get("username", ""),
                    "points":    udata.get("points", 0),
                    "streak":    udata.get("streak", 0),
                    "photo":     udata.get("photo_url", ""),
                    "is_friend": fid_str in my_friends,
                })
            if len(results) >= 10:
                break
        return jsonify({"results": results})

    @api_app.route("/api/friends/<int:uid>/add/<int:fid>", methods=["POST"])
    @require_auth
    def api_friends_add(uid, fid):
        if uid == fid:
            return jsonify({"ok": False, "error": "O'zingizni qo'sha olmaysiz"}), 400
        u = load_user(uid)
        friends = u.get("friends", [])
        if fid not in friends:
            if len(friends) >= 50:
                return jsonify({"ok": False, "error": "Do'stlar limiti 50 ta"}), 400
            friends.append(fid)
            u["friends"] = friends
            save_user(uid, u)
        # Ikkinchi tomon: fid ning ro'yxatiga ham uid ni qo'shish
        f = load_user(fid)
        if f:
            f_friends = f.get("friends", [])
            if uid not in f_friends and len(f_friends) < 50:
                f_friends.append(uid)
                f["friends"] = f_friends
                save_user(fid, f)
        return jsonify({"ok": True})

    @api_app.route("/api/friends/<int:uid>/remove/<int:fid>", methods=["DELETE"])
    @require_auth
    def api_friends_remove(uid, fid):
        u = load_user(uid)
        friends = u.get("friends", [])
        if fid in friends:
            friends.remove(fid)
            u["friends"] = friends
            save_user(uid, u)
        # Ikkinchi tomon: fid ning ro'yxatidan ham uid ni o'chirish
        f = load_user(fid)
        if f:
            f_friends = f.get("friends", [])
            if uid in f_friends:
                f_friends.remove(uid)
                f["friends"] = f_friends
                save_user(fid, f)
        return jsonify({"ok": True})

    @api_app.route("/api/challenges/<int:uid>")
    @require_auth
    def api_challenges(uid):
        challenges_col = mongo_db.get_collection("challenges") if hasattr(mongo_db, "get_collection") else mongo_db["challenges"]
        sent = list(challenges_col.find({"from_uid": str(uid)}))
        recv = list(challenges_col.find({"to_uid":   str(uid), "status": "pending"}))
        def fmt(c):
            from_uid_str = c.get("from_uid", "")
            try:
                fu = load_user(int(from_uid_str)) if from_uid_str else {}
                from_name = fu.get("name", "?") if fu else "?"
            except Exception:
                from_name = "?"
            return {
                "id":          str(c.get("_id","")),
                "habit_name":  c.get("habit_name",""),
                "from_uid":    from_uid_str,
                "from_name":   from_name,
                "to_uid":      c.get("to_uid",""),
                "status":      c.get("status","pending"),
                "days":        c.get("days", 7),
                "bet":         c.get("bet", 50),
                "expires_at":  c.get("expires_at",""),
                "created_at":  c.get("created_at",""),
            }
        return jsonify({"sent": [fmt(c) for c in sent], "received": [fmt(c) for c in recv]})

    @api_app.route("/api/challenges/<int:uid>/send", methods=["POST"])
    @require_auth
    def api_challenges_send(uid):
        data        = request.get_json(force=True, silent=True) or {}
        receiver_id = data.get("receiver_id")
        habit_name  = (data.get("habit_name") or "").strip()
        try:
            days = int(data.get("days") or 7)
        except (ValueError, TypeError):
            days = 7
        try:
            bet = int(data.get("bet") or 50)
        except (ValueError, TypeError):
            bet = 50
        # Validatsiya
        if not habit_name:
            return jsonify({"ok": False, "error": "Odat nomi kerak"})
        if len(habit_name) > 100:
            return jsonify({"ok": False, "error": "Odat nomi 100 belgidan oshmasin"})
        if not receiver_id:
            return jsonify({"ok": False, "error": "Qabul qiluvchi ID kerak"})
        try:
            receiver_id = int(receiver_id)
        except (ValueError, TypeError):
            return jsonify({"ok": False, "error": "Noto'g'ri ID"})
        if receiver_id == uid:
            return jsonify({"ok": False, "error": "O'zingizga challenge yubora olmaysiz"})
        if days < 1 or days > 30:
            return jsonify({"ok": False, "error": "Muddat 1 dan 30 kungacha bo'lishi kerak"})
        if bet < 10 or bet > 1000:
            return jsonify({"ok": False, "error": "Garov 10 dan 1000 ballgacha bo'lishi kerak"})
        if not user_exists(receiver_id):
            return jsonify({"ok": False, "error": "Foydalanuvchi topilmadi"})
        sender = load_user(uid)
        if sender.get("points", 0) < bet:
            return jsonify({"ok": False, "error": f"Yetarli ball yo'q (kerak: {bet})"})
        challenges_col = mongo_db["challenges"]
        existing = challenges_col.find_one({
            "from_uid": str(uid),
            "to_uid":   str(receiver_id),
            "status":   "pending"
        })
        if existing:
            return jsonify({"ok": False, "error": "Allaqachon kutilayotgan challenge bor"})
        import datetime as _dt
        challenges_col.insert_one({
            "from_uid":   str(uid),
            "to_uid":     str(receiver_id),
            "habit_name": habit_name,
            "days":       days,
            "bet":        bet,
            "status":     "pending",
            "created_at": today_uz5(),
            "expires_at": (datetime.now(__import__('datetime').timezone(__import__('datetime').timedelta(hours=5))) + _dt.timedelta(days=days)).strftime("%Y-%m-%d"),
        })
        try:
            sender_name = sender.get("name", "Kimdir")
            bot.send_message(
                int(receiver_id),
                f"🎯 *Challenge keldi!*\n\n"
                f"👤 *{sender_name}* sizni challenge qildi!\n"
                f"📌 Odat: *{habit_name}*\n"
                f"📅 Muddat: *{days} kun*\n"
                f"💰 Garov: *{bet} ball*\n\n"
                f"_Qabul qilish uchun botga kiring._",
                parse_mode="Markdown"
            )
        except Exception:
            pass
        return jsonify({"ok": True})

    @api_app.route("/api/challenges/<int:uid>/<cid>/accept", methods=["POST"])
    @require_auth
    def api_challenges_accept(uid, cid):
        from bson import ObjectId
        challenges_col = mongo_db["challenges"]
        try:
            c = challenges_col.find_one({"_id": ObjectId(cid), "to_uid": str(uid), "status": "pending"})
        except Exception:
            return jsonify({"ok": False, "error": "Topilmadi"})
        if not c:
            return jsonify({"ok": False, "error": "Challenge topilmadi yoki allaqachon ko'rib chiqilgan"})
        bet        = c.get("bet", 50)
        from_uid   = int(c.get("from_uid", 0))
        # Ikkalasidan ham garov yechish
        u_recv = load_user(uid)
        u_send = load_user(from_uid)
        if not u_recv or not u_send:
            return jsonify({"ok": False, "error": "Foydalanuvchi topilmadi"})
        if u_recv.get("points", 0) < bet:
            return jsonify({"ok": False, "error": f"Sizda yetarli ball yo'q (kerak: {bet})"})
        if u_send.get("points", 0) < bet:
            return jsonify({"ok": False, "error": "Challenger'da yetarli ball yo'q"})
        u_recv["points"] = u_recv.get("points", 0) - bet
        u_send["points"] = u_send.get("points", 0) - bet
        save_user(uid, u_recv)
        save_user(from_uid, u_send)
        challenges_col.update_one(
            {"_id": ObjectId(cid)},
            {"$set": {
                "status":      "active",
                "accepted_at": today_uz5(),
                "expires_at":  (datetime.now(__import__("datetime").timezone(__import__("datetime").timedelta(hours=5))) + __import__("datetime").timedelta(days=c.get("days", 7))).strftime("%Y-%m-%d"),
            }}
        )
        # Yuboruvchiga xabar
        try:
            recv_name = u_recv.get("name", "Raqib")
            bot.send_message(
                from_uid,
                f"✅ *Challenge qabul qilindi!*\n\n"
                f"👤 *{recv_name}* sizning challengingizni qabul qildi!\n"
                f"📌 Odat: *{c.get('habit_name','')}*\n"
                f"📅 Muddat: *{c.get('days',7)} kun*\n"
                f"💰 Garov: *{bet} ball* (ikkalangizdan)\n\n"
                f"_Omad! 💪_",
                parse_mode="Markdown"
            )
        except Exception:
            pass
        return jsonify({"ok": True, "points": u_recv.get("points", 0)})

    @api_app.route("/api/challenges/<int:uid>/<cid>/reject", methods=["POST"])
    @require_auth
    def api_challenges_reject(uid, cid):
        from bson import ObjectId
        challenges_col = mongo_db["challenges"]
        try:
            c = challenges_col.find_one({"_id": ObjectId(cid), "to_uid": str(uid), "status": "pending"})
        except Exception:
            return jsonify({"ok": False, "error": "Topilmadi"})
        if not c:
            return jsonify({"ok": False, "error": "Challenge topilmadi"})
        challenges_col.update_one(
            {"_id": ObjectId(cid)},
            {"$set": {"status": "rejected", "rejected_at": today_uz5()}}
        )
        # Yuboruvchiga xabar
        try:
            from_uid  = int(c.get("from_uid", 0))
            u_recv    = load_user(uid)
            recv_name = u_recv.get("name", "Raqib") if u_recv else "Raqib"
            bot.send_message(
                from_uid,
                f"❌ *Challenge rad etildi*\n\n"
                f"👤 *{recv_name}* sizning challengingizni rad etdi.\n"
                f"📌 Odat: *{c.get('habit_name','')}*",
                parse_mode="Markdown"
            )
        except Exception:
            pass
        return jsonify({"ok": True})

    @api_app.route("/api/ai/advice/<int:uid>", methods=["POST"])
    @require_auth
    def api_ai_advice(uid):
        """Foydalanuvchi statistikasi asosida AI maslahat qaytaradi. Kuniga 3 marta limit."""
        if not ANTHROPIC_API_KEY:
            return jsonify({"ok": False, "error": "AI xizmati sozlanmagan"}), 503
        u = load_user(uid)
        today = today_uz5()
        # Kunlik limit: 3 marta
        ai_log = u.get("ai_advice_log", {})
        used_today = ai_log.get(today, 0)
        if used_today >= 3:
            return jsonify({"ok": False, "error": "Bugun 3 ta AI maslahat oldingiz. Ertaga qayta urinib ko'ring."}), 429
        # Foydalanuvchi ma'lumotlari
        habits   = u.get("habits", [])
        lang     = u.get("lang", "uz")
        streak   = u.get("streak", 0)
        points   = u.get("points", 0)
        best_str = _calc_best_streak(u)
        history  = u.get("history", {})
        from datetime import datetime as _dt2, timedelta as _td2
        now_uz  = _dt2.now() + _td2(hours=5)
        # Oxirgi 7 kunlik faollik foizi
        weekly_pct = []
        for i in range(6, -1, -1):
            d = (now_uz - _td2(days=i)).strftime("%Y-%m-%d")
            day_data = history.get(d, {})
            done  = day_data.get("done", 0)
            total = day_data.get("total", 0) or len(habits) or 1
            weekly_pct.append(round(done / total * 100))
        avg_7 = round(sum(weekly_pct) / len(weekly_pct)) if weekly_pct else 0
        habit_names = [h.get("name", "") for h in habits[:10]]
        # Til bo'yicha prompt
        lang_prompts = {
            "uz": "O'zbek tilida javob ber.",
            "ru": "Отвечай на русском языке.",
            "en": "Reply in English.",
        }
        lang_instr = lang_prompts.get(lang, lang_prompts["uz"])
        _no_habits = "yo'q"
        prompt = (
            f"Sen odatlarni shakllantirish bo'yicha motivatsion murabbiysan. {lang_instr}\n\n"
            f"Foydalanuvchi ma'lumotlari:\n"
            f"- Odatlar: {', '.join(habit_names) if habit_names else _no_habits}\n"
            f"- Joriy streak: {streak} kun\n"
            f"- Eng uzun streak: {best_str} kun\n"
            f"- Ballar: {points}\n"
            f"- Oxirgi 7 kunlik o'rtacha bajarilish: {avg_7}%\n"
            f"- Haftalik natijalar (%): {weekly_pct}\n\n"
            f"Ushbu foydalanuvchiga qisqa (3-4 gap), aniq va iliq maslahat ber. "
            f"Zaif tomonlarini ayt, kuchli tomonlarini maqta, va bugun nima qilish kerakligini tavsiya et. "
            f"Emoji ishlatma, faqat matn."
        )
        try:
            import requests as _req, json as _json
            resp = _req.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "Content-Type":      "application/json",
                    "x-api-key":         ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 300,
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=25
            )
            resp.raise_for_status()
            result = resp.json()
            advice = result["content"][0]["text"].strip()
        except Exception as e:
            print(f"[ai_advice] xato: {e}")
            return jsonify({"ok": False, "error": "AI xizmatiga ulanib bo'lmadi"}), 502
        # Limitni yangilash
        ai_log[today] = used_today + 1
        u["ai_advice_log"] = ai_log
        save_user(uid, u)
        return jsonify({"ok": True, "advice": advice, "used": used_today + 1, "limit": 3})

    @api_app.route("/api/smart-remind/<int:uid>/<hid>")
    @require_auth
    def api_smart_remind(uid, hid):
        """Oxirgi 30 kunlik checkin vaqtlaridan eng ko'p uchragan vaqtni taklif qiladi."""
        u = load_user(uid)
        history = u.get("history", {})
        from datetime import datetime as _dt_sr2, timedelta as _td_sr2
        from collections import Counter
        now_uz = _dt_sr2.now() + _td_sr2(hours=5)
        times = []
        for i in range(30):
            d = (now_uz - _td_sr2(days=i)).strftime("%Y-%m-%d")
            ct = history.get(d, {}).get("checkin_times", {})
            if hid in ct:
                times.append(ct[hid])
        if len(times) < 3:
            return jsonify({"ok": False, "reason": "not_enough_data", "count": len(times)})
        # Eng yaqin 30 daqiqaga yaxlitlab, eng ko'p uchragan vaqtni topamiz
        def _round_30(t):
            try:
                h, m = map(int, t.split(":"))
                return f"{h:02d}:{'00' if m < 30 else '30'}"
            except Exception:
                return t
        rounded = [_round_30(t) for t in times]
        suggested = Counter(rounded).most_common(1)[0][0]
        return jsonify({"ok": True, "suggested_time": suggested, "based_on": len(times)})

    @api_app.route("/api/reminder/<int:uid>/<hid>", methods=["PUT"])
    @require_auth
    def api_reminder(uid, hid):
        data = request.get_json() or {}
        u = load_user(uid)
        habits = u.get("habits", [])
        for h in habits:
            if h["id"] == hid:
                h["time"] = data.get("time", h.get("time", ""))
                h["reminder"] = data.get("reminder", h.get("reminder", False))
                break
        u["habits"] = habits
        save_user(uid, u)
        # Yangi vaqt bilan qayta rejalashtirish
        updated_h = next((h for h in habits if h.get("id") == hid), None)
        if updated_h:
            try:
                schedule_habit(uid, updated_h)
            except Exception as _e:
                print(f"[warn] schedule_habit reminder: {_e}")
        return jsonify({"ok": True})

    @api_app.route("/api/profile/<int:uid>", methods=["PUT"])
    @require_auth
    def api_profile_put(uid):
        data = request.get_json() or {}
        u = load_user(uid)
        # lang
        if "lang" in data:
            if data["lang"] in ("uz", "ru", "en"):
                u["lang"] = data["lang"]
        # evening_notify
        if "evening_notify" in data:
            u["evening_notify"] = bool(data["evening_notify"])
        # dark_mode
        if "dark_mode" in data:
            u["dark_mode"] = bool(data["dark_mode"])
        # photo_url
        if "photo_url" in data:
            url = str(data["photo_url"] or "")[:500]
            u["photo_url"] = url
        # display_name
        if "display_name" in data:
            dn = str(data["display_name"] or "").strip()[:50]
            u["display_name"] = dn
        # phone
        if "phone" in data:
            phone = str(data["phone"] or "").strip()[:20]
            u["phone"] = phone
        save_user(uid, u)
        return jsonify({"ok": True})

    @api_app.route("/")
    def api_index():
        import os as _os
        html_path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "index.html")
        if _os.path.exists(html_path):
            from flask import send_file
            return send_file(html_path)
        return jsonify({"status": "ok", "bot": "Super Habits"})

    @api_app.route("/health")
    def api_health():
        return jsonify({"status": "ok", "bot": "Super Habits"})

    # ── Webhook endpoint (Telegram xabarlarini qabul qiladi) ──
    _WEBHOOK_PATH = "/webhook/" + BOT_TOKEN

    @api_app.route(_WEBHOOK_PATH, methods=["POST"])
    def telegram_webhook():
        import json as _wjson
        import threading as _thr
        from flask import request as _wreq
        if _wreq.headers.get("content-type") == "application/json":
            update = telebot.types.Update.de_json(_wjson.loads(_wreq.data))
            _thr.Thread(target=bot.process_new_updates, args=([update],), daemon=True).start()
        return "", 200

    @api_app.route("/setup_webhook")
    def setup_webhook():
        """Bir marta brauzerdan ochiladi — webhook o'rnatadi"""
        _base = os.environ.get("WEBAPP_URL", "").rstrip("/")
        if not _base:
            return jsonify({"ok": False, "error": "WEBAPP_URL sozlanmagan"}), 500
        _url = _base + _WEBHOOK_PATH
        try:
            bot.set_webhook(url=_url, allowed_updates=["message", "callback_query", "pre_checkout_query"])
            from telebot.types import BotCommand
            bot.set_my_commands([
                BotCommand("start",       "Botni ishga tushirish"),
                BotCommand("admin_panel", "Admin panel"),
            ])
            return jsonify({"ok": True, "webhook": _url})
        except Exception as _e:
            return jsonify({"ok": False, "error": str(_e)}), 502

    def run_api():
        port = int(os.environ.get("PORT", 8080))
        api_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

    print("[API] Flask server tayyor (port 8080)")

except ImportError:
    print("[API] Flask yo'q — Web App API ishlamaydi. 'pip install flask flask-cors' qiling.")
    run_api = None


# ============================================================
#  ISHGA TUSHURISH
# ============================================================
if __name__ == "__main__":
    print("=" * 45)
    print("  Odatlar Shakllantirish Boti ishga tushdi!")
    print("=" * 45)
    threading.Thread(target=scheduler_loop, daemon=True).start()
    if run_api:
        threading.Thread(target=run_api, daemon=True).start()
    print("Bot tayyor! /setup_webhook endpointini bir marta oching.")
    # Railway da webhook ishlaydi — polling shart emas
    # Lokal test uchun polling
    WEBAPP_URL_CHECK = os.environ.get("WEBAPP_URL", "")
    if not WEBAPP_URL_CHECK:
        import logging
        bot.infinity_polling(timeout=60, long_polling_timeout=30, logger_level=logging.DEBUG, allowed_updates=["message", "callback_query", "pre_checkout_query"], restart_on_change=False)
    else:
        # Webhook rejimi: Flask thread asosiy thread sifatida ishlaydi
        import time as _main_sleep
        while True:
            _main_sleep.sleep(60)