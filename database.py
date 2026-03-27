#!/usr/bin/env python3
"""
Ma'lumotlar bazasi funksiyalari
"""

import time as _cache_time
from datetime import date

from config import mongo_col, groups_col

# ============================================================
#  MA'LUMOTLAR BAZASI FUNKSIYALARI
# ============================================================
def load_user(user_id):
    uid = str(user_id)
    for _attempt in range(3):
        try:
            doc = mongo_col.find_one({"_id": uid})
            if doc:
                return {k: v for k, v in doc.items() if k != "_id"}
            return {"habits": [], "state": None, "joined_at": str(date.today())}
        except Exception as _e:
            if _attempt < 2:
                import time as _t; _t.sleep(0.5)
            else:
                print(f"[load_user] xato ({uid}): {_e}")
                return {"habits": [], "state": None, "joined_at": str(date.today())}

def save_user(user_id, udata):
    for _attempt in range(3):
        try:
            mongo_col.update_one(
                {"_id": str(user_id)},
                {"$set": udata},
                upsert=True
            )
            invalidate_users_cache()
            return
        except Exception as _e:
            if _attempt < 2:
                import time as _t; _t.sleep(0.5)
            else:
                print(f"[save_user] xato ({user_id}): {_e}")

def load_settings():
    doc = mongo_col.find_one({"_id": "_settings"})
    if doc:
        return {k: v for k, v in doc.items() if k != "_id"}
    return {}

def save_settings(settings):
    mongo_col.update_one(
        {"_id": "_settings"},
        {"$set": settings},
        upsert=True
    )

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
    users = {}
    for doc in mongo_col.find({"_id": {"$not": {"$regex": "^_"}}}):
        uid = doc["_id"]
        users[uid] = {k: v for k, v in doc.items() if k != "_id"}
    _all_users_cache      = users
    _all_users_cache_time = now
    return users

def user_exists(user_id):
    uid = str(user_id)
    for _attempt in range(3):
        try:
            return mongo_col.find_one({"_id": uid}) is not None
        except Exception as _e:
            if _attempt < 2:
                import time as _t; _t.sleep(0.5)
            else:
                print(f"[user_exists] xato ({uid}): {_e}")
                return False

def count_users():
    return mongo_col.count_documents({"_id": {"$not": {"$regex": "^_"}}})

def load_group(group_id):
    doc = groups_col.find_one({"_id": str(group_id)})
    if doc:
        return {k: v for k, v in doc.items() if k != "_id"}
    return None

def save_group(group_id, gdata):
    groups_col.update_one(
        {"_id": str(group_id)},
        {"$set": gdata},
        upsert=True
    )

def delete_group(group_id):
    groups_col.delete_one({"_id": str(group_id)})
