#!/usr/bin/env python3
"""
Ma'lumotlar bazasi funksiyalari
"""

import time as _cache_time
from datetime import date, datetime, timedelta

from config import mongo_col, groups_col, reminders_col

# ── Exponential backoff retry yordamchi ──────────────────────
# 3 urinish: 0.3s → 0.7s → crash + log
# (timeout 5s bo'lgani uchun kichik delay yetarli)
_RETRY_DELAYS = [0.3, 0.7]

def _retry_mongo(fn, label, default=None):
    """fn() ni 3 marta urinib ko'radi. Exponential backoff bilan."""
    for _attempt in range(3):
        try:
            return fn()
        except Exception as _e:
            if _attempt < 2:
                import time as _t; _t.sleep(_RETRY_DELAYS[_attempt])
            else:
                print(f"[{label}] xato: {_e}")
                return default

# ============================================================
#  MA'LUMOTLAR BAZASI FUNKSIYALARI
# ============================================================
def load_user(user_id):
    uid = str(user_id)
    _default = {"habits": [], "state": None, "joined_at": str(date.today())}

    def _fn():
        doc = mongo_col.find_one({"_id": uid})
        if doc:
            return {k: v for k, v in doc.items() if k != "_id"}
        return {"habits": [], "state": None, "joined_at": str(date.today())}

    result = _retry_mongo(_fn, f"load_user ({uid})", default=_default)
    return result if result is not None else _default

def save_user(user_id, udata):
    def _fn():
        mongo_col.update_one(
            {"_id": str(user_id)},
            {"$set": udata},
            upsert=True
        )
        invalidate_users_cache()

    _retry_mongo(_fn, f"save_user ({user_id})")

def load_settings():
    def _fn():
        doc = mongo_col.find_one({"_id": "_settings"})
        if doc:
            return {k: v for k, v in doc.items() if k != "_id"}
        return {}

    result = _retry_mongo(_fn, "load_settings", default={})
    return result if result is not None else {}

def save_settings(settings):
    def _fn():
        mongo_col.update_one(
            {"_id": "_settings"},
            {"$set": settings},
            upsert=True
        )

    _retry_mongo(_fn, "save_settings")

# ── load_all_users cache (TTL: 60 soniya) ──
_all_users_cache      = None
_all_users_cache_time = 0.0
_ALL_USERS_TTL        = 60

def invalidate_users_cache():
    global _all_users_cache, _all_users_cache_time
    _all_users_cache      = None
    _all_users_cache_time = 0.0

def load_all_users(force=False):
    global _all_users_cache, _all_users_cache_time
    now = _cache_time.time()
    if not force and _all_users_cache is not None and (now - _all_users_cache_time) < _ALL_USERS_TTL:
        return _all_users_cache

    def _fn():
        users = {}
        for doc in mongo_col.find({"_id": {"$not": {"$regex": "^_"}}}):
            uid = doc["_id"]
            users[uid] = {k: v for k, v in doc.items() if k != "_id"}
        return users

    users = _retry_mongo(_fn, "load_all_users", default={})
    if users is not None:
        _all_users_cache      = users
        _all_users_cache_time = now
    return _all_users_cache or {}

def user_exists(user_id):
    uid = str(user_id)
    result = _retry_mongo(
        lambda: mongo_col.find_one({"_id": uid}) is not None,
        f"user_exists ({uid})",
        default=False
    )
    return result if result is not None else False

def count_users():
    result = _retry_mongo(
        lambda: mongo_col.count_documents({"_id": {"$not": {"$regex": "^_"}}}),
        "count_users",
        default=0
    )
    return result if result is not None else 0

# ============================================================
#  POINTS HISTORY VA PERIOD HELPER'LARI
# ============================================================
# udata["points_history"] = {"YYYY-MM-DD": net_delta_int, ...}
# Har kun uchun bir entry (positive yoki negative). Bu /api/rating
# endpoint'da period (week/month/all) bo'yicha ball hisoblash uchun.
# Backward compat: points_history bo'sh bo'lsa, eski xulq saqlanadi
# (umumiy udata["points"] qaytariladi).

def _today_uz5_str():
    """UZ+5 timezone bo'yicha bugungi sana ('YYYY-MM-DD').
    helpers.today_uz5() bilan sinxron — ammo circular import oldini olish
    uchun bu yerda mustaqil hisoblanadi."""
    return (datetime.utcnow() + timedelta(hours=5)).strftime("%Y-%m-%d")

