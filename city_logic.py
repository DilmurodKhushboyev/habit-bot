#!/usr/bin/env python3
"""
City (Shahar) logikasi — sof funksiyalar.

Bu modul faqat udata["city"] strukturasi bilan ishlaydi:
- Bino qurish, progress yangilash, siljitish
- Dekoratsiya joylashtirish, siljitish, o'chirish
- Bo'sh katak topish, stage hisoblash

DB ga to'g'ridan-to'g'ri yozilmaydi — chaqiruvchi (handler/route)
udata ni o'zgartirgandan so'ng save_user(uid, udata) ni o'zi chaqiradi
(mavjud pattern bilan mos: callbacks_habits.py, flask_routes_*.py).

Bog'liqlik: faqat config va database (sof helperlar uchun).
"""

import random
import time as _time
from datetime import datetime, timedelta

from config import (
    CITY_GRID_SIZE,
    BUILDING_DAYS,
    BUILDING_TYPES,
    BUILDING_STAGE_THRESHOLDS,
    DECORATION_TYPES,
)
from database import get_user_city, _today_uz5_str

# ============================================================
#  YORDAMCHI FUNKSIYALAR
# ============================================================

def _gen_id(prefix):
    """Unique ID yaratadi: 'bld_' yoki 'dec_' prefix bilan.
    Vaqt + random suffix — to'qnashuv ehtimoli juda past.
    """
    suffix = random.randint(1000, 9999)
    return f"{prefix}_{int(_time.time() * 1000)}_{suffix}"

def _is_valid_coord(x, y):
    """Koordinata grid ichidami tekshiradi."""
    return (
        isinstance(x, int) and isinstance(y, int)
        and 0 <= x < CITY_GRID_SIZE
        and 0 <= y < CITY_GRID_SIZE
    )

def _occupied_set(city):
    """Hozirda band kataklar setini qaytaradi: {(x, y), ...}.
    Bino + dekoratsiyalar birlashtirilgan."""
    occupied = set()
    for b in city.get("buildings") or []:
        x, y = b.get("x"), b.get("y")
        if isinstance(x, int) and isinstance(y, int):
            occupied.add((x, y))
    for d in city.get("decorations") or []:
        x, y = d.get("x"), d.get("y")
        if isinstance(x, int) and isinstance(y, int):
            occupied.add((x, y))
    return occupied

def find_empty_slot(udata):
    """Markazga ENG YAQIN bo'sh katakni topadi → (x, y) tuple yoki None.
    None qaytarsa — shahar to'la.

    MANTIQ (A varianti — markazga yig'ish): avval random katak tanlanardi,
    natijada binolar 30x30 grid bo'ylab tarqoq joylashardi (foydalanuvchi
    faqat 1-2 tasini ko'rardi). Endi markazdan (CITY_GRID_SIZE//2) boshlab
    halqama-halqa (ring) tashqariga qarab birinchi bo'sh katak qidiriladi —
    shahar markazda jipslashib, tashqariga "o'sib boradi" (Hay Day/SimCity hissi).

    Deterministik: bir xil shahar holatida har doim bir xil natija
    (eski random xulqdan farqi — barqaror, oldindan aytib bo'ladigan joylashuv).
    """
    city = get_user_city(udata)
    occupied = _occupied_set(city)
    total = CITY_GRID_SIZE * CITY_GRID_SIZE
    if len(occupied) >= total:
        return None  # to'la

    cx = CITY_GRID_SIZE // 2  # markaz x (30 grid → 15)
    cy = CITY_GRID_SIZE // 2  # markaz y

    # Markaz katagi bo'sh bo'lsa — darhol qaytaramiz (1-bino aynan markazga)
    if (cx, cy) not in occupied:
        return (cx, cy)

    # Markaz band — halqama-halqa tashqariga qarab qidiramiz.
    # radius=1,2,3,... har halqaning chekka kataklarini tekshiramiz.
    # Maksimal radius: markazdan grid chetigacha bo'lgan eng katta masofa.
    max_radius = CITY_GRID_SIZE  # xavfsiz yuqori chegara (butun grid qamrab olinadi)
    for radius in range(1, max_radius + 1):
        ring = []
        # Halqaning yuqori va pastki qatorlari
        for x in range(cx - radius, cx + radius + 1):
            ring.append((x, cy - radius))
            ring.append((x, cy + radius))
        # Halqaning chap va o'ng ustunlari (burchaklarsiz — yuqorida qo'shilgan)
        for y in range(cy - radius + 1, cy + radius):
            ring.append((cx - radius, y))
            ring.append((cx + radius, y))
        # Halqadagi bo'sh va grid ichidagi birinchi katakni topamiz.
        # sorted — deterministik tartib (radius teng kataklar orasida barqarorlik).
        for (x, y) in sorted(ring):
            if 0 <= x < CITY_GRID_SIZE and 0 <= y < CITY_GRID_SIZE:
                if (x, y) not in occupied:
                    return (x, y)

    return None  # mantiqan bu yerga yetib kelmaydi (occupied < total tekshirilgan)


