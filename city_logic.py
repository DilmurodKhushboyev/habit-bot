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

def find_empty_slot(udata, gap=True):
    """Markazga ENG YAQIN bo'sh katakni topadi → (x, y) tuple yoki None.
    None qaytarsa — shahar to'la.

    gap=True (default): topilgan katakning 8 qo'shnisi (yuqori/past/chap/o'ng
       + 4 diagonal) ham band bo'lmasligi kerak — binolar orasida bo'sh joy
       qoladi (Hay Day/SimCity hissi). Agar bunday katak topilmasa — gap=False
       rejimida qayta qidiriladi (fallback, shahar siqilganda).
    gap=False: har qanday bo'sh katak qabul qilinadi (qo'shni cheklovsiz).

    MANTIQ (markazga yig'ish): markazdan (CITY_GRID_SIZE//2) boshlab
    halqama-halqa (ring) tashqariga qarab birinchi mos katak qidiriladi —
    shahar markazda jipslashib, tashqariga "o'sib boradi".

    Deterministik: bir xil shahar holatida har doim bir xil natija.
    """
    city = get_user_city(udata)
    occupied = _occupied_set(city)
    total = CITY_GRID_SIZE * CITY_GRID_SIZE
    if len(occupied) >= total:
        return None  # to'la

    cx = CITY_GRID_SIZE // 2  # markaz x (30 grid → 15)
    cy = CITY_GRID_SIZE // 2  # markaz y

    def _has_gap(x, y):
        """8 qo'shni katak bo'shmi? (grid chetidagi yo'q-katak ham "bo'sh" deb hisoblanadi)"""
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                # Grid tashqarisi — "bo'sh" (chetdagi binoga chap/yuqori xalaqit bermaydi)
                if not (0 <= nx < CITY_GRID_SIZE and 0 <= ny < CITY_GRID_SIZE):
                    continue
                if (nx, ny) in occupied:
                    return False
        return True

    # Markaz katagi bo'sh va (gap shart bo'lsa) qo'shnilar ham bo'sh bo'lsa — markazga
    if (cx, cy) not in occupied:
        if not gap or _has_gap(cx, cy):
            return (cx, cy)

    # Markaz band yoki gap shartiga mos kelmadi — halqama tashqariga qidiramiz.
    # radius=1,2,3,... har halqaning chekka kataklarini tekshiramiz.
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
        # Halqadagi mos katakni topamiz. sorted — deterministik tartib.
        for (x, y) in sorted(ring):
            if not (0 <= x < CITY_GRID_SIZE and 0 <= y < CITY_GRID_SIZE):
                continue
            if (x, y) in occupied:
                continue
            if gap and not _has_gap(x, y):
                continue
            return (x, y)

    # gap=True rejimida hech narsa topilmadi — fallback: qattiq qoidasiz qaytadan
    # (shahar siqilganda baribir bino joylashishi kerak).
    if gap:
        return find_empty_slot(udata, gap=False)

    return None  # mantiqan bu yerga yetib kelmaydi (occupied < total tekshirilgan)


# Migration versiyasi — har "compact mantig'i" o'zgarganda OSHIRILADI.
# `city.compact_version` < bu raqam bo'lsa, compact_buildings_to_center qayta ishlaydi.
# v1: markazga yig'ish (oldingi version, marker `compacted=True` edi).
# v2: gap qoidasi (binolar orasida bo'sh katak). Pinned binolar hurmat qilinadi.
COMPACT_VERSION = 2


