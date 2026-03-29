# 🧭 Super Habits Bot — Modular Tuzilma

> Backend: 9 382 qatorlik monolitik `habit_bot.py` → 28 ta mustaqil modul
> Frontend: 5 739 qatorlik monolitik `index.html` → 9 ta mustaqil fayl

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

### 🌐 Frontend (Telegram WebApp)

```
super_habits/
│
└── static/                      ← Flask static papka (frontend fayllar)
    ├── index.html               ← HTML tuzilma (267 qator) — faqat layout, modal, nav
    ├── style.css                ← CSS (1049 qator) — neumorphism, dark mode, animatsiyalar
    ├── strings.js               ← Tarjimalar (882 qator) — UZ/RU/EN, S() funksiya
    │
    ├── ─── JS YADRO ──────────────────────────────────────
    ├── app-core.js              ← (236 qator) TG init, API, state, tabs, premium, SVG helpers
    │
    ├── ─── JS SAHIFALAR ──────────────────────────────────
    ├── app-pages.js             ← (567 qator) Bugun (checkin), eslatmalar, yutuqlar
    ├── app-stats.js             ← (857 qator) Statistika, chartlar, heatmap, reyting
    ├── app-profile.js           ← (506 qator) Profil, tahrirlash, til, dark mode
    ├── app-habits.js            ← (305 qator) Odatlar CRUD, icon picker, modal
    └── app-social.js            ← (1073 qator) Guruh, do'st, shop, challenge, onboarding, init, PTR
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

index.html (WebApp entry point)
    │
    ├── style.css ................ hech nimaga bog'liq emas (CSS)
    │
    ├── strings.js ............... hech nimaga bog'liq emas (tarjimalar + S())
    │   ↑ selectedLang, currentLang, STRINGS, S()
    │
    ├── app-core.js .............. strings.js
    │   ↑ tg, user, userId, API, initData, data, loaded
    │   ↑ switchTab, loadTab, apiFetch, ringHTML, jonRingHTML
    │   ↑ showPremiumPage, renderPremium, buyPremium
    │
    ├── app-pages.js ............. strings.js, app-core.js
    │   ↑ loadToday, renderToday, checkin
    │   ↑ loadReminders, renderReminders, saveReminder
    │   ↑ loadAchievements, renderAchievements, showBadgePopup
    │
    ├── app-stats.js ............. strings.js, app-core.js
    │   ↑ loadStats, renderStats, generateShareCard
    │   ↑ loadRating, renderRating, userAvatarHTML
    │
    ├── app-profile.js ........... strings.js, app-core.js, app-pages.js
    │   ↑ loadProfile, renderProfile
    │   ↑ updateNavLabels, setLang, saveLang, saveDarkMode
    │
    ├── app-habits.js ............ strings.js, app-core.js
    │   ↑ loadHabits, renderHabits, saveHabit, deleteHabit
    │   ↑ openAdd, openEdit, closeModal, ICON_CATS
    │
    └── app-social.js ............ strings.js, app-core.js + barcha yuqoridagilar
        ↑ loadGroups, renderGroups, groupCheckin
        ↑ loadFriends, renderFriends, searchFriends
        ↑ loadShop, renderShop, buyItem, sellItem, activateItem
        ↑ openChallenge, sendChallenge, acceptChallenge
        ↑ onboarding (maybeShowOnboard, obMarkDone)
        ↑ window.onload, playHabitSound, PTR
```

---

## 📋 Har bir fayl nima qiladi

### Yadro modullari

| Fayl | Qatorlar | Vazifasi |
|------|----------|----------|
| `config.py` | 39 | `BOT_TOKEN`, `ADMIN_ID`, `MONGO_URI`, MongoDB ulanish va indekslar |
| `database.py` | 111 | `load_user`, `save_user`, `load_group`, `save_group`, `load_all_users` (60s cache), `count_users`, `user_exists` (3x retry) |
| `texts.py` | ~368 | `LANGS` dict — uz/en/ru (3 til). `btn_ack` — xabarni o'chirish tugmasi. Repeat odat kalitlari: `habit_type_choose`, `ask_repeat_count`, `ask_repeat_first_time`, `ask_repeat_next_time`, `repeat_progress`, `btn_type_simple`, `btn_type_repeat`, `btn_no_time` |
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
| `handlers_callbacks.py` | 165 | **Dispatcher**: darhol `answer_callback_query` (timeout oldini oladi), umumiy preamble (til, obuna) + 6 ta sub-handlerga yo'naltirish. `ack_delete_msg` — universal xabar o'chirish |
| `handlers_text.py` | ~1031 | Barcha matn xabarlari (state machine), repeat odat vaqt so'rash T() bilan, Telegram Stars to'lov, broadcast, inline query. Import tuzatilgan: `time`, `schedule`, `user_exists`, `admin_menu`, `load_settings`, `save_settings` |
| `handlers_rating.py` | 381 | PIL bilan reyting rasmi generatsiyasi (top-10 grid), `show_rating()`. Import tuzatilgan: `datetime`, `save_user` |
| `handlers_stats.py` | 438 | `show_stats()`, haftalik/oylik/yillik hisobot generatsiyasi va yuborish. Import tuzatilgan: `time`, `mongo_col`, `main_menu` |

