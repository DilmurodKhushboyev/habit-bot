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
#  MOTIVATSIYA
# ============================================================
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

# ============================================================
#  BOT
# ============================================================
bot = telebot.TeleBot(BOT_TOKEN)

def main_menu():
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("➕ Odat qo'shish", callback_data="menu_add"),
        InlineKeyboardButton("📋 Odatlarim",     callback_data="menu_list")
    )
    kb.row(
        InlineKeyboardButton("📊 Statistika",    callback_data="menu_stats"),
        InlineKeyboardButton("🗑 Odat o'chirish", callback_data="menu_delete")
    )
    kb.row(
        InlineKeyboardButton("🏆 Reyiting", callback_data="menu_rating")
    )
    return kb

def done_keyboard(habit_id):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("✅ Bajardim!", callback_data=f"done_{habit_id}"))
    return kb

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
    kb.add(InlineKeyboardButton("📢 Kanalga o'tish", url=f"https://t.me/{channel.lstrip('@')}"))
    kb.add(InlineKeyboardButton("✅ A'zo bo'ldim", callback_data="check_sub"))
    old_msg_id = u.get("sub_msg_id")
    if old_msg_id:
        try:
            bot.delete_message(uid, old_msg_id)
        except Exception:
            pass
    sent = bot.send_message(uid, "⚠️ Botdan foydalanish uchun avvalo kanalga a'zo bo'ling!", reply_markup=kb)
    u["sub_msg_id"] = sent.message_id
    save_user(uid, u)

