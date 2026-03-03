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
from datetime import datetime, date
from telebot.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from pymongo import MongoClient

# ============================================================
#  SOZLAMALAR
# ============================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "SHU_YERGA_TOKEN_QOYING")
ADMIN_ID   = int(os.environ.get("ADMIN_ID", 5071908808))
MONGO_URI  = os.environ.get("MONGO_URI", "mongodb+srv://habitbot:Habit2026@cluster0.i0jux9m.mongodb.net/?appName=Cluster0")

# ============================================================
#  MONGODB ULANISH
# ============================================================
mongo_client  = MongoClient(MONGO_URI)
mongo_db      = mongo_client["habit_bot"]
mongo_col     = mongo_db["users"]

# ============================================================
#  MA'LUMOTLAR BAZASI FUNKSIYALARI
# ============================================================
def load_user(user_id):
    uid = str(user_id)
    doc = mongo_col.find_one({"_id": uid})
    if doc:
        return {k: v for k, v in doc.items() if k != "_id"}
    return {"habits": [], "state": None, "joined_at": str(date.today())}

def save_user(user_id, udata):
    mongo_col.update_one(
        {"_id": str(user_id)},
        {"$set": udata},
        upsert=True
    )

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

def load_all_users():
    users = {}
    for doc in mongo_col.find({"_id": {"$not": {"$regex": "^_"}}}):
        uid = doc["_id"]
        users[uid] = {k: v for k, v in doc.items() if k != "_id"}
    return users

def user_exists(user_id):
    return mongo_col.find_one({"_id": str(user_id)}) is not None

def count_users():
    return mongo_col.count_documents({"_id": {"$not": {"$regex": "^_"}}})

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
        "btn_rating":        "🏆 Reyiting",
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
        InlineKeyboardButton("🇹🇷 Türkçe",   callback_data="set_lang_tr"),
    )
    kb.row(
        InlineKeyboardButton("🇰🇿 Қазақша",  callback_data="set_lang_kk"),
        InlineKeyboardButton("🇹🇯 Тоҷикӣ",  callback_data="set_lang_tg"),
    )
    kb.row(
        InlineKeyboardButton("🇹🇲 Türkmençe", callback_data="set_lang_tk"),
        InlineKeyboardButton("🇰🇬 Кыргызча",  callback_data="set_lang_ky"),
    )
    kb.row(
        InlineKeyboardButton("🇩🇪 Deutsch",   callback_data="set_lang_de"),
        InlineKeyboardButton("🇫🇷 Français",  callback_data="set_lang_fr"),
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
    "en": ["💪 Every day is a new opportunity!", "🔥 Don't break the streak!", "🌟 Small steps lead to big success!", "🚀 You can do it!", "🎯 One step closer to your goal!"],
    "ru": ["💪 Каждый день — новый шанс!", "🔥 Не прерывай серию!", "🌟 Маленькие шаги — большие победы!", "🚀 Ты можешь это!", "🎯 На шаг ближе к цели!"],
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

def send_message_colored(chat_id, text, reply_markup_dict, parse_mode="Markdown"):
    """Bot API 9.4 style (rangli tugmalar) uchun to'g'ridan HTTP so'rov"""
    url  = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id":      chat_id,
        "text":         text,
        "parse_mode":   parse_mode,
        "reply_markup": json.dumps(reply_markup_dict),
    }
    resp = requests.post(url, data=data)
    result = resp.json()
    if result.get("ok"):
        class FakeMsg:
            def __init__(self, msg_id):
                self.message_id = msg_id
        return FakeMsg(result["result"]["message_id"])
    # Markdown xatosi bo'lsa — parse_mode'siz qayta urinish
    if result.get("error_code") == 400:
        data2 = {
            "chat_id":      chat_id,
            "text":         text,
            "reply_markup": json.dumps(reply_markup_dict),
        }
        resp2 = requests.post(url, data=data2)
        result2 = resp2.json()
        if result2.get("ok"):
            class FakeMsg:
                def __init__(self, msg_id):
                    self.message_id = msg_id
            return FakeMsg(result2["result"]["message_id"])
    print(f"[send_message_colored] XATO: {result.get('description')}")
    return None

def cBtn(text, callback_data, style=None):
    """Rangli InlineKeyboardButton - style atributini qo'shadi"""
    btn = InlineKeyboardButton(text, callback_data=callback_data)
    if style:
        btn.style = style
    return btn

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
    data = {
        "chat_id":      chat_id,
        "message_id":   message_id,
        "text":         text,
        "parse_mode":   parse_mode,
        "reply_markup": json.dumps(reply_markup_dict),
    }
    resp = requests.post(url, data=data)
    result = resp.json()
    if not result.get("ok") and result.get("error_code") == 400:
        # Markdown xatosi bo'lsa — parse_mode'siz qayta urinish
        data2 = {
            "chat_id":      chat_id,
            "message_id":   message_id,
            "text":         text,
            "reply_markup": json.dumps(reply_markup_dict),
        }
        requests.post(url, data=data2)

