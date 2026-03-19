#!/usr/bin/env python3
"""
config.py
=========
Sozlamalar va kutubxonalar.
Bu faylda: BOT_TOKEN, ADMIN_ID, MONGO_URI va barcha import-lar.
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
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    InlineQueryResultCachedPhoto, SwitchInlineQueryChosenChat
)
from pymongo import MongoClient

# ============================================================
#  SOZLAMALAR
# ============================================================
BOT_TOKEN        = os.environ.get("BOT_TOKEN", "")
ADMIN_ID         = int(os.environ.get("ADMIN_ID", 0))
MONGO_URI        = os.environ.get("MONGO_URI", "")

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
