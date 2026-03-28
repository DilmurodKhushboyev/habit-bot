#!/usr/bin/env python3
"""
Flask API extra routes: achievements, shop, friends, challenges, webhook
"""

import os
import io
import json
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, date, timedelta, timezone
from flask import jsonify, request

from config import BOT_TOKEN, ADMIN_ID, mongo_db
from database import (load_user, save_user, load_all_users, count_users,
                      load_group, save_group, user_exists)
from helpers import T, get_lang, get_rank, today_uz5
from texts import LANGS
from bot_setup import bot, get_bot_username, _share_file_ids
from achievements import _ACHIEVEMENTS as ACHIEVEMENTS, check_achievements_toplevel
from flask_helpers import (require_auth, rate_limit_check, _tz_today,
                           _is_done_today, _calc_best_streak)

# Achievements kategoriya nomlari (3 tilda)
CAT_LABELS = {
    "streak":   {"uz": "Streak",    "ru": "Стрик",      "en": "Streak"},
    "ball":     {"uz": "Ballar",    "ru": "Очки",       "en": "Points"},
    "odat":     {"uz": "Odatlar",   "ru": "Привычки",   "en": "Habits"},
    "faollik":  {"uz": "Faollik",   "ru": "Активность", "en": "Activity"},
    "ijtimoiy": {"uz": "Ijtimoiy",  "ru": "Социальное", "en": "Social"},
}


