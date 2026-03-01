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
mongo_client = MongoClient(MONGO_URI)
mongo_db     = mongo_client["habit_bot"]
mongo_col    = mongo_db["users"]

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
        "btn_delete":        "🗑 Odat o'chirish",
        "btn_stats":         "📊 Statistika",
        "btn_rating":        "🏆 Reyiting",
        "btn_home":          "🏠 Asosiy menyu",
        "btn_cancel":        "❌ Bekor qilish",
        "btn_yes":           "Ha ✅",
        "btn_no":            "Yo'q ❌",
        "ask_habit_name":    "📝 Odatning nomini yozing:\n\n_Masalan: Kitob o'qish, Sport, Suv ichish..._",
        "ask_habit_time":    "✅ Odat: *{name}*\n\n⏰ Eslatma vaqtini yozing (24 soat):\n\n_Masalan: 07:30 yoki 21:00_",
        "habit_added":       "🎉 *{name}* odati qo'shildi!\n\n⏰ Eslatma: *{time}* da keladi\n🔥 Streak: 0 kun\n\nHar kuni vaqtida bajaring!",
        "wrong_time":        "❌ Noto'g'ri format. HH:MM formatida yozing.\n_Masalan: 08:00_",
        "no_habits":         "📭 Hali odat qo'shilmagan.\n\n➕ Odat qo'shish tugmasini bosing!",
        "no_stats":          "📭 Hali odat yo'q.",
        "confirm_delete":    "⚠️ Haqiqatan ham *{name}* odatini o'chirishni xohlaysizmi?",
        "deleted":           "🗑 *{name}* o'chirildi.",
        "no_delete":         "📭 O'chirish uchun odat yo'q.",
        "done_today":        "✅ Bugun allaqachon bajardingiz!",
        "done_ok":           "✅ *{name}* — bajarildi!",
        "undone":            "❌ *{name}* — bekor qilindi!",
        "all_done":          "Bugungi barcha odatni bajardingiz, tabriklaymiz 🎉",
        "limit":             "⚠️ Odatlarni yaratish me'yori 15 ta!",
        "remind_title":      "⏰ *Eslatma!*\n\n🎯 Odat: *{name}*\n\n{motiv}",
        "btn_done":          "✅ Bajardim!",
        "stats_title":       "📊 *Statistika* — {page}/{total} sahifa",
        "stats_ball":        "⭐ *Jami ball: {ball} ball*",
        "stats_rank":        "🎖 Daraja: {rank}",
        "stats_streak":      "🔥 Streak: {streak} kun",
        "stats_time":        "⏰ Vaqt: {time}",
        "stats_ball2":       "⭐ Odat balli: {ball} ball",
        "stats_done":        "✅ Jami bajarilgan: {n} marta",
        "stats_missed":      "❌ Jami bajarilmagan: {n} marta",
        "stats_last":        "📅 Oxirgi: {d}",
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
        "done_percent":      "Bajarildi: {p}%",
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
        "ask_habit_time":    "✅ Habit: *{name}*\n\n⏰ Enter reminder time (24h):\n\n_Example: 07:30 or 21:00_",
        "habit_added":       "🎉 Habit *{name}* added!\n\n⏰ Reminder: *{time}*\n🔥 Streak: 0 days\n\nComplete it daily!",
        "wrong_time":        "❌ Wrong format. Use HH:MM.\n_Example: 08:00_",
        "no_habits":         "📭 No habits yet.\n\nPress ➕ Add Habit!",
        "no_stats":          "📭 No habits yet.",
        "confirm_delete":    "⚠️ Really delete *{name}*?",
        "deleted":           "🗑 *{name}* deleted.",
        "no_delete":         "📭 No habits to delete.",
        "done_today":        "✅ Already done today!",
        "done_ok":           "✅ *{name}* — done!",
        "undone":            "❌ *{name}* — undone!",
        "all_done":          "You completed all today's habits, congratulations 🎉",
        "limit":             "⚠️ Maximum 15 habits allowed!",
        "remind_title":      "⏰ *Reminder!*\n\n🎯 Habit: *{name}*\n\n{motiv}",
        "btn_done":          "✅ Done!",
        "stats_title":       "📊 *Statistics* — page {page}/{total}",
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
        "done_percent":      "Done: {p}%",
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
        "ask_habit_time":    "✅ Привычка: *{name}*\n\n⏰ Введите время (24ч):\n\n_Пример: 07:30 или 21:00_",
        "habit_added":       "🎉 Привычка *{name}* добавлена!\n\n⏰ Напоминание: *{time}*\n🔥 Серия: 0 дней\n\nВыполняйте каждый день!",
        "wrong_time":        "❌ Неверный формат. Используйте ЧЧ:ММ.\n_Пример: 08:00_",
        "no_habits":         "📭 Привычек пока нет.\n\nНажмите ➕ Добавить!",
        "no_stats":          "📭 Привычек пока нет.",
        "confirm_delete":    "⚠️ Удалить привычку *{name}*?",
        "deleted":           "🗑 *{name}* удалена.",
        "no_delete":         "📭 Нет привычек для удаления.",
        "done_today":        "✅ Уже выполнено сегодня!",
        "done_ok":           "✅ *{name}* — выполнено!",
        "undone":            "❌ *{name}* — отменено!",
        "all_done":          "Вы выполнили все привычки сегодня, поздравляем 🎉",
        "limit":             "⚠️ Максимум 15 привычек!",
        "remind_title":      "⏰ *Напоминание!*\n\n🎯 Привычка: *{name}*\n\n{motiv}",
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
        "done_percent":      "Выполнено: {p}%",
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
        "ask_habit_time":    "✅ Alışkanlık: *{name}*\n\n⏰ Hatırlatma saatini girin (24 saat):\n\n_Örnek: 07:30 veya 21:00_",
        "habit_added":       "🎉 *{name}* alışkanlığı eklendi!\n\n⏰ Hatırlatma: *{time}*\n🔥 Seri: 0 gün\n\nHer gün yapın!",
        "wrong_time":        "❌ Yanlış format. SS:DD formatında girin.\n_Örnek: 08:00_",
        "no_habits":         "📭 Henüz alışkanlık yok.\n\n➕ Ekle butonuna basın!",
        "no_stats":          "📭 Henüz alışkanlık yok.",
        "confirm_delete":    "⚠️ *{name}* alışkanlığını silmek istiyor musunuz?",
        "deleted":           "🗑 *{name}* silindi.",
        "no_delete":         "📭 Silinecek alışkanlık yok.",
        "done_today":        "✅ Bugün zaten yapıldı!",
        "done_ok":           "✅ *{name}* — yapıldı!",
        "undone":            "❌ *{name}* — geri alındı!",
        "all_done":          "Bugünkü tüm alışkanlıkları tamamladınız, tebrikler 🎉",
        "limit":             "⚠️ Maksimum 15 alışkanlık!",
        "remind_title":      "⏰ *Hatırlatma!*\n\n🎯 Alışkanlık: *{name}*\n\n{motiv}",
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
        "done_percent":      "Tamamlandı: {p}%",
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
        "ask_habit_time":    "✅ Дағды: *{name}*\n\n⏰ Еске салу уақытын енгізіңіз (24 сағ):\n\n_Мысалы: 07:30 немесе 21:00_",
        "habit_added":       "🎉 *{name}* дағдысы қосылды!\n\n⏰ Еске салу: *{time}*\n🔥 Streak: 0 күн\n\nКүн сайын орындаңыз!",
        "wrong_time":        "❌ Қате формат. СС:ММ форматында жазыңыз.\n_Мысалы: 08:00_",
        "no_habits":         "📭 Әлі дағды жоқ.\n\n➕ Дағды қосыңыз!",
        "no_stats":          "📭 Әлі дағды жоқ.",
        "confirm_delete":    "⚠️ *{name}* дағдысын жоюды растайсыз ба?",
        "deleted":           "🗑 *{name}* жойылды.",
        "no_delete":         "📭 Жоятын дағды жоқ.",
        "done_today":        "✅ Бүгін орындалды!",
        "done_ok":           "✅ *{name}* — орындалды!",
        "undone":            "❌ *{name}* — болдырылмады!",
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
        "done_percent":      "Орындалды: {p}%",
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
        "ask_habit_time":    "✅ Одат: *{name}*\n\n⏰ Вақти огоҳиро ворид кунед (24 соат):\n\n_Масалан: 07:30 ё 21:00_",
        "habit_added":       "🎉 Одати *{name}* илова шуд!\n\n⏰ Огоҳӣ: *{time}*\n🔥 Streak: 0 рӯз\n\nҲар рӯз иҷро кунед!",
        "wrong_time":        "❌ Формати нодуруст. СС:ДД навишта шавад.\n_Масалан: 08:00_",
        "no_habits":         "📭 Ҳоло одате нест.\n\n➕ Одат илова кунед!",
        "no_stats":          "📭 Ҳоло одате нест.",
        "confirm_delete":    "⚠️ Воқеан одати *{name}* -ро нест кардан мехоҳед?",
        "deleted":           "🗑 *{name}* нест шуд.",
        "no_delete":         "📭 Одате барои нест кардан нест.",
        "done_today":        "✅ Имрӯз аллакай иҷро шуд!",
        "done_ok":           "✅ *{name}* — иҷро шуд!",
        "undone":            "❌ *{name}* — бекор шуд!",
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
        "done_percent":      "Иҷро шуд: {p}%",
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
        "ask_habit_time":    "✅ Endik: *{name}*\n\n⏰ Ýatlatma wagtyny giriziň (24 sagat):\n\n_Mysal: 07:30 ýa-da 21:00_",
        "habit_added":       "🎉 *{name}* endigi goşuldy!\n\n⏰ Ýatlatma: *{time}*\n🔥 Streak: 0 gün\n\nHer gün ýerine ýetiriň!",
        "wrong_time":        "❌ Nädogry format. SS:MM formatynda ýazyň.\n_Mysal: 08:00_",
        "no_habits":         "📭 Entek endik ýok.\n\n➕ Endik goşuň!",
        "no_stats":          "📭 Entek endik ýok.",
        "confirm_delete":    "⚠️ *{name}* endigi pozmak isleýärsiňizmi?",
        "deleted":           "🗑 *{name}* pozuldy.",
        "no_delete":         "📭 Pozmak üçin endik ýok.",
        "done_today":        "✅ Şu gün eýýäm edildi!",
        "done_ok":           "✅ *{name}* — edildi!",
        "undone":            "❌ *{name}* — ýatyryldy!",
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
        "done_percent":      "Edildi: {p}%",
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
        "ask_habit_time":    "✅ Адат: *{name}*\n\n⏰ Эстетме убагын киргизиңиз (24 саат):\n\n_Мисалы: 07:30 же 21:00_",
        "habit_added":       "🎉 *{name}* адаты кошулду!\n\n⏰ Эстетме: *{time}*\n🔥 Streak: 0 күн\n\nКүн сайын аткарыңыз!",
        "wrong_time":        "❌ Туура эмес формат. СС:ММ форматында жазыңыз.\n_Мисалы: 08:00_",
        "no_habits":         "📭 Азырынча адат жок.\n\n➕ Адат кошуңуз!",
        "no_stats":          "📭 Азырынча адат жок.",
        "confirm_delete":    "⚠️ *{name}* адатын чындап жоюуну каалайсызбы?",
        "deleted":           "🗑 *{name}* жойулду.",
        "no_delete":         "📭 Жоюу үчүн адат жок.",
        "done_today":        "✅ Бүгүн буга чейин аткарылды!",
        "done_ok":           "✅ *{name}* — аткарылды!",
        "undone":            "❌ *{name}* — жокко чыгарылды!",
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
        "done_percent":      "Аткарылды: {p}%",
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
        "ask_habit_time":    "✅ Gewohnheit: *{name}*\n\n⏰ Erinnerungszeit eingeben (24h):\n\n_Beispiel: 07:30 oder 21:00_",
        "habit_added":       "🎉 Gewohnheit *{name}* hinzugefügt!\n\n⏰ Erinnerung: *{time}*\n🔥 Serie: 0 Tage\n\nTäglich ausführen!",
        "wrong_time":        "❌ Falsches Format. Bitte HH:MM verwenden.\n_Beispiel: 08:00_",
        "no_habits":         "📭 Noch keine Gewohnheiten.\n\n➕ Füge eine hinzu!",
        "no_stats":          "📭 Noch keine Gewohnheiten.",
        "confirm_delete":    "⚠️ Gewohnheit *{name}* wirklich löschen?",
        "deleted":           "🗑 *{name}* gelöscht.",
        "no_delete":         "📭 Keine Gewohnheit zum Löschen.",
        "done_today":        "✅ Heute bereits erledigt!",
        "done_ok":           "✅ *{name}* — erledigt!",
        "undone":            "❌ *{name}* — rückgängig!",
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
        "done_percent":      "Erledigt: {p}%",
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
        "ask_habit_time":    "✅ Habitude: *{name}*\n\n⏰ Entrez l'heure du rappel (24h):\n\n_Exemple: 07:30 ou 21:00_",
        "habit_added":       "🎉 Habitude *{name}* ajoutée!\n\n⏰ Rappel: *{time}*\n🔥 Série: 0 jours\n\nFaites-le chaque jour!",
        "wrong_time":        "❌ Format incorrect. Utilisez HH:MM.\n_Exemple: 08:00_",
        "no_habits":         "📭 Pas encore d'habitudes.\n\nAppuyez sur ➕ Ajouter!",
        "no_stats":          "📭 Pas encore d'habitudes.",
        "confirm_delete":    "⚠️ Supprimer l'habitude *{name}*?",
        "deleted":           "🗑 *{name}* supprimée.",
        "no_delete":         "📭 Aucune habitude à supprimer.",
        "done_today":        "✅ Déjà fait aujourd'hui!",
        "done_ok":           "✅ *{name}* — fait!",
        "undone":            "❌ *{name}* — annulé!",
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
        "done_percent":      "Accompli: {p}%",
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
    if points >= 500: return ranks[5]
    if points >= 200: return ranks[4]
    if points >= 100: return ranks[3]
    if points >= 50:  return ranks[2]
    if points >= 20:  return ranks[1]
    return ranks[0]

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
    "uz": ["💪 Har bir kun yangi imkoniyat!", "🔥 Ketma-ketligingizni yo'qotmang!", "🌟 Kichik qadamlar katta muvaffaqiyatga!", "🚀 Siz qila olasiz!", "🎯 Maqsadingizga bir qadam!"],
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

