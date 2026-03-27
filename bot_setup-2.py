#!/usr/bin/env python3
"""
Bot instance va UI yordamchi funksiyalari
"""

import os
import logging
import requests
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# ============================================================
#  LOGGING
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("super_habits")

from config import BOT_TOKEN
from database import load_user, save_user
from helpers import T

# ============================================================
#  BOT
# ============================================================
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
    logger.error("[send_message_colored] XATO: %s", result.get('description'))
    return None

def cBtn(text, callback_data, style=None):
    """Rangli InlineKeyboardButton - style atributini qo'shadi"""
    btn = InlineKeyboardButton(text, callback_data=callback_data)
    if style:
        btn.style = style
    return btn

def ok_kb(uid=None):
    """'✅ Tushunarli' tugmasi — bosish bilan xabar o'chadi"""
    label = T(uid, "btn_ack") if uid else "✅ OK"
    kb = InlineKeyboardMarkup()
    kb.add(cBtn(label, "ack_delete_msg", "success"))
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
#  GLOBAL ERROR HANDLER (pyTelegramBotAPI)
# ============================================================
class BotExceptionHandler(telebot.ExceptionHandler):
    """Barcha handler xatolarini ushlaydi — bot crash bo'lmaydi."""
    def handle(self, exception):
        logger.error("Handler xatolik: %s", exception, exc_info=True)
        return True   # True = bot ishlashda davom etadi

bot.exception_handler = BotExceptionHandler()
