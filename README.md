# 🧭 Super Habits Bot — Modular Tuzilma

> 9 382 qatorlik monolitik `habit_bot.py` → 28 ta mustaqil modul

---

## 🚀 Ishga tushurish

```bash
pip install pyTelegramBotAPI schedule pymongo flask Pillow
python habit_bot.py
```

Barcha `.py` fayllar **bitta papkada** turishi kerak.

---

## 📁 Fayl tuzilmasi

```
super_habits/
│
├── habit_bot.py              ← ASOSIY ENTRY POINT (ishga tushurish)
│
├── ─── YADRO ──────────────────────────────────────────
├── config.py                 ← Sozlamalar, MongoDB ulanish
├── database.py               ← CRUD: load/save user, group, settings, cache
├── texts.py                  ← LANGS dictionary (uz/en/ru tarjimalar)
├── motivation.py             ← Motivatsiya matinlari
├── helpers.py                ← Yordamchilar: T(), get_lang(), today_uz5()
│
├── ─── BOT VA UI ──────────────────────────────────────
├── bot_setup.py              ← Bot instance, tugmalar, menyu yordamchilari
├── menus.py                  ← 2-menyu, obuna tekshirish, admin menyulari
├── achievements.py           ← Yutuqlar (achievements) ro'yxati va tekshiruvi
│
├── ─── HANDLERLAR ─────────────────────────────────────
├── handlers_commands.py      ← /start, /admin_panel, kontakt qabul qilish
├── handlers_onboarding.py    ← Yangi foydalanuvchi uchun onboarding jarayoni
├── handlers_callbacks.py     ← Callback DISPATCHER (sub-modullarga yo'naltiradi)
├── handlers_text.py          ← Matn xabarlari, to'lov, broadcast, inline query
├── handlers_rating.py        ← Reyting rasm generatsiyasi (PIL bilan)
├── handlers_stats.py         ← Statistika, haftalik/oylik/yillik hisobotlar
│
├── ─── CALLBACK SUB-MODULLAR ─────────────────────────
├── callbacks_admin.py        ← Admin panel: broadcast, statistika, kanal, ball
├── callbacks_settings.py     ← Sozlamalar: til, vaqt, ism o'zgartirish
├── callbacks_habits.py       ← Odat: qo'shish, o'chirish, toggle, done, skip
├── callbacks_menu.py         ← Menyu navigatsiya, hisobot ro'yxati
├── callbacks_groups.py       ← Guruh: yaratish, o'chirish, a'zo, reyting
├── callbacks_shop.py         ← Bozor: ball transfer, jon sotib olish, referral
│
├── ─── GURUH VA JADVAL ────────────────────────────────
├── groups.py                 ← Guruh funksiyalari + yangi odat saqlash
├── scheduler.py              ← Eslatmalar, kunlik reset, jadval boshqaruvi
│
├── ─── FLASK WEB APP API ──────────────────────────────
├── flask_api.py              ← Flask app yaratish va route registratsiya
├── flask_helpers.py          ← CORS, rate limiter, Telegram auth tekshirish
├── flask_routes_core.py      ← API: rating, profile, habits, groups CRUD
├── flask_routes_data.py      ← API: today, checkin, stats
└── flask_routes_extra.py     ← API: achievements, shop, friends, challenges, webhook
```

---

## 🔗 Modullar orasidagi bog'liqlik