def compact_buildings_to_center(udata):
    """Eski tarqoq binolarni markazga yig'adi (bir martalik migration).

    SABAB (Qoida #21): eski `find_empty_slot` 30×30 grid bo'ylab tasodifiy
    katak tanlardi → binolar tarqoq joylashardi va foydalanuvchi faqat 1-2
    tasini ko'rardi. Yangi `find_empty_slot` markazdan-tashqariga halqama
    ishlaydi, lekin u faqat YANGI binolar uchun. Eski binolarni ham markazga
    yig'ish uchun bir martalik migration kerak.

    MANTIQ:
    1) Barcha binolarni vaqtincha "olib qo'yamiz" (eski x,y unutiladi).
    2) Eng katta progress'dan boshlab qayta joylashtiramiz — markazga eng
       yaqin bo'sh katakdan boshlab (find_empty_slot mantig'i). Sabab:
       muhimroq (oldinroq qurilgan) binolar markazga yaqin tursin.
    3) `city["compacted"] = True` markeri — keyingi safar qayta ishlamaydi
       (idempotent).

    Dekoratsiyalar TEGILMAYDI (Qoida #1 — faqat bino muammosi so'ralgan,
    dekoratsiyalar hozir render ham qilinmaydi). Agar dekoratsiya binoning
    eski koordinatasida bo'lsa, u joyida qoladi (kelajakda alohida hal qilinadi).

    Qaytaradi: True — migration bajarildi, False — kerak emas edi
    (compacted=True yoki bino yo'q). Chaqiruvchi save_user'ni o'zi chaqiradi.
    """
    city = get_user_city(udata)
    # Allaqachon yig'ilgan bo'lsa — qayta ishlamaymiz (idempotent)
    if city.get("compacted"):
        return False
    buildings = city.get("buildings") or []
    if not buildings:
        # Hech qanday bino yo'q — markerni qo'yamiz va chiqamiz (kelajakka qadar)
        city["compacted"] = True
        return False

    # 1) Eski koordinatalarni "olib qo'yish" — `_occupied_set` endi
    #    faqat dekoratsiyalardan iborat bo'ladi (binolar koordinatasi
    #    o'chirilgani uchun _occupied_set ularni ko'rmaydi).
    #    Sort: katta progress avval (markazga yaqin tursin), keyin habit_id
    #    (deterministik tartib teng progress'lar uchun).
    sorted_buildings = sorted(
        buildings,
        key=lambda b: (-(b.get("progress") or 0), str(b.get("habit_id", ""))),
    )
    for b in sorted_buildings:
        b.pop("x", None)
        b.pop("y", None)

    # 2) Qayta joylashtirish: find_empty_slot markazdan-tashqariga ishlaydi
    for b in sorted_buildings:
        slot = find_empty_slot(udata)
        if slot is None:
            # Shahar to'la — qolgan binolar joysiz qoladi. Mantiqan bu yerga
            # yetib kelmaydi (900 katak, max ~10 bino), lekin xavfsizlik uchun.
            # Bunday holatda bino ma'lumotini buzmaymiz — keyingi safarga.
            city["compacted"] = True
            return True
        b["x"], b["y"] = slot

    city["compacted"] = True
    return True


# ============================================================
#  PROGRESS / STAGE
# ============================================================

def get_building_stage(progress):
    """Progress (0-66) → vizual stage (0-4).
    Frontend shu raqamni olib mos SVG/rasm chizadi.

    Stage 0: 0-13   (foundation)
    Stage 1: 14-26  (skeleton)
    Stage 2: 27-39  (walls)
    Stage 3: 40-52  (roof)
    Stage 4: 53-66  (complete)
    """
    if not isinstance(progress, (int, float)):
        return 0
    p = int(progress)
    for stage_idx, threshold in enumerate(BUILDING_STAGE_THRESHOLDS):
        if p <= threshold:
            return stage_idx
    return len(BUILDING_STAGE_THRESHOLDS) - 1  # max stage

# ============================================================
#  BINO YARATISH / O'ZGARTIRISH
# ============================================================

