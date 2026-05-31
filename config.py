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
mongo_db      = mongo_client.get_default_database()
mongo_col     = mongo_db["users"]
reminders_col = mongo_db["reminders"]

# -- MongoDB indekslar (bot ishga tushganda bir marta) --
try:
    mongo_col.create_index([("points", DESCENDING)], name="idx_points",  background=True)
    mongo_col.create_index([("streak", DESCENDING)], name="idx_streak",  background=True)
    mongo_col.create_index([("name",   ASCENDING)],  name="idx_name",    background=True)
    reminders_col.create_index([("user_id", ASCENDING), ("status", ASCENDING)], name="idx_user_status", background=True)
    reminders_col.create_index([("remind_at", ASCENDING)], name="idx_remind_at", background=True)
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
    "pet_rabbit":  {"type": "jon_soften",  "value": 50},     # Jon kamayishi 50% yumshoqroq (har kun ishlaydi)

    # ── CAR: ball bonus + vizual status ──
    "car_sport":   {"type": "points_percent", "value": 8},   # +8% har bir checkin ball'iga + reytingda gold ramka
}

# ============================================================
#  ESLATMALAR (bir martalik, odatlardan ajratilgan)
# ============================================================
REMINDER_COMPLETE_POINTS = 2              # Eslatma bajarilganda beriladigan ball
REMINDER_JOB_PREFIX      = "reminder_"    # schedule job tag prefix (SYSTEM_JOB_TAGS bilan konflikt yo'q)
REMINDER_MAX_TEXT_LEN    = 200            # Eslatma matnining maksimal uzunligi (profil bio bilan bir xil)

# ============================================================
#  ODATLAR
# ============================================================
HABIT_LIMIT = 15                          # Bir foydalanuvchi yarata oladigan maksimal odat soni
                                          # (freemium qo'shilganda FREE/PREM ga ajratiladi)

# Odat yaratilgandan keyin uni o'chirish uchun kutiladigan vaqt (soniya).
# Anti-exploit: "yarat → tasdiqla → ball ol → o'chir → qayta yarat" ball to'plash
# siklini buzadi. flask_routes_core.api_habits_delete VA callbacks_habits.confirm_delete_
# (bot/WebApp sinxron, Qoida #10) shu konstantadan o'qiydi.
HABIT_DELETE_LOCK_SEC = 3600              # 1 soat

# ============================================================
#  STREAK MILESTONE'LARI (markazlashtirilgan — yagona manba)
#  Bot (callbacks_checkin / callbacks_checkin_done) VA WebApp
#  (flask_routes_data.api_checkin) shu dict'dan o'qiydi — sinxron.
#  streak global qiymati shu kalitlardan biriga tenglashganda:
#    - foydalanuvchiga "bonus" ball beriladi
#    - u["streak_milestones_sent"] ga qo'shiladi (takror bermaslik uchun)
#  emoji — xabarda; bonus — beriladigan ball.
#  (Eslatma: foydalanuvchiga ko'rinadigan matn texts.py "streak_milestone"
#   orqali 3 tilda — Qoida #22. Bu yerdagi qiymat faqat raqam/emoji.)
# ============================================================
STREAK_MILESTONES = {
    3:   {"emoji": "✨", "bonus": 5},
    7:   {"emoji": "🔥", "bonus": 10},
    14:  {"emoji": "⚡", "bonus": 20},
    30:  {"emoji": "💎", "bonus": 50},
    60:  {"emoji": "🏆", "bonus": 100},
    100: {"emoji": "👑", "bonus": 200},
    180: {"emoji": "🌟", "bonus": 300},
    365: {"emoji": "🎖️", "bonus": 500},
}

# ============================================================
#  CITY (SHAHAR) — gamification 2.0
#  Foydalanuvchi har odat tasdiqlasa → bino qurilishi davom etadi.
#  66 kun = bino to'liq quriladi (odat shakllanishi ilmiy chegarasi).
#  Grid 30x30 = 900 katak (PHASE C2.1 da 20→30 ga kengaytirildi).
# ============================================================
CITY_GRID_SIZE   = 30                  # 30x30 = 900 katak
BUILDING_DAYS    = 66                  # odat shakllanish kunlari (max progress)
CITY_VERSION     = 1                   # schema versiyasi (kelajakdagi migratsiyalar uchun)
CITY_NAME_MAX_LEN = 30                 # Shahar nomi maksimal uzunligi (XSS/UI uchun)

# Bino turlari (10 ta) — har biri emoji + tarjima kaliti
# name_key keyinchalik texts.py LANGS dict'iga 3 tilga qo'shiladi (Qoida #22)
BUILDING_TYPES = {
    "stadium":   {"emoji": "🏟️", "name_key": "city_bld_stadium"},
    "library":   {"emoji": "📚", "name_key": "city_bld_library"},
    "mosque":    {"emoji": "🕌", "name_key": "city_bld_mosque"},
    "school":    {"emoji": "🎓", "name_key": "city_bld_school"},
    "park":      {"emoji": "🌳", "name_key": "city_bld_park"},
    "cafe":      {"emoji": "☕", "name_key": "city_bld_cafe"},
    "bank":      {"emoji": "🏦", "name_key": "city_bld_bank"},
    "hospital":  {"emoji": "🏥", "name_key": "city_bld_hospital"},
    "studio":    {"emoji": "🎨", "name_key": "city_bld_studio"},
    "house":     {"emoji": "🏠", "name_key": "city_bld_house"},
}

# Progress → Stage (5 ta vizual bosqich)
# get_building_stage(progress) shu chegaralarni ishlatadi (city_logic.py)
# Stage 0: foundation (asos)        — 0-13 kun (0-20%)
# Stage 1: skeleton (skelet)        — 14-26 kun (21-40%)
# Stage 2: walls (devorlar)         — 27-39 kun (41-60%)
# Stage 3: roof (tom + derazalar)   — 40-52 kun (61-80%)
# Stage 4: complete (to'liq)        — 53-66 kun (81-100%)
BUILDING_STAGE_THRESHOLDS = [13, 26, 39, 52, 66]   # max progress shu yerdan oshmasligi kerak

# Dekoratsiya turlari (bozordan sotib olinadi, odatdan emas)
# Birinchi versiyada 5 ta — kelajakda kengayadi
DECORATION_TYPES = {
    "tree":        {"emoji": "🌳", "name_key": "city_dec_tree"},
    "flower":      {"emoji": "🌸", "name_key": "city_dec_flower"},
    "car":         {"emoji": "🚗", "name_key": "city_dec_car"},
    "bench":       {"emoji": "🪑", "name_key": "city_dec_bench"},
    "fountain":    {"emoji": "⛲", "name_key": "city_dec_fountain"},
}

# Dekoratsiya narxlari (ball bilan, bozorda) — alohida dict
# (asosiy SHOP_PRICES bilan aralashtirmaymiz, chunki ular boshqa toifa)
SHOP_DECORATION_PRICES = {
    "tree":     30,
    "flower":   20,
    "car":      80,
    "bench":    40,
    "fountain": 120,
}

# Construction Insurance — premium feature (Qoida #5 javob: HA, kelajakka)
# Faol bo'lsa: kun o'tkazilsa progress -1 bo'lmaydi (saqlanadi)
INSURANCE_PRICE       = 200            # ball
INSURANCE_DURATION    = 30             # kun (1 oy)
