"""
keyboards.py
============
Barcha tugmalar (klaviaturalar), bot obyekti va yordamchi UI funksiyalar.
Bu faylda: bot = telebot.TeleBot(...), main_menu, done_keyboard, menu2 va boshqalar.
Bog'liq fayllar: config.py, database.py, languages.py
"""

import telebot
from telebot.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from config import BOT_TOKEN, ADMIN_ID, mongo_col
from database import load_user, save_user, load_settings, save_settings
from languages import T, get_lang, LANGS, lang_keyboard

bot = telebot.TeleBot(BOT_TOKEN)

# Bot username — bir marta yuklanadi, keyingi murojaatlarda qayta so'ralmasin
_BOT_USERNAME = None

# Share card file_id — inline query orqali rasmni boshqa chatga yuborish uchun
_share_file_ids = {}

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
    btn_text = T(uid, "btn_enter") if uid else "📃 Kirish"
    return {"inline_keyboard": [[
        {"text": btn_text, "web_app": {"url": webapp_url}}
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
    return T(uid, "main_greeting", name=name)


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
