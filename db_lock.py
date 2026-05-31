#!/usr/bin/env python3
"""
Per-user lock infratuzilmasi — race condition himoyasi (S1/S2).

MUAMMO (S1): Loyiha bo'ylab `u = load_user(uid); ...; save_user(uid, u)`
patterni ishlatiladi. Ikki jarayon bir vaqtda bir userga tegsa — keyingi
yozish oldingisini o'chiradi (last-write-wins) → ball yo'qoladi yoki
double-spend bo'ladi.

YECHIM (Variant 2 — Strategik muammo S1 qaydidan): har user uchun bitta
`threading.Lock`. Chaqiruvchi `load → modify → save` BUTUN blokini lock
ichiga o'raydi:

    from db_lock import user_lock
    with user_lock(uid):
        u = load_user(uid)
        u["points"] += 5
        save_user(uid, u)

MUHIM — lock NIMA UCHUN `load_user`/`save_user` ICHIGA qo'yilmadi:
Faqat `save_user` ni qulflash poyga'ni to'xtatmaydi. A o'qib bo'lib,
B ham o'qib oladi (ikkalasi eski qiymat) — keyin navbatma-navbat yozadi,
baribir bittasi yo'qoladi. Lock O'QISHDAN OLDIN olinishi va YOZISHDAN
KEYIN qo'yib yuborilishi shart → shuning uchun chaqiruvchi blokni o'raydi.

CHEKLOV (halol qayd): Bu yechim faqat BITTA process (Railway 1 instance)
ichida ishlaydi. `threading.Lock` process'lararo emas. Kelajakda 2+
instance kerak bo'lsa — MongoDB atomic operatsiyalari ($inc/$push) yoki
transactions kerak (S1 Variant 1). Hozircha 1 instance → bu yetarli.

QATLAM (README bog'liqlik xaritasi): L0 (poydevor) — hech qanday lokal
modul import qilmaydi (hatto `config` ham emas). Circular import xavfi YO'Q.
"""

import threading
from contextlib import contextmanager

# ── Per-user lock registry ──
# uid (str) → threading.Lock. Lazy yaratiladi (faqat tegilgan userlar uchun).
_user_locks = {}
_locks_master = threading.Lock()   # registry'ning o'zini himoyalaydi

# Lock olishda kutish chegarasi (soniya). Mavjud shop namunasi 3s ishlatardi
# (flask_routes_extra._get_shop_lock chaqiruvchilari). Bir xil saqlanadi.
LOCK_TIMEOUT = 3


def get_user_lock(user_id):
    """Foydalanuvchi uchun lazy yaratiladigan lock (thread-safe).

    Bir xil uid uchun har doim AYNI Lock obyektini qaytaradi (shuning uchun
    `int` ham `str` ham bir xil kalitga kelishi uchun `str(user_id)`).
    """
    uid = str(user_id)
    with _locks_master:
        lock = _user_locks.get(uid)
        if lock is None:
            lock = threading.Lock()
            _user_locks[uid] = lock
        return lock


@contextmanager
def user_lock(user_id, timeout=LOCK_TIMEOUT):
    """`with user_lock(uid):` — load→modify→save blokini himoyalaydi.

    timeout ichida lock olinmasa TimeoutError ko'taradi (chaqiruvchi
    o'zi ushlab, foydalanuvchiga "server band" javobini berishi mumkin).
    Lock har doim qaytariladi (xato bo'lsa ham — finally).

    Misol:
        try:
            with user_lock(uid):
                u = load_user(uid)
                u["points"] += 5
                save_user(uid, u)
        except TimeoutError:
            return jsonify({"ok": False, "error": "Server band"}), 429
    """
    lock = get_user_lock(user_id)
    acquired = lock.acquire(timeout=timeout)
    if not acquired:
        raise TimeoutError(f"user_lock timeout (uid={user_id})")
    try:
        yield
    finally:
        lock.release()


@contextmanager
def two_user_locks(uid_a, uid_b, timeout=LOCK_TIMEOUT):
    """Bir vaqtda IKKI foydalanuvchini himoyalaydi (ball transfer uchun).

    Transfer A→B: A dan ayiriladi, B ga qo'shiladi — ikkala userning
    `load → modify → save` bloki bitta atomik zona ichida bo'lishi shart
    (S1 + S2). Aks holda transfer paytida A yoki B alohida checkin qilsa
    ball yo'qoladi yoki rollback bo'lmaydi.

    DEADLOCK OLDINI OLISH (lock ordering): lock'lar HAR DOIM kichik uid'dan
    boshlab olinadi. Misol — A→B va B→A teskari transferlar bir vaqtda:
      - Tartibsiz olsa: thread1 lock(A)+kutadi lock(B); thread2 lock(B)+
        kutadi lock(A) → ikkalasi bir-birini kutadi (deadlock).
      - Tartibli (kichik→katta): ikkala thread ham AVVAL min(A,B) ni oladi
        → biri ikkinchisini kutadi, deadlock yo'q.

    A == B bo'lsa (o'ziga transfer — bo'lmasligi kerak, lekin himoya):
    faqat BITTA lock olinadi (bir lock'ni 2 marta olish → o'z-o'zini bloklash).

    Misol:
        try:
            with two_user_locks(uid, target_id):
                u  = load_user(uid)
                tu = load_user(target_id)
                u["points"]  -= amount
                tu["points"] += amount
                save_user(uid, u)
                save_user(target_id, tu)
        except TimeoutError:
            ...  # server band
    """
    a, b = str(uid_a), str(uid_b)
    # Bir xil user → bitta lock kifoya (ikki marta olish o'z-o'zini bloklaydi)
    if a == b:
        with user_lock(a, timeout=timeout):
            yield
        return
    # Deterministik tartib — kichik uid avval (deadlock oldini olish)
    first, second = (a, b) if a < b else (b, a)
    lock1 = get_user_lock(first)
    lock2 = get_user_lock(second)
    if not lock1.acquire(timeout=timeout):
        raise TimeoutError(f"two_user_locks timeout (uid={first})")
    try:
        if not lock2.acquire(timeout=timeout):
            raise TimeoutError(f"two_user_locks timeout (uid={second})")
        try:
            yield
        finally:
            lock2.release()
    finally:
        lock1.release()
