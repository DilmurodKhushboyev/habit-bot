# 🧭 Super Habits Bot — Modular Tuzilma

> Backend: 9 382 qatorlik monolitik `habit_bot.py` → 28 ta mustaqil modul
> Frontend: 5 739 qatorlik monolitik `index.html` → 9 ta mustaqil fayl
> **Bozor sahifasi: 100/100 professional baho** — race condition fix, mahsulot vazifalari (badge/pet/car bonus tizimi), info modal + sotib olish tasdig'i, 3 tilga to'liq tarjima, 6 ta bugli Stars mahsulot olib tashlangan

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
    ├── style.css                ← CSS (1710 qator) — neumorphism, dark mode, animatsiyalar, shop stillar
    ├── strings.js               ← Tarjimalar (942 qator) — UZ/RU/EN, S() funksiya
    │
    ├── ─── JS YADRO ──────────────────────────────────────
    ├── app-core.js              ← (236 qator) TG init, API, state, tabs, premium, SVG helpers
    │
    ├── ─── JS SAHIFALAR ──────────────────────────────────
    ├── app-pages.js             ← (567 qator) Bugun (checkin), eslatmalar, yutuqlar
    ├── app-stats.js             ← (857 qator) Statistika, chartlar, heatmap, reyting
    ├── app-profile.js           ← (506 qator) Profil, tahrirlash, til, dark mode
    ├── app-habits.js            ← (305 qator) Odatlar CRUD, icon picker, modal
    └── app-social.js            ← (1345 qator) Guruh, do'st, shop, challenge, onboarding, init, PTR
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
| `config.py` | ~109 | `BOT_TOKEN`, `ADMIN_ID`, `MONGO_URI`, MongoDB ulanish va indekslar. **Bozor narxlari markazlashtirilgan:** `SHOP_PRICES` (14 ta ball mahsulot), `SHOP_SELL_PRICES` (12 ta 50% sotish narxi), `SHOP_STARS_PRICES` (faqat `gift_box`: 5 Stars), `SHOP_ONE_TIME` (bir martalik nishon/pet/car ro'yxati). **YANGI: `SHOP_BONUS_EFFECTS`** — 7 ta mahsulot vazifasi markazlashtirilgan: `badge_fire` (points_percent 3%), `badge_star` (5%), `badge_secret` (12%), `pet_cat` (streak_save 7 kun), `pet_dog` (daily_bonus +2), `pet_rabbit` (jon_soften 50%), `car_sport` (points_percent 8%) |
| `database.py` | 111 | `load_user`, `save_user`, `load_group`, `save_group`, `load_all_users` (60s cache), `count_users`, `user_exists` (3x retry) |
| `texts.py` | ~424 | `LANGS` dict — uz/en/ru (3 til, har birida 156+ kalit). `btn_ack` — xabarni o'chirish tugmasi. Repeat odat kalitlari: `habit_type_choose`, `ask_repeat_count`, `ask_repeat_first_time`, `ask_repeat_next_time`, `repeat_progress`, `btn_type_simple`, `btn_type_repeat`, `btn_no_time`. `weekly_share_caption` — share card caption. **Bozor bot callback kalitlari (27 ta × 3 til):** `bozor_title`, `bozor_btn_buy_jon`, `bozor_btn_referral`, `bozor_btn_transfer`, `bozor_btn_reset`, `bozor_btn_subtract`, `bozor_jon_high/no_pts/ok`, `bozor_ref_title/link/stats/reward/goals/next/all_done/copy`, `bozor_transfer_ask`, `bozor_edit_title/sub_btn`, `bozor_reset_warn/yes/no`, `bozor_sub_ask`, `bozor_btn_back`. **Stars:** faqat `stars_item_gift_box`, `stars_desc_gift_box` (3 tilga) — ortiqcha 6 ta Stars kaliti olib tashlangan |
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
| `handlers_text.py` | ~1065 | Barcha matn xabarlari (state machine), repeat odat vaqt so'rash T() bilan, Telegram Stars to'lov (`handle_pre_checkout`, `handle_successful_payment` — **faqat `gift_box` qo'llab-quvvatlanadi**: random mukofot 100/200/500 ball, 1 shield, 3 kun XP booster. Noma'lum item_id kelsa log'ga yoziladi va return qilinadi — eski ishlamaydigan `else` bloki olib tashlangan), broadcast, inline query. Import tuzatilgan: `time`, `schedule`, `user_exists`, `admin_menu`, `load_settings`, `save_settings` |
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
| `callbacks_shop.py` | 248 | Bozor: jon sotib olish, referral, ball transfer, tahrirlash, reset. **To'liq 3 tilga o'tkazildi** — barcha matnlar `T(uid, "bozor_*")` orqali `texts.py` dan olinadi. **Narxlar `config.py` dan:** `SHOP_PRICES["jon_restore"]` (25 ball — bot va API sinxron). Helper: `_bozor_back_row(uid)` — takrorlanuvchi tugma qatorlari. Import: `time`, `threading`, `SHOP_PRICES` config dan |

### Guruh va jadval

| Fayl | Qatorlar | Vazifasi |
|------|----------|----------|
| `groups.py` | ~375 | `_save_new_habit()` (repeat\_times + repeat\_count to'g'ri saqlaydi, schedule\_habit ni repeat uchun chaqiradi), `_send_group_view()`, `_build_group_rating()`, `_save_new_group()`. Import tuzatilgan: `time`, `threading` |
| `scheduler.py` | ~864 | `send_reminder()`, `daily_reset()` (**YANGI:** `_try_pet_cat_save()` — pet_cat faol boʻlsa 7 kunda 1 marta streak avtomatik saqlaydi, shield'dan keyin tekshiriladi, `pet_cat_last_used_date` maydoni, xushxabar xabari; `_apply_pet_rabbit_soften()` — pet_rabbit faol boʻlsa jon jazosi 50% yumshatiladi, musbat change'ga tegmaydi), `schedule_habit()` (repeat\_times ro'yxatini qo'llab-quvvatlaydi — har bir vaqt uchun alohida schedule), `_uz5_to_utc()`, `scheduler_loop()`, `send_evening_reminders()`. **Import:** `SHOP_BONUS_EFFECTS` config dan qoʻshildi |

### Flask Web App API

| Fayl | Qatorlar | Vazifasi |
|------|----------|----------|
| `flask_api.py` | 35 | Flask app yaratish, route modullarni ro'yxatdan o'tkazish, `run_api()` |
| `flask_helpers.py` | 132 | CORS, rate limiter, `verify_init_data()`, `require_auth()` dekorator |
| `flask_routes_core.py` | ~581 | `/api/rating`, `/api/profile` (GET + PUT), `/api/habits` CRUD (repeat\_times qo'llab-quvvatlaydi: GET da `times` qaytaradi, POST/PUT da `repeat_times`/`times` qabul qiladi — ~~POST da 15 ta odat limiti~~ **VAQTINCHA OʻCHIRILGAN**), `/api/groups` CRUD. **Import tuzatish:** `mongo_db`, `mongo_col` (config dan), `ACHIEVEMENTS` qo'shildi |
| `flask_routes_data.py` | ~596 | `/api/today` (har bir odatda `days_66_done` va `times` qaytaradi), `/api/checkin` (bajarish logikasi + **YANGI: badge/car ball bonus** `_apply_item_bonuses()` — `SHOP_BONUS_EFFECTS` dan foiz olib qoʻshadi, B variant: majburiy +1 kafolat, stack qilinadi badge+car; **pet_dog kunlik bonus** `_apply_pet_dog_bonus()` — kunlik birinchi checkin'ga +2 ball, `pet_dog_last_bonus_date` maydoni), `/api/stats`. **Import:** `SHOP_BONUS_EFFECTS` config dan |
| `flask_routes_extra.py` | ~868 | `/api/achievements`, `/api/shop` (**15 ta mahsulot**: 14 ta ball + 1 ta Stars (`gift_box`), `_shop_i18n` T() orqali texts.py dan, `sell_price` API response da qaytariladi, one_time `SHOP_ONE_TIME` config dan — **6 ta bugli Stars mahsulot olib tashlangan**: stars_100pts, stars_500pts, badge_diamond, pet_dragon, premium_week, premium_month), **`/api/shop/buy`** (atomic **per-user threading.Lock** bilan himoyalangan — race condition fix, `_get_shop_lock(uid)` + try/finally, timeout=3s → 429 qaytadi, narxlar `SHOP_PRICES` config dan), **`/api/shop/sell`** (lock bilan himoyalangan, `SHOP_SELL_PRICES` config dan), **`/api/shop/activate`** (lock bilan himoyalangan), **`/api/shop/stars_invoice`** (faqat `gift_box`: nom/desc `T()` dan, `SHOP_STARS_PRICES` config dan), `/api/friends`, `/api/challenges`, `/api/reminder`, `/api/share-card`, `/health`, `/favicon.ico` (204), webhook. **Infrastructure:** `_shop_user_locks = {}` dict + `_shop_locks_master` global, `_get_shop_lock(uid)` lazy per-user lock helper. **Import:** `threading`, `SHOP_PRICES`, `SHOP_SELL_PRICES`, `SHOP_STARS_PRICES`, `SHOP_ONE_TIME` config dan, `telebot`, `InlineKeyboardMarkup/Button`, `ACHIEVEMENTS`, `CAT_LABELS` |

### Frontend (Telegram WebApp)

| Fayl | Qatorlar | Vazifasi |
|------|----------|----------|
| `index.html` | ~283 | HTML tuzilma: **splash screen** (`#splash-screen` — neumorphism loading ekran: haqiqiy bot logo `<img>` (`id="splash-logo"`), orbit ring, bouncing dots, 5s ko'rsatiladi, yashirilganda logo header yuqori chapga uchadi), header, **global PTR indikator** (barcha sahifalar uchun), tablar, sahifalar (page-today, page-stats, page-profile...), modallar, bottom nav, badge popup. Hech qanday JS/CSS yo'q |
| `style.css` | ~1754 | Barcha CSS: `:root` ranglar, dark mode, neumorphism shadow'lar, `.header` da `--tg-safe-top` safe area padding, card/button/modal/toast/nav stillar, animatsiyalar (spin, fadeIn, slideUp, confetti), PTR indikator (yuqori + pastki), nav ball glow pulsatsiya (`ballGlow`), toʻlqin ripple effekti (`navRippleWave`), **checkin-card swipe-to-reveal** (`.checkin-front`, `.checkin-actions-bg`, `.cswipe-btn`, `.cswipe-close`), **3-nuqta dropdown** (`.checkin-dots-btn`, `.checkin-dropdown`, `.checkin-dropdown-close`, `cdropIn` animatsiya), **splash screen** (neumorphism: `.splash-icon-wrap` sh-out shadow + pulse, `.splash-orbit` aylanuvchi dashed circle, `.splash-dot` bouncing dots, `.hide` fade-out, `.fly` — matn/orbit yashirish, `.fly-logo` — logo header joyiga uchish transition). **Bozor stillari (260+ qator):** `.shop-balance` (ball banner), `.shop-balance-icon/info/label/value` (`.updated` animatsiya), `.shop-cats` (gorizontal scroll, scrollbar yashirin), `.shop-cat-btn/.active`, `.shop-item` (neumorphic kartochka, `:active` scale, `position:relative`), `.shop-item.sold-out` (opacity), `.shop-item-top/emoji/info/name/desc/owned/cat-label`, `.shop-progress/fill` (gradient), `.shop-buy-btn.primary/.disabled`, `.shop-stars-btn` (gold gradient), `.shop-sell-btn` (qizil accent), `.shop-inv-item/.active-item` (box-shadow green border), `.shop-act-btn.is-active/.not-active`, `.shop-empty/-icon/-text`, `@keyframes shopBuyPulse`, `.shop-item.just-bought`. **YANGI: `.shop-item-info-btn`** (yuqori oʻng burchak neumorphic doira, ℹ belgisi), **`.shop-modal-overlay`** (blur fond, fade-in), **`.shop-modal-box`** (neumorphic modal, scale animatsiya), `.shop-modal-emoji/title/desc/effect/effect-label/meta/btns`, `.shop-modal-btn-yes` (yashil gradient), `.shop-modal-btn-no` (neytral), `.shop-modal-btn-close` |
| `strings.js` | ~992 | `STRINGS` obyekt (UZ/RU/EN tarjimalar), `S(key, sub)` funksiya, `selectedLang`, `currentLang` o'zgaruvchilari. `days_left` — "Odat shakllanishiga {n} kun qoldi" (3 tilda). `habits.edit_btn`/`habits.delete_btn` — swipe va dropdown tugmalari matni (3 tilda). **Bozor:** `shop.cat_badge/cat_pet/cat_car` (3 ta kategoriya × 3 til — `cat_premium`/`cat_stars` olib tashlangan), `shop.your_points/points_unit/inventory/active_label/activate_btn/already_bought/shop_title/protection/bonus/gift/empty_cat/buy_success/activate_success/deactivate_success/you_have/items_unit`, **YANGI:** `shop.confirm_title/confirm_msg/confirm_yes/confirm_no` (sotib olish tasdig'i), `shop.info_title/info_effect/info_price/info_sell/info_close` (info modal). **14 ta mahsulot vazifasi** `bozor.info_*` (har biri 3 tilga): `info_shield_1/3`, `info_bonus_2x/3x`, `info_xp_booster`, `info_badge_fire/star/secret`, `info_pet_cat/dog/rabbit`, `info_car_sport`, `info_jon_restore`, `info_gift_box`. `msg.sell_price/sell_title/sell_confirm/sold_toast` (3 tilda) |
| `app-core.js` | 396 | Telegram WebApp init (`tg.ready()`, `tg.expand()`, `tg.requestFullscreen()`, `tg.disableVerticalSwipes()`, `applySafeArea()` — CSS `--tg-safe-top` variable), `user`/`userId`/`API` konstantalari, `data`/`loaded` state, `switchTab()`/`goBack()`/`loadTab()` (profil va bozor har safar qayta yuklanadi, **`_tabLoading` lock** — tez-tez bosishdan himoya: tab yuklanayotganda yangi switchTab chaqiruvlari e'tiborsiz qoldiriladi, `loadTab` da `try/finally` bilan lock ochiladi), `apiFetch()` (20s timeout), `showPremiumPage()`/`renderPremium()`/`buyPremium()`, `ringHTML()`/`jonRingHTML()` SVG generatorlar, `spawnNavRipple()` toʻlqin effekti |
| `app-pages.js` | ~700 | **Bugun**: `loadToday()`, `renderToday()` (har bir odat kartochkasida 66-kun compact progress bar, **swipe-to-reveal** tahrirlash/oʻchirish tugmalari), `checkin()` (done/undo, repeat dots, confetti, badge popup, streak milestone), `checkinFromFront()` (swipe himoyali checkin), `showTodayToast()`. **Swipe**: `_initCheckinSwipe()`, `closeAllCheckinSwipes()` — chapga surish orqali ✕/Edit/Delete tugmalar ochiladi. **3-nuqta tugma**: `toggleCheckinDrop()` — swipe bilan bir xil natija beradi (dropdown emas, swipe ochiladi), `closeAllCheckinDrops()`. **Eslatmalar**: `loadReminders()`, `renderReminders()`, `toggleReminder()`, `setRepeat()`, `addTime()`/`removeTime()`, `saveReminder()`. **Yutuqlar**: `loadAchievements()`, `renderAchievements()`, `filterAch()`, `showBadgePopup()`/`nextPopup()` |
| `app-stats.js` | 857 | **Statistika**: `loadStats()`, `renderStats()` (summary grid, bar chart, 30-kun area chart, haftalik trend, heatmap, har bir odat statistikasi), `toggleHabitStats()`, `generateShareCard()` (Canvas PNG). **Reyting**: `loadRating()`, `renderRating()` (podium top-3, qator 4-10, sort/period switch), `userAvatarHTML()`, `setRatSort()`/`setRatPeriod()` |
| `app-profile.js` | 506 | **Profil**: `loadProfile()`, `renderProfile()` (avatar: `d.photo_url || user.photo_url` — DB dagi rasm birinchi oʻrinda, stats grid, jon bar, yutuqlar, odatlar, referral, sozlamalar — ~~premiumBadge (Free/Premium yozuvi)~~ **VAQTINCHA OʻCHIRILGAN**). **Tahrirlash**: `openEditProfile()`, `saveEditProfile()`, `previewEpPhoto()`. **Sozlama**: `updateNavLabels()`, `setLang()`, `openLangModal()`/`saveLang()`, `saveDarkMode()`, `saveEveningNotify()`, `updateToggleVisual()` |
| `app-habits.js` | ~380 | **Odatlar CRUD**: `loadHabits()`, `renderHabits()`, `openAdd()`/`openEdit()` (times array qoʻllab-quvvatlaydi), `saveHabit()` (`repeat_times` API ga yuboradi), `deleteHabit()`, `closeModal()`, `showToast()`. **Dinamik vaqt inputlari**: `_buildTimeInputs(count, existingTimes)` (ochilganda vaqtlarni tartiblaydi), `addHabitTime()`, `_onRepeatCountChange()` — repeat_count oʻzgarganda vaqt inputlari soni avtomatik moslashadi. **Avtomatik tartiblash**: `_sortHabitTimes()` — har bir vaqt input oʻzgarganda barcha vaqtlarni chronologik tartiblaydi (boʻshlarni oxirga suradi). **Icon picker**: `ICON_CATS` (10 kategoriya), `selectIconCat()`, `selectIcon()`. ~~Premium limit tekshiruvi~~ **VAQTINCHA OʻCHIRILGAN** — odat qoʻshishda cheklov yoʻq, barcha foydalanuvchilar cheksiz odat qoʻsha oladi. `openAddFromToday()` — today sahifasidan qoʻshish |
| `app-social.js` | ~1432 | **Guruhlar**: `loadGroups()`, `renderGroups()`, `saveGroup()`, `deleteGroup()`, `groupCheckin()`, `setGroupGoal()`. **Do'stlar**: `loadFriends()`, `renderFriends()`, `searchFriends()`, `addFriend()`, `removeFriend()`. **Shop (to'liq qayta yozildi)**: `_shopData`, `_shopContentId`, `_shopCat`, **`_shopActionLock = new Set()`** (double-tap guard). `loadShop()`, `renderShop()` — CSS class'lar bilan, SVG ikonalar o'zgaruvchiga chiqarildi, `data-cat` atributi, **7 ta kategoriya** (all/protection/bonus/badge/pet/car/gift — `premium`/`stars` olib tashlangan). **YANGI: ℹ️ tugma** har kartochkada (`.shop-item-info-btn`). **`openShopInfo(itemId)`** — info modal: emoji, nom, tavsif, haqiqiy vazifa (`bozor.info_*` kalitidan), narx, sotish narxi. **`confirmBuyItem(itemId, method)`** — sotib olish tasdig'i modali ("Haqiqatan olmoqchimisiz?"). **`buyItem()`** → `confirmBuyItem()` → `_doConfirmedBuy()` → `_executeBuy()` (yangi zanjir, eski logika `_executeBuy` ichida). **`closeShopModal()`** — overlay ga bosish ham ishlaydi. Haptic feedback (`tg.HapticFeedback`). `sellItem()`, `activateItem()` — `_shopActionLock` bilan himoyalangan. **Challenge**: `openChallenge()`, `sendChallenge()`, `acceptChallenge()`, `rejectChallenge()`. **Onboarding**: `maybeShowOnboard()`, `obMarkDone()`, `renderOnboard()`. **Init**: `window.onload` (splash, `loadToday()` parallal), `visibilitychange`. **Ovoz**: `playHabitSound()`, `playProgressSound()`. **PTR**: pull-to-refresh |

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

**Bozor narxini o'zgartirmoqchimisiz?**
→ **Faqat `config.py`** — `SHOP_PRICES` (ball), `SHOP_SELL_PRICES` (sotish 50%), `SHOP_STARS_PRICES` (Stars). Hech qayerda hardcoded ishlatilmaydi — bir joyni o'zgartiring, hamma joy avtomatik yangilanadi

**Yangi bozor mahsuloti qo'shmoqchimisiz?**
→ 4 ta fayl: (1) `config.py` — `SHOP_PRICES` va `SHOP_ONE_TIME` ga qo'shing; (2) `texts.py` — nom va tavsifni 3 tilga (`stars_item_*`, `stars_desc_*`); (3) `flask_routes_extra.py` — `shop_items` array ga + `_shop_i18n` ga; (4) agar Stars mahsulot bo'lsa `handlers_text.py` `handle_successful_payment` ga reward logikasi. Frontend `app-social.js` avtomatik ko'rsatadi

**Bozor bot matnini o'zgartirmoqchimisiz?**
→ `texts.py` → `bozor_*` kalitlari (3 tilga), keyin `callbacks_shop.py` `T(uid, "bozor_*")` orqali avtomatik oladi

**Bozor UI dizaynini o'zgartirmoqchimisiz?**
→ `style.css` — `.shop-*` class'lar (`.shop-balance`, `.shop-item`, `.shop-cats`, `.shop-buy-btn`), `app-social.js` `renderShop()` — inline CSS yozmang, class'lardan foydalaning

**Bozor race condition muammosi bormi?**
→ `flask_routes_extra.py` — `_get_shop_lock(uid)` helper ishlatilgan. Yangi endpoint qo'shsangiz (ball/inventory o'zgartiradigan) — `with try/finally` bilan lock ni o'rang. Frontend'da `app-social.js` `_shopActionLock` Set double-tap guard uchun

---

## ⚠️ Muhim eslatmalar

1. **Import tartibi muhim**: `habit_bot.py` dagi import tartibi handlerlarni telebot'da ro'yxatdan o'tkazadi
2. **Circular import yo'q**: `schedule_habit` va shunga o'xshash funksiyalar lazy import (`from scheduler import ...` funksiya ichida) ishlatadi
3. **Callback dispatcher**: `handlers_callbacks.py` barcha callback'larni oladi va sub-modullarga yo'naltiradi — sub-modul `True` qaytarsa, boshqasiga o'tmaydi
4. **Flask routes**: `register_*_routes(app)` funksiyalari orqali ro'yxatdan o'tadi — `flask_api.py` dan chaqiriladi
5. **Frontend script tartibi muhim**: `strings.js` → `app-core.js` (head da), keyin `app-pages.js` → `app-stats.js` → `app-profile.js` → `app-habits.js` → `app-social.js` (body oxirida). Tartibni buzish global o'zgaruvchilarning topilmasligiga olib keladi
6. **Frontend cache-busting**: barcha `<script src>` va `<link href>` larda `?v=423` query string bor — yangilanganda versiyani oshiring
7. **Frontend cross-file calls**: funksiyalar global scope da, lekin ko'pchiligi faqat user action (onclick) da chaqiriladi — shuning uchun yuklash tartibida xato bo'lmaydi
8. **Frontend `window.onload`**: `app-social.js` da — splash subtitle tilga moslash, 5s `hideSplash()` timer, keyin `loadToday()` chaqiriladi
9. **Bozor narxlari va vazifalari markazlashtirilgan**: Narxlar `config.py` da (`SHOP_PRICES`, `SHOP_SELL_PRICES`, `SHOP_STARS_PRICES`), mahsulot vazifalari `SHOP_BONUS_EFFECTS` da. Hech qachon hardcoded raqam ishlatmang — har doim config dan oling. Narx yoki vazifa o'zgartirish kerak bo'lsa — faqat 1 joyni o'zgartiring
10. **Bozor race condition himoyasi**: `flask_routes_extra.py` da `_get_shop_lock(uid)` per-user `threading.Lock` ishlaydi. Buy/sell/activate endpoint'larida `try/finally` bilan lock avtomatik ochiladi, timeout=3s (429 qaytadi). Frontend'da `_shopActionLock` Set — double-tap guard. Bu 2 qatlamli himoya ball 2 marta yechilishdan saqlaydi
11. **Bozor 3 tilga to'liq tarjima**: Bot callback'lari `callbacks_shop.py` da `T(uid, "bozor_*")` orqali, Stars mahsulot nomlari `flask_routes_extra.py` da `T(uid, "stars_item_*")` orqali, frontend `strings.js` da `S('shop', '*')` va `S('bozor', 'info_*')`. Yangi bozor matni qo'shilganda — 3 tilga ham qo'shishni unutmang (23-qoida)
12. **Stars to'lov oqimi**: WebApp → `/api/shop/stars_invoice` → `bot.send_invoice()` (XTR currency) → foydalanuvchi to'laydi → `handle_pre_checkout` (auto-OK) → `handle_successful_payment` (`handlers_text.py`) → faqat `gift_box` qo'llab-quvvatlanadi (random mukofot) → foydalanuvchiga xabar yuboriladi
13. **Mahsulot vazifalari (SHOP_BONUS_EFFECTS)**: Badge'lar (`badge_fire/star/secret`) — checkin ball'iga foizli bonus (3%/5%/12%), `_apply_item_bonuses()` orqali `flask_routes_data.py` da. Car (`car_sport`) — 8% bonus (badge bilan stack qilinadi). Pet'lar — har biri alohida: `pet_dog` — kunlik +2 ball (`_apply_pet_dog_bonus()`), `pet_cat` — 7 kunda 1 marta streak save (`_try_pet_cat_save()` scheduler.py da), `pet_rabbit` — jon jazosi 50% yumshoq (`_apply_pet_rabbit_soften()` scheduler.py da). Badge + car bonus'lari **stack qilinadi** va B variant (majburiy +1 ball kafolat) ishlatiladi
14. **Sotib olish tasdig'i**: `buyItem()` → `confirmBuyItem()` → `_doConfirmedBuy()` → `_executeBuy()` zanjiri. Foydalanuvchi "Ha" bosmagunicha hech narsa sotib olinmaydi (qo'li tegib ketishdan himoya)
15. **Info modal**: Har bir kartochkada ℹ️ tugma — `openShopInfo(itemId)` → modal ochiladi: emoji, nom, tavsif, **haqiqiy vazifa** (`S('bozor','info_'+itemId)` dan), narx, sotish narxi
