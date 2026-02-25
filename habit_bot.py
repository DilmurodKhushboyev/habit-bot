#!/usr/bin/env python3
"""
Odatlar Shakllantirish Boti
============================
O'rnatish:
    pip install pyTelegramBotAPI schedule

Ishga tushurish:
    python habit_bot.py
"""

import telebot
import json
import os
import schedule
import time
import threading
from datetime import datetime, date
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# ============================================================
#  SOZLAMALAR — TOKEN NI SHU YERGA QOYING
# ============================================================
import os
BOT_TOKEN = os.environ.get("BOT_TOKEN", "SHU_YERGA_TOKEN_QOYING")

# ============================================================
#  MA'LUMOTLAR (data.json da saqlanadi)
# ============================================================
DATA_FILE = "habit_data.json"

MOTIVATSIYA = [
    "💪 Har bir kun yangi imkoniyat! Odatingizni bajaring!",
    "🔥 Ketma-ketligingizni yo'qotmang, bugun ham bajaring!",
    "🌟 Kichik qadamlar katta muvaffaqiyatga olib boradi!",
    "🚀 Siz qila olasiz! Hoziroq boshlang!",
    "⚡ Odatlar taqdirni shakllantiradi. Bugun bajaring!",
    "🎯 Maqsadingizga bir qadam yaqinlashing!",
    "🌱 Har kuni o'sish — bu g'alaba!",
    "✨ Bugungi harakat ertangi natijani belgilaydi!",
]

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user(data, user_id):
    uid = str(user_id)
    if uid not in data:
        data[uid] = {"habits": [], "state": None}
    return data[uid]

# ============================================================
#  BOT
# ============================================================
bot = telebot.TeleBot(BOT_TOKEN)
data = load_data()

# --- Asosiy menyu ---
def main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton("➕ Odat qo'shish"), KeyboardButton("📋 Odatlarim"))
    kb.row(KeyboardButton("📊 Statistika"), KeyboardButton("🗑 Odat o'chirish"))
    return kb

# --- Inline bajarildi tugmasi ---
def done_keyboard(habit_id):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("✅ Bajardim!", callback_data=f"done_{habit_id}"))
    return kb

# ============================================================
#  HANDLERLAR
# ============================================================

@bot.message_handler(commands=["start"])
def cmd_start(msg):
    uid = msg.from_user.id
    name = msg.from_user.first_name
    d = load_data()
    get_user(d, uid)
    save_data(d)

    bot.send_message(
        uid,
        f"👋 Salom, *{name}*!\n\n"
        "🌱 *Odatlar Shakllantirish Boti*ga xush kelibsiz!\n\n"
        "Bu bot sizga:\n"
        "• Odatlarni belgilash\n"
        "• Vaqtida eslatma olish\n"
        "• Streak va statistika kuzatish\n"
        "imkonini beradi.\n\n"
        "Boshlash uchun *➕ Odat qo'shish* tugmasini bosing!",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )

# --- Odat qo'shish ---
@bot.message_handler(func=lambda m: m.text == "➕ Odat qo'shish")
def add_habit_start(msg):
    uid = msg.from_user.id
    d = load_data()
    u = get_user(d, uid)
    u["state"] = "waiting_habit_name"
    save_data(d)
    bot.send_message(uid, "📝 Odatning nomini yozing:\n\n_Masalan: Kitob o'qish, Sport, Suv ichish..._", parse_mode="Markdown")