def main_menu_dict(uid=None, page=1):
    """Bot API 9.4 rangli tugmalar uchun dict formatida keyboard"""
    rows = []
    rows.append([
        {"text": T(uid, "btn_add"),    "callback_data": "menu_add",    "style": "primary"},
        {"text": T(uid, "btn_delete"), "callback_data": "menu_delete", "style": "danger"},
    ])
    rows.append([
        {"text": T(uid, "btn_stats"),  "callback_data": "menu_stats",  "style": "primary"},
        {"text": T(uid, "btn_rating"), "callback_data": "menu_rating", "style": "primary"},
    ])
    if uid:
        u      = load_user(uid)
        today  = today_uz5()
        habits = u.get("habits", [])
        per_page    = 10
        total_pages = (len(habits) + per_page - 1) // per_page if habits else 1
        page        = max(1, min(page, total_pages))
        # Odatlarni vaqt bo'yicha tartiblash
        def _sort_key(h):
            t = h.get("time", "23:59")
            try:
                hh, mm = t.split(":")
                return int(hh) * 60 + int(mm)
            except:
                return 9999
        habits = sorted(habits, key=_sort_key)
        page_habits = habits[(page - 1) * per_page : page * per_page]
        # Bajarilmaganlar avval (yashil), bajarilganlar oxirga (rangsiz)
        not_done = []
        done_list = []
        for h in page_habits:
            hab_type  = h.get("type", "simple")
            rep_count = h.get("repeat_count", 1)
            if hab_type == "repeat" and rep_count > 1:
                done_today = h.get("done_today_count", 0)
                if done_today >= rep_count:
                    label = f"☑️ {h['name']} {done_today}/{rep_count}"
                    done_list.append({"text": label, "callback_data": f"toggle_{h['id']}"})
                else:
                    label = f"✅ {h['name']} {done_today}/{rep_count}"
                    not_done.append({"text": label, "callback_data": f"toggle_{h['id']}", "style": "success"})
            else:
                is_done = h.get("last_done") == today
                if is_done:
                    label = f"☑️ {h['name']}"
                    done_list.append({"text": label, "callback_data": f"toggle_{h['id']}"})
                else:
                    label = f"✅ {h['name']}"
                    not_done.append({"text": label, "callback_data": f"toggle_{h['id']}", "style": "success"})
        for btn in not_done + done_list:
            rows.append([btn])
        if total_pages > 1:
            nav = []
            if page > 1:
                nav.append({"text": f"⬅️ {page-1}", "callback_data": f"main_page_{page-1}", "style": "primary"})
            nav.append({"text": f"📄 {page}/{total_pages}", "callback_data": "noop", "style": "primary"})
            if page < total_pages:
                nav.append({"text": f"{page+1} ➡️", "callback_data": f"main_page_{page+1}", "style": "primary"})
            rows.append(nav)
    rows.append([
        {"text": "🛒 Bozor",             "callback_data": "menu_bozor",     "style": "primary"},
        {"text": T(uid, "btn_settings"), "callback_data": "menu_settings", "style": "primary"},
    ])
    return {"inline_keyboard": rows}

def main_menu(uid=None, page=1):
    """Eski kod bilan moslik uchun (ba'zi joylarda hali ishlatiladi)"""
    d = main_menu_dict(uid, page)
    kb = InlineKeyboardMarkup()
    for row in d["inline_keyboard"]:
        btns = [InlineKeyboardButton(b["text"], callback_data=b["callback_data"]) for b in row]
        if len(btns) == 1:
            kb.add(btns[0])
        else:
            kb.row(*btns)
    return kb

def done_keyboard(uid, habit_id):
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton(T(uid, "btn_done"), callback_data=f"done_{habit_id}"),
        InlineKeyboardButton("❌ Bajarmadim",    callback_data=f"skip_{habit_id}")
    )
    return kb

def build_main_text(uid):
    u      = load_user(uid)
    habits = u.get("habits", [])
    if not habits:
        return T(uid, "no_habits")
    total_points = u.get("points", 0)
    today      = today_uz5()
    done_count = sum(1 for h in habits if h.get("last_done") == today)
    percent    = round(done_count / len(habits) * 100) if habits else 0
    header     = T(uid, 'welcome_back').replace('📊 *', '').replace('*', '').strip()
    pct_text   = T(uid, 'done_percent', p=percent)
    jon   = u.get("jon", 100)
    jon   = max(0, min(100, jon))
    if jon >= 80:   jon_emoji = "❤️"
    elif jon >= 50: jon_emoji = "🧡"
    elif jon >= 20: jon_emoji = "💛"
    else:           jon_emoji = "🖤"
    text  = f"📊 *{header} | {pct_text}*\n"
    text += f"*{jon_emoji} Jon:* {jon}%\n"
    text += "━" * 16 + "\n"
    text += T(uid, "stats_ball", ball=total_points) + "\n"
    text += T(uid, "stats_rank", rank=get_rank(uid, total_points)) + "\n"
    text += "━" * 16 + "\n"
    today = today_uz5()
    # Odatlarni vaqt bo'yicha tartiblash
    def habit_sort_key(h):
        t = h.get("time", "23:59")
        try:
            hh, mm = t.split(":")
            return int(hh) * 60 + int(mm)
        except:
            return 9999
    sorted_habits = sorted(habits, key=habit_sort_key)
    text += "\n"
    for h in sorted_habits:
        streak     = h.get("streak", 0)
        total_done = h.get("total_done", 0)
        if streak >= 30:   medal = "🥇"
        elif streak >= 14: medal = "🥈"
        elif streak >= 7:  medal = "🥉"
        else:              medal = "🌱"
        text += f"{medal} *{h['name']}* — {total_done} marta\n"
    text += "\n" + "━" * 16
    return text

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
    kb.add(cBtn("🏠 Asosiy menyu", "admin_close", "primary"))
    return kb

def admin_broadcast_menu():
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("👤 Shaxsiy chatlar", callback_data="admin_bc_private"),
        InlineKeyboardButton("👥 Guruhlar",         callback_data="admin_bc_groups")
    )
    kb.add(InlineKeyboardButton("📣 Umumiy (hammasi)", callback_data="admin_bc_all"))
    kb.add(InlineKeyboardButton("❌ Bekor qilish",     callback_data="admin_cancel"))
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
    kb.add(InlineKeyboardButton("❌ Bekor qilish", callback_data="admin_cancel"))
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

