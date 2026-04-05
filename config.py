#!/usr/bin/env python3
"""
Sozlamalar va MongoDB ulanish
"""

import os
from pymongo import MongoClient, ASCENDING, DESCENDING

# ============================================================
#  SOZLAMALAR
# ============================================================
BOT_TOKEN   = os.environ.get("BOT_TOKEN", "SHU_YERGA_TOKEN_QOYING")
ADMIN_ID    = int(os.environ.get("ADMIN_ID", 5071908808))
MONGO_URI   = os.environ.get("MONGO_URI",
    "mongodb+srv://habitbot:Habit2026@cluster0.i0jux9m.mongodb.net/?appName=Cluster0")

# ============================================================
#  MONGODB ULANISH
# ============================================================
mongo_client = MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=30000,  # 5000 → 30000: Amsterdam→Bahrain uzoq masofa
    connectTimeoutMS=20000,          # 5000 → 20000: ulanish o'rnatishga vaqt
    socketTimeoutMS=30000,           # 10000 → 30000: so'rov bajarishga vaqt
    retryWrites=True,
    retryReads=True,
    maxPoolSize=20,                  # bir vaqtda max 20 ulanish
    waitQueueTimeoutMS=10000,        # 5000 → 10000: pool to'liq bo'lsa kutish
    maxIdleTimeMS=30000,             # YANGI: 30s ishlatilmagan ulanishni yopadi (Atlas M0 uchun)
    heartbeatFrequencyMS=10000,      # YANGI: 10s da bir ulanish tekshiruvi (cluster uyg'oq turadi)
)
mongo_db   = mongo_client["habit_bot"]
mongo_col  = mongo_db["users"]
groups_col = mongo_db["groups"]

# -- MongoDB indekslar (bot ishga tushganda bir marta) --
try:
    mongo_col.create_index([("points", DESCENDING)], name="idx_points",  background=True)
    mongo_col.create_index([("streak", DESCENDING)], name="idx_streak",  background=True)
    mongo_col.create_index([("name",   ASCENDING)],  name="idx_name",    background=True)
    groups_col.create_index([("members", ASCENDING)], name="idx_members", background=True)
except Exception as _e:
    print(f"[warn] MongoDB indeks yaratishda xato: {_e}")

# ============================================================
#  BOZOR NARXLARI (markazlashtirilgan)
# ============================================================
SHOP_PRICES = {
    "shield_1":    100,
    "shield_3":    250,
    "bonus_2x":    150,
    "bonus_3x":    300,
    "xp_booster":  400,
    "badge_fire":  200,
    "badge_star":  250,
    "badge_secret":600,
    "pet_cat":     300,
    "pet_dog":     350,
    "pet_rabbit":  300,
    "car_sport":   500,
    "jon_restore":  25,
    "gift_box":      0,   # faqat Stars bilan sotib olinadi
}

SHOP_SELL_PRICES = {
    "shield_1":     50,
    "shield_3":    125,
    "bonus_2x":     75,
    "bonus_3x":    150,
    "xp_booster":  200,
    "badge_fire":  100,
    "badge_star":  125,
    "badge_secret":300,
    "pet_cat":     150,
    "pet_dog":     175,
    "pet_rabbit":  150,
    "car_sport":   250,
}

SHOP_STARS_PRICES = {
    "gift_box": 5,
}

# Bir martalik narsalar (qayta sotib olinmaydi)
SHOP_ONE_TIME = [
    "badge_fire", "badge_star", "badge_secret",
    "pet_cat", "pet_dog", "pet_rabbit", "car_sport",
]

# ============================================================
#  BOZOR MAHSULOTLARI VAZIFALARI (markazlashtirilgan)
#  Har bir badge/pet/car ning HAQIQIY ta'siri shu yerda belgilanadi.
#  type — qaysi logika ishlatiladi (backend shu asosda tekshiradi)
#  value — raqamli qiymat (foiz yoki miqdor)
# ============================================================
SHOP_BONUS_EFFECTS = {
    # ── BADGES: checkin ball'iga foizli bonus (passive, active_badge faol bo'lganda) ──
    "badge_fire":  {"type": "points_percent", "value": 3},   # +3% har bir checkin ball'iga
    "badge_star":  {"type": "points_percent", "value": 5},   # +5% har bir checkin ball'iga
    "badge_secret":{"type": "points_percent", "value": 12},  # +12% har bir checkin ball'iga

    # ── PETS: har biri o'ziga xos super-kuch ──
    "pet_cat":     {"type": "streak_save", "value": 7},      # 7 kunda 1 marta streak avtomatik saqlash
    "pet_dog":     {"type": "daily_bonus", "value": 2},      # Kunlik birinchi checkin'ga +2 ball
    "pet_rabbit":  {"type": "jon_delay",   "value": 30},     # Jon kamaytirilishi +30 daqiqa kechikadi

    # ── CAR: ball bonus + vizual status ──
    "car_sport":   {"type": "points_percent", "value": 8},   # +8% har bir checkin ball'iga + reytingda gold ramka
}