@bot.message_handler(func=lambda m: True)
def handle_text(msg):
    uid = msg.from_user.id
    text = msg.text
    d = load_data()
    u = get_user(d, uid)
    state = u.get("state")

    # --- Odat nomi ---
    if state == "waiting_habit_name":
        u["temp_habit"] = {"name": text}
        u["state"] = "waiting_habit_time"
        save_data(d)
        bot.send_message(
            uid,
            f"✅ Odat: *{text}*\n\n"
            "⏰ Eslatma vaqtini yozing (24 soat formatida):\n\n"
            "_Masalan: 07:30 yoki 21:00_",
            parse_mode="Markdown"
        )
        return

    # --- Vaqt ---
    if state == "waiting_habit_time":
        try:
            t = datetime.strptime(text.strip(), "%H:%M")
            time_str = t.strftime("%H:%M")
            habit = {
                "id": str(int(time.time())),
                "name": u["temp_habit"]["name"],
                "time": time_str,
                "streak": 0,
                "total_done": 0,
                "last_done": None,
                "created": str(date.today()),
            }
            if "habits" not in u:
                u["habits"] = []
            u["habits"].append(habit)
            u["state"] = None
            u.pop("temp_habit", None)
            save_data(d)

            # Eslatmani rejalashtirish
            schedule_habit(uid, habit)

            bot.send_message(
                uid,
                f"🎉 *{habit['name']}* odati qo'shildi!\n\n"
                f"⏰ Eslatma: *{time_str}* da keladi\n"
                f"🔥 Streak: 0 kun\n\n"
                "Har kuni vaqtida bajaring va streak'ingizni o'stirib boring!",
                parse_mode="Markdown",
                reply_markup=main_menu()
            )
        except ValueError:
            bot.send_message(uid, "❌ Noto'g'ri format. Iltimos HH:MM formatida yozing.\n_Masalan: 08:00_", parse_mode="Markdown")
        return

    # --- Odatlar ro'yxati ---
    if text == "📋 Odatlarim":
        show_habits(msg)
        return

    # --- Statistika ---
    if text == "📊 Statistika":
        show_stats(msg)
        return

    # --- O'chirish ---
    if text == "🗑 Odat o'chirish":
        delete_habit_menu(msg)
        return

    bot.send_message(uid, "Pastdagi tugmalardan foydalaning 👇", reply_markup=main_menu())

# --- Odatlar ro'yxati ---
def show_habits(msg):
    uid = msg.from_user.id
    d = load_data()
    u = get_user(d, uid)
    habits = u.get("habits", [])

    if not habits:
        bot.send_message(uid, "📭 Hali odat qo'shilmagan.\n\n➕ Odat qo'shish tugmasini bosing!", reply_markup=main_menu())
        return

    text = "📋 *Sizning odatlaringiz:*\n\n"
    for h in habits:
        streak = h.get("streak", 0)
        fire = "🔥" if streak > 0 else "⚪"
        text += f"{fire} *{h['name']}*\n"
        text += f"   ⏰ {h['time']}  |  🔥 {streak} kunlik streak\n\n"

    bot.send_message(uid, text, parse_mode="Markdown", reply_markup=main_menu())

# --- Statistika ---
def show_stats(msg):
    uid = msg.from_user.id
    d = load_data()
    u = get_user(d, uid)
    habits = u.get("habits", [])

    if not habits:
        bot.send_message(uid, "📭 Hali odat yo'q.", reply_markup=main_menu())
        return

    text = "📊 *Statistika:*\n\n"
    for h in habits:
        streak = h.get("streak", 0)
        total = h.get("total_done", 0)
        last = h.get("last_done", "Hali bajarilmagan")

        if streak >= 30:
            medal = "🥇"
        elif streak >= 14:
            medal = "🥈"
        elif streak >= 7:
            medal = "🥉"
        else:
            medal = "🌱"

        text += f"{medal} *{h['name']}*\n"
        text += f"   🔥 Streak: {streak} kun\n"
        text += f"   ✅ Jami bajarilgan: {total} marta\n"
        text += f"   📅 Oxirgi: {last}\n\n"

    bot.send_message(uid, text, parse_mode="Markdown", reply_markup=main_menu())

