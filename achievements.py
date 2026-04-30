#!/usr/bin/env python3
"""
Yutuqlar (achievements) tizimi
"""

from database import load_user, save_user
from bot_setup import bot, ok_kb
from helpers import T, today_uz5


# Top-level achievements (bot callback'dan ham chaqirish uchun)
# desc: 3 tilli dict — yutuq nima uchun olinganini tasvirlaydi
_ACHIEVEMENTS = [
    {"id":"streak_3",   "cat":"streak",  "icon":"🔥", "title":"Ilk olov",        "req":3,    "field":"streak",
     "desc":{"uz":"3 kun ketma-ket bajardingiz",        "ru":"Выполнили 3 дня подряд",         "en":"Completed 3 days in a row"}},
    {"id":"streak_7",   "cat":"streak",  "icon":"🌟", "title":"Haftalik qahramon","req":7,    "field":"streak",
     "desc":{"uz":"7 kun ketma-ket bajardingiz",        "ru":"Выполнили 7 дней подряд",        "en":"Completed 7 days in a row"}},
    {"id":"streak_30",  "cat":"streak",  "icon":"💎", "title":"Oylik ustoz",      "req":30,   "field":"streak",
     "desc":{"uz":"30 kun ketma-ket bajardingiz",       "ru":"Выполнили 30 дней подряд",       "en":"Completed 30 days in a row"}},
    {"id":"streak_100", "cat":"streak",  "icon":"👑", "title":"100 kun shohi",    "req":100,  "field":"streak",
     "desc":{"uz":"100 kun ketma-ket bajardingiz",      "ru":"Выполнили 100 дней подряд",      "en":"Completed 100 days in a row"}},
    {"id":"pts_100",    "cat":"ball",    "icon":"⭐", "title":"Birinchi yulduz",  "req":100,  "field":"points",
     "desc":{"uz":"100 ball to'pladingiz",              "ru":"Набрали 100 очков",              "en":"Earned 100 points"}},
    {"id":"pts_500",    "cat":"ball",    "icon":"🌠", "title":"Yulduz yomg'iri",  "req":500,  "field":"points",
     "desc":{"uz":"500 ball to'pladingiz",              "ru":"Набрали 500 очков",              "en":"Earned 500 points"}},
    {"id":"pts_1000",   "cat":"ball",    "icon":"🏆", "title":"Ming ball",        "req":1000, "field":"points",
     "desc":{"uz":"1000 ball to'pladingiz",             "ru":"Набрали 1000 очков",             "en":"Earned 1000 points"}},
    {"id":"pts_5000",   "cat":"ball",    "icon":"💰", "title":"Ball millioneri",  "req":5000, "field":"points",
     "desc":{"uz":"5000 ball to'pladingiz",             "ru":"Набрали 5000 очков",             "en":"Earned 5000 points"}},
    {"id":"hab_1",      "cat":"odat",    "icon":"🌱", "title":"Birinchi qadam",   "req":1,    "field":"habits_count",
     "desc":{"uz":"Birinchi odatingizni yaratdingiz",   "ru":"Создали первую привычку",        "en":"Created your first habit"}},
    {"id":"hab_5",      "cat":"odat",    "icon":"🌿", "title":"To'plam",          "req":5,    "field":"habits_count",
     "desc":{"uz":"5 ta odat yaratdingiz",              "ru":"Создали 5 привычек",             "en":"Created 5 habits"}},
    {"id":"hab_10",     "cat":"odat",    "icon":"🌳", "title":"Bog'bon",          "req":10,   "field":"habits_count",
     "desc":{"uz":"10 ta odat yaratdingiz",             "ru":"Создали 10 привычек",            "en":"Created 10 habits"}},
    {"id":"done_10",    "cat":"faollik", "icon":"✅", "title":"O'n marta",        "req":10,   "field":"total_done",
     "desc":{"uz":"10 marta odat bajardingiz",          "ru":"Выполнили привычку 10 раз",      "en":"Completed habits 10 times"}},
    {"id":"done_50",    "cat":"faollik", "icon":"🎯", "title":"Ellik marta",      "req":50,   "field":"total_done",
     "desc":{"uz":"50 marta odat bajardingiz",          "ru":"Выполнили привычку 50 раз",      "en":"Completed habits 50 times"}},
    {"id":"done_100",   "cat":"faollik", "icon":"🚀", "title":"Yuz marta",        "req":100,  "field":"total_done",
     "desc":{"uz":"100 marta odat bajardingiz",         "ru":"Выполнили привычку 100 раз",     "en":"Completed habits 100 times"}},
    {"id":"done_500",   "cat":"faollik", "icon":"⚡", "title":"Besh yuz",         "req":500,  "field":"total_done",
     "desc":{"uz":"500 marta odat bajardingiz",         "ru":"Выполнили привычку 500 раз",     "en":"Completed habits 500 times"}},
    {"id":"friend_1",   "cat":"ijtimoiy","icon":"🤝", "title":"Birinchi do'st",   "req":1,    "field":"friends_count",
     "desc":{"uz":"Birinchi do'st qo'shdingiz",         "ru":"Добавили первого друга",         "en":"Added your first friend"}},
    {"id":"friend_5",   "cat":"ijtimoiy","icon":"👥", "title":"Jamoatchi",        "req":5,    "field":"friends_count",
     "desc":{"uz":"5 ta do'st qo'shdingiz",             "ru":"Добавили 5 друзей",              "en":"Added 5 friends"}},
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