def create_building(udata, habit_id, building_type=None, x=None, y=None):
    """Yangi bino yaratadi (habit birinchi marta tasdiqlanganda yoki
    yangi habit yaratilganda chaqiriladi).

    Argumentlar:
      udata         — foydalanuvchi ma'lumoti
      habit_id      — odat IDsi (string)
      building_type — bino turi (BUILDING_TYPES dan kalit). None bo'lsa
                      random tanlanadi (foydalanuvchi keyinchalik shahar
                      sahifasida o'zgartirishi mumkin — Qoida #5 javob: A).
      x, y          — pozitsiya. None bo'lsa random bo'sh katak topiladi.

    Qaytaradi:
      yaratilgan bino dict (success) yoki None (shahar to'la / xato).

    Edge case'lar:
      - Agar shu habit_id uchun bino allaqachon bor → yangi yaratmaymiz,
        mavjudini qaytaramiz (idempotent).
      - Agar shahar to'la → None.
      - Agar building_type noto'g'ri → random valid tur tanlanadi.
    """
    city = get_user_city(udata)
    habit_id = str(habit_id)

    # Idempotency: agar shu habit uchun bino bor bo'lsa — qaytaramiz
    for b in city.get("buildings") or []:
        if str(b.get("habit_id")) == habit_id:
            return b

    # Bino tipini tekshirish / random tanlash
    valid_types = list(BUILDING_TYPES.keys())
    if building_type not in valid_types:
        building_type = random.choice(valid_types)

    # Pozitsiya
    if x is None or y is None or not _is_valid_coord(x, y):
        slot = find_empty_slot(udata)
        if slot is None:
            return None  # shahar to'la
        x, y = slot
    else:
        # Berilgan pozitsiya bandmi tekshirish
        if (x, y) in _occupied_set(city):
            slot = find_empty_slot(udata)
            if slot is None:
                return None
            x, y = slot

    today = _today_uz5_str()
    new_building = {
        "id": _gen_id("bld"),
        "habit_id": habit_id,
        "building_type": building_type,
        "x": int(x),
        "y": int(y),
        "progress": 0,
        "started_at": today,
        "last_updated": today,
    }

    if not isinstance(city.get("buildings"), list):
        city["buildings"] = []
    city["buildings"].append(new_building)
    return new_building

def update_building_progress(udata, habit_id, delta):
    """Bino progress'ini yangilaydi (+1 = checkin, -1 = kun o'tkazildi).

    Insurance faol bo'lsa va delta < 0 → o'zgarish bo'lmaydi (saqlanadi).

    Progress chegaralari:
      min: 0 (manfiy bo'lmaydi — soft regress)
      max: BUILDING_DAYS = 66 (bundan oshmaydi)

    Qaytaradi:
      yangilangan bino dict (success) yoki None (bino topilmadi).

    Agar bino topilmasa va delta > 0 → avtomatik yaratamiz (foydalanuvchi
    eski user, hali bino yo'q lekin habit checkin qildi). Bu qulay
    auto-init — shahar feature kelganda eski habitlar uchun ham ishlaydi.
    """
    if delta == 0:
        return None

    city = get_user_city(udata)
    habit_id = str(habit_id)

    # Insurance tekshirish (delta < 0 holatda)
    if delta < 0 and _is_insurance_active(city):
        return None  # progress saqlanadi

    # Binoni topish
    target = None
    for b in city.get("buildings") or []:
        if str(b.get("habit_id")) == habit_id:
            target = b
            break

    if target is None:
        # Eski user uchun auto-init: faqat positive delta'da yaratamiz
        if delta > 0:
            target = create_building(udata, habit_id)
            if target is None:
                return None  # shahar to'la
        else:
            return None  # bino yo'q va negative delta — hech nima qilmaymiz

    # Progress yangilash (clamp 0..BUILDING_DAYS)
    cur = int(target.get("progress", 0))
    new_progress = max(0, min(BUILDING_DAYS, cur + int(delta)))
    target["progress"] = new_progress
    target["last_updated"] = _today_uz5_str()
    return target

def change_building_type(udata, habit_id, new_type):
    """Bino turini o'zgartiradi (foydalanuvchi shahar sahifasidan).
    Progress saqlanadi — faqat vizual ko'rinish o'zgaradi.

    Qaytaradi:
      yangilangan bino (success) yoki None (bino topilmadi / noto'g'ri tur).
    """
    if new_type not in BUILDING_TYPES:
        return None

    city = get_user_city(udata)
    habit_id = str(habit_id)

    for b in city.get("buildings") or []:
        if str(b.get("habit_id")) == habit_id:
            b["building_type"] = new_type
            b["last_updated"] = _today_uz5_str()
            return b
    return None