def main_menu(uid=None, page=1):
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton(T(uid, "btn_add"),    callback_data="menu_add"),
        InlineKeyboardButton(T(uid, "btn_delete"), callback_data="menu_delete")
    )
    kb.row(
        InlineKeyboardButton(T(uid, "btn_stats"),  callback_data="menu_stats"),
        InlineKeyboardButton(T(uid, "btn_rating"), callback_data="menu_rating")
    )
    if uid:
        u      = load_user(uid)
        today  = today_uz5()
        habits = u.get("habits", [])
        per_page    = 10
        total_pages = (len(habits) + per_page - 1) // per_page if habits else 1
        page        = max(1, min(page, total_pages))
        page_habits = habits[(page - 1) * per_page : page * per_page]
        for h in page_habits:
            hab_type  = h.get("type", "simple")
            rep_count = h.get("repeat_count", 1)
            if hab_type == "repeat" and rep_count > 1:
                done_today = h.get("done_today_count", 0)
                if done_today >= rep_count:
                    label = f"☑️ {h['name']} {done_today}/{rep_count}"
                else:
                    label = f"✅ {h['name']} {done_today}/{rep_count}"
            else:
                done = h.get("last_done") == today
                label = f"☑️ {h['name']}" if done else f"✅ {h['name']}"
            kb.add(InlineKeyboardButton(label, callback_data=f"toggle_{h['id']}"))
        if total_pages > 1:
            nav = []
            if page > 1:
                nav.append(InlineKeyboardButton(f"⬅️ {page-1}", callback_data=f"main_page_{page-1}"))
            nav.append(InlineKeyboardButton(f"📄 {page}/{total_pages}", callback_data="noop"))
            if page < total_pages:
                nav.append(InlineKeyboardButton(f"{page+1} ➡️", callback_data=f"main_page_{page+1}"))
            kb.row(*nav)
    kb.row(
        InlineKeyboardButton("🛒 Bozor",             callback_data="menu_bozor"),
        InlineKeyboardButton(T(uid, "btn_settings"), callback_data="menu_settings")
    )
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
    text  = f"📊 *{header} | {pct_text}*\n"
    text += "━" * 16 + "\n"
    text += T(uid, "stats_ball", ball=total_points) + "\n"
    text += T(uid, "stats_rank", rank=get_rank(uid, total_points)) + "\n"
    text += "━" * 16 + "\n\n"
    for h in habits:
        total  = h.get("total_done", 0)
        points = total * 5
        streak = h.get("streak", 0)
        if streak >= 30:   medal = "🥇"
        elif streak >= 14: medal = "🥈"
        elif streak >= 7:  medal = "🥉"
        else:              medal = "🌱"
        text += f"{medal} *{h['name']}* - {points} ball\n"
    return text

