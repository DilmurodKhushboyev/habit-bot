#!/usr/bin/env python3
"""
Flask API: City (Shahar) routes — bino siljitish, dekoratsiya bozori,
bino turini o'zgartirish, Construction Insurance.

Pattern (mavjud kod bilan moslik):
- @require_auth — Telegram WebApp auth (flask_helpers)
- _get_city_lock(uid) — race condition himoyasi (shop pattern)
- add_points_history(u, delta) — har ball o'zgarishida (Qoida #26)
- 3 tilda xato xabarlari (uz/ru/en) — DRY i18n dict

Bog'liqlik: city_logic (sof funksiyalar), database (load/save user),
config (narxlar va konstantalar), flask_helpers (auth, lock).

ESLATMA: Habit checkin → bino progress yangilash bu fayda EMAS.
U PHASE A3 da callbacks_habits.py va flask_routes_data.py orqali
qo'shiladi (Qoida #10 — bot va WebApp sinxron).
"""

import threading
from flask import jsonify, request

from config import (
    SHOP_DECORATION_PRICES,
    DECORATION_TYPES,
    BUILDING_TYPES,
    INSURANCE_PRICE,
    INSURANCE_DURATION,
    CITY_GRID_SIZE,
)
from database import (
    load_user, save_user, init_city_for_user,
    get_user_city, add_points_history,
)
from city_logic import (
    create_building, change_building_type, delete_building_for_habit,
    place_decoration, delete_decoration, move_item,
    activate_insurance, get_building_stage,
    compact_buildings_to_center, backfill_buildings_from_habits,
    cleanup_orphan_buildings,
)
from flask_helpers import require_auth

# ── Race condition himoyasi (shop pattern bilan bir xil) ──
# Shop bilan alohida lock (city va shop bir vaqtda ishlasa, blok qilmaslik uchun)
_city_user_locks = {}
_city_locks_master = threading.Lock()

def _get_city_lock(uid):
    """Foydalanuvchi uchun lazy yaratiladigan lock (thread-safe).
    Shop pattern bilan mos: per-user, 3s timeout."""
    with _city_locks_master:
        lock = _city_user_locks.get(uid)
        if lock is None:
            lock = threading.Lock()
            _city_user_locks[uid] = lock
        return lock

# ── 3 tilda xato xabarlari (DRY i18n) ──
# Faqat shu fayl uchun — texts.py ga keyingi sessiyada (Qoida #22)
_CITY_ERR = {
    "unauth": {
        "uz": "Ruxsat yo'q",
        "ru": "Нет доступа",
        "en": "Unauthorized",
    },
    "busy": {
        "uz": "Server band — qaytadan urinib ko'ring",
        "ru": "Сервер занят — попробуйте снова",
        "en": "Server busy — try again",
    },
    "not_enough_points": {
        "uz": "Ball yetarli emas",
        "ru": "Недостаточно очков",
        "en": "Not enough points",
    },
    "invalid_type": {
        "uz": "Noto'g'ri tur",
        "ru": "Неверный тип",
        "en": "Invalid type",
    },
    "invalid_coord": {
        "uz": "Noto'g'ri koordinata",
        "ru": "Неверные координаты",
        "en": "Invalid coordinates",
    },
    "city_full": {
        "uz": "Shahar to'la — joy yo'q",
        "ru": "Город заполнен — нет места",
        "en": "City is full — no space",
    },
    "occupied": {
        "uz": "Bu joy band",
        "ru": "Это место занято",
        "en": "This spot is taken",
    },
    "not_found": {
        "uz": "Topilmadi",
        "ru": "Не найдено",
        "en": "Not found",
    },
    "insurance_active": {
        "uz": "Sug'urta allaqachon faol",
        "ru": "Страховка уже активна",
        "en": "Insurance already active",
    },
}

def _err(u, key, status=400):
    """Foydalanuvchining tilida xato xabarini qaytaradi."""
    lang = (u.get("lang") if isinstance(u, dict) else None) or "uz"
    msg = _CITY_ERR.get(key, {}).get(lang) or _CITY_ERR.get(key, {}).get("uz", key)
    return jsonify({"ok": False, "error": msg}), status