def delete_building_for_habit(udata, habit_id):
    """Habit o'chirilganda mos binoni ham o'chiradi.
    Bino bo'sh katakka aylanadi (boshqa narsa joylashtirish mumkin).

    Qaytaradi:
      True — o'chirildi, False — topilmadi.
    """
    city = get_user_city(udata)
    habit_id = str(habit_id)
    buildings = city.get("buildings") or []

    new_list = [b for b in buildings if str(b.get("habit_id")) != habit_id]
    if len(new_list) == len(buildings):
        return False  # topilmadi

    city["buildings"] = new_list
    return True

# ============================================================
#  DEKORATSIYALAR (bozordan sotib olinadi)
# ============================================================

def place_decoration(udata, decoration_type, x=None, y=None):
    """Dekoratsiyani shaharga joylashtiradi (bozordan sotib olingandan keyin).

    Argumentlar:
      decoration_type — DECORATION_TYPES dan kalit
      x, y            — pozitsiya. None bo'lsa random bo'sh katak.

    Qaytaradi:
      yaratilgan dekoratsiya dict (success) yoki None.

    Eslatma: ball yechish (purchase) bu yerda emas — chaqiruvchi
    (callbacks_shop.py yoki flask_routes) to'lovni o'zi boshqaradi
    (mavjud pattern bilan mos).
    """
    if decoration_type not in DECORATION_TYPES:
        return None

    city = get_user_city(udata)

    # Pozitsiya
    if x is None or y is None or not _is_valid_coord(x, y):
        slot = find_empty_slot(udata)
        if slot is None:
            return None  # shahar to'la
        x, y = slot
    else:
        if (x, y) in _occupied_set(city):
            slot = find_empty_slot(udata)
            if slot is None:
                return None
            x, y = slot

    new_dec = {
        "id": _gen_id("dec"),
        "decoration_type": decoration_type,
        "x": int(x),
        "y": int(y),
        "placed_at": _today_uz5_str(),
    }

    if not isinstance(city.get("decorations"), list):
        city["decorations"] = []
    city["decorations"].append(new_dec)
    return new_dec

def delete_decoration(udata, item_id):
    """Dekoratsiyani o'chiradi (foydalanuvchi shahar sahifasidan).
    Qaytaradi: True/False."""
    city = get_user_city(udata)
    decorations = city.get("decorations") or []

    new_list = [d for d in decorations if d.get("id") != item_id]
    if len(new_list) == len(decorations):
        return False
    city["decorations"] = new_list
    return True

# ============================================================
#  SILJITISH (drag & drop)
# ============================================================

def move_item(udata, item_id, new_x, new_y):
    """Bino yoki dekoratsiyani yangi koordinataga ko'chiradi.
    Yangi pozitsiya band bo'lsa — False qaytariladi (frontend'da
    foydalanuvchi boshqa joy tanlashi kerak).

    Qaytaradi: True (success) / False (band yoki topilmadi / koord noto'g'ri).
    """
    if not _is_valid_coord(new_x, new_y):
        return False

    city = get_user_city(udata)
    occupied = _occupied_set(city)

    # Hozirgi joyini topish
    target = None
    for b in city.get("buildings") or []:
        if b.get("id") == item_id:
            target = b
            break
    if target is None:
        for d in city.get("decorations") or []:
            if d.get("id") == item_id:
                target = d
                break
    if target is None:
        return False  # topilmadi

    cur_x, cur_y = target.get("x"), target.get("y")
    if cur_x == new_x and cur_y == new_y:
        return True  # bir xil joy — hech nima qilmaymiz, success

    # Yangi joy band emasmi? (o'zining hozirgi joyi mustasno)
    occupied.discard((cur_x, cur_y))
    if (new_x, new_y) in occupied:
        return False

    target["x"] = int(new_x)
    target["y"] = int(new_y)
    return True

# ============================================================
#  INSURANCE (premium feature, kelajakka asos)
# ============================================================

def _is_insurance_active(city):
    """Insurance hozir faolmi tekshiradi (sana bo'yicha)."""
    if not city.get("insurance_active"):
        return False
    until = city.get("insurance_until")
    if not until:
        return False
    today = _today_uz5_str()
    return today <= until

def activate_insurance(udata, days):
    """Insurance'ni N kunga faollashtiradi.
    Chaqiruvchi (shop handler) ball yechib bu funksiyani chaqiradi.
    """
    city = get_user_city(udata)
    today = datetime.utcnow() + timedelta(hours=5)
    until = (today + timedelta(days=int(days))).strftime("%Y-%m-%d")
    city["insurance_active"] = True
    city["insurance_until"] = until
    return until
