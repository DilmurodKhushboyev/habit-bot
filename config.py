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