def send_main_menu(uid, text="Quyidagi tugmalardan foydalaning 👇"):
    u    = load_user(uid)
    sent = bot.send_message(uid, text, reply_markup=main_menu())
    u["main_msg_id"] = sent.message_id
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
        # /start xabarining o'zini ham o'chirish
        try:
            bot.delete_message(chat_id, before_id)
        except Exception:
            pass
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

    sent_main = bot.send_message(
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
        bot.send_message(uid, "⚠️ Botdan foydalanish uchun avvalo kanalga a'zo bo'ling!", reply_markup=ReplyKeyboardRemove())
        send_sub_required(uid)
        return
    sent_reg = bot.send_message(
        uid,
        f"✅ Ro'yxatdan o'tdingiz, *{name}*!\n\n"
        "Boshlash uchun *➕ Odat qo'shish* tugmasini bosing!",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    # Tasdiq xabarini 2 soniyadan so'ng o'chirish
    def delete_reg_confirm(chat_id, message_id):
        time.sleep(2)
        try:
            bot.delete_message(chat_id, message_id)
        except Exception:
            pass
    threading.Thread(target=delete_reg_confirm, args=(uid, sent_reg.message_id), daemon=True).start()
    send_main_menu(uid)

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
                bot.send_message(int(target_uid), text)
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
        cancel_kb.add(InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel"))
        sent = bot.send_message(
            uid,
            f"✅ Odat: *{text}*\n\n"
            "⏰ Eslatma vaqtini yozing (24 soat formatida):\n\n"
            "_Masalan: 07:30 yoki 21:00_",
            parse_mode="Markdown",
            reply_markup=cancel_kb
        )
        u["temp_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    # --- Vaqt ---
    if state == "waiting_habit_time":
        try:
            t        = datetime.strptime(text.strip(), "%H:%M")
            time_str = t.strftime("%H:%M")
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
                f"🎉 *{habit['name']}* odati qo'shildi!\n\n"
                f"⏰ Eslatma: *{time_str}* da keladi\n"
                f"🔥 Streak: 0 kun\n\n"
                "Har kuni vaqtida bajaring va streak'ingizni o'stirib boring!",
                parse_mode="Markdown",
                reply_markup=main_menu()
            )
            u["main_msg_id"] = sent_main.message_id
            save_user(uid, u)
        except ValueError:
            bot.send_message(uid, "❌ Noto'g'ri format. Iltimos HH:MM formatida yozing.\n_Masalan: 08:00_", parse_mode="Markdown")
        return

    # Noaniq habar — o'chirib, xabar yuborish
    try:
        bot.delete_message(uid, msg.message_id)
    except Exception:
        pass
    # Oldingi asosiy menyu xabarini ham o'chirish
    old_main = u.get("main_msg_id")
    if old_main:
        try:
            bot.delete_message(uid, old_main)
        except Exception:
            pass
    sent_warn = bot.send_message(uid, "⚠️ Sizning noaniq habarlaringiz qo'llab quvvatlanmaydi.")
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
    sent = bot.send_message(uid, text, parse_mode="Markdown", reply_markup=main_menu())
    u["main_msg_id"] = sent.message_id
    save_user(uid, u)

# ============================================================
#  STATISTIKA
# ============================================================
def show_stats(uid):
    u      = load_user(uid)
    habits = u.get("habits", [])
    if not habits:
        send_main_menu(uid, "📭 Hali odat yo'q.")
        return
    total_points = u.get("points", 0)
    if total_points >= 500:
        rank = "🏆 Legenda"
    elif total_points >= 200:
        rank = "💎 Master"
    elif total_points >= 100:
        rank = "🥇 Professional"
    elif total_points >= 50:
        rank = "🥈 Tajribali"
    elif total_points >= 20:
        rank = "🥉 Boshlang'ich"
    else:
        rank = "🌱 Yangi boshlovchi"
    text  = "📊 *Statistika*\n"
    text += "▬" * 16 + "\n"
    text += f"⭐ *Jami ball: {total_points} ball*\n"
    text += f"🎖 Daraja: {rank}\n"
    text += "▬" * 16 + "\n\n"
    for h in habits:
        streak       = h.get("streak", 0)
        total        = h.get("total_done", 0)
        last         = h.get("last_done", "Hali bajarilmagan")
        habit_points = total * 5
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
        text += f"   ❌ Jami bajarilmagan: {h.get('total_missed', 0)} marta\n"
        text += f"   ⭐ Odat balli: {habit_points} ball\n"
        text += f"   📅 Oxirgi: {last}\n\n"
    sent = bot.send_message(uid, text, parse_mode="Markdown", reply_markup=main_menu())
    u["main_msg_id"] = sent.message_id
    save_user(uid, u)

# ============================================================
#  REYITING
# ============================================================
def show_rating(uid):
    users   = load_all_users()
    ranking = []
    for user_id, udata in users.items():
        ranking.append((udata.get("name", "Noma'lum"), udata.get("points", 0)))
    ranking.sort(key=lambda x: x[1], reverse=True)
    top10  = ranking[:10]
    medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    text   = "🏆 Top 10 Reyiting\n" + "▬" * 16 + "\n\n"
    if top10:
        for i, (name, points) in enumerate(top10):
            text += f"{medals[i]} {name} — {points} ball\n"
    else:
        text += "Hali hech kim ball to'plamagan."
    u    = load_user(uid)
    sent = bot.send_message(uid, text, reply_markup=main_menu())
    u["main_msg_id"] = sent.message_id
    save_user(uid, u)

# ============================================================
#  ODAT O'CHIRISH
# ============================================================
def delete_habit_menu(uid):
    u      = load_user(uid)
    habits = u.get("habits", [])
    if not habits:
        bot.send_message(uid, "📭 O'chirish uchun odat yo'q.", reply_markup=main_menu())
        return
    kb = InlineKeyboardMarkup()
    for h in habits:
        kb.add(InlineKeyboardButton(f"🗑 {h['name']} ({h['time']})", callback_data=f"delete_{h['id']}"))
    kb.add(InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel"))
    bot.send_message(uid, "Qaysi odatni o'chirmoqchisiz?", reply_markup=kb)

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

    if cdata not in ("check_sub", "admin_cancel", "admin_close") and not cdata.startswith("admin_"):
        if not check_subscription(uid):
            bot.answer_callback_query(call.id)
            send_sub_required(uid)
            return

    if cdata == "check_sub":
        if check_subscription(uid):
            bot.answer_callback_query(call.id, "✅ Tasdiqlandi!")
            bot.delete_message(uid, call.message.message_id)
            u.pop("sub_msg_id", None)
            save_user(uid, u)
            name      = call.from_user.first_name
            sent_main = bot.send_message(
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
            u["main_msg_id"] = sent_main.message_id
            save_user(uid, u)
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

    if cdata == "menu_add":
        u["state"] = "waiting_habit_name"
        bot.answer_callback_query(call.id)
        bot.delete_message(uid, call.message.message_id)
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.add(InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel"))
        sent = bot.send_message(
            uid,
            "📝 Odatning nomini yozing:\n\n_Masalan: Kitob o'qish, Sport, Suv ichish..._",
            parse_mode="Markdown",
            reply_markup=cancel_kb
        )
        u["temp_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    if cdata == "cancel":
        u["state"] = None
        u.pop("temp_habit", None)
        old_msg_id = u.pop("temp_msg_id", None)
        save_user(uid, u)
        bot.answer_callback_query(call.id, "Bekor qilindi")
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

    if cdata.startswith("done_"):
        habit_id = cdata[5:]
        today    = str(date.today())
        u        = load_user(uid)
        for h in u.get("habits", []):
            if h["id"] == habit_id:
                if h.get("last_done") == today:
                    bot.answer_callback_query(call.id, "✅ Bugun allaqachon bajardingiz!")
                    return
                yesterday   = str(date.fromordinal(date.today().toordinal() - 1))
                h["streak"] = h.get("streak", 0) + 1 if h.get("last_done") == yesterday else 1
                h["last_done"]  = today
                h["total_done"] = h.get("total_done", 0) + 1
                u["points"]     = u.get("points", 0) + 5
                save_user(uid, u)
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
                # Eslatma xabarini 3 soniyadan so'ng o'chirish
                def delete_reminder(chat_id, message_id):
                    time.sleep(3)
                    try:
                        bot.delete_message(chat_id, message_id)
                    except Exception:
                        pass
                threading.Thread(target=delete_reminder, args=(uid, call.message.message_id), daemon=True).start()
                return

    if cdata.startswith("delete_"):
        habit_id   = cdata[7:]
        u          = load_user(uid)
        habits     = u.get("habits", [])
        habit_name = next((h["name"] for h in habits if h["id"] == habit_id), "")
        if not habit_name:
            return
        # Tasdiqlash so'rash
        kb_confirm = InlineKeyboardMarkup()
        kb_confirm.row(
            InlineKeyboardButton("Ha ✅", callback_data=f"confirm_delete_{habit_id}"),
            InlineKeyboardButton("Yo'q ❌", callback_data="cancel_delete")
        )
        bot.answer_callback_query(call.id)
        bot.edit_message_text(
            f"⚠️ Haqiqatan ham *{habit_name}* odatini o'chirishni xohlaysizmi?",
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
        u["habits"] = [h for h in habits if h["id"] != habit_id]
        save_user(uid, u)
        bot.answer_callback_query(call.id)
        try:
            bot.delete_message(uid, call.message.message_id)
        except Exception:
            pass
        # O'chirilgandan so'ng odatlar ro'yxatiga qaytish
        delete_habit_menu(uid)
        return

    if cdata == "cancel_delete":
        bot.answer_callback_query(call.id, "Bekor qilindi")
        try:
            bot.delete_message(uid, call.message.message_id)
        except Exception:
            pass
        delete_habit_menu(uid)
        return

# ============================================================
#  ESLATMA
# ============================================================
def send_reminder(user_id, habit):
    u      = load_user(user_id)
    habits = u.get("habits", [])
    exists = False
    for h in habits:
        if h["id"] == habit["id"]:
            exists = True
            # Kecha bajarilganmi tekshirish — bajarilmagan bo'lsa missed++
            yesterday = str(date.fromordinal(date.today().toordinal() - 1))
            if h.get("last_done") != str(date.today()) and h.get("last_done") != yesterday and h.get("last_done") is not None:
                h["total_missed"] = h.get("total_missed", 0) + 1
            break
    if not exists:
        return
    save_user(user_id, u)
    try:
        bot.send_message(
            user_id,
            f"⏰ *Eslatma!*\n\n"
            f"🎯 Odat: *{habit['name']}*\n\n"
            f"{random.choice(MOTIVATSIYA)}",
            parse_mode="Markdown",
            reply_markup=done_keyboard(habit["id"])
        )
    except Exception as e:
        print(f"[reminder] xato: {e}")

def schedule_habit(user_id, habit):
    # Foydalanuvchi UTC+5 da vaqt kiritadi, Railway UTC da ishlaydi
    # Shuning uchun 5 soat ayiramiz
    try:
        h, m   = map(int, habit["time"].split(":"))
        total  = h * 60 + m - 5 * 60  # 5 soat ayirish
        total  = total % (24 * 60)     # 24 soat ichida qoldirish
        utc_h  = total // 60
        utc_m  = total % 60
        utc_time = f"{utc_h:02d}:{utc_m:02d}"
    except Exception:
        utc_time = habit["time"]

    schedule.every().day.at(utc_time).do(
        send_reminder, user_id=user_id, habit=habit
    ).tag(f"{user_id}_{habit['id']}")
    print(f"[schedule] {habit['name']} — {habit['time']} (UTC: {utc_time})")

def load_all_schedules():
    users = load_all_users()
    for uid, udata in users.items():
        try:
            user_id = int(uid)
        except ValueError:
            continue
        for habit in udata.get("habits", []):
            schedule_habit(user_id, habit)

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
