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
        "settings_title":    "⚙️ *Sozlamalar*",
        "btn_change_lang":   "🌐 Tilni o'zgartirish",
        "btn_change_info":   "📝 Ma'lumotlarni o'zgartirish",
        "change_info_text":  "📝 *Ma'lumotlarni o'zgartirish*\n\nNimani o'zgartirmoqchisiz?",
        "rating_no_link":    "username yo'q",
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
    },
}

MOTIVATSIYA = {
    "uz": ["💪 Har bir kun yangi imkoniyat!","🔥 Ketma-ketligingizni yo'qotmang!","🌟 Kichik qadamlar katta muvaffaqiyatga!","🚀 Siz qila olasiz!","🎯 Maqsadingizga bir qadam!"],
    "en": ["💪 Every day is a new opportunity!","🔥 Don't break the streak!","🌟 Small steps lead to big success!","🚀 You can do it!","🎯 One step closer to your goal!"],
    "ru": ["💪 Каждый день — новый шанс!","🔥 Не прерывай серию!","🌟 Маленькие шаги — большие победы!","🚀 Ты можешь это!","🎯 На шаг ближе к цели!"],
    "tr": ["💪 Her gün yeni bir fırsat!","🔥 Seriyi bozma!","🌟 Küçük adımlar büyük başarıya!","🚀 Yapabilirsin!","🎯 Hedefe bir adım daha!"],
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
        InlineKeyboardButton("🇺🇿 O'zbek",  callback_data="set_lang_uz"),
        InlineKeyboardButton("🇬🇧 English", callback_data="set_lang_en"),
    )
    kb.row(
        InlineKeyboardButton("🇷🇺 Русский", callback_data="set_lang_ru"),
        InlineKeyboardButton("🇹🇷 Türkçe",  callback_data="set_lang_tr"),
    )
    return kb

# ============================================================
#  MOTIVATSIYA (eski o'zgaruvchini o'chirish uchun placeholder)
# ============================================================

# ============================================================
#  BOT
# ============================================================
bot = telebot.TeleBot(BOT_TOKEN)

def main_menu(uid=None):
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
        for h in habits:
            done  = h.get("last_done") == today
            label = f"☑️ {h['name']}" if done else f"✅ {h['name']}"
            kb.add(InlineKeyboardButton(label, callback_data=f"toggle_{h['id']}"))
    kb.add(InlineKeyboardButton(T(uid, "btn_settings"), callback_data="menu_settings"))
    return kb

def done_keyboard(uid, habit_id):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(T(uid, "btn_done"), callback_data=f"done_{habit_id}"))
    return kb

def build_main_text(uid):
    u      = load_user(uid)
    habits = u.get("habits", [])
    if not habits:
        return T(uid, "no_habits")
    total_points = u.get("points", 0)
    text  = f"📊 *{T(uid, 'welcome_back').replace('📊 *', '').replace('*', '')}*\n"
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
    save_user(uid, u)


def check_subscription(user_id):
    settings = load_settings()
    channel  = settings.get("required_channel", None)
    if not channel:
        return True
    try:
        member = bot.get_chat_member(channel, user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        return True

def send_sub_required(uid):
    u        = load_user(uid)
    settings = load_settings()
    channel  = settings.get("required_channel", "")
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(T(uid, "btn_join"), url=f"https://t.me/{channel.lstrip('@')}"))
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
    kb.add(InlineKeyboardButton("🆕 Bot yangilandi xabari", callback_data="admin_notify_update"))
    kb.add(InlineKeyboardButton("❌ Bekor qilish", callback_data="admin_close"))
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
    u           = load_user(uid)
    main_msg_id = u.pop("main_msg_id", None)
    save_user(uid, u)
    if main_msg_id:
        try:
            bot.delete_message(uid, main_msg_id)
        except Exception:
            pass
    bot.send_message(uid, "🛠 *Admin panel*", parse_mode="Markdown", reply_markup=admin_menu())