```
habit_bot.py (entry point)
    │
    ├── config.py ............... hech nimaga bog'liq emas
    │
    ├── database.py ............. config
    │
    ├── texts.py ................ hech nimaga bog'liq emas
    ├── motivation.py ........... hech nimaga bog'liq emas
    ├── helpers.py .............. database, texts
    │
    ├── bot_setup.py ............ config, database, helpers
    ├── menus.py ................ database, helpers, bot_setup
    ├── achievements.py ......... database, bot_setup, helpers
    │
    ├── handlers_commands.py .... config, database, helpers, bot_setup, menus
    ├── handlers_onboarding.py .. database, helpers, bot_setup
    ├── handlers_callbacks.py ... → dispatcher, sub-modullarga yo'naltiradi:
    │   ├── callbacks_admin.py
    │   ├── callbacks_settings.py
    │   ├── callbacks_habits.py
    │   ├── callbacks_menu.py
    │   ├── callbacks_groups.py
    │   └── callbacks_shop.py
    │
    ├── handlers_text.py ........ database, helpers, bot_setup, groups, scheduler
    ├── handlers_rating.py ...... database, helpers, bot_setup
    ├── handlers_stats.py ....... database, helpers, bot_setup
    │
    ├── groups.py ............... database, helpers, bot_setup, menus
    ├── scheduler.py ............ database, helpers, bot_setup, handlers_stats
    │
    └── flask_api.py ............ flask_helpers + 3 ta route modul
        ├── flask_helpers.py
        ├── flask_routes_core.py
        ├── flask_routes_data.py
        └── flask_routes_extra.py
```

---

## 📋 Har bir fayl nima qiladi

### Yadro modullari

| Fayl | Qatorlar | Vazifasi |
|------|----------|----------|
| `config.py` | 39 | `BOT_TOKEN`, `ADMIN_ID`, `MONGO_URI`, MongoDB ulanish va indekslar |
| `database.py` | 101 | `load_user`, `save_user`, `load_group`, `save_group`, `load_all_users` (60s cache), `count_users` |
| `texts.py` | ~344 | `LANGS` dict — uz/en/ru (3 til). `btn_ack` — xabarni o'chirish tugmasi |
| `motivation.py` | 111 | `MOTIVATSIYA` dict — uz/en/ru motivatsion gaplar |
| `helpers.py` | 51 | `T(uid, key)` — tarjima, `get_lang()`, `today_uz5()`, `get_rank()`, `lang_keyboard()` |

### Bot va UI

| Fayl | Qatorlar | Vazifasi |
|------|----------|----------|
| `bot_setup.py` | 142 | `bot` instance, `send_message_colored()`, `cBtn()`, `ok_kb(uid)` — dismiss tugmasi, `main_menu_dict()`, `send_main_menu()` |
| `menus.py` | 167 | `menu2_dict()`, `send_menu2()`, `check_subscription()`, `admin_menu()`, `admin_broadcast_menu()` |
| `achievements.py` | 55 | `_ACHIEVEMENTS` ro'yxati, `check_achievements_toplevel()` |

### Handlerlar

| Fayl | Qatorlar | Vazifasi |
|------|----------|----------|
| `handlers_commands.py` | 362 | `/start` — ro'yxatdan o'tish, til tanlash, deep link; `/admin_panel`; kontakt qabul qilish |
| `handlers_onboarding.py` | — | *OLIB TASHLANGAN* — onboarding oʻchirilgan, foydalanuvchi toʻgʻridan-toʻgʻri asosiy menyuga tushadi |
| `handlers_callbacks.py` | 145 | **Dispatcher**: umumiy preamble (til, obuna) + 6 ta sub-handlerga yo'naltirish. `ack_delete_msg` — universal xabar o'chirish |
| `handlers_text.py` | 1027 | Barcha matn xabarlari (state machine), Telegram Stars to'lov, broadcast, inline query |
| `handlers_rating.py` | 380 | PIL bilan reyting rasmi generatsiyasi (top-10 grid), `show_rating()` |
| `handlers_stats.py` | 436 | `show_stats()`, haftalik/oylik/yillik hisobot generatsiyasi va yuborish |

### Callback sub-modullar