# --- O'chirish menyusi ---
def delete_habit_menu(msg):
    uid = msg.from_user.id
    d = load_data()
    u = get_user(d, uid)
    habits = u.get("habits", [])

    if not habits:
        bot.send_message(uid, "📭 O'chirish uchun odat yo'q.", reply_markup=main_menu())
        return

    kb = InlineKeyboardMarkup()
    for h in habits:
        kb.add(InlineKeyboardButton(f"🗑 {h['name']} ({h['time']})", callback_data=f"delete_{h['id']}"))

    bot.send_message(uid, "Qaysi odatni o'chirmoqchisiz?", reply_markup=kb)

# --- Callback (Bajardim / O'chirish) ---
@bot.callback_query_handler(func=lambda c: True)
def callback_handler(call):
    uid = call.from_user.id
    cdata = call.data
    d = load_data()
    u = get_user(d, uid)

    # Bajardim
    if cdata.startswith("done_"):
        habit_id = cdata[5:]
        today = str(date.today())
        for h in u.get("habits", []):
            if h["id"] == habit_id:
                if h.get("last_done") == today:
                    bot.answer_callback_query(call.id, "✅ Bugun allaqachon bajardingiz!")
                    return
                # Streak hisoblash
                yesterday = str(date.fromordinal(date.today().toordinal() - 1))
                if h.get("last_done") == yesterday:
                    h["streak"] = h.get("streak", 0) + 1
                else:
                    h["streak"] = 1
                h["last_done"] = today
                h["total_done"] = h.get("total_done", 0) + 1
                save_data(d)

                streak = h["streak"]
                if streak >= 30:
                    msg_extra = "🏆 30 kunlik streak! Siz ajoyibsiz!"
                elif streak >= 14:
                    msg_extra = "🌟 2 haftalik streak! Davom eting!"
                elif streak == 7:
                    msg_extra = "🔥 1 haftalik streak! Zo'r!"
                else:
                    msg_extra = f"💪 {streak} kunlik streak!"

                bot.edit_message_text(
                    f"✅ *{h['name']}* — bajarildi!\n\n{msg_extra}",
                    uid, call.message.message_id,
                    parse_mode="Markdown"
                )
                bot.answer_callback_query(call.id, "✅ Barakalla!")
                return

    # O'chirish
    if cdata.startswith("delete_"):
        habit_id = cdata[7:]
        habits = u.get("habits", [])
        habit_name = ""
        for h in habits:
            if h["id"] == habit_id:
                habit_name = h["name"]
                break
        u["habits"] = [h for h in habits if h["id"] != habit_id]
        save_data(d)
        bot.edit_message_text(f"🗑 *{habit_name}* o'chirildi.", uid, call.message.message_id, parse_mode="Markdown")
        bot.answer_callback_query(call.id, "O'chirildi")

# ============================================================
#  ESLATMA YUBORISH
# ============================================================
def send_reminder(user_id, habit):
    import random
    motivatsiya = random.choice(MOTIVATSIYA)
    d = load_data()
    u = get_user(d, str(user_id))
    # Habit hali borligini tekshirish
    exists = any(h["id"] == habit["id"] for h in u.get("habits", []))
    if not exists:
        return
    try:
        bot.send_message(
            user_id,
            f"⏰ *Eslatma!*\n\n"
            f"🎯 Odat: *{habit['name']}*\n\n"
            f"{motivatsiya}",
            parse_mode="Markdown",
            reply_markup=done_keyboard(habit["id"])
        )
    except Exception as e:
        print(f"Xatolik: {e}")

def schedule_habit(user_id, habit):
    t = habit["time"]
    schedule.every().day.at(t).do(send_reminder, user_id=user_id, habit=habit).tag(f"{user_id}_{habit['id']}")
    print(f"Rejalashtirildi: {habit['name']} — {t}")

def load_all_schedules():
    d = load_data()
    for uid, udata in d.items():
        for habit in udata.get("habits", []):
            schedule_habit(int(uid), habit)

def scheduler_loop():
    load_all_schedules()
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

    # Scheduler alohida threadda
    t = threading.Thread(target=scheduler_loop, daemon=True)
    t.start()

    print("Bot tayyor! Telegramdan /start yuboring.")
    bot.infinity_polling()