def compact_buildings_to_center(udata):
    """Tarqoq yoki siqilgan binolarni markazga "gap" qoidasi bilan qayta yig'adi.

    SABAB (Qoida #21):
    - v1 migration random joylashuvni markazga yig'di, lekin binolar BIRGA yopishib
      qolardi (orasida bo'sh joy yo'q).
    - v2 migration: `find_empty_slot(gap=True)` — har bino atrofida 1 katak bo'sh
      joy qoladi (Hay Day/SimCity hissi).

    PINNED BINOLAR (long-press move uchun kelajak asos):
    - `b["pinned"] = True` bo'lgan binolar TEGILMAYDI — foydalanuvchi qo'lda
      ko'chirgan joy saqlanib qoladi (yangi safar sahifa ochilganda yoki kelgusi
      migration'larda ham). Ular `occupied` set'iga ham qo'shiladi —
      `find_empty_slot` ularga teginmaydi va atrofiga joylashtirmaydi (gap).
    - Pinned bo'lmagan (default: hech bir bino) qayta joylashtiriladi.

    VERSIYALANGAN (idempotent + qayta migratsiyaga ochiq):
    - `city.compact_version >= COMPACT_VERSION` bo'lsa — chiqib ketadi (ish yo'q).
    - Mantiq o'zgarsa — COMPACT_VERSION oshiriladi → barcha user'larda bir marta
      qayta ishlaydi.

    Dekoratsiyalar TEGILMAYDI (Qoida #1, hozircha render qilinmaydi).

    Qaytaradi: True — migration bajarildi, False — kerak emas edi.
    Chaqiruvchi save_user'ni o'zi chaqiradi.
    """
    city = get_user_city(udata)
    # Versiya allaqachon yangi bo'lsa — ish yo'q (eski "compacted=True" markerini
    # ham hurmat qilamiz: u v1 bilan teng. v2 ga o'tish uchun versiyani tekshiramiz.)
    current_version = city.get("compact_version", 1 if city.get("compacted") else 0)
    if current_version >= COMPACT_VERSION:
        return False

    buildings = city.get("buildings") or []
    if not buildings:
        # Bino yo'q — versiyani yangilab chiqib ketamiz
        city["compact_version"] = COMPACT_VERSION
        # Eski marker — qoldirish zarari yo'q (allaqachon DB'da bo'lishi mumkin)
        city["compacted"] = True
        return False

    # Pinned va pinned bo'lmagan binolarni ajratamiz
    pinned = [b for b in buildings if b.get("pinned")]
    movable = [b for b in buildings if not b.get("pinned")]

    if not movable:
        # Hammasi pinned — hech narsa qilmaymiz, versiyani yangilaymiz
        city["compact_version"] = COMPACT_VERSION
        city["compacted"] = True
        return False

    # 1) Movable binolarning x,y ni tozalaymiz — `_occupied_set` ularni ko'rmaydi.
    #    Pinned binolar va dekoratsiyalar `occupied` ichida qoladi → find_empty_slot
    #    ularni hurmat qiladi (gap qoidasi ham ularga nisbatan ishlaydi).
    #    Sort: katta progress avval (markazga yaqin tursin), keyin habit_id (deterministik).
    movable_sorted = sorted(
        movable,
        key=lambda b: (-(b.get("progress") or 0), str(b.get("habit_id", ""))),
    )
    for b in movable_sorted:
        b.pop("x", None)
        b.pop("y", None)

    # 2) Qayta joylashtirish: find_empty_slot gap=True (default) → orasida bo'sh joy.
    #    Topilmasa avtomatik gap=False fallback (find_empty_slot ichida).
    for b in movable_sorted:
        slot = find_empty_slot(udata)
        if slot is None:
            # Shahar to'la — qolgan binolar joysiz qoladi (mantiqan bu yerga yetib
            # kelmaydi: 30×30=900 katak, max 10 bino). Bino ma'lumotini buzmaymiz.
            city["compact_version"] = COMPACT_VERSION
            city["compacted"] = True
            return True
        b["x"], b["y"] = slot

    city["compact_version"] = COMPACT_VERSION
    city["compacted"] = True  # eski marker — qolaversin (eski kod o'qisa ham buzilmaydi)
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

