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
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from pymongo import MongoClient

# MongoDB ma'lumotlar bazasiga ulanish
MONGO_URL = os.environ.get('MONGO_URL')
if MONGO_URL:
    client = MongoClient(MONGO_URL, tlsAllowInvalidCertificates=True)

    db = client['habitbot_db']
    users_collection = db['users_data']
else:
    print("XATOLIK: MONGO_URL topilmadi!")
    

# ============================================================
#  SOZLAMALAR — TOKEN NI SHU YERGA QOYING
# ============================================================
import os
BOT_TOKEN = os.environ.get("BOT_TOKEN", "SHU_YERGA_TOKEN_QOYING")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 5071908808))  # Bot egasining Telegram ID si

# ============================================================
#  MA'LUMOTLAR (data.json da saqlanadi)
# ============================================================
if os.path.exists('/app/data'):
    DATA_FILE = "/app/data/habit_data.json"
else:
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
    if MONGO_URL:
        try:
            doc = users_collection.find_one({"_id": "all_bot_data"})
            if doc and "data" in doc:
                return doc["data"]
            return {}
        except Exception as e:
            print("Bazadan o'qishda xatolik:", e)
            return {}
    else:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

def save_data(data):
    if MONGO_URL:
        try:
            users_collection.update_one(
                {"_id": "all_bot_data"},
                {"$set": {"data": data}},
                upsert=True
            )
        except Exception as e:
            print("Bazaga saqlashda xatolik:", e)
    else:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    

def get_user(data, user_id):
    uid = str(user_id)
    if uid not in data:
        data[uid] = {"habits": [], "state": None, "joined_at": str(date.today())}
    if "joined_at" not in data[uid]:
        data[uid]["joined_at"] = str(date.today())
    return data[uid]

# ============================================================
#  BOT
# ============================================================
bot = telebot.TeleBot(BOT_TOKEN)
data = load_data()

# --- Asosiy menyu ---
def main_menu():
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("➕ Odat qo'shish", callback_data="menu_add"),
        InlineKeyboardButton("📋 Odatlarim", callback_data="menu_list")
    )
    kb.row(
        InlineKeyboardButton("📊 Statistika", callback_data="menu_stats"),
        InlineKeyboardButton("🗑 Odat o'chirish", callback_data="menu_delete")
    )
    kb.row(
        InlineKeyboardButton("🏆 Reyiting", callback_data="menu_rating")
    )
    return kb

# --- Inline bajarildi tugmasi ---
def done_keyboard(habit_id):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("✅ Bajardim!", callback_data=f"done_{habit_id}"))
    return kb

# --- Majburiy kanal tekshirish ---
def check_subscription(user_id):
    d = load_data()
    channel = d.get("_settings", {}).get("required_channel", None)
    if not channel:
        return True
    try:
        member = bot.get_chat_member(channel, user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        return True

# --- "A'zo bo'ling" xabarini yuborish (oldingi o'chirib) ---
def send_sub_required(uid):
    d = load_data()
    u = get_user(d, uid)
    channel = d.get("_settings", {}).get("required_channel", "")
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("📢 Kanalga o'tish", url=f"https://t.me/{channel.lstrip('@')}"))
    kb.add(InlineKeyboardButton("✅ A'zo bo'ldim", callback_data="check_sub"))
    # Oldingi "a'zo bo'ling" xabarini o'chirish
    old_msg_id = u.get("sub_msg_id")
    if old_msg_id:
        try:
            bot.delete_message(uid, old_msg_id)
        except Exception:
            pass
    sent = bot.send_message(uid, "⚠️ Botdan foydalanish uchun avvalo kanalga a'zo bo'ling!", reply_markup=kb)
    u["sub_msg_id"] = sent.message_id
    save_data(d)

# --- Asosiy menyuni yuborish va main_msg_id saqlash ---
def send_main_menu(uid, text="Quyidagi tugmalardan foydalaning 👇"):
    d = load_data()
    u = get_user(d, uid)
    sent = bot.send_message(uid, text, reply_markup=main_menu())
    u["main_msg_id"] = sent.message_id
    save_data(d)