def register_extra_routes(app):

    @app.route("/api/achievements/<int:uid>")
    @require_auth
    def api_achievements(uid):
        u    = load_user(uid)
        lang = u.get("lang", "uz")
        earned_ids = {a["id"] for a in u.get("achievements", []) if isinstance(a, dict)}
        streak      = u.get("streak", 0)
        points      = u.get("points", 0)
        habits      = u.get("habits", [])
        total_done  = sum(h.get("total_done", 0) for h in habits)
        friends_cnt = len(u.get("friends", []))
        habits_cnt  = len(habits)
        field_vals  = {
            "streak":       streak,
            "points":       points,
            "habits_count": habits_cnt,
            "total_done":   total_done,
            "friends_count":friends_cnt,
        }
        result = []
        cats_seen = {}
        for ach in ACHIEVEMENTS:
            earned = ach["id"] in earned_ids
            current = min(field_vals.get(ach["field"], 0), ach["req"])
            cat_id  = ach["cat"]
            if cat_id not in cats_seen:
                label = CAT_LABELS.get(cat_id, {}).get(lang, cat_id)
                cats_seen[cat_id] = {"id": cat_id, "label": label}
            result.append({
                "id":      ach["id"],
                "cat":     cat_id,
                "icon":    ach["icon"],
                "title":   ach["title"],
                "desc":    ach["desc"],
                "req":     ach["req"],
                "current": current,
                "earned":  1 if earned else 0,
            })
        earned_count = sum(1 for a in result if a["earned"])
        return jsonify({
            "achievements": result,
            "cats":         list(cats_seen.values()),
            "earned_count": earned_count,
            "total_count":  len(result),
        })

    @app.route("/api/shop/<int:uid>")
    @require_auth
    def api_shop(uid):
        u = load_user(uid)
        lang = get_lang(uid)
        _shop_i18n = {
            "shield_1":   {"uz":("Streak himoyasi","1 kunlik streak himoyasi"), "ru":("Защита стрика","1 день защиты стрика"), "en":("Streak shield","1 day streak protection")},
            "shield_3":   {"uz":("3x Streak freeze","3 kunlik streak himoyasi"), "ru":("3x Заморозка стрика","3 дня защиты стрика"), "en":("3x Streak freeze","3 days streak protection")},
            "bonus_2x":   {"uz":("2x Ball bonus","1 kun uchun 2x ball"), "ru":("2x Бонус очков","2x очков на 1 день"), "en":("2x Points bonus","2x points for 1 day")},
            "bonus_3x":   {"uz":("3x Ball bonus","1 kun uchun 3x ball"), "ru":("3x Бонус очков","3x очков на 1 день"), "en":("3x Points bonus","3x points for 1 day")},
            "xp_booster": {"uz":("XP Booster","7 kun davomida +10% qo'shimcha ball"), "ru":("XP Бустер","7 дней +10% дополнительных очков"), "en":("XP Booster","7 days +10% extra points")},
            "badge_fire": {"uz":("Olov badge","Profilda ko'rsatiladi"), "ru":("Значок Огонь","Показывается в профиле"), "en":("Fire badge","Shows on profile")},
            "badge_star": {"uz":("Yulduz badge","Profilda ko'rsatiladi"), "ru":("Значок Звезда","Показывается в профиле"), "en":("Star badge","Shows on profile")},
            "badge_secret":{"uz":("Maxfiy badge","Noyob toj — faqat bozordan"), "ru":("Секретный значок","Редкая корона — только из магазина"), "en":("Secret badge","Rare crown — shop exclusive")},
            "pet_cat":    {"uz":("Mushuk","Sevimli mushukcha"), "ru":("Кошка","Милый котёнок"), "en":("Cat","Cute kitty")},
            "pet_dog":    {"uz":("It","Sodiq do'st"), "ru":("Собака","Верный друг"), "en":("Dog","Loyal friend")},
            "pet_rabbit": {"uz":("Quyon","Tez-tez sakrashi"), "ru":("Кролик","Часто прыгает"), "en":("Rabbit","Hops around")},
            "car_sport":  {"uz":("Sport mashina","Tez mashina"), "ru":("Спорткар","Быстрая машина"), "en":("Sports car","Fast car")},
            "jon_restore":{"uz":("Jon tiklash","Jonni 100% ga tiklash (faqat 20% va kam holda)"), "ru":("Восстановить жизнь","Восстановить до 100% (только при 20% и ниже)"), "en":("Restore life","Restore to 100% (only at 20% or below)")},
            "gift_box":   {"uz":("Sovga qutisi","Tasodifiy mukofot"), "ru":("Подарочная коробка","Случайная награда"), "en":("Gift box","Random reward")},
        }
        shop_items = [
            {"id": "shield_1",    "cat": "protection", "emoji": "\U0001f6e1",  "price_ball": 100,  "price_stars": 0},
            {"id": "shield_3",    "cat": "protection", "emoji": "\U0001f9ca",  "price_ball": 250,  "price_stars": 0},
            {"id": "bonus_2x",    "cat": "bonus",      "emoji": "\u26a1",  "price_ball": 150,  "price_stars": 0},
            {"id": "bonus_3x",    "cat": "bonus",      "emoji": "\U0001f680",  "price_ball": 300,  "price_stars": 0},
            {"id": "xp_booster",  "cat": "bonus",      "emoji": "\U0001f48e",  "price_ball": 400,  "price_stars": 0},
            {"id": "badge_fire",  "cat": "badge",      "emoji": "\U0001f525",  "price_ball": 200,  "price_stars": 0},
            {"id": "badge_star",  "cat": "badge",      "emoji": "\u2b50",  "price_ball": 250,  "price_stars": 0},
            {"id": "badge_secret","cat": "badge",      "emoji": "\U0001f451",  "price_ball": 600,  "price_stars": 0},
            {"id": "pet_cat",     "cat": "pet",        "emoji": "\U0001f431",  "price_ball": 300,  "price_stars": 0},
            {"id": "pet_dog",     "cat": "pet",        "emoji": "\U0001f436",  "price_ball": 350,  "price_stars": 0},
            {"id": "pet_rabbit",  "cat": "pet",        "emoji": "\U0001f430",  "price_ball": 300,  "price_stars": 0},
            {"id": "car_sport",   "cat": "car",        "emoji": "\U0001f3ce\ufe0f", "price_ball": 500,  "price_stars": 0},
            {"id": "jon_restore", "cat": "bonus",      "emoji": "\u2764\ufe0f", "price_ball": 25,   "price_stars": 0},
            {"id": "gift_box",    "cat": "gift",       "emoji": "\U0001f381",  "price_ball": 0,    "price_stars": 5},
        ]
        for item in shop_items:
            tr = _shop_i18n.get(item["id"], {}).get(lang, _shop_i18n.get(item["id"], {}).get("uz", ("",""))  )
            item["name"] = tr[0]
            item["desc"] = tr[1]
        raw_inventory = u.get("inventory", [])
        # inventory: list -> dict formatiga
        if isinstance(raw_inventory, list):
            inventory = {item_id: 1 for item_id in raw_inventory}
        else:
            inventory = raw_inventory
        active_pet   = u.get("active_pet", "")
        active_badge = u.get("active_badge", "")
        active_car   = u.get("active_car", "")
        # can_buy va owned fieldlarini har bir item ga qo'shish
        one_time = ["badge_fire","badge_star","badge_secret","pet_cat","pet_dog","pet_rabbit","car_sport"]
        # Counter fieldlardan owned miqdorini to'ldirish
        _counter_owned = {
            "shield_1":  u.get("streak_shields", 0),
            "shield_3":  u.get("streak_shields", 0) // 3,
            "bonus_2x":  1 if (u.get("bonus_2x_active") and u.get("bonus_2x_date") == today_uz5()) else 0,
            "bonus_3x":  1 if (u.get("bonus_3x_active") and u.get("bonus_3x_date") == today_uz5()) else 0,
            "xp_booster": u.get("xp_booster_days", 0),
        }
        for item in shop_items:
            if item["id"] in _counter_owned:
                owned_qty = _counter_owned[item["id"]]
            else:
                owned_qty = inventory.get(item["id"], 0)
            item["owned"] = owned_qty
            # Bir martalik narsalar: allaqachon olingan bo'lsa can_buy=False
            if item["id"] in one_time:
                item["can_buy"] = owned_qty == 0
            else:
                item["can_buy"] = True
        return jsonify({
            "points":       u.get("points", 0),
            "items":        shop_items,
            "inventory":    inventory,
            "active_pet":   active_pet,
            "active_badge": active_badge,
            "active_car":   active_car,
        })

    @app.route("/api/shop/<int:uid>/buy", methods=["POST"])
    @require_auth
    def api_shop_buy(uid):
        data = request.get_json() or {}
        item_id   = data.get("item_id", "")
        pay_type  = data.get("type", "ball")  # "ball" yoki "stars"
        prices = {
            "shield_1": 100, "shield_3": 250,
            "bonus_2x": 150, "bonus_3x": 300, "xp_booster": 400,
            "badge_fire": 200, "badge_star": 250, "badge_secret": 600,
            "pet_cat": 300, "pet_dog": 350, "pet_rabbit": 300, "car_sport": 500,
            "jon_restore": 25,
        }
        price = prices.get(item_id, 0)
        if not price and item_id != "gift_box":
            return jsonify({"ok": False, "error": "Noma'lum mahsulot"})
        u = load_user(uid)
        raw_inv = u.get("inventory", [])
        if isinstance(raw_inv, list):
            inventory = {i: 1 for i in raw_inv}
        else:
            inventory = raw_inv
        # Faqat badge/pet/car bir marta sotib olinadi
        one_time = ["badge_fire","badge_star","badge_secret","pet_cat","pet_dog","pet_rabbit","car_sport"]
        if item_id in one_time and inventory.get(item_id, 0) > 0:
            return jsonify({"ok": False, "error": "Allaqachon sotib olingan"})
        if item_id == "jon_restore":
            jon_val = round(u.get("jon", 100.0))
            if jon_val > 20:
                return jsonify({"ok": False, "error": f"Jon faqat 20% va undan kam bo'lganda tiklanadi. Hozir: {jon_val}%"})
            if u.get("points", 0) < 25:
                return jsonify({"ok": False, "error": "Ball yetarli emas"})
            u["points"] = u.get("points", 0) - 25
            u["jon"] = 100.0
            save_user(uid, u)
            return jsonify({"ok": True, "points": u["points"]})
        if item_id == "shield_1":
            if u.get("points", 0) < 100:
                return jsonify({"ok": False, "error": "Ball yetarli emas"})
            u["points"] = u.get("points", 0) - 100
            u["streak_shields"] = u.get("streak_shields", 0) + 1
            save_user(uid, u)
            return jsonify({"ok": True, "points": u["points"], "streak_shields": u["streak_shields"]})
        if item_id == "shield_3":
            if u.get("points", 0) < 250:
                return jsonify({"ok": False, "error": "Ball yetarli emas"})
            u["points"] = u.get("points", 0) - 250
            u["streak_shields"] = u.get("streak_shields", 0) + 3
            save_user(uid, u)
            return jsonify({"ok": True, "points": u["points"], "streak_shields": u["streak_shields"]})
        if item_id == "bonus_2x":
            if u.get("points", 0) < 150:
                return jsonify({"ok": False, "error": "Ball yetarli emas"})
            if u.get("bonus_2x_active") and u.get("bonus_2x_date") == today_uz5():
                return jsonify({"ok": False, "error": "Bugun 2x bonus allaqachon aktiv"})
            u["points"] = u.get("points", 0) - 150
            u["bonus_2x_active"] = True
            u["bonus_2x_date"] = today_uz5()
            save_user(uid, u)
            return jsonify({"ok": True, "points": u["points"]})
        if item_id == "bonus_3x":
            if u.get("points", 0) < 300:
                return jsonify({"ok": False, "error": "Ball yetarli emas"})
            if u.get("bonus_3x_active") and u.get("bonus_3x_date") == today_uz5():
                return jsonify({"ok": False, "error": "Bugun 3x bonus allaqachon aktiv"})
            u["points"] = u.get("points", 0) - 300
            u["bonus_3x_active"] = True
            u["bonus_3x_date"] = today_uz5()
            save_user(uid, u)
            return jsonify({"ok": True, "points": u["points"]})
        if item_id == "xp_booster":
            if u.get("points", 0) < 400:
                return jsonify({"ok": False, "error": "Ball yetarli emas"})
            u["points"] = u.get("points", 0) - 400
            u["xp_booster_days"] = u.get("xp_booster_days", 0) + 7
            save_user(uid, u)
            return jsonify({"ok": True, "points": u["points"], "xp_booster_days": u["xp_booster_days"]})
        if item_id == "gift_box":
            return jsonify({"ok": False, "error": "gift_box faqat Telegram Stars bilan sotib olinadi"})
        if pay_type == "ball":
            if u.get("points", 0) < price:
                return jsonify({"ok": False, "error": "Ball yetarli emas"})
            u["points"] = u.get("points", 0) - price
        inventory[item_id] = inventory.get(item_id, 0) + 1
        u["inventory"] = inventory
        save_user(uid, u)
        return jsonify({"ok": True, "points": u.get("points", 0)})

    @app.route("/api/shop/<int:uid>/stars_invoice", methods=["POST"])
    @require_auth
    def api_shop_stars_invoice(uid):
        data    = request.get_json(force=True, silent=True) or {}
        item_id = data.get("item_id", "")
        stars_prices = {"gift_box": 5}
        price = stars_prices.get(item_id)
        if not price:
            return jsonify({"ok": False, "error": "Stars bilan sotib bo'lmaydigan mahsulot"})
        item_names = {"gift_box": "Sovga qutisi"}
        item_descs = {"gift_box": "Tasodifiy mukofot: ball, streak himoya yoki XP booster"}
        try:
            from telebot.types import LabeledPrice as _LP
            bot.send_invoice(
                chat_id=uid,
                title=item_names.get(item_id, item_id),
                description=item_descs.get(item_id, ""),
                invoice_payload=f"stars_{item_id}",
                provider_token="",
                currency="XTR",
                prices=[_LP(item_names.get(item_id, item_id), price)],
            )
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)})

    @app.route("/api/shop/<int:uid>/activate", methods=["POST"])
    @require_auth
    def api_shop_activate(uid):
        data = request.get_json() or {}
        item_id  = data.get("item_id", "")
        deactive = data.get("deactivate", False)
        u = load_user(uid)
        if item_id.startswith("pet_"):
            u["active_pet"]   = "" if deactive else item_id
        elif item_id.startswith("badge_"):
            u["active_badge"] = "" if deactive else item_id
        elif item_id.startswith("car_"):
            u["active_car"]   = "" if deactive else item_id
        save_user(uid, u)
        return jsonify({"ok": True})

    @app.route("/api/shop/<int:uid>/sell", methods=["POST"])
    @require_auth
    def api_shop_sell(uid):
        """Inventardagi narsani 50% narxiga sotish."""
        data    = request.get_json() or {}
        item_id = data.get("item_id", "")
        # Sotish narxlari (asl narxning 50%)
        sell_prices = {
            "badge_fire":   100, "badge_star":  125, "badge_secret": 300,
            "pet_cat":      150, "pet_dog":     175, "pet_rabbit":   150,
            "car_sport":    250,
            "shield_1":      50, "shield_3":    125,
            "bonus_2x":      75, "bonus_3x":    150,
            "xp_booster":   200,
        }
        refund = sell_prices.get(item_id)
        if refund is None:
            return jsonify({"ok": False, "error": "Bu narsa sotilmaydi"})
        u = load_user(uid)
        today = today_uz5()
        # Counter fieldlar uchun alohida tekshirish
        if item_id in ("shield_1", "shield_3"):
            raw_inv_s = u.get("inventory", [])
            inv_s = {i: 1 for i in raw_inv_s} if isinstance(raw_inv_s, list) else dict(raw_inv_s)
            shields = u.get("streak_shields", 0)
            in_inv  = inv_s.get(item_id, 0) >= 1
            if shields < 1 and not in_inv:
                return jsonify({"ok": False, "error": "Inventarda topilmadi"})
            if shields >= 1:
                sell_qty = 3 if item_id == "shield_3" else 1
                if item_id == "shield_3" and shields < 3:
                    return jsonify({"ok": False, "error": "shield_3 sotish uchun kamida 3 ta shield kerak"})
                actual_refund = refund
                u["streak_shields"] = max(0, shields - sell_qty)
            else:
                actual_refund = refund
                inv_s[item_id] = inv_s.get(item_id, 0) - 1
                if inv_s[item_id] <= 0:
                    del inv_s[item_id]
                u["inventory"] = inv_s
            u["points"] = u.get("points", 0) + actual_refund
            save_user(uid, u)
            return jsonify({"ok": True, "points": u["points"], "refund": actual_refund})
        if item_id == "bonus_2x":
            if not (u.get("bonus_2x_active") and u.get("bonus_2x_date") == today):
                return jsonify({"ok": False, "error": "Aktiv bonus topilmadi"})
            u["bonus_2x_active"] = False
            u["points"] = u.get("points", 0) + refund
            save_user(uid, u)
            return jsonify({"ok": True, "points": u["points"], "refund": refund})
        if item_id == "bonus_3x":
            if not (u.get("bonus_3x_active") and u.get("bonus_3x_date") == today):
                return jsonify({"ok": False, "error": "Aktiv bonus topilmadi"})
            u["bonus_3x_active"] = False
            u["points"] = u.get("points", 0) + refund
            save_user(uid, u)
            return jsonify({"ok": True, "points": u["points"], "refund": refund})
        if item_id == "xp_booster":
            if u.get("xp_booster_days", 0) < 1:
                return jsonify({"ok": False, "error": "Inventarda topilmadi"})
            days_left = u["xp_booster_days"]
            actual_refund = round(refund * days_left / 7)
            u["xp_booster_days"] = 0
            u["points"] = u.get("points", 0) + actual_refund
            save_user(uid, u)
            return jsonify({"ok": True, "points": u["points"], "refund": actual_refund})
        # Inventory narsalar (badge/pet/car)
        raw_inv = u.get("inventory", [])
        if isinstance(raw_inv, list):
            inventory = {i: 1 for i in raw_inv}
        else:
            inventory = dict(raw_inv)
        if inventory.get(item_id, 0) < 1:
            return jsonify({"ok": False, "error": "Inventarda topilmadi"})
        inventory[item_id] = inventory.get(item_id, 0) - 1
        if inventory[item_id] <= 0:
            del inventory[item_id]
        u["inventory"] = inventory
        if item_id.startswith("pet_")   and u.get("active_pet")   == item_id:
            u["active_pet"]   = ""
        if item_id.startswith("badge_") and u.get("active_badge") == item_id:
            u["active_badge"] = ""
        if item_id.startswith("car_")   and u.get("active_car")   == item_id:
            u["active_car"]   = ""
        u["points"] = u.get("points", 0) + refund
        save_user(uid, u)
        return jsonify({"ok": True, "points": u["points"], "refund": refund})

    @app.route("/api/friends/<int:uid>")
    @require_auth
    def api_friends(uid):
        u = load_user(uid)
        friends_ids = u.get("friends", [])
        today = today_uz5()
        friends = []
        for fid in friends_ids[:20]:
            fu = load_user(fid)
            if fu:
                # done_today: bugun kamida bitta odat bajarilganmi
                fhabits = fu.get("habits", [])
                f_done_today = any(h.get("last_done") == today for h in fhabits)
                friends.append({
                    "id":           fid,
                    "name":         fu.get("name", "?"),
                    "points":       fu.get("points", 0),
                    "streak":       fu.get("streak", 0),
                    "photo":        fu.get("photo_url", ""),
                    "done_today":   f_done_today,
                    "mutual_streak": min(u.get("streak", 0), fu.get("streak", 0)),
                })
        # Invite link
        invite_link = f"https://t.me/{get_bot_username()}?start=ref_{uid}"
        return jsonify({"friends": friends, "invite_link": invite_link})

    @app.route("/api/friends/<int:uid>/search")
    @require_auth
    def api_friends_search(uid):
        q = (request.args.get("q") or "").strip().lower().lstrip("@")
        if len(q) < 2:
            return jsonify({"ok": False, "error": "Kamida 2 harf kiriting"}), 400
        u = load_user(uid)
        my_friends = set(str(f) for f in u.get("friends", []))
        results = []
        all_users = load_all_users()
        for fid_str, udata in all_users.items():
            if str(fid_str) == str(uid):
                continue
            uname = (udata.get("username") or "").lower()
            uname_display = (udata.get("name") or "").lower()
            if q in uname or q in uname_display:
                results.append({
                    "id":        int(fid_str),
                    "name":      udata.get("name", "?"),
                    "username":  udata.get("username", ""),
                    "points":    udata.get("points", 0),
                    "streak":    udata.get("streak", 0),
                    "photo":     udata.get("photo_url", ""),
                    "is_friend": fid_str in my_friends,
                })
            if len(results) >= 10:
                break
        return jsonify({"results": results})

    @app.route("/api/friends/<int:uid>/add/<int:fid>", methods=["POST"])
    @require_auth
    def api_friends_add(uid, fid):
        if uid == fid:
            return jsonify({"ok": False, "error": "O'zingizni qo'sha olmaysiz"}), 400
        u = load_user(uid)
        friends = u.get("friends", [])
        if fid not in friends:
            if len(friends) >= 50:
                return jsonify({"ok": False, "error": "Do'stlar limiti 50 ta"}), 400
            friends.append(fid)
            u["friends"] = friends
            save_user(uid, u)
        # Ikkinchi tomon: fid ning ro'yxatiga ham uid ni qo'shish
        f = load_user(fid)
        if f:
            f_friends = f.get("friends", [])
            if uid not in f_friends and len(f_friends) < 50:
                f_friends.append(uid)
                f["friends"] = f_friends
                save_user(fid, f)
        return jsonify({"ok": True})

    @app.route("/api/friends/<int:uid>/remove/<int:fid>", methods=["DELETE"])
    @require_auth
    def api_friends_remove(uid, fid):
        u = load_user(uid)
        friends = u.get("friends", [])
        if fid in friends:
            friends.remove(fid)
            u["friends"] = friends
            save_user(uid, u)
        # Ikkinchi tomon: fid ning ro'yxatidan ham uid ni o'chirish
        f = load_user(fid)
        if f:
            f_friends = f.get("friends", [])
            if uid in f_friends:
                f_friends.remove(uid)
                f["friends"] = f_friends
                save_user(fid, f)
        return jsonify({"ok": True})

    @app.route("/api/challenges/<int:uid>")
    @require_auth
    def api_challenges(uid):
        challenges_col = mongo_db["challenges"]
        sent = list(challenges_col.find({"from_uid": str(uid)}))
        recv = list(challenges_col.find({"to_uid":   str(uid), "status": "pending"}))
        def fmt(c):
            from_uid_str = c.get("from_uid", "")
            try:
                fu = load_user(int(from_uid_str)) if from_uid_str else {}
                from_name = fu.get("name", "?") if fu else "?"
            except Exception:
                from_name = "?"
            return {
                "id":          str(c.get("_id","")),
                "habit_name":  c.get("habit_name",""),
                "from_uid":    from_uid_str,
                "from_name":   from_name,
                "to_uid":      c.get("to_uid",""),
                "status":      c.get("status","pending"),
                "days":        c.get("days", 7),
                "bet":         c.get("bet", 50),
                "expires_at":  c.get("expires_at",""),
                "created_at":  c.get("created_at",""),
            }
        return jsonify({"sent": [fmt(c) for c in sent], "received": [fmt(c) for c in recv]})

    @app.route("/api/challenges/<int:uid>/send", methods=["POST"])
    @require_auth
    def api_challenges_send(uid):
        data        = request.get_json(force=True, silent=True) or {}
        receiver_id = data.get("receiver_id")
        habit_name  = (data.get("habit_name") or "").strip()
        try:
            days = int(data.get("days") or 7)
        except (ValueError, TypeError):
            days = 7
        try:
            bet = int(data.get("bet") or 50)
        except (ValueError, TypeError):
            bet = 50
        # Validatsiya
        if not habit_name:
            return jsonify({"ok": False, "error": "Odat nomi kerak"})
        if len(habit_name) > 100:
            return jsonify({"ok": False, "error": "Odat nomi 100 belgidan oshmasin"})
        if not receiver_id:
            return jsonify({"ok": False, "error": "Qabul qiluvchi ID kerak"})
        try:
            receiver_id = int(receiver_id)
        except (ValueError, TypeError):
            return jsonify({"ok": False, "error": "Noto'g'ri ID"})
        if receiver_id == uid:
            return jsonify({"ok": False, "error": "O'zingizga challenge yubora olmaysiz"})
        if days < 1 or days > 30:
            return jsonify({"ok": False, "error": "Muddat 1 dan 30 kungacha bo'lishi kerak"})
        if bet < 10 or bet > 1000:
            return jsonify({"ok": False, "error": "Garov 10 dan 1000 ballgacha bo'lishi kerak"})
        if not user_exists(receiver_id):
            return jsonify({"ok": False, "error": "Foydalanuvchi topilmadi"})
        sender = load_user(uid)
        if sender.get("points", 0) < bet:
            return jsonify({"ok": False, "error": f"Yetarli ball yo'q (kerak: {bet})"})
        challenges_col = mongo_db["challenges"]
        existing = challenges_col.find_one({
            "from_uid": str(uid),
            "to_uid":   str(receiver_id),
            "status":   "pending"
        })
        if existing:
            return jsonify({"ok": False, "error": "Allaqachon kutilayotgan challenge bor"})
        challenges_col.insert_one({
            "from_uid":   str(uid),
            "to_uid":     str(receiver_id),
            "habit_name": habit_name,
            "days":       days,
            "bet":        bet,
            "status":     "pending",
            "created_at": today_uz5(),
            "expires_at": (datetime.now(timezone(timedelta(hours=5))) + timedelta(days=days)).strftime("%Y-%m-%d"),
        })
        try:
            sender_name = sender.get("name", "Kimdir")
            bot.send_message(
                int(receiver_id),
                f"🎯 *Challenge keldi!*\n\n"
                f"👤 *{sender_name}* sizni challenge qildi!\n"
                f"📌 Odat: *{habit_name}*\n"
                f"📅 Muddat: *{days} kun*\n"
                f"💰 Garov: *{bet} ball*\n\n"
                f"_Qabul qilish uchun botga kiring._",
                parse_mode="Markdown"
            )
        except Exception:
            pass
        return jsonify({"ok": True})

    @app.route("/api/challenges/<int:uid>/<cid>/accept", methods=["POST"])
    @require_auth
    def api_challenges_accept(uid, cid):
        from bson import ObjectId
        challenges_col = mongo_db["challenges"]
        try:
            c = challenges_col.find_one({"_id": ObjectId(cid), "to_uid": str(uid), "status": "pending"})
        except Exception:
            return jsonify({"ok": False, "error": "Topilmadi"})
        if not c:
            return jsonify({"ok": False, "error": "Challenge topilmadi yoki allaqachon ko'rib chiqilgan"})
        bet        = c.get("bet", 50)
        from_uid   = int(c.get("from_uid", 0))
        # Ikkalasidan ham garov yechish
        u_recv = load_user(uid)
        u_send = load_user(from_uid)
        if not u_recv or not u_send:
            return jsonify({"ok": False, "error": "Foydalanuvchi topilmadi"})
        if u_recv.get("points", 0) < bet:
            return jsonify({"ok": False, "error": f"Sizda yetarli ball yo'q (kerak: {bet})"})
        if u_send.get("points", 0) < bet:
            return jsonify({"ok": False, "error": "Challenger'da yetarli ball yo'q"})
        u_recv["points"] = u_recv.get("points", 0) - bet
        u_send["points"] = u_send.get("points", 0) - bet
        save_user(uid, u_recv)
        save_user(from_uid, u_send)
        challenges_col.update_one(
            {"_id": ObjectId(cid)},
            {"$set": {
                "status":      "active",
                "accepted_at": today_uz5(),
                "expires_at":  (datetime.now(timezone(timedelta(hours=5))) + timedelta(days=c.get("days", 7))).strftime("%Y-%m-%d"),
            }}
        )
        # Yuboruvchiga xabar
        try:
            recv_name = u_recv.get("name", "Raqib")
            bot.send_message(
                from_uid,
                f"✅ *Challenge qabul qilindi!*\n\n"
                f"👤 *{recv_name}* sizning challengingizni qabul qildi!\n"
                f"📌 Odat: *{c.get('habit_name','')}*\n"
                f"📅 Muddat: *{c.get('days',7)} kun*\n"
                f"💰 Garov: *{bet} ball* (ikkalangizdan)\n\n"
                f"_Omad! 💪_",
                parse_mode="Markdown"
            )
        except Exception:
            pass
        return jsonify({"ok": True, "points": u_recv.get("points", 0)})

    @app.route("/api/challenges/<int:uid>/<cid>/reject", methods=["POST"])
    @require_auth
    def api_challenges_reject(uid, cid):
        from bson import ObjectId
        challenges_col = mongo_db["challenges"]
        try:
            c = challenges_col.find_one({"_id": ObjectId(cid), "to_uid": str(uid), "status": "pending"})
        except Exception:
            return jsonify({"ok": False, "error": "Topilmadi"})
        if not c:
            return jsonify({"ok": False, "error": "Challenge topilmadi"})
        challenges_col.update_one(
            {"_id": ObjectId(cid)},
            {"$set": {"status": "rejected", "rejected_at": today_uz5()}}
        )
        # Yuboruvchiga xabar
        try:
            from_uid  = int(c.get("from_uid", 0))
            u_recv    = load_user(uid)
            recv_name = u_recv.get("name", "Raqib") if u_recv else "Raqib"
            bot.send_message(
                from_uid,
                f"❌ *Challenge rad etildi*\n\n"
                f"👤 *{recv_name}* sizning challengingizni rad etdi.\n"
                f"📌 Odat: *{c.get('habit_name','')}*",
                parse_mode="Markdown"
            )
        except Exception:
            pass
        return jsonify({"ok": True})

    @app.route("/api/reminder/<int:uid>/<hid>", methods=["PUT"])
    @require_auth
    def api_reminder(uid, hid):
        import re as _re
        data = request.get_json() or {}
        u = load_user(uid)
        habits = u.get("habits", [])
        for h in habits:
            if h["id"] == hid:
                # Asosiy vaqt
                h["time"] = data.get("time", h.get("time", ""))
                # repeat_times ro'yxati (frontend "times" sifatida yuboradi)
                raw_times = data.get("times") or data.get("repeat_times") or []
                repeat_times = []
                if isinstance(raw_times, list):
                    for rt in raw_times:
                        rt_s = str(rt).strip()
                        if rt_s and _re.match(r"^\d{2}:\d{2}$", rt_s):
                            repeat_times.append(rt_s)
                h["repeat_times"] = repeat_times
                # Birinchi vaqtni time ga sinxronlash
                if repeat_times:
                    h["time"] = repeat_times[0]
                # Eslatma yoqilgan/o'chirilgan (frontend "enabled" yuboradi)
                if "enabled" in data:
                    h["reminder_enabled"] = bool(data["enabled"])
                elif "reminder" in data:
                    h["reminder_enabled"] = bool(data["reminder"])
                # Takrorlash rejimi (daily/weekdays/weekends)
                if "repeat" in data and data["repeat"] in ("daily", "weekdays", "weekends"):
                    h["repeat"] = data["repeat"]
                break
        u["habits"] = habits
        save_user(uid, u)
        # Yangi vaqt bilan qayta rejalashtirish
        updated_h = next((h for h in habits if h.get("id") == hid), None)
        if updated_h:
            try:
                from scheduler import schedule_habit
                # Eslatma o'chirilgan bo'lsa — schedule yaratmaymiz
                if updated_h.get("reminder_enabled", True) is False:
                    import schedule as _sched
                    _sched.clear(f"{uid}_{hid}")
                else:
                    schedule_habit(uid, updated_h)
            except Exception as _e:
                print(f"[warn] schedule_habit reminder: {_e}")
        return jsonify({"ok": True})

    @app.route("/api/profile/<int:uid>", methods=["PUT"])
    @require_auth
    def api_profile_put(uid):
        data = request.get_json() or {}
        u = load_user(uid)
        # lang
        if "lang" in data:
            if data["lang"] in ("uz", "ru", "en"):
                u["lang"] = data["lang"]
        # evening_notify
        if "evening_notify" in data:
            u["evening_notify"] = bool(data["evening_notify"])
        # dark_mode
        if "dark_mode" in data:
            u["dark_mode"] = bool(data["dark_mode"])
        # photo_url (base64 data URL yoki oddiy URL)
        if "photo_url" in data:
            url = str(data["photo_url"] or "")
            if url.startswith("data:"):
                url = url[:2_000_000]   # base64 data URL uchun ~2MB limit
            else:
                url = url[:500]         # oddiy URL
            u["photo_url"] = url
        # display_name
        if "display_name" in data:
            dn = str(data["display_name"] or "").strip()[:50]
            u["display_name"] = dn
        # phone
        if "phone" in data:
            phone = str(data["phone"] or "").strip()[:20]
            u["phone"] = phone
        save_user(uid, u)
        return jsonify({"ok": True})

    @app.route("/api/share-card/<int:uid>", methods=["POST"])
    @require_auth
    def api_share_card(uid):
        """Canvas rasmni qabul qilib, Telegram chatga yuboradi."""
        try:
            if 'photo' not in request.files:
                return jsonify({"ok": False, "error": "photo not found"}), 400
            photo = request.files['photo']
            photo_bytes = io.BytesIO(photo.read())
            photo_bytes.name = "weekly.png"
            caption_text = "\U0001f4ca " + T(uid, "weekly_share_caption")
            kb = InlineKeyboardMarkup()
            kb.row(
                InlineKeyboardButton(T(uid, "share_del_btn"), callback_data="share_del")
            )
            sent = bot.send_photo(uid, photo_bytes, caption=caption_text, reply_markup=kb)
            return jsonify({"ok": True})
        except Exception as e:
            print(f"[share-card] xato: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/")
    def api_index():
        import os as _os
        html_path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "index.html")
        if _os.path.exists(html_path):
            from flask import send_file
            return send_file(html_path)
        return jsonify({"status": "ok", "bot": "Super Habits"})

    @app.route("/health")
    def api_health():
        return jsonify({"status": "ok", "bot": "Super Habits"})

    # ── Webhook endpoint (Telegram xabarlarini qabul qiladi) ──
    _WEBHOOK_PATH = "/webhook/" + BOT_TOKEN

    @app.route(_WEBHOOK_PATH, methods=["POST"])
    def telegram_webhook():
        import json as _wjson
        import threading as _thr
        from flask import request as _wreq
        if _wreq.headers.get("content-type") == "application/json":
            update = telebot.types.Update.de_json(_wjson.loads(_wreq.data))
            _thr.Thread(target=bot.process_new_updates, args=([update],), daemon=True).start()
        return "", 200

    @app.route("/setup_webhook")
    def setup_webhook():
        """Bir marta brauzerdan ochiladi — webhook o'rnatadi"""
        _base = os.environ.get("WEBAPP_URL", "").rstrip("/")
        if not _base:
            return jsonify({"ok": False, "error": "WEBAPP_URL sozlanmagan"}), 500
        _url = _base + _WEBHOOK_PATH
        try:
            bot.set_webhook(url=_url, allowed_updates=["message", "callback_query", "pre_checkout_query"])
            from telebot.types import BotCommand
            bot.set_my_commands([
                BotCommand("start",       "Botni ishga tushirish"),
                BotCommand("admin_panel", "Admin panel"),
            ])
            # Oldingi API orqali o'rnatilgan bio/tavsifni BARCHA tillar uchun tozalash
            try:
                for _lc in [None, "uz", "ru", "en"]:
                    try:
                        if _lc:
                            bot.set_my_short_description("", language_code=_lc)
                            bot.set_my_description("", language_code=_lc)
                        else:
                            bot.set_my_short_description("")
                            bot.set_my_description("")
                    except Exception:
                        pass
            except Exception:
                pass
            return jsonify({"ok": True, "webhook": _url})
        except Exception as _e:
            return jsonify({"ok": False, "error": str(_e)}), 502