| Fayl | Qatorlar | Vazifasi |
|------|----------|----------|
| `callbacks_admin.py` | 426 | Admin: broadcast, foydalanuvchilar ro'yxati, kanal sozlash, ball berish, statistika |
| `callbacks_settings.py` | 363 | Sozlamalar: til, odat vaqtlari, ism, telefon o'zgartirish |
| `callbacks_habits.py` | 754 | Odat qo'shish (`menu_add`), o'chirish, `toggle_` (bajarish), `done_`, `skip_`, shield |
| `callbacks_menu.py` | 345 | Menyu navigatsiya, hisobot ro'yxatlari (weekly/monthly/yearly view) |
| `callbacks_groups.py` | 562 | Guruh yaratish/o'chirish, a'zo qo'shish/chiqarish, guruh reytingi, guruh odat bajarish |
| `callbacks_shop.py` | 270 | Bozor: jon sotib olish, referral, ball transfer, tahrirlash, reset |

### Guruh va jadval

| Fayl | Qatorlar | Vazifasi |
|------|----------|----------|
| `groups.py` | 355 | `_save_new_habit()`, `_send_group_view()`, `_build_group_rating()`, `_save_new_group()` |
| `scheduler.py` | 751 | `send_reminder()`, `daily_reset()`, `schedule_habit()`, `scheduler_loop()`, `send_evening_reminders()` |

### Flask Web App API

| Fayl | Qatorlar | Vazifasi |
|------|----------|----------|
| `flask_api.py` | 35 | Flask app yaratish, route modullarni ro'yxatdan o'tkazish, `run_api()` |
| `flask_helpers.py` | 132 | CORS, rate limiter, `verify_init_data()`, `require_auth()` dekorator |
| `flask_routes_core.py` | 511 | `/api/rating`, `/api/profile`, `/api/habits` CRUD, `/api/groups` CRUD. **Import tuzatish:** `mongo_db`, `mongo_col` (config dan), `ACHIEVEMENTS` qo'shildi |
| `flask_routes_data.py` | 485 | `/api/today`, `/api/checkin` (bajarish logikasi), `/api/stats` |
| `flask_routes_extra.py` | 786 | `/api/achievements`, `/api/shop`, `/api/friends`, `/api/challenges`, `/health`, webhook. **Import tuzatish:** `telebot`, `InlineKeyboardMarkup/Button`, `ACHIEVEMENTS as _ACHIEVEMENTS`, `CAT_LABELS` qo'shildi |

---

## ✏️ Qanday tahrirlash kerak

**Yangi odat turi qo'shmoqchimisiz?**
→ `callbacks_habits.py` + `groups.py` (`_save_new_habit`)

**Yangi API endpoint qo'shmoqchimisiz?**
→ `flask_routes_core.py` yoki `flask_routes_extra.py`

**Matn/tarjima o'zgartirmoqchimisiz?**
→ `texts.py` (`LANGS` dict)

**Yangi callback tugma qo'shmoqchimisiz?**
→ Tegishli `callbacks_*.py` fayliga + `handlers_callbacks.py` dispatcherda tartibni tekshiring

**Admin funksiya qo'shmoqchimisiz?**
→ `callbacks_admin.py` + `menus.py` (`admin_menu`)

**Scheduler/eslatma o'zgartirmoqchimisiz?**
→ `scheduler.py`

---

## ⚠️ Muhim eslatmalar

1. **Import tartibi muhim**: `habit_bot.py` dagi import tartibi handlerlarni telebot'da ro'yxatdan o'tkazadi
2. **Circular import yo'q**: `schedule_habit` va shunga o'xshash funksiyalar lazy import (`from scheduler import ...` funksiya ichida) ishlatadi
3. **Callback dispatcher**: `handlers_callbacks.py` barcha callback'larni oladi va sub-modullarga yo'naltiradi — sub-modul `True` qaytarsa, boshqasiga o'tmaydi
4. **Flask routes**: `register_*_routes(app)` funksiyalari orqali ro'yxatdan o'tadi — `flask_api.py` dan chaqiriladi