### Callback sub-modullar

| Fayl | Qatorlar | Vazifasi |
|------|----------|----------|
| `callbacks_admin.py` | 428 | Admin: broadcast, foydalanuvchilar ro'yxati, kanal sozlash, ball berish, statistika. Import tuzatilgan: `time`, `threading` |
| `callbacks_settings.py` | ~369 | Sozlamalar: til, odat vaqtlari (repeat\_times tozalash tuzatildi), ism, telefon o'zgartirish. Tahrirlash matnlari T() bilan 3 tilga. Import tuzatilgan: `time`, `threading`, `schedule`, `ReplyKeyboardMarkup`, `KeyboardButton`, `lang_keyboard` |
| `callbacks_habits.py` | ~756 | Odat qo'shish (`menu_add`) — ~~odat limiti tekshiruvi~~ **VAQTINCHA OʻCHIRILGAN**, turi tanlash (T() bilan 3 tilga), repeat count so'rash, o'chirish, `toggle_` (bajarish), `done_`, `skip_`, shield. Import tuzatilgan: `time`, `threading`, `schedule` |
| `callbacks_menu.py` | 347 | Menyu navigatsiya, hisobot ro'yxatlari (weekly/monthly/yearly view). Import tuzatilgan: `time`, `threading` |
| `callbacks_groups.py` | 564 | Guruh yaratish/o'chirish, a'zo qo'shish/chiqarish, guruh reytingi, guruh odat bajarish. Import tuzatilgan: `time`, `threading` |
| `callbacks_shop.py` | 272 | Bozor: jon sotib olish, referral, ball transfer, tahrirlash, reset. Import tuzatilgan: `time`, `threading` |

### Guruh va jadval

| Fayl | Qatorlar | Vazifasi |
|------|----------|----------|
| `groups.py` | ~375 | `_save_new_habit()` (repeat\_times + repeat\_count to'g'ri saqlaydi, schedule\_habit ni repeat uchun chaqiradi), `_send_group_view()`, `_build_group_rating()`, `_save_new_group()`. Import tuzatilgan: `time`, `threading` |
| `scheduler.py` | ~779 | `send_reminder()`, `daily_reset()`, `schedule_habit()` (repeat\_times ro'yxatini qo'llab-quvvatlaydi — har bir vaqt uchun alohida schedule), `_uz5_to_utc()`, `scheduler_loop()`, `send_evening_reminders()`. Import tuzatilgan: `mongo_col`, `groups_col`, `mongo_db` (config dan) |

### Flask Web App API

