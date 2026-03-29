#!/usr/bin/env python3
"""
Yutuqlar (achievements) tizimi
"""

from database import load_user, save_user
from bot_setup import bot, ok_kb
from helpers import T, today_uz5


# Top-level achievements (bot callback'dan ham chaqirish uchun)
_ACHIEVEMENTS = [
    {"id":"streak_3",   "cat":"streak",  "icon":"🔥", "title":"Ilk olov",        "req":3,    "field":"streak"},
    {"id":"streak_7",   "cat":"streak",  "icon":"🌟", "title":"Haftalik qahramon","req":7,    "field":"streak"},
    {"id":"streak_30",  "cat":"streak",  "icon":"💎", "title":"Oylik ustoz",      "req":30,   "field":"streak"},
    {"id":"streak_100", "cat":"streak",  "icon":"👑", "title":"100 kun shohi",    "req":100,  "field":"streak"},
    {"id":"pts_100",    "cat":"ball",    "icon":"⭐", "title":"Birinchi yulduz",  "req":100,  "field":"points"},
    {"id":"pts_500",    "cat":"ball",    "icon":"🌠", "title":"Yulduz yomg'iri",  "req":500,  "field":"points"},
    {"id":"pts_1000",   "cat":"ball",    "icon":"🏆", "title":"Ming ball",        "req":1000, "field":"points"},
    {"id":"pts_5000",   "cat":"ball",    "icon":"💰", "title":"Ball millioneri",  "req":5000, "field":"points"},
    {"id":"hab_1",      "cat":"odat",    "icon":"🌱", "title":"Birinchi qadam",   "req":1,    "field":"habits_count"},
    {"id":"hab_5",      "cat":"odat",    "icon":"🌿", "title":"To'plam",          "req":5,    "field":"habits_count"},
    {"id":"hab_10",     "cat":"odat",    "icon":"🌳", "title":"Bog'bon",          "req":10,   "field":"habits_count"},
    {"id":"done_10",    "cat":"faollik", "icon":"✅", "title":"O'n marta",        "req":10,   "field":"total_done"},
    {"id":"done_50",    "cat":"faollik", "icon":"🎯", "title":"Ellik marta",      "req":50,   "field":"total_done"},
    {"id":"done_100",   "cat":"faollik", "icon":"🚀", "title":"Yuz marta",        "req":100,  "field":"total_done"},
    {"id":"done_500",   "cat":"faollik", "icon":"⚡", "title":"Besh yuz",         "req":500,  "field":"total_done"},
    {"id":"friend_1",   "cat":"ijtimoiy","icon":"🤝", "title":"Birinchi do'st",   "req":1,    "field":"friends_count"},
    {"id":"friend_5",   "cat":"ijtimoiy","icon":"👥", "title":"Jamoatchi",        "req":5,    "field":"friends_count"},
]

def check_achievements_toplevel(uid, u):
    """Bot callback'dan chaqirish uchun top-level achievements tekshiruvi."""
    earned_ids = {a["id"] for a in u.get("achievements", []) if isinstance(a, dict)}
    field_vals = {
        "streak":        u.get("streak", 0),
        "points":        u.get("points", 0),
        "habits_count":  len(u.get("habits", [])),
        "total_done":    sum(h.get("total_done", 0) for h in u.get("habits", [])),
        "friends_count": len(u.get("friends", [])),
    }
    new_ach = []
    ach_list = list(u.get("achievements", []))
    changed = False
    for ach in _ACHIEVEMENTS:
        if ach["id"] in earned_ids:
            continue
        if field_vals.get(ach["field"], 0) >= ach["req"]:
            ach_list.append({"id": ach["id"], "earned_at": today_uz5()})
            new_ach.append(ach)
            changed = True
    if changed:
        u["achievements"] = ach_list
        save_user(uid, u)
    return new_ach
