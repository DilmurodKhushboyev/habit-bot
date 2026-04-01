#!/usr/bin/env python3
"""
Ma'lumotlar bazasi funksiyalari
"""

import time as _cache_time
from datetime import date

from config import mongo_col, groups_col

# ── Exponential backoff retry yordamchi ──────────────────────
# 3 urinish: 0.5s → 1s → crash + log
_RETRY_DELAYS = [0.5, 1.0]

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