# ============================================================
#  /start
# ============================================================
@bot.message_handler(commands=["start"])
def cmd_start(msg):
    uid  = msg.from_user.id
    name = msg.from_user.first_name

    def delete_old_messages(chat_id, before_id):
        for mid in range(before_id - 1, max(before_id - 50, 0), -1):
            try:
                bot.delete_message(chat_id, mid)
            except Exception:
                pass
    threading.Thread(target=delete_old_messages, args=(uid, msg.message_id), daemon=True).start()

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

    if not u.get("phone"):
        kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb.add(KeyboardButton("📱 Telefon raqamni yuborish", request_contact=True))
        sent = bot.send_message(
            uid,
            f"👋 Salom, *{name}*!\n\n"
            "🌱 *Odatlar Shakllantirish Boti*ga xush kelibsiz!\n\n"
            "Davom etish uchun ro'yxatdan o'ting — quyidagi tugma orqali telefon raqamingizni yuboring:",
            parse_mode="Markdown",
            reply_markup=kb
        )
        u["reg_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    if not check_subscription(uid):
        send_sub_required(uid)
        return

    # Til tanlamagan foydalanuvchiga — til tanlash
    if not u.get("lang"):
        sent_lang = bot.send_message(uid, "🌐 Tilni tanlang / Choose language / Выберите язык / Dil seçin:", reply_markup=lang_keyboard())
        u["lang_msg_id"] = sent_lang.message_id
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
        bot.send_message(uid, "✅", reply_markup=ReplyKeyboardRemove())
        # Sozlamalar menyusiga qaytish
        def back_to_settings(chat_id):
            time.sleep(1)
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
        threading.Thread(target=back_to_settings, args=(uid,), daemon=True).start()
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
        time.sleep(2)
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

    if state not in ("admin_bc_private", "admin_bc_groups", "admin_bc_all", "admin_waiting_channel") and uid != ADMIN_ID:
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
                failed_list.append(f"{udata.get('name','?')} ({target_uid}): {e}")
                print(f"[broadcast] xato: {target_uid} — {e}")
        u["state"] = None
        save_user(uid, u)
        result = f"✅ Habar {sent_count} ta foydalanuvchiga yuborildi."
        if failed > 0:
            result += f"\n❌ {failed} ta foydalanuvchiga yetmadi:"
            for fl in failed_list:
                result += f"\n  • {fl}"
        bot.send_message(uid, result)
        bot.send_message(uid, "🛠 *Admin panel*", parse_mode="Markdown", reply_markup=admin_menu())
        return

    # --- Kanal username ---
    if state == "admin_waiting_channel" and uid == ADMIN_ID:
        channel = text.strip()
        if not channel.startswith("@"):
            channel = "@" + channel
        # Foydalanuvchi yozgan xabarni o'chirish
        try:
            bot.delete_message(uid, msg.message_id)
        except Exception:
            pass
        # "Majburiy kanal" xabarini o'chirish
        channel_msg_id = u.pop("channel_msg_id", None)
        if channel_msg_id:
            try:
                bot.delete_message(uid, channel_msg_id)
            except Exception:
                pass
        try:
            chat     = bot.get_chat(channel)
            settings = load_settings()
            settings["required_channel"]       = channel
            settings["required_channel_title"] = chat.title
            save_settings(settings)
            u["state"] = None
            save_user(uid, u)
            # Tasdiq xabarini yuborib, 2 soniyadan so'ng o'chirish
            sent_confirm = bot.send_message(uid, f"✅ Majburiy kanal tasdiqlandi: *{chat.title}* (`{channel}`)", parse_mode="Markdown")
            def delete_confirm_and_menu(chat_id, message_id):
                time.sleep(2)
                try:
                    bot.delete_message(chat_id, message_id)
                except Exception:
                    pass
                send_main_menu(chat_id)
            threading.Thread(target=delete_confirm_and_menu, args=(uid, sent_confirm.message_id), daemon=True).start()
        except Exception as e:
            bot.send_message(uid, f"❌ Xatolik: `{e}`\n\nBot kanalga admin sifatida qo'shilganmi?\n\nQaytadan username yozing:", parse_mode="Markdown")
        return

    # --- Odat nomi ---
    if state == "waiting_habit_name":
        u["temp_habit"] = {"name": text}
        u["state"]      = "waiting_habit_time"
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
        sent = bot.send_message(uid, T(uid, "ask_habit_time", name=text), parse_mode="Markdown", reply_markup=cancel_kb)
        u["temp_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    # --- Vaqt ---
    if state == "waiting_habit_time":
        try:
            t        = datetime.strptime(text.strip(), "%H:%M")
            time_str = t.strftime("%H:%M")
            # 4. Xatolik xabarini o'chirish (agar oldin xato bo'lgan bo'lsa)
            err_msg_id = u.pop("time_err_msg_id", None)
            if err_msg_id:
                def del_err(chat_id, msg_id):
                    time.sleep(3)
                    try:
                        bot.delete_message(chat_id, msg_id)
                    except Exception:
                        pass
                threading.Thread(target=del_err, args=(uid, err_msg_id), daemon=True).start()
            habit = {
                "id":         str(int(time.time())),
                "name":       u["temp_habit"]["name"],
                "time":       time_str,
                "streak":     0,
                "total_done": 0,
                "last_done":  None,
                "created":    str(date.today()),
            }
            if "habits" not in u:
                u["habits"] = []
            u["habits"].append(habit)
            u["state"] = None
            u.pop("temp_habit", None)
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
            save_user(uid, u)
            schedule_habit(uid, habit)
            sent_main = bot.send_message(
                uid,
                T(uid, "habit_added", name=habit["name"], time=time_str),
                parse_mode="Markdown",
                reply_markup=main_menu(uid)
            )
            u["main_msg_id"] = sent_main.message_id
            save_user(uid, u)
        except ValueError:
            sent_err = bot.send_message(uid, T(uid, "wrong_time"), parse_mode="Markdown")
            u["time_err_msg_id"] = sent_err.message_id
            save_user(uid, u)
        return

    # --- Ismni yangilash ---
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
    kb = InlineKeyboardMarkup()
    if top10:
        for i, (name, points, username, target_uid) in enumerate(top10):
            text += f"{medals[i]} {name} — {points} ball\n"
            # Username bo'lsa — link tugmasi qo'shish
            uname = username.lstrip("@") if username and username != "—" else ""
            if uname:
                kb.add(InlineKeyboardButton(
                    f"{medals[i]} {name}",
                    url=f"https://t.me/{uname}"
                ))
    else:
        text += T(uid, "rating_empty")
    kb.add(InlineKeyboardButton(T(uid, "btn_home"), callback_data="menu_main"))
    u    = load_user(uid)
    sent = bot.send_message(uid, text, reply_markup=kb)
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
    kb.add(InlineKeyboardButton(T(uid, "btn_cancel"), callback_data="cancel"))
    bot.send_message(uid, "🗑", reply_markup=kb)

# ============================================================
#  CALLBACK HANDLER
# ============================================================
@bot.callback_query_handler(func=lambda c: True)
def callback_handler(call):
    uid   = call.from_user.id
    cdata = call.data
    u     = load_user(uid)

    # Eski tugma bosilsa — bot yangilanganini bildirish
    if not u.get("phone"):
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
            if u.get("habits"):
                sent_main = bot.send_message(uid, build_main_text(uid), parse_mode="Markdown", reply_markup=main_menu(uid))
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
        bot.send_message(uid, "🛠 *Admin panel*", parse_mode="Markdown", reply_markup=admin_menu())
        return

    if cdata == "admin_notify_update":
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
        bot.send_message(uid, result)
        bot.send_message(uid, "🛠 *Admin panel*", parse_mode="Markdown", reply_markup=admin_menu())
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

    if cdata == "admin_users":
        if uid != ADMIN_ID:
            return
        bot.answer_callback_query(call.id)
        bot.delete_message(uid, call.message.message_id)
        users = load_all_users()
        if not users:
            bot.send_message(uid, "👥 Foydalanuvchilar yo'q.", reply_markup=admin_menu())
            return
        kb      = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🔙 Admin panel", callback_data="admin_cancel"))
        parts   = []
        current = f"👥 Jami foydalanuvchilar: {len(users)} ta\n" + "▬" * 20 + "\n\n"
        for i, (target_uid, udata) in enumerate(users.items(), 1):
            name     = udata.get("name", "—")
            username = udata.get("username", "—")
            if username and username != "—" and not username.startswith("@"):
                username = "@" + username
            phone  = udata.get("phone", "Kiritilmagan")
            joined = udata.get("joined_at", "—")
            habits = udata.get("habits", [])
            block  = f"👤 {i}. {name}\n"
            block += f"  🆔 ID: {target_uid}\n"
            block += f"  📌 Username: {username}\n"
            block += f"  📞 Tel: {phone}\n"
            block += f"  📅 Qo'shilgan: {joined}\n"
            if habits:
                block += f"  📋 Odatlar ({len(habits)} ta):\n"
                for h in habits:
                    block += f"    • {h['name']} | {h['time']} | streak: {h.get('streak',0)} kun | jami: {h.get('total_done',0)}\n"
            else:
                block += "  📋 Odatlar: yo'q\n"
            block += "\n"
            if len(current) + len(block) > 3800:
                parts.append(current)
                current = block
            else:
                current += block
        if current:
            parts.append(current)
        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                bot.send_message(uid, part, reply_markup=kb)
            else:
                bot.send_message(uid, part)
        return

    if cdata == "admin_channel":
        if uid != ADMIN_ID:
            return
        bot.answer_callback_query(call.id)
        bot.delete_message(uid, call.message.message_id)
        settings = load_settings()
        current  = settings.get("required_channel", None)
        kb2 = InlineKeyboardMarkup()
        if current:
            kb2.add(InlineKeyboardButton("🗑 Kanalni o'chirish", callback_data="admin_channel_remove"))
        kb2.add(InlineKeyboardButton("❌ Bekor qilish", callback_data="admin_cancel"))
        msg_text = "🔗 Majburiy kanal\n\n"
        if current:
            title     = settings.get("required_channel_title", current)
            msg_text += f"Hozirgi kanal: {title} ({current})\n\nO'zgartirish uchun yangi kanal username yozing:"
        else:
            msg_text += "Hozircha majburiy kanal yo'q.\n\nKanal username yozing (Masalan: @mening_kanalim):"
        u["state"] = "admin_waiting_channel"
        sent_ch = bot.send_message(uid, msg_text, reply_markup=kb2)
        u["channel_msg_id"] = sent_ch.message_id
        save_user(uid, u)
        return

    if cdata == "admin_channel_remove":
        if uid != ADMIN_ID:
            return
        bot.answer_callback_query(call.id)
        bot.delete_message(uid, call.message.message_id)
        settings = load_settings()
        settings.pop("required_channel", None)
        settings.pop("required_channel_title", None)
        save_settings(settings)
        bot.send_message(uid, "✅ Majburiy kanal o'chirildi.", reply_markup=admin_menu())
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

    if cdata == "settings_info":
        bot.answer_callback_query(call.id)
        bot.delete_message(uid, call.message.message_id)
        kb_info = InlineKeyboardMarkup()
        kb_info.add(InlineKeyboardButton("✏️ Ismni o'zgartirish",       callback_data="change_name"))
        kb_info.add(InlineKeyboardButton("📱 Telefon raqamni o'zgartirish", callback_data="change_phone"))
        kb_info.row(
            InlineKeyboardButton("⬅️ Orqaga",         callback_data="menu_settings"),
            InlineKeyboardButton(T(uid, "btn_home"),   callback_data="menu_main")
        )
        sent = bot.send_message(uid, T(uid, "change_info_text"), parse_mode="Markdown", reply_markup=kb_info)
        u["main_msg_id"] = sent.message_id
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
        sent = bot.send_message(uid, "📱 Yangi telefon raqamingizni yuboring:", reply_markup=kb_phone)
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
        u["state"] = "waiting_habit_name"
        bot.answer_callback_query(call.id)
        bot.delete_message(uid, call.message.message_id)
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
            send_main_menu(chat_id)
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
                if h.get("last_done") == today:
                    # Bekor qilish — bildirishnomani qayta yoqish
                    h["last_done"]  = None
                    h["streak"]     = max(0, h.get("streak", 0) - 1)
                    h["total_done"] = max(0, h.get("total_done", 0) - 1)
                    u["points"]     = max(0, u.get("points", 0) - 5)
                    save_user(uid, u)
                    # Eslatmani qayta yoqish
                    schedule_habit(uid, h)
                    bot.answer_callback_query(call.id)
                    sent_msg = bot.send_message(uid, T(uid, "undone", name=h["name"]), parse_mode="Markdown")
                    def del_msg1(chat_id, msg_id):
                        time.sleep(3)
                        try: bot.delete_message(chat_id, msg_id)
                        except: pass
                    threading.Thread(target=del_msg1, args=(uid, sent_msg.message_id), daemon=True).start()
                else:
                    # Bajarildi — bildirishnomani bugunlik to'xtatish
                    h["streak"] = h.get("streak", 0) + 1 if h.get("last_done") == yesterday else 1
                    h["last_done"]  = today
                    h["total_done"] = h.get("total_done", 0) + 1
                    u["points"]     = u.get("points", 0) + 5
                    save_user(uid, u)
                    # Faqat bugunlik to'xtatish (ertaga daily_reset qayta yuklaydi)
                    unschedule_habit_today(uid, habit_id)
                    bot.answer_callback_query(call.id)
                    sent_msg = bot.send_message(uid, T(uid, "done_ok", name=h["name"]), parse_mode="Markdown")
                    def del_msg2(chat_id, msg_id):
                        time.sleep(3)
                        try: bot.delete_message(chat_id, msg_id)
                        except: pass
                    threading.Thread(target=del_msg2, args=(uid, sent_msg.message_id), daemon=True).start()
                    # Barcha odat bajarildi?
                    all_done = all(hh.get("last_done") == today for hh in u.get("habits", []))
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
                if streak >= 30:   msg_extra = "🏆"
                elif streak >= 14: msg_extra = "🌟"
                elif streak == 7:  msg_extra = "🔥"
                else:              msg_extra = f"💪 {streak}"
                bot.edit_message_text(
                    f"{T(uid, 'done_ok', name=h['name'])}\n\n{msg_extra}",
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