def backfill_buildings_from_habits(udata):
    """Eski tasdiqlangan odatlar uchun retroaktiv bino yaratadi.

    SABAB (Qoida #21):
    City feature deploy qilingach, foydalanuvchining mavjud odatlari uchun
    binolar avtomatik yaratilmagan — `update_building_progress` faqat YANGI
    checkin (delta > 0) bo'lganda bino yaratadi. Natijada deploy'dan oldin
    tasdiqlangan kunlar shaharda ko'rinmaydi (shahar bo'sh ko'rinadi).

    Bu funksiya har bir odat uchun:
      - Shu habit_id uchun bino bormi tekshiradi
      - Yo'q bo'lsa → bino yaratadi va progress = min(effective_done, BUILDING_DAYS)
        qiymati bilan to'ldiradi (effective_done=0 bo'lsa progress=0 — bo'sh poydevor)

    Variant B mantig'i (README §314):
      - Har bir odat uchun bino yaratiladi, hatto hech qachon tasdiqlanmagan bo'lsa ham
      - "Odat tasdiqlanmagan bo'lsa ham bo'sh bino (progress 0) ko'rinadi"
      - Yangi odat qo'shilganda `api_habits_add` `create_building` chaqiradi —
        backfill ham xuddi shu mantiqni eski odatlarga qo'llaydi (sinxronlik)

    Effective_done hisoblash (Qoida #10/#11 — statistika bilan sinxron):
      - effective_done = max(total_done, history_count)
      - total_done: DB'dagi rasmiy hisob (faqat to'liq kun yopilganda o'sadi)
      - history_count: history dan habit_id tasdiqlangan barcha kunlar
      - max: ikkala manbadan eng yuqori qiymat (eng adolatli ko'rsatkich)

    Nima uchun max (shartli emas):
      - Repeat odatlar (Suv ichish 1/2, Uyqu 1/3): qisman tasdiqlanganda
        `total_done` o'smaydi, lekin `history` har tasdiqlashni hisoblaydi
      - Simple odatlar: `total_done` va `history` mos keladi
      - Eski user (history yo'q): `total_done` ishlatiladi
      - Statistika `api_stats` bilan to'g'ridan-to'g'ri mos kelishi uchun

    IDEMPOTENT:
      - Bino allaqachon bor → tegilmaydi (mavjud progress saqlanadi)
      - Habit ro'yxati bo'sh → hech narsa qilmaydi
      - Keyingi chaqiriqlarda hech narsa o'zgartirmaydi (xavfsiz)

    Qaytaradi:
      Yaratilgan binolar soni (int). 0 = hech narsa qo'shilmadi.
      Chaqiruvchi save_user'ni o'zi chaqiradi (faqat created > 0 bo'lsa).
    """
    habits = udata.get("habits") or []
    if not habits:
        return 0

    city = get_user_city(udata)
    # Mavjud bino habit_id larini setga yig'ib olamiz (tezkor tekshiruv uchun)
    existing_habit_ids = {
        str(b.get("habit_id"))
        for b in (city.get("buildings") or [])
        if b.get("habit_id") is not None
    }

    # History dan hisoblash uchun bir marta olamiz (har odat uchun qaytarmaslik).
    # SABAB (Qoida #11 — consistency): statistika `api_stats` (flask_routes_data.py)
    # `done_all = total_done if > 0 else done_30_hist` mantig'ini ishlatadi —
    # repeat odatlar uchun `total_done=0` bo'lsa ham history dan haqiqiy
    # tasdiqlangan kunlar hisoblanadi. Backfill ham xuddi shu mantiqni
    # ishlatishi kerak — aks holda bino balandligi statistika "JAMI" qiymati
    # bilan mos kelmaydi (foydalanuvchi chalkash).
    history = udata.get("history") or {}

    created = 0
    for h in habits:
        habit_id = h.get("id")
        if habit_id is None:
            continue
        habit_id_str = str(habit_id)

        # Allaqachon bino bor → tegmaymiz (idempotent)
        if habit_id_str in existing_habit_ids:
            continue

        # Variant B: shartisiz — har bir odat uchun bino yaratamiz.
        # effective_done=0 bo'lsa progress=0 (bo'sh poydevor) ko'rinadi.
        # SABAB (Qoida #21): README §314 — "odat tasdiqlanmagan bo'lsa ham
        # bo'sh bino (progress 0) ko'rinadi". Yangi odat qo'shilganda
        # `api_habits_add` `create_building` chaqiradi — backfill ham xuddi
        # shu mantiqni eski odatlarga qo'llashi kerak (sinxronlik).
        total_done = int(h.get("total_done", 0) or 0)

        # Statistika bilan sinxron hisoblash (Qoida #10/#11):
        # MUAMMO: Repeat odatlar (Suv ichish 1/2 va h.k.) qisman tasdiqlanganda
        # `total_done` o'sib qolmaydi — faqat to'liq kun yopilganda yangilanadi.
        # Lekin foydalanuvchi har tasdiqlashni shahar va statistikada ko'rishi kerak.
        # YECHIM: max(total_done, history_count) — ikkala manbadan eng yuqori qiymat.
        # - Simple odat (Dasturlash): total_done=34, history=34 → max=34
        # - Repeat odat (Suv ichish): total_done=2, history=26 → max=26
        # - Eski user (history bo'sh): total_done=12, history=0 → max=12
        # - Yangi user: total_done=0, history=0 → max=0 (bo'sh poydevor)
        history_count = sum(
            1 for day_data in history.values()
            if day_data.get("habits", {}).get(habit_id_str)
        )
        effective_done = max(total_done, history_count)

        # Bino yaratish (random tip, random bo'sh katak — create_building o'zi tanlaydi)
        new_building = create_building(udata, habit_id_str)
        if new_building is None:
            # Shahar to'la — qolgan odatlarni o'tkazib yuboramiz
            break

        # Progress'ni effective_done ga sozlaymiz (clamp 0..BUILDING_DAYS)
        progress = max(0, min(BUILDING_DAYS, effective_done))
        new_building["progress"] = progress
        new_building["last_updated"] = _today_uz5_str()

        # Yangi yaratilgan habit_id ni set'ga qo'shamiz (xavfsizlik uchun,
        # garchi habits ro'yxatida takror bo'lmasligi kerak)
        existing_habit_ids.add(habit_id_str)
        created += 1

    return created