@bot.message_handler(commands=["start"])
def cmd_start(msg):
    uid  = msg.from_user.id
    name = msg.from_user.first_name

    # Barcha oldingi xabarlarni o'chirish
    u_prev = load_user(uid)
    old_start_ids = list(u_prev.get("start_msg_ids", []))
    old_main = u_prev.get("main_msg_id")
    if old_main and old_main not in old_start_ids:
        old_start_ids.append(old_main)
    u_prev["start_msg_ids"] = []
    save_user(uid, u_prev)
    def delete_old_starts(chat_id, ids, cmd_id):
        for mid in ids + [cmd_id]:
            try: bot.delete_message(chat_id, mid)
            except: pass
    threading.Thread(target=delete_old_starts, args=(uid, old_start_ids, msg.message_id), daemon=True).start()

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
        kb_lang.add(cBtn(T(uid, "btn_home"), "menu_main", "primary"))
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
    if reg_msg_id:
        try:
            bot.delete_message(uid, reg_msg_id)
        except Exception:
            pass
    try:
        bot.delete_message(uid, msg.message_id)
    except Exception:
        pass
    if not check_subscription(uid):
        bot.send_message(uid, T(uid, "sub_required"), reply_markup=ReplyKeyboardRemove())
        send_sub_required(uid)
        return
    sent_reg = bot.send_message(uid, "✅", reply_markup=ReplyKeyboardRemove())
    def delete_reg_confirm(chat_id, message_id):
        time.sleep(3)
        try:
            bot.delete_message(chat_id, message_id)
        except Exception:
            pass
    threading.Thread(target=delete_reg_confirm, args=(uid, sent_reg.message_id), daemon=True).start()

    # Referal bonus berish
    referrer_id = u.pop("pending_referrer", None)
    if referrer_id and not u.get("ref_used"):
        try:
            u["points"] = u.get("points", 0) + 25
            u["ref_used"] = True
            bot.send_message(uid,
                "🎁 *Do'st taklifi bonusi!*\n\n"
                "*⭐ +25 ball* hisobingizga qo'shildi!",
                parse_mode="Markdown")
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
                parse_mode="Markdown")
        except Exception:
            pass

    # Til tanlash
    sent_lang = bot.send_message(uid, "🌐 Tilni tanlang / Choose language / Выберите язык / Dil seçin:", reply_markup=lang_keyboard())
    u["lang_msg_id"] = sent_lang.message_id
    save_user(uid, u)