| Fayl | Qatorlar | Vazifasi |
|------|----------|----------|
| `flask_api.py` | 35 | Flask app yaratish, route modullarni ro'yxatdan o'tkazish, `run_api()` |
| `flask_helpers.py` | 132 | CORS, rate limiter, `verify_init_data()`, `require_auth()` dekorator |
| `flask_routes_core.py` | ~581 | `/api/rating`, `/api/profile` (GET + PUT), `/api/habits` CRUD (repeat\_times qo'llab-quvvatlaydi: GET da `times` qaytaradi, POST/PUT da `repeat_times`/`times` qabul qiladi — ~~POST da 15 ta odat limiti~~ **VAQTINCHA OʻCHIRILGAN**), `/api/groups` CRUD. **Import tuzatish:** `mongo_db`, `mongo_col` (config dan), `ACHIEVEMENTS` qo'shildi |
| `flask_routes_data.py` | 496 | `/api/today` (har bir odatda `days_66_done` va `times` qaytaradi), `/api/checkin` (bajarish logikasi), `/api/stats` |
| `flask_routes_extra.py` | ~822 | `/api/achievements`, `/api/shop` (buy da `owned` qaytaradi), `/api/friends`, `/api/challenges`, `/api/reminder` (repeat\_times, reminder\_enabled, repeat qo'llab-quvvatlaydi), `/health`, `/favicon.ico` (204), webhook. **Import tuzatish:** `telebot`, `InlineKeyboardMarkup/Button`, `ACHIEVEMENTS as _ACHIEVEMENTS`, `CAT_LABELS` qo'shildi |

### Frontend (Telegram WebApp)

| Fayl | Qatorlar | Vazifasi |
|------|----------|----------|
| `index.html` | 267 | HTML tuzilma: header, **global PTR indikator** (barcha sahifalar uchun), tablar, sahifalar (page-today, page-stats, page-profile...), modallar, bottom nav, badge popup. Hech qanday JS/CSS yo'q |
| `style.css` | ~1230 | Barcha CSS: `:root` ranglar, dark mode, neumorphism shadow'lar, `.header` da `--tg-safe-top` safe area padding, card/button/modal/toast/nav stillar, animatsiyalar (spin, fadeIn, slideUp, confetti), PTR indikator (yuqori + pastki), nav ball glow pulsatsiya (`ballGlow`), toʻlqin ripple effekti (`navRippleWave`), **checkin-card swipe-to-reveal** (`.checkin-front`, `.checkin-actions-bg`, `.cswipe-btn`, `.cswipe-close`), **3-nuqta dropdown** (`.checkin-dots-btn`, `.checkin-dropdown`, `.checkin-dropdown-close`, `cdropIn` animatsiya) |
| `strings.js` | ~891 | `STRINGS` obyekt (UZ/RU/EN tarjimalar), `S(key, sub)` funksiya, `selectedLang`, `currentLang` o'zgaruvchilari. `days_left` — "Odat shakllanishiga {n} kun qoldi" (3 tilda). `habits.edit_btn`/`habits.delete_btn` — swipe va dropdown tugmalari matni (3 tilda) |
| `app-core.js` | 383 | Telegram WebApp init (`tg.ready()`, `tg.expand()`, `tg.requestFullscreen()`, `tg.disableVerticalSwipes()`, `applySafeArea()` — CSS `--tg-safe-top` variable), `user`/`userId`/`API` konstantalari, `data`/`loaded` state, `switchTab()`/`goBack()`/`loadTab()` (profil va bozor har safar qayta yuklanadi), `apiFetch()` (20s timeout), `showPremiumPage()`/`renderPremium()`/`buyPremium()`, `ringHTML()`/`jonRingHTML()` SVG generatorlar, `spawnNavRipple()` toʻlqin effekti |
| `app-pages.js` | ~700 | **Bugun**: `loadToday()`, `renderToday()` (har bir odat kartochkasida 66-kun compact progress bar, **swipe-to-reveal** tahrirlash/oʻchirish tugmalari), `checkin()` (done/undo, repeat dots, confetti, badge popup, streak milestone), `checkinFromFront()` (swipe himoyali checkin), `showTodayToast()`. **Swipe**: `_initCheckinSwipe()`, `closeAllCheckinSwipes()` — chapga surish orqali ✕/Edit/Delete tugmalar ochiladi. **3-nuqta tugma**: `toggleCheckinDrop()` — swipe bilan bir xil natija beradi (dropdown emas, swipe ochiladi), `closeAllCheckinDrops()`. **Eslatmalar**: `loadReminders()`, `renderReminders()`, `toggleReminder()`, `setRepeat()`, `addTime()`/`removeTime()`, `saveReminder()`. **Yutuqlar**: `loadAchievements()`, `renderAchievements()`, `filterAch()`, `showBadgePopup()`/`nextPopup()` |
| `app-stats.js` | 857 | **Statistika**: `loadStats()`, `renderStats()` (summary grid, bar chart, 30-kun area chart, haftalik trend, heatmap, har bir odat statistikasi), `toggleHabitStats()`, `generateShareCard()` (Canvas PNG). **Reyting**: `loadRating()`, `renderRating()` (podium top-3, qator 4-10, sort/period switch), `userAvatarHTML()`, `setRatSort()`/`setRatPeriod()` |
| `app-profile.js` | 506 | **Profil**: `loadProfile()`, `renderProfile()` (avatar: `d.photo_url || user.photo_url` — DB dagi rasm birinchi oʻrinda, stats grid, jon bar, yutuqlar, odatlar, referral, sozlamalar — ~~premiumBadge (Free/Premium yozuvi)~~ **VAQTINCHA OʻCHIRILGAN**). **Tahrirlash**: `openEditProfile()`, `saveEditProfile()`, `previewEpPhoto()`. **Sozlama**: `updateNavLabels()`, `setLang()`, `openLangModal()`/`saveLang()`, `saveDarkMode()`, `saveEveningNotify()`, `updateToggleVisual()` |
| `app-habits.js` | ~360 | **Odatlar CRUD**: `loadHabits()`, `renderHabits()`, `openAdd()`/`openEdit()` (times array qoʻllab-quvvatlaydi), `saveHabit()` (`repeat_times` API ga yuboradi), `deleteHabit()`, `closeModal()`, `showToast()`. **Dinamik vaqt inputlari**: `_buildTimeInputs(count, existingTimes)`, `addHabitTime()`, `_onRepeatCountChange()` — repeat_count oʻzgarganda vaqt inputlari soni avtomatik moslashadi. **Icon picker**: `ICON_CATS` (10 kategoriya), `selectIconCat()`, `selectIcon()`. ~~Premium limit tekshiruvi~~ **VAQTINCHA OʻCHIRILGAN** — odat qoʻshishda cheklov yoʻq, barcha foydalanuvchilar cheksiz odat qoʻsha oladi. `openAddFromToday()` — today sahifasidan qoʻshish |
| `app-social.js` | 1073 | **Guruhlar**: `loadGroups()`, `renderGroups()`, `saveGroup()`, `deleteGroup()`, `groupCheckin()`, `setGroupGoal()`. **Do'stlar**: `loadFriends()`, `renderFriends()`, `searchFriends()`, `addFriend()`, `removeFriend()`. **Shop**: `loadShop()`, `renderShop()`, `buyItem()` (sotib olish/sotishda `data.profile.points` va `loaded.profile` yangilanadi), `sellItem()`, `activateItem()`. **Challenge**: `openChallenge()`, `sendChallenge()`, `acceptChallenge()`, `rejectChallenge()`. **Onboarding**: `maybeShowOnboard()`, `obMarkDone()`, `renderOnboard()`. **Init**: `window.onload`, `visibilitychange`. **Ovoz**: `playHabitSound()` (done=celebration chime 4-nota marimba+shimmer, undo=soft whomp-down), `playProgressSound(step, total)` (repeat odat oraliq progress — ko'tariluvchi pop). **PTR**: pull-to-refresh universal touch handler — yuqoridan va pastdan (barcha asosiy sahifalar uchun; ichki sahifalar — achievements/reminders/premium — bundan mustasno) |

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

**WebApp UI/stil o'zgartirmoqchimisiz?**
→ `style.css` (CSS) + tegishli `app-*.js` (render funksiyasi)

**WebApp tarjima qo'shmoqchimisiz?**
→ `strings.js` (`STRINGS` ichida UZ/RU/EN ga qo'shish)

**Yangi WebApp sahifa qo'shmoqchimisiz?**
→ `index.html` (HTML), `style.css` (stil), tegishli `app-*.js` (mantiq), `app-core.js` (`loadTab` ichiga qo'shish)

**WebApp checkin/today mantiqini o'zgartirmoqchimisiz?**
→ `app-pages.js` (`checkin()`, `renderToday()`)

**WebApp shop/guruh/do'st o'zgartirmoqchimisiz?**
→ `app-social.js`

---

## ⚠️ Muhim eslatmalar

1. **Import tartibi muhim**: `habit_bot.py` dagi import tartibi handlerlarni telebot'da ro'yxatdan o'tkazadi
2. **Circular import yo'q**: `schedule_habit` va shunga o'xshash funksiyalar lazy import (`from scheduler import ...` funksiya ichida) ishlatadi
3. **Callback dispatcher**: `handlers_callbacks.py` barcha callback'larni oladi va sub-modullarga yo'naltiradi — sub-modul `True` qaytarsa, boshqasiga o'tmaydi
4. **Flask routes**: `register_*_routes(app)` funksiyalari orqali ro'yxatdan o'tadi — `flask_api.py` dan chaqiriladi
5. **Frontend script tartibi muhim**: `strings.js` → `app-core.js` (head da), keyin `app-pages.js` → `app-stats.js` → `app-profile.js` → `app-habits.js` → `app-social.js` (body oxirida). Tartibni buzish global o'zgaruvchilarning topilmasligiga olib keladi
6. **Frontend cache-busting**: barcha `<script src>` va `<link href>` larda `?v=417` query string bor — yangilanganda versiyani oshiring
7. **Frontend cross-file calls**: funksiyalar global scope da, lekin ko'pchiligi faqat user action (onclick) da chaqiriladi — shuning uchun yuklash tartibida xato bo'lmaydi
8. **Frontend `window.onload`**: `app-social.js` da — barcha fayllar yuklanganidan keyin `loadToday()` chaqiriladi