def resync_building_progress(udata):
    """Mavjud binolarning progress qiymatini effective_done bilan sinxronlaydi.

    SABAB (Qoida #21):
    Foydalanuvchi qisman tasdiqlash qilganda (repeat odat 1/3, 2/3 va h.k.)
    `update_building_progress` chaqirilmaydi — chunki `total_done` o'sib qolmaydi
    va checkin logikasi `delta=0` deb qaror qiladi. Lekin statistika `history`
    asosida har tasdiqlashni hisoblaydi. Natija: bino past balandlikda qoladi,
    statistikada esa balandroq raqam — chalkashlik.

    Bu funksiya har mavjud bino uchun:
      - Mos habit'ni topadi
      - effective_done = max(total_done, history_count) hisoblaydi
      - Agar bino progress < effective_done bo'lsa → progress'ni yangilaydi
        (faqat KO'TARILADI, hech qachon tushirilmaydi — chunki bu sinxron
        qilish, regress emas)

    NIMA UCHUN faqat ko'tarish (ikki yo'l emas):
      - Insurance, daily_reset va boshqa qoidalar bilan to'qnashmaslik uchun
      - Foydalanuvchi mehnatini past ko'rsatish — yomon UX (haqiqiy progress
        yo'qotilmasligi kerak)
      - Asl `update_building_progress` -1 ni o'z mantig'i bilan ushlaydi —
        bu yerda yana takrorlash keraksiz

    IDEMPOTENT:
      - progress allaqachon yetarli baland → tegmaydi
      - habit_id bo'lmagan bino → tegmaydi (cleanup vazifasi)
      - Habit yo'q bino → tegmaydi (cleanup vazifasi)

    Qaytaradi:
      Yangilangan binolar soni (int). 0 = hech narsa o'zgarmadi.
      Chaqiruvchi save_user'ni o'zi chaqiradi (faqat updated > 0 bo'lsa).
    """
    city = get_user_city(udata)
    buildings = city.get("buildings") or []
    if not buildings:
        return 0

    habits = udata.get("habits") or []
    if not habits:
        return 0

    # Habit ID → habit obyekti mapping (tezkor o'qish)
    habit_by_id = {
        str(h.get("id")): h
        for h in habits
        if h.get("id") is not None
    }

    history = udata.get("history") or {}
    updated = 0
    today_str = _today_uz5_str()

    for b in buildings:
        habit_id = b.get("habit_id")
        if habit_id is None:
            continue
        habit_id_str = str(habit_id)

        h = habit_by_id.get(habit_id_str)
        if h is None:
            # Orfan bino — cleanup_orphan_buildings vazifasi, tegmaymiz
            continue

        # effective_done hisoblash (backfill bilan bir xil mantiq — Qoida #11)
        total_done = int(h.get("total_done", 0) or 0)
        history_count = sum(
            1 for day_data in history.values()
            if day_data.get("habits", {}).get(habit_id_str)
        )
        effective_done = max(total_done, history_count)

        # Faqat ko'tarish — past tushirmaymiz
        target_progress = max(0, min(BUILDING_DAYS, effective_done))
        current_progress = int(b.get("progress", 0) or 0)

        if target_progress > current_progress:
            b["progress"] = target_progress
            b["last_updated"] = today_str
            updated += 1

    return updated