def send_main_menu(uid, text=None):
    u = load_user(uid)
    if text is None:
        text = build_main_text(uid)
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
    kb.add(InlineKeyboardButton("🏠 Asosiy menyu", callback_data="admin_close"))
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

    # /start dan oldingi barcha xabarlarni o'chirish
    # msg.message_id — foydalanuvchi yozgan /start xabari
    # Undan oldingi 60 ta xabarni o'chirishga harakat qilamiz
    def delete_before_start(chat_id, before_id):
        for mid in range(before_id - 1, max(before_id - 61, 0), -1):
            try: bot.delete_message(chat_id, mid)
            except: pass
    threading.Thread(target=delete_before_start, args=(uid, msg.message_id), daemon=True).start()

    is_new = not user_exists(uid)
    u = load_user(uid)
    u["name"]     = name
    u["username"] = msg.from_user.username or "—"
    if "joined_at" not in u:
        u["joined_at"] = str(date.today())
    save_user(uid, u)

    if is_new and uid != ADMIN_ID:
        total = count_users()
        try:
            bot.send_message(
                ADMIN_ID,
                f"🆕 Yangi Foydalanuvchi!\n"
                f"Umumiy: {total}\n"
                f"Ismi: {name}"
            )
        except Exception:
            pass

    if not u.get("lang"):
        sent_lang = bot.send_message(uid, "🌐 Tilni tanlang / Choose language / Выберите язык / Dil seçin:", reply_markup=lang_keyboard())
        u["lang_msg_id"] = sent_lang.message_id
        save_user(uid, u)
        return

    if not u.get("phone"):
        kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb.add(KeyboardButton("📱 Telefon raqamni yuborish", request_contact=True))
        sent = bot.send_message(
            uid,
            f"👋 Salom, *{name}*!\n\n"
            "🌱 *Odatlar Shakllantirish Boti*ga xush kelibsiz!\n\n"
            "Davom etish uchun ro'yxatdan o'ting:\n\n"
            "📌 Telefon raqamingizni yuboring:\n"
            "• Tugmani bosib yuboring, _yoki_\n"
            "• Qo'lda kiriting: *+998901234567*",
            parse_mode="Markdown",
            reply_markup=kb
        )
        u["reg_msg_id"] = sent.message_id
        u["state"] = "waiting_phone_reg"
        save_user(uid, u)
        return

    # Odati bor foydalanuvchiga — to'g'ridan asosiy menyu
    if u.get("habits"):
        sent_main = bot.send_message(
            uid,
            build_main_text(uid),
            parse_mode="Markdown",
            reply_markup=main_menu(uid)
        )
        u["main_msg_id"] = sent_main.message_id
        ids = u.get("start_msg_ids", [])
        ids.append(sent_main.message_id)
        u["start_msg_ids"] = ids
        save_user(uid, u)
        return

    # Odati yo'q foydalanuvchiga — xush kelibsiz xabari
    sent_main = bot.send_message(
        uid,
        T(uid, "welcome_new", name=name),
        parse_mode="Markdown",
        reply_markup=main_menu(uid)
    )
    u["main_msg_id"] = sent_main.message_id
    ids = u.get("start_msg_ids", [])
    ids.append(sent_main.message_id)
    u["start_msg_ids"] = ids
    save_user(uid, u)

# ============================================================
#  TELEFON RAQAMI
# ============================================================
@bot.message_handler(content_types=["contact"])
def handle_contact(msg):
    uid  = msg.from_user.id
    name = msg.from_user.first_name
    u    = load_user(uid)
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
        # Sozlamalar menyusiga qaytish
        def back_to_settings(chat_id, ok_mid):
            time.sleep(3)
            try: bot.delete_message(chat_id, ok_mid)
            except: pass
            try:
                u2 = load_user(chat_id)
                kb_set = InlineKeyboardMarkup()
                kb_set.add(InlineKeyboardButton(T(chat_id, "btn_change_lang"), callback_data="settings_lang"))
                kb_set.add(InlineKeyboardButton(T(chat_id, "btn_change_info"), callback_data="settings_info"))
                kb_set.add(InlineKeyboardButton(T(chat_id, "btn_home"),        callback_data="menu_main"))
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
    # Til tanlash
    sent_lang = bot.send_message(uid, "🌐 Tilni tanlang / Choose language / Выберите язык / Dil seçin:", reply_markup=lang_keyboard())
    u["lang_msg_id"] = sent_lang.message_id
    save_user(uid, u)