# --- Admin panel menyusi ---
def admin_menu():
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("📢 Habar yuborish", callback_data="admin_broadcast"),
        InlineKeyboardButton("👥 Foydalanuvchilar", callback_data="admin_users")
    )
    kb.row(
        InlineKeyboardButton("🔗 Majburiy kanal", callback_data="admin_channel"),
        InlineKeyboardButton("📈 Statistika", callback_data="admin_stats")
    )
    kb.add(InlineKeyboardButton("❌ Bekor qilish", callback_data="admin_close"))
    return kb

# ============================================================
#  ADMIN HANDLERLAR
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
            time.sleep(2)
            try:
                bot.delete_message(uid, sent.message_id)
            except Exception:
                pass
        threading.Thread(target=send_and_delete, daemon=True).start()
        return
    d = load_data()
    u = get_user(d, uid)
    main_msg_id = u.pop("main_msg_id", None)
    save_data(d)
    # main_msg_id ni o'chirish
    if main_msg_id:
        try:
            bot.delete_message(uid, main_msg_id)
        except Exception:
            pass
    # main_msg_id yo'q bo'lsa yoki boshqa xabar qolgan bo'lsa —
    # /admin_panel xabaridan oldingi xabarni ham o'chirishga harakat qilamiz
    if not main_msg_id:
        try:
            bot.delete_message(uid, msg.message_id - 1)
        except Exception:
            pass
    bot.send_message(uid, "🛠 *Admin panel*", parse_mode="Markdown", reply_markup=admin_menu())

def admin_broadcast_menu():
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("👤 Shaxsiy chatlar", callback_data="admin_bc_private"),
        InlineKeyboardButton("👥 Guruhlar", callback_data="admin_bc_groups")
    )
    kb.add(InlineKeyboardButton("📣 Umumiy (hammasi)", callback_data="admin_bc_all"))
    kb.add(InlineKeyboardButton("❌ Bekor qilish", callback_data="admin_cancel"))
    return kb

def admin_stats_period_menu():
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("1 kun", callback_data="admin_stats_1"),
        InlineKeyboardButton("1 hafta", callback_data="admin_stats_7"),
        InlineKeyboardButton("1 oy", callback_data="admin_stats_30")
    )
    kb.row(
        InlineKeyboardButton("1 yil", callback_data="admin_stats_365"),
        InlineKeyboardButton("Umumiy", callback_data="admin_stats_all")
    )
    kb.add(InlineKeyboardButton("❌ Bekor qilish", callback_data="admin_cancel"))
    return kb

# ============================================================
#  HANDLERLAR
# ============================================================

@bot.message_handler(commands=["start"])
def cmd_start(msg):
    uid = msg.from_user.id
    name = msg.from_user.first_name
    d = load_data()
    u = get_user(d, uid)

    # /start dan oldingi barcha xabarlarni orqada o'chirish (/start o'zi qoladi)
    def delete_old_messages(chat_id, before_id):
        for mid in range(before_id - 1, max(before_id - 50, 0), -1):
            try:
                bot.delete_message(chat_id, mid)
            except Exception:
                pass
    threading.Thread(target=delete_old_messages, args=(uid, msg.message_id), daemon=True).start()

    # Yangi foydalanuvchi tekshiruvi — bazada umuman yo'q bo'lsa
    is_new = str(uid) not in d
    u["name"] = msg.from_user.first_name
    u["username"] = msg.from_user.username or "—"
    save_data(d)

    # Faqat yangi foydalanuvchiga bildirishnoma
    if is_new and uid != ADMIN_ID:
        total_users = len([k for k in d if not k.startswith("_")])
        try:
            bot.send_message(
                ADMIN_ID,
                f"🆕 Yangi Foydalanuvchi!\n"
                f"Umumiy: {total_users}\n"
                f"Ismi: {name}"
            )
        except Exception:
            pass

    # Telefon raqami hali yo'q bo'lsa — ro'yxatdan o'tishni so'raymiz
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
        save_data(d)
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
    save_data(d)