def cleanup_orphan_buildings(udata):
    """Mavjud bo'lmagan odatlarga bog'langan "orfan" binolarni o'chiradi.

    SABAB (Qoida #21):
    Foydalanuvchi odatni o'chirganda bino ham o'chirilishi kerak edi
    (`delete_building_for_habit` orqali), lekin ba'zi joylarda bu chaqiriq
    yetishmagan (masalan WebApp orqali odat o'chirilganda). Natijada
    shaharda "orfan" binolar qoladi — habit_id mavjud bo'lmagan odatga
    ishora qiladi va frontend nom label'ini bo'sh ko'rsatadi, lekin
    bino o'zi qoladi.

    Bu funksiya har bir bino uchun:
      - habit_id ni hozirgi habits ro'yxatiga solishtiradi
      - Agar mos odat YO'Q bo'lsa → binoni o'chiradi

    NIMA UCHUN avtomatik o'chirish (label saqlash o'rniga):
      - Foydalanuvchi odatni qasdan o'chirgan (xato emas)
      - Bo'sh label'li bino UX uchun chalkash ("bu nima binosi edi?")
      - Joy bo'shaydi → boshqa odatlar uchun ishlatish mumkin

    IDEMPOTENT:
      - Habit'i bor binolarga tegmaydi
      - Buildings bo'sh bo'lsa hech narsa qilmaydi
      - Keyingi chaqiriqlarda orfan yo'q → hech narsa o'zgartirmaydi

    DEKORATSIYALAR TEGILMAYDI:
      - Ular habit'ga bog'liq emas (bozordan sotib olingan, mustaqil)

    PINNED FLAGI TEGILMAYDI:
      - Pinned (foydalanuvchi qo'lda joylashtirgan) — chunki habit yo'q
        bo'lsa, pinned ham mantiqsiz. Orfan = orfan, pinned bo'lsa ham o'chiriladi.

    Qaytaradi:
      O'chirilgan binolar soni (int). 0 = orfan topilmadi.
      Chaqiruvchi save_user'ni o'zi chaqiradi (faqat removed > 0 bo'lsa).
    """
    city = get_user_city(udata)
    buildings = city.get("buildings") or []
    if not buildings:
        return 0

    # Joriy odat ID'larini setga yig'ib olamiz (tezkor tekshiruv uchun)
    habits = udata.get("habits") or []
    valid_habit_ids = {
        str(h.get("id"))
        for h in habits
        if h.get("id") is not None
    }

    # Orfan emas binolarni qoldiramiz
    new_list = []
    removed = 0
    for b in buildings:
        habit_id = b.get("habit_id")
        if habit_id is None:
            # habit_id'siz bino mantiqsiz — orfan deb hisoblaymiz
            removed += 1
            continue
        if str(habit_id) not in valid_habit_ids:
            # Mos odat yo'q — orfan
            removed += 1
            continue
        new_list.append(b)

    if removed > 0:
        city["buildings"] = new_list

    return removed

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

    PINNED (foydalanuvchi qo'lda joylashtirgan): bino muvaffaqiyatli ko'chirilsa
    `pinned=True` qo'yiladi. Bu kelajakdagi compact_buildings_to_center yoki
    auto-rearrange mantiqlariga signal: bu joy foydalanuvchi tomonidan qasdan
    qo'yilgan, tegmang. (Dekoratsiyalar uchun ham xuddi shu mantiq.)

    ITEM_ID: binoda `habit_id` ni qidiradi (frontend `data-habit-id` atributi),
    dekoratsiyada `id` ni qidiradi. Backend ikkala variantni ham qabul qiladi.

    Qaytaradi:
      True  — muvaffaqiyatli ko'chirildi
      False — yangi joy band yoki koordinata noto'g'ri
      None  — item (bino/dekoratsiya) topilmadi
    """
    if not _is_valid_coord(new_x, new_y):
        return False

    city = get_user_city(udata)
    occupied = _occupied_set(city)

    # Hozirgi joyini topish — binoda `habit_id`, dekoratsiyada `id` ishlatiladi
    # (Qoida #11: frontend `data-habit-id` atributidan o'qiydi va shu qiymatni
    # `item_id` sifatida yuboradi. Backend ikkalasini ham qidiradi.)
    target = None
    for b in city.get("buildings") or []:
        if b.get("habit_id") == item_id or b.get("id") == item_id:
            target = b
            break
    if target is None:
        for d in city.get("decorations") or []:
            if d.get("id") == item_id:
                target = d
                break
    if target is None:
        return None  # topilmadi (band emas — route 404 qaytaradi)

    cur_x, cur_y = target.get("x"), target.get("y")
    if cur_x == new_x and cur_y == new_y:
        # Bir xil joy — koord o'zgarmadi, lekin foydalanuvchi qasdan tegdi
        # → pinned belgisi baribir qo'yiladi (compact tegmasligi uchun).
        target["pinned"] = True
        return True

    # Yangi joy band emasmi? (o'zining hozirgi joyi mustasno)
    occupied.discard((cur_x, cur_y))
    if (new_x, new_y) in occupied:
        return False

    target["x"] = int(new_x)
    target["y"] = int(new_y)
    target["pinned"] = True  # foydalanuvchi qo'lda joylashtirdi — compact tegmasin
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
