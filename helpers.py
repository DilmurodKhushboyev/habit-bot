#!/usr/bin/env python3
"""
Yordamchi funksiyalar: get_lang, T, get_rank, today_uz5, lang_keyboard
"""

from datetime import datetime, timezone, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import load_user
from texts import LANGS


def get_lang(uid):
    u = load_user(uid)
    return u.get("lang", "uz")

def today_uz5():
    """UTC+5 (Toshkent) bo'yicha bugungi sana"""
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
