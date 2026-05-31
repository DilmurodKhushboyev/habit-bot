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
>
> **Header greeting markaziy helper:** `updateGreeting(name, photoUrl)` — `#greeting-hello`/`#greeting-name`/`#greeting-avatar` sinxron yangilanadi. Init paytida Telegram'dan, `renderProfile()` da DB'dan chaqiriladi. Yangi endpoint ism yoki rasmni o'zgartirsa — shu helper chaqirilsin (DRY).
> **Xato holati markaziy helper:** `renderErrorState(containerId, retryFn)` — internet uzilganda barcha sahifa loaderlari (`loadToday`, `loadReminders`, `loadAchievements`, `loadStatsPage`, `loadRating`, `loadFriends`, `loadShop`, `loadProfile`, `loadCity`) shu funksiyani chaqiradi. Vizual: 📡 ikonka + "Serverga ulanib bo'lmadi" + neumorphik ↻ qayta urinish tugmasi. CSS: `.empty-state-error*` (`style.css` da markazlashgan). 3 til avtomatik (`S('msg','connection_error')`). Avval har sahifa o'z `.empty-state` + SVG kombinatsiyasini takrorlardi — Qoida #17 markazlashtirish. Yangi sahifa loaderi qo'shilsa — xato `catch(e)` blokida shu helper chaqirilsin.
> **Touch gesture lock:** swipe va PTR uchun intent detection (dastlabki 8px da yo'nalish "locked" bo'ladi — diagonal harakat, gorizontal siljishda PTR chiqmaydi)
> **Today sahifasi 2.0:** `today-hero` blok va ikkita doiraviy halqa (`prog-ring` foiz + `jon-ring` JON) butunlay olib tashlandi → o'rniga **haftalik kalendar** (7 katakcha, joriy=yashil accent, kelajak=opacity 0.55, chap/o'ng swipe → boshqa hafta) + chiziqli **JARAYON bar** (yashil gradient fill `var(--accent2)→#66C893`, sakrash animatsiya). Boshqa kun ko'rilganda `?date=YYYY-MM-DD` backend ga jo'natiladi (read-only history view). Bugun emas kun bossa checkin bloklanadi → ⚠️ toast yuqoridan slide-down + ✨"Bugunga qaytish" tugma.
> **Celebration loop:** oxirgi odat bajarilganda konfetti (42 ta zarrachalar) + "Barchasi bajarildi!" karta 3s keyin kollaps + reytingda avatar ustida yashil zar (5 ta zarracha) — hammasi NASA yashil palitrasida
> **Shahar (City) gamification:** har odat tasdiqlanganda → shaxsiy isometric 30×30 grid'da bino qurilishi davom etadi, **66 kun = to'liq qurilgan bino** (odat shakllanish ilmiy chegarasi). 10 ta bino turi (stadion/kutubxona/masjid/...), 5 vizual stage (foundation→complete) — barcha binolar BIR XIL standart kub o'lchamida (qaror sababi: diqqat qurilish bosqichida). Yangi binolar grid markazidan halqama-halqa joylashtiriladi (`find_empty_slot(gap=True)` — har bino atrofida bo'sh katak qoldiriladi, Hay Day/SimCity hissi). Daraxt/gul/avtomobil/bench/fountain — bozordan ball bilan (kelajakda professional SVG ikonkalar bilan render qilinadi). Kun o'tkazilsa soft regress (-1, 0 da clamp). Construction Insurance premium feature (30 kun progress saqlash). Backend deploy bo'lgan (`CITY_GRID_SIZE=30`, `compact_buildings_to_center` versiyalangan migration eski tarqoq binolarni qayta yig'adi). Frontend `app-city.js` + `app-city-buildings.js` + `app-city-move.js` yakunlangan: `loadCity()` async `GET /api/city/<uid>` chaqiradi, javob `_cityData` ga keshlanadi, API xato bo'lsa xato holati + ↻ qayta urinish. **Long-press → drag → drop** bilan bino ko'chirish — 600ms ushlab turish faollashtiradi (`tg.HapticFeedback.medium` vibrate), barmoq surilsa ghost ergashadi, nishon katak yashil (bo'sh) yoki qizil (band) highlight, qo'yib yuborilganda DOM in-place yangilash (asl `<g>` ga `transform=translate(dx,dy)` — sahifa siljimaydi, tez ketma-ket drag mumkin). Foydalanuvchi qo'lda ko'chirgan binolar `pinned=True` belgisi oladi — migration ularga hech qachon tegmaydi. C2.2 pan / C2.3 zoom — YAGNI sababli o'tkazib yuborilgan. C5 modal (`change_type`) — rad etilgan (binolar bir xil — tur o'zgartirish ma'nosiz); endpoint va `change_building_type` funksiyasi audit #11 da o'lik kod sifatida o'chirildi. C3.3 dekoratsiyalar — keyinga qoldirilgan (kichik izometrik primitivlar tanib bo'lmaydi, kelajakda professional SVG kerak)
>
> **Bottom-nav yangi strukturasi (5 tab):** `Odatlar | Reyting | 🏙️ Shahar | Statistika | Bozor`. `nav-profile` tugma olib tashlandi — profilga **header avatar+ism** orqali kiriladi (`greeting-block onclick="switchTab('profile')"`). Shahar tabini markaziy 3-pozitsiyaga qo'yildi (nav-ball yashil shar markaziy elementni urg'ulashi uchun ideal). Sabab: bottom-nav'da 6 tab mobile UX'da siqilib qoladi, profil avatar orqali allaqachon yetarli ko'rinarli.
> **Bottom-nav render intizomi (mobil WebView pirpirashning oldini olish):** Mobil WebView'da sahifa o'tishida nav panel/shar pirpirashining bosh sababi — animatsiyalanadigan element ustidagi CSS `filter` (ayniqsa `drop-shadow`) va SVG gradient'lar har kadr qayta rasterizatsiya bo'lishi. Shuning uchun doimiy qoidalar: (1) **`.bottom-nav` panelning soyasi `box-shadow` orqali beriladi, `.nav-bg` SVG'ga `filter: drop-shadow` QO'YILMAYDI** — `drawNavNotch` har o'tishda SVG `path`'ni yangilaydi, `drop-shadow` esa har safar rasterizatsiya bo'lib pirpiratardi. (2) **nav-ball ichidagi ikonka SVG'sida CSS `filter` ishlatilmaydi** — `moveNavBall` ikonkani ko'chirganda gradient referenslarini (`url(#...)`) to'g'ridan-to'g'ri `#fff` ga almashtiradi (ikonka manbasidan oq, filtersiz). (3) Nav-bg panel `fill` sahifa fonidan farqli (`var(--surface)`) — notch ("kosa") o'yig'i shu rang farqi bilan ko'rinadi, `drop-shadow` yoki `stroke` kerak emas. (4) `.bottom-nav` ichiga animatsiya paytida yangi element (ripple va h.k.) `appendChild` qilinmaydi — compositing qayta hisoblanib pirpiratadi. (5) `moveNavBall`'da `animationend` listener BIR MARTA o'rnatiladi (`ball._endBound` flagi), har chaqiruvda emas — aks holda tez bosishda osilgan listenerlar sharni noto'g'ri joyda qotiradi; joriy maqsad `ball._targetX`'da saqlanadi. Yangi nav effekti qo'shilganda — animatsiyalanadigan element ustiga `filter` qo'ymaslik, soya uchun `box-shadow` ishlatish.

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
├── config.py                 ← Sozlamalar, MongoDB, SHOP_PRICES/SELL/STARS/BONUS_EFFECTS, STREAK_MILESTONES, CITY konstantalar
├── database.py               ← CRUD: load/save user, settings, cache, init_city_for_user
├── db_lock.py                ← Per-user lock (race condition himoyasi S1/S2): user_lock, two_user_locks
├── city_logic.py             ← Shahar logikasi: bino qurish, progress, dekoratsiya, insurance (sof funksiyalar)
├── points_logic.py           ← Ball bonus logikasi: badge/car foiz, pet_dog kunlik bonus (sof funksiyalar)
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
├── callbacks_habits.py       ← Odat: bekor, o'chirish, streak shield + checkin dispatcher
├── callbacks_checkin.py      ← Checkin: toggle_/skip_ + streak milestone helper
├── callbacks_checkin_done.py ← Checkin: done_ (bildirishnomadan)
├── callbacks_menu.py         ← Menyu navigatsiya
├── callbacks_shop.py         ← Bozor: jon, referral, transfer, reset
├── callbacks_reminders.py    ← Eslatma (bir martalik): remdone_*, remskip_* + auto-delete 3s
│
├── ─── JADVAL ──────────────────────────────────────────
├── scheduler.py              ← Eslatmalar, kunlik reset, pet_cat/pet_rabbit bonuslar
├── reminders_scheduler.py    ← Bir martalik eslatmalar (30s loop, remind_at <= now → yuborish)
│
├── ─── FLASK WEB APP API ──────────────────────────────
├── flask_api.py              ← Flask app yaratish va route registratsiya
├── flask_helpers.py          ← CORS, rate limiter, Telegram auth
├── flask_routes_core.py      ← API: rating, profile, habits CRUD
├── flask_routes_data.py      ← API: today, checkin, stats
├── flask_routes_extra.py     ← API: achievements, shop, friends, challenges, webhook
├── flask_routes_city.py      ← API: shahar (city) — get, move, rename, decorations shop, buy_decoration, buy_insurance
└── flask_routes_reminders.py ← API: /api/reminders CRUD (bir martalik eslatma)
```

### Frontend (Telegram WebApp)

```
super_habits/static/
│
├── index.html               ← (~351 qator) HTML layout, splash, modallar, nav, **FAB**
├── style.css                ← (~3273 qator) neumorphism, dark mode, animatsiyalar, **FAB stillari**, **.empty-state-error*** (xato holati — barcha sahifalar uchun umumiy) (city CSS YO'Q — style-city.css ga ko'chirilgan)
├── style-city.css           ← (~226 qator) Shahar CSS — 3 qism: umumiy city + glass yuzlar + bino label (style.css dan KEYIN yuklanadi); xato holati `.empty-state-error*` ga ko'chirildi (style.css)
├── strings.js               ← (~1227 qator) UZ/RU/EN tarjimalar, S() funksiya
│
├── ─── JS YADRO ──────────────────────────────────────
├── app-core.js              ← (~664 qator) TG init, API, state, tabs, updateHeaderPts, updateGreeting, renderErrorState, **FAB toggle**
│
├── ─── JS SAHIFALAR ──────────────────────────────────
├── app-pages.js             ← (~730 qator) Bugun, checkin, eslatmalar, yutuqlar, glow ring
├── app-stats.js             ← (~1235 qator) Statistika, chartlar, heatmap, reyting, inventory modal
├── app-profile.js           ← (~628 qator) Profil, tahrirlash, til, dark mode, referral
├── app-habits.js            ← (~380 qator) Odatlar CRUD, icon picker, modal
├── app-social.js            ← (~1198 qator) do'st, shop, challenge, init, PTR
├── app-reminders.js         ← (~337 qator) Bir martalik eslatmalar: CRUD, modal, Today kartalar
├── app-city.js              ← Shahar sahifasi: async GET /api/city/<uid> + 30×30 isometric grid + initCityMoveHandlers chaqirig'i
├── app-city-buildings.js    ← Shahar binolari: uzluksiz balandlik, yarim shaffof glass yuzlar, odat nomi label, data-habit-id atributi
└── app-city-move.js         ← Long-press → drag → drop: bino ko'chirish (DOM in-place yangilash)
```

---

## 🔗 Modullar orasidagi bog'liqlik

### Backend

```
habit_bot.py (entry point)
    │
    ├── config.py ............... hech nimaga bog'liq emas
    ├── database.py ............. config
    ├── city_logic.py ........... config, database (sof funksiyalar)
    ├── points_logic.py ........ config, database (sof funksiyalar)
    ├── texts.py, motivation.py . hech nimaga bog'liq emas
    ├── helpers.py .............. database, texts
    │
    ├── bot_setup.py ............ config, database, helpers
    ├── menus.py ................ database, helpers, bot_setup
    ├── achievements.py ......... database, bot_setup, helpers
    │
    ├── handlers_commands.py .... config, database, helpers, bot_setup, menus
    ├── handlers_callbacks.py ... → dispatcher (6 ta callbacks_* ga yo'naltiradi)
    ├── handlers_text.py ........ database, helpers, bot_setup, scheduler
    ├── handlers_rating.py ...... database, helpers, bot_setup
    ├── handlers_stats.py ....... database, helpers, bot_setup
    │
    ├── scheduler.py ............ database, helpers, bot_setup, handlers_stats
    ├── reminders_scheduler.py .. database, helpers, bot_setup, config (mustaqil 30s loop)
    │
    └── flask_api.py ............ flask_helpers + 5 ta route modul (core, data, extra, reminders, city)
```

### Frontend

```
index.html (WebApp entry point)
    │
    ├── style.css ................ (CSS — city stillaridan tashqari hammasi)
    ├── style-city.css ........... (Shahar CSS — style.css dan KEYIN yuklanadi, cascade)
    ├── strings.js ............... selectedLang, currentLang, STRINGS, S()
    │
    ├── app-core.js .............. strings.js
    │   ↑ tg, user, userId, API, data, loaded
    │   ↑ switchTab, loadTab, apiFetch, ringHTML, jonRingHTML, checkinRingHTML
    │   ↑ updateHeaderPts (markaziy ball yangilagich), updateGreeting (header salomlashish/avatar/ism sinxronlagich)
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
    ├── app-social.js ............ strings.js, app-core.js + barcha yuqoridagilar
    │   ↑ loadFriends, loadShop, buyItem, window.onload, PTR
    │
    └── app-reminders.js ......... strings.js, app-core.js, app-pages.js (loadToday chaqiradi)
    │   ↑ loadReminderCards, renderReminderSections, openReminderModal,
    │   ↑ saveReminder, markReminderDone, deleteReminder
    │
    └── app-city.js .............. app-core.js
        │   ↑ loadCity (async — apiFetch GET /api/city/<uid>), renderCityGrid,
        │   ↑ renderCityError, cityIsoX/Y, CITY_* konstantalar,
        │   ↑ _cityData (oxirgi API javobi keshi — interaktivlik uchun: drag binoni keshdan topadi)
        │
        ├── app-city-buildings.js ... app-city.js (CITY_* konstantalar, cityIsoX/Y)
        │   ↑ cityBuildingHeight (uzluksiz balandlik), cityBuildingStage (faqat data-stage),
        │   ↑ cityCubeFaces, cityLabelText (label helper), cityBuildingSVG, renderCityBuildings
        │   ↑ data-habit-id atributi har <g> ga (drag uchun bino identifikatori)
        │   ↑ (index.html da app-city.js dan KEYIN yuklanadi — konstantalar bog'liqligi)
        │
        └── app-city-move.js ........ app-city.js, app-city-buildings.js
            ↑ initCityMoveHandlers, _moveState, _cityCreateGhost/Ring/Highlight, cityChangeType yo'q (modal rad etilgan)
            ↑ Long-press 600ms → drag → drop bilan POST /api/city/<uid>/move
            ↑ DOM in-place yangilash (asl <g> ga transform=translate, loadCity chaqirilmaydi)
            ↑ (index.html da app-city-buildings.js dan KEYIN yuklanadi — _cityData/cityIsoX bog'liqligi)
```

---

## 📋 Har bir fayl nima qiladi

### Yadro modullari

| Fayl | Qatorlar | Vazifasi |
|------|----------|----------|
| `config.py` | ~178 | `BOT_TOKEN`, `ADMIN_ID`, `MONGO_URI` (DB nomi oxiridan avtomatik — staging/prod ajratish), MongoDB ulanish va indekslar. **Bozor markazlashtirilgan:** `SHOP_PRICES` (14 mahsulot), `SHOP_SELL_PRICES` (12 × 50%), `SHOP_STARS_PRICES` (`gift_box`: 5 Stars), `SHOP_ONE_TIME` (bir martalik nishon/pet/car), `SHOP_BONUS_EFFECTS` (7 ta mahsulot vazifasi: badge_fire/star/secret points_percent 3/5/12%, car_sport 8%, pet_cat streak_save 7 kun, pet_dog daily_bonus +2, pet_rabbit jon_soften 50%). **City konstantalari:** `CITY_GRID_SIZE=30` (PHASE C2.1 da 20→30 kengaytirildi — eski user binolari saqlanadi, koordinatalar 0-29 oraliqda valid), `BUILDING_DAYS=66`, `CITY_VERSION=1`, `BUILDING_TYPES` (10 ta: stadium/library/mosque/school/park/cafe/bank/hospital/studio/house — emoji + name_key), `BUILDING_STAGE_THRESHOLDS=[13,26,39,52,66]` (5 vizual stage), `DECORATION_TYPES` (5 ta: tree/flower/car/bench/fountain), `SHOP_DECORATION_PRICES` (tree:30, flower:20, car:80, bench:40, fountain:120), `INSURANCE_PRICE=200`, `INSURANCE_DURATION=30`. **Odat:** `HABIT_LIMIT=15` (bir foydalanuvchi maksimal odat soni — freemium qo'shilganda FREE/PREM ga ajratiladi). **Streak milestone (yagona manba — S4):** `STREAK_MILESTONES` dict (8 ta: 3✨/7🔥/14⚡/30💎/60🏆/100👑/180🌟/365🎖️, har biri `emoji`+`bonus` 5/10/20/50/100/200/300/500). Bot (`callbacks_checkin`+`callbacks_checkin_done`) VA WebApp (`flask_routes_data.api_checkin`) SHU dict'dan o'qiydi — sinxron. Streak global qiymati kalitga tenglashganda: `bonus` ball beriladi + `u["streak_milestones_sent"][]` ga yoziladi (takror bermaslik guard). Ball asosiy thread'da (S1 race'dan qochish), xabar thread'da. Foydalanuvchi matni `texts.py` `streak_milestone` (xabar) + `streak_milestone_title` (WebApp popup sarlavhasi) — 3 til. `emoji` dinamik (matn boshida hardcode emoji YO'Q) |
| `database.py` | ~370 | `load_user`, `save_user`, `load_all_users` (60s cache), `count_users`, `user_exists` (3x retry). **Period helper'lari:** `add_points_history(udata, delta)` — har kun delta'ni `points_history: {YYYY-MM-DD: int}` ga saqlaydi, `get_points_in_period(udata, days)` — davriy ball yig'indisi (history bo'sh → fallback umumiy `points`), `get_streak_in_period(udata, days)` — `done_log` dan davriy maks ketma-ket kunlar. **City helper'lari:** `init_city_for_user(udata)` — bo'sh shahar yaratadi (idempotent — mavjud city'ga tegmaydi), `get_user_city(udata)` — auto-init bilan shahar obyektini qaytaradi. `udata["city"] = {version, name, buildings: [...], decorations: [...], insurance_active, insurance_until}` |
| `points_logic.py` | ~71 | **Ball bonus logikasi** — sof funksiyalar, DB ga to'g'ridan-to'g'ri yozmaydi (chaqiruvchi `save_user` qiladi). `apply_item_bonuses(u, base_points)` — faol `active_badge` + `active_car` foizlarini stack qiladi (`SHOP_BONUS_EFFECTS` dan `points_percent` turi), B variant majburiy `+1` kafolat (round natijasida bonus yo'qolsa ham foydalanuvchi foyda ko'rsin), `apply_pet_dog_bonus(u, today, is_undo=False)` — `active_pet=="pet_dog"` bo'lsa kunlik BIRINCHI checkin'ga `+N` (`daily_bonus` qiymati), `pet_dog_last_bonus_date` field bilan kuniga 1 marta kafolat; `is_undo=True` da bonus qaytariladi. **Audit #5:** avval `flask_routes_data.py` ichidagi nested funksiyalar edi — 3 joydan (WebApp checkin, bot `toggle_`, bot `done_`) import qilinishi uchun ajratildi (Qoida #10 sinxron) |
| `city_logic.py` | ~470 | **Shahar (City) logikasi** — sof funksiyalar, DB ga to'g'ridan-to'g'ri yozmaydi (chaqiruvchi `save_user` qiladi). `find_empty_slot(udata, gap=True)` — markazdan halqama-halqa birinchi mos katak (gap=True: 8 qo'shni katak ham bo'sh, fallback gap=False), `get_building_stage(progress)` 0-66→0-4 vizual bosqich, `create_building(...)` idempotent (bir habit_id bir bino), `update_building_progress(udata, habit_id, delta)` +1/-1 clamp 0..66 + insurance check + eski user uchun auto-create (delta>0 da), `backfill_buildings_from_habits(udata)` — har odat uchun retroaktiv bino yaratadi (Variant B: bo'sh poydevor ham yaratiladi, progress = `min(effective_done, 66)`, `effective_done = max(total_done, history_count)` — repeat odatlar qisman tasdiqlangan kunlari ham hisoblanadi, statistika `api_stats` bilan to'g'ridan-to'g'ri sinxron), idempotent, `GET /api/city/<uid>` da bir marta chaqiriladi, `resync_building_progress(udata)` — mavjud binolar progress'ini `effective_done` bilan sinxronlaydi (faqat KO'TARADI, past tushirmaydi — insurance/regress mantig'i bilan to'qnashmaslik uchun), idempotent, repeat odatlar qisman tasdiqlash holatida bino balandligi va statistika "JAMI" orasidagi nomuvofiqlikni tuzatadi, `cleanup_orphan_buildings(udata)` — odat ro'yxatida mavjud bo'lmagan `habit_id` ga bog'langan binolarni o'chiradi (orfan tozalash), idempotent, `compact_buildings_to_center(udata)` — versiyalangan migration (`COMPACT_VERSION`, pinned bo'lmagan binolarni progress bo'yicha markazga qayta yig'adi, pinned tegilmaydi), `delete_building_for_habit`, `place_decoration`/`delete_decoration`, `move_item(udata, item_id, new_x, new_y)` (`True`=ko'chdi / `False`=band yoki koord noto'g'ri / `None`=item topilmadi, muvaffaqiyatda `pinned=True` — kelajak migration tegmaydi; item_id binoda `habit_id`, dekoratsiyada `id`), `activate_insurance`, `_is_insurance_active` |
| `texts.py` | ~436 | `LANGS` dict — uz/en/ru (3 til, har birida 160+ kalit). Repeat odat kalitlari, bozor bot callback kalitlari (`bozor_*` — 21 ta × 3 til), Stars faqat `gift_box` uchun + Stars to'lov xato xabari (`stars_error_user_msg`, `stars_error_btn_contact` — 3 tilda). **Jon 0% ogohlantirish** (`scheduler.py:daily_reset` → `callbacks_shop.py:jonfix`): `jon_zero_title` / `jon_zero_btn` (ikkala kalit `{price}` placeholder — narx config'dan) / `jon_zero_done` / `jon_zero_already` — 4 kalit × 3 til |
| `motivation.py` | 111 | `MOTIVATSIYA` dict — motivatsion gaplar |
| `helpers.py` | 51 | `T(uid, key)`, `get_lang()`, `today_uz5()`, `get_rank()`, `lang_keyboard()` |

### Bot va UI

| Fayl | Qatorlar | Vazifasi |
|------|----------|----------|
| `bot_setup.py` | 142 | `bot` instance, `send_message_colored()`, `cBtn()`, `ok_kb(uid)`, `main_menu_dict()` |
| `menus.py` | 104 | `check_subscription()`, `send_sub_required()`, `admin_menu()`, `admin_broadcast_menu()`, `admin_stats_period_menu()`. **Eslatma:** `menu2_dict`/`build_menu2_text`/`send_menu2` (eski guruh menyu sahifasi) audit #14 da o'chirildi — guruh tizimi olib tashlangan |
| `achievements.py` | 110 | `_ACHIEVEMENTS` ro'yxati (17 ta yutuq, har biri `desc_done`/`desc_todo` 3 tilli dict bilan: qozonilgan vs qulflangan uchun alohida matnlar), `check_achievements_toplevel()` |

### Handlerlar

| Fayl | Qatorlar | Vazifasi |
|------|----------|----------|
| `handlers_commands.py` | 334 | `/start`, til tanlash, deep link (`ref_` referral), `/admin_panel`, kontakt qabul qilish. **Eslatma:** guruh deep-link (`grp_` qo'shilish so'rovi) + pending-guruh bloki audit #14 da o'chirildi (guruh tizimi olib tashlangan) |
| `handlers_callbacks.py` | 165 | **Dispatcher**: darhol `answer_callback_query` → umumiy preamble (til, obuna) → 6 ta sub-handlerga yo'naltirish. `ack_delete_msg` — universal xabar o'chirish |
| `handlers_text.py` | ~802 | Matn xabarlari (state machine), Stars to'lov (faqat `gift_box`: random 100/200/500 ball, 1 shield, 3 kun XP booster) — `handle_successful_payment` idempotency check (`stars_payments[]` ro'yxati `telegram_payment_charge_id`'larni saqlaydi, duplicate event'lar rad etiladi), xato yuz berganda foydalanuvchiga 3 tilli xabar + `tg://user?id={ADMIN_ID}` tugmasi va adminga avtomatik bildirishnoma (`charge_id`/`payload`/xato bilan), noma'lum `item_id` → `raise ValueError` (mavjud `except` blok ushlab xuddi shu xabarlarni yuboradi), broadcast, inline query. **Eslatma:** shaxsiy odat qo'shish state'lari (`waiting_repeat_count`/`waiting_habit_name`/`waiting_habit_time`) audit #3 da o'chirildi; `bozor_waiting_subtract` state audit #7 da olib tashlandi; guruh odati wizard'i (`group_waiting_*`) + pending-guruh bloki audit #14 da o'chirildi (guruh tizimi olib tashlangan) |
| `handlers_rating.py` | 381 | PIL bilan reyting rasm generatsiyasi (top-10 grid) |
| `handlers_stats.py` | 438 | `show_stats()`, haftalik/oylik/yillik hisobot generatsiyasi |

### Callback sub-modullar

| Fayl | Qatorlar | Vazifasi |
|------|----------|----------|
| `callbacks_admin.py` | 428 | Broadcast, foydalanuvchilar ro'yxati, kanal sozlash, ball berish, statistika |
| `callbacks_settings.py` | ~369 | Til, odat vaqtlari, ism/telefon o'zgartirish — 3 tilga |
| `callbacks_habits.py` | ~246 | Odat callback dispatcher: bekor (`cancel`/`cancel_to_main`), o'chirish (`delete_`/`confirm_delete_` — city `delete_building_for_habit`), menyu sahifalash (`main_page_`), streak shield (`shield_use_all`/`shield_skip_all` + eski `shield_use_<id>`/`shield_skip_<id>` backward compat). Checkin (`toggle_`/`skip_`/`done_`) → `callbacks_checkin.py` ga delegatsiya (`handle_checkin_callbacks`). **Eslatma:** bot orqali odat qo'shish wizard'i audit #3 da o'chirildi — odat qo'shishning yagona joyi WebApp `api_habits_add`. `build_main_text`/`main_menu`/`delete_habit_menu` import qilinadi (`bot_setup` / `handlers_stats`) |
| `callbacks_checkin.py` | ~391 | Odat checkin callbacks: `toggle_` (WebApp/menyu — done/undo, repeat 1/N qisman holat) + `skip_` (bildirishnoma xabarini o'chiradi). `_check_streak_milestone()` + `STREAK_MILESTONES` helper shu yerda (`callbacks_checkin_done.py` import qiladi). `done_` → `handle_done_callbacks` ga delegatsiya. **Ball bonus (audit #5):** `apply_item_bonuses` (badge/car foiz) + `apply_pet_dog_bonus` (pet_dog kunlik) — `points_logic.py` dan; WebApp `api_checkin` bilan sinxron (Qoida #10). Undo joylarida `_still_done` tekshiruvi pet_dog qaytarish uchun. **City:** simple/repeat fully done → `update_building_progress(+1)`, fully undo → `(-1)` (try/except ichida) |
| `callbacks_checkin_done.py` | ~216 | Bildirishnomadan kelgan `done_` checkin handleri (`handle_done_callbacks`). Repeat (progress +1, to'liq bo'lsa ball) va simple odat. Ball bonus + city progress `callbacks_checkin.py` bilan bir xil pattern. `_check_streak_milestone` ni `callbacks_checkin.py` dan import qiladi |
| `callbacks_menu.py` | 334 | Menyu navigatsiya, hisobot ro'yxatlari (weekly/monthly/yearly). **Eslatma:** `menu2_open` (eski guruh menyusi) audit #14 da o'chirildi |
| `callbacks_shop.py` | ~255 | Jon sotib olish, referral, ball transfer, reset — 3 tilga. Narxlar `config.py` dan. Helper: `_bozor_back_row(uid)`. Reset `add_points_history(u, -old_points)` chaqiradi (period rating sinxron). **`jonfix` callback** (💀 jon 0% ogohlantirish xabaridagi tugma — `scheduler.py:daily_reset` yuboradi): bir martalik, bosilgach 💀 xabar o'chadi. Mantiq `bozor_buy_jon` bilan SINXRON (Qoida #10): narx `SHOP_PRICES["jon_restore"]` (=25), `jon > 20` chegarasi, `jon=100.0`, `add_points_history(-price)`. Farqlar: (a) jon allaqachon >20 → 💀 xabar o'chadi + "allaqachon yetarli" toast; (b) ball yetmasa → 💀 xabar QOLADI (keyin bosilishi mumkin) + ogohlantirish; (c) muvaffaqiyat → ball yech, jon 100%, 💀 xabar o'chadi, "tiklandi" tasdig'i 2s ko'rinib avto-o'chadi. Tarjimalar `texts.py` `jon_zero_*`. `bozor_buy_jon` (bozor menyusidagi) TEGILMAGAN |
| `callbacks_reminders.py` | ~122 | **Bir martalik eslatma** callbacks: `remdone_<rid>` → `mark_reminder_done()` (+2 ball, matn "bajarildi" bilan edit), `remskip_<rid>` → `mark_reminder_skipped()` (matn "o'tkazildi"). **Matn formati `parse_mode="Markdown"` bilan odat tasdiqlash uslubiga moslashtirilgan** (`texts.py:rem_done_toast` = `"✅ Eslatma bajarildi! *+{pts} ⭐ ball*"`, `rem_skipped_toast` = `"⏭ Eslatma o'tkazib yuborildi"`). Telegram callback popup Markdown'ni qo'llab-quvvatlamaganligi uchun popup uchun asterisksiz `clean_toast` ishlatiladi, `edit_message_text` esa Markdown'li to'liq matnni saqlaydi. `edit_message_text(reply_markup=None)` orqali tugmalar olib tashlanadi. **Auto-delete 3s:** `_delete_message_after(chat_id, msg_id, delay=3)` fon thread (`threading.Thread(daemon=True)`) — tugma bosilgandan 3 soniya keyin xabar avtomatik o'chadi (ikkala tugma ham). Konstanta: `_AUTO_DELETE_DELAY = 3` (§17). `reminders_scheduler.py` dan import. Pattern: `handle_reminder_callbacks(call, uid, cdata, u) -> bool` |

### Jadval

| Fayl | Qatorlar | Vazifasi |
|------|----------|----------|
| `scheduler.py` | ~890 | `_send_auto_delete(uid, text, reply_markup=None, delay=3)` — tabriklash/xushxabar xabarlari uchun: yuborib X soniyadan keyin avto-o'chiradi (chat tarixini toza saqlash). `_check_streak_milestone()` (`callbacks_checkin.py`) shu helper'dan foydalanadi. Pet_cat xushxabarlari `daily_reset()` 00:00 da chaqirilgani uchun avto-o'chmaydi — inline "OK" tugma orqali yopiladi. `send_reminder()` (yuborilgan xabarni `pending_reminders` ga yozadi, 200 entry limit — §23), `daily_reset()` (00:00 UZ+5 — kechagi javobsiz eslatma xabarlarini chatdan o'chiradi; tizim joblarini saqlaydi `SYSTEM_JOB_TAGS` orqali — §22; **City regress YO'Q — qaror: shahar binosi kun o'tkazilsa joyida qoladi**), `send_evening_reminders()` (21:00 UZ+5), `_try_pet_cat_save()` (7 kunda 1 streak save), `_apply_pet_rabbit_soften()` (jon jazosi 50% yumshatish), `schedule_habit()`, `_uz5_to_utc()`, `scheduler_loop()` |
| `reminders_scheduler.py` | ~190 | **Bir martalik eslatma scheduler** (odat eslatmalaridan mustaqil). Fon thread har 30 soniyada `list_pending_reminders_all()` → `remind_at <= now` bo'lsa `send_one_time_reminder()`. Telegram xabari: Markdown matn + 2 inline tugma (`remdone_*`, `remskip_*`), **Bot API 9.4 `style`**: done=`"primary"` (ko'k), skip=`"danger"` (qizil) — eski clientlarda e'tiborga olinmaydi. Status: `pending → sent → done/skipped/expired`. `start_reminders_scheduler()` ni `habit_bot.py` ishga tushirganda chaqiriladi. `mark_reminder_done(rid, uid)` +2 ball (`REMINDER_COMPLETE_POINTS`). **Yuborilgan xabar `pending_reminders: [{message_id, date_uz5}]` ga yoziladi** (max 200 entry, odat eslatmasi bilan bir xil format) — `scheduler.py:daily_reset()` 00:00 UZ+5 da kechagi javobsiz xabarlarni chatdan o'chiradi (§23 pattern). SYSTEM_JOB_TAGS dan mustaqil — daily_reset job'lariga tegmaydi |

### Flask Web App API

| Fayl | Qatorlar | Vazifasi |
|------|----------|----------|
| `flask_api.py` | 43 | Flask app yaratish, route modullarni ro'yxatdan o'tkazish (core, data, extra, reminders, city), `run_api()` |
| `flask_helpers.py` | ~150 | CORS, rate limiter, `verify_init_data()` (uid + user_obj tuple qaytaradi — §25), `get_init_tg_first_name()` (HMAC-tasdiqlangan Telegram first_name), `require_auth()` dekorator |
| `flask_routes_core.py` | ~612 | `/api/rating`, `/api/profile` (GET + PUT bio, max 200 belgi), `/api/habits` CRUD (repeat_times). **`/api/user/<uid>/public-profile`** — boshqa user'ning ommaviy profil ma'lumotlari (reyting modal'i uchun): name, rank, bio, jon, achievements, items_list. Privat maydonlar yo'q (phone, lang, dark_mode, ref_link). `@require_auth` o'rniga `rate_limit_check` (caller != target — pattern `/api/rating` kabi). **Inventory:** `items_count` + `items_list: [{id, qty, price}, ...]` maydonlari — frontend `S('inventory','item_'+id)` orqali tarjima qiladi, top-1 emoji tanlash uchun `price` ham yuboriladi. **Auto-save name (§25):** `/api/rating` va `/api/profile` boshida — DB'da `name` boʻsh foydalanuvchi uchun `get_init_tg_first_name()` orqali Telegram `first_name` DB'ga yoziladi (Telegram'da ism boʻsh boʻlsa — tegmaydi, maxfiylik) **C3.5 (`api_habits_add`):** yangi odat yaratilganda `create_building(u, habit_id)` chaqiradi — shaharda bo'sh bino (`progress 0`); `create_building` idempotent. **Odat limiti (audit #3):** `api_habits_add` da `len(habits) >= HABIT_LIMIT` (config, =15) bo'lsa `400 {"error": "habit_limit"}` qaytaradi — frontend `S('today','limit_reached')` orqali 3 tilda toast ko'rsatadi |
| `flask_routes_data.py` | ~618 | `/api/today` (`days_66_done`, `times`; **`?date=YYYY-MM-DD` query param** — read-only history view: o'tgan kun → `u["history"][date]["habits"]` dan `done` o'qiladi, kelajak → hammasi `done:false`, default = bugun. Response: `view_date`/`is_today_view`/`is_future_view` flaglar; `last_done_at` faqat bugun uchun, aks holda `null`. Validation: noto'g'ri format → 400. Read-only: `last_done`/`streak`/`points`/`history` o'zgarmaydi), `/api/checkin` — **badge/car ball bonus** (`apply_item_bonuses()` — audit #5 da `points_logic.py` ga ko'chirildi; `SHOP_BONUS_EFFECTS` dan foiz + B variant majburiy +1 kafolat, stack qilinadi), **pet_dog kunlik bonus** (`apply_pet_dog_bonus()` — `points_logic.py` dan), **har odat uchun `best_streak`** (streak oshgach `max(h["best_streak"], h["streak"])`), **City integration:** yagona joy yondashuv — `_city_delta` boshida `0` init qilinadi, 4 ta scenariy (repeat fully done/undo, simple done/undo) `+1/-1` belgilaydi, `save_user` oldida bitta yagona `update_building_progress(u, hid, _city_delta)` chaqirig'i (try/except — city xato checkin'ni buzmaydi). `/api/stats` — `summary.streak` = barcha odatlar streaklari yig'indisi, `summary.best_streak` = all-time rekord |
| `flask_routes_extra.py` | ~870 | `/api/achievements` (har karta uchun `earned_at` sana + `desc` matn — `earned`'ga qarab `desc_done`/`desc_todo` dan tanlanadi, lang asosida tarjima), **`/api/shop`** (15 mahsulot: 14 ball + 1 Stars `gift_box`), **`/api/shop/buy`** (per-user `threading.Lock` + 3s timeout → 429), **`/api/shop/sell`**, **`/api/shop/activate`** (hammasi lock bilan himoyalangan), **`/api/shop/stars_invoice`**, `/api/friends`, `/api/challenges`, `/api/reminder`, `/api/share-card`, webhook. Helper: `_get_shop_lock(uid)` lazy per-user lock |
| `flask_routes_city.py` | ~420 | **City (Shahar) API** — 6 ta endpoint, shop pattern bilan moslashtirilgan (per-user `_get_city_lock` 3s timeout, `add_points_history` har ball o'zgarishida, 3 tilda xato xabarlari `_CITY_ERR` dict). `GET /api/city/<uid>` (to'liq shahar — har bino'ga `stage` (0-4) va **`habit_name`** (C3.5c — bino ustidagi label uchun, `u["habits"]` dan `id→name`; orfan bino → bo'sh string) qo'shilgan, eski user uchun avto-init va save; **bir martalik migration auto-chaqirig'i** — `compact_buildings_to_center(u)` try/except bilan, tarqoq/gap'siz binolarni markazga qayta yig'adi va `compact_version` markerini qo'yadi), `POST /api/city/<uid>/move` (item_id ni (x,y) ga ko'chiradi — band katak → `occupied` 400, item topilmadi → `not_found` 404, grid tashqarisi → `invalid_coord`; muvaffaqiyatda `move_item` `pinned=True` qo'yadi → keyingi migration tegmaydi; `move_item` `None`=topilmadi / `False`=band / `True`=ko'chdi qaytaradi), `GET /api/city/<uid>/decorations_shop`, `POST /api/city/<uid>/buy_decoration`, `POST /api/city/<uid>/delete_decoration`, `POST /api/city/<uid>/buy_insurance`. `register_city_routes(app)` orqali `flask_api.py` da ro'yxatdan o'tadi |
| `flask_routes_reminders.py` | ~148 | **Bir martalik eslatmalar CRUD:** `GET /api/reminders/<uid>` (ro'yxat, ixtiyoriy `?status=` filter), `POST /api/reminders/<uid>` (yaratish, `REMINDER_MAX_TEXT_LEN=200` cheklov, o'tgan vaqt tekshiruvi 60s tolerance), **`PUT /api/reminders/<uid>/<rid>`** (tahrirlash — faqat `pending` status va kelajakdagi eslatmalar; eski yoki yangi vaqt o'tib ketgan bo'lsa `expired`/`past_time` qaytaradi), `DELETE /api/reminders/<uid>/<rid>` (egasi tekshirish), `PATCH /api/reminders/<uid>/<rid>/done` (+2 ball, `REMINDER_COMPLETE_POINTS`). Helper: `_parse_iso_datetime()`, `_serialize_reminder()` (datetime → ISO). `@require_auth` hamma endpointlarda |

### Frontend (Telegram WebApp)

| Fayl | Qatorlar | Vazifasi |
|------|----------|----------|
| `index.html` | ~315 | HTML layout: **splash screen** (haqiqiy bot logo `<img>` `id="splash-logo"`, orbit ring, bouncing dots, 5s → ekran fade-out), **header** (`greeting-block` chap: 40×40 avatar `#greeting-avatar` + `#greeting-hello` salomlashish + `#greeting-name` ism — bosish `switchTab('profile')`; `pts-chip` ⭐ ball oʻngda), **global PTR indikator**, tablar, sahifalar, modallar, **FAB blok** (`#fab-overlay` + `#fab-wrap` ichida `#fab-actions` (2 ta button: `#fab-action-habit` va `#fab-action-reminder` — ikon + label) va `#fab-main` (yashil yumaloq + tugma) — bottom-nav'dan oldin joylashgan), bottom nav, badge popup. Hech qanday JS/CSS yo'q |
| `style.css` | ~3273 | `:root` dizayn tokenlari (NASA yashil `#4CAF7D` accent, neumorphism 2.0 shadow'lar `--sh-*`, safe-area padding), dark mode, umumiy animatsiyalar (spin/fadeIn/slideUp/confetti/ripple/glow). Komponent bloklari prefiks bo'yicha: checkin kartochka (`.checkin-*` — swipe-to-reveal, `.readonly` disabled holat), profil (`.profile-chip`/`.profile-bar-row`), reyting (`.inv-badge-*`/`.avatar-snow-*`), bozor (`.shop-*` — segmented chip tablar), Today FAB (`.fab-*` — suzuvchi tugma, wrapper `pointer-events:none` "qora teshik" oldini oladi), haftalik kalendar (`.weekcal-*`), JARAYON bar (`.progress-bar-*`), read-only toast (`.readonly-toast-*`), celebration (`all-done-banner` + konfetti), **xato holati `.empty-state-error*`** (`.empty-state` dan keyin; 📡 ikonka + matn + ↻ neumorphik tugma — barcha sahifalar uchun umumiy, app-core.js `renderErrorState` ishlatadi; avval `style-city.css` da `.city-error*` edi, §17 markazlashtirish). City CSS bu faylda EMAS — `style-city.css` da (Qoida #24) |
| `style-city.css` | ~226 | **Shahar sahifa CSS** — `style.css` dan ajratilgan (Qoida #24). `index.html` da `style.css` dan KEYIN yuklanadi (cascade — bu fayl selektorlari ustun). **3 qism (ichki cascade — pastki yuqorisini override qiladi):** (1) Umumiy city CSS — `#page-city`, `.city-canvas-wrap` (`position:fixed`, `overscroll-behavior:contain` PTR bloklash; **fon `var(--bg)` — header va nav bilan BIR XIL koʻkimtir-kulrang fon, vizual uzluksizlik**), `.city-canvas`, `.city-tile-*` (**uniform oq 3D kublar — shaxmat YOʻQ, `tile-a` va `tile-b` bir xil `#FFFFFF` (dark: `var(--surface)`); `stroke: none` — chiziq yoʻq, kublar polygon shrink orqali gap bilan ajraladi, gap'da `var(--bg)` fon koʻrinib soya hissi beradi**), `.city-bld` (3 yuz polygon), long-press drag overlay (`.city-bld-ring-*`/`.city-bld-hidden`/`.city-bld-ghost`/`.city-tile-highlight-*`), dark mode. (2) Glass yuzlar — `.city-bld-glass-top/left/right` (qurilmagan qism; solid bino yuzlari bilan AYNI rang, `fill-opacity: 0.5` yarim shaffof; `.city-bld polygon` selektorni `stroke:none` bilan override qiladi). (3) Bino label — `.city-bld-label` (odat nomi `<text>`, oq `paint-order:stroke` halo fon ustida o'qilishi uchun), dark mode. **Xato holati:** `.city-error-*` olib tashlandi — umumiy `.empty-state-error*` ga ko'chirildi (`style.css`), barcha sahifalar bir xil uslubdan foydalanadi (§17). **KELAJAK:** yangi shahar CSS shu faylga yoziladi |
| `strings.js` | ~1080 | `STRINGS` obyekt (UZ/RU/EN), `S(key, sub)` funksiya. Asosiy kalitlar: `profile.bio_*`, `shop.cat_*`/`info_*`/`confirm_*`, `bozor.info_*` (14 mahsulot vazifasi), `inventory.*` (17 kalit — badge_label, modal_*, 11 item nomi), `msg.sell_*`/`copy_link`, `today.add_habit`, `today.progress_label` (UZ "JARAYON" / RU "ПРОГРЕСС" / EN "PROGRESS" — chiziqli progress bar ostidagi label), `today.readonly_msg` + `today.back_to_today` (o'tgan/kelajak kun ko'rilayotganda checkin urinishi uchun toast: "Faqat bugungi odatlarni belgilash mumkin" / "Bugunga qaytish" + 3 til), `today.limit_reached` (odat limiti — 15 ta, 3 til; `app-habits.js` `saveHabit` da `habit_limit` xato kodi uchun), `stats.streak_total_label` |
| `app-core.js` | ~664 | TG init (`tg.ready/expand/requestFullscreen/disableVerticalSwipes`, `applySafeArea` → `--tg-safe-top`), `user`/`userId`/`API`, `data`/`loaded` state, `switchTab`/`goBack`/`loadTab` (profil, bozor, shahar har safar qayta yuklanadi — `loaded[tab]=false` pattern; `_tabLoading` lock double-tap himoya), `apiFetch` (20s timeout). **Markaziy helperlar:** `updateHeaderPts(points)` (DOM `#header-pts` + state sinxron — yangi endpoint ball o'zgartirganda faqat shu chaqiriladi), `updateGreeting(name, photoUrl)` (`#greeting-*` sinxron — vaqtga qarab salomlashish, ism `?` fallback §25), `renderErrorState(containerId, retryFn)` (xato holati markaziy renderi — 9 ta loader (`loadToday`, `loadReminders`, `loadAchievements`, `loadStatsPage`, `loadRating`, `loadFriends`, `loadShop`, `loadProfile`, `loadCity`) `catch(e)` blokida chaqiriladi; vizual: 📡 + "Serverga ulanib bo'lmadi" + ↻ tugma; CSS `.empty-state-error*` `style.css` da; `retryFn` `window[_retryErr_*]` orqali global saqlanadi inline onclick uchun; §17 markazlashtirish), `ringHTML`/`jonRingHTML` SVG generatorlar (3 darajali yashil gradient), `checkinRingHTML(percent, isDone, label, size=42)` (odat+eslatma tasdiqlash tugmasi yagona SVG halqa generatori — pending bo'sh, repeat qisman `N/M`, done ✓; §15). **FAB boshqaruvi:** `_updateFabVisibility(tab)` (FAB faqat `today` da), `_updateFabLabels` (3 til), `toggleFab`/`openFab`/`closeFab` (haptic), `fabCreateHabit`/`fabCreateReminder` (modal ochadi). `spawnNavRipple`, `showPremiumPage` |
| `app-pages.js` | ~1010 | **Bugun:** `loadToday(dateStr=null)` (optional `?date=YYYY-MM-DD` — parametrsiz = bugun), `renderToday` (swipe-to-reveal kartalar, tasdiqlash tugmasi `checkinRingHTML` SVG halqa; o'tgan/kelajak kun → `.readonly` class). **Haftalik kalendar:** `_dayAbbrMap` (3 til), `weekCalHtml` 7 katak `.weekcal-day`, `window._selectedDate`/`_weekOffset` global state, `selectDay`/`_shiftWeek`/`_initWeekCalSwipe` (chap/o'ng swipe → boshqa hafta, gesture intent lock). **JARAYON bar:** `progressBarHtml`, `checkin()` da `prog-ring` bilan birga yangilanadi. **Read-only toast:** `_showReadonlyToast`/`_backToToday` — bugun emas kun checkin urinishi → ⚠️ slide-down toast; `checkin()` boshida `is_today_view === false` guard. **Checkin:** `checkin` (done/undo, konfetti `_triggerConfetti`, badge popup, streak milestone, `wasAllDone` — konfetti faqat yangi yutuqda). **Swipe:** `_initCheckinSwipe` gesture intent lock. **Yutuqlar:** `renderAchievements` (3 ustunli `.ach-grid` mini-cards), modal `openAchievementDetail`/`closeAchievementDetail` |
| `app-stats.js` | ~1410 | **Statistika:** `loadStats`, `renderStats` (summary, bar chart, 30-kun area, haftalik trend, heatmap, har odat), `generateShareCard` (Canvas PNG). **Reyting:** `loadRating`, `renderRating` (podium top-3; qator 4-10 + `caller_entry` — ism alohida `flex:1` div, metrik badgelar (inv, habits, jon, ball) alohida o'ng konteynerda; dinamik width tekislash — `_habW`/`_jonW`/`_scoreW` render boshida hisoblanadi, badgelar vertikal chiziqda tekislanadi; inventory badge faqat `items_count > 0` da), `setRatSort`/`setRatPeriod`; `userAvatarHTML` (`today_done` → `avatar-snow-*` zar; bosilganda `is_me` → profil, boshqa → `openUserProfile` modal). **Inventory:** `window._invCache` (XSS safe onclick), `_invBadgeDisplay` (price bo'yicha top-1 emoji + `+N`), `openUserInventory` modal (`.shop-modal-*` qayta ishlatadi). **User Profile Modal:** `openUserProfile(uid)` → fetch `/api/user/<uid>/public-profile` → `_userProfileCardHTML` (`profile-card` nusxasi — avatar, rank, inventory chips, bio, JON/YUTUQLAR bar; tahrirlash yo'q), `closeUserProfile`; SVG ID prefiks `Up*` (konflikt oldini olish) |
| `app-profile.js` | ~628 | `loadProfile`, `renderProfile` (boshida `updateGreeting(...)` chaqiradi — header sinxron; avatar, bio XSS himoyali, jon bar, achievements progress bar, referral kompakt tugma `rem-card` patternida, inventory kompakt banda `🎒 N` → `openUserInventoryByKey` app-stats modali qayta ishlatiladi, Yutuqlarim kompakt tugma → `switchTab('achievements')`). **Modal:** `openReferralModal`/`closeReferralModal` (bonuslar, 3 milestone, referral link, nusxalash, haptic). **Tahrirlash:** `openEditProfile` (avatar file → base64, ism max 60, telefon, bio 200 belgi + counter), `saveEditProfile` (PUT `/profile/<uid>` — `display_name`/`phone`/`bio`/`photo_url`, muvaffaqiyatdan keyin `loadProfile` → `renderProfile` → `updateGreeting`). **Sozlamalar:** `updateNavLabels`, `setLang`/`openLangModal`/`saveLang`, `saveDarkMode`, `saveEveningNotify`, `copyRefLink` (clipboard + fallback) |
| `app-habits.js` | ~380 | `loadHabits`, `renderHabits`, `openAdd`/`openEdit`, `saveHabit` (`repeat_times` API), `deleteHabit`, `closeModal`. **Dinamik vaqtlar:** `_buildTimeInputs`, `addHabitTime`, `_onRepeatCountChange`, `_sortHabitTimes` (avtomatik chronologik). **Icon picker:** `ICON_CATS` (10 kategoriya, neumorphic 3D dome dizayn), `selectIconCat`, `selectIcon`, `_buildIconGrid`. `openAddFromToday` — today sahifasidan |
| `app-social.js` | ~1198 | **Do'stlar:** `loadFriends`, `searchFriends`, `addFriend`, `removeFriend`. **Shop:** `_shopData`/`_shopCat`, `_shopActionLock` double-tap guard, `loadShop`, `renderShop` (7 kategoriya: all/protection/bonus/badge/pet/car/gift — balance karta va sarlavha yo'q, header `#header-pts` doimiy). **SVG ikonalar:** `svgStar`/`svgShield`/`svgBolt`/`svgBadge`/`svgPet`/`svgCar`/`svgGiftCat` — gradient bilan unifikatsiya. **Sotib olish:** `openShopInfo` (info modal), `confirmBuyItem` → `_doConfirmedBuy` → `_executeBuy` (zanjir: tasdiq → lock → `updateHeaderPts`; §12), `sellItem`/`activateItem`, `closeShopModal`. **Challenge**, **Init** (`window.onload`: splash 5s → `loadToday`). **PTR:** pull-to-refresh (yuqori + pastki, gesture intent lock — §16; `skipTabs = ['achievements','reminders','premium','city']` bu tablarda PTR o'chiriladi — §9). **Ovoz:** `playHabitSound`, `playProgressSound` |
| `app-reminders.js` | ~430 | **Bir martalik eslatmalar** (Today sahifa bo'limi, odat kartalardan KEYIN). `loadReminderCards` + cache `_cachedReminders`, `renderReminderSections` (pending+sent filter, Bugun/Keyin ajratish — "Keyingi" default YOPIQ collapsible), `_renderRemCard` (front/back qatlam — orqada `.rem1-actions-bg` Tahrirlash+O'chirish, ustda `.rem1-front` + `checkinRingHTML` tasdiqlash tugmasi + 3-nuqta). **Swipe:** `toggleRem1Swipe`, `_initRem1Swipe` (gesture intent lock, `closeAllRem1Swipes`). **Modal (yaratish+edit):** `openReminderModal(existing)` — `existing` bo'lsa edit rejimi, `_editingReminderId` global state; `editReminder` (pending+kelajak tekshiruvi, expired → toast), `saveReminder` (PUT/POST avtomatik, backend `expired` xatosida modal yopiladi — race-safe). **Actions:** `markReminderDone` PATCH `/done` (+2 ball, fade-out), `deleteReminder` DELETE. **Helper:** `_remFetch`, `_formatRemTime`, `_escRemHtml`. **CSS prefiks `rem1-`** (§11 — `.rem-card` profil bilan konflikt oldini olish): `.rem1-card`/`.rem1-front`/`.rem1-actions-bg`/`.rem1-modal-*` va h.k. **Strings:** `today.*` + `rem_modal.*` (yaratish/edit juftlari, 3 til) |
| `app-city.js` | ~233 | **Shahar sahifasi** (API integratsiya + interaktivlik trigger). `loadCity()` — async, `apiFetch` orqali `GET /api/city/<uid>`, javobni `_cityData` ga keshlaydi → `renderCityGrid`. `renderCityError` — API xato holati (📡 + ↻ qayta urinish; soxta demo data KO'RSATILMAYDI). **Konstantalar (§17):** `CITY_GRID_SIZE=30` (backend bilan sinxron — Qoida #11), `CITY_TILE_W/H`, `CITY_PADDING`, **`CITY_TILE_SHRINK=0.92`** (3D suzuvchi kub effekti — har polygon vertex'i markazga 8% tortiladi, qoʻshni polygon'lar orasida tabiiy gap, gap'da `var(--bg)` fon koʻrinadi → "kublar suzayotgan" hissi; chiziq EMAS, gap+soya yondashuvi — Stripe/Linear premium minimalist 3D shahar referensiga mos), `CITY_STAGE_THRESHOLDS` (backend bilan sinxron), `CITY_BLD_BASE_W/H`. Eski `CITY_BLD_HEIGHTS` massivi OLIB TASHLANDI — balandlik endi uzluksiz (`app-city-buildings.js`). **Helper'lar:** `cityIsoX`/`cityIsoY` (grid→ekran piksel). **`renderCityGrid`** — 900 katak `<polygon>` (`data-x`/`data-y` drag hit-testing; **vertex koordinatalari romb markaziga `CITY_TILE_SHRINK` bilan tortilgan — polygon kichikroq, atrofida gap**), parity saqlangan (data-attribute uchun, fill CSS da bir xil — shaxmat YOʻQ), binolar layer `renderCityBuildings`, `viewBox` matematikasi (`viewY` label headroom — bino ustidagi label kesilmasligi uchun), auto-scroll markazga. Oxirida `initCityMoveHandlers(container)`. **CSS:** `style-city.css`. **Bog'liqlik:** `app-city-buildings.js` + `app-city-move.js` index.html da BU fayldan KEYIN yuklanadi. C2.2/C2.3 (pan/zoom) rejadan olib tashlangan, C3.3 dekoratsiyalar keyinga qoldirilgan, C5 modal rad etilgan |
| `app-city-buildings.js` | ~254 | **Shahar binolari** — bino render mantiqi, `app-city.js` dan ajratilgan (Qoida #24). **Konstantalar (§17):** `CITY_BLD_FULL_HEIGHT=84`, `CITY_BLD_MIN_HEIGHT=8`, `CITY_BLD_MAX_PROGRESS=66` (config.py `BUILDING_DAYS` bilan sinxron), `CITY_BLD_LABEL_MAX=12`. **`cityBuildingHeight(progress)`** — kun soni (0-66) → solid kub balandligi UZLUKSIZ chiziqli interpolyatsiya (har bajarilgan kun farq qiladi). **`cityBuildingStage(progress)`** — `0-66`→`0-4` stage, faqat `data-stage` atributi uchun (balandlikka ta'sirsiz). **`cityCubeFaces`** — izometrik kub 3 yuz polygon. **`cityLabelText(raw)`** — 12 belgidan uzun nom "…" qisqartiradi, XSS escape. **`cityBuildingSVG(...)`** — bitta bino `<g>`: solid kub (qurilgan qism) + glass kub (qurilmagan qism — solid bilan AYNI rangda, yarim shaffof yuzlar; C3.5d da wireframe qirra chiziqlari olib tashlandi — binolar yaqin turganda shovqin yaratardi) + odat nomi `<text>` label bino ustida; atributlar `data-type`/`data-stage`/`data-habit-id` (drag identifikatori). **MUHIM qaror:** barcha bino BIR XIL standart kub — faqat `progress` balandlikni belgilaydi. `renderCityBuildings(buildings)` — painter's algorithm (depth `x+y` sort). **CSS:** `style-city.css`. **Bog'liqlik:** `app-city.js` global konstantalariga tayanadi — index.html da undan KEYIN yuklanadi |
| `app-city-move.js` | ~320 | **Shahar bino ko'chirish** — long-press → drag → drop. `initCityMoveHandlers(container)` `renderCityGrid` oxirida chaqiriladi, SVG ga delegated touch handlerlar ulaydi. **Konfiguratsiya:** `LONGPRESS_MS=600` (Hay Day patterni), `LONGPRESS_MAX_MOVE=10` (scroll niyat chegarasi). `_moveState` drag holatini ushlaydi. **Oqim:** `touchstart` `.city-bld` ga → pulse halqa (`_cityCreateRing`) + 600ms taymer (foydalanuvchi surilsa → scroll deb bekor); 600ms o'tgach `_cityActivateDrag` → ghost clone (`_cityCreateGhost`), haptic medium, asl bino `.city-bld-hidden`. `touchmove` → ghost barmoq ortidan (`_cityMoveGhost`), nishon katak `_cityClientToGrid` (`elementFromPoint` DOM hit-testing) → highlight (yashil bo'sh / qizil band). `touchend` → `_cityFinishDrag` → `POST /api/city/<uid>/move` (`move_item` `pinned=True` qo'yadi). **MUHIM (DOM in-place):** muvaffaqiyatdan keyin `loadCity()` chaqirilMAYDI — asl `<g>` ga `transform=translate(dx,dy)` qo'shiladi, `_cityData` lokal yangilanadi. Sabab: `loadCity` butun grid'ni qayta yaratib auto-scroll'ni sakratardi. **Anti-flash:** band joy / API xato → rollback (`_cancelMove`). **Bog'liqlik:** `app-city.js`, `app-city-buildings.js`, `app-core.js` — index.html da `app-city-buildings.js` dan KEYIN yuklanadi |

---

## ✏️ Qanday tahrirlash kerak

**Yangi odat turi qo'shmoqchimisiz?** → `flask_routes_core.py` (`api_habits_add` — WebApp odat qo'shishning yagona joyi)

**Yangi API endpoint qo'shmoqchimisiz?** → `flask_routes_core.py` yoki `flask_routes_extra.py`

**Matn/tarjima o'zgartirmoqchimisiz?** → `texts.py` (bot) yoki `strings.js` (WebApp) — 3 tilga ham qo'shing

**Yangi callback tugma qo'shmoqchimisiz?** → Tegishli `callbacks_*.py` + `handlers_callbacks.py` dispatcherda tartibni tekshiring. Eslatma callback'lari (`remdone_*`, `remskip_*`) — `callbacks_reminders.py` ichida

**Scheduler/eslatma o'zgartirmoqchimisiz?** → **Odat eslatmalari** (takroriy): `scheduler.py`. **Bir martalik eslatmalar** (alohida funksiya): `reminders_scheduler.py` — fon thread har 30s tekshiradi

**WebApp UI/stil o'zgartirmoqchimisiz?** → `style.css` + tegishli `app-*.js` (render funksiyasi). **Inline CSS yozmang — class'lardan foydalaning**

**Yangi WebApp sahifa qo'shmoqchimisiz?** → `index.html` (layout), `style.css`, tegishli `app-*.js`, `app-core.js` (`loadTab` ichiga)

**WebApp checkin/today mantiqini o'zgartirmoqchimisiz?** → `app-pages.js` (`checkin`, `renderToday`)

**Bozor narxini o'zgartirmoqchimisiz?** → **Faqat `config.py`** (`SHOP_PRICES`/`SELL_PRICES`/`STARS_PRICES`). Hardcode ishlatmang — bir joy, hamma joy avtomatik

**Yangi bozor mahsuloti qo'shmoqchimisiz?** → 4 fayl: (1) `config.py` `SHOP_PRICES`+`SHOP_ONE_TIME`; (2) `texts.py` nom/tavsif 3 tilga; (3) `flask_routes_extra.py` `shop_items`+`_shop_i18n`; (4) agar Stars — `handlers_text.py` `handle_successful_payment` reward logikasi

**Yangi endpoint ball o'zgartirmoqchimisiz?** → Inline `getElementById('header-pts')` YOZMAYMIZ — `updateHeaderPts(r.points)` helper chaqiring (DRY)

**Shahar (city) feature o'zgartirmoqchimisiz?** → **Backend logika** (bino qurish, progress, dekoratsiya, gap qoidasi, migration): `city_logic.py` (sof funksiyalar). **API**: `flask_routes_city.py` (`api_city_get` javobiga `stage` + `habit_name` qo'shadi). **Konstantalar** (bino turlari, narxlar, `BUILDING_DAYS=66`, `CITY_GRID_SIZE=30`): `config.py` CITY bloki. **Habit checkin bilan ulanish** (yangi checkin joyi qo'shilsa): `update_building_progress(u, habit_id, delta)` — bot (`callbacks_checkin.py` + `callbacks_checkin_done.py`), WebApp (`flask_routes_data.py`) bilan sinxron. `daily_reset` city ga TEGMAYDI (qaror — bino joyida qoladi). **Odat YARATILGANDA bino:** `create_building(u, habit_id)` — WebApp `flask_routes_core.py` `api_habits_add` (odat qo'shishning yagona joyi — bot wizard'i audit #3 da o'chirildi); odat tasdiqlanmagan bo'lsa ham bo'sh bino (`progress 0`) ko'rinadi; `create_building` idempotent. **Migration qoidasi o'zgartirilsa:** `city_logic.py` `COMPACT_VERSION` ni oshiring. **Frontend shahar sahifasi:** `app-city.js` (async `GET /api/city/<uid>`, `_cityData` keshi, `viewY=-150` label headroom, oxirida `initCityMoveHandlers`), `app-city-buildings.js` (bino render: `cityBuildingHeight` uzluksiz balandlik, `cityBuildingSVG` solid+glass+label, `cityLabelText`, `renderCityBuildings`), `app-city-move.js` (long-press → drag → drop, DOM in-place). **Tartibi (Qoida #4):** `index.html` da `app-city.js` → `app-city-buildings.js` → `app-city-move.js`. **CSS:** `style-city.css` (BARCHA city stillari — `style.css` da EMAS; `style.css` dan KEYIN yuklanadi, cascade; 3 qism: umumiy + glass + label). **Tarjima:** `strings.js` `S('city', '*')` — 3 til (`title`/`coming_soon`/`description`/`moved`/`move_failed`); odat nomi label tarjima QILINMAYDI (foydalanuvchi matni). **Sahifa konteyneri:** `index.html` `<div id="page-city">`. **Navigatsiya:** `app-core.js` `loadTab()` `case 'city'`. **MUHIM (Qoida #11):** `CITY_GRID_SIZE`, `CITY_STAGE_THRESHOLDS`, `CITY_BLD_MAX_PROGRESS=66` frontend va backend (`config.py`) o'rtasida sinxron bo'lishi shart.

**Bottom-nav tab qo'shmoqchi/o'zgartirmoqchimisiz?** → `index.html` `.bottom-nav` (5 tab: `Odatlar | Reyting | Shahar | Statistika | Bozor`; `nav-profile` butunlay yo'q — profilga **header `.greeting-block` avatar+ism** orqali kiriladi, `onclick="switchTab('profile')"`). Yangi tab qo'shilsa: nav-item SVG + label, `loaded` state'ga field, `loadTab()` ga case, `<div id="page-X">` konteyner, `strings.js` `nav.X` 3 tilda. `switchTab()` guard'lari (`if (_navEl) ...`) `nav-X` yo'q bo'lsa ham xavfsiz — `greeting-block` orqali chaqirish kabi tabga DOM tugmasiz o'tish ishlaydi.

---

## ⚠️ Muhim eslatmalar (arxitektura qoidalari)

### 1. Import tartibi muhim
`habit_bot.py` dagi import tartibi handlerlarni telebot'da ro'yxatdan o'tkazadi. Circular import yo'q — `schedule_habit` kabi funksiyalar lazy import (`from scheduler import ...` funksiya ichida).

### 2. Callback dispatcher
`handlers_callbacks.py` barcha callback'larni oladi va 7 ta sub-modulga yo'naltiradi — sub-modul `True` qaytarsa, boshqasiga o'tmaydi.

### 3. Flask routes
`register_*_routes(app)` funksiyalari orqali ro'yxatdan o'tadi — `flask_api.py` dan chaqiriladi.

### 4. Frontend script tartibi muhim
**CSS:** `<head>` da `style.css` → `style-city.css` (shahar CSS `style.css` dan KEYIN — cascade: `.city-bld-glass-*` selektorlari `.city-bld polygon` ni override qilishi shart).
**JS:** `strings.js` → `app-core.js` (`<head>` da), keyin `app-pages.js` → `app-stats.js` → `app-profile.js` → `app-habits.js` → `app-social.js` → `app-reminders.js` → `app-city.js` → `app-city-buildings.js` → `app-city-move.js` (body oxirida). Tartibni buzish global o'zgaruvchilarning topilmasligiga olib keladi. **Muhim:** `app-city-buildings.js` aynan `app-city.js` dan KEYIN (CITY_* konstantalar va `cityIsoX/Y` ga tayanadi). `app-city-move.js` ikkalasidan ham KEYIN (`_cityData`, `CITY_TILE_*`, `cityIsoX/Y` ga tayanadi, va `cityBuildingSVG` orqali yaratilgan `data-habit-id` atributiga).

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
WebApp → `/api/shop/stars_invoice` → `bot.send_invoice()` (XTR currency) → `handle_pre_checkout` (auto-OK) → `handle_successful_payment` (`handlers_text.py`) → **idempotency check** (`charge_id` `stars_payments[]` ro'yxatida bo'lsa rad etiladi) → **faqat `gift_box`** qo'llab-quvvatlanadi (random mukofot) → foydalanuvchiga xabar. Noma'lum `item_id` → `raise ValueError` → mavjud `except` blok ushlab foydalanuvchiga 3 tilli xato xabari + admin link tugmasi, adminga avtomatik bildirishnoma (`charge_id`/`payload`/xato). Har qanday boshqa xato (`save_user` MongoDB uzilishi va h.k.) ham xuddi shu yo'l bilan ishlanadi.

### 11. Mahsulot vazifalari stack qilinadi
Badge'lar (`badge_fire/star/secret` — 3%/5%/12%) + car (`car_sport` — 8%) **stack qilinadi**, `_apply_item_bonuses()` B variant (majburiy +1 ball kafolat). Pet'lar alohida: `pet_dog` kunlik +2 (`_apply_pet_dog_bonus`), `pet_cat` 7 kunda 1 streak save (`_try_pet_cat_save` scheduler.py da), `pet_rabbit` jon jazosi 50% yumshoq (`_apply_pet_rabbit_soften`).

### 12. Sotib olish tasdig'i zanjiri
`buyItem()` → `confirmBuyItem()` → `_doConfirmedBuy()` → `_executeBuy()`. Foydalanuvchi "Ha" bosmagunicha hech narsa olinmaydi (qo'li tegib ketishdan himoya).

### 13. Inventory banda va modal
Reyting (podium/4-10/my-row) + profil: `🎒 N` o'rniga **eng qimmat top-1 emoji + `+N`** (`👑 +8`). Backend: `items_list: [{id, qty, price}, ...]` (`SHOP_PRICES.get(iid, 0)` fallback). Frontend: `_invBadgeDisplay(u)` price bo'yicha sort → `.slice(0, 1)`. **Cache trick:** `window._invCache` onclick XSS safe. Modal `openUserInventory(userName, itemsList)` — `.shop-modal-*` qayta ishlatadi, 250ms fade-out. Press effekti: `.inv-badge-clickable:active` scale 0.88.

### 14. Statistika streak mantig'i
`summary.streak` = barcha odatlar streaklari **yig'indisi** (Sport=3 + Dasturlash=8 = 11). `summary.best_streak` = har odatning `best_streak` maksimumi (all-time rekord — `daily_reset()` ga tegmaydi). Checkin 2 joyda sinxron yangilaydi: `callbacks_checkin.py` / `callbacks_checkin_done.py` (bot) va `flask_routes_data.py` `/api/checkin` (WebApp). Fallback: `max(h.get("best_streak", 0), h.get("streak", 0))`.

### 15. Tasdiqlash tugmasi: yagona `checkinRingHTML` helper
Odat va eslatma kartalaridagi tasdiqlash tugmasi **`app-core.js` `checkinRingHTML(percent, isDone, label, size=42)`** orqali render qilinadi (DRY pattern). Vizual: `Odat 1/9` halqasi uslubida — pending=bo'sh kulrang halqa (ichida hech narsa yo'q — toza ko'rinish, foydalanuvchini "belgilanmagan" deb chalg'itadigan ✓ yo'q), repeat qisman=kulrang track + to'q yashil progress yoy + kulrang `N/M` matn, done=ochroq yashil halqa + ochroq yashil ✓ (xirashroq `#7DC29A` — done karta `opacity: 0.45` bilan birga ohanglashadi). Karta foniga singadi, e'tibor odat nomiga tortiladi. **Real-time yangilash:** `checkin()` da `btn.innerHTML = checkinRingHTML(...)` to'g'ridan-to'g'ri qayta yoziladi (oldingi animatsion glow ring bilan murakkab sinxronlash mantig'i kerak emas — animatsiya yo'q). **Yangi joyda tasdiqlash tugmasi kerak bo'lsa** (kelajak feature) — `checkinRingHTML` chaqirilsin, alohida SVG yozilmaydi.

**Save tugmasi spinneri (yagona `.save-btn-spinner`):** Modal save tugmalari (odat — `app-habits.js:saveHabit`, eslatma — `app-reminders.js:saveReminder`) saqlash davomida bir xil vizual: 16×16 ingichka aylanuvchi halqa + matn (`profile.saving_clean` — ⏳ emojisiz, 3 til). CSS `style.css` `.save-btn-spinner` (mavjud `spin` keyframe qayta ishlatadi). Pattern: `btn.innerHTML = '<span class="save-btn-spinner"></span>' + S('profile','saving_clean')`. Matn qaytarish: `textContent` orqali (DOM avtomatik tozalanadi, span yo'qoladi). Yangi modal save tugmasi qo'shilsa — shu pattern ishlatilsin.

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
2. **"Muhim eslatmalar" qoidalari > 25 ta** (hozirgi: 23 ta)
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

### 22. Scheduler job tozalash intizomi
`daily_reset()` ichida `schedule.get_jobs()` aylantirilganda — **tizim joblari saqlanishi SHART**: `SYSTEM_JOB_TAGS` set'i (`daily_reset`, `weekly_report`, `monthly_report`, `yearly_report`, `evening_reminder`, `challenge_resolve`, `habit_health`). Faqat **odat eslatma joblari** (tagsiz yoki boshqa tagli) tozalanadi, chunki ular kun davomida o'zgarishi mumkin (odat qo'shilish/o'chirilish). Yangi tizim jobi qo'shilganda — `SYSTEM_JOB_TAGS` ga ham qo'shing, aks holda 00:00 da `daily_reset` uni o'chirib yuboradi va hisobot/eslatma kelmay qoladi.

### 23. Javobsiz eslatmalarni avto-tozalash
`send_reminder()` (odat eslatmasi), `send_evening_reminders()` (kechki eslatma) va `send_one_time_reminder()` (bir martalik eslatma — `reminders_scheduler.py`) yuborilgan xabarning `{message_id, date_uz5}` ni `pending_reminders` ga yozadi (max 200 entry). `daily_reset()` 00:00 UZ+5 da kechagi (`date_uz5 < today_str`) entry'larni `bot.delete_message()` bilan chatdan o'chiradi — bugungilar qoladi (hali javob berish vaqti bor). Tugma bosilganda xabar darhol/3s keyin o'chadi (mavjud xulq `callbacks_checkin.py` / `callbacks_checkin_done.py` va `callbacks_reminders.py` da), stale entry ertasi kuni sukut bilan tozalanadi. Maqsad: foydalanuvchi chati toza. **Yangi yuboriladigan takrorlanuvchi xabar turlari qo'shilsa** (masalan, haftalik eslatma, challenge ogohlantirishi) — xuddi shunday pattern bilan `pending_reminders` ga yozing. **Istisno — 💀 jon 0% xabari:** `pending_reminders` ga YOZILMAYDI. Buning o'rniga `jonfix` callback bosilganda 💀 xabar darhol o'chadi (`bot.delete_message(call.message.message_id)`) — bir martalik, jon tiklash bilan birga. Sabab: bu ogohlantirish javob talab qiladi (jon tiklash yoki odat bajarish), kun oxirida sukut bilan o'chmasligi kerak edi, lekin foydalanuvchi javob bergach chat toza qolishi uchun callback'da o'chiriladi.

### 24. Streak shield — bitta xabar, bitta qaror
`daily_reset()` 00:00 UZ+5 da foydalanuvchi uchun **barcha xavf ostidagi odatlarni** `at_risk_habits` ro'yxatiga yig'adi, loop tugagach **1 ta umumiy xabar** yuboradi (har odat uchun alohida emas). Tugmalar: `shield_use_all` / `shield_skip_all` — `callbacks_habits.py` da qayta ishlanadi. Mantiq: **1 ta shield barcha xavfli odatlarga ishlaydi** (odatlar soni muhim emas). "Ha": `streak_shields -= 1`, `pending_shield` dagi BARCHA odat streaki tiklanadi, `pending_shield = {}`. "Yo'q": `pending_shield = {}`, shield tegmaydi. Eski `shield_use_<habit_id>` / `shield_skip_<habit_id>` handler'lar **backward compat** uchun saqlangan (chatda qolgan eski xabarlar uchun), lekin `shield_use_all` / `shield_skip_all` bilan to'qnashmaslik uchun `and cdata != "shield_use_all"` guard qo'shilgan. Tarjimalar: `texts.py` `shield_risk_*` / `shield_used_*` / `shield_skipped` kalitlari 3 tilda. Pet_cat streak save logikasi (shield yo'q holatda) alohida va tegmagan.

### 25. Auto-save Telegram first_name (maxfiylikni hurmat qilib)
Foydalanuvchi `/start` bosmasdan toʻgʻridan-toʻgʻri WebApp'ga kirsa, DB'da `name` boʻsh qoladi va reytingda `?` koʻrinadi. Yechim: API endpointlari boshida (hozir `/api/rating` va `/api/profile`) DB'da `name` boʻsh boʻlsa — `flask_helpers.get_init_tg_first_name()` orqali `X-Init-Data` headeridan Telegram `first_name` olinadi va DB'ga yoziladi. Manba ishonchli: `verify_init_data()` HMAC-SHA256 bilan imzoni tasdiqlaydi (frontend soxta qila olmaydi). **Maxfiylik qoidasi:** Telegram'da `first_name` boʻsh boʻlsa — DB'ga hech narsa yozilmaydi, `?` fallback qoladi (foydalanuvchi atayin ismsiz boʻlishni tanlagan — hurmat qilish kerak). Tegilmaydigan fallback chegarasi: `flask_routes_core.py` 3 joyda `u.get("name", "?")` literal saqlanadi (xavfsizlik tarmog'i). **Kelajakka qoida:** yangi endpoint qo'shilsa va u ham DB'dan ism o'qisa — shu pattern ishlatilsin (yoki umumlashtirilgan helper `auto_save_tg_name(uid, udata)` qilinsin). `verify_init_data()` endi `(uid, user_obj)` tuple qaytaradi — eski `return uid` imzosi o'zgartirilgan; yangi kod yozilganda diqqat.

### 26. Points history pattern (period reyting filtrlari uchun)
Reyting `/api/rating?period=week|month|all` filtri toʻliq ishlashi uchun har `udata["points"]` oʻzgartirilganda **`add_points_history(udata, delta)`** chaqirilishi SHART (`save_user(uid, udata)` dan oldin, lock ichida). Bu `points_history: {"YYYY-MM-DD": net_delta_int}` field'ini saqlaydi va backend `get_points_in_period(udata, days)` orqali davriy ball yigʻindisini hisoblaydi. **Streak filtri** alohida — `done_log` dan dinamik hisoblanadi (`get_streak_in_period`), DB tarixi shart emas. **Pattern oddiy `+/-`:** `u["points"] += N; add_points_history(u, N); save_user(uid, u)`. **Pattern `max(0, ...)`:** `_old = u.get("points", 0); u["points"] = max(0, _old - N); add_points_history(u, -N)` — `-N` symmetric delta (done branch `+N` bilan teskari). **DIQQAT:** `u["points"] - _old` ishlatmang — clamp tufayli noto'g'ri delta beradi (audit #8/#9). `points` (real ball) clamp bilan saqlanadi, `points_history` esa to'liq audit yozuvi sifatida saqlanadi. **Backward compat (3 qatlamli mantiq `get_points_in_period`):** Layer 1 — `days=None` ('Barchasi') holatida har doim umumiy `udata["points"]` qaytariladi (chunki `points_history` to'liq tarix emas — yangi pattern qo'shilgandan keyingi delta'larni saqlaydi xolos, umumiy ball ishonchliroq). Layer 2 — `days=N` va history bor → aniq period yig'indisi. Layer 3 — `days=N` va history yo'q (eski user) → `done_log` dagi davriy faol kunlar × 5 ball proxy (taxminiy, bonus/booster hisobga olinmaydi, lekin eski foydalanuvchilarni reytingda 0 ball bilan butunlay yiqitmaydi). Yangi action qilgan eski user uchun history asta-sekin to'lib boradi va Layer 2 ga o'tadi (vaqt o'tgan sari aniqlik oshadi). **Hozirgi qamrov (7 ta fayl):** `callbacks_checkin.py` / `callbacks_checkin_done.py` (checkin/undo + audit #5 dan keyin badge/car/pet_dog bonus — `points_logic.py` funksiyalari `add_points_history` ni o'zi chaqiradi), `callbacks_shop.py` (jon + reset), `scheduler.py` (streak milestone, challenge resolve), `flask_routes_extra.py` (shop API, sell, challenge stake), `handlers_text.py` (referral, transfer, admin manual, Stars gift_box), `flask_routes_data.py` (WebApp checkin, pet_dog bonus, streak milestone). **Kelajakka qoida:** yangi joy `points` oʻzgartirsa — `add_points_history` chaqirish unutilmasin, aks holda davriy reyting noaniq boʻladi. Backend `entries.append({...})` da `points`/`streak` field'lari period qiymatlari bilan toʻldirilgan, `total_points`/`total_streak` umumiy qiymatlar saqlangan.

### 27. City (shahar) bino progress pattern
Habit checkin oqimi har bir nuqtasida (bot + WebApp) bino progress **sinxron** yangilanishi kerak — aks holda foydalanuvchining shahari haqiqiy progress bilan moslashmay qoladi. Pattern: `update_building_progress(udata, habit_id, delta)` chaqiriladi — `+1` (simple done / repeat fully done), `-1` (simple undo / repeat fully undo). Repeat habit `1/N` qisman holatida progress **o'zgartirilmaydi** — faqat `done >= rep_count` bo'lganda. **MUHIM QAROR:** `daily_reset` (kun o'tkazilgan habit) city ga **TEGMAYDI** — bino joyida qoladi (foydalanuvchi qarori). **Hozirgi qamrov (3 ta fayl):** `callbacks_checkin.py` (bot `toggle_` — simple/repeat done/undo), `callbacks_checkin_done.py` (bot `done_` — bildirishnomadan), `flask_routes_data.py` (`/api/checkin` — yagona joy yondashuv: `_city_delta` boshida `0`, 4 ta scenariy belgilaydi, save_user oldida bitta chaqiruv). **Habit o'chirilganda** `delete_building_for_habit(u, habit_id)` ham chaqirilsin **ikkala joyda** (Qoida #10 — bot/WebApp sinxron): bot `callbacks_habits.py:confirm_delete_*` va WebApp `flask_routes_core.py:api_habits_delete` (lazy import `from city_logic import delete_building_for_habit` — circular import oldini olish uchun, `save_user`'dan oldin, try/except ichida). Aks holda bino "orfan" qoladi va shaharda mavjud bo'lmagan odatga bog'liq. **Try/except majburiy:** har chaqiruv `try: update_building_progress(...) except Exception: print("[city] ...")` ichida — city xato bo'lsa asosiy habit checkin BUZILMASIN (city ikkilamchi feature, asosiy oqim muhimroq). **Eski user'lar uchun auto-init:** `update_building_progress` o'zi tekshiradi — agar bino yo'q va `delta > 0` bo'lsa, avtomatik `create_building` chaqiriladi (random tip, random bo'sh katak). **Backfill + Resync + Cleanup (sinxronlash, `GET /api/city/<uid>` da):** `flask_routes_city.py:api_city_get` ichida `compact_buildings_to_center` dan keyin **`backfill_buildings_from_habits`** chaqiriladi (Variant B: har odat uchun bino yaratadi, hatto hech qachon tasdiqlanmagan bo'lsa ham — README §314 ga mos. Progress = `min(effective_done, 66)`. **effective_done formula (Qoida #10 — statistika bilan sinxron): `effective_done = max(total_done, history_count)`** — ikkala manbadan eng yuqori qiymat. total_done DB'dagi rasmiy hisob (faqat to'liq kun yopilganda o'sadi, repeat odatlar uchun cheklangan), history_count history dan habit_id tasdiqlangan barcha kunlar yig'indisi. Repeat odatlar (Suv ichish 1/2, Uyqu 1/3) qisman tasdiqlanganda total_done o'sib qolmaydi, lekin history har tasdiqlashni hisoblaydi — max formula chalkashlikning oldini oladi. Statistika `api_stats` bir xil formula ishlatadi (Qoida #11)), keyin **`resync_building_progress`** chaqiriladi (mavjud binolar progress'ini effective_done bilan sinxronlaydi — faqat KO'TARADI, past tushirmaydi. Backfill yangi binolarni to'g'ri yaratadi, lekin avvaldan mavjud binolar past balandlikda qolib ketgan bo'lishi mumkin — resync ularni to'g'rilaydi. Eskirgan mantiq bilan yaratilgan binolar uchun ham foydali — bir martalik tuzatish), undan keyin **`cleanup_orphan_buildings`** chaqiriladi (eski o'chirilgan odatlardan qolgan orfan binolarni o'chiradi — backward compat, A qism deploy'gacha bo'lgan iflosliklar uchun). Uchchalasi idempotent va try/except ichida (`compact` bilan bir xil pattern); har biri o'z `save_user`'ini chaqiradi (faqat o'zgarish bo'lsa). Tartib MUHIM: avval mavjud odatlar uchun bino yaratiladi (backfill), keyin mavjudlarning balandligi to'g'irlanadi (resync), keyin mavjud bo'lmagan odatlarning binolari o'chiriladi (cleanup) — turli operatsiyalar, bir-biriga aralashmaydi. **Insurance:** `update_building_progress` o'zi tekshiradi — `_is_insurance_active(city)` bo'lsa va `delta < 0` bo'lsa, regress bekor qilinadi (faqat undo joylarida ishlaydi — `daily_reset` city ga tegmagani uchun). **Kelajakka qoida:** yangi habit checkin joyi qo'shilsa (masalan, yangi callback yoki API) — `update_building_progress` chaqirish unutilmasin, aks holda bot/WebApp orasida desinxron yuzaga keladi (foydalanuvchi WebApp'da tasdiqlasa bino qurilsa, bot'dan tasdiqlasa qurilmasa — chalkash UX). **Daily_reset'ga `-1` chaqirig'ini QAYTA QO'SHMANG** — bu yopiq qaror.

### 28. Loyiha bo'ylab tarqalgan muammolar — darhol qayd qilish, lokal tuzatish
Audit jarayonida muammo bir joyda topilib, **boshqa joylarda ham tarqalgan** bo'lishi mumkinligi aniqlansa (race condition, izchillik, security pattern, takrorlanuvchi bug) — uni unutmaslik uchun darhol amal qilish kerak. **Sabab:** kelajakda u joyni ko'rib chiqish imkonsiz bo'lib qolishi yoki muammo haqiqatan paydo bo'lganda eslamasligi mumkin. **Algoritm:** (1) **Darhol `SESSION_LOG_audit.md` boshidagi "🎯 STRATEGIK MUAMMOLAR" bo'limiga qayd qiling** (S1, S2, S3... raqamlash bilan) — qaysi fayllar zarar ko'rishi mumkin, xavf darajasi, mavjud yarim yechimlar, strategik yechim variantlari. (2) Agar muammo **mustaqil tuzatilishi mumkin bo'lsa** (boshqa joylarga ta'sirsiz, kichik o'zgarish) — **darhol tuzating** (qoida #04 buzilmaydi, chunki bu boshqa "yaxshilik" emas — bu o'sha audit doirasidagi tuzatish). (3) Agar **strategik infrastruktura kerak bo'lsa** (MongoDB atomic operatsiyalar, global lock, butun loyiha bo'ylab refactor) — `SESSION_LOG_audit.md` ga to'liq tafsilot bilan yozing va **keyingi sessiyaga qoldiring** (alohida audit sessiyasi). (4) Qoidalar #04 + #09 + #23 saqlanadi — bir muammoni tuzatganda boshqasiga sakramaslik, lekin **eslab qoldirilishi va `SESSION_LOG_audit.md`'ga yozilishi shart**. **Hozirgi strategik muammolar:** `SESSION_LOG_audit.md` boshini ko'ring (S1: race condition `load_user`/`save_user` pattern butun loyiha bo'ylab; S2: ball transfer atomic emas; S3: `bot.get_me()` cache'siz chaqiruvlari). Yangi audit sessiyasida birinchi qadam — `SESSION_LOG_audit.md` ni o'qish (mavjud strategik muammolar va oxirgi audit qaydlari bilan to'qnashmaslik uchun).

---

## 🔗 Bog'liqlik xaritasi

Modullar orasidagi `import` bog'liqligi — **koddan avtomatik chiqarilgan** (taxmin emas). Bir faylni o'zgartirishdan oldin "kim meni import qiladi" ustunига qarang — ta'sir doirasi shu (Qoida #9).

**Qatlamlar** (pastdan yuqoriga — pastki qatlam yuqorisini import qilmaydi):
- **L0 (poydevor):** `config`, `texts`, `motivation`, `handlers_onboarding`, `db_lock` — hech qanday lokal modul import qilmaydi
- **L1 (ma'lumot):** `database` (→config), `helpers` (→database, texts)
- **L2 (yadro):** `bot_setup`, `city_logic`, `points_logic`, `flask_helpers`
- **L3 (mantiq):** `achievements`, `menus`, `handlers_*`, `scheduler`, `reminders_scheduler`
- **L4 (callback/route):** `callbacks_*`, `flask_routes_*`
- **L5 (yig'uvchi):** `handlers_callbacks`, `flask_api`
- **L6 (kirish nuqtasi):** `habit_bot` — hech kim import qilmaydi

| Modul | → import qiladi | ← kim import qiladi |
|-------|-----------------|---------------------|
| `config` | — | deyarli barcha modul |
| `texts` | — | `callbacks_settings`, `helpers`, `scheduler`, `handlers_*`, `flask_routes_data/extra`, `habit_bot` |
| `motivation` | — | `handlers_commands/stats/text`, `scheduler`, `flask_routes_data`, `habit_bot` |
| `handlers_onboarding` | — | `habit_bot` |
| `db_lock` | — (faqat `threading`, `contextlib`) | `handlers_text` (+ kelajakda `callbacks_shop`, `callbacks_checkin*`, `flask_routes_data/extra` — S1 migratsiyasi davom etmoqda) |
| `database` | `config` | deyarli barcha modul |
| `helpers` | `database`, `texts` | deyarli barcha modul |
| `bot_setup` | `config`, `database`, `helpers` | deyarli barcha L3–L5 modul |
| `city_logic` | `config`, `database` | `callbacks_checkin`, `callbacks_checkin_done`, `callbacks_habits`, `scheduler`, `flask_routes_city/core/data` |
| `points_logic` | `config`, `database` | `callbacks_checkin`, `callbacks_checkin_done`, `flask_routes_data` |
| `flask_helpers` | `config` | `flask_api`, `flask_routes_*` (barcha 5 ta) |
| `achievements` | `bot_setup`, `database`, `helpers` | `callbacks_checkin`, `callbacks_checkin_done`, `flask_routes_core/extra`, `habit_bot` |
| `menus` | `bot_setup`, `database`, `helpers` | `callbacks_admin/menu`, `handlers_callbacks/commands/text`, `habit_bot` |
| `handlers_rating` | `bot_setup`, `database`, `helpers` | `callbacks_menu`, `habit_bot` |
| `handlers_stats` | `bot_setup`, `config`, `database`, `helpers`, `motivation`, `texts` | `callbacks_habits`, `callbacks_menu`, `scheduler`, `habit_bot` |
| `handlers_commands` | `bot_setup`, `config`, `database`, `helpers`, `menus`, `motivation`, `texts` | `habit_bot` |
| `handlers_text` | `bot_setup`, `config`, `database`, `db_lock`, `helpers`, `menus`, `motivation`, `scheduler`, `texts` | `habit_bot` |
| `scheduler` | `bot_setup`, `city_logic`, `config`, `database`, `handlers_stats`, `helpers`, `motivation`, `texts` | `callbacks_checkin`, `callbacks_checkin_done`, `flask_routes_core/extra`, `handlers_text`, `habit_bot` |
| `reminders_scheduler` | `bot_setup`, `config`, `database`, `helpers` | `callbacks_reminders`, `habit_bot` |
| `callbacks_habits` | `bot_setup`, `callbacks_checkin`, `city_logic`, `database`, `handlers_stats`, `helpers` | `handlers_callbacks` |
| `callbacks_checkin` | `achievements`, `bot_setup`, `callbacks_checkin_done`, `city_logic`, `config`, `database`, `helpers`, `points_logic`, `scheduler` | `callbacks_checkin_done`, `callbacks_habits` |
| `callbacks_checkin_done` | `achievements`, `bot_setup`, `callbacks_checkin`, `city_logic`, `config`, `database`, `helpers`, `points_logic`, `scheduler` | `callbacks_checkin` |
| `callbacks_admin` | `bot_setup`, `config`, `database`, `helpers`, `menus` | `handlers_callbacks` |
| `callbacks_menu` | `bot_setup`, `config`, `database`, `handlers_rating`, `handlers_stats`, `helpers`, `menus` | `handlers_callbacks` |
| `callbacks_reminders` | `bot_setup`, `helpers`, `reminders_scheduler` | `handlers_callbacks` |
| `callbacks_settings` | `bot_setup`, `config`, `database`, `helpers`, `texts` | `handlers_callbacks` |
| `callbacks_shop` | `bot_setup`, `config`, `database`, `helpers` | `handlers_callbacks` |
| `flask_routes_city` | `city_logic`, `config`, `database`, `flask_helpers` | `flask_api` |
| `flask_routes_core` | `achievements`, `bot_setup`, `city_logic`, `config`, `database`, `flask_helpers`, `helpers`, `scheduler` | `flask_api` |
| `flask_routes_data` | `bot_setup`, `city_logic`, `config`, `database`, `flask_helpers`, `helpers`, `motivation`, `points_logic`, `texts` | `flask_api` |
| `flask_routes_extra` | `achievements`, `bot_setup`, `config`, `database`, `flask_helpers`, `helpers`, `scheduler`, `texts` | `flask_api` |
| `flask_routes_reminders` | `config`, `database`, `flask_helpers` | `flask_api` |
| `handlers_callbacks` | `bot_setup`, `callbacks_*` (6 ta: admin, habits, menu, reminders, settings, shop), `database`, `helpers`, `menus` | `habit_bot` |
| `flask_api` | `flask_helpers`, `flask_routes_*` (barcha 5 ta) | `habit_bot` |
| `habit_bot` | L0–L5 modullarning ko'pi (`achievements`, `bot_setup`, `config`, `database`, `flask_api`, `handlers_*`, `helpers`, `menus`, `motivation`, `reminders_scheduler`, `scheduler`, `texts`) | — (kirish nuqtasi) |

**⚠️ Nazorat ostidagi circular import:** `callbacks_checkin` ↔ `callbacks_checkin_done` bir-birini import qiladi. Buzilmaydi, chunki `callbacks_checkin.py` `STREAK_MILESTONES` va `_check_streak_milestone` ta'rifidan **keyin** `callbacks_checkin_done` ni import qiladi (modul yarmigacha yuklangач). Bu ikki faylning import tartibini o'zgartirmang.

**Eslatma:** yuqoridagi jadval `import X` / `from X import ...` (modul boshidagi) larни qamraydi. Funksiya ichidagi lazy import'lar (masalan circular oldini olish uchun) bu jadvalga kirmasligi mumkin — batafsil bog'liqlik feature qo'shganda tekshiriladi.