# --- Telefon raqami qabul qilish ---
@bot.message_handler(content_types=["contact"])
def handle_contact(msg):
    uid = msg.from_user.id
    name = msg.from_user.first_name
    d = load_data()
    u = get_user(d, uid)
    u["phone"] = msg.contact.phone_number

    # Ro'yxatdan o'tish so'ragan xabarni o'chirish
    reg_msg_id = u.pop("reg_msg_id", None)
    save_data(d)
    if reg_msg_id:
        try:
            bot.delete_message(uid, reg_msg_id)
        except Exception:
            pass
    # Foydalanuvchi yuborgan contact xabarini ham o'chirish
    try:
        bot.delete_message(uid, msg.message_id)
    except Exception:
        pass

    if not check_subscription(uid):
        bot.send_message(uid, "⚠️ Botdan foydalanish uchun avvalo kanalga a'zo bo'ling!", reply_markup=ReplyKeyboardRemove())
        send_sub_required(uid)
        return

    bot.send_message(
        uid,
        f"✅ Ro'yxatdan o'tdingiz, *{name}*!\n\n"
        "Boshlash uchun *➕ Odat qo'shish* tugmasini bosing!",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    send_main_menu(uid)

# --- Faqat matn holati (odat nomi va vaqt kiritish) ---
@bot.message_handler(func=lambda m: True)
def handle_text(msg):
    uid = msg.from_user.id
    text = msg.text
    if not text:
        return
    d = load_data()
    u = get_user(d, uid)
    state = u.get("state")

    # Admin state larida a'zolik tekshirilmaydi
    if state not in ("admin_bc_private", "admin_bc_groups", "admin_bc_all", "admin_waiting_channel") and uid != ADMIN_ID:
        if not check_subscription(uid):
            send_sub_required(uid)
            return

    # --- Admin: habar matni ---
    if state in ("admin_bc_private", "admin_bc_groups", "admin_bc_all") and uid == ADMIN_ID:
        users = {k: v for k, v in d.items() if not k.startswith("_")}
        sent = 0
        failed = 0
        failed_list = []
        for target_uid, udata in users.items():
            if int(target_uid) == ADMIN_ID:
                continue
            if state == "admin_bc_groups":
                chat_type = udata.get("chat_type", "private")
                if chat_type != "group":
                    continue
            try:
                bot.send_message(int(target_uid), text)
                sent += 1
            except Exception as e:
                failed += 1
                failed_list.append(f"{udata.get('name','?')} ({target_uid}): {e}")
                print(f"[broadcast] xato: {target_uid} — {e}")
        u["state"] = None
        save_data(d)
        result = f"✅ Habar {sent} ta foydalanuvchiga yuborildi."
        if failed > 0:
            result += f"\n❌ {failed} ta foydalanuvchiga yetmadi:"
            for fl in failed_list:
                result += f"\n  • {fl}"
        bot.send_message(uid, result)
        bot.send_message(uid, "🛠 *Admin panel*", parse_mode="Markdown", reply_markup=admin_menu())
        return

    # --- Admin: kanal username ---
    if state == "admin_waiting_channel" and uid == ADMIN_ID:
        channel = text.strip()
        if not channel.startswith("@"):
            channel = "@" + channel
        if "_settings" not in d:
            d["_settings"] = {}
        try:
            chat = bot.get_chat(channel)
            d["_settings"]["required_channel"] = channel
            d["_settings"]["required_channel_title"] = chat.title
            u["state"] = None
            save_data(d)
            bot.send_message(uid, f"✅ Majburiy kanal tasdiqlandi: *{chat.title}* (`{channel}`)", parse_mode="Markdown")
            bot.send_message(uid, "🛠 *Admin panel*", parse_mode="Markdown", reply_markup=admin_menu())
        except Exception as e:
            bot.send_message(uid, f"❌ Xatolik: `{e}`\n\nBot kanalga admin sifatida qo'shilganmi?\n\nQaytadan username yozing:", parse_mode="Markdown")
        return

    # --- Odat nomi ---
    if state == "waiting_habit_name":
        u["temp_habit"] = {"name": text}
        u["state"] = "waiting_habit_time"
        # Foydalanuvchi va bot xabarlarini o'chirish
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
        save_data(d)
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
            # Foydalanuvchi va bot xabarlarini o'chirish
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
            save_data(d)

            # Eslatmani rejalashtirish
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
            save_data(d)
        except ValueError:
            bot.send_message(uid, "❌ Noto'g'ri format. Iltimos HH:MM formatida yozing.\n_Masalan: 08:00_", parse_mode="Markdown")
        return

    send_main_menu(uid)

# --- Odatlar ro'yxati ---
def show_habits(uid):
    d = load_data()
    u = get_user(d, uid)
    habits = u.get("habits", [])

    if not habits:
        send_main_menu(uid, "📭 Hali odat qo'shilmagan.\n\n➕ Odat qo'shish tugmasini bosing!")
        return

    text = "📋 *Sizning odatlaringiz:*\n\n"
    for h in habits:
        streak = h.get("streak", 0)
        fire = "🔥" if streak > 0 else "⚪"
        text += f"{fire} *{h['name']}*\n"
        text += f"   ⏰ {h['time']}  |  🔥 {streak} kunlik streak\n\n"

    d = load_data()
    u = get_user(d, uid)
    sent = bot.send_message(uid, text, parse_mode="Markdown", reply_markup=main_menu())
    u["main_msg_id"] = sent.message_id
    save_data(d)

# --- Statistika ---
def show_stats(uid):
    d = load_data()
    u = get_user(d, uid)
    habits = u.get("habits", [])

    if not habits:
        send_main_menu(uid, "📭 Hali odat yo'q.")
        return

    total_points = u.get("points", 0)

    # Ball darajasi
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

    text = "📊 *Statistika*\n"
    text += "▬" * 16 + "\n"
    text += f"⭐ *Jami ball: {total_points} ball*\n"
    text += f"🎖 Daraja: {rank}\n"
    text += "▬" * 16 + "\n\n"

    for h in habits:
        streak = h.get("streak", 0)
        total = h.get("total_done", 0)
        last = h.get("last_done", "Hali bajarilmagan")
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
        text += f"   ⭐ Odat balli: {habit_points} ball\n"
        text += f"   📅 Oxirgi: {last}\n\n"

    d = load_data()
    u = get_user(d, uid)
    sent = bot.send_message(uid, text, parse_mode="Markdown", reply_markup=main_menu())
    u["main_msg_id"] = sent.message_id
    save_data(d)

# --- Reyiting ---
def show_rating(uid):
    d = load_data()
    users = {k: v for k, v in d.items() if not k.startswith("_")}

    # Balllar bo'yicha saralash
    ranking = []
    for user_id, udata in users.items():
        points = udata.get("points", 0)
        name = udata.get("name", "Noma'lum")
        ranking.append((name, points))
    ranking.sort(key=lambda x: x[1], reverse=True)
    top10 = ranking[:10]

    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

    text = "🏆 Top 10 Reyiting\n"
    text += "▬" * 16 + "\n\n"

    for i, (name, points) in enumerate(top10):
        text += f"{medals[i]} {name} — {points} ball\n"

    if not top10:
        text += "Hali hech kim ball to'plamagan."

    u = get_user(d, uid)
    sent = bot.send_message(uid, text, reply_markup=main_menu())
    u["main_msg_id"] = sent.message_id
    save_data(d)

# --- O'chirish menyusi ---
def delete_habit_menu(uid):
    d = load_data()
    u = get_user(d, uid)
    habits = u.get("habits", [])

    if not habits:
        bot.send_message(uid, "📭 O'chirish uchun odat yo'q.", reply_markup=main_menu())
        return

    kb = InlineKeyboardMarkup()
    for h in habits:
        kb.add(InlineKeyboardButton(f"🗑 {h['name']} ({h['time']})", callback_data=f"delete_{h['id']}"))
    kb.add(InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel"))

    bot.send_message(uid, "Qaysi odatni o'chirmoqchisiz?", reply_markup=kb)

# --- Callback (Menyu / Bajardim / O'chirish) ---
@bot.callback_query_handler(func=lambda c: True)
def callback_handler(call):
    uid = call.from_user.id
    cdata = call.data
    d = load_data()
    u = get_user(d, uid)

    # Asosiy menyu tugmalari
    if cdata == "check_sub":
        if check_subscription(uid):
            bot.answer_callback_query(call.id, "✅ Tasdiqlandi!")
            bot.delete_message(uid, call.message.message_id)
            u.pop("sub_msg_id", None)
            save_data(d)
            name = call.from_user.first_name
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
            save_data(d)
        else:
            bot.answer_callback_query(call.id, "❌ Hali a'zo bo'lmadingiz!")
        return

    # admin_cancel va check_sub dan tashqari barcha callbacklarda a'zolik tekshiruvi
    if cdata not in ("check_sub", "admin_cancel", "admin_close") and not cdata.startswith("admin_"):
        if not check_subscription(uid):
            bot.answer_callback_query(call.id)
            send_sub_required(uid)
            return

    # Admin panel callbacklari
    if cdata == "admin_close":
        if uid != ADMIN_ID:
            return
        u["state"] = None
        save_data(d)
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
        save_data(d)
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
        save_data(d)
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
        users = {k: v for k, v in d.items() if not k.startswith("_")}
        if not users:
            bot.send_message(uid, "👥 Foydalanuvchilar yo'q.", reply_markup=admin_menu())
            return

        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🔙 Admin panel", callback_data="admin_cancel"))

        parts = []
        current = f"👥 Jami foydalanuvchilar: {len(users)} ta\n"
        current += "▬" * 20 + "\n\n"

        for i, (target_uid, udata) in enumerate(users.items(), 1):
            name = udata.get("name", "—")
            username = udata.get("username", "—")
            if username and username != "—" and not username.startswith("@"):
                username = "@" + username
            phone = udata.get("phone", "Kiritilmagan")
            joined = udata.get("joined_at", "—")
            habits = udata.get("habits", [])

            block = f"👤 {i}. {name}\n"
            block += f"  🆔 ID: {target_uid}\n"
            block += f"  📌 Username: {username}\n"
            block += f"  📞 Tel: {phone}\n"
            block += f"  📅 Qo'shilgan: {joined}\n"

            if habits:
                block += f"  📋 Odatlar ({len(habits)} ta):\n"
                for h in habits:
                    streak = h.get("streak", 0)
                    total = h.get("total_done", 0)
                    block += f"    • {h['name']} | {h['time']} | streak: {streak} kun | jami: {total}\n"
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
        d2 = load_data()
        current = d2.get("_settings", {}).get("required_channel", None)
        kb = InlineKeyboardMarkup()
        if current:
            kb.add(InlineKeyboardButton("🗑 Kanalni o'chirish", callback_data="admin_channel_remove"))
        kb.add(InlineKeyboardButton("❌ Bekor qilish", callback_data="admin_cancel"))
        msg_text = "🔗 Majburiy kanal\n\n"
        if current:
            title = d2.get("_settings", {}).get("required_channel_title", current)
            msg_text += f"Hozirgi kanal: {title} ({current})\n\nO'zgartirish uchun yangi kanal username yozing:"
        else:
            msg_text += "Hozircha majburiy kanal yo'q.\n\nKanal username yozing (Masalan: @mening_kanalim):"
        u["state"] = "admin_waiting_channel"
        save_data(d)
        bot.send_message(uid, msg_text, reply_markup=kb)
        return

    if cdata == "admin_channel_remove":
        if uid != ADMIN_ID:
            return
        bot.answer_callback_query(call.id)
        bot.delete_message(uid, call.message.message_id)
        d2 = load_data()
        if "_settings" in d2:
            d2["_settings"].pop("required_channel", None)
            d2["_settings"].pop("required_channel_title", None)
            save_data(d2)
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
        users = {k: v for k, v in d.items() if not k.startswith("_")}
        today = date.today()

        if period == "all":
            filtered = users
            period_label = "Umumiy"
        else:
            days = int(period)
            filtered = {}
            for k, v in users.items():
                try:
                    joined = date.fromisoformat(v.get("joined_at", "2000-01-01"))
                    if (today - joined).days <= days:
                        filtered[k] = v
                except Exception:
                    pass
            labels = {"1": "1 kun", "7": "1 hafta", "30": "1 oy", "365": "1 yil"}
            period_label = labels.get(period, period)

        text = f"📈 *Statistika — {period_label}*\n\n"
        text += f"👥 Qo'shilgan foydalanuvchilar: *{len(filtered)} ta*\n\n"
        text += "📋 *Odat yaratish bo'yicha:*\n"
        habit_counts = []
        for target_uid, udata in users.items():
            name = udata.get("name", f"ID:{target_uid}")
            count = len(udata.get("habits", []))
            if count > 0:
                habit_counts.append((name, count))
        habit_counts.sort(key=lambda x: x[1], reverse=True)
        if habit_counts:
            for name, count in habit_counts[:20]:
                text += f"  • *{name}*: {count} ta odat\n"
        else:
            text += "  Hali odat yaratilmagan.\n"

        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("❌ Bekor qilish", callback_data="admin_cancel"))
        bot.send_message(uid, text, parse_mode="Markdown", reply_markup=kb)
        return

    # Asosiy menyu tugmalari
    if cdata == "menu_add":
        u["state"] = "waiting_habit_name"
        bot.answer_callback_query(call.id)
        bot.delete_message(uid, call.message.message_id)
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.add(InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel"))
        sent = bot.send_message(uid, "📝 Odatning nomini yozing:\n\n_Masalan: Kitob o'qish, Sport, Suv ichish..._", parse_mode="Markdown", reply_markup=cancel_kb)
        u["temp_msg_id"] = sent.message_id
        save_data(d)
        return

    if cdata == "cancel":
        u["state"] = None
        u.pop("temp_habit", None)
        old_msg_id = u.pop("temp_msg_id", None)
        save_data(d)
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
                # 5 ball qo'shish
                u["points"] = u.get("points", 0) + 5
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
        msg_id = call.message.message_id
        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass
        try:
            bot.edit_message_text(f"🗑 *{habit_name}* o'chirildi.", uid, msg_id, parse_mode="Markdown")
        except Exception:
            pass

        def delete_and_menu(chat_id, message_id):
            time.sleep(2)
            try:
                bot.delete_message(chat_id, message_id)
            except Exception as e:
                print(f"[delete_and_menu] delete_message xatosi: {e}")
            try:
                send_main_menu(chat_id)
            except Exception as e:
                print(f"[delete_and_menu] send_main_menu xatosi: {e}")

        threading.Thread(target=delete_and_menu, args=(uid, msg_id), daemon=True).start()

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

    # Bot menyusini o'rnatish
    from telebot.types import BotCommand
    try:
        bot.set_my_commands([
            BotCommand("start", "Botni ishga tushirish"),
            BotCommand("admin_panel", "Admin panel"),
        ])
        print("Bot menyusi o'rnatildi: /start, /admin_panel")
    except Exception as e:
        print(f"Menyu o'rnatishda xato: {e}")

    # Scheduler alohida threadda
    t = threading.Thread(target=scheduler_loop, daemon=True)
    t.start()

    print("Bot tayyor! Telegramdan /start yuboring.")
    bot.infinity_polling()