# ============================================================
#  REYITING
# ============================================================
def show_rating(uid):
    users   = load_all_users()
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
    medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    text   = T(uid, "rating_title") + "\n" + "▬" * 16 + "\n\n"
    if top10:
        for i, (name, points, username, target_uid) in enumerate(top10):
            uname = username.lstrip("@") if username and username != "—" else ""
            if uname:
                link = f"[{name}](https://t.me/{uname})"
            else:
                link = f"[{name}](tg://user?id={target_uid})"
            # Jon va VIP ko'rsatish
            udata   = users.get(str(target_uid), {})
            jon_val = udata.get("jon", 100)
            jon_val = max(0, min(100, jon_val))
            if jon_val >= 80:   je = "❤️"
            elif jon_val >= 50: je = "🧡"
            elif jon_val >= 20: je = "💛"
            else:               je = "🖤"
            vip_badge = " 💎" if udata.get("is_vip") else ""
            text += f"{medals[i]} {link}{vip_badge} — {points} ball,  {je} {jon_val}%\n"
    else:
        text += T(uid, "rating_empty")
    kb = InlineKeyboardMarkup()
    kb.add(cBtn(T(uid, "btn_home"), "menu_main", "primary"))
    u    = load_user(uid)
    sent = bot.send_message(uid, text, parse_mode="Markdown", reply_markup=kb, disable_web_page_preview=True)
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
    text += f"*⭐ Yig'ilgan ball:* +{balls_earned}\n\n"
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
    users = load_all_users()
    print(f"[weekly_report] {len(users)} foydalanuvchiga hisobot yuborilmoqda...")
    for uid_str, udata in users.items():
        try:
            habits = udata.get("habits", [])
            if not habits:
                continue
            uid_int  = int(uid_str)
            jon_end  = udata.get("jon", 100)
            jon_start = max(0, min(100, round(jon_end - (jon_end - 50) * 0.1)))
            total_possible = 0
            total_done_w   = 0
            habit_scores   = []
            best_streak    = 0
            for h in habits:
                rep  = h.get("repeat_count", 1) if h.get("type") == "repeat" else 1
                done = min(h.get("total_done", 0), rep * 7)
                poss = rep * 7
                total_possible += poss
                total_done_w   += done
                score = round(done / poss * 100) if poss else 0
                habit_scores.append((h["name"], score))
                if h.get("streak", 0) > best_streak:
                    best_streak = h.get("streak", 0)
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
            }
            try:
                mongo_col.update_one(
                    {"_id": uid_int},
                    {"$push": {"weekly_reports": report}},
                    upsert=False
                )
            except Exception as e:
                print(f"[weekly_report] MongoDB saqlash xato {uid_int}: {e}")
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
    sent = bot.send_message(uid, "🗑 *Qaysi odatni o'chirmoqchisiz?*", parse_mode="Markdown", reply_markup=kb)
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
        try:
            bot.delete_message(uid, call.message.message_id)
        except Exception:
            pass
        if lang_msg_id and lang_msg_id != call.message.message_id:
            try:
                bot.delete_message(uid, lang_msg_id)
            except Exception:
                pass
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
                kb_ph.add(KeyboardButton("📱 Telefon raqamni yuborish", request_contact=True))
                sent_ph = bot.send_message(
                    uid,
                    f"👋 Salom, *{name}*!\n\n"
                    "Davom etish uchun ro'yxatdan o'ting:\n\n"
                    "📌 Telefon raqamingizni yuboring:\n"
                    "• Tugmani bosib yuboring, _yoki_\n"
                    "• Qo'lda kiriting: *+998901234567*",
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
        return

    if cdata not in ("check_sub", "admin_cancel", "admin_close") and not cdata.startswith("admin_"):
        if not check_subscription(uid):
            bot.answer_callback_query(call.id)
            send_sub_required(uid)
            return

    if cdata == "check_sub":
        if check_subscription(uid):
            bot.answer_callback_query(call.id, "✅")
            bot.delete_message(uid, call.message.message_id)
            u.pop("sub_msg_id", None)
            save_user(uid, u)
            # Til tanlamagan bo'lsa
            if not u.get("lang"):
                sent_lang = bot.send_message(uid, "🌐 Tilni tanlang / Choose language / Выберите язык / Dil seçin:", reply_markup=lang_keyboard())
                u["lang_msg_id"] = sent_lang.message_id
                save_user(uid, u)
            else:
                send_main_menu(uid)
        else:
            bot.answer_callback_query(call.id, "❌ Hali a'zo bo'lmadingiz!")
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

    if cdata == "bc_confirm":
        if uid != ADMIN_ID:
            return
        bot.answer_callback_query(call.id, "✅ Tasdiqlandi")
        def del_bc_confirm(chat_id, mid):
            time.sleep(5)
            try: bot.delete_message(chat_id, mid)
            except: pass
        threading.Thread(target=del_bc_confirm, args=(uid, call.message.message_id), daemon=True).start()
        return

    if cdata == "bc_detail":
        if uid != ADMIN_ID:
            return
        bot.answer_callback_query(call.id)
        failed_list = u.get("bc_failed_list", [])
        if not failed_list:
            bot.answer_callback_query(call.id, "Bloklagan foydalanuvchi yo'q", show_alert=True)
            return
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
        bot.delete_message(uid, call.message.message_id)
        kb_confirm = InlineKeyboardMarkup()
        kb_confirm.row(
            InlineKeyboardButton("✅ Ha, yuborish", callback_data="admin_notify_confirm"),
            InlineKeyboardButton("❌ Yo'q",         callback_data="admin_cancel")
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
        bot.delete_message(uid, call.message.message_id)
        users      = load_all_users()
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
        bot.delete_message(uid, call.message.message_id)
        u["state"] = "admin_waiting_points_id"
        kb2 = InlineKeyboardMarkup()
        kb2.add(InlineKeyboardButton("❌ Bekor qilish", callback_data="admin_cancel"))
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
        bot.delete_message(uid, call.message.message_id)
        bot.send_message(uid, "📢 *Habar yuborish*\n\nQayerga yubormoqchisiz?", parse_mode="Markdown", reply_markup=admin_broadcast_menu())
        return

    if cdata in ("admin_bc_private", "admin_bc_groups", "admin_bc_all"):
        if uid != ADMIN_ID:
            return
        u["state"] = cdata
        save_user(uid, u)
        bot.answer_callback_query(call.id)
        bot.delete_message(uid, call.message.message_id)
        labels = {"admin_bc_private": "shaxsiy chatlarga", "admin_bc_groups": "guruhlarga", "admin_bc_all": "hammaga"}
        bot.send_message(uid, f"✏️ Yubormoqchi bo'lgan xabaringizni yozing ({labels[cdata]}):", parse_mode="Markdown")
        return

    if cdata == "admin_users" or cdata.startswith("admin_users_page_"):
        if uid != ADMIN_ID:
            return
        bot.answer_callback_query(call.id)
        bot.delete_message(uid, call.message.message_id)
        users = load_all_users()
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
            InlineKeyboardButton("🔙 Admin panel", callback_data="admin_cancel"),
            InlineKeyboardButton("🏠 Asosiy menyu", callback_data="admin_close")
        )
        bot.send_message(uid, text, reply_markup=kb)
        return

    if cdata == "admin_channel":
        if uid != ADMIN_ID:
            return
        bot.answer_callback_query(call.id)
        bot.delete_message(uid, call.message.message_id)
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
        kb2.add(InlineKeyboardButton("❌ Bekor qilish", callback_data="admin_cancel"))
        sent_ch = bot.send_message(uid, msg_text, parse_mode="Markdown", reply_markup=kb2)
        u["channel_msg_id"] = sent_ch.message_id
        save_user(uid, u)
        return

    if cdata.startswith("admin_ch_edit_"):
        if uid != ADMIN_ID:
            return
        slot = int(cdata[14:])
        bot.answer_callback_query(call.id)
        bot.delete_message(uid, call.message.message_id)
        u["state"] = f"admin_waiting_channel_{slot}"
        kb2 = InlineKeyboardMarkup()
        kb2.add(InlineKeyboardButton("❌ Bekor qilish", callback_data="admin_cancel"))
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
        bot.delete_message(uid, call.message.message_id)
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
        bot.delete_message(uid, call.message.message_id)
        bot.send_message(uid, "📈 *Statistika — davr tanlang:*", parse_mode="Markdown", reply_markup=admin_stats_period_menu())
        return

    if cdata.startswith("admin_stats_"):
        if uid != ADMIN_ID:
            return
        bot.answer_callback_query(call.id)
        bot.delete_message(uid, call.message.message_id)
        period = cdata[12:]
        users  = load_all_users()
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
        kb2.add(InlineKeyboardButton("❌ Bekor qilish", callback_data="admin_cancel"))
        bot.send_message(uid, text, parse_mode="Markdown", reply_markup=kb2)
        return

    if cdata == "menu_settings":
        bot.answer_callback_query(call.id)
        bot.delete_message(uid, call.message.message_id)
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
        bot.delete_message(uid, call.message.message_id)
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
        bot.delete_message(uid, call.message.message_id)
        u["state"] = "waiting_dev_message"
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.add(InlineKeyboardButton(T(uid, "btn_cancel"), callback_data="menu_settings"))
        sent = bot.send_message(uid, "💬 *Dasturchiga habar yozing:*\n\nHabaringizni quyida kiriting:", parse_mode="Markdown", reply_markup=cancel_kb)
        u["dev_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    if cdata == "settings_info":
        bot.answer_callback_query(call.id)
        bot.delete_message(uid, call.message.message_id)
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
        bot.delete_message(uid, call.message.message_id)
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
        sent = bot.send_message(uid, "⚙️ *Odat sozlamalari*", parse_mode="Markdown", reply_markup=kb_habits)
        u["main_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    # --- Umumiy vaqtni olib tashlash ---
    if cdata == "edit_htime_all_remove":
        bot.answer_callback_query(call.id)
        bot.delete_message(uid, call.message.message_id)
        for h in u.get("habits", []):
            h["time"] = "vaqtsiz"
            schedule.clear(f"{uid}_{h['id']}")
        save_user(uid, u)
        sent_ok = bot.send_message(uid, "🔕 Barcha odatlar vaqtsiz holatga o'tkazildi!")
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
        sent2 = bot.send_message(uid, "⏰ *Qaysi odatning vaqtini tahrirlash?*", parse_mode="Markdown", reply_markup=kb_habits)
        u2 = load_user(uid)
        u2["main_msg_id"] = sent2.message_id
        save_user(uid, u2)
        return

    # --- Umumiy vaqt belgilash (barcha odatlarga bir vaqt) ---
    if cdata == "edit_htime_all_set":
        bot.answer_callback_query(call.id)
        bot.delete_message(uid, call.message.message_id)
        u["state"]             = "editing_all_habits_time"
        u["editing_habit_id"]  = "ALL"
        save_user(uid, u)
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.add(InlineKeyboardButton(T(uid, "btn_cancel"), callback_data="settings_habits_time"))
        sent = bot.send_message(uid, "⏰ Barcha odatlar uchun umumiy vaqtni kiriting:\n\n_Masalan: 07:00_", parse_mode="Markdown", reply_markup=cancel_kb)
        u["temp_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    # --- Bitta odat vaqti tahrirlash ---
    if cdata.startswith("edit_htime_") and not cdata.startswith("edit_htime_notime_") and not cdata.startswith("edit_htime_start_"):
        habit_id = cdata[11:]
        bot.answer_callback_query(call.id)
        bot.delete_message(uid, call.message.message_id)
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
        bot.delete_message(uid, call.message.message_id)
        for h in u.get("habits", []):
            if h["id"] == habit_id:
                h["time"] = "vaqtsiz"
                schedule.clear(f"{uid}_{habit_id}")
                break
        save_user(uid, u)
        sent_ok = bot.send_message(uid, "🔕 Odat vaqtsiz holatga o'tkazildi!", parse_mode="Markdown")
        def del_ok_notime(chat_id, mid):
            time.sleep(2)
            try: bot.delete_message(chat_id, mid)
            except: pass
        threading.Thread(target=del_ok_notime, args=(uid, sent_ok.message_id), daemon=True).start()
        # Odatlar ro'yxatiga qaytish
        kb_back = InlineKeyboardMarkup()
        kb_back.add(InlineKeyboardButton("⬅️ Odatlar ro'yxati", callback_data="settings_habits_time"))
        kb_back.add(cBtn(T(uid, "btn_home"),     "menu_main", "primary"))
        sent2 = bot.send_message(uid, "⏰ *Odatlar vaqtini tahrirlash*", parse_mode="Markdown", reply_markup=kb_back)
        u["main_msg_id"] = sent2.message_id
        save_user(uid, u)
        return

    # --- Vaqtni tahrirlash boshlash ---
    if cdata.startswith("edit_htime_start_"):
        habit_id = cdata[17:]
        bot.answer_callback_query(call.id)
        bot.delete_message(uid, call.message.message_id)
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
        cancel_kb.add(InlineKeyboardButton(T(uid, "btn_cancel"), callback_data="settings_habits_time"))
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
        bot.delete_message(uid, call.message.message_id)
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
        sent = bot.send_message(uid, "✏️ *Qaysi odatning nomini o'zgartirmoqchisiz?*", parse_mode="Markdown", reply_markup=kb_hn)
        u["main_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    if cdata == "change_name":
        bot.answer_callback_query(call.id)
        bot.delete_message(uid, call.message.message_id)
        u["state"] = "updating_name"
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.add(cBtn("⬅️ Orqaga", "settings_info", "primary"))
        sent = bot.send_message(uid, "✏️ Yangi ismingizni yozing:", reply_markup=cancel_kb)
        u["info_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    if cdata.startswith("rename_habit_"):
        habit_id = cdata[len("rename_habit_"):]
        bot.answer_callback_query(call.id)
        bot.delete_message(uid, call.message.message_id)
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
        bot.delete_message(uid, call.message.message_id)
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
        if len(u.get("habits", [])) >= 10:
            bot.answer_callback_query(call.id)
            sent_limit = bot.send_message(
                uid,
                "⚠️ *Siz maksimal 10 ta odat yarata olasiz!*\n\nLimitga yetdingiz.",
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
        bot.delete_message(uid, call.message.message_id)
        # Odat turini tanlash
        kb_type = InlineKeyboardMarkup()
        kb_type.row(
            InlineKeyboardButton("📌 Oddiy",          callback_data="habit_type_simple"),
            InlineKeyboardButton("🔁 Takrorlanuvchi", callback_data="habit_type_repeat")
        )
        kb_type.add(InlineKeyboardButton(T(uid, "btn_cancel"), callback_data="cancel"))
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
        bot.delete_message(uid, call.message.message_id)
        u["state"] = "waiting_habit_name"
        u["temp_habit"] = {"type": "simple"}
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.add(InlineKeyboardButton(T(uid, "btn_cancel"), callback_data="cancel"))
        sent = bot.send_message(uid, T(uid, "ask_habit_name"), parse_mode="Markdown", reply_markup=cancel_kb)
        u["temp_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    if cdata == "habit_type_repeat":
        bot.answer_callback_query(call.id)
        bot.delete_message(uid, call.message.message_id)
        u["state"] = "waiting_habit_name"
        u["temp_habit"] = {"type": "repeat"}
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.add(InlineKeyboardButton(T(uid, "btn_cancel"), callback_data="cancel"))
        sent = bot.send_message(uid, T(uid, "ask_habit_name"), parse_mode="Markdown", reply_markup=cancel_kb)
        u["temp_msg_id"] = sent.message_id
        save_user(uid, u)
        return



    if cdata == "cancel":
        u["state"] = None
        u.pop("temp_habit", None)
        old_msg_id = u.pop("temp_msg_id", None)
        save_user(uid, u)
        bot.answer_callback_query(call.id, T(uid, "btn_cancel"))
        bot.delete_message(uid, call.message.message_id)
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
        bot.delete_message(uid, call.message.message_id)
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
        bot.delete_message(uid, call.message.message_id)
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
        bot.delete_message(uid, call.message.message_id)
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

    if cdata == "menu_list":
        bot.answer_callback_query(call.id)
        bot.delete_message(uid, call.message.message_id)
        show_habits(uid)
        return

    if cdata == "menu_stats":
        bot.answer_callback_query(call.id)
        bot.delete_message(uid, call.message.message_id)
        show_stats(uid)
        return

    if cdata.startswith("stats_page_"):
        page = int(cdata[11:])
        bot.answer_callback_query(call.id)
        bot.delete_message(uid, call.message.message_id)
        show_stats(uid, page=page)
        return

    if cdata == "menu_delete":
        bot.answer_callback_query(call.id)
        bot.delete_message(uid, call.message.message_id)
        delete_habit_menu(uid)
        return

    if cdata == "menu_rating":
        bot.answer_callback_query(call.id)
        bot.delete_message(uid, call.message.message_id)
        show_rating(uid)
        return

    if cdata == "menu_main":
        bot.answer_callback_query(call.id)
        bot.delete_message(uid, call.message.message_id)
        send_main_menu(uid)
        return

    # ============================================================
    #  BOZOR
    # ============================================================
    if cdata == "menu_bozor":
        bot.answer_callback_query(call.id)
        bot.delete_message(uid, call.message.message_id)
        balls = u.get("points", 0)
        ref_count  = len(u.get("referrals", []))
        bozor_text = (
            f"🛒 *Bozor —* bu sizning ballaringiz bilan qilinadigan barcha ammalar joyi.\n\n"
            f"*⭐ Sizning balingiz:* {balls} ball\n"
            f"*👥 Taklif qilganlar:* {ref_count} ta do'st\n\n"
            "*👥 Do'st taklif qilish —* +50 ball (siz), +25 ball (do'st)\n"
            "*💸 Ballarni ayirboshlash —* yaqin insoniga ball yuborish\n"
            "*🔴 Ballarimni 0 ga tushirish —* barcha ballarni nollash\n"
            "*➖ Ballarimdan olib tashlash —* ma'lum miqdorni ayirish"
        )
        bozor_kb = {"inline_keyboard": [
            [{"text": "👥 Do'st taklif qilish",       "callback_data": "bozor_referral",      "style": "primary"}],
            [{"text": "💸 Ballarni ayirboshlash",     "callback_data": "bozor_transfer"}],
            [{"text": "🔴 Ballarimni 0 ga tushirish", "callback_data": "bozor_reset_confirm", "style": "danger"}],
            [{"text": "➖ Ballarimdan olib tashlash",  "callback_data": "bozor_subtract"}],
            [{"text": T(uid, "btn_home"),              "callback_data": "menu_main",           "style": "primary"}],
        ]}
        sent = send_message_colored(uid, bozor_text, bozor_kb)
        if sent is None:
            kb_b = InlineKeyboardMarkup()
            kb_b.add(InlineKeyboardButton("👥 Do'st taklif qilish",      callback_data="bozor_referral"))
            kb_b.add(InlineKeyboardButton("💸 Ballarni ayirboshlash",    callback_data="bozor_transfer"))
            kb_b.add(InlineKeyboardButton("🔴 Ballarimni 0 ga tushirish", callback_data="bozor_reset_confirm"))
            kb_b.add(InlineKeyboardButton("➖ Ballarimdan olib tashlash",  callback_data="bozor_subtract"))
            kb_b.add(cBtn(T(uid, "btn_home"),             "menu_main", "primary"))
            sent = bot.send_message(uid, bozor_text, parse_mode="Markdown", reply_markup=kb_b)
        u["main_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    if cdata == "bozor_referral":
        bot.answer_callback_query(call.id)
        bot.delete_message(uid, call.message.message_id)
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
        bot.delete_message(uid, call.message.message_id)
        u["state"] = "bozor_waiting_transfer_id"
        save_user(uid, u)
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
        bot.delete_message(uid, call.message.message_id)
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
        bot.delete_message(uid, call.message.message_id)
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
        bot.delete_message(uid, call.message.message_id)
        u["points"] = 0
        save_user(uid, u)
        sent_ok = bot.send_message(uid, "✅ Ballaringiz *0 ga* tushirildi.", parse_mode="Markdown")
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
        bot.delete_message(uid, call.message.message_id)
        u["state"] = "bozor_waiting_subtract"
        save_user(uid, u)
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
        bot.delete_message(uid, call.message.message_id)
        u["state"] = f"admin_waiting_reply_{target_user_id}"
        kb_cancel = InlineKeyboardMarkup()
        kb_cancel.add(InlineKeyboardButton("❌ Bekor qilish", callback_data="admin_cancel"))
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
        if not habit_name:
            return
        kb_confirm = InlineKeyboardMarkup()
        kb_confirm.row(
            cBtn(T(uid, "btn_yes"), f"confirm_delete_{habit_id}", "success"),
            cBtn(T(uid, "btn_no"),  "cancel_delete", "danger")
        )
        bot.answer_callback_query(call.id)
        bot.edit_message_text(
            T(uid, "confirm_delete", name=habit_name),
            uid, call.message.message_id,
            parse_mode="Markdown",
            reply_markup=kb_confirm
        )
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
                    fully_done       = done_today_count >= rep_count

                    if fully_done:
                        # Bekor qilish: to'liq bajarilganidan qaytarish (ball va total_done qaytariladi)
                        h["done_today_count"] = 0
                        h["last_done"]  = None
                        h["streak"]     = max(0, h.get("streak", 0) - 1)
                        h["total_done"] = max(0, h.get("total_done", 0) - 1)
                        u["points"]     = max(0, u.get("points", 0) - 5)
                        save_user(uid, u)
                        schedule_habit(uid, h)
                        bot.answer_callback_query(call.id, f"↩️ 0/{rep_count}")
                    else:
                        # Bir bosish = progress +1, lekin ball YO'Q
                        done_today_count += 1
                        h["done_today_count"] = done_today_count
                        if done_today_count >= rep_count:
                            # To'liq bajarildi — faqat shu yerda ball beriladi
                            h["last_done"]  = today
                            h["streak"]     = h.get("streak", 0) + 1 if h.get("last_done") == yesterday else 1
                            h["total_done"] = h.get("total_done", 0) + 1
                            u["points"]     = u.get("points", 0) + 5
                            unschedule_habit_today(uid, habit_id)
                            save_user(uid, u)
                            bot.answer_callback_query(call.id)
                            streak_r = h.get("streak", 1)
                            if streak_r >= 30:   s_extra_r = f"\n🔥 Streak: {streak_r} kun 🏆"
                            elif streak_r >= 14: s_extra_r = f"\n🔥 Streak: {streak_r} kun 🌟"
                            elif streak_r >= 7:  s_extra_r = f"\n🔥 Streak: {streak_r} kun 🔥"
                            else:                s_extra_r = f"\n🔥 Streak: {streak_r} kun"
                            sent_msg = bot.send_message(
                                uid,
                                T(uid, "done_ok", name=h["name"]) + f" *+5 ⭐ ball*" + s_extra_r,
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
                        u["points"]     = max(0, u.get("points", 0) - 5)
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
                        h["streak"]     = h.get("streak", 0) + 1 if h.get("last_done") == yesterday else 1
                        h["last_done"]  = today
                        h["total_done"] = h.get("total_done", 0) + 1
                        u["points"]     = u.get("points", 0) + 5
                        save_user(uid, u)
                        unschedule_habit_today(uid, habit_id)
                        bot.answer_callback_query(call.id)
                        streak_s = h.get("streak", 1)
                        if streak_s >= 30:   s_extra_s = f"\n🔥 Streak: {streak_s} kun 🏆"
                        elif streak_s >= 14: s_extra_s = f"\n🔥 Streak: {streak_s} kun 🌟"
                        elif streak_s >= 7:  s_extra_s = f"\n🔥 Streak: {streak_s} kun 🔥"
                        else:                s_extra_s = f"\n🔥 Streak: {streak_s} kun"
                        sent_msg = bot.send_message(uid, T(uid, "done_ok", name=h["name"]) + " *+5 ⭐ ball*" + s_extra_s, parse_mode="Markdown")
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
                if h.get("last_done") == today:
                    bot.answer_callback_query(call.id, T(uid, "done_today"))
                    return
                h["streak"] = h.get("streak", 0) + 1 if h.get("last_done") == yesterday else 1
                h["last_done"]  = today
                h["total_done"] = h.get("total_done", 0) + 1
                u["points"]     = u.get("points", 0) + 5
                save_user(uid, u)
                # Bugunlik eslatmani to'xtatish (ertaga daily_reset qayta yuklaydi)
                unschedule_habit_today(uid, habit_id)
                streak = h["streak"]
                if streak >= 30:   msg_extra = f"🔥 Streak: {streak} kun 🏆"
                elif streak >= 14: msg_extra = f"🔥 Streak: {streak} kun 🌟"
                elif streak >= 7:  msg_extra = f"🔥 Streak: {streak} kun 🔥"
                else:              msg_extra = f"🔥 Streak: {streak} kun"
                bot.edit_message_text(
                    f"{T(uid, 'done_ok', name=h['name'])} *+5 ⭐ ball*\n\n{msg_extra}",
                    uid, call.message.message_id, parse_mode="Markdown"
                )
                bot.answer_callback_query(call.id, "✅")
                # Eslatma xabarini 3 soniyada o'chirish
                def del_remind(chat_id, message_id):
                    time.sleep(3)
                    try: bot.delete_message(chat_id, message_id)
                    except: pass
                threading.Thread(target=del_remind, args=(uid, call.message.message_id), daemon=True).start()
                # Asosiy menyuni yangilash (☑️ ga o'zgartirish)
                main_msg_id = u.get("main_msg_id")
                if main_msg_id:
                    try:
                        edit_message_colored(uid, main_msg_id, build_main_text(uid), main_menu_dict(uid))
                    except Exception:
                        pass
                return

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
    for h in habits:
        if h["id"] == habit["id"]:
            exists = True
            # Bugun allaqachon bajarilgan bo'lsa — eslatma yubormaymiz
            if h.get("last_done") == today:
                return
            # Kecha bajarilganmi — aks holda missed++
            if h.get("last_done") not in (today, yesterday, None):
                h["total_missed"] = h.get("total_missed", 0) + 1
            break
    if not exists:
        return
    save_user(user_id, u)
    lang = get_lang(user_id)
    motiv = random.choice(MOTIVATSIYA.get(lang, MOTIVATSIYA["uz"]))
    try:
        bot.send_message(
            user_id,
            T(user_id, "remind_title", name=habit["name"], motiv=motiv),
            parse_mode="Markdown",
            reply_markup=done_keyboard(user_id, habit["id"])
        )
    except Exception as e:
        print(f"[reminder] xato: {e}")

def schedule_habit(user_id, habit):
    # Avval eski jadval bo'lsa o'chiramiz (dublikat bo'lmasligi uchun)
    schedule.clear(f"{user_id}_{habit['id']}")
    # Foydalanuvchi UTC+5 da vaqt kiritadi, Railway UTC da ishlaydi
    try:
        h, m   = map(int, habit["time"].split(":"))
        total  = h * 60 + m - 5 * 60
        total  = total % (24 * 60)
        utc_h  = total // 60
        utc_m  = total % 60
        utc_time = f"{utc_h:02d}:{utc_m:02d}"
    except Exception:
        utc_time = habit["time"]

    schedule.every().day.at(utc_time).do(
        send_reminder, user_id=user_id, habit=habit
    ).tag(f"{user_id}_{habit['id']}")
    print(f"[schedule] {habit['name']} — {habit['time']} (UTC: {utc_time})")

def unschedule_habit_today(user_id, habit_id):
    """Bugun uchun eslatmani to'xtatish — ertaga avtomatik ishlaydi"""
    schedule.clear(f"{user_id}_{habit_id}")
    print(f"[schedule] {user_id}_{habit_id} — bugunlik to'xtatildi")

def daily_reset():
    """Har kuni 00:00 (UTC+5) da barcha jadvallarni qayta yuklash"""
    print("[daily_reset] Barcha jadvallar qayta yuklanmoqda...")
    from datetime import timezone, timedelta
    tz_uz     = timezone(timedelta(hours=5))
    yesterday = (datetime.now(tz_uz) - timedelta(days=1)).strftime("%Y-%m-%d")
    users = load_all_users()
    for uid, udata in users.items():
        changed = False
        for habit in udata.get("habits", []):
            hab_type = habit.get("type", "simple")
            if hab_type == "repeat":
                # Repeat: done_today_count tozalash + bajarilmasa missed++
                if habit.get("done_today_count", 0) < habit.get("repeat_count", 1):
                    if habit.get("last_done") != yesterday:
                        habit["total_missed"] = habit.get("total_missed", 0) + 1
                habit["done_today_count"] = 0
                habit["last_done"] = None
                changed = True
            else:
                # Oddiy: kecha bajarilmagan bo'lsa missed++ va streak nollanadi
                missed_today = False
                if habit.get("last_done") != yesterday and habit.get("last_done") is not None:
                    habit["total_missed"] = habit.get("total_missed", 0) + 1
                    missed_today = True
                    changed = True
                elif habit.get("last_done") is None and habit.get("total_done", 0) > 0:
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
            today_str = (datetime.now(tz_uz)).strftime("%Y-%m-%d")
            d = 0
            for h in habits_list:
                htype = h.get("type", "simple")
                if htype == "repeat":
                    if h.get("done_today_count", 0) >= h.get("repeat_count", 1):
                        d += 1
                else:
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
                    bot.send_message(
                        user_id_int,
                        "*💀 Joningiz 0% ga yetdi!*\n\n"
                        "Kecha barcha odatlaringiz bajarilmadi.\n"
                        "Bugun barcha odatlaringizni bajarsangiz jon tiklanadi!",
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass

        if changed:
            try:
                update_data = {"habits": udata["habits"], "jon": udata.get("jon", 100)}
                mongo_col.update_one({"_id": uid}, {"$set": update_data})
            except Exception:
                pass
    # daily_reset ni saqlab, faqat habit jadvallarini tozalash
    all_jobs = schedule.get_jobs()
    for job in all_jobs:
        if "daily_reset" not in job.tags:
            schedule.cancel_job(job)
    load_all_schedules()

def load_all_schedules():
    users = load_all_users()
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
        users = load_all_users()
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
    # Har dushanba 09:00 (UTC+5 = 04:00 UTC) da haftalik hisobot
    schedule.every().monday.at("04:00").do(send_weekly_reports).tag("weekly_report")
    while True:
        schedule.run_pending()
        time.sleep(30)

# ============================================================
#  ISHGA TUSHURISH
# ============================================================
if __name__ == "__main__":
    print("=" * 45)
    print("  Odatlar Shakllantirish Boti ishga tushdi!")
    print("=" * 45)
    from telebot.types import BotCommand
    try:
        bot.set_my_commands([
            BotCommand("start",       "Botni ishga tushirish"),
            BotCommand("admin_panel", "Admin panel"),
        ])
        print("Bot menyusi o'rnatildi.")
    except Exception as e:
        print(f"Menyu o'rnatishda xato: {e}")
    threading.Thread(target=scheduler_loop, daemon=True).start()
    print("Bot tayyor! Telegramdan /start yuboring.")
    bot.infinity_polling()