# ============================================================
#  MATN HANDLER
# ============================================================
@bot.message_handler(func=lambda m: True)
def handle_text(msg):
    uid  = msg.from_user.id
    text = msg.text
    if not text:
        return
    u     = load_user(uid)
    state = u.get("state")

    if (state not in ("admin_bc_private", "admin_bc_groups", "admin_bc_all") and
        not (state and state.startswith("admin_waiting_channel")) and
        not (state and state.startswith("admin_waiting_points")) and
        not (state and state.startswith("admin_waiting_reply_")) and
        state != "editing_habit_time" and
        state != "editing_all_habits_time" and
        state != "bozor_waiting_transfer_id" and
        state != "bozor_waiting_transfer_amount" and
        state != "bozor_waiting_subtract") and uid != ADMIN_ID:
        if not check_subscription(uid):
            send_sub_required(uid)
            return

    # --- Broadcast ---
    if state in ("admin_bc_private", "admin_bc_groups", "admin_bc_all") and uid == ADMIN_ID:
        users       = load_all_users()
        sent_count  = 0
        failed      = 0
        failed_list = []
        for target_uid, udata in users.items():
            if int(target_uid) == ADMIN_ID:
                continue
            if state == "admin_bc_groups":
                if udata.get("chat_type", "private") != "group":
                    continue
            try:
                bot.copy_message(int(target_uid), uid, msg.message_id)
                sent_count += 1
            except Exception as e:
                failed += 1
                failed_list.append(f"{udata.get('name','?')} ({target_uid}): botni bloklagan")
                print(f"[broadcast] xato: {target_uid} — {e}")
        u["state"] = None
        # Bloklagan foydalanuvchilar ma'lumotini vaqtincha saqlaymiz
        u["bc_failed_list"] = failed_list
        save_user(uid, u)
        result = (
            f"📊 *Broadcast natija:*\n\n"
            f"✅ Yetib bordi: *{sent_count} ta*\n"
            f"🚫 Bloklagan: *{failed} ta*"
        )
        kb_bc = InlineKeyboardMarkup()
        if failed > 0:
            kb_bc.row(
                InlineKeyboardButton("✅ Tasdiqlash",  callback_data="bc_confirm"),
                InlineKeyboardButton("📋 Batafsil",   callback_data="bc_detail")
            )
        else:
            kb_bc.add(InlineKeyboardButton("✅ Tasdiqlash", callback_data="bc_confirm"))
        bot.send_message(uid, result, parse_mode="Markdown", reply_markup=kb_bc)
        return

    # --- Telefon raqam (ro'yxatdan o'tish - qo'lda kiritish) ---
    if state in ("waiting_phone_reg", "updating_phone", "updating_phone_text"):
        import re
        phone_clean = re.sub(r"[\s\-\(\)]", "", text.strip())
        if not re.match(r"^\+?\d{9,15}$", phone_clean):
            sent_err = bot.send_message(uid, "❌ Noto'g'ri format. Masalan: *+998901234567*", parse_mode="Markdown")
            def del_perr(chat_id, mid):
                time.sleep(3)
                try: bot.delete_message(chat_id, mid)
                except: pass
            threading.Thread(target=del_perr, args=(uid, sent_err.message_id), daemon=True).start()
            return
        try:
            bot.delete_message(uid, msg.message_id)
        except Exception:
            pass
        if state == "waiting_phone_reg":
            reg_msg_id = u.pop("reg_msg_id", None)
            if reg_msg_id:
                try: bot.delete_message(uid, reg_msg_id)
                except: pass
            u["phone"] = phone_clean
            u["state"] = None
            save_user(uid, u)
            sent_ok = bot.send_message(uid, "✅", reply_markup=ReplyKeyboardRemove())
            def del_ok_reg(chat_id, mid):
                time.sleep(2)
                try: bot.delete_message(chat_id, mid)
                except: pass
            threading.Thread(target=del_ok_reg, args=(uid, sent_ok.message_id), daemon=True).start()
            sent_lang = bot.send_message(uid, "🌐 Tilni tanlang / Choose language / Выберите язык / Dil seçin:", reply_markup=lang_keyboard())
            u["lang_msg_id"] = sent_lang.message_id
            save_user(uid, u)
        else:  # updating_phone
            info_msg_id = u.pop("info_msg_id", None)
            if info_msg_id:
                try: bot.delete_message(uid, info_msg_id)
                except: pass
            u["phone"] = phone_clean
            u["state"] = None
            save_user(uid, u)
            sent_ok2 = bot.send_message(uid, "✅", reply_markup=ReplyKeyboardRemove())
            def back_to_set(chat_id, ok_mid):
                time.sleep(3)
                try: bot.delete_message(chat_id, ok_mid)
                except: pass
                u2 = load_user(chat_id)
                kb_set = InlineKeyboardMarkup()
                kb_set.add(InlineKeyboardButton(T(chat_id, "btn_change_lang"), callback_data="settings_lang"))
                kb_set.add(InlineKeyboardButton(T(chat_id, "btn_change_info"), callback_data="settings_info"))
                kb_set.add(InlineKeyboardButton(T(chat_id, "btn_home"),        callback_data="menu_main"))
                sent = bot.send_message(chat_id, T(chat_id, "settings_title"), parse_mode="Markdown", reply_markup=kb_set)
                u2["main_msg_id"] = sent.message_id
                save_user(chat_id, u2)
            threading.Thread(target=back_to_set, args=(uid, sent_ok2.message_id), daemon=True).start()
        return

    # --- Ball berish: ID kiritish ---
    if state == "admin_waiting_points_id" and uid == ADMIN_ID:
        try:
            bot.delete_message(uid, msg.message_id)
        except Exception:
            pass
        target_id = text.strip()
        try:
            target_uid_int = int(target_id)
        except ValueError:
            bot.send_message(uid, "❌ Noto'g'ri ID. Faqat raqam kiriting!")
            return
        target_u = load_user(target_uid_int)
        if not target_u.get("phone"):
            bot.send_message(uid, f"❌ ID {target_id} topilmadi!")
            return
        gp_msg_id = u.pop("give_points_msg_id", None)
        if gp_msg_id:
            try: bot.delete_message(uid, gp_msg_id)
            except: pass
        u["state"] = "admin_waiting_points_amount"
        u["give_points_target"] = target_uid_int
        kb2 = InlineKeyboardMarkup()
        kb2.add(InlineKeyboardButton("❌ Bekor qilish", callback_data="admin_cancel"))
        sent_gp2 = bot.send_message(
            uid,
            f"🎁 *Ball berish / ayirish*\n\n"
            f"👤 Foydalanuvchi: *{target_u.get('name','?')}* (ID: `{target_id}`)\n"
            f"⭐ Hozirgi ball: *{target_u.get('points', 0)}*\n\n"
            f"Qo'shish uchun: *+50*\n"
            f"Ayirish uchun: *-50*\n\n"
            f"Ball miqdorini kiriting:",
            parse_mode="Markdown",
            reply_markup=kb2
        )
        u["give_points_msg_id"] = sent_gp2.message_id
        save_user(uid, u)
        return

    # --- Ball berish: miqdor kiritish ---
    if state == "admin_waiting_points_amount" and uid == ADMIN_ID:
        try:
            bot.delete_message(uid, msg.message_id)
        except Exception:
            pass
        amount_str = text.strip().replace(" ", "")
        try:
            amount = int(amount_str)
        except ValueError:
            bot.send_message(uid, "❌ Noto'g'ri format. Masalan: *+50* yoki *-30*", parse_mode="Markdown")
            return
        target_uid_int = u.get("give_points_target")
        gp_msg_id = u.pop("give_points_msg_id", None)
        if gp_msg_id:
            try: bot.delete_message(uid, gp_msg_id)
            except: pass
        u["state"] = None
        u.pop("give_points_target", None)
        save_user(uid, u)
        # Foydalanuvchi balini yangilash
        target_u = load_user(target_uid_int)
        old_points = target_u.get("points", 0)
        new_points = max(0, old_points + amount)
        target_u["points"] = new_points
        save_user(target_uid_int, target_u)
        # Admin panelga qaytish
        sign = "+" if amount >= 0 else ""
        result_text = (
            f"✅ *{target_u.get('name','?')}* (ID: `{target_uid_int}`)\n"
            f"Ball: *{old_points}* → *{new_points}* ({sign}{amount})"
        )
        bot.send_message(uid, result_text, parse_mode="Markdown", reply_markup=admin_menu())
        # Foydalanuvchiga xabar yuborish
        if amount >= 0:
            user_notif = f"🎁 Sizga *{amount}* ball qo'shildi!\n\n⭐ Jami ball: *{new_points}*"
        else:
            user_notif = f"📉 Hisobingizdan *{abs(amount)}* ball ayirildi.\n\n⭐ Qolgan ball: *{new_points}*"
        try:
            kb_notif = InlineKeyboardMarkup()
            kb_notif.add(InlineKeyboardButton("✅ Ko'rdim", callback_data="dismiss_ball_notif"))
            sent_notif = bot.send_message(target_uid_int, user_notif, parse_mode="Markdown", reply_markup=kb_notif)
        except Exception:
            pass
        return

    # --- Kanal username ---
    if state and state.startswith("admin_waiting_channel") and uid == ADMIN_ID:
        channel = text.strip()
        if not channel.startswith("@"):
            channel = "@" + channel
        try:
            bot.delete_message(uid, msg.message_id)
        except Exception:
            pass
        channel_msg_id = u.pop("channel_msg_id", None)
        if channel_msg_id:
            try:
                bot.delete_message(uid, channel_msg_id)
            except Exception:
                pass
        try:
            chat     = bot.get_chat(channel)
            settings = load_settings()
            # Slot aniqlash
            if state == "admin_waiting_channel":
                slot = 1
            else:
                slot = int(state.split("_")[-1])
            settings[f"required_channel_{slot}"]       = channel
            settings[f"required_channel_title_{slot}"] = chat.title
            save_settings(settings)
            u["state"] = None
            save_user(uid, u)
            sent_confirm = bot.send_message(uid, f"✅ {slot}-kanal tasdiqlandi: *{chat.title}* (`{channel}`)", parse_mode="Markdown")
            def delete_confirm_and_menu(chat_id, message_id):
                time.sleep(2)
                try:
                    bot.delete_message(chat_id, message_id)
                except Exception:
                    pass
                bot.send_message(chat_id, "🛠 *Admin panel | Maxfiy va muhim qism*", parse_mode="Markdown", reply_markup=admin_menu())
            threading.Thread(target=delete_confirm_and_menu, args=(uid, sent_confirm.message_id), daemon=True).start()
        except Exception as e:
            bot.send_message(uid, f"❌ Xatolik: `{e}`\n\nBot kanalga admin sifatida qo'shilganmi?\n\nQaytadan username yozing:", parse_mode="Markdown")
        return

    # --- Foydalanuvchiga javob (admin) ---
    if state and state.startswith("admin_waiting_reply_") and uid == ADMIN_ID:
        target_user_id = int(state[20:])
        try: bot.delete_message(uid, msg.message_id)
        except: pass
        reply_msg_id = u.pop("reply_msg_id", None)
        if reply_msg_id:
            try: bot.delete_message(uid, reply_msg_id)
            except: pass
        u["state"] = None
        save_user(uid, u)
        # Foydalanuvchiga yuborish
        try:
            bot.send_message(
                target_user_id,
                f"📩 *Dasturchidan javob:*\n\n{text}",
                parse_mode="Markdown"
            )
            # Eski admin panel va main menyularni o'chirish
            u3 = load_user(uid)
            for mid_key in ("admin_msg_id", "main_msg_id"):
                old_mid = u3.pop(mid_key, None)
                if old_mid:
                    try: bot.delete_message(uid, old_mid)
                    except: pass
            save_user(uid, u3)
            sent_ok = bot.send_message(uid, "✅ Javob yuborildi!")
            def del_ok_and_panel(chat_id, ok_mid):
                time.sleep(2)
                try: bot.delete_message(chat_id, ok_mid)
                except: pass
                bot.send_message(chat_id, "🛠 *Admin panel | Maxfiy va muhim qism*", parse_mode="Markdown", reply_markup=admin_menu())
            threading.Thread(target=del_ok_and_panel, args=(uid, sent_ok.message_id), daemon=True).start()
        except Exception as e:
            bot.send_message(uid, f"❌ Xatolik: {e}", reply_markup=admin_menu())
        return

    # --- Dasturchiga habar ---
    if state == "waiting_dev_message":
        try: bot.delete_message(uid, msg.message_id)
        except: pass
        dev_msg_id = u.pop("dev_msg_id", None)
        if dev_msg_id:
            try: bot.delete_message(uid, dev_msg_id)
            except: pass
        u["state"] = None
        save_user(uid, u)
        user_name = u.get("name", "Noma'lum")
        user_id_str = str(uid)
        # Adminga sarlavha bilan yuborish + "Javob berish" tugmasi
        try:
            kb_reply = InlineKeyboardMarkup()
            kb_reply.add(InlineKeyboardButton(
                f"↩️ Javob berish ({user_name})",
                callback_data=f"admin_reply_to_{uid}"
            ))
            bot.send_message(
                ADMIN_ID,
                f"📩 *Dasturchi sizga foydalanuvchidan habar bor:*\n\n"
                f"👤 {user_name} (ID: `{user_id_str}`)\n\n"
                f"💬 {text}",
                parse_mode="Markdown",
                reply_markup=kb_reply
            )
        except Exception:
            pass
        # Foydalanuvchiga tasdiq
        sent_ok = bot.send_message(uid, "✅ Habaringiz dasturchiga yuborildi!")
        def del_dev_ok(chat_id, mid):
            time.sleep(3)
            try: bot.delete_message(chat_id, mid)
            except: pass
        threading.Thread(target=del_dev_ok, args=(uid, sent_ok.message_id), daemon=True).start()
        # Sozlamalar menyusiga qaytish
        def back_to_set_dev(chat_id):
            time.sleep(3)
            kb_set = InlineKeyboardMarkup()
            kb_set.add(InlineKeyboardButton(T(chat_id, "btn_change_lang"), callback_data="settings_lang"))
            kb_set.add(InlineKeyboardButton(T(chat_id, "btn_change_info"), callback_data="settings_info"))
            kb_set.add(InlineKeyboardButton("💬 Dasturchiga habar",        callback_data="settings_contact_dev"))
            kb_set.add(InlineKeyboardButton(T(chat_id, "btn_home"),        callback_data="menu_main"))
            u2 = load_user(chat_id)
            sent = bot.send_message(chat_id, T(chat_id, "settings_title"), parse_mode="Markdown", reply_markup=kb_set)
            u2["main_msg_id"] = sent.message_id
            save_user(chat_id, u2)
        threading.Thread(target=back_to_set_dev, args=(uid,), daemon=True).start()
        return

    # --- Odat takror soni ---
    if state == "waiting_habit_repeat_count":
        try:
            count = int(text.strip())
            if count < 2 or count > 20:
                raise ValueError
        except ValueError:
            try: bot.delete_message(uid, msg.message_id)
            except: pass
            sent_err = bot.send_message(uid, "❌ 2 dan 20 gacha raqam kiriting!", parse_mode="Markdown")
            u["time_err_msg_id"] = sent_err.message_id
            save_user(uid, u)
            return
        try: bot.delete_message(uid, msg.message_id)
        except: pass
        old_msg_id = u.pop("temp_msg_id", None)
        if old_msg_id:
            try: bot.delete_message(uid, old_msg_id)
            except: pass
        u["temp_habit"]["repeat_count"] = count
        u["temp_habit"]["repeat_times"] = []       # har bir vaqtni yig'amiz
        u["state"] = "waiting_habit_repeat_times"
        habit_name = u["temp_habit"].get("name", "")
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.add(InlineKeyboardButton(T(uid, "btn_cancel"), callback_data="cancel"))
        prompt = (
            f"⏰ *{habit_name}* odati uchun *1/{count}* eslatma vaqtini kiriting:\n\n"
            f"_Masalan: 06:00_"
        )
        sent = bot.send_message(uid, prompt, parse_mode="Markdown", reply_markup=cancel_kb)
        u["temp_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    # --- Odat nomi ---
    if state == "waiting_habit_name":
        temp = u.get("temp_habit", {})
        temp["name"] = text
        u["temp_habit"] = temp
        try:
            bot.delete_message(uid, msg.message_id)
        except Exception:
            pass
        old_msg_id = u.pop("temp_msg_id", None)
        if old_msg_id:
            try:
                bot.delete_message(uid, old_msg_id)
            except Exception:
                pass
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.add(InlineKeyboardButton(T(uid, "btn_cancel"), callback_data="cancel"))
        hab_type  = temp.get("type", "simple")
        rep_count = temp.get("repeat_count", 1)
        if hab_type == "repeat":
            # Takrorlanuvchi: nom kiritildi, endi son so'rasin
            u["state"] = "waiting_habit_repeat_count"
            prompt = (
                f"🔁 *{text}* — kuniga necha marta takrorlanadi?\n\n"
                f"_Masalan: 5 (5 vaqt namoz uchun)_"
            )
        else:
            u["state"] = "waiting_habit_time"
            prompt = T(uid, "ask_habit_time", name=text)
        sent = bot.send_message(uid, prompt, parse_mode="Markdown", reply_markup=cancel_kb)
        u["temp_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    # --- Takrorlanuvchi vaqtlar ---
    if state == "waiting_habit_repeat_times":
        try:
            t_obj    = datetime.strptime(text.strip(), "%H:%M")
            time_str = t_obj.strftime("%H:%M")
        except ValueError:
            try: bot.delete_message(uid, msg.message_id)
            except: pass
            sent_err = bot.send_message(uid, T(uid, "wrong_time"), parse_mode="Markdown")
            u["time_err_msg_id"] = sent_err.message_id
            save_user(uid, u)
            return
        try: bot.delete_message(uid, msg.message_id)
        except: pass
        old_msg_id = u.pop("temp_msg_id", None)
        if old_msg_id:
            try: bot.delete_message(uid, old_msg_id)
            except: pass
        temp = u.get("temp_habit", {})
        times_list = temp.get("repeat_times", [])
        times_list.append(time_str)
        temp["repeat_times"] = times_list
        u["temp_habit"] = temp
        rep_count = temp.get("repeat_count", 2)
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.add(InlineKeyboardButton(T(uid, "btn_cancel"), callback_data="cancel"))
        if len(times_list) < rep_count:
            # Keyingi vaqtni so'rash
            next_n = len(times_list) + 1
            done_str = ", ".join(times_list)
            prompt = (
                f"⏰ *{temp['name']}* odati uchun *{next_n}/{rep_count}* eslatma vaqtini kiriting:\n\n"
                f"✅ Kiritilganlar: {done_str}\n\n"
                f"_Masalan: 12:00_"
            )
            sent = bot.send_message(uid, prompt, parse_mode="Markdown", reply_markup=cancel_kb)
            u["temp_msg_id"] = sent.message_id
            save_user(uid, u)
            return
        # Barcha vaqtlar kiritildi — odatni saqlash
        first_time = times_list[0]
        habit_base = {
            "id":           str(int(time.time())),
            "name":         temp["name"],
            "time":         first_time,
            "type":         "repeat",
            "repeat_count": rep_count,
            "repeat_times": times_list,
            "streak":       0,
            "total_done":   0,
            "last_done":    None,
            "done_today_count": 0,
            "created":      str(date.today()),
        }
        if "habits" not in u:
            u["habits"] = []
        u["habits"].append(habit_base)
        u["state"] = None
        u.pop("temp_habit", None)
        save_user(uid, u)
        # Har bir kiritilgan vaqtga alohida eslatma
        for i, t_str in enumerate(times_list):
            rep_habit      = dict(habit_base)
            rep_habit["id"]   = f"{habit_base['id']}_{i}"
            rep_habit["time"] = t_str
            rep_habit["name"] = f"{habit_base['name']} ({i+1}/{rep_count})"
            schedule_habit(uid, rep_habit)
        times_display = " | ".join(f"*{t}*" for t in times_list)
        type_info     = f"\n🔁 Takror vaqtlari: {times_display}"
        is_first_habit = len(u.get("habits", [])) == 1
        added_text = T(uid, "habit_added", name=habit_base["name"], time=first_time) + type_info
        sent_added = bot.send_message(uid, added_text, parse_mode="Markdown")
        def del_added_rep(chat_id, mid, first):
            time.sleep(5)
            try: bot.delete_message(chat_id, mid)
            except: pass
            u2 = load_user(chat_id)
            main_text = build_main_text(chat_id)
            if first:
                main_text += f"\n\n*{T(chat_id, 'hint_toggle')}*"
            sent2 = bot.send_message(chat_id, main_text, parse_mode="Markdown", reply_markup=main_menu(chat_id))
            u2["main_msg_id"] = sent2.message_id
            save_user(chat_id, u2)
        threading.Thread(target=del_added_rep, args=(uid, sent_added.message_id, is_first_habit), daemon=True).start()
        return

    # --- Vaqt ---
    if state == "waiting_habit_time":
        try:
            t        = datetime.strptime(text.strip(), "%H:%M")
            time_str = t.strftime("%H:%M")
            err_msg_id = u.pop("time_err_msg_id", None)
            if err_msg_id:
                def del_err(chat_id, msg_id):
                    time.sleep(3)
                    try: bot.delete_message(chat_id, msg_id)
                    except: pass
                threading.Thread(target=del_err, args=(uid, err_msg_id), daemon=True).start()
            temp      = u.get("temp_habit", {})
            hab_type  = temp.get("type", "simple")
            rep_count = temp.get("repeat_count", 1)
            habit_base = {
                "id":           str(int(time.time())),
                "name":         temp["name"],
                "time":         time_str,
                "type":         hab_type,
                "repeat_count": rep_count,
                "streak":       0,
                "total_done":   0,
                "last_done":    None,
                "created":      str(date.today()),
            }
            if "habits" not in u:
                u["habits"] = []
            u["habits"].append(habit_base)
            u["state"] = None
            u.pop("temp_habit", None)
            try: bot.delete_message(uid, msg.message_id)
            except: pass
            old_msg_id = u.pop("temp_msg_id", None)
            if old_msg_id:
                try: bot.delete_message(uid, old_msg_id)
                except: pass
            save_user(uid, u)
            # Eslatmalarni rejalashtirish
            if hab_type == "repeat" and rep_count > 1:
                # Vaqtni teng bo'laklarga bo'lib eslatma
                h0, m0  = map(int, time_str.split(":"))
                start_m = h0 * 60 + m0
                # Kunni 24 soatga teng bo'lib, 1-eslatma berilgan vaqtdan boshlanadi
                interval_m = (24 * 60) // rep_count
                for i in range(rep_count):
                    t_m   = (start_m + i * interval_m) % (24 * 60)
                    t_h   = t_m // 60
                    t_min = t_m % 60
                    rep_habit = dict(habit_base)
                    rep_habit["id"]   = f"{habit_base['id']}_{i}"
                    rep_habit["time"] = f"{t_h:02d}:{t_min:02d}"
                    rep_habit["name"] = f"{habit_base['name']} ({i+1}/{rep_count})"
                    # Faqat schedulelab qo'yamiz (habits ga qo'shmaymiz)
                    schedule_habit(uid, rep_habit)
                # Asosiy habitni ham schedule qilamiz
                schedule_habit(uid, habit_base)
            else:
                schedule_habit(uid, habit_base)
            # Tip matni
            if hab_type == "repeat":
                type_info = f"\n🔁 Takror: {rep_count} marta/kun"
            else:
                type_info = ""
            is_first_habit = len(u.get("habits", [])) == 1
            added_text = T(uid, "habit_added", name=habit_base["name"], time=time_str) + type_info
            sent_added = bot.send_message(uid, added_text, parse_mode="Markdown")
            def del_added_and_main(chat_id, mid, first):
                time.sleep(5)
                try: bot.delete_message(chat_id, mid)
                except: pass
                u2 = load_user(chat_id)
                main_text = build_main_text(chat_id)
                if first:
                    main_text += f"\n\n*{T(chat_id, 'hint_toggle')}*"
                sent2 = bot.send_message(chat_id, main_text, parse_mode="Markdown", reply_markup=main_menu(chat_id))
                u2["main_msg_id"] = sent2.message_id
                save_user(chat_id, u2)
            threading.Thread(target=del_added_and_main, args=(uid, sent_added.message_id, is_first_habit), daemon=True).start()
        except ValueError:
            sent_err = bot.send_message(uid, T(uid, "wrong_time"), parse_mode="Markdown")
            u["time_err_msg_id"] = sent_err.message_id
            save_user(uid, u)
        return

    # --- Odat vaqtini tahrirlash ---
    if state == "editing_habit_time":
        try:
            t_obj    = datetime.strptime(text.strip(), "%H:%M")
            time_str = t_obj.strftime("%H:%M")
        except ValueError:
            try: bot.delete_message(uid, msg.message_id)
            except: pass
            sent_err = bot.send_message(uid, T(uid, "wrong_time"), parse_mode="Markdown")
            u["time_err_msg_id"] = sent_err.message_id
            save_user(uid, u)
            return
        try: bot.delete_message(uid, msg.message_id)
        except: pass
        old_msg_id = u.pop("temp_msg_id", None)
        if old_msg_id:
            try: bot.delete_message(uid, old_msg_id)
            except: pass
        habit_id   = u.get("editing_habit_id")
        h_type     = u.get("editing_habit_type", "simple")
        rep_count  = u.get("editing_habit_rep_count", 1)
        times_coll = u.get("editing_habit_times_collected", [])
        times_coll.append(time_str)
        u["editing_habit_times_collected"] = times_coll
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.add(InlineKeyboardButton(T(uid, "btn_cancel"), callback_data="settings_habits_time"))
        if h_type == "repeat" and rep_count > 1 and len(times_coll) < rep_count:
            next_n   = len(times_coll) + 1
            done_str = ", ".join(times_coll)
            prompt = (
                f"⏰ *{next_n}/{rep_count}* yangi vaqtni kiriting:\n\n"
                f"✅ Kiritilganlar: {done_str}\n\n"
                f"_Masalan: 12:00_"
            )
            sent = bot.send_message(uid, prompt, parse_mode="Markdown", reply_markup=cancel_kb)
            u["temp_msg_id"] = sent.message_id
            save_user(uid, u)
            return
        # Barcha vaqtlar kiritildi — yangilash
        for h in u.get("habits", []):
            if h["id"] == habit_id:
                schedule.clear(f"{uid}_{habit_id}")
                if h_type == "repeat" and rep_count > 1:
                    h["time"]         = times_coll[0]
                    h["repeat_times"] = times_coll
                    for i, t_s in enumerate(times_coll):
                        rep_h        = dict(h)
                        rep_h["id"]  = f"{habit_id}_{i}"
                        rep_h["time"]= t_s
                        rep_h["name"]= f"{h['name']} ({i+1}/{rep_count})"
                        schedule_habit(uid, rep_h)
                else:
                    h["time"] = time_str
                    schedule_habit(uid, h)
                break
        u["state"] = None
        u.pop("editing_habit_id", None)
        u.pop("editing_habit_type", None)
        u.pop("editing_habit_rep_count", None)
        u.pop("editing_habit_times_collected", None)
        save_user(uid, u)
        if h_type == "repeat":
            times_display = " | ".join(f"*{t}*" for t in times_coll)
            ok_text = f"✅ Vaqtlar yangilandi: {times_display}"
        else:
            ok_text = f"✅ Vaqt yangilandi: *{time_str}*"
        sent_ok = bot.send_message(uid, ok_text, parse_mode="Markdown")
        def del_edit_ok(chat_id, mid):
            time.sleep(2)
            try: bot.delete_message(chat_id, mid)
            except: pass
        threading.Thread(target=del_edit_ok, args=(uid, sent_ok.message_id), daemon=True).start()
        # Odatlar ro'yxatiga qaytish
        kb_back = InlineKeyboardMarkup()
        kb_back.add(InlineKeyboardButton("⬅️ Odatlar ro'yxati", callback_data="settings_habits_time"))
        kb_back.add(InlineKeyboardButton(T(uid, "btn_home"),     callback_data="menu_main"))
        sent2 = bot.send_message(uid, "⏰ *Odatlar vaqtini tahrirlash*", parse_mode="Markdown", reply_markup=kb_back)
        u2 = load_user(uid)
        u2["main_msg_id"] = sent2.message_id
        save_user(uid, u2)
        return

    # --- Barcha odatlar uchun umumiy vaqt ---
    if state == "editing_all_habits_time":
        try:
            t_obj    = datetime.strptime(text.strip(), "%H:%M")
            time_str = t_obj.strftime("%H:%M")
        except ValueError:
            try: bot.delete_message(uid, msg.message_id)
            except: pass
            sent_err = bot.send_message(uid, T(uid, "wrong_time"), parse_mode="Markdown")
            u["time_err_msg_id"] = sent_err.message_id
            save_user(uid, u)
            return
        try: bot.delete_message(uid, msg.message_id)
        except: pass
        old_msg_id = u.pop("temp_msg_id", None)
        if old_msg_id:
            try: bot.delete_message(uid, old_msg_id)
            except: pass
        for h in u.get("habits", []):
            if h.get("type", "simple") != "repeat":
                schedule.clear(f"{uid}_{h['id']}")
                h["time"] = time_str
                schedule_habit(uid, h)
        u["state"] = None
        u.pop("editing_habit_id", None)
        save_user(uid, u)
        sent_ok = bot.send_message(uid, f"✅ Barcha oddiy odatlar uchun vaqt belgilandi: *{time_str}*", parse_mode="Markdown")
        def del_all_ok(chat_id, mid):
            time.sleep(2)
            try: bot.delete_message(chat_id, mid)
            except: pass
        threading.Thread(target=del_all_ok, args=(uid, sent_ok.message_id), daemon=True).start()
        kb_back = InlineKeyboardMarkup()
        kb_back.add(InlineKeyboardButton("⬅️ Odatlar ro'yxati", callback_data="settings_habits_time"))
        kb_back.add(InlineKeyboardButton(T(uid, "btn_home"),     callback_data="menu_main"))
        sent2 = bot.send_message(uid, "⏰ *Odatlar vaqtini tahrirlash*", parse_mode="Markdown", reply_markup=kb_back)
        u2 = load_user(uid)
        u2["main_msg_id"] = sent2.message_id
        save_user(uid, u2)
        return

    # --- Bozor: transfer ID ---
    if state == "bozor_waiting_transfer_id":
        try: bot.delete_message(uid, msg.message_id)
        except: pass
        target_id_str = text.strip()
        if not target_id_str.isdigit():
            sent_err = bot.send_message(uid, "❌ Noto'g'ri ID. Faqat raqam kiriting.", parse_mode="Markdown")
            def del_berr(chat_id, mid):
                time.sleep(3)
                try: bot.delete_message(chat_id, mid)
                except: pass
            threading.Thread(target=del_berr, args=(uid, sent_err.message_id), daemon=True).start()
            return
        target_id = int(target_id_str)
        if target_id == uid:
            sent_err = bot.send_message(uid, "❌ O'zingizga ball yubora olmaysiz.", parse_mode="Markdown")
            def del_berr2(chat_id, mid):
                time.sleep(3)
                try: bot.delete_message(chat_id, mid)
                except: pass
            threading.Thread(target=del_berr2, args=(uid, sent_err.message_id), daemon=True).start()
            return
        target_u = load_user(target_id)
        if not target_u.get("name"):
            sent_err = bot.send_message(uid, "❌ Bu ID bo'yicha foydalanuvchi topilmadi.", parse_mode="Markdown")
            def del_berr3(chat_id, mid):
                time.sleep(3)
                try: bot.delete_message(chat_id, mid)
                except: pass
            threading.Thread(target=del_berr3, args=(uid, sent_err.message_id), daemon=True).start()
            return
        u["state"]               = "bozor_waiting_transfer_amount"
        u["bozor_transfer_to"]   = target_id
        old_msg_id = u.pop("temp_msg_id", None)
        if old_msg_id:
            try: bot.delete_message(uid, old_msg_id)
            except: pass
        save_user(uid, u)
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.row(
            InlineKeyboardButton("⬅️ Orqaga", callback_data="bozor_transfer"),
            InlineKeyboardButton(T(uid, "btn_home"), callback_data="menu_main")
        )
        sent = bot.send_message(
            uid,
            f"💸 *{target_u.get('name','?')}* ga necha ball yubormoqchisiz?\n\n"
            f"⭐ Sizning balingiz: *{u.get('points', 0)} ball*",
            parse_mode="Markdown", reply_markup=cancel_kb
        )
        u["temp_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    # --- Bozor: transfer miqdori ---
    if state == "bozor_waiting_transfer_amount":
        try: bot.delete_message(uid, msg.message_id)
        except: pass
        try:
            amount = int(text.strip())
            if amount <= 0: raise ValueError
        except ValueError:
            sent_err = bot.send_message(uid, "❌ Musbat son kiriting.", parse_mode="Markdown")
            def del_aerr(chat_id, mid):
                time.sleep(3)
                try: bot.delete_message(chat_id, mid)
                except: pass
            threading.Thread(target=del_aerr, args=(uid, sent_err.message_id), daemon=True).start()
            return
        my_balls   = u.get("points", 0)
        target_id  = u.get("bozor_transfer_to")
        if amount > my_balls:
            old_msg_id = u.pop("temp_msg_id", None)
            if old_msg_id:
                try: bot.delete_message(uid, old_msg_id)
                except: pass
            sent_err = bot.send_message(
                uid,
                f"😔 Afsuski, sizning hisobingizda *{my_balls} ball* bor — *{amount} ball* yo'q!",
                parse_mode="Markdown"
            )
            def del_noball(chat_id, mid):
                time.sleep(3)
                try: bot.delete_message(chat_id, mid)
                except: pass
                # Bozor menyusiga qaytish
                u2 = load_user(chat_id)
                u2["state"] = None
                u2.pop("bozor_transfer_to", None)
                balls2 = u2.get("points", 0)
                kb_b = InlineKeyboardMarkup()
                kb_b.row(
                    InlineKeyboardButton("💸 Ballarni ayirboshlash", callback_data="bozor_transfer"),
                    InlineKeyboardButton("✏️ Ballarni tahrirlash",   callback_data="bozor_edit")
                )
                kb_b.add(InlineKeyboardButton(T(chat_id, "btn_home"), callback_data="menu_main"))
                s2 = bot.send_message(chat_id, f"🛒 *Bozor*\n\n⭐ Sizning balingiz: *{balls2} ball*", parse_mode="Markdown", reply_markup=kb_b)
                u2["main_msg_id"] = s2.message_id
                save_user(chat_id, u2)
            threading.Thread(target=del_noball, args=(uid, sent_err.message_id), daemon=True).start()
            return
        # Transfer amalga oshirish
        old_msg_id = u.pop("temp_msg_id", None)
        if old_msg_id:
            try: bot.delete_message(uid, old_msg_id)
            except: pass
        target_u              = load_user(target_id)
        u["points"]           = my_balls - amount
        target_u["points"]    = target_u.get("points", 0) + amount
        u["state"]            = None
        u.pop("bozor_transfer_to", None)
        save_user(uid, u)
        save_user(target_id, target_u)
        # Qabul qiluvchiga xabar
        try:
            bot.send_message(
                target_id,
                f"🎁 *{u.get('name','?')}* sizga *{amount} ball* yubordi!\n⭐ Sizning balingiz: *{target_u['points']} ball*",
                parse_mode="Markdown"
            )
        except: pass
        sent_ok = bot.send_message(
            uid,
            f"✅ *{amount} ball* muvaffaqiyatli yuborildi!\n⭐ Qolgan balingiz: *{u['points']} ball*",
            parse_mode="Markdown"
        )
        def del_tok(chat_id, mid):
            time.sleep(3)
            try: bot.delete_message(chat_id, mid)
            except: pass
        threading.Thread(target=del_tok, args=(uid, sent_ok.message_id), daemon=True).start()
        balls2 = u.get("points", 0)
        kb_b   = InlineKeyboardMarkup()
        kb_b.row(
            InlineKeyboardButton("💸 Ballarni ayirboshlash", callback_data="bozor_transfer"),
            InlineKeyboardButton("✏️ Ballarni tahrirlash",   callback_data="bozor_edit")
        )
        kb_b.add(InlineKeyboardButton(T(uid, "btn_home"), callback_data="menu_main"))
        sent2 = bot.send_message(uid, f"🛒 *Bozor*\n\n⭐ Sizning balingiz: *{balls2} ball*", parse_mode="Markdown", reply_markup=kb_b)
        u2 = load_user(uid)
        u2["main_msg_id"] = sent2.message_id
        save_user(uid, u2)
        return

    # --- Bozor: ballarni olib tashlash ---
    if state == "bozor_waiting_subtract":
        try: bot.delete_message(uid, msg.message_id)
        except: pass
        try:
            amount = int(text.strip())
            if amount <= 0: raise ValueError
        except ValueError:
            sent_err = bot.send_message(uid, "❌ Musbat son kiriting.", parse_mode="Markdown")
            def del_serr(chat_id, mid):
                time.sleep(3)
                try: bot.delete_message(chat_id, mid)
                except: pass
            threading.Thread(target=del_serr, args=(uid, sent_err.message_id), daemon=True).start()
            return
        my_balls = u.get("points", 0)
        old_msg_id = u.pop("temp_msg_id", None)
        if old_msg_id:
            try: bot.delete_message(uid, old_msg_id)
            except: pass
        new_balls   = max(0, my_balls - amount)
        u["points"] = new_balls
        u["state"]  = None
        save_user(uid, u)
        sent_ok = bot.send_message(
            uid,
            f"✅ *{min(amount, my_balls)} ball* olib tashlandi.\n⭐ Qolgan balingiz: *{new_balls} ball*",
            parse_mode="Markdown"
        )
        def del_sok(chat_id, mid):
            time.sleep(2)
            try: bot.delete_message(chat_id, mid)
            except: pass
        threading.Thread(target=del_sok, args=(uid, sent_ok.message_id), daemon=True).start()
        kb_b2  = InlineKeyboardMarkup()
        kb_b2.add(InlineKeyboardButton("💸 Ballarni ayirboshlash", callback_data="bozor_transfer"))
        kb_b2.row(
            InlineKeyboardButton("🔴 Ballarimni 0 ga tushirish", callback_data="bozor_reset_confirm"),
            InlineKeyboardButton("➖ Ballarimdan olib tashlash",  callback_data="bozor_subtract")
        )
        kb_b2.add(InlineKeyboardButton(T(uid, "btn_home"), callback_data="menu_main"))
        sent2 = bot.send_message(
            uid,
            f"🛒 *Bozor — bu sizning ballaringiz bilan qilinadigan barcha ammalar joyi.*\n\n⭐ Sizning balingiz: *{new_balls} ball*\n\n"
            "💸 *Ballarni ayirboshlash* — yaqin insoniga ball yuborish\n"
            "🔴 *Ballarimni 0 ga tushirish* — barcha ballarni nollash\n"
            "➖ *Ballarimdan olib tashlash* — ma'lum miqdorni ayirish",
            parse_mode="Markdown", reply_markup=kb_b2
        )
        u2 = load_user(uid)
        u2["main_msg_id"] = sent2.message_id
        save_user(uid, u2)
        return

    if state == "updating_name":
        new_name = text.strip()
        try:
            bot.delete_message(uid, msg.message_id)
        except Exception:
            pass
        info_msg_id = u.pop("info_msg_id", None)
        if info_msg_id:
            try:
                bot.delete_message(uid, info_msg_id)
            except Exception:
                pass
        u["name"]  = new_name
        u["state"] = None
        save_user(uid, u)
        # Sozlamalar menyusiga qaytish
        kb_set = InlineKeyboardMarkup()
        kb_set.add(InlineKeyboardButton(T(uid, "btn_change_lang"), callback_data="settings_lang"))
        kb_set.add(InlineKeyboardButton(T(uid, "btn_change_info"), callback_data="settings_info"))
        kb_set.add(InlineKeyboardButton(T(uid, "btn_home"),        callback_data="menu_main"))
        sent = bot.send_message(uid, T(uid, "settings_title"), parse_mode="Markdown", reply_markup=kb_set)
        u["main_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    # Noaniq habar
    try:
        bot.delete_message(uid, msg.message_id)
    except Exception:
        pass
    old_main = u.get("main_msg_id")
    if old_main:
        try:
            bot.delete_message(uid, old_main)
        except Exception:
            pass
    sent_warn = bot.send_message(uid, T(uid, "invalid_msg"))
    def delete_warn_and_menu(chat_id, message_id):
        time.sleep(3)
        try:
            bot.delete_message(chat_id, message_id)
        except Exception:
            pass
        send_main_menu(chat_id)
    threading.Thread(target=delete_warn_and_menu, args=(uid, sent_warn.message_id), daemon=True).start()

# ============================================================
#  ODATLAR RO'YXATI
# ============================================================
def show_habits(uid):
    u      = load_user(uid)
    habits = u.get("habits", [])
    if not habits:
        send_main_menu(uid, "📭 Hali odat qo'shilmagan.\n\n➕ Odat qo'shish tugmasini bosing!")
        return
    text = "📋 *Sizning odatlaringiz:*\n\n"
    for h in habits:
        streak = h.get("streak", 0)
        fire   = "🔥" if streak > 0 else "⚪"
        text  += f"{fire} *{h['name']}*\n"
        text  += f"   ⏰ {h['time']}  |  🔥 {streak} kunlik streak\n\n"
    sent = bot.send_message(uid, text, parse_mode="Markdown", reply_markup=main_menu(uid))
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
        streak       = h.get("streak", 0)
        total        = h.get("total_done", 0)
        last         = h.get("last_done", "—")
        habit_points = total * 5
        if streak >= 30:   medal = "🥇"
        elif streak >= 14: medal = "🥈"
        elif streak >= 7:  medal = "🥉"
        else:              medal = "🌱"
        text += f"{medal} *{h['name']}*\n"
        text += "   " + T(uid, "stats_time",   time=h.get("time","—")) + "\n"
        text += "   " + T(uid, "stats_streak", streak=streak) + "\n"
        text += "   " + T(uid, "stats_ball2",  ball=habit_points) + "\n"
        text += "   " + T(uid, "stats_done",   n=total) + "\n"
        text += "   " + T(uid, "stats_missed", n=h.get("total_missed",0)) + "\n"
        text += "   " + T(uid, "stats_last",   d=last) + "\n\n"

    kb_stats = InlineKeyboardMarkup()
    nav_row  = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(T(uid, "nav_prev", n=page-1), callback_data=f"stats_page_{page-1}"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton(T(uid, "nav_next", n=page+1), callback_data=f"stats_page_{page+1}"))
    if nav_row:
        kb_stats.row(*nav_row)
    kb_stats.add(InlineKeyboardButton(T(uid, "btn_home"), callback_data="menu_main"))
    sent = bot.send_message(uid, text, parse_mode="Markdown", reply_markup=kb_stats)
    u["main_msg_id"] = sent.message_id
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
            text += f"{medals[i]} {link} — {points} ball\n"
    else:
        text += T(uid, "rating_empty")
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(T(uid, "btn_home"), callback_data="menu_main"))
    u    = load_user(uid)
    sent = bot.send_message(uid, text, parse_mode="Markdown", reply_markup=kb, disable_web_page_preview=True)
    u["main_msg_id"] = sent.message_id
    save_user(uid, u)

# ============================================================
#  ODAT O'CHIRISH
# ============================================================
def delete_habit_menu(uid):
    u      = load_user(uid)
    habits = u.get("habits", [])
    if not habits:
        bot.send_message(uid, T(uid, "no_delete"), reply_markup=main_menu(uid))
        return
    kb = InlineKeyboardMarkup()
    for h in habits:
        kb.add(InlineKeyboardButton(f"🗑 {h['name']} ({h['time']})", callback_data=f"delete_{h['id']}"))
    kb.row(
        InlineKeyboardButton(T(uid, "btn_home"), callback_data="menu_main")
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
            kb_set.add(InlineKeyboardButton(T(uid, "btn_home"),        callback_data="menu_main"))
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
                sent_main = bot.send_message(uid, build_main_text(uid), parse_mode="Markdown", reply_markup=main_menu(uid))
                u["main_msg_id"] = sent_main.message_id
                save_user(uid, u)
            else:
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
        kb_set.add(InlineKeyboardButton(T(uid, "btn_change_lang"), callback_data="settings_lang"))
        kb_set.add(InlineKeyboardButton(T(uid, "btn_change_info"), callback_data="settings_info"))
        kb_set.add(InlineKeyboardButton("💬 Dasturchiga habar",    callback_data="settings_contact_dev"))
        kb_set.add(InlineKeyboardButton(T(uid, "btn_home"),        callback_data="menu_main"))
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
        kb_lang.add(InlineKeyboardButton(T(uid, "btn_home"), callback_data="menu_main"))
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
        kb_info.add(InlineKeyboardButton("✏️ Ismni o'zgartirish",            callback_data="change_name"))
        kb_info.add(InlineKeyboardButton("📱 Telefon raqamni o'zgartirish",  callback_data="change_phone"))
        kb_info.add(InlineKeyboardButton("⏰ Odatlar vaqtini tahrirlash",    callback_data="settings_habits_time"))
        kb_info.row(
            InlineKeyboardButton("⬅️ Orqaga",         callback_data="menu_settings"),
            InlineKeyboardButton(T(uid, "btn_home"),   callback_data="menu_main")
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
            kb_back.add(InlineKeyboardButton("⬅️ Orqaga", callback_data="settings_info"))
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
        kb_habits.row(
            InlineKeyboardButton("⬅️ Orqaga",        callback_data="settings_info"),
            InlineKeyboardButton(T(uid, "btn_home"),  callback_data="menu_main")
        )
        sent = bot.send_message(uid, "⏰ *Qaysi odatning vaqtini tahrirlash?*", parse_mode="Markdown", reply_markup=kb_habits)
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
            InlineKeyboardButton("⬅️ Orqaga",        callback_data="settings_info"),
            InlineKeyboardButton(T(uid, "btn_home"),  callback_data="menu_main")
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
            InlineKeyboardButton("⬅️ Orqaga",        callback_data="settings_habits_time"),
            InlineKeyboardButton(T(uid, "btn_home"), callback_data="menu_main")
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
        kb_back.add(InlineKeyboardButton(T(uid, "btn_home"),     callback_data="menu_main"))
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

    if cdata == "change_name":
        bot.answer_callback_query(call.id)
        bot.delete_message(uid, call.message.message_id)
        u["state"] = "updating_name"
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.add(InlineKeyboardButton(T(uid, "btn_cancel"), callback_data="menu_settings"))
        sent = bot.send_message(uid, "✏️ Yangi ismingizni yozing:", reply_markup=cancel_kb)
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
        if len(u.get("habits", [])) >= 15:
            bot.answer_callback_query(call.id)
            sent_limit = bot.send_message(uid, T(uid, "limit"))
            def del_limit(chat_id, msg_id):
                time.sleep(5)
                try:
                    bot.delete_message(chat_id, msg_id)
                except Exception:
                    pass
            threading.Thread(target=del_limit, args=(uid, sent_limit.message_id), daemon=True).start()
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
        sent = bot.send_message(uid, "📋 *Odat turini tanlang:*\n\n📌 *Oddiy* — kuniga 1 marta\n🔁 *Takrorlanuvchi* — kuniga bir necha marta (masalan: 5 vaqt namoz)", parse_mode="Markdown", reply_markup=kb_type)
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
            try:
                bot.delete_message(uid, old_msg_id)
            except Exception:
                pass
        send_main_menu(uid)
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
        kb_b  = InlineKeyboardMarkup()
        kb_b.add(InlineKeyboardButton("💸 Ballarni ayirboshlash", callback_data="bozor_transfer"))
        kb_b.row(
            InlineKeyboardButton("🔴 Ballarimni 0 ga tushirish", callback_data="bozor_reset_confirm"),
            InlineKeyboardButton("➖ Ballarimdan olib tashlash",  callback_data="bozor_subtract")
        )
        kb_b.add(InlineKeyboardButton(T(uid, "btn_home"), callback_data="menu_main"))
        sent = bot.send_message(
            uid,
            f"🛒 *Bozor — bu sizning ballaringiz bilan qilinadigan barcha ammalar joyi.*\n\n⭐ Sizning balingiz: *{balls} ball*\n\n"
            "💸 *Ballarni ayirboshlash* — yaqin insoniga ball yuborish\n"
            "🔴 *Ballarimni 0 ga tushirish* — barcha ballarni nollash\n"
            "➖ *Ballarimdan olib tashlash* — ma'lum miqdorni ayirish",
            parse_mode="Markdown", reply_markup=kb_b
        )
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
            InlineKeyboardButton("⬅️ Orqaga", callback_data="menu_bozor"),
            InlineKeyboardButton(T(uid, "btn_home"), callback_data="menu_main")
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
            InlineKeyboardButton("⬅️ Orqaga", callback_data="menu_bozor"),
            InlineKeyboardButton(T(uid, "btn_home"), callback_data="menu_main")
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
            InlineKeyboardButton("✅ Ha, 0 ga tushirish", callback_data="bozor_reset_do"),
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
        kb_b.add(InlineKeyboardButton("💸 Ballarni ayirboshlash", callback_data="bozor_transfer"))
        kb_b.row(
            InlineKeyboardButton("🔴 Ballarimni 0 ga tushirish", callback_data="bozor_reset_confirm"),
            InlineKeyboardButton("➖ Ballarimdan olib tashlash",  callback_data="bozor_subtract")
        )
        kb_b.add(InlineKeyboardButton(T(uid, "btn_home"), callback_data="menu_main"))
        sent2 = bot.send_message(
            uid,
            f"🛒 *Bozor — bu sizning ballaringiz bilan qilinadigan barcha ammalar joyi.*\n\n⭐ Sizning balingiz: *{balls} ball*\n\n"
            "💸 *Ballarni ayirboshlash* — yaqin insoniga ball yuborish\n"
            "🔴 *Ballarimni 0 ga tushirish* — barcha ballarni nollash\n"
            "➖ *Ballarimdan olib tashlash* — ma'lum miqdorni ayirish",
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
            InlineKeyboardButton("⬅️ Orqaga", callback_data="menu_bozor"),
            InlineKeyboardButton(T(uid, "btn_home"), callback_data="menu_main")
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
            InlineKeyboardButton(T(uid, "btn_yes"), callback_data=f"confirm_delete_{habit_id}"),
            InlineKeyboardButton(T(uid, "btn_no"),  callback_data="cancel_delete")
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
                        bot.edit_message_text(
                            build_main_text(uid), uid, main_msg_id,
                            parse_mode="Markdown", reply_markup=main_menu(uid)
                        )
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
                        bot.edit_message_text(
                            build_main_text(uid), uid, main_msg_id,
                            parse_mode="Markdown", reply_markup=main_menu(uid)
                        )
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
    # Takrorlanuvchi odatlarning done_today_count ni tozalash
    users = load_all_users()
    for uid, udata in users.items():
        changed = False
        for habit in udata.get("habits", []):
            if habit.get("type") == "repeat" and habit.get("done_today_count", 0) > 0:
                habit["done_today_count"] = 0
                habit["last_done"] = None
                changed = True
        if changed:
            try:
                mongo_col.update_one({"_id": uid}, {"$set": {"habits": udata["habits"]}})
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
    load_all_schedules()
    # Har kuni 00:00 (UTC+5 = 19:00 UTC) da reset
    schedule.every().day.at("19:00").do(daily_reset).tag("daily_reset")
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