def add_points_history(udata, delta, date_str=None):
    """udata["points_history"] ga delta qo'shadi (positive yoki negative).
    udata ni mutate qiladi — chaqiruvchi save_user() ni o'zi qiladi
    (mavjud pattern: udata["points"] += N; save_user(uid, udata)).

    delta=0 bo'lsa hech narsa qilmaydi (DB shishishini oldini olish).
    """
    if delta == 0:
        return
    if date_str is None:
        date_str = _today_uz5_str()
    hist = udata.get("points_history") or {}
    if not isinstance(hist, dict):
        hist = {}
    hist[date_str] = int(hist.get(date_str, 0)) + int(delta)
    # Agar net 0 bo'lib qolsa — entry'ni tozalamaymiz (audit uchun foydali,
    # va get_points_in_period() 0 ni e'tiborsiz qoldiradi).
    udata["points_history"] = hist

def get_points_in_period(udata, days=None):
    """Period (hafta/oy/barchasi) ichidagi ball qiymati.

    3 qatlamli mantiq:
    - Layer 1 (days=None, 'Barchasi'): doim umumiy udata["points"] qaytariladi
      (chunki points_history to'liq tarix emas — yangi pattern qo'shilgandan
      keyin saqlangan delta'lar emas, balki umumiy mavjud ball ishonchli).
    - Layer 2 (days=N, history bor): points_history dan aniq period yig'indisi.
    - Layer 3 (days=N, history yo'q — eski user): done_log dagi davriy faol
      kunlar × 5 ball proxy. Bu taxminiy (bonus/booster hisobga olinmaydi),
      lekin eski foydalanuvchilarni reytingda adolatli ko'rsatadi (chunki
      0 ball ko'rsatish ularni butunlay yiqitardi).

    Yangi action qilgan eski user uchun history asta-sekin to'lib boradi va
    layer 2 ga o'tadi (vaqt o'tgan sari aniqlik oshadi).
    """
    # Layer 1: 'Barchasi' → umumiy points (har doim ishonchli)
    if days is None:
        return int(udata.get("points", 0))

    # Layer 2: history bor → aniq period yig'indisi
    hist = udata.get("points_history") or {}
    if isinstance(hist, dict) and hist:
        today = datetime.utcnow() + timedelta(hours=5)
        cutoff = (today - timedelta(days=days)).strftime("%Y-%m-%d")
        return sum(int(v) for d, v in hist.items() if d >= cutoff)

    # Layer 3: history yo'q (eski user) → done_log dan proxy 5 ball/kun
    done_log = udata.get("done_log") or {}
    if not isinstance(done_log, dict) or not done_log:
        return 0
    today = datetime.utcnow() + timedelta(hours=5)
    cutoff_dt = (today - timedelta(days=days)).date()
    active_days = 0
    for d_str, v in done_log.items():
        if not v:
            continue
        try:
            d_obj = datetime.strptime(d_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue
        if d_obj >= cutoff_dt:
            active_days += 1
    return active_days * 5

def get_streak_in_period(udata, days=None):
    """udata["done_log"] dan davriy oraliqdagi maksimum ketma-ket
    ✅ kunlar uzunligi. days=None → butun tarix.

    Misol: done_log = {"2026-05-01": True, "2026-05-02": True, "2026-05-04": True}
    → period 7 kun → maks ketma-ket 2 kun (1-2 may), keyin 1 kun (4 may).
    Natija: 2.

    Backward compat: done_log bo'sh bo'lsa → udata["streak"] qaytariladi
    (joriy streak — eski xulq).
    """
    done_log = udata.get("done_log") or {}
    if not isinstance(done_log, dict) or not done_log:
        return int(udata.get("streak", 0))

    today = datetime.utcnow() + timedelta(hours=5)
    if days is None:
        cutoff_dt = None
    else:
        cutoff_dt = (today - timedelta(days=days)).date()

    # Faqat True kunlarni date obyektlariga aylantiramiz va saralаymiz
    active_dates = []
    for d_str, v in done_log.items():
        if not v:
            continue
        try:
            d_obj = datetime.strptime(d_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue
        if cutoff_dt is not None and d_obj < cutoff_dt:
            continue
        active_dates.append(d_obj)

    if not active_dates:
        return 0

    active_dates.sort()
    max_streak = 1
    cur_streak = 1
    for i in range(1, len(active_dates)):
        if (active_dates[i] - active_dates[i-1]).days == 1:
            cur_streak += 1
            if cur_streak > max_streak:
                max_streak = cur_streak
        else:
            cur_streak = 1
    return max_streak

# ============================================================
#  CITY (SHAHAR) HELPER'LARI
# ============================================================
# udata["city"] = {
#   "version": 1,
#   "buildings": [{id, habit_id, building_type, x, y, progress, started_at, last_updated}],
#   "decorations": [{id, decoration_type, x, y, placed_at}],
#   "insurance_active": bool,
#   "insurance_until": "YYYY-MM-DD" yoki None
# }
# Schema oqilona: faqat band kataklarni saqlaymiz (400 ta entry emas).
# Asosiy logic city_logic.py da — bu yerda faqat init/get helper'lari.

def init_city_for_user(udata):
    """Yangi foydalanuvchi uchun bo'sh shahar yaratadi. Idempotent —
    agar udata["city"] allaqachon bor va to'g'ri schema'da bo'lsa,
    hech narsa qilmaydi (eski user'larni buzmaslik uchun).

    udata ni mutate qiladi — chaqiruvchi save_user() ni o'zi qiladi.
    """
    from config import CITY_VERSION

    city = udata.get("city")
    if isinstance(city, dict) and city.get("version") == CITY_VERSION:
        # Allaqachon mavjud va to'g'ri versiya — tegmaymiz
        return

    udata["city"] = {
        "version": CITY_VERSION,
        "buildings": [],
        "decorations": [],
        "insurance_active": False,
        "insurance_until": None,
    }

def get_user_city(udata):
    """udata dan shahar obyektini qaytaradi. Agar yo'q bo'lsa —
    init_city_for_user() chaqirib bo'sh shahar yaratadi va qaytaradi.

    Helper sifatida ishlatiladi (city_logic.py va flask routes'lar uchun).
    Mutate qilmaydi (faqat yo'q bo'lsa init qiladi).
    """
    if not isinstance(udata.get("city"), dict):
        init_city_for_user(udata)
    return udata["city"]

def load_group(group_id):
    def _fn():
        doc = groups_col.find_one({"_id": str(group_id)})
        if doc:
            return {k: v for k, v in doc.items() if k != "_id"}
        return None

    return _retry_mongo(_fn, f"load_group ({group_id})", default=None)

def save_group(group_id, gdata):
    def _fn():
        groups_col.update_one(
            {"_id": str(group_id)},
            {"$set": gdata},
            upsert=True
        )

    _retry_mongo(_fn, f"save_group ({group_id})")

def delete_group(group_id):
    def _fn():
        groups_col.delete_one({"_id": str(group_id)})

    _retry_mongo(_fn, f"delete_group ({group_id})")

# ============================================================
#  ESLATMALAR (bir martalik)
# ============================================================
def create_reminder(reminder_doc):
    """Yangi eslatma yaratadi. reminder_doc dict — _id avtomatik."""
    def _fn():
        res = reminders_col.insert_one(reminder_doc)
        return str(res.inserted_id)

    return _retry_mongo(_fn, "create_reminder", default=None)

def get_reminder(reminder_id):
    """Bitta eslatma olish (_id bo'yicha)."""
    from bson import ObjectId
    def _fn():
        try:
            doc = reminders_col.find_one({"_id": ObjectId(reminder_id)})
        except Exception:
            return None
        if doc:
            doc["_id"] = str(doc["_id"])
        return doc

    return _retry_mongo(_fn, f"get_reminder ({reminder_id})", default=None)

def list_reminders(user_id, status=None):
    """Foydalanuvchining eslatmalari. status=None → barchasi."""
    def _fn():
        query = {"user_id": int(user_id)}
        if status:
            query["status"] = status
        docs = list(reminders_col.find(query).sort("remind_at", 1))
        for d in docs:
            d["_id"] = str(d["_id"])
        return docs

    return _retry_mongo(_fn, f"list_reminders ({user_id})", default=[])

def update_reminder(reminder_id, updates):
    """Eslatma yangilash (status o'zgartirish, notified_at belgilash)."""
    from bson import ObjectId
    def _fn():
        try:
            reminders_col.update_one(
                {"_id": ObjectId(reminder_id)},
                {"$set": updates}
            )
            return True
        except Exception:
            return False

    return _retry_mongo(_fn, f"update_reminder ({reminder_id})", default=False)

def delete_reminder(reminder_id):
    """Eslatma o'chirish."""
    from bson import ObjectId
    def _fn():
        try:
            reminders_col.delete_one({"_id": ObjectId(reminder_id)})
            return True
        except Exception:
            return False

    return _retry_mongo(_fn, f"delete_reminder ({reminder_id})", default=False)

def list_pending_reminders_all():
    """Server restart'da qayta rejalash uchun — barcha pending eslatmalar."""
    def _fn():
        docs = list(reminders_col.find({"status": "pending"}))
        for d in docs:
            d["_id"] = str(d["_id"])
        return docs

    return _retry_mongo(_fn, "list_pending_reminders_all", default=[])
