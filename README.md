# 🧭 Super Habits Bot — Modular Tuzilma

> ## ⚠️ CLAUDE UCHUN MUHIM ESLATMA
> **1. Cache-busting (MAJBURIY):** Frontend fayllar (`*.css`, `app-*.js`, `strings.js`) o'zgartirilganda — `index.html` dagi `?v=NNN` versiyasini AVTOMATIK +1 ga oshirish SHART. Foydalanuvchidan so'ramaslik. Batafsil: 5-qoida.
> **2. README yangilash (MAJBURIY):** Har o'zgarishdan keyin README'ga nima qo'shish va nima qo'shmaslik haqida aniq qoidalar bor. Versiya raqamlari, revert zanjirlari, "YANGI" belgilari README'ga **YOZILMAYDI** — bular git vazifasi. Batafsil: 21-qoida (Decision tree, triggerlar, misollar).

> **Backend:** 9 382 qatorlik monolitik `habit_bot.py` → 28 ta mustaqil modul
> **Frontend:** 5 739 qatorlik monolitik `index.html` → 9 ta mustaqil fayl
> **Dizayn:** NASA-style minimalist rang intizomi (yagona yashil `#4CAF7D` accent + neytrallar + qizil faqat xavf uchun), neumorphism 2.0, Streaks/Habitify uslubidagi "faded done" karta ierarxiyasi
> **Bozor:** 15 ta mahsulot (14 ball + 1 Stars `gift_box`), race condition fix (per-user threading.Lock + 3s timeout), info modal + sotib olish tasdig'i, narxlar `config.py` da markazlashtirilgan (`SHOP_PRICES`, `SHOP_SELL_PRICES`, `SHOP_STARS_PRICES`, `SHOP_BONUS_EFFECTS`), 3 tilga to'liq tarjima
> **Inventory "Trofey ko'rgazmasi":** reyting (podium, 4-10 rows, myRow) va profil sahifalarida eng qimmat top-1 emoji + qolgani `+N` (masalan `👑 +8`) — nodir buyumlar bilan passiv maqtanish
> **Header ball markaziy helper:** `updateHeaderPts(points)` — DOM + global state sinxron yangilanadi (yangi endpoint ball o'zgartirganda faqat shu chaqiriladi, inline kod yozilmaydi)
> **Touch gesture lock:** swipe va PTR uchun intent detection (dastlabki 8px da yo'nalish "locked" bo'ladi — diagonal harakat, gorizontal siljishda PTR chiqmaydi)
> **Celebration loop:** oxirgi odat bajarilganda konfetti (42 ta zarrachalar) + "Barchasi bajarildi!" karta 3s keyin kollaps + hero bayram emoji (🎉 SVG) + reytingda avatar ustida yashil zar (5 ta zarracha) — hammasi NASA yashil palitrasida

---

## 🚀 Ishga tushurish

```bash
pip install pyTelegramBotAPI schedule pymongo flask Pillow
python habit_bot.py
```

Barcha `.py` fayllar **bitta papkada** turishi kerak.

---

## 📁 Fayl tuzilmasi

### Backend (Python)

```
super_habits/
│
├── habit_bot.py              ← ASOSIY ENTRY POINT
│
├── ─── YADRO ──────────────────────────────────────────
├── config.py                 ← Sozlamalar, MongoDB, SHOP_PRICES/SELL/STARS/BONUS_EFFECTS
├── database.py               ← CRUD: load/save user, group, settings, cache
├── texts.py                  ← LANGS dict (uz/en/ru tarjimalar)
├── motivation.py             ← Motivatsiya matnlari
├── helpers.py                ← T(), get_lang(), today_uz5()
│
├── ─── BOT VA UI ──────────────────────────────────────
├── bot_setup.py              ← Bot instance, tugmalar, menyu yordamchilari
├── menus.py                  ← 2-menyu, obuna tekshirish, admin menyulari
├── achievements.py           ← Yutuqlar ro'yxati va tekshiruvi
│
├── ─── HANDLERLAR ─────────────────────────────────────
├── handlers_commands.py      ← /start, /admin_panel, kontakt qabul qilish
├── handlers_callbacks.py     ← Callback DISPATCHER (sub-modullarga yo'naltiradi)
├── handlers_text.py          ← Matn xabarlari, Stars to'lov, broadcast, inline query
├── handlers_rating.py        ← Reyting rasm generatsiyasi (PIL)
├── handlers_stats.py         ← Statistika, haftalik/oylik/yillik hisobotlar
│
├── ─── CALLBACK SUB-MODULLAR ─────────────────────────
├── callbacks_admin.py        ← Admin panel
├── callbacks_settings.py     ← Sozlamalar: til, vaqt, ism
├── callbacks_habits.py       ← Odat: qo'shish, o'chirish, toggle, done, skip
├── callbacks_menu.py         ← Menyu navigatsiya
├── callbacks_groups.py       ← Guruh: yaratish, a'zo, reyting
├── callbacks_shop.py         ← Bozor: jon, referral, transfer, reset
│
├── ─── GURUH VA JADVAL ────────────────────────────────
├── groups.py                 ← Guruh funksiyalari + yangi odat saqlash
├── scheduler.py              ← Eslatmalar, kunlik reset, pet_cat/pet_rabbit bonuslar
│
├── ─── FLASK WEB APP API ──────────────────────────────
├── flask_api.py              ← Flask app yaratish va route registratsiya
├── flask_helpers.py          ← CORS, rate limiter, Telegram auth
├── flask_routes_core.py      ← API: rating, profile, habits, groups CRUD
├── flask_routes_data.py      ← API: today, checkin, stats
└── flask_routes_extra.py     ← API: achievements, shop, friends, challenges, webhook
```

### Frontend (Telegram WebApp)

```
super_habits/static/
│
├── index.html               ← (~283 qator) HTML layout, splash, modallar, nav
├── style.css                ← (~2127 qator) neumorphism, dark mode, animatsiyalar
├── strings.js               ← (~1074 qator) UZ/RU/EN tarjimalar, S() funksiya
│
├── ─── JS YADRO ──────────────────────────────────────
├── app-core.js              ← (~396 qator) TG init, API, state, tabs, updateHeaderPts
│
├── ─── JS SAHIFALAR ──────────────────────────────────
├── app-pages.js             ← (~730 qator) Bugun, checkin, eslatmalar, yutuqlar, glow ring
├── app-stats.js             ← (~1235 qator) Statistika, chartlar, heatmap, reyting, inventory modal
├── app-profile.js           ← (~617 qator) Profil, tahrirlash, til, dark mode, referral
├── app-habits.js            ← (~380 qator) Odatlar CRUD, icon picker, modal
└── app-social.js            ← (~1432 qator) Guruh, do'st, shop, challenge, init, PTR
```

---

## 🔗 Modullar orasidagi bog'liqlik

### Backend

```
habit_bot.py (entry point)
    │
    ├── config.py ............... hech nimaga bog'liq emas
    ├── database.py ............. config
    ├── texts.py, motivation.py . hech nimaga bog'liq emas
    ├── helpers.py .............. database, texts
    │
    ├── bot_setup.py ............ config, database, helpers
    ├── menus.py ................ database, helpers, bot_setup
    ├── achievements.py ......... database, bot_setup, helpers
    │
    ├── handlers_commands.py .... config, database, helpers, bot_setup, menus
    ├── handlers_callbacks.py ... → dispatcher (6 ta callbacks_* ga yo'naltiradi)
    ├── handlers_text.py ........ database, helpers, bot_setup, groups, scheduler
    ├── handlers_rating.py ...... database, helpers, bot_setup
    ├── handlers_stats.py ....... database, helpers, bot_setup
    │
    ├── groups.py ............... database, helpers, bot_setup, menus
    ├── scheduler.py ............ database, helpers, bot_setup, handlers_stats
    │
    └── flask_api.py ............ flask_helpers + 3 ta route modul
```

### Frontend

```
index.html (WebApp entry point)
    │
    ├── style.css ................ (CSS)
    ├── strings.js ............... selectedLang, currentLang, STRINGS, S()
    │
    ├── app-core.js .............. strings.js
    │   ↑ tg, user, userId, API, data, loaded
    │   ↑ switchTab, loadTab, apiFetch, ringHTML, jonRingHTML
    │   ↑ updateHeaderPts (markaziy ball yangilagich)
    │
    ├── app-pages.js ............. strings.js, app-core.js
    │   ↑ loadToday, renderToday, checkin, loadReminders, loadAchievements
    │
    ├── app-stats.js ............. strings.js, app-core.js
    │   ↑ loadStats, renderStats, loadRating, renderRating, userAvatarHTML
    │
    ├── app-profile.js ........... strings.js, app-core.js, app-pages.js
    │   ↑ loadProfile, renderProfile, setLang, saveDarkMode
    │
    ├── app-habits.js ............ strings.js, app-core.js
    │   ↑ loadHabits, openAdd, openEdit, saveHabit, ICON_CATS
    │
    └── app-social.js ............ strings.js, app-core.js + barcha yuqoridagilar
        ↑ loadGroups, loadFriends, loadShop, buyItem, window.onload, PTR
```

---

## 📋 Har bir fayl nima qiladi

### Yadro modullari

| Fayl | Qatorlar | Vazifasi |
|------|----------|----------|
| `config.py` | ~109 | `BOT_TOKEN`, `ADMIN_ID`, `MONGO_URI` (DB nomi oxiridan avtomatik — staging/prod ajratish), MongoDB ulanish va indekslar. **Bozor markazlashtirilgan:** `SHOP_PRICES` (14 mahsulot), `SHOP_SELL_PRICES` (12 × 50%), `SHOP_STARS_PRICES` (`gift_box`: 5 Stars), `SHOP_ONE_TIME` (bir martalik nishon/pet/car), `SHOP_BONUS_EFFECTS` (7 ta mahsulot vazifasi: badge_fire/star/secret points_percent 3/5/12%, car_sport 8%, pet_cat streak_save 7 kun, pet_dog daily_bonus +2, pet_rabbit jon_soften 50%) |
| `database.py` | 111 | `load_user`, `save_user`, `load_group`, `save_group`, `load_all_users` (60s cache), `count_users`, `user_exists` (3x retry) |
| `texts.py` | ~424 | `LANGS` dict — uz/en/ru (3 til, har birida 156+ kalit). Repeat odat kalitlari, bozor bot callback kalitlari (`bozor_*` — 27 ta × 3 til), Stars faqat `gift_box` uchun |
| `motivation.py` | 111 | `MOTIVATSIYA` dict — motivatsion gaplar |
| `helpers.py` | 51 | `T(uid, key)`, `get_lang()`, `today_uz5()`, `get_rank()`, `lang_keyboard()` |

### Bot va UI

| Fayl | Qatorlar | Vazifasi |
|------|----------|----------|
| `bot_setup.py` | 142 | `bot` instance, `send_message_colored()`, `cBtn()`, `ok_kb(uid)`, `main_menu_dict()` |
| `menus.py` | 167 | `menu2_dict()`, `check_subscription()`, `admin_menu()`, `admin_broadcast_menu()` |
| `achievements.py` | 55 | `_ACHIEVEMENTS` ro'yxati, `check_achievements_toplevel()` |

### Handlerlar

| Fayl | Qatorlar | Vazifasi |
|------|----------|----------|
| `handlers_commands.py` | 362 | `/start`, til tanlash, deep link, `/admin_panel`, kontakt qabul qilish |
| `handlers_callbacks.py` | 165 | **Dispatcher**: darhol `answer_callback_query` → umumiy preamble (til, obuna) → 6 ta sub-handlerga yo'naltirish. `ack_delete_msg` — universal xabar o'chirish |
| `handlers_text.py` | ~1065 | Matn xabarlari (state machine), Stars to'lov (faqat `gift_box`: random 100/200/500 ball, 1 shield, 3 kun XP booster), broadcast, inline query |
| `handlers_rating.py` | 381 | PIL bilan reyting rasm generatsiyasi (top-10 grid) |
| `handlers_stats.py` | 438 | `show_stats()`, haftalik/oylik/yillik hisobot generatsiyasi |

### Callback sub-modullar

| Fayl | Qatorlar | Vazifasi |
|------|----------|----------|
| `callbacks_admin.py` | 428 | Broadcast, foydalanuvchilar ro'yxati, kanal sozlash, ball berish, statistika |
| `callbacks_settings.py` | ~369 | Til, odat vaqtlari, ism/telefon o'zgartirish — 3 tilga |
| `callbacks_habits.py` | ~756 | Odat qo'shish, turi tanlash (simple/repeat), repeat count, o'chirish, `toggle_`/`done_`/`skip_`, shield |
| `callbacks_menu.py` | 347 | Menyu navigatsiya, hisobot ro'yxatlari (weekly/monthly/yearly) |
| `callbacks_groups.py` | 564 | Guruh yaratish/o'chirish, a'zo qo'shish/chiqarish, guruh reyting va checkin |
| `callbacks_shop.py` | 248 | Jon sotib olish, referral, ball transfer, tahrirlash, reset — 3 tilga. Narxlar `config.py` dan. Helper: `_bozor_back_row(uid)` |

### Guruh va jadval

| Fayl | Qatorlar | Vazifasi |
|------|----------|----------|
| `groups.py` | ~375 | `_save_new_habit()` (repeat_times + repeat_count), `_send_group_view()`, `_build_group_rating()`, `_save_new_group()` |
| `scheduler.py` | ~864 | `send_reminder()`, `daily_reset()`, `_try_pet_cat_save()` (7 kunda 1 marta streak saqlash), `_apply_pet_rabbit_soften()` (jon jazosi 50% yumshatish), `schedule_habit()` (repeat_times massivini qo'llab-quvvatlaydi), `_uz5_to_utc()`, `scheduler_loop()`, `send_evening_reminders()` |

### Flask Web App API

| Fayl | Qatorlar | Vazifasi |
|------|----------|----------|
| `flask_api.py` | 35 | Flask app yaratish, route modullarni ro'yxatdan o'tkazish, `run_api()` |
| `flask_helpers.py` | 132 | CORS, rate limiter, `verify_init_data()`, `require_auth()` dekorator |
| `flask_routes_core.py` | ~644 | `/api/rating`, `/api/profile` (GET + PUT bio, max 200 belgi), `/api/habits` CRUD (repeat_times), `/api/groups` CRUD. **Inventory:** `items_count` + `items_list: [{id, qty, price}, ...]` maydonlari — frontend `S('inventory','item_'+id)` orqali tarjima qiladi, top-1 emoji tanlash uchun `price` ham yuboriladi |
| `flask_routes_data.py` | ~596 | `/api/today` (`days_66_done`, `times`), `/api/checkin` — **badge/car ball bonus** (`_apply_item_bonuses()`: `SHOP_BONUS_EFFECTS` dan foiz + B variant majburiy +1 kafolat, stack qilinadi), **pet_dog kunlik +2** (`_apply_pet_dog_bonus()`), **har odat uchun `best_streak`** (streak oshgach `max(h["best_streak"], h["streak"])`). `/api/stats` — `summary.streak` = barcha odatlar streaklari yig'indisi, `summary.best_streak` = all-time rekord |
| `flask_routes_extra.py` | ~868 | `/api/achievements`, **`/api/shop`** (15 mahsulot: 14 ball + 1 Stars `gift_box`), **`/api/shop/buy`** (per-user `threading.Lock` + 3s timeout → 429), **`/api/shop/sell`**, **`/api/shop/activate`** (hammasi lock bilan himoyalangan), **`/api/shop/stars_invoice`**, `/api/friends`, `/api/challenges`, `/api/reminder`, `/api/share-card`, webhook. Helper: `_get_shop_lock(uid)` lazy per-user lock |

### Frontend (Telegram WebApp)

| Fayl | Qatorlar | Vazifasi |
|------|----------|----------|
| `index.html` | ~283 | HTML layout: **splash screen** (haqiqiy bot logo `<img>` `id="splash-logo"`, orbit ring, bouncing dots, 5s → header yuqori chapga uchadi), **header** (logo shaffof fonli inline base64 PNG, neumorphism foniga to'g'ridan-to'g'ri tushadi), **global PTR indikator**, tablar, sahifalar, modallar, bottom nav, badge popup. Hech qanday JS/CSS yo'q |
| `style.css` | ~2127 | `:root` ranglar (NASA yashil `#4CAF7D`), dark mode, **neumorphism 2.0** shadow'lar (`--sh-out/in/press/sm/btn`), safe area padding, card/button/modal/toast/nav, animatsiyalar (spin, fadeIn, slideUp, confetti, ripple, glow, ballGlow). **Checkin kartochka:** 44×44 neumorphic inset icon, swipe-to-reveal (`.checkin-front`/`.checkin-actions-bg`, subpixel `bottom:1px` fix), 3-nuqta dropdown, pending tugmada yashil ✓ (`:empty::before`) + nozik halqa + aylanuvchi glow SVG ring, `done` karta "faded" `opacity: 0.45` + yashil gradient tugma (Streaks/Habitify pattern). **Profile:** `.profile-chips`/`.profile-chip` (inventory banda + press effekti), `.profile-bar-row` (JON/achievements). **Reyting:** `.inv-badge-clickable` (avatar ustida yashil zar `.avatar-snow-*`). **Bozor:** `.shop-*` (balance, cats, item, buy/sell btn, info-btn, modal-overlay/box). **Today:** `.today-add-btn` (neumorphic "+ Odat yaratish"). **Celebration:** `all-done-banner` (avto-kollaps 3s), `hero-party-badge` (SVG 🎉), konfetti (42 ta zarracha 3 darajali yashil) |
| `strings.js` | ~1074 | `STRINGS` obyekt (UZ/RU/EN), `S(key, sub)` funksiya. Asosiy kalitlar: `profile.bio_*`, `shop.cat_*`/`info_*`/`confirm_*`, `bozor.info_*` (14 mahsulot vazifasi), `inventory.*` (17 kalit — badge_label, modal_*, 11 item nomi), `msg.sell_*`/`copy_link`, `today.add_habit`, `stats.streak_total_label` |
| `app-core.js` | ~396 | TG init (`tg.ready/expand/requestFullscreen/disableVerticalSwipes`, `applySafeArea` → `--tg-safe-top`), `user`/`userId`/`API`, `data`/`loaded` state, `switchTab`/`goBack`/`loadTab` (profil va bozor har safar qayta yuklanadi, `_tabLoading` lock double-tap himoya), `apiFetch` (20s timeout), **`updateHeaderPts(points)` markaziy helper** (DOM `#header-pts` + `data.today/profile.points` sinxron — yangi endpoint ball o'zgartirganda faqat shu chaqiriladi), `ringHTML`/`jonRingHTML` SVG generatorlar (3 darajali yashil gradient, JON `<30%` qizil), `spawnNavRipple`, `showPremiumPage` |
| `app-pages.js` | ~730 | **Bugun:** `loadToday`, `renderToday` (66-kun compact progress bar, swipe-to-reveal, `.today-add-btn`, **pending habit SVG glow ring** — `<svg class="habit-glow-ring">` aylanuvchi yashil nur, matn `.checkin-btn-content` span ichida), `checkin` (done/undo, repeat dots, **konfetti + `_triggerConfetti`**, badge popup, streak milestone, **`wasAllDone` boolean** — konfetti faqat yangi yutuqda, **hero bayram emoji `_partySvg` SVG** yuqori-o'ng burchakda + `bannerCollapse` 3s keyin joyni bo'shatadi, **glow SVG ga tegmaydi** — faqat `.checkin-btn-content` yangilanadi, undo paytida `animation-delay` bilan sinxronlash). **Swipe:** `_initCheckinSwipe` + gesture intent lock (touchmove `passive:false`, gorizontal `locked` bo'lganda `preventDefault`). **Eslatmalar**, **Yutuqlar** |
| `app-stats.js` | ~1235 | **Statistika:** `loadStats`, `renderStats` (summary, bar chart, 30-kun area, haftalik trend, heatmap, har odat), `generateShareCard` (Canvas PNG). **Reyting:** `loadRating`, `renderRating` (podium top-3, qator 4-10, sort/period), `userAvatarHTML` (agar `u.today_done` → `avatar-snow-wrap` wrapper bilan 5 ta yashil zar), `setRatSort`/`setRatPeriod`. **Inventory:** `window._invCache` (XSS safe onclick), `_invKey`/`_invBadgeDisplay(u)` (price bo'yicha top-1 emoji + `+N`), `openUserInventoryByKey` → `openUserInventory` modal (`.shop-modal-*` qayta ishlatilgan, `INV_EMOJI` dict, `_invEscapeHtml`, `requestAnimationFrame` → `.show` fade animatsiya), `closeUserInventory` |
| `app-profile.js` | ~617 | `loadProfile`, `renderProfile` (avatar `d.photo_url`, bio XSS himoyali, jon bar, achievements progress bar, **referral kompakt tugma** `rem-card` patternida, **inventory kompakt banda** `🎒 N` → `openUserInventoryByKey('profile_me')` app-stats modali qayta ishlatiladi; `d.active_pet`/`active_badge` tegilmagan). **Modal:** `openReferralModal`/`closeReferralModal` (bonuslar, 3 milestone, referral link, gradient "Havolani nusxalash", ✕, haptic). **Tahrirlash:** `openEditProfile` (bio textarea 200 belgi + counter), `saveEditProfile` (loading holat). **Sozlamalar:** `updateNavLabels`, `setLang`/`openLangModal`/`saveLang`, `saveDarkMode`, `saveEveningNotify`, `copyRefLink` (clipboard + fallback) |
| `app-habits.js` | ~380 | `loadHabits`, `renderHabits`, `openAdd`/`openEdit`, `saveHabit` (`repeat_times` API), `deleteHabit`, `closeModal`. **Dinamik vaqtlar:** `_buildTimeInputs`, `addHabitTime`, `_onRepeatCountChange`, `_sortHabitTimes` (avtomatik chronologik). **Icon picker:** `ICON_CATS` (10 kategoriya, neumorphic 3D dome dizayn), `selectIconCat`, `selectIcon`, `_buildIconGrid`. `openAddFromToday` — today sahifasidan |
| `app-social.js` | ~1432 | **Guruhlar:** `loadGroups`, `renderGroups`, `saveGroup`, `groupCheckin` (`updateHeaderPts(r.points)` done/undo branch'larda). **Do'stlar:** `loadFriends`, `searchFriends`, `addFriend`, `removeFriend`. **Shop:** `_shopData`/`_shopContentId`/`_shopCat`, `_shopActionLock = new Set()` double-tap guard, `loadShop`, `renderShop` (7 kategoriya: all/protection/bonus/badge/pet/car/gift), **`openShopInfo`** (info modal — emoji, nom, vazifa `bozor.info_*`, narx, sotish narxi), **`confirmBuyItem`** → `_doConfirmedBuy` → `_executeBuy` (zanjir: tasdiq → lock → `updateHeaderPts`), `sellItem`/`activateItem`, `closeShopModal` (overlay bosish ham), haptic feedback. **Challenge**, **Init** (`window.onload`: splash 5s → `loadToday`, visibilitychange). **PTR:** pull-to-refresh (yuqori + pastki, intent lock: `|dx| > |dy|` → bekor, `|dy| > 8` → locked). **Ovoz:** `playHabitSound`, `playProgressSound` |

---

## ✏️ Qanday tahrirlash kerak

**Yangi odat turi qo'shmoqchimisiz?** → `callbacks_habits.py` + `groups.py` (`_save_new_habit`)

**Yangi API endpoint qo'shmoqchimisiz?** → `flask_routes_core.py` yoki `flask_routes_extra.py`

**Matn/tarjima o'zgartirmoqchimisiz?** → `texts.py` (bot) yoki `strings.js` (WebApp) — 3 tilga ham qo'shing

**Yangi callback tugma qo'shmoqchimisiz?** → Tegishli `callbacks_*.py` + `handlers_callbacks.py` dispatcherda tartibni tekshiring

**Scheduler/eslatma o'zgartirmoqchimisiz?** → `scheduler.py`

**WebApp UI/stil o'zgartirmoqchimisiz?** → `style.css` + tegishli `app-*.js` (render funksiyasi). **Inline CSS yozmang — class'lardan foydalaning**

**Yangi WebApp sahifa qo'shmoqchimisiz?** → `index.html` (layout), `style.css`, tegishli `app-*.js`, `app-core.js` (`loadTab` ichiga)

**WebApp checkin/today mantiqini o'zgartirmoqchimisiz?** → `app-pages.js` (`checkin`, `renderToday`)

**Bozor narxini o'zgartirmoqchimisiz?** → **Faqat `config.py`** (`SHOP_PRICES`/`SELL_PRICES`/`STARS_PRICES`). Hardcode ishlatmang — bir joy, hamma joy avtomatik

**Yangi bozor mahsuloti qo'shmoqchimisiz?** → 4 fayl: (1) `config.py` `SHOP_PRICES`+`SHOP_ONE_TIME`; (2) `texts.py` nom/tavsif 3 tilga; (3) `flask_routes_extra.py` `shop_items`+`_shop_i18n`; (4) agar Stars — `handlers_text.py` `handle_successful_payment` reward logikasi

**Yangi endpoint ball o'zgartirmoqchimisiz?** → Inline `getElementById('header-pts')` YOZMAYMIZ — `updateHeaderPts(r.points)` helper chaqiring (DRY)

---

## ⚠️ Muhim eslatmalar (arxitektura qoidalari)

### 1. Import tartibi muhim
`habit_bot.py` dagi import tartibi handlerlarni telebot'da ro'yxatdan o'tkazadi. Circular import yo'q — `schedule_habit` kabi funksiyalar lazy import (`from scheduler import ...` funksiya ichida).

### 2. Callback dispatcher
`handlers_callbacks.py` barcha callback'larni oladi va 6 ta sub-modulga yo'naltiradi — sub-modul `True` qaytarsa, boshqasiga o'tmaydi.

### 3. Flask routes
`register_*_routes(app)` funksiyalari orqali ro'yxatdan o'tadi — `flask_api.py` dan chaqiriladi.

### 4. Frontend script tartibi muhim
`strings.js` → `app-core.js` (`<head>` da), keyin `app-pages.js` → `app-stats.js` → `app-profile.js` → `app-habits.js` → `app-social.js` (body oxirida). Tartibni buzish global o'zgaruvchilarning topilmasligiga olib keladi.

### 5. 🚨 Frontend cache-busting (MAJBURIY AVTOMATIK)
Barcha `<script src>` va `<link href>` larda `?v=NNN`. **Har qanday frontend fayl o'zgartirilganda — `index.html` dagi BARCHA `?v=` larni +1 ga oshirish SHART.** Bu Claude vazifasi — foydalanuvchi so'ramaydi. Versiya bir vaqtda barcha fayllarda sinxron oshiriladi. Sabab: Telegram WebApp va brauzerlar eski faylni cache dan oladi.

### 6. `<head>` script'larda `document.body` xavfi
`<head>` da yuklanuvchi skriptlar (strings.js, app-core.js) parse qilinayotganda `document.body` hali `null`. To'g'ridan-to'g'ri `document.body.classList.add()` → `TypeError` → butun skript to'xtaydi → zanjirli `ReferenceError`. **Pattern:** `document.body` tekshiring, yo'q bo'lsa `DOMContentLoaded` kuting:
```javascript
if (document.body) {
  document.body.classList.add('dark');
} else {
  document.addEventListener('DOMContentLoaded', () => document.body.classList.add('dark'));
}
```

### 7. Bozor race condition himoyasi (2 qatlamli)
**Backend:** `flask_routes_extra.py` `_get_shop_lock(uid)` per-user `threading.Lock` + `try/finally`, timeout=3s → 429. **Frontend:** `app-social.js` `_shopActionLock = new Set()` double-tap guard. Yangi endpoint ball/inventory o'zgartirsa — lock bilan o'rang.

### 8. Bozor narxlari va vazifalari markazlashtirilgan
Narxlar `config.py` `SHOP_PRICES`/`SELL`/`STARS` da, vazifalar `SHOP_BONUS_EFFECTS` da. Hardcoded raqam ishlatmang — har doim config dan. Narx yoki vazifa o'zgartirish: faqat 1 joy.

### 9. Bozor 3 tilga to'liq tarjima
Bot: `callbacks_shop.py` `T(uid, "bozor_*")`. Stars: `flask_routes_extra.py` `T(uid, "stars_item_*")`. Frontend: `strings.js` `S('shop'/'bozor'/'inventory', '*')`. Yangi matn — 3 tilga majburiy.

### 10. Stars to'lov oqimi
WebApp → `/api/shop/stars_invoice` → `bot.send_invoice()` (XTR currency) → `handle_pre_checkout` (auto-OK) → `handle_successful_payment` (`handlers_text.py`) → **faqat `gift_box`** qo'llab-quvvatlanadi (random mukofot) → foydalanuvchiga xabar. Noma'lum item_id → log + return.

### 11. Mahsulot vazifalari stack qilinadi
Badge'lar (`badge_fire/star/secret` — 3%/5%/12%) + car (`car_sport` — 8%) **stack qilinadi**, `_apply_item_bonuses()` B variant (majburiy +1 ball kafolat). Pet'lar alohida: `pet_dog` kunlik +2 (`_apply_pet_dog_bonus`), `pet_cat` 7 kunda 1 streak save (`_try_pet_cat_save` scheduler.py da), `pet_rabbit` jon jazosi 50% yumshoq (`_apply_pet_rabbit_soften`).

### 12. Sotib olish tasdig'i zanjiri
`buyItem()` → `confirmBuyItem()` → `_doConfirmedBuy()` → `_executeBuy()`. Foydalanuvchi "Ha" bosmagunicha hech narsa olinmaydi (qo'li tegib ketishdan himoya).

### 13. Inventory banda va modal
Reyting (podium/4-10/my-row) + profil: `🎒 N` o'rniga **eng qimmat top-1 emoji + `+N`** (`👑 +8`). Backend: `items_list: [{id, qty, price}, ...]` (`SHOP_PRICES.get(iid, 0)` fallback). Frontend: `_invBadgeDisplay(u)` price bo'yicha sort → `.slice(0, 1)`. **Cache trick:** `window._invCache` onclick XSS safe. Modal `openUserInventory(userName, itemsList)` — `.shop-modal-*` qayta ishlatadi, 250ms fade-out. Press effekti: `.inv-badge-clickable:active` scale 0.88.

### 14. Statistika streak mantig'i
`summary.streak` = barcha odatlar streaklari **yig'indisi** (Sport=3 + Dasturlash=8 = 11). `summary.best_streak` = har odatning `best_streak` maksimumi (all-time rekord — `daily_reset()` ga tegmaydi). Checkin 2 joyda sinxron yangilaydi: `callbacks_habits.py` (bot) va `flask_routes_data.py` `/api/checkin` (WebApp). Fallback: `max(h.get("best_streak", 0), h.get("streak", 0))`.

### 15. Pending habit SVG glow ring
`!h.done` → `<svg class="habit-glow-ring">` `.checkin-btn` atrofida, 48×48 `stroke-dasharray: 36 108`, `3s linear infinite`, `stroke-dashoffset 0 → -144` (aniq bitta aylanma, sakrashsiz). **Muhim:** `checkin()` da `btn.innerHTML = ...` **YOZMANG** — faqat `.checkin-btn-content` span innerHTML yangilang, aks holda undo paytida yangi SVG 0° dan desync. Undo paytida yangisiga `animation-delay: -(progress*3) + 's'` bilan sinxronlash. Matematika: 2π × 23 = 144.51 px.

### 16. Touch gesture intent lock
Swipe va PTR uchun **intent detection**: `touchstart` da `startX`/`startY`, `touchmove` da dastlabki 8px da yo'nalish aniqlanadi, g'olib yo'nalish `locked`, ikkinchisi bekor. **Swipe** (`.checkin-front`): `passive:false`, gorizontal `locked` bo'lganda `preventDefault`. **PTR** (`document`): `passive:true` qoldi (butun sahifa scroll performance uchun). `|dx| > |dy| && |dx| > 8` → PTR bekor; `|dy| > 8` → locked. Kelajakda yangi gesture qo'shilsa — shu pattern'ni ishlating.

### 17. NASA-style rang intizomi
Yagona yashil accent `#4CAF7D` (`--accent`/`--accent2`/`--green` uch o'zgaruvchi bir rang — semantik ajratish). `--gold` neytral kulrang. `--red: #E05050` **faqat xavf** (delete, jon `<30%`, err toast). Ringlar 3 darajali yashil gradient (`ringHTML`/`jonRingHTML`). Done karta nomi `var(--text) + opacity: 0.55` (yashil shovqin yo'q — tick yashil asosiy signal). Yangi rang kerak bo'lsa — CSS variables, hardcode qilmang. **Dizayn printsipi:** bir accent + neytrallar + qizil faqat xavf.

### 18. Database environment ajratish (staging/production)
`config.py` `mongo_db = mongo_client.get_default_database()` — DB nomi **MONGO_URI oxiridan avtomatik** (hardcode YO'Q). Railway'da 2 project alohida:
- Production: `habit_bot` DB (`worker` / `perfect-rejoicing`)
- Staging: `superhabits_test` DB (`habit-bot` / `patient-renewal`)

**MUHIM:** `mongo_client["habit_bot"]` kabi hardcoded DB nomi ishlatmang — aks holda ikkala bot bir xil DB ga ulanadi va test production'ni buzadi. Workflow: staging'da sinash → main'ga PR → production avtomatik.

### 19. Mobil WebApp debug (Eruda)
Murakkab xato (ayniqsa "staging ishlaydi, main yo'q") uchun `index.html` `<head>` ga vaqtincha:
```html
<script src="https://cdn.jsdelivr.net/npm/eruda"></script>
<script>try { eruda.init(); } catch(e) {}</script>
```
**Eng muhim kuzatish — birinchi xato** (zanjirli xatolar unga bog'liq). Diagnostika tugagach darhol olib tashlang. Professional yechim: `?debug=1` URL parametrida yoki admin user_id uchun.

### 20. Fayllar max 200-300 qatordan iborat bo'lishi kerak
Kodlarni kichik mustaqil modullarda saqlaymiz — katta monolitik fayllarga o'tmaymiz. Monolit `habit_bot.py` (9 382 qator) 28 ta modulga, monolit `index.html` (5 739 qator) 9 ta faylga bo'lingan — shu pattern'ni saqlang.

### 21. 📘 README yangilash va tozalash qoidalari

README bot arxitekturasining **xaritasi** — versiya nazorati tizimi emas. Git commit xabarlari va qator-qator tarixni saqlaydi; README esa **"bu botda nima bor va qayerda"** degan savolga 3 daqiqada javob berishi kerak. Shu maqsadda har o'zgarishda quyidagi qoidalarga rioya qilinadi.

**A. Qayerga yozish (Decision tree):**

Yangi o'zgarish kirganda Claude quyidagi tartibda fikr yuritadi:

1. **Bu yangi fayl bo'lyaptimi?** → Fayl tuzilmasi `tree` ichiga qo'shing + `📋 Har bir fayl` jadvaliga 1 qator qo'shing (faqat 1 ta yuqori darajali vazifa bilan, masalan "Bozor: jon, referral, transfer").

2. **Mavjud faylga yangi funksiya/feature qo'shilayaptimi?** → Faqat o'sha fayl jadvali qatorini **yangilang** (qo'shmaydi — mavjud ta'rifga integratsiya qiling). Har feature qisqa nom bilan atalsin (masalan `updateHeaderPts`), uzun paragraf yozilmaydi.

3. **Bu arxitektura darajadagi naqsh (pattern) bo'lyaptimi?** (Boshqa joylarga ham qo'llaniladi, kelajakda qayta ishlatiladi) → Quyidagi "Muhim eslatmalar" ga **yangi qoida** yoki mavjud qoidaga subpunkt qo'shing. Misol: "har yangi endpoint ball o'zgartirganda `updateHeaderPts` chaqirilsin" — bu kelajakka qoida, shuning uchun 8-qoida ichiga kirdi.

4. **Bu faqat bitta feature uchun bir martalik ishmi?** (Faqat bir sahifada, qayta ishlatilmaydi) → README'ga **YOZILMAYDI**. Git commit xabari yetarli. Misol: "Reyting sahifasi tab bandasi olib tashlandi" — bu arxitektura emas, bir martalik UI o'zgarish.

**B. Yuqoridagi "yashil kvadrat" bloklari (`>` bilan boshlanadi):**

README boshidagi `>` bloklari **ayni hozirgi holat** ni ko'rsatadi — "bu botda hozir nima bor". Versiya raqami (`v442`, `v468`) **YOZILMAYDI** — u git'da. Yangi katta feature kirganda shu bloklarning tegishlisini **yangilang** (eski matnni o'zgartirib yoziladi). Yangi qator qo'shilsa — 6-7 tadan oshmasin; oshib ketsa kichkina bloklarni birlashtiring.

**C. "YANGI:" belgisini ishlatmaslik:**

Jadval qatorlarida "**YANGI**: ... " yozmang. Sabab: 2 oydan keyin "YANGI" eski bo'lib qoladi va xarita "eski YANGI"lar to'plamiga aylanadi. Feature to'g'ridan-to'g'ri qo'shilsin, "yangi" so'zi yo'q. Git blame qachon qo'shilganini ko'rsatadi.

**D. Fayl jadvali qator uzunligi (qattiq chegara):**

Har jadval qatori **max ~800 belgi**. Oshib ketsa — `style.css` ga o'xshab uzun bo'lsa — feature nomlari bilan to'plamlarga bo'ling ("Checkin kartochka:", "Profile:", "Bozor:" kabi prefikslar), lekin CSS selector-by-selector yozmang. Konkret selector faqat 1-2 eng muhimi uchun, qolganlari "va boshqalar" yoki pattern orqali.

**E. Revert zanjirlari README'ga YOZILMAYDI:**

Har feature uchun "v-N → v-(N-1) qaytarish, qator 681 o'chirish..." kabi ko'rsatmalar **git revert** vazifasi. README'da faqat **pattern** aytiladi (masalan "undo paytida `animation-delay` bilan sinxronlash"), qator raqamlari emas. Agar feature juda nozik va revert murakkab bo'lsa — kodga **komment** yozing (`# REVERT: also remove line X in scheduler.py`), README'ga emas.

**F. README tozalash triggeri:**

Quyidagi holatlardan biri yuz bersa — README **tozalash seansi** kerak:

1. **Fayl hajmi > 40 KB** (hozirgi: ~29 KB, chegara: 40 KB)
2. **"Muhim eslatmalar" qoidalari > 25 ta** (hozirgi: 21 ta)
3. **Jadval qatori > 1500 belgi** (bitta fayl haddan tashqari to'lgan — bo'lish kerak)
4. **3+ qoida bir xil mavzuda** (takrorlanuvchi — birlashtirish kerak)
5. **Versiya raqamlari (`v4XX`) README'da 10+ marta uchragan bo'lsa** (git tarix shovqini kirib kelgan)

Tozalash seansi so'ralsa, Claude quyidagilarni qiladi: (1) takroriy bandlarni birlashtiradi; (2) versiya raqamlarini olib tashlaydi; (3) git'da qayta topsa bo'ladigan konkret tafsilotlarni (qator raqamlari, revert zanjirlari) o'chiradi; (4) jadval qatorlarini pattern-based qayta yozadi; (5) saqlangan va o'chirilganlarini foydalanuvchiga hisobotda bildiradi.

**G. Tozalashda NIMA saqlanadi:**

- Fayl tuzilmasi (tree)
- Modullar orasidagi bog'liqlik
- Har fayl uchun 1 qator jadvalda (asosiy vazifa + eng muhim funksiyalar)
- Arxitektura qoidalari (pattern'lar, naqshlar)
- "Qanday tahrirlash kerak" navigatsion yordam

**H. Tozalashda NIMA o'chiriladi:**

- Versiya raqamlari (`v442`, `v468`)
- Revert zanjirlari (qator raqamlari bilan)
- Bir martalik UI o'zgarish tafsilotlari
- "YANGI" belgilari (agar 2+ oy o'tgan bo'lsa)
- Har selector-level CSS tavsifi
- Takroriy ma'lumotlar (2 joyda bir xil tushuntirilsa — bitta joyga jamlanadi)

**I. Misol (to'g'ri vs noto'g'ri):**

❌ **Noto'g'ri** (README'ga yozilmaydi):
> **YANGI: Header ball bug fix (v459)** — `_executeBuy()` da header ball yangilanmasdi. Endi `app-social.js` qator 748 va 783 da `updateHeaderPts(r.points)` qo'shildi. **Revert**: o'sha qatorlarni o'chirish. **Sabab**: WebApp qayta ochilgandagina to'g'rilanardi.

✅ **To'g'ri** (README'ga yoziladi — 8-qoida yoki app-core.js jadvalida):
> `updateHeaderPts(points)` markaziy helper — DOM + global state sinxron yangilanadi. Yangi endpoint ball o'zgartirganda faqat shu chaqiriladi, inline kod yozilmaydi (DRY pattern).

Farqi: birinchisi **tarix** (git bor), ikkinchisi **qoida** (kelajakka).