def register_city_routes(app):
    """City API endpointlarini Flask app'ga ro'yxatdan o'tkazadi.
    flask_api.py register_city_routes(api_app) chaqiradi."""

    # =================================================================
    #  GET /api/city/<uid>  — Shaharni qaytarish
    # =================================================================
    @app.route("/api/city/<int:uid>", methods=["GET"])
    @require_auth
    def api_city_get(uid):
        """Foydalanuvchining to'liq shaharini qaytaradi.
        Eski user'lar uchun avtomatik init qilinadi (idempotent)."""
        u = load_user(uid)
        # Eski user (city yo'q) → init va save (faqat schema yo'q bo'lsa)
        had_city = isinstance(u.get("city"), dict)
        init_city_for_user(u)
        if not had_city:
            save_user(uid, u)

        # Bir martalik migration: eski tarqoq binolarni markazga yig'ish.
        # compact_buildings_to_center idempotent — `city.compacted=True` markeri
        # qo'yiladi, keyingi GET'larda darhol chiqib ketadi. try/except — migration
        # xato bo'lsa, asosiy GET buzilmasin (city ikkilamchi feature mantig'i).
        try:
            if compact_buildings_to_center(u):
                save_user(uid, u)
        except Exception as e:
            print(f"[city] compact_buildings_to_center failed for {uid}: {e}")

        # Backfill: deploy'gacha tasdiqlangan odatlar uchun retroaktiv bino yaratish.
        # Eski user'da habits bor lekin bino yo'q (city feature keyin qo'shilgan) —
        # habit["total_done"] qiymatlariga qarab binolar yaratiladi. Idempotent —
        # bino allaqachon bor odatlarga tegmaydi. try/except: backfill xato bo'lsa
        # asosiy GET buzilmasin (compact bilan bir xil pattern).
        try:
            if backfill_buildings_from_habits(u) > 0:
                save_user(uid, u)
        except Exception as e:
            print(f"[city] backfill_buildings_from_habits failed for {uid}: {e}")

        # Cleanup: orfan binolarni (mavjud bo'lmagan odatlarga bog'langan) o'chirish.
        # Odat o'chirilganda ba'zan delete_building_for_habit chaqirilmagan
        # (masalan WebApp orqali) → shaharda bo'sh label'li binolar qoladi.
        # Idempotent — keyingi GET'larda orfan yo'q bo'lsa hech narsa qilmaydi.
        # Backfill'dan KEYIN: avval mavjud odatlar uchun bino yaratamiz, keyin
        # mavjud bo'lmagan odatlarning binolarini tozalaymiz (tartib mantiqi).
        try:
            if cleanup_orphan_buildings(u) > 0:
                save_user(uid, u)
        except Exception as e:
            print(f"[city] cleanup_orphan_buildings failed for {uid}: {e}")

        city = get_user_city(u)

        # Frontend uchun har bino'ga stage va habit_name qo'shamiz.
        # habit_name: bino ustida label ko'rsatish uchun (qaysi bino qaysi
        # odatniki). habit_id → name lug'ati u["habits"] dan tuziladi.
        # Odat o'chirilgan bo'lsa (orfan bino) — bo'sh string.
        habit_names = {
            str(h.get("id")): h.get("name", "")
            for h in u.get("habits", [])
        }
        buildings = []
        for b in city.get("buildings", []):
            buildings.append({
                **b,
                "stage": get_building_stage(b.get("progress", 0)),
                "habit_name": habit_names.get(str(b.get("habit_id")), ""),
            })

        return jsonify({
            "ok": True,
            "grid_size": CITY_GRID_SIZE,
            "buildings": buildings,
            "decorations": city.get("decorations", []),
            "insurance_active": bool(city.get("insurance_active")),
            "insurance_until": city.get("insurance_until"),
            "version": city.get("version", 1),
        })

    # =================================================================
    #  POST /api/city/<uid>/move  — Bino/dekoratsiyani siljitish
    # =================================================================
    @app.route("/api/city/<int:uid>/move", methods=["POST"])
    @require_auth
    def api_city_move(uid):
        """item_id ni (x, y) ga ko'chiradi.
        Body: {"item_id": "bld_xxx", "x": 5, "y": 7}"""
        data = request.get_json(silent=True) or {}
        item_id = str(data.get("item_id", "")).strip()
        try:
            x = int(data.get("x"))
            y = int(data.get("y"))
        except (TypeError, ValueError):
            u_tmp = load_user(uid)
            return _err(u_tmp, "invalid_coord")

        if not item_id:
            u_tmp = load_user(uid)
            return _err(u_tmp, "not_found", 404)

        if not (0 <= x < CITY_GRID_SIZE and 0 <= y < CITY_GRID_SIZE):
            u_tmp = load_user(uid)
            return _err(u_tmp, "invalid_coord")

        _lock = _get_city_lock(uid)
        if not _lock.acquire(timeout=3):
            u_tmp = load_user(uid)
            return _err(u_tmp, "busy", 429)
        try:
            u = load_user(uid)
            init_city_for_user(u)
            ok = move_item(u, item_id, x, y)
            if not ok:
                # False — band yoki topilmadi (city_logic ikki holatni ham qaytaradi)
                # Foydalanuvchi tushuntirish uchun "occupied" qaytaramiz
                # (band holat ko'proq sodir bo'ladi UX nuqtai nazaridan)
                return _err(u, "occupied")
            save_user(uid, u)
            return jsonify({"ok": True, "x": x, "y": y})
        finally:
            _lock.release()

    # =================================================================
    #  POST /api/city/<uid>/change_type  — Bino turini o'zgartirish
    # =================================================================
    @app.route("/api/city/<int:uid>/change_type", methods=["POST"])
    @require_auth
    def api_city_change_type(uid):
        """Bino turini o'zgartirish (foydalanuvchi qiziquvchi bo'lsa,
        shahar sahifasidan tanlaydi — Qoida #5 javob: B varianti).
        Body: {"habit_id": "...", "building_type": "stadium"}"""
        data = request.get_json(silent=True) or {}
        habit_id = str(data.get("habit_id", "")).strip()
        new_type = str(data.get("building_type", "")).strip()

        if new_type not in BUILDING_TYPES:
            u_tmp = load_user(uid)
            return _err(u_tmp, "invalid_type")
        if not habit_id:
            u_tmp = load_user(uid)
            return _err(u_tmp, "not_found", 404)

        _lock = _get_city_lock(uid)
        if not _lock.acquire(timeout=3):
            u_tmp = load_user(uid)
            return _err(u_tmp, "busy", 429)
        try:
            u = load_user(uid)
            init_city_for_user(u)
            result = change_building_type(u, habit_id, new_type)
            if result is None:
                return _err(u, "not_found", 404)
            save_user(uid, u)
            return jsonify({
                "ok": True,
                "building_type": result["building_type"],
                "progress": result["progress"],
            })
        finally:
            _lock.release()

    # =================================================================
    #  GET /api/city/<uid>/decorations_shop  — Dekoratsiya bozori
    # =================================================================
    @app.route("/api/city/<int:uid>/decorations_shop", methods=["GET"])
    @require_auth
    def api_city_decorations_shop(uid):
        """Bozordagi dekoratsiyalar ro'yxati narxi bilan.
        Frontend shu ma'lumotdan dekoratsiya bo'limini chizadi."""
        u = load_user(uid)
        items = []
        for dec_type, info in DECORATION_TYPES.items():
            items.append({
                "id": dec_type,
                "emoji": info.get("emoji", ""),
                "name_key": info.get("name_key", ""),  # frontend tarjima qiladi
                "price": SHOP_DECORATION_PRICES.get(dec_type, 0),
            })

        return jsonify({
            "ok": True,
            "items": items,
            "user_points": int(u.get("points", 0)),
            "insurance_price": INSURANCE_PRICE,
            "insurance_duration": INSURANCE_DURATION,
        })

    # =================================================================
    #  POST /api/city/<uid>/buy_decoration  — Dekoratsiya sotib olish
    # =================================================================
    @app.route("/api/city/<int:uid>/buy_decoration", methods=["POST"])
    @require_auth
    def api_city_buy_decoration(uid):
        """Dekoratsiyani sotib olib shaharga joylashtiradi.
        Body: {"decoration_type": "tree", "x": 5, "y": 7}
        x, y ixtiyoriy — yo'q bo'lsa random bo'sh slot.

        Ball yechish + add_points_history (Qoida #26) + place_decoration
        — barchasi lock ichida, atomic operation."""
        data = request.get_json(silent=True) or {}
        dec_type = str(data.get("decoration_type", "")).strip()

        if dec_type not in DECORATION_TYPES:
            u_tmp = load_user(uid)
            return _err(u_tmp, "invalid_type")

        price = SHOP_DECORATION_PRICES.get(dec_type, 0)

        # Ixtiyoriy koordinata
        x = data.get("x")
        y = data.get("y")
        if x is not None and y is not None:
            try:
                x = int(x); y = int(y)
                if not (0 <= x < CITY_GRID_SIZE and 0 <= y < CITY_GRID_SIZE):
                    u_tmp = load_user(uid)
                    return _err(u_tmp, "invalid_coord")
            except (TypeError, ValueError):
                u_tmp = load_user(uid)
                return _err(u_tmp, "invalid_coord")
        else:
            x, y = None, None

        _lock = _get_city_lock(uid)
        if not _lock.acquire(timeout=3):
            u_tmp = load_user(uid)
            return _err(u_tmp, "busy", 429)
        try:
            u = load_user(uid)
            init_city_for_user(u)

            # Ball yetarlimi?
            cur_points = int(u.get("points", 0))
            if cur_points < price:
                return _err(u, "not_enough_points")

            # Joylashtirish (shahar to'la bo'lsa None qaytaradi)
            new_dec = place_decoration(u, dec_type, x, y)
            if new_dec is None:
                return _err(u, "city_full")

            # Ball yechish + history (Qoida #26)
            u["points"] = cur_points - price
            add_points_history(u, -price)
            save_user(uid, u)

            return jsonify({
                "ok": True,
                "decoration": new_dec,
                "points": u["points"],
            })
        finally:
            _lock.release()

    # =================================================================
    #  POST /api/city/<uid>/delete_decoration  — Dekoratsiyani o'chirish
    # =================================================================
    @app.route("/api/city/<int:uid>/delete_decoration", methods=["POST"])
    @require_auth
    def api_city_delete_decoration(uid):
        """Foydalanuvchi shahar sahifasidan dekoratsiyani o'chirish.
        Body: {"item_id": "dec_xxx"}
        ESLATMA: Ball qaytarib berilmaydi (sotib olingan narsa qaytarilmaydi
        — shop pattern bilan mos: SHOP_SELL_PRICES da decoration yo'q)."""
        data = request.get_json(silent=True) or {}
        item_id = str(data.get("item_id", "")).strip()

        if not item_id:
            u_tmp = load_user(uid)
            return _err(u_tmp, "not_found", 404)

        _lock = _get_city_lock(uid)
        if not _lock.acquire(timeout=3):
            u_tmp = load_user(uid)
            return _err(u_tmp, "busy", 429)
        try:
            u = load_user(uid)
            init_city_for_user(u)
            ok = delete_decoration(u, item_id)
            if not ok:
                return _err(u, "not_found", 404)
            save_user(uid, u)
            return jsonify({"ok": True})
        finally:
            _lock.release()

    # =================================================================
    #  POST /api/city/<uid>/buy_insurance  — Construction Insurance
    # =================================================================
    @app.route("/api/city/<int:uid>/buy_insurance", methods=["POST"])
    @require_auth
    def api_city_buy_insurance(uid):
        """Construction Insurance sotib olish (premium feature).
        INSURANCE_DURATION kun davomida kun o'tkazilsa progress saqlanadi.
        Faol bo'lsa qayta sotib olish bekor qilinadi (vaqtni davom ettirmaydi
        — bu mantiqiyroq UX uchun, foydalanuvchi adashib qayta sotib olmasin)."""
        _lock = _get_city_lock(uid)
        if not _lock.acquire(timeout=3):
            u_tmp = load_user(uid)
            return _err(u_tmp, "busy", 429)
        try:
            u = load_user(uid)
            init_city_for_user(u)
            city = get_user_city(u)

            # Allaqachon faol bo'lsa
            from city_logic import _is_insurance_active
            if _is_insurance_active(city):
                return _err(u, "insurance_active")

            # Ball yetarlimi?
            cur_points = int(u.get("points", 0))
            if cur_points < INSURANCE_PRICE:
                return _err(u, "not_enough_points")

            # Faollashtirish + ball yechish
            until = activate_insurance(u, INSURANCE_DURATION)
            u["points"] = cur_points - INSURANCE_PRICE
            add_points_history(u, -INSURANCE_PRICE)
            save_user(uid, u)

            return jsonify({
                "ok": True,
                "insurance_until": until,
                "points": u["points"],
            })
        finally:
            _lock.release()
