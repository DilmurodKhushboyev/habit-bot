# 🔧 Sessiya qaydi — Audit (umumiy log)

> **Maqsad:** Yangi feature emas — borini mukammallashtirish, kamchiliklarni
> tuzatish, chala/o'lik kodni olib tashlash.

---

## 📖 BU FAYL HAQIDA (Claude uchun yo'l-yo'riq — har sessiya boshida o'qing)

**Bu fayl auditning yagona manbasi.** Bu yerda 3 narsa saqlanadi:

1. **🎯 STRATEGIK MUAMMOLAR** (quyida) — butun loyiha bo'ylab tarqalgan, alohida
   sessiyada hal qilinishi kerak bo'lgan muammolar (S1, S2, S3...). Yangi audit
   sessiyasi boshlanishidan oldin **majburiy o'qing** — mavjud strategik
   muammolar bilan to'qnashmaslik va ularni qayta "kashf qilmaslik" uchun.

2. **✅ AUDIT TARIXI** (o'rtada) — yakunlangan auditlar (#4, #5, #6, #7...) —
   qaysi fayllar, qaysi muammolar tuzatildi, qaysi qoldirildi, revert plan.
   Bir xil joyni qayta audit qilmaslik uchun ko'ring.

3. **🔵 KEYINGI SESSIYAGA** (oxirida) — joriy sessiyada qoldirilgan ishlar,
   keyingi audit prioritetlari, foydalanuvchiga eslatma.

**Qoida №28 (README) ga muvofiq:** Audit jarayonida loyiha bo'ylab tarqalgan
yangi muammo topilsa — quyidagi "🎯 STRATEGIK MUAMMOLAR" bo'limiga **darhol**
qo'shing (S4, S5... raqamlash bilan). Yo'qotilgan kontekst keyingi sessiyada
muammoni "ko'rinmas" qiladi — har topilgan strategik masala SHU faylda.

**Yangi audit sessiyasini boshlash:**
1. Bu faylni o'qing — STRATEGIK MUAMMOLAR + oxirgi "🔵 KEYINGI SESSIYAGA" bo'limi
2. README'ni o'qing — 28 ta qoida, ayniqsa #04, #09, #23, #28
3. Foydalanuvchi yuborgan kod fayllarini o'qing
4. Auditni boshlang

---

## 🎯 STRATEGIK MUAMMOLAR — Loyiha bo'ylab tarqalgan

> Bu muammolarni **bir joyda tuzatib bo'lmaydi** — butun loyiha bo'ylab tarqalgan,
> infrastruktura darajasida hal qilinishi kerak. Alohida sessiyada qo'l urilanadi.
>
> **Status belgilari:** 🔴 Yuqori xavf · 🟡 O'rta xavf · 🟢 Past xavf · ⚪ Tugatilgan

### 🔴 S1 — Race condition (load_user/save_user pattern) — MIGRATSIYA BOSHLANDI (#18)

**Topilgan:** Audit #5 (Stars to'lov)
**Tarqalish:** Butun loyiha — har joyda `u = load_user(uid); ...; save_user(uid, u)`

**⚙️ INFRATUZILMA TAYYOR (#18):** `db_lock.py` yaratildi — `user_lock(uid)` (bitta user) va `two_user_locks(a, b)` (transfer, deadlock-safe lock ordering: kichik uid avval). L0 qatlam (faqat `threading`/`contextlib`, circular import yo'q). Stress-test: 50 parallel checkin lock'siz 250→35 (ball yo'qoldi), lock bilan 250→250. Transfer 30x parallel double-spend yo'q, jami saqlandi.

**✅ #18 da migratsiya qilingan joylar (`handlers_text.py`):**
- 🔴 Transfer (`bozor_waiting_transfer_amount`) — `two_user_locks`, u+target_u lock ichida qayta o'qiladi, balans tekshiruvi lock ichida → double-spend + over-spend + qabul qiluvchi yo'qolishi YOPILDI (S2 ham — atomik zona).
- 🟡 Admin ball berish (`admin_waiting_points_amount`) — `two_user_locks`, target_u lock ichida.
- 🟡 Referral bonus (referrer `u_ref`) — `user_lock(referrer_id)`, lock ichida o'qiladi.
- 🔴 Stars to'lov (`handle_successful_payment`) — `user_lock(uid)`, idempotency tekshiruvi (charge_id) HAM lock ichida → duplicate event 2x mukofot xavfi yopildi.

**⏳ Migratsiya QOLGAN joylar (keyingi bosqichlar):**

**Muammo:** Ikki jarayon bir vaqtda bir userning `udata` sini o'qib, modifikatsiya
qilib, yozsa — keyingi yozish oldingisini **o'chiradi** (last-write-wins).

**Aniq topilgan joylar:**

| Fayl | Joy | Senariy | Xavf | Holat |
|------|-----|---------|------|-------|
| `handlers_text.py` | transfer (double-spend) | Tugma 2x bosilsa ball "yaratiladi" | 🔴 | ✅ #18 |
| `handlers_text.py` | transfer (qabul qiluvchi checkin) | Checkin yo'qoladi | 🔴 | ✅ #18 |
| `handlers_text.py` | admin ball berish | Target checkin to'qnashishi | 🟡 | ✅ #18 |
| `handlers_text.py` | referral bonus | Referrer checkin to'qnashishi | 🟡 | ✅ #18 |
| `handlers_text.py` | Stars to'lov | Duplicate event / checkin | 🔴 | ✅ #18 |
| `callbacks_shop.py` | 83-86 (jon sotib olish) | Ayni vaqtda checkin → ball yo'qoladi | 🟡 | ✅ #19 |
| `callbacks_shop.py` | 198-203 (reset) | Ayni vaqtda ball qo'shilsa → yo'qoladi | 🟡 | ✅ #19 |
| `callbacks_checkin.py` | hammasi | Standart checkin pattern | 🟡 | ✅ #19 |
| `callbacks_checkin_done.py` | hammasi | Bildirishnomadan checkin | 🟡 | ✅ #19 |
| `flask_routes_data.py` | api_checkin | WebApp checkin | 🟡 | ⏳ |
| `flask_routes_core.py` | habits CRUD | Odat | 🟢 | ⏳ |
| `scheduler.py` | daily_reset, milestone | Cron job + bot xabari to'qnashishi | 🟡 | ⏳ |
| `flask_routes_extra.py` | api_friends_add | Mutual friends (Audit #10) | 🟡 | ⏳ |
| `flask_routes_extra.py` | shop buy/sell/activate | Mavjud `_get_shop_lock` → `db_lock` ga ko'chirilsin (markazlashtirish) | 🟡 | ⏳ |

**Mavjud yarim yechim:** `flask_routes_extra.py` da `_get_shop_lock(uid)` per-user
`threading.Lock` (faqat WebApp shop himoyalangan, bot tomonida yo'q).

**Strategik yechim variantlari:**
- **Variant 1 — MongoDB atomic operatsiyalar (`$inc`, `$push`):** Eng kuchli
  (multi-process safe), lekin `udata` nested → katta refactor.
- **Variant 2 — Global per-user lock (`db_lock.py`):** `with user_lock(uid):` —
  kod minimal o'zgaradi. Multi-process safe emas (faqat bitta Railway instance),
  hozircha yetarli.

**Tavsiya:** Variant 2 (oson, tez). Variant 1 keyinroq scale-out kerak bo'lganda.

**Keyingi qadam:** Alohida sessiya — `db_lock.py` + asta-sekin har faylni migratsiya.

---

### 🟡 S2 — Ball transfer atomic emas (rollback yo'q)

**Topilgan:** Audit #7 (`callbacks_shop.py`)
**Tarqalish:** `handlers_text.py` 443-451 (ball transfer), `flask_routes_extra.py` 660-665 (`api_challenges_accept` — Audit #10 qayd)

**Muammo:** Transfer = 2 ta `save_user`. Agar 2-`save_user` xato bersa
(MongoDB uzilishi), birinchi qabul qilingan — ball yo'qoladi.

**Misol:** A → B ga 50 ball:
- A: `100 → 50` ✅
- B: `200 → 250` ❌ (MongoDB xato)
- Natija: **50 ball yo'qoldi** (atomic emas, rollback yo'q)

**Strategik yechim:**
- MongoDB transactions (Atlas free tier qo'llab-quvvatlaydi)
- Yoki rollback pattern: 2-save xato bo'lsa, 1-save ni qaytarish

**Keyingi qadam:** S1 bilan birga hal qilinadi.

---

### 🟢 S3 — `bot.get_me()` cache'siz chaqiruvlari

**Topilgan:** Audit #7 (`callbacks_shop.py`)
**Tarqalish:** Bir necha joyda (to'liq audit qilinmagan)

**Joylar:**
- `callbacks_shop.py:97` — `bot_info = bot.get_me()` (referral)
- (Boshqalari noma'lum — loyiha bo'ylab `grep` kerak)

**Mavjud yechim:** `bot_setup.py:get_bot_username()` (cache bilan helper).

**Muammo:** Ba'zi joylar helper'ni ishlatmaydi → har bosishda Telegram API so'rovi.

**Xavf:** 🟢 Past — Telegram ruxsat beradi, faqat kichik kechikish.

**Keyingi qadam:** Kichik refactor sessiyasi — `grep -rn "bot.get_me()" *.py`
va `get_bot_username()` ga almashtirish.

---

### ⚪ S4 — Bot tomonida streak milestone ball bermaydi (YOPILDI — audit #17)

**Status:** ⚪ YOPILDI — audit #17 da hal qilindi. `STREAK_MILESTONES` `config.py` ga ko'chirildi (8 ta, yagona manba, dict). Bot (`callbacks_checkin` toggle_/skip_ + `callbacks_checkin_done` done_) endi WebApp `api_checkin` bilan AYNI mantiq: `bonus` ball + `add_points_history` + `streak_milestones_sent[]` duplicate guard — ball asosiy thread'da (S1 race'dan qochib), xabar thread'da. WebApp `flask_routes_data` ham config'dan o'qiydi (avval lokal 5-elementli dict edi) + `title` lokalizatsiya qilindi (`texts.py streak_milestone_title`, 3 til — avval o'zbekcha hardcode). Bot xabariga `{bonus}` qo'shildi (3 til). 3 kanal to'liq sinxron, kanal asosidagi adolatsizlik yo'q. Batafsil: audit #17 qaydi.

**Tarixiy qayd (asl muammo):** WebApp ball berardi+guard bor edi, bot faqat xabar yuborardi (ball yo'q, guard yo'q → spam). Bot tuple (8 ta), WebApp dict (5 ta) — nomuvofiq. Endi dolzarb emas.

---

### 🗄️ S4 — TARIXIY TAFSILOT (yopilgan, ma'lumot uchun saqlangan)

**Topilgan:** Audit #8 (`points_logic.py` chaqiruvchilari audit)
**Tarqalish:** `callbacks_checkin.py`, `callbacks_checkin_done.py`, `flask_routes_data.py`

**Muammo:** WebApp `api_checkin` global streak milestone'da `ms["bonus"]` ball
beradi va `streak_milestones_sent[]` duplicate guard yozadi. Bot tomonida
(`callbacks_checkin.py:_check_streak_milestone` qator 29-37) **faqat tabrik
xabari yuboriladi — ball BERMAYDI**, duplicate guard ham yo'q (har checkin'da
xabar qayta yuboriladi).

**Natija:** Foydalanuvchi bot orqali milestone'ga yetsa — bonus ball yo'qotadi
va spam xabar oladi. Bir xil foydalanuvchi WebApp orqali bo'lsa — ball oladi.
**Kanal asosida tafovut → adolatsizlik.**

**Aniq tafovutlar:**

| Holat | WebApp (`flask_routes_data.py` qator 24-30, 328-336) | Bot (`callbacks_checkin.py` qator 26, 29-37) |
|-------|---------------------------------------------------|------------------------------------------|
| `STREAK_MILESTONES` turi | **dict** | **tuple** |
| Milestone qiymatlari | `7, 14, 30, 60, 100` (5 ta) | `3, 7, 14, 30, 60, 100, 180, 365` (8 ta) |
| Ball berish | ✅ `u["points"] += ms["bonus"]` | ❌ YO'Q |
| `add_points_history` | ✅ `ms["bonus"]` qo'shiladi | ❌ YO'Q (ball ham yo'q) |
| Duplicate guard | ✅ `streak_milestones_sent[]` | ❌ YO'Q (har checkin'da xabar) |
| Xabar yetkazish | response JSON `streak_milestone` | Telegram xabar `T(uid, "streak_milestone")` |

**Strategik yechim:**

1. **`STREAK_MILESTONES` ni `config.py` ga ko'chirish** (yagona manba, dict format):
   ```python
   STREAK_MILESTONES = {
       3:   {"emoji": "✨", "title": "...", "bonus": 5},
       7:   {"emoji": "🔥", "title": "...", "bonus": 10},
       14:  {"emoji": "⚡", "title": "...", "bonus": 20},
       30:  {"emoji": "💎", "title": "...", "bonus": 50},
       60:  {"emoji": "🏆", "title": "...", "bonus": 100},
       100: {"emoji": "👑", "title": "...", "bonus": 200},
       180: {"emoji": "🌟", "title": "...", "bonus": 300},
       365: {"emoji": "🎖️", "title": "...", "bonus": 500},
   }
   ```
2. **Bot tomonida ball berish** — `_check_streak_milestone` ga `u["points"] +=
   ms["bonus"]` + `add_points_history(u, ms["bonus"], today)` + `save_user`
   qo'shish (yoki chaqiruvchi joyga ko'chirish — `_check_streak_milestone`
   thread'da ishlaydi → save_user race condition).
3. **Duplicate guard** — bot tomoniga ham `streak_milestones_sent[]` tekshiruvi
   qo'shish (WebApp bilan sinxron — bir manba).
4. **Milestone qaror** — 3, 180, 365 milestone'lar WebApp da ham bo'lishi
   kerakmi? (Hozir bot 8 ta, WebApp 5 ta — `texts.py` da `streak_milestone`
   matni qaysi qiymatlarga moslangan? Qoida №22 — 3 tilda)

**Diqqat — race condition (S1 bilan bog'liq):** `_check_streak_milestone` bot
tomonida `threading.Thread` da ishlaydi (qator 152, 308) → agar ball berish shu
yerga qo'shilsa, `load_user`/`save_user` race condition (S1) bilan to'qnashadi.
Yaxshi yondashuv — ball berishni asosiy thread'da qilish (chaqiruvchi joyda),
faqat **xabar yuborish** thread'da qolsin.

**Keyingi qadam:** Alohida sessiya — `config.py` migration + 3 fayl sinxron
qilish + `texts.py` da 8 milestone uchun matn tarjima (qoida №22). S1 race
condition bilan to'qnashmaslik uchun ball berish bot'da asosiy thread'da
qo'shiladi.

---

### ⚪ S5 — Guruh hujjati race condition (YOPILDI — audit #14)

**Status:** ⚪ YOPILDI — guruh tizimi audit #14 da butunlay olib tashlandi (foydalanuvchi qarori). `flask_routes_core` `api_groups_*` endpointlari, `mongo_db["groups"]` kolleksiyasi, barcha guruh kodi o'chirildi. Race condition mavzusi endi mavjud emas.

**Tarixiy qayd (asl muammo):** S1 faqat user hujjatini qamrardi; guruh hujjati `find_one`→`replace_one` lock'siz edi. Endi dolzarb emas.

---

### ⚪ Tugatilgan strategik muammolar

(Hozircha bo'sh — birinchi strategik muammo hal qilinsa, shu yerga ko'chiriladi)

---

## 📋 Yangi strategik muammo qo'shish formati

```
### [xavf belgisi] S[raqam] — [Qisqa nom]

**Topilgan:** [Audit raqami / sessiya]
**Tarqalish:** [Fayllar / joylar]

**Muammo:** [Qisqa tushuntirish]

**Aniq topilgan joylar:** [Jadval yoki ro'yxat]

**Strategik yechim variantlari:** [Variantlar]

**Keyingi qadam:** [Aniq reja]
```

---

# ✅ AUDIT TARIXI (yakunlangan sessiyalar)

## ✅ #4 — `done_` vs `toggle_` repeat handler farqlari (YAKUNLANDI)

**Solishtirildi:** `callbacks_checkin.py` (`toggle_`) vs `callbacks_checkin_done.py`
(`done_`). 2 ta haqiqiy nomuvofiqlik topildi — ikkalasi ham `done_` repeat
fully-done blokida yetishmasdi:

**Tuzatish 1 — `h["best_streak"]` per-habit rekord saqlanish:**
`done_` repeat fully-done blokiga `if h["streak"] > h.get("best_streak", 0):
h["best_streak"] = h["streak"]` ikki qator qo'shildi (`toggle_` 128-129 dan
so'zma-so'z).

**Tuzatish 2 — XP booster decrement:**
`done_` repeat fully-done blokiga 4 qatorlik booster kun kamaytirish
qo'shildi (`toggle_` 168-172 dan so'zma-so'z). Avval booster faol foydalanuvchi
repeat odatni bildirishnomadan tasdiqlasa — booster kuni hech qachon
kamaymasdi (cheksiz booster bug'i).

Faqat `callbacks_checkin_done.py` o'zgardi. `toggle_` tegilmadi.

---

## ✅ WebApp `api_checkin` — `total_done` `_city_delta` ga bog'landi (YAKUNLANDI)

**Muammo edi:** `flask_routes_data.py` `api_checkin` 297-blok `is_done` ga
qarab `total_done` ni o'zgartirardi. Repeat partial holatda (`1/5`, `2/5`...)
`is_done = False` → `total_done` har safar **kamayardi**. 5 marta bosish:
`-1-1-1-1+1 = -3` net. Achievements va city `days_66_done` buzilardi.

**Tuzatish:** `total_done` yangilash sharti `is_done` o'rniga `_city_delta`
ga bog'landi:
- `_city_delta == +1` (fully done) → `+1`
- `_city_delta == -1` (undo) → `-1`
- `_city_delta == 0` (repeat partial) → tegilmaydi

Bot `toggle_`/`done_` bilan sinxron. `update_building_progress` ham
`_city_delta` ga bog'liq — ikkalasi bir signaldan, demak `days_66_done` va
city binosi endi sinxron.

---

## ✅ `scheduler.py` — city regress o'chirildi (YAKUNLANDI — foydalanuvchi qaroriga ko'ra)

**Tarix:** `daily_reset` ikkita `update_building_progress(udata, habit["id"], -1)`
chaqirig'iga ega edi (qator 394 repeat, 414 simple) — kun o'tkazilsa shahar
binosi regress bo'lardi.

**Birinchi tuzatish urinishi:** `update_data` dict ga `"city"` maydonini
qo'shdim (regress DB ga yozilmas edi). Sintaksis ✅, lekin foydalanuvchi
eslatdi: bu uning eski qaroriga zid — **shahar regress umuman bo'lmasligi
kerak edi** (joyida qolsin).

**To'g'ri yechim — Variant A (foydalanuvchi xohish + tavsiya):**
- Ikkala `update_building_progress(-1)` chaqirig'i o'chirildi (try/except
  bloklari bilan birga).
- `"city"` qo'shganim **kiritilmadi** — chunki regress yo'qligi sababli
  `daily_reset` `city` ga umuman tegmaydi.
- `from city_logic import update_building_progress` import qatori qoldirildi
  (kelajakda kerak bo'lishi mumkin, Qoida #4 — keraksiz "yaxshilik" qilmaslik).

**Natija:** Kun o'tkazilsa endi shahar binosi joyida qoladi.

**⚠️ Eslatma keyingi sessiyalar uchun:** Insurance feature endi `daily_reset`
da ishlamaydi (chunki regress yo'q). Lekin u hali ham undo'da ishlaydi
(`callbacks_checkin` qator 113, 268; `flask_routes_data` undo). Insurance
mantig'i ostida qayta ko'rib chiqilishi mumkin (alohida ish).

---

## ✅ `city_logic.py` `update_building_progress` — TOZA (TUZATISH YO'Q)

Audit doirasi: faqat checkin oqimi bilan bog'liq joylar (insurance check,
clamp 0..66, auto-init, `total_done` ga tegmaslik, exception handling).

**Natija:** Hech qanday bug topilmadi:
- Insurance faqat `delta < 0` da ishlaydi ✅
- Clamp `max(0, min(66, cur+delta))` to'g'ri ✅
- Auto-init faqat `delta > 0` da (regress'da bino yaratmaydi) ✅
- `total_done` ga TEGMAYDI ✅ (yuqoridagi tuzatishlar bilan ikki marta
  hisoblanish xavfi yo'q)
- `raise` qilmaydi, `None` qaytaradi ✅ (chaqiruvchilarning try/except — extra
  ehtiyot)
- `delta == 0` himoyasi mavjud, hech qaerda chaqirilmaydi (mudofaa kodi) ✅

Yuqoridagi 3 ta tuzatish `update_building_progress` ning to'g'ri yozilganligiga
tayanadi — endi buni tasdiqladik.

---

## 🔵 KEYINGI SESSIYAGA QOLDIRILDI

### `callbacks_checkin.py` ~360 qator — Qoida #24
- Foydalanuvchi aytdi: faylga bo'lmaymiz. Helper refactor varianti ham
  ball mantig'iga tegadi — alohida sessiya, shoshilinch emas.

### README qoidalar 27 → 25 birlashtirish — Qoida #21-F (trigger 2)
- Qoidalar soni 25 dan oshgan (avvalgi sessiyadan qoldirildi).

### Premium narx hardcode (eski sessiyadan)
- `app-core.js` `renderPremium()`: `freeLimit=3`/`premLimit=15` hardcode.
- Freemium qo'shilguncha kutadi.

### Insurance feature qayta ko'rib chiqish
- `daily_reset` regress o'chirilgach insurance faqat undo'da ishlaydi.
- Foydalanuvchilarga sotilayotgan bo'lsa — qiymati qayta baholanishi kerak.

### Tekshirilmagan fayllar (kelajak audit)
- `database.py` — `get_user_city` reference qaytarayotganini kod orqali
  tasdiqlash (amaliy ishlayotgani isbot, lekin manba ko'rilmadi),
  `add_points_history` izchilligi.
- `points_logic.py` — kichik (71 qator), sof funksiyalar, tezda tekshirish
  mumkin.
- Frontend `app-habits.js` — checkin POST tomonidan WebApp API ga to'g'ri
  payload yuborilayotgani.

---

## ⚪ MUHIM QAYDLAR (kelajak sessiyalar uchun)

### "City regress yo'q" — foydalanuvchi qarori
- `daily_reset` da `update_building_progress(-1)` chaqirilmaydi. Boshqa
  sessiyada bu qoidaga zid tuzatish kiritmaslik kerak (bu sessiyada men bu
  qarorni bilmasdim va xato yo'lda tuzatish kiritdim — foydalanuvchi
  to'g'irladi).

### `_city_delta` signal
- WebApp `api_checkin` ichida `_city_delta` 3 holat signali:
  - `+1` = fully done
  - `-1` = undo
  - `0` = repeat partial (hech narsa o'zgarmaydi)
- `total_done` va `update_building_progress` ikkalasi ham shu signalga
  bog'liq — sinxron qoladi.

---

## 📦 BU SESSIYADA O'ZGARGAN FAYLLAR
**Backend:**
- `callbacks_checkin_done.py` — 2 ta qo'shimcha (best_streak, XP booster)
- `flask_routes_data.py` — `total_done` mantiqi
- `scheduler.py` — 2 ta city regress chaqirig'i o'chirildi

**Hujjat:** `README.md` (§254 `scheduler.py` tavsifidan "City regress" qatori
olib tashlanadi), `SESSION_LOG_audit.md`

## ⚠️ DEPLOY ESLATMASI
- ✅ Backend 3 fayli GitHub'ga yuklanishi kerak.
- ✅ README yangilangan versiyasi yuklanishi kerak.
- Yangi fayl YO'Q — barchasi mavjud fayllarning yangilangan versiyasi.

## ↩️ REVERT
- `callbacks_checkin_done.py`: 6 qator (2 blok — best_streak 2 qator + booster
  4 qator + izoh) o'chirilsa eski holat qaytariladi.
- `flask_routes_data.py`: 297-blok eski `is_done` mantig'iga qaytariladi.
- `scheduler.py`: ikkita `update_building_progress(-1)` `try/except` bloki
  qaytariladi (qator 394 va 414 atrofida).
- Hammasi mustaqil — bittasini revert qilish boshqalarga ta'sir qilmaydi.

---

## ✅ #5 — Stars to'lov auditi (YAKUNLANDI)

**Audit yo'nalishi:** Pul/Stars to'lovi — eng yuqori xavf darajasi (real pul
aylanadi). Faqat `handlers_text.py` ning `handle_successful_payment` funksiyasi
(819-900 qator) va `texts.py` ga tegildi. Boshqa fayllar **butunlay tegilmadi**
(qoida №02).

**Auditdan oldin topilgan 5 ta muammo:**

| # | Muammo | Xavf | Holat |
|---|--------|------|-------|
| 1 | Double-claim (duplicate event'lar) | 🔴 Kritik | ✅ Tuzatildi |
| 2 | Race condition (`load_user`/`save_user`) | 🔴 Kritik | ⏭️ O'tkazib yuborildi — butun loyiha bo'yicha muammo, alohida sessiyada |
| 3 | Exception silencing (xato → faqat log) | 🟡 O'rta | ✅ Tuzatildi |
| 4 | Noma'lum `item_id` (silent return) | 🟡 O'rta | ✅ Tuzatildi |
| 5 | Stars narx tekshiruvi | 🟢 Past (nazariy) | ⏭️ Real xavf yo'q — Telegram darajasida manipulation mumkin emas |

---

### Tuzatish 1 — Double-claim (idempotency):

**Sabab:** Telegram `successful_payment` event'ini at-least-once tarzda
yuboradi (webhook retry yoki network glitch paytida bir to'lov 2-3 marta
kelishi mumkin). Avval idempotency check yo'q edi — foydalanuvchi 5 Stars
to'lab, 2 marta mukofot olishi mumkin edi (real moliyaviy zarar).

**Yechim:** `msg.successful_payment.telegram_payment_charge_id` (Telegram'ning
unikal to'lov ID'si) olinadi. User document'ga yangi `stars_payments[]` field
qo'shilgan — har bir charge_id shu yerga saqlanadi. Yangi to'lov kelganda
ro'yxatda bormi tekshiriladi → bo'lsa rad etiladi (log + return).

**Kod joyi:** `handlers_text.py` 824-qator (`charge_id` olish), 828-834-qator
(duplicate check), 865-868-qator (charge_id ro'yxatga qo'shish).

**Backward compat:** Eski foydalanuvchilar uchun `u.get("stars_payments", [])`
default bo'sh ro'yxat — birinchi to'lovda muammosiz ishlaydi.

---

### Tuzatish 2 — Exception silencing:

**Sabab:** Avval `except Exception as e: print(...)` — agar `save_user`
MongoDB uzilishi tufayli xato bersa, foydalanuvchi pul to'lagan bo'ladi
lekin mukofot olmaydi va **hech qanday xabar olmaydi**. Faqat server logiga
yoziladi (admin Railway logini kuzatib turmasa — bilmay qoladi).

**Yechim:** `except` blok ichida 2 ta xabar yuboriladi:
1. **Foydalanuvchiga** — 3 tilli xato xabari + "💬 Admin bilan bog'lanish"
   tugmasi (`url=f"tg://user?id={ADMIN_ID}"` — username shart emas, ID yetadi).
2. **Adminga** — avtomatik bildirishnoma o'zbekcha (faqat siz o'qiysiz),
   `User ID` / `Charge ID` / `Payload` / `Xato` bilan — qo'lda mukofot
   yoki refund qilish uchun yetarli ma'lumot.

Ikkala `bot.send_message` ham ichki `try/except` ga o'ralgan — agar admin
xabari ham xato bersa (juda kam ehtimol), asosiy log baribir yozilgan
bo'ladi (debug uchun).

**Kod joyi:** `handlers_text.py` 871-900-qator (yangi `except` blok).

---

### Tuzatish 3 — Noma'lum `item_id`:

**Sabab:** Kelajakda yangi Stars mahsulot qo'shilsa (masalan
`SHOP_STARS_PRICES["premium"] = 50`) lekin `handle_successful_payment` da
handler yozilmasa — `else` bloki `print + return` qilardi (silent fail).
Foydalanuvchi pul to'lab, hech qanday xabar olmasdi.

**Yechim:** `raise ValueError(f"Noma'lum Stars item_id: {item_id}")` —
mavjud `except` blok ushlab, Tuzatish 2 dagi 2 ta xabarni yuboradi (DRY,
kod takrorlanmaydi). Admin xabarida `Xato: Noma'lum Stars item_id: premium`
ko'rinadi — sababini darhol tushunadi.

**Kod joyi:** `handlers_text.py` 860-863-qator.

**Idempotency bilan birga:** Agar `raise` bo'lsa, `charge_id`
`stars_payments[]` ga **qo'shilmaydi** — duplicate event kelsa yana xato
xabari yuboriladi. Bu **to'g'ri xulq-atvor** (mukofot berilmagan, foydalanuvchi
va admin qayta xabardor bo'lishi shart).

---

### Tarjima — 3 tilga to'liq (qoida №22):

`texts.py` ga 2 ta yangi kalit har 3 tilda qo'shildi (UZ/EN/RU):
- `stars_error_user_msg` — foydalanuvchiga xato matni
- `stars_error_btn_contact` — "Admin bilan bog'lanish" tugma matni

Joylashuv: `stars_desc_gift_box` qatoridan keyin (mantiqan birga turadi).

**Admin xabari tarjima qilinmagan** — faqat siz o'qiysiz, o'zbekcha yetarli
(qoida №04 — keraksiz "yaxshilik" qilmaymiz).

---

### Race condition (Muammo #2) — nima uchun o'tkazildi:

**Loyihada keng tarqalgan muammo** — `load_user`/`save_user` patterni har
joyda bor (`callbacks_shop.py`, `callbacks_checkin.py`, `flask_routes_*.py`).
Faqat `handlers_text.py` da tuzatish — qoida №09 ga zid (yarim yechim).

**Kelajak strategiya:**
- MongoDB atomic operatsiyalar (`$inc`, `$push`) — eng kuchli (multi-process safe)
- Yoki global per-user `threading.Lock` infrastrukturasi (`flask_routes_extra.py`
  shop da allaqachon bor ko'rinadi — README'da aytilgan, lekin biz bu sessiyada
  ko'rmadik)
- **Butun loyiha bo'ylab birga** hal qilinishi kerak

**Stars uchun real xavf past:** Stars to'lovi kamdan-kam (kuniga 1-5 marta),
bir vaqtda boshqa amal qilish ehtimoli juda past. Foydalanuvchi to'lovni
kutib turadi — boshqa joyda checkin qilmaydi.

---

### Stars narx tekshiruvi (Muammo #5) — nima uchun o'tkazildi:

Stars manipulation **Telegram darajasida mumkin emas**:
- Foydalanuvchi narxni o'zgartira olmaydi (Telegram UI orqali to'laydi)
- MITM mumkin emas (Telegram HTTPS)
- Faqat bot kodi xato bo'lsa muammo (bug yuborilsa) — bu boshqa audit

Hozirgi 4 ta tuzatish allaqachon real xavflarni hal qildi.

---

### Fayl o'zgarishlari xulosasi:

**`handlers_text.py`** (959 → 999 qator, +40 qator):
- 824: `charge_id` olish
- 828-834: idempotency check (duplicate rad etish)
- 860-863: `else` blokda `raise ValueError`
- 865-868: `charge_id` ni `stars_payments[]` ga qo'shish
- 871-900: yangi `except` blok (foydalanuvchi+admin xabar)

**`texts.py`** (502 → 508 qator, +6 qator):
- UZ blok: `stars_error_user_msg`, `stars_error_btn_contact`
- EN blok: `stars_error_user_msg`, `stars_error_btn_contact`
- RU blok: `stars_error_user_msg`, `stars_error_btn_contact`

**Boshqa fayllar:** TEGILMADI.

---

### Revert reja:

- `handlers_text.py` 824-qator (`charge_id` olish) → olib tashlash (zararsiz)
- `handlers_text.py` 828-834-qator (duplicate check) → olib tashlash
- `handlers_text.py` 860-863-qator → eski `print + return` ga qaytarish
- `handlers_text.py` 865-868-qator → olib tashlash
- `handlers_text.py` 871-900-qator → eski `except: print(...)` 2 qatoriga qaytarish
- `texts.py`: 3 ta blokdan 2 qatordan olib tashlash (UZ/EN/RU)
- Hammasi mustaqil — qisman revert ham mumkin (masalan, faqat idempotency'ni olib qolish, exception silencing'ni qaytarish).

---

### README yangilashlari:

- `texts.py` qatori (213): `stars_error_*` kalitlari qayd etildi
- `handlers_text.py` qatori (231): Stars to'lov to'liq yangi xulq-atvor tasvirlandi
- Flow xaritasi (358): idempotency + xato xabari yo'li qayd etildi

---

## ✅ #6 — Admin panel auditi (qisman YAKUNLANDI)

**Audit yo'nalishi:** Admin panel — yuqori xavf darajasi (avtorizatsiya, ball
berish, broadcast, ban/unban). Bu sessiyada faqat **`callbacks_admin.py`**
(438 qator) auditdan o'tdi. `handlers_text.py` admin qismi keyingi sessiyaga
qoldirildi (qoida №23 — kichik qismlarga bo'lish).

**Auditdan oldin topilgan muammolar:**

| # | Muammo | Xavf | Holat |
|---|--------|------|-------|
| A | Auth buzilishida log/`answer_callback_query` yo'q | 🟡 O'rta | ⏭️ O'tkazib yuborildi — 18+ joy, qoida №04 (keraksiz yaxshilik) |
| B | `admin_notify_confirm` sinxron broadcast loop — bot bloklanadi | 🔴 Yuqori | ✅ Tuzatildi |
| C | `bc_user_ack` da auth yo'q | 🟢 — | ✅ Muammo emas (foydalanuvchilar uchun mo'ljallangan) |

**Auth tekshiruvi:** `callbacks_admin.py` ning **barcha** admin amallarida
`if uid != ADMIN_ID: return True` mavjud. Silent reject — ma'lumot oqib
chiqmaydi. Slice indexlari (`admin_ch_edit_[14:]`, `admin_ch_del_[13:]`,
`admin_users_page_[17:]`, `admin_stats_[12:]`, `admin_reply_to_[15:]`) —
barchasi to'g'ri tekshirildi.

---

### Tuzatish 1 — Sinxron broadcast loop (Muammo B):

**Sabab:** `admin_notify_confirm` (qator 143-171) "Bot yangilandi" xabarini
**sinxron** loop bilan barcha foydalanuvchilarga yuborardi. 1000 foydalanuvchi
= 30+ soniya **butun bot bloklanadi** (callback'lar, checkin, scheduler —
hammasi kutadi). Telegram rate limit 30 msg/sec — 429 xatosi paytida
foydalanuvchiga xabar bermasdi.

**Yechim:** Loop **background thread**'ga ko'chirildi:
- Admin tugmani bosgan zahoti darhol "📤 Yuborilmoqda..." xabari ko'rsatiladi
- `_do_notify_broadcast()` ichki funksiyasi `threading.Thread(daemon=True)`
  da ishga tushiriladi
- Asosiy thread darhol qaytadi → bot bloklanmaydi
- Natija xabari va admin panel qaytishi thread ichida (loop tugagandan keyin)
- Qo'shimcha `try/except` thread ichida — yakuniy xabar yuborilmasa ham bot
  crash bo'lmaydi

**Kod joyi:** `callbacks_admin.py` 143-185-qator (avval 143-171).

**Fayl uzunligi:** 438 → 452 qator (+14 qator).

---

### Tarjima — KERAK EMAS (qoida №22 istisnosi):

Faqat 1 ta yangi matn qo'shildi: **"📤 Yuborilmoqda... (bir necha soniya
kutib turing)"** — bu **faqat adminga** ko'rinadi (`uid == ADMIN_ID`),
boshqa foydalanuvchilarga hech qachon ko'rsatilmaydi. Tarjima qilish keraksiz
(`stars_error_user_msg` tarjima qilindi, chunki u oddiy foydalanuvchiga
ko'rinadi — bu farq).

---

### Muammo A (auth log) — nima uchun o'tkazildi:

**Sabab:** Bu xavfsizlik buzilishi emas — silent reject allaqachon ishlaydi.
Faqat "yaxshi bo'lardi" turidagi yaxshilash bo'lardi (DoS/brute-force aniqlash
uchun log). 18+ joyni o'zgartirish kerak (`if uid != ADMIN_ID` har joyda),
qoida №04 (bir muammoni tuzatganda boshqa yaxshilik qilmaslik) va №18 (error
message va loglarni mantiq o'zgarishi bilan birga tegmaslik) — ikkisi ham
"hozir tegmang" deydi.

**Agar kelajakda DoS xavfi paydo bo'lsa:** har `if uid != ADMIN_ID:` ga 2
qator qo'shish kifoya: `print(f"[admin_auth] denied uid={uid} cdata={cdata}")`
va `bot.answer_callback_query(call.id)`.

---

### Fayl o'zgarishlari xulosasi:

**`callbacks_admin.py`** (438 → 452 qator, +14 qator):
- 143-185: `admin_notify_confirm` to'liq qayta yozildi (background thread)

**Boshqa fayllar:** TEGILMADI. README va `handlers_text.py` tegilmadi.

---

### Revert reja:

- `callbacks_admin.py` 143-185-qator → eski sinxron loop (143-171-qator)
  versiyasiga qaytarish. `_do_notify_broadcast` ichki funksiyani olib tashlab,
  loop'ni darhol asosiy if-blok ichiga ko'chirish. Bitta blok, mustaqil,
  boshqa joyga ta'siri yo'q.

---

### README — TEGILMADI:

Qoida №21'ga muvofiq, bu bir martalik bug fix — pattern emas. Hozir bitta
joyda background thread ishlatildi. Agar kelajakda 2+ joyda xuddi shu
tuzatish kerak bo'lsa (masalan `handlers_text.py` broadcast'da ham), o'shanda
README ga umumiy "broadcast loop background thread" qoidasi qo'shiladi.

---

## 🔵 KEYINGI SESSIYAGA QOLDIRILDI (#6 davomi)

### `handlers_text.py` admin qismi (eng katta keyingi audit)
- ~959 qator. Admin state machine: `admin_waiting_points_id` (ball berish),
  `admin_waiting_reply_*` (foydalanuvchiga javob), `admin_bc_*` (broadcast
  matn qabul qilish), `admin_waiting_channel_*` (kanal sozlash).
- **Xotira eslatmasi:** "points gifting race condition" va "self-grant
  overwrite bug" — eski auditlardan ma'lum muammolar. **Tuzatilganmi yoki yo'q
  — toza ko'z bilan tekshirish kerak.**
- **Diqqat:** `admin_bc_*` flow'da ham ehtimol sinxron broadcast loop bor —
  agar shunday bo'lsa, xuddi shu background thread patterni qo'llanadi.
  Qoida №09 — ta'sir doirasi, mavjud bo'lsa bir xil tuzatish.

### `menus.py` (167 qator — kichik, oson)
- `admin_menu()`, `admin_broadcast_menu()`, `admin_stats_period_menu()` —
  faqat tugma strukturasi. Auth bo'lmasligi mantiqiy (menyu o'zi xavfsiz).
- Tezda audit qilish mumkin.

### `flask_routes_*.py` admin endpoint'lar
- README'da admin route'lar bormi tekshirish kerak. Agar bo'lsa — auth
  tekshiruvi qilingani isbotlash.

---

## ⚪ MUHIM QAYDLAR (kelajak sessiyalar uchun) — #6 dan

### Background thread pattern qoidasi (tasdiqlanmagan)
- Hozircha 1 ta joyda (`admin_notify_confirm`) qo'llanildi.
- Agar `handlers_text.py` admin broadcast'da ham xuddi shu muammo topilsa va
  tuzatilsa — o'shanda README'ga umumiy qoida sifatida qo'shamiz.

### Admin auth pattern toza
- `callbacks_admin.py` ning barcha admin amallarida `if uid != ADMIN_ID:
  return True` mavjud. Bu **yaxshi pattern** — keyingi audit fayllarida
  ham xuddi shu standart kutilishi kerak.

---

## 📦 BU SESSIYADA O'ZGARGAN FAYLLAR (#6)
**Backend:**
- `callbacks_admin.py` — `admin_notify_confirm` background thread'ga ko'chirildi

**Hujjat:** `SESSION_LOG_audit.md` (README tegilmadi)

## ⚠️ DEPLOY ESLATMASI (#6)
- ✅ `callbacks_admin.py` GitHub'ga yuklanishi kerak.
- Yangi fayl YO'Q.
- README yangilanmagan — yuklash kerak emas.

---

## ✅ #7 — `handlers_text.py` + `callbacks_shop.py` auditi (YAKUNLANDI)

**Audit yo'nalishi:** Ball aylanishi (admin ball berish, transfer, jon sotib olish,
reset, subtract). Bot tomonidagi pul/ball oqimi — yuqori xavfli zona.

**Auditdan oldin topilgan muammolar:**

| # | Fayl | Muammo | Xavf | Holat |
|---|------|--------|------|-------|
| A | `handlers_text.py` | Self-grant overwrite bug (admin o'ziga ball berishi) | 🔴 Kritik | ✅ Allaqachon tuzatilgan (eski audit, qator 560-564) |
| B | `handlers_text.py` | Broadcast sinxron loop | 🔴 Yuqori | ✅ Allaqachon tuzatilgan (background thread, qator 802-807) |
| C | `handlers_text.py` | Admin ball berish race condition (qator 555-559) | 🟡 O'rta | ⏭️ Strategik (S1 ga ko'chirildi) |
| D | `callbacks_shop.py` | `bozor_reset_do` `add_points_history` chaqirmaydi (qator 198-203) | 🟡 O'rta | ✅ Tuzatildi |
| E | `callbacks_shop.py` | `bozor_subtract` foydalanuvchiga ball ayirish huquqi (faqat admin) | 🟡 O'rta | ✅ Tuzatildi (feature olib tashlandi) |
| F | `handlers_text.py` | Ball transfer race condition (qator 443-451) | 🔴 Yuqori | ⏭️ Strategik (S1 ga ko'chirildi) |
| G | `handlers_text.py` | Ball transfer atomic emas (rollback yo'q) | 🟡 O'rta | ⏭️ Strategik (S2 ga ko'chirildi) |
| H | `callbacks_shop.py` | `bot.get_me()` cache'siz | 🟢 Past | ⏭️ Strategik (S3 ga ko'chirildi) |

### 🆕 Yangi qoida №28 qo'shildi (README)

**Maqsad:** Audit jarayonida topilgan, lekin bir joyda tuzatib bo'lmaydigan
muammolarni unutmaslik. Foydalanuvchi istagi: "muammolar chiqadiku — butun bot
bo'ylab tarqalganlari — o'shalarni bir chekkadan tuzatishga doim tayyorman,
chunki hozir qilinmasa keyin u joyni ko'rishim ancha imkonsiz bo'lib qolishi yoki
u muammo haqiqatan paydo bo'lib unga duch kelsam eslashim mumkin".

**Algoritm:**
1. Strategik muammo topilsa → SESSION_LOG'ning "🎯 STRATEGIK MUAMMOLAR" bo'limiga
   darhol qayd (xavf, joylar, yechim variantlari)
2. Mustaqil tuzatilishi mumkin → darhol tuzatish
3. Infrastruktura kerak → keyingi sessiyaga, lekin to'liq tafsilot bilan

### 🆕 SESSION_LOG strukturasi qayta tartiblandi

Hammasi bitta faylda: STRATEGIK MUAMMOLAR (boshi) + AUDIT TARIXI (o'rtasi) +
KEYINGI SESSIYAGA (oxiri). Yangi sessiya boshlanganda Claude shu fayldan
boshlaydi.

---

### Tuzatish 1 (Muammo D) — `bozor_reset_do` `add_points_history` qo'shildi:

**Sabab:** `bozor_reset_do` `u["points"] = 0` qilardi, lekin `add_points_history`
chaqirmasdi. Natijada `points_history` da reset hodisasi yoq → kunlik/haftalik/oylik
rating notog'ri ko'rsatardi (user reset qilgandan keyin ham eski balli reytingda
ko'rinardi).

**Yechim:** `old_points = u.get("points", 0)` saqlanadi, `u["points"] = 0` dan
keyin `if old_points > 0: add_points_history(u, -old_points)` chaqiriladi.
Shartli — `old_points == 0` bo'lsa keraksiz log yozilmaydi (yangi user yoki
qayta reset edge-case).

**Kod joyi:** `callbacks_shop.py` qator 198-207 (avval 198-203, +4 qator).

**Pattern:** README qator 485 da yozilgan oddiy `+/-` pattern'ga mos. `max(0,...)`
kerak emas — reset to'liq 0 ga tushadi, manfiy delta `-old_points` aniq.

---

### Tuzatish 2 (Muammo E) — `bozor_subtract` feature olib tashlandi:

**Sabab:** "Ballarimdan olib tashlash" tugmasi orqali foydalanuvchi o'ziga
ball ayira olardi. Bu admin amal (manfiy ball berish — admin nazorat ostidagi
amal). Oddiy user uchun ma'nosiz feature — ball yo'qotish faqat foydalanuvchini
zarar ko'rdiradi (ehtimol tasodifiy bosish). To'liq reset esa `bozor_btn_reset`
orqali mavjud (atayin tasdiq dialog bilan).

**Yechim:** 5 joyda olib tashlash:
1. `callbacks_shop.py` qator 49 — asosiy menyudan tugma
2. `callbacks_shop.py` qator 59 — fallback menyudan tugma
3. `callbacks_shop.py` qator 157-179 — `bozor_edit` o'lik kod (23 qator) — hech
   qaerda chaqirilmaydigan handler edi, ichida faqat `bozor_subtract` va
   `bozor_reset_confirm` bor edi (oxirgisi asosiy menyuda ham mavjud)
4. `callbacks_shop.py` qator 224 — `bozor_reset_do` ichidagi qayta chiziladigan
   menyudan tugma
5. `callbacks_shop.py` qator 234-246 — `bozor_subtract` callback handler

**Soft-removal (eski cache xabarlar uchun):** `bozor_subtract` callback to'liq
olib tashlanmadi — `answer_callback_query` + `return True` saqlandi. Sabab:
Telegram'da eski menyu xabarlari cache'da qoladi — agar foydalanuvchi eski
xabardan tugma bossa, "callback xato" bo'lmaydi (silent ignore). 1 oydan keyin
to'liq olib tashlasa bo'ladi.

**handlers_text.py qator 469-497** — `bozor_waiting_subtract` state handler (29
qator) ham olib tashlandi (callback olib tashlanganidan keyin state hech qachon
o'rnatilmaydi → handler ham keraksiz). Eski user state'da qolib qolsa — boshqa
amal qilganda state default reset bo'ladi (xavfsiz).

---

### Tuzatish 3 — Tarjimalar (`texts.py`, qoida №22):

Olib tashlangan kalitlar (3 tilda jami **15 qator + bozor_title ichidagi 3 qator**):

| Kalit | UZ qator | EN qator | RU qator | Sabab |
|-------|----------|----------|----------|-------|
| `ok_self_deduct` | 113 | 279 | 445 | `bozor_waiting_subtract` muvaffaqiyat xabari |
| `bozor_btn_subtract` | 122 | 288 | 454 | Asosiy menyu tugma matni |
| `bozor_edit_title` | 135 | 301 | 467 | `bozor_edit` (o'lik) — title |
| `bozor_edit_sub_btn` | 136 | 302 | 468 | `bozor_edit` (o'lik) — tugma matni |
| `bozor_sub_ask` | 140 | 306 | 472 | `bozor_subtract` so'rov xabari |

`bozor_title` ichida `"➖ Ballarimdan olib tashlash —* ma'lum miqdorni ayirish"`
qatori ham 3 tilda olib tashlandi.

---

### Fayl o'zgarishlari xulosasi:

**`callbacks_shop.py`** (249 → 218 qator, -31 qator):
- 198-207: `bozor_reset_do` ga `old_points` saqlash + shartli `add_points_history`
- 49: asosiy menyudan `bozor_subtract` qatori olib tashlandi
- 59: fallback menyudan `bozor_subtract` qatori olib tashlandi
- 157-179: `bozor_edit` o'lik handler olib tashlandi (-23 qator)
- 224: `bozor_reset_do` ichidagi menyudan `bozor_subtract` olib tashlandi
- 234-246: `bozor_subtract` handler soft-removal'ga qisqartirildi (-13 qator → 5 qator)

**`handlers_text.py`** (999 → 972 qator, -27 qator):
- 469-497: `bozor_waiting_subtract` state handler olib tashlandi (izoh bilan
  almashtirildi, 29 → 3 qator)

**`texts.py`** (508 → 493 qator, -15 qator):
- UZ blok: 5 ta kalit + `bozor_title` ichidagi 1 qator
- EN blok: 5 ta kalit + `bozor_title` ichidagi 1 qator
- RU blok: 5 ta kalit + `bozor_title` ichidagi 1 qator

**Boshqa fayllar:** TEGILMADI.

---

### Revert reja:

**Muammo D revert:**
- `callbacks_shop.py` qator 198-207 dan `old_points = ...` va `if old_points >
  0: add_points_history(...)` qatorlari olib tashlanadi → eski 3 qatorli holat.

**Muammo E revert:**
- 5 joyda olib tashlangan kod qatorlari qaytariladi (asosiy menyu tugma, fallback
  tugma, `bozor_edit` handler, `bozor_reset_do` ichidagi tugma, `bozor_subtract`
  handler asl 13 qatorga qaytariladi).
- `handlers_text.py` 469-497 dagi 29 qatorli state handler qaytariladi.
- `texts.py` da 5 ta kalit har 3 tilda qaytariladi (15 qator) + `bozor_title`
  ichidagi qator har 3 tilda qaytariladi.

Hammasi mustaqil — qisman revert ham mumkin (faqat asosiy menyu tugmasini
qaytarish, qolganlarini emas; yoki faqat Muammo D ni revert qilish, E ni
saqlash).

---

### README yangilashlari:

- Qator 213: `texts.py` tasvirida `bozor_*` kalitlar soni `27 → 21`
- Qator 231: `handlers_text.py` tasvirida `bozor_waiting_subtract` audit #7 da
  olib tashlanganligi qayd etildi, qator soni `~959 → ~972`
- Qator 246: `callbacks_shop.py` qator soni `248 → 218`, "tahrirlash" so'zi
  olib tashlandi, reset `add_points_history` haqida eslatma qo'shildi
- Qator 485: `points` o'zgartirgan joylar ro'yxatida `callbacks_shop.py (jon)`
  → `(jon + reset)` ga o'zgartirildi

---

## 📦 BU SESSIYADA O'ZGARGAN FAYLLAR (#7)
**Backend:**
- `callbacks_shop.py` — Muammo D (reset → add_points_history) + Muammo E
  (`bozor_subtract`/`bozor_edit` olib tashlandi)
- `handlers_text.py` — `bozor_waiting_subtract` state handler olib tashlandi
- `texts.py` — 5 ta kalit har 3 tilda olib tashlandi + `bozor_title` ichidagi qator

**Hujjat:** `README.md` (4 ta qator yangilandi), `SESSION_LOG_audit.md` (audit #7
yakuniy holat)

## ⚠️ DEPLOY ESLATMASI (#7)
- ✅ Backend 3 fayli GitHub'ga yuklanishi kerak: `callbacks_shop.py`,
  `handlers_text.py`, `texts.py`
- ✅ README yangilangan versiyasi yuklanishi kerak
- Yangi fayl YO'Q — barchasi mavjud fayllarning yangilangan versiyasi

---

## 💬 KEYINGI CHATGA (#10 boshlash)

> Salom! Super Habits Bot — audit davom etmoqda.
>
> **Avval o'qing:**
> 1. `SESSION_LOG_audit.md` boshidagi "🎯 STRATEGIK MUAMMOLAR" bo'limi
>    (S1, S2, S3, **S4** — bu muammolarni qayta "kashf qilmang", ular allaqachon qayd etilgan)
> 2. `README.md` 28 ta qoida (ayniqsa #04, #09, #23, #28)
>
> **#9 da bajarilgan (YAKUNLANDI):**
> - `callbacks_checkin.py` (393 qator) va `flask_routes_data.py` `api_checkin` qismi auditdan o'tdi
> - **4 ta tuzatish** (audit #8 Muammo A pattern'ining loyiha bo'ylab tarqalishi):
>   - `callbacks_checkin.py` qator 89 (repeat fully undo) va 247 (simple undo)
>   - `flask_routes_data.py` qator 164 (repeat fully undo) va 224 (simple undo)
>   - Eski: `add_points_history(u, u["points"] - _old_pts, today)` (clamp tufayli noto'g'ri delta)
>   - Yangi: `add_points_history(u, -_undo_base, today)` (done branch `+_base` bilan symmetric)
> - Audit #9 davomida tekshirilgan, **bug yo'q** topilgan joylar:
>   - Repeat fully bekor qilish (bot/api bir xil — bitta bosish = 0 ga tushish)
>   - Repeat partial holatda pet_dog/streak/done_log tegmaslik (to'g'ri xulq)
>   - Repeat partial all_done celebration (shart to'g'ri)
> - Audit #9 strategikga ko'chirilganlar: hech narsa yo'q (S4 davom etadi)
>
> **#8 da bajarilgan (YAKUNLANDI):**
> - `points_logic.py` (72 qator) auditdan o'tdi — `apply_item_bonuses`, `apply_pet_dog_bonus`
> - `database.py:add_points_history` auditdan o'tdi — toza, mudofaa kodi yaxshi
> - Chaqiruvchilar tekshirildi: `flask_routes_data.py`, `callbacks_checkin.py`, `callbacks_checkin_done.py` — `apply_item_bonuses` natijasi 3 joyda ham `add_points_history` ga to'g'ri yetadi
> - **Muammo A tuzatildi:** `apply_pet_dog_bonus` undo branch — `add_points_history` ga doim `-bonus_value` yoziladi (clamp edge case'da done/undo symmetric saqlanadi)
> - **Muammo B tuzatildi:** `flask_routes_data.py` qator 333 milestone `add_points_history(u, ms["bonus"], today)` — izchillik uchun `today` argumenti qo'shildi
> - **🔴 S4 STRATEGIK qayd qilindi:** Bot tomonida streak milestone ball BERMAYDI (faqat xabar). WebApp dict + 5 milestone, bot tuple + 8 milestone. Foydalanuvchi bot kanali orqali milestone'ga yetsa bonus ball yo'qotadi.
>
> **Audit ustuvorligi (xavf bo'yicha):**
> - **🔴 S4 — Streak milestone bot/WebApp nomuvofiq** (eng yangi va kritik — adolatsizlik)
> - **🔴 S1 — Race condition** `load_user`/`save_user` (loyiha bo'ylab)
> - **`flask_routes_extra.py`** — shop API, friends, challenges (lock pattern bor, ball mantig'i, audit qilinmagan)
> - **`flask_routes_city.py`** — yangi feature, ko'p edge-case
> - **`flask_routes_core.py`** — habits CRUD, group checkin
> - **`menus.py`** (167 qator — tezda)
> - **Frontend** (audit qilinmagan: 13 ta fayl)
>
> README xaritaga qarab, qaysi fayllarni yuborishimni ayting.
> 28 qoidaga rioya qiling.


---

## ✅ #8 — `points_logic.py` + `add_points_history` chaqiruvchilari (YAKUNLANDI)

**Audit yo'nalishi:** Ball bonus mantiqi va `points_history` izchilligi.
`points_logic.py` (72 qator) + `database.py:add_points_history` + ularning
3 chaqiruvchisi (`flask_routes_data.py` WebApp, `callbacks_checkin.py`
toggle_, `callbacks_checkin_done.py` done_).

**Auditdan oldin topilgan muammolar:**

| # | Joy | Muammo | Xavf | Holat |
|---|-----|--------|------|-------|
| A | `points_logic.py` qator 58-60 | `apply_pet_dog_bonus` undo: clamp tufayli `add_points_history` ga noto'g'ri delta (edge case: reset orasida undo) | 🟡 O'rta | ✅ Tuzatildi |
| B | `flask_routes_data.py` qator 333 | Milestone `add_points_history` ga `today` argumenti yuborilmagan (boshqa joylar yuboradi — izchillik buzilgan) | 🟢 Past | ✅ Tuzatildi |
| C | 3 fayl (callbacks_checkin.py, callbacks_checkin_done.py, flask_routes_data.py) | Bot streak milestone ball bermaydi (faqat xabar), WebApp/bot `STREAK_MILESTONES` formati va qiymati nomuvofiq | 🔴 Kritik | ⏭️ Strategik (S4 ga ko'chirildi) |

---

### Tuzatish 1 (Muammo A) — `apply_pet_dog_bonus` undo branch:

**Sabab:** Joriy `add_points_history(u, u["points"] - _old_pts, today)` —
delta `u["points"]` ning aslida o'zgargan qiymatiga teng. Bu **`max(0, ...)`
clamp tufayli noto'g'ri** bo'lishi mumkin. Misol: foydalanuvchi reset qilgan
(`points=0`), keyin pet_dog undo qiladi → `_old_pts = 0`, `u["points"] = max(0, -5) = 0` →
delta `0 - 0 = 0` → history'ga `0` yoziladi. Lekin done branch `+bonus_value` yozgan
edi (bugun avval bonus berilgan). Net history: `+bonus_value` (yo'qolgan emas, lekin
asimmetrik — qaytarish history'da aks etmaydi).

**Yechim:** `add_points_history(u, -bonus_value, today)` — done branch
`+bonus_value` bilan **symmetric**. Real `points` clamp himoya alohida
saqlanadi (manfiy ball oldini olish), `points_history` esa audit yozuvi
sifatida to'liq saqlanadi.

**Kod joyi:** `points_logic.py` qator 60-63 (4 qator: 3 qator izoh + 1 qator
o'zgartirilgan `add_points_history` chaqirig'i).

**Test scenariy:**
- Normal: `points=100, bonus_value=5` → DONE: `points=105, history+5` → UNDO: `points=100, history-5` ✅ net 0
- Edge (reset orasida): DONE history+5 → reset history-105 → UNDO yangi kod history-5 → net `+5-105-5 = -105` (`points` clamp = 0 da to'xtaydi, history `-105` mantiqiy chunki barcha amallar to'liq audit qilingan)

---

### Tuzatish 2 (Muammo B) — `flask_routes_data.py` milestone `today` argumenti:

**Sabab:** Boshqa barcha `add_points_history` chaqiruvlari `add_points_history(u, delta, today)` ko'rinishida. Bu yerda `today`
argumenti yuborilmagan (`date_str=None` → ichkarida bugun hisoblanadi).
Funksional farq YO'Q, lekin izchillik buzilgan (qoida №09 — bir xil pattern).

**Yechim:** `add_points_history(u, ms["bonus"])` → `add_points_history(u, ms["bonus"], today)`. `today` qator 128 da scope ichida aniqlangan, mavjud.

**Kod joyi:** `flask_routes_data.py` qator 333.

---

### Muammo C (S4 — STRATEGIK) — nima uchun o'tkazildi:

**Sabab:** Bu **bir joyda tuzatib bo'lmaydi** — 3 fayl + `config.py` migration
+ `texts.py` da 8 milestone uchun matn tarjimasi (qoida №22) + S1 race
condition bilan ehtiyot. Maxsus sessiya kerak.

**Aniq tafovutlar (S4 da batafsil):**
- WebApp: `STREAK_MILESTONES` dict, 5 milestone, ball + duplicate guard
- Bot: `STREAK_MILESTONES` tuple, 8 milestone, faqat xabar, duplicate guard yo'q

**S4 yechim rejasi:** `config.py` ga yagona dict ko'chirish, 3 faylda sinxron
qilish, bot'ga ball berish va duplicate guard qo'shish, `texts.py` da
milestone matnlari tarjima.

---

### Tarjima — KERAK EMAS:

Bu auditda hech qanday yangi foydalanuvchiga ko'rinadigan matn qo'shilmadi
(faqat kod tuzatish + izoh). Qoida №22 ishga tushmaydi.

---

### Fayl o'zgarishlari xulosasi:

**`points_logic.py`** (72 → 75 qator, +3 qator):
- 60-63: `add_points_history` argumentini `u["points"] - _old_pts` dan
  `-bonus_value` ga o'zgartirish + 3 qatorlik izoh (sabab tushuntirish)

**`flask_routes_data.py`** (631 → 631 qator, +0 qator):
- 333: `add_points_history(u, ms["bonus"])` → `add_points_history(u, ms["bonus"], today)` (5 belgi qo'shildi)

**Boshqa fayllar:** TEGILMADI (`callbacks_checkin.py`,
`callbacks_checkin_done.py`, `database.py` — toza, hech qanday tuzatish kerak emas).

---

### Revert reja:

**Muammo A revert:** `points_logic.py` qator 60-63 (3 qator izoh + 1 qator
kod) → eski 1 qator: `add_points_history(u, u["points"] - _old_pts, today)`.

**Muammo B revert:** `flask_routes_data.py` qator 333 da `, today` ni olib
tashlash (5 belgi).

Hammasi mustaqil — qisman revert ham mumkin (faqat A yoki faqat B).

---

### README yangilashlari:

- **TEGILMADI** — bu audit hech qanday yangi pattern qo'shmadi, faqat
  mavjud `apply_pet_dog_bonus` ichida 1 qator o'zgartirildi va
  `flask_routes_data.py` qator 333 da izchillik uchun argument qo'shildi.
- S4 esa allaqachon `SESSION_LOG_audit.md` ga qayd etilgan (qoida №28).

---

## 📦 BU SESSIYADA O'ZGARGAN FAYLLAR (#8)
**Backend:**
- `points_logic.py` — Muammo A (apply_pet_dog_bonus undo branch sinxronligi)
- `flask_routes_data.py` — Muammo B (milestone today argument izchilligi)

**Hujjat:** `SESSION_LOG_audit.md` (S4 STRATEGIK qayd + audit #8 yakuniy holat)

## ⚠️ DEPLOY ESLATMASI (#8)
- ✅ Backend 2 fayli GitHub'ga yuklanishi kerak: `points_logic.py`, `flask_routes_data.py`
- ❌ README **YANGILANMAGAN** — yuklash kerak emas
- Yangi fayl YO'Q — barchasi mavjud fayllarning yangilangan versiyasi

---


## ✅ #9 — `callbacks_checkin.py` + `flask_routes_data.py` undo delta (YAKUNLANDI)

**Audit yo'nalishi:** Checkin yadrosi — `toggle_` (callbacks_checkin.py) vs `done_`
(callbacks_checkin_done.py) vs `api_checkin` (flask_routes_data.py) parallel
mantiq solishtirildi. Audit #8 Muammo A pattern'i — `add_points_history`
clamp delta — loyiha bo'ylab tarqalganligi tasdiqlandi va tuzatildi.

**Auditdan oldin topilgan muammolar:**

| # | Joy | Muammo | Xavf | Holat |
|---|-----|--------|------|-------|
| 1 | callbacks_checkin.py repeat fully undo (qator 86) | `add_points_history` clamp delta — done branch `+_base` bilan asimmetrik | 🟡 O'rta | ✅ Tuzatildi |
| 2 | callbacks_checkin.py simple undo (qator 244) | Xuddi shu pattern | 🟡 O'rta | ✅ Tuzatildi |
| 3 | flask_routes_data.py repeat fully undo (qator 161) | Xuddi shu pattern WebApp tomonida | 🟡 O'rta | ✅ Tuzatildi |
| 4 | flask_routes_data.py simple undo (qator 218) | Xuddi shu pattern WebApp tomonida | 🟡 O'rta | ✅ Tuzatildi |
| 5 | Streak milestone duplicate guard yo'q (bot tomon) | Undo→redo siklida milestone spam | 🔴 Kritik | ⏭️ S4 (allaqachon qayd qilingan) |
| 6 | Repeat fully bekor qilish (bot/api bir xil) | Bug yo'q | — | ✅ Tasdiqlandi toza |
| 7 | Repeat partial pet_dog/streak tegmasligi | To'g'ri xulq | — | ✅ Tasdiqlandi toza |
| 8 | Repeat partial all_done celebration | Shart to'g'ri | — | ✅ Tasdiqlandi toza |
| 9 | Import takrorlanishi (qator 53, done.py qator 28) | Kod tozaligi, bug emas | 🟢 Past | ⏭️ Qoida #04 (keraksiz yaxshilik qilmaslik) |

---

### Tuzatish 1-4 (Muammo 1-4) — `add_points_history` symmetric delta:

**Sabab:** `u["points"] = max(0, _old_pts - _undo_base)` clamp tufayli
`u["points"] - _old_pts` har doim `-_undo_base` ga teng emas.

Misol: `_old_pts = 3`, `_undo_base = 5` → `u["points"] = max(0, -2) = 0` →
eski delta `0 - 3 = -3` (lekin done branch `+5` yozgan). Asimmetrik — 2 ball
history'da "tutuq" qoladi.

Audit #8 da `apply_pet_dog_bonus` uchun aynan shu yechim tanlangan
(`points_logic.py` qator 60-63: `add_points_history(u, -bonus_value, today)`).
Audit #9 esa shu pattern'ning **butun loyihada tarqalishi** ekanligini aniqladi
va 4 joyda parallel tuzatdi.

**Yechim:** `add_points_history(u, u["points"] - _old_pts, today)` →
`add_points_history(u, -_undo_base, today)` — done branch `+_base` bilan
symmetric.

**Kod joylari (yakuniy qatorlar, 3 qator izoh qo'shilgandan keyin):**
- `callbacks_checkin.py` qator 89 (repeat fully undo, `if fully_done:` ichida)
- `callbacks_checkin.py` qator 247 (simple undo, `if h.get("last_done") == today:` ichida)
- `flask_routes_data.py` qator 164 (repeat fully undo, `if done >= rep_count:` ichida)
- `flask_routes_data.py` qator 224 (simple undo, `if h.get("last_done") == today:` ichida)

**Test scenariy:**
- **Normal:** `points=100, base=5` → done `+5`, undo `-5` → net 0 ✅
- **Clamp edge:** `points=3, base=5` → undo: eski `-3` (2 ball yo'qoladi), yangi `-5` ✅ (audit yozuvi to'liq)
- **Reset orasida:** done `+5` → reset `-105` → undo: eski `0` (asimmetrik), yangi `-5` ✅ (symmetric)
- **Bonus 2x:** `points=100, base=10` → undo `-10` ✅ (ikkala kodda bir xil — bonus bekor bo'lmagan holat)

**Diqqat:** `points` (real ball) **hech qachon manfiy bo'lmaydi** — clamp
saqlanib qoladi. `points_history` esa **to'liq audit yozuvi** sifatida
saqlanadi (rating va statistika to'g'ri ishlaydi).

---

### Muammo 5 (Streak milestone duplicate guard) — S4 ga ulandi:

`callbacks_checkin.py` qator 29-37 — `_check_streak_milestone` funksiya:
- ❌ Ball BERMAYDI (S4 qayd qilingan)
- ❌ Duplicate guard yo'q — undo→redo siklida spam mumkin
- WebApp `streak_milestones_sent[]` — bot tomonida yo'q

**Senariy:** Streak 7 ga yetdi → milestone xabari yuborildi. Undo qildi →
`streak_last_date = ""`, `u["streak"] = 6`. Yana tasdiqladi → `u["streak"] = 7`
→ **milestone xabari YANA yuboriladi**.

S4 da bu allaqachon qayd qilingan (qator 124-148, `STREAK_MILESTONES` dict vs tuple
nomuvofiqligi). Hozir tegmaymiz — S4 alohida sessiyada hal qilinadi.

---

### Muammo 9 (Import takrorlanishi) — qoldirildi:

`callbacks_checkin.py` qator 10 da `from datetime import datetime, timedelta, timezone`
modul boshida bor. Qator 53 da `from datetime import timezone, timedelta` —
funksiya ichida yana takrorlanadi. Xuddi shu `callbacks_checkin_done.py` qator 28 da ham.

Bu **bug emas** (Python ruxsat beradi), faqat keraksiz takror. Qoida #04 —
keraksiz "yaxshilik" qilmaymiz, audit doirasidan tashqari. Kelajak sessiyada
kod tozaligi bo'limida hal qilish mumkin.

---

### Tarjima (qoida №22) — KERAK EMAS:

Foydalanuvchiga ko'rinadigan matn yo'q (faqat kod tuzatish + 3 qator izoh
har bir joyda). Qoida №22 ishga tushmaydi.

---

### Fayl o'zgarishlari xulosasi:

**`callbacks_checkin.py`** (393 → 399 qator, +6 qator):
- Qator 86-89: 3 qator izoh + 1 qator o'zgartirilgan `add_points_history` (repeat fully undo)
- Qator 244-247: 3 qator izoh + 1 qator o'zgartirilgan `add_points_history` (simple undo)

**`flask_routes_data.py`** (630 → 636 qator, +6 qator):
- Qator 161-164: 3 qator izoh + 1 qator o'zgartirilgan `add_points_history` (repeat fully undo)
- Qator 218-221: 3 qator izoh + 1 qator o'zgartirilgan `add_points_history` (simple undo)

**Boshqa fayllar:** TEGILMADI (`callbacks_checkin_done.py` da undo branch yo'q —
done_ bildirishnomadan faqat tasdiq qiladi, undo qilmaydi).

---

### Revert reja:

Har 4 joyda quyidagini qaytarish kifoya:
- 3 qator izoh olib tashlanadi: `# Audit #9: ... # points_logic.py).`
- 1 qator almashtiriladi: `add_points_history(u, -_undo_base, today)` →
  `add_points_history(u, u["points"] - _old_pts, today)`

Har 4 joy **mustaqil** — qisman revert ham mumkin (masalan, faqat
`callbacks_checkin.py` ni revert, `flask_routes_data.py` ni qoldirish; yoki
faqat repeat undo'larni revert, simple undo'larni qoldirish).

---

### README yangilashlari:

- **TEGILMADI** — bu audit hech qanday yangi pattern qo'shmadi, faqat audit
  #8 Muammo A pattern'ining loyiha bo'ylab tarqalishi tuzatildi
  (`add_points_history` ga symmetric delta). README'da `add_points_history`
  haqida umumiy qoida allaqachon mavjud (qator 485 atrofida).

---

## 📦 BU SESSIYADA O'ZGARGAN FAYLLAR (#9)
**Backend:**
- `callbacks_checkin.py` — 2 ta tuzatish (repeat fully undo + simple undo `add_points_history` delta)
- `flask_routes_data.py` — 2 ta tuzatish (repeat fully undo + simple undo `add_points_history` delta)

**Hujjat:** `SESSION_LOG_audit.md` (audit #9 yakuniy holat + #10 boshlash eslatmasi)

## ⚠️ DEPLOY ESLATMASI (#9)
- ✅ Backend 2 fayli GitHub'ga yuklanishi kerak: `callbacks_checkin.py`, `flask_routes_data.py`
- ❌ README **YANGILANMAGAN** — yuklash kerak emas
- ❌ Frontend cache-busting kerak emas (faqat backend o'zgardi)
- Yangi fayl YO'Q — barchasi mavjud fayllarning yangilangan versiyasi

---

## ✅ #10 — `flask_routes_extra.py` Stars manipulyatsiya himoyasi (YAKUNLANDI)

**Audit yo'nalishi:** Shop API, friends, challenges, webhook (~870 qator).
Pul/ball mantig'i, lock pattern tekshiruvi, va Audit #5 (Stars to'lov) +
Audit #7 (callbacks_shop) davomi sifatida WebApp shop tarafini auditdan
o'tkazish.

**Auditdan oldin topilgan muammolar:**

| # | Joy | Muammo | Xavf | Holat |
|---|-----|--------|------|-------|
| 1 | `api_shop_buy` qator 187-285 | `pay_type="stars"` validation yo'q — manipulyatsiya: `{item_id: "badge_secret", type: "stars"}` → ball ushlanmaydi, badge bepul olinadi (600 ball moliyaviy xavf) | 🔴 Kritik | ✅ Tuzatildi |
| 2 | `api_shop_buy` qator 273-274 | `gift_box` faqat erta return bilan himoyalangan — kelajakda yangi Stars mahsulot qo'shilsa avtomatik himoya yo'q | 🟡 O'rta | ✅ Tuzatildi (#1 bilan birga) |
| 3 | `api_challenges_send` qator 602-603 | Garovni faqat tekshiradi, ushlamaydi — yuboruvchi `accept` gacha ball sarflasa challenge bekor bo'ladi (UX muammo, **dizayn qarori**) | 🟡 O'rta | ⏭️ Foydalanuvchi qaroriga ko'ra qoldirildi (B variant tanlandi) |
| 4 | `api_challenges_accept` qator 660-665 | Atomic emas — ikki `save_user` orasida MongoDB xato bersa ball yo'qoladi yoki history ↔ points sinxronligi buziladi | 🔴 Kritik | ⏭️ **S2** (allaqachon strategik) |
| 5 | `api_friends_add` qator 510-519 | Race condition — `fid` ayni vaqtda checkin qilsa friends ro'yxat eski versiyasi yoziladi → checkin yo'qoladi | 🟡 O'rta | ⏭️ **S1** (allaqachon strategik) |
| 6 | `api_friends_add` qator 506-509, 516 | Asimmetrik fail — B ning ro'yxati to'la bo'lsa, A da bor B da yo'q (silent fail). Frontendga xato yuborilmaydi | 🟢 Past | ⏭️ Qoida #04 (keraksiz "yaxshilik" qilmaslik) |
| 7 | `api_challenges_send` qator 605-611 | Race condition `existing` topish va `insert_one` orasida — Mongo unique index kerak | 🟢 Past | ⏭️ Strategik (alohida sessiya) |
| 8 | `api_friends_search` qator 479-496 | `load_all_users()` linear scan har qidiruvda — ko'p user bo'lsa sekin (60s cache yumshatadi). MongoDB text index kerak | 🟢 Past | ⏭️ Strategik (kelajak optimizatsiya) |
| 9 | `_shop_user_locks` dict | Hech qachon tozalanmaydi — millionlab user bo'lsa kichik memory leak | 🟢 Past | ⏭️ Real xavf juda past, kelajak ish |
| 10 | `api_shop_sell` umumiy | Tekshirildi — `SHOP_SELL_PRICES.get(item_id)` None bo'lsa rad etiladi, `gift_box` va `jon_restore` qasddan ro'yxatda yo'q | — | ✅ Tasdiqlandi toza |
| 11 | `api_shop_stars_invoice` qator 287-327 | One-time check va `bot.send_invoice` orasida race condition — lekin `handlers_text.handle_successful_payment` da Audit #5 idempotency (`charge_id` tekshiruvi) himoyalaydi | — | ✅ Tasdiqlandi toza (Audit #5 himoyalaydi) |
| 12 | `_get_shop_lock` qator 30-37 | Per-user lazy lock pattern + 3s timeout — to'g'ri implement qilingan | — | ✅ Tasdiqlandi toza |

---

### Tuzatish 1 (Muammo 1+2) — Stars mahsulotlari uchun `api_shop_buy` rad etish:

**Sabab:** Joriy kod `pay_type` argumentini tekshirmaydi. Foydalanuvchi
`{item_id: "badge_secret", type: "stars"}` yuborsa, `pay_type=="ball"`
branch o'tkazib yuboriladi (qator 275), ball ushlanmaydi, va to'g'ridan-to'g'ri
`inventory[item_id] += 1` ishlaydi (qator 280-282) → **600 ballik badge
bepul olinadi**. Faqat `gift_box` uchun erta return mavjud edi (qator 273),
lekin kelajakda yangi Stars mahsulot qo'shilsa (`SHOP_STARS_PRICES["premium"]=50`)
avtomatik himoya yo'q edi.

**Hujum scenariy:**
```javascript
fetch('/api/shop/<uid>/buy', {
  method: 'POST',
  body: JSON.stringify({ item_id: 'badge_secret', type: 'stars' })
});
// Eski: bepul olinadi (kritik bug)
// Yangi: 400 "Bu mahsulot faqat Telegram Stars bilan sotib olinadi"
```

**Yechim — Variant B (qattiqroq, kelajakka ham xavfsiz):**
`pay_type` argumentini umuman ishonmaymiz. `item_id` `SHOP_STARS_PRICES`
da bo'lsa (`gift_box` dan tashqari) — endpoint boshida darhol rad etamiz.
`gift_box` uchun qator 280 dagi mavjud erta return saqlanadi (ikki bosqichli
mudofaa).

**Kod joyi:** `flask_routes_extra.py` qator 196-202 (+7 qator: 5 izoh + 2 kod):
```python
# Audit #10: Stars mahsulotlari bu endpoint orqali sotib olinmaydi.
# Frontend pay_type="stars" manipulyatsiyasidan qat'i nazar — Stars
# narxi mavjud mahsulotlar faqat /stars_invoice → Telegram to'lov
# orqali olinadi (handlers_text.handle_successful_payment idempotent).
# gift_box uchun pastdagi `if item_id == "gift_box"` erta return alohida ushlaydi.
if item_id in SHOP_STARS_PRICES and item_id != "gift_box":
    return jsonify({"ok": False, "error": T(uid, "stars_only_item")})
```

**Test scenariy:**
- Normal ball xarid: `{item_id: "shield_1"}` → 100 ball yechiladi ✅
- `gift_box` ball urinishi: `{item_id: "gift_box"}` → qator 280 da "gift_box faqat Telegram Stars bilan" (eski xulq saqlanadi) ✅
- **Manipulyatsiya hujumi:** `{item_id: "badge_secret", type: "stars"}` → 400 "Bu mahsulot faqat Telegram Stars bilan sotib olinadi" (himoya ishlaydi) ✅
- Frontend xato (Stars mahsulot uchun `shop_buy` chaqirilgan): `{item_id: "gift_box", type: "stars"}` → qator 280 ushlaydi ✅
- Kelajak Stars mahsulot: `SHOP_STARS_PRICES["premium"]=50` qo'shilsa → avtomatik rad etiladi (`item_id in SHOP_STARS_PRICES` check) ✅

**Ta'sir doirasi (qoida №09) tekshiruvi:**
- Bot tomonida shop buy mantig'i YO'Q (faqat WebApp API) — parallel handler kerak emas
- `callbacks_shop.py` faqat jon/referral/transfer/reset bilan ishlaydi — Stars mahsulotlariga tegmaydi
- `handlers_text.py` Stars to'lovi (`successful_payment`) — alohida oqim, bu tuzatishga bog'liq emas

---

### Tarjima (qoida №22) — 3 tilga to'liq:

`texts.py` ga yangi kalit `stars_only_item` har 3 tilda qo'shildi:
- **UZ** (qator 141): `"Bu mahsulot faqat Telegram Stars bilan sotib olinadi"`
- **EN** (qator 303): `"This item can only be purchased with Telegram Stars"`
- **RU** (qator 465): `"Этот товар можно купить только за Telegram Stars"`

Joylashuv: har 3 tilda `stars_error_btn_contact` dan keyin (mantiqan Stars
matnlari yonida). `flask_routes_extra.py` da `T(uid, "stars_only_item")`
chaqiriladi (`T` allaqachon helpers'dan import qilingan — qoida №12).

---

### Muammo 3 (Challenge garov ushlanmasligi) — qoldirildi:

Yuboruvchi pending challenge yuborgach `accept` gacha ball'ni sarflashi
mumkin (garov ushlanmagan). Agar accept paytida `u_send.get("points") < bet`
bo'lsa → challenge bekor qilinadi (qator 658-659).

Bu **dizayn qarori** — pending challenge ball'ni "muzlatishi" yoki yo'qmi?
Hozircha qoldirildi (foydalanuvchi B variantni tanladi — sessiyani yakunlash).
Kelajak sessiyada qayta ko'rib chiqilishi mumkin.

---

### Muammo 4 (Challenge accept atomic emas) — S2 ga ulandi:

`api_challenges_accept` qator 660-665 — ikki `save_user` orasida MongoDB
xato bersa ball yo'qoladi. Bu **S2 strategik muammo** (`SESSION_LOG_audit.md`
qator 83-101 — "Ball transfer atomic emas") bilan bir xil pattern. S2 ga
qo'shimcha joy qayd qilindi (`api_challenges_accept` shu yerga ham tegishli).

**Diqqat:** `add_points_history(-bet)` ikkala foydalanuvchiga ham `save_user`
dan **oldin** chaqiriladi. Agar 2-`save_user` xato bersa, history'da -50
yozuv qoladi lekin real points kamaymaydi → history ↔ points sinxronligi
buziladi. S2 yechimi bu yerda ham qo'llaniladi.

---

### Muammo 5 (Friends add race condition) — S1 ga ulandi:

`api_friends_add` qator 510-519 — `load_user(fid)` → modify → `save_user(fid, f)`
orasida `fid` user ayni vaqtda checkin qilsa, friends ro'yxat eski versiyasi
yoziladi → checkin yo'qoladi. Bu **S1 strategik muammo** bilan bir xil
pattern, S1 jadvaliga `flask_routes_extra.py` qo'shimcha satr sifatida
qayd qilindi.

---

### Fayl o'zgarishlari xulosasi:

**`flask_routes_extra.py`** (887 → 894 qator, +7 qator):
- Qator 196-202: 5 qatorlik izoh + 2 qator kod (Stars mahsulotlari rad etish)

**`texts.py`** (493 → 496 qator, +3 qator):
- Qator 141: UZ — `"stars_only_item"`
- Qator 303: EN — `"stars_only_item"`
- Qator 465: RU — `"stars_only_item"`

**Boshqa fayllar:** TEGILMADI (`config.py`, `database.py`, `points_logic.py`
— audit doirasida tekshirildi, hech qanday tuzatish kerak emas; `callbacks_shop.py`,
`handlers_text.py` — Audit #5 va #7 da allaqachon auditdan o'tgan).

---

### Revert reja:

**Tuzatish 1 revert:** `flask_routes_extra.py` qator 196-202 — 7 qatorni
(5 izoh + 2 kod) olib tashlash. Eski xulq qaytadi.

**Tarjima revert:** `texts.py` har 3 tilda `stars_only_item` qatorini
olib tashlash (3 ta qator, har til uchun 1 ta).

Ikkalasi mustaqil — qisman revert ham mumkin (faqat kod yoki faqat tarjima).
Lekin tavsiya etilmaydi: kod revert qilinsa tarjima ishlatilmaydi (kelajakda
kerak bo'lishi mumkin).

---

### README yangilashlari:

- **TEGILMADI** — bu audit yangi pattern qo'shmadi, faqat mavjud mantiqning
  zaifligini yopdi. Stars mahsulotlari `stars_invoice` orqali sotib olinadigan
  pattern allaqachon ishlayotgan edi — endi faqat **mantiqiy chiqib ketishni**
  ham to'sib qo'ydik. README'ga texnik detal yozish keraksiz.
- S1 va S2 strategik muammolarning **tarqalish jadvali** auditda eslatildi
  (alohida sessiyada hal qilinganda kerak bo'ladi).

---

## 📦 BU SESSIYADA O'ZGARGAN FAYLLAR (#10)
**Backend:**
- `flask_routes_extra.py` — 1 ta tuzatish (Stars manipulyatsiya himoyasi)
- `texts.py` — 1 ta yangi kalit `stars_only_item` × 3 tilda

**Hujjat:** `SESSION_LOG_audit.md` (audit #10 yakuniy holat + #11 boshlash eslatmasi)

## ⚠️ DEPLOY ESLATMASI (#10)
- ✅ Backend 2 fayli GitHub'ga yuklanishi kerak: `flask_routes_extra.py`, `texts.py`
- ❌ README **YANGILANMAGAN** — yuklash kerak emas
- ❌ Frontend cache-busting kerak emas (faqat backend o'zgardi)
- Yangi fayl YO'Q — barchasi mavjud fayllarning yangilangan versiyasi

---

## 💬 KEYINGI CHATGA (#12 boshlash)

> Salom! Super Habits Bot — audit davom etmoqda.
>
> **Avval o'qing:**
> 1. `SESSION_LOG_audit.md` boshidagi "🎯 STRATEGIK MUAMMOLAR" bo'limi
>    (S1, S2, S3, **S4** — bu muammolarni qayta "kashf qilmang", ular allaqachon qayd etilgan)
> 2. `README.md` 28 ta qoida (ayniqsa #04, #09, #23, #28)
>
> **#11 da bajarilgan (YAKUNLANDI):** `flask_routes_city.py` auditi
> - **`change_type` o'lik kod zanjiri o'chirildi** — endpoint (`flask_routes_city.py`) + `change_building_type` funksiya (`city_logic.py`) + 2 keraksiz import. Frontend ishlatmasdi (grep tasdiqladi), modal rad etilgan. City endpoint 7 → 6.
> - **`move_item` xato aniqligi (Variant A)** — endi `None`=topilmadi / `False`=band / `True`=ko'chdi. Route `not_found` (404) va `occupied` (400) ni ajratadi. Avval ikkalasi ham noto'g'ri "joy band" derdi.
> - **`_CITY_ERR` f-string** — O'TKAZIB YUBORILDI (real xavf yo'q, import allaqachon majburiy).
> - **Bug yo'q tasdiqlandi:** `buy_decoration`/`buy_insurance` atomik ball yechish, koord validatsiya, `rename` tozalash, GET migration zanjiri, `_get_city_lock` race himoya.
> - Tegilgan fayllar: `flask_routes_city.py`, `city_logic.py`. README 4 joyda tozalandi.
>
> **Audit ustuvorligi (xavf bo'yicha):**
> - **🔴 S4 — Streak milestone bot/WebApp nomuvofiq** (eng kritik — adolatsizlik; `config.py` migration + 3 fayl sinxron + `texts.py` tarjima)
> - **🔴 S1 — Race condition** `load_user`/`save_user` (loyiha bo'ylab, `db_lock.py` strategik)
> - **🔴 S2 — Ball transfer atomic emas** (S1 bilan birga)
> - **`flask_routes_core.py`** (~760 qator) — habits CRUD, group checkin, profile PUT (eng yirik audit qilinmagan)
> - **`menus.py`** (167 qator — tezda)
> - **Frontend** (audit qilinmagan: 13 ta fayl)
>
> README xaritaga qarab, qaysi fayllarni yuborishimni ayting.
> 28 qoidaga rioya qiling.


---

## ✅ REFACTOR R1 — Xato holati UI markazlashtirish (YAKUNLANDI)

**Tur:** Audit emas, UI refactor (Qoida #17 markazlashtirish).
**Sabab:** Foydalanuvchi rasm yubordi — shahar sahifasida internet uzilganda chiroyli "Serverga ulanib bo'lmadi" + 📡 + ↻ tugma ko'rinishi bor edi. Boshqa sahifalarda esa har xil rangli ⚠️ uchburchak SVG + `data_error` matni edi (izchil emas). Maqsad: barcha sahifalarni bir xil etalonga keltirish.

### Etalon
Shahar sahifasi `renderCityError(container)` → `.city-error*` CSS bilan: 📡 ikonka (40px, opacity 0.7) + "Serverga ulanib bo'lmadi" matni + neumorphik 48×48 ↻ tugma (`var(--sh-out)` → bosilganda `var(--sh-in)`, `scale(0.94)`).

### Topilgan tarqalish
9 ta sahifa loaderida turli xil xato holati (har biri har xil rangda SVG uchburchak, ↻ tugma yo'q):

| Fayl | Loader | Container | Eski rang |
|------|--------|-----------|-----------|
| `app-pages.js` | `loadToday` | `today-content` | Sariq SVG + `data_error` + xato matni + "Qayta urinish" tugma |
| `app-pages.js` | `loadReminders` | `reminders-content` | Sariq SVG + `data_error` (tugma yo'q) |
| `app-pages.js` | `loadAchievements` | `achievements-content` | Sariq SVG + `data_error` (tugma yo'q) |
| `app-stats.js` | `loadStatsPage` | `stats-detail-content` | Yashil SVG + `data_error` + xato matni |
| `app-stats.js` | `loadRating` | `rating-content` | Qizil SVG + `data_error` |
| `app-social.js` | `loadGroups` | `groups-content` | Qizil SVG + `data_error` |
| `app-social.js` | `loadFriends` | `friends-content` | Qizil SVG + `data_error` |
| `app-social.js` | `loadShop` | `bozor-content` | Qizil SVG + `data_error` |
| `app-profile.js` | `loadProfile` | `profile-content` | Sariq SVG + `data_error` |
| `app-city.js` | `loadCity` | `city-content` | ✅ Etalon (📡 + matn + ↻) |

### Yechim — 6 qadam (Qoida #23 kichik qadamlar)

**1-qadam: Helper + CSS poydevor.**
- `app-core.js` ga `renderErrorState(containerId, retryFn)` qo'shildi — `apiFetch` dan keyin. `window[fnName]` orqali `retryFn` global saqlanadi (`innerHTML` ichidagi `onclick` faqat global nomlarni ko'radi).
- `style.css` ga `.empty-state-error*` CSS qo'shildi (`.empty-state` dan keyin) — etalon CSS aynan nusxalandi.

**2-qadam: Shahar etaloni ham markazlashtirildi.**
- `app-city.js`: `renderCityError(container)` endi `renderErrorState(container.id, () => loadCity())` ni chaqiradi. 9 qator HTML → 4 qator.
- `style-city.css`: `.city-error*` CSS olib tashlandi (21 qator). Joyiga audit izohi qoldirildi. 229-qatordagi izoh `.city-error-btn` → `.empty-state-error-btn` ga yangilandi.

**3-qadam: `app-pages.js`** — 3 ta loader: `loadToday`, `loadReminders`, `loadAchievements`. `loadToday` `retryFn` da `loaded.today = false; loadToday()` mantig'i saqlandi (eski cache-reset xulqi).

**4-qadam: `app-stats.js`** — 2 ta loader: `loadStatsPage`, `loadRating`. `_ratSort`/`_ratPeriod` filtrlar saqlandi (xato holatida o'zgarmaydi).

**5-qadam: `app-social.js`** — 3 ta loader: `loadGroups`, `loadFriends`, `loadShop`. `_shopContentId` o'zgaruvchisi — eski xulqdek `'bozor-content'` hardcoded saqlandi (Qoida #04 — boshqa "yaxshilik" qilmaslik).

**6-qadam: `app-profile.js`** — 1 ta loader: `loadProfile`.

### Tarjima (Qoida #22)
`S('msg','connection_error')` — `strings.js` da uz/ru/en 3 tilda allaqachon mavjud edi ("Serverga ulanib bo'lmadi" / "Не удалось подключиться" / "Connection failed"). Yangi kalit qo'shilmadi.

### Fayl o'zgarishlari xulosasi
- `app-core.js` — yangi `renderErrorState` helper (608 → 664 qator)
- `style.css` — yangi `.empty-state-error*` bloki (3248 → 3273 qator)
- `style-city.css` — `.city-error*` olib tashlandi (745 → 726 qator)
- `app-city.js` — `renderCityError` qisqartirildi (helper'ga ko'chirildi)
- `app-pages.js` — 3 ta `catch(e)` bloki markazlashtirildi
- `app-stats.js` — 2 ta `catch(e)` bloki markazlashtirildi
- `app-social.js` — 3 ta `catch(e)` bloki markazlashtirildi
- `app-profile.js` — 1 ta `catch(e)` bloki markazlashtirildi
- `index.html` — cache-bust ×6: `style.css?v=615→616`, `style-city.css?v=26→27`, `app-core.js?v=568→569`, `app-pages.js?v=569→570`, `app-stats.js?v=557→558`, `app-social.js?v=557→558`, `app-profile.js?v=553→554`, `app-city.js?v=34→35`

**Jami: 9 ta fayl o'zgartirildi. ~80 qator takroriy HTML olib tashlandi, 1 markaziy helper qo'shildi.**

### Test scenario (Qoida #15)
Foydalanuvchi internetsiz **istalgan sahifaga** kiradi (Bugun, Eslatma, Yutuq, Statistika, Reyting, Guruh, Do'st, Bozor, Profil, Shahar) → bir xil chiroyli **📡 + "Serverga ulanib bo'lmadi" + neumorphik ↻ tugma** ko'rinadi. ↻ bossa → mos loader funksiyasi qayta chaqiriladi.

### Revert reja (Qoida #16)
- `app-core.js` dan `renderErrorState` (475-498 qator) olib tashlash
- `style.css` dan `.empty-state-error*` bloki olib tashlash
- Boshqa 6 ta JS faylda `catch(e)` bloklarini eski versiyaga qaytarish (har birida 1-3 ta SVG bilan `innerHTML`)
- `style-city.css` ga `.city-error*` qaytarish
- `index.html` cache-bust raqamlarini -1 qaytarish

### Strategik muammoga TA'SIR YO'Q
Bu refactor S1-S4 (race condition, atomic operations, get_me cache, milestone) ga aloqasiz — sof UI o'zgarishi. Backend tegmadi.

### Keyingi audit uchun eslatmalar (o'lik kod)
Qoida #04 sababli hozir tegmadim, lekin kelajak audit uchun:
1. **`strings.js` `data_error` kaliti** — 3 tilda mavjud (409, 830, 1251 qatorlar), hech qayerda ishlatilmaydi.
2. **`strings.js` `today.retry` kaliti** — 3 tilda mavjud (110, 530, 951), hech qayerda ishlatilmaydi.
3. **`app-core.js` `loadMyReminders`** — `loadTab('my_reminders')` chaqiriladi (434-qator), lekin funksiya hech qayerda aniqlanmagan va `page-my-reminders` HTML konteyneri yo'q. O'lik kod.

### README yangilashlari
- Markaziy helperlar bo'limiga `renderErrorState` haqida yangi qator qo'shildi.
- `app-core.js` fayl ro'yxati va jadval qatori yangilandi (~608 → ~664 qator, `renderErrorState` qo'shildi).
- `style.css` jadval qatori yangilandi (`.empty-state-error*` qo'shildi).
- `style-city.css` jadval qatori yangilandi (`.city-error*` olib tashlandi, izoh qo'shildi).

## 📦 BU SESSIYADA O'ZGARGAN FAYLLAR (R1)
**Frontend (8 fayl):**
- `app-core.js` — `renderErrorState` helper qo'shildi
- `style.css` — `.empty-state-error*` bloki qo'shildi
- `app-city.js` — `renderCityError` helper'ga ko'chirildi
- `style-city.css` — `.city-error*` olib tashlandi
- `app-pages.js` — 3 ta `catch(e)` bloki markazlashtirildi
- `app-stats.js` — 2 ta `catch(e)` bloki markazlashtirildi
- `app-social.js` — 3 ta `catch(e)` bloki markazlashtirildi
- `app-profile.js` — 1 ta `catch(e)` bloki markazlashtirildi

**HTML:**
- `index.html` — 8 ta cache-bust raqami +1

**Hujjat:** `README.md` (markaziy helperlar bo'limi + fayl jadvali), `SESSION_LOG_audit.md` (refactor R1 qaydi)

## ⚠️ DEPLOY ESLATMASI (R1)
- ✅ Frontend 8 fayli + `index.html` GitHub'ga yuklanishi kerak
- ✅ README **YANGILANDI** — yuklash kerak
- ✅ Cache-busting o'rnatilgan (`?v=NNN +1`) — foydalanuvchilarda yangi versiya avtomatik yuklanadi
- ❌ Backend o'zgarmadi
- ❌ Yangi fayl YO'Q

---

## ✅ #11 — `flask_routes_city.py` auditi (YAKUNLANDI)

**Audit yo'nalishi:** Shahar (City) API — eng yirik audit qilinmagan backend fayli (~420 qator), yangi feature (ko'p edge-case). Mustaqil audit (S1–S4 strategik infratuzilma talab qilmaydi). Tegilgan fayllar: `flask_routes_city.py`, `city_logic.py`. Qoidalar #04, #09, #11, #12, #23 saqlangan.

**Auditdan oldin topilgan muammolar:**

| # | Muammo | Xavf | Holat |
|---|--------|------|-------|
| 1 | `change_type` endpoint o'lik kod (frontend ishlatmaydi, modal rad etilgan) | 🟡 O'rta (API yuzasi, test qilinmagan) | ✅ O'chirildi |
| 2 | `move_item` band/topilmadi holatini ajratmaydi (noto'g'ri "joy band" xabari) | 🟡 Past (UX) | ✅ Tuzatildi |
| 3 | `_CITY_ERR` f-string `CITY_NAME_MAX_LEN` ga import paytida bog'liq | 🟢 Nazariy | ⏭️ Real xavf yo'q |

**Bug YO'Q tasdiqlangan joylar:** `buy_decoration`/`buy_insurance` (ball tekshiruvi + yechish lock ichida atomik, `add_points_history` chaqiriladi — Qoida #26 ✅), `buy_insurance` qayta sotib olish guard (`_is_insurance_active` ✅), koordinata validatsiyasi (`move`, `buy_decoration` chegara ✅), `rename` (bo'sh/uzunlik/`<>` tozalash ✅), GET migration zanjiri (compact→backfill→resync→cleanup, har biri try/except ✅), S1 race condition (`_get_city_lock` per-user lock himoya qiladi ✅).

### Tuzatish 1 — `change_type` o'lik kod zanjiri o'chirildi

README 2 joyda tasdiqlaydi: "frontend bu endpoint'ni ishlatmaydi, modal rad etilgan". `grep` butun frontend bo'ylab (`app-city-move.js`, `index.html`) — `change_type`/`cityChangeType` chaqiruvi YO'Q. To'liq o'lik kod.

- **`flask_routes_city.py`:** `api_city_change_type` endpoint (38 qator) o'chirildi. `BUILDING_TYPES` + `change_building_type` importlari olib tashlandi (faqat shu endpoint ishlatardi — Qoida #12).
- **`city_logic.py`:** `change_building_type` funksiyasi (19 qator) o'chirildi — endpoint o'chgach hech qaerdan chaqirilmasdi. `BUILDING_TYPES` import QOLDIRILDI (`create_building` 281-qator hali ishlatadi — Qoida #12 tekshiruvi).
- `_CITY_ERR["invalid_type"]` QOLDIRILDI — `buy_decoration` ishlatadi.
- **Natija:** City endpoint soni 7 → 6.

### Tuzatish 2 — `move_item` xato aniqligi (Variant A)

**Sabab (Qoida #21):** `move_item` 3 holatda bir xil `False` qaytarardi (koord noto'g'ri / topilmadi / band). Route doim `"occupied"` (joy band) deb javob berardi — item topilmaganda foydalanuvchi noto'g'ri xabar olardi.

- **`city_logic.py` `move_item`:** "topilmadi" holati endi `None` qaytaradi (avval `False`). Docstring 3 qaytarish qiymatini hujjatlashtirdi (`True`=ko'chdi / `False`=band yoki koord noto'g'ri / `None`=topilmadi).
- **`flask_routes_city.py` `api_city_move`:** `None`→`not_found` (404), `False`→`occupied` (400).
- **Ta'sir doirasi (Qoida #09):** `move_item` ni faqat shu route chaqiradi (`grep` tasdiqladi) — boshqa joyga ta'sir yo'q. Route `if result is None` / `if not result` bilan ajratadi.

### Tuzatish 3 — `_CITY_ERR` f-string — O'TKAZIB YUBORILDI (real xavf yo'q)

`name_too_long` f-string'i `CITY_NAME_MAX_LEN` ni modul import paytida ishlatadi. Dastlab "import tartibi xavfi" deb belgilangan edi, lekin qayta baholandi: `CITY_NAME_MAX_LEN` allaqachon faylning `from config import` blokida majburiy import qilinadi (29-qator) → agar config'da bo'lmasa, fayl import paytidayoq qulaydi, f-string'ga yetib bormaydi. F-string `_CITY_ERR` da bo'lishi **qo'shimcha xavf qo'shmaydi**. `_err` ichiga ko'chirish kodni murakkablashtirardi va hech narsa himoya qilmasdi (Qoida #04 — keraksiz "yaxshilik"). Audit #5 dagi 5-muammoga o'xshash nazariy holat.

### Test scenario (Qoida #15)
- Shahar sahifasini ochish → GET ishlaydi (`change_type` ga bog'liq emas).
- Bino bo'sh katakka ko'chirish → ✅ ko'chadi.
- Band katakka → "Bu joy band" (`occupied`, 400).
- Kesh eskirgan/o'chirilgan bino → "Topilmadi" (`not_found`, 404).
- Dekoratsiya/sug'urta sotib olish → `invalid_type` kaliti hali joyida ✅.

### Revert reja (Qoida #16)
- `flask_routes_city.py`: `change_type` endpoint + 2 import qaytarish; `api_city_move` 258-263 ni `if not ok: return _err(u, "occupied")` ga qaytarish.
- `city_logic.py`: `change_building_type` funksiyani qaytarish; `move_item` 773-qator `None`→`False`.
- Hammasi mustaqil — bittasini revert qilish boshqalarga ta'sir qilmaydi.

## 📦 BU SESSIYADA O'ZGARGAN FAYLLAR (#11)
**Backend (2 fayl):**
- `flask_routes_city.py` — `change_type` endpoint o'chirildi (2 import + endpoint), `api_city_move` xato ajratish (404/400)
- `city_logic.py` — `change_building_type` funksiya o'chirildi, `move_item` `None`/`False` ajratish + docstring

**Hujjat:** `README.md` (4 joyda `change_type`/`change_building_type` tozalandi: §19 dizayn izohi, §89 fayl ro'yxati, §213 `city_logic` jadval, §267 `flask_routes_city` jadval "7→6 endpoint" + `move` 404 holati; §489 eski API eslatmasi olib tashlandi), `SESSION_LOG_audit.md` (#11 qaydi)

## ⚠️ DEPLOY ESLATMASI (#11)
- ✅ Backend 2 fayli (`flask_routes_city.py`, `city_logic.py`) GitHub'ga yuklanishi kerak
- ✅ README **YANGILANDI** — yuklash kerak
- ❌ Cache-bust SHART EMAS — frontend tegilmadi (backend o'zgarishi)
- ❌ Yangi fayl YO'Q

---

## ✅ #12 — `flask_routes_core.py` auditi (qisman YAKUNLANDI)

**Audit yo'nalishi:** Eng yirik audit qilinmagan backend fayli (~820 qator) — rating, profil (GET/PUT/public), habits CRUD, guruhlar (create/GET/checkin/goal/delete). Mustaqil audit (S1–S4 strategik infratuzilma talab qilmaydi). Tegilgan fayl: faqat `flask_routes_core.py`. Solishtirildi: `callbacks_habits.py` (M3 uchun). Qoidalar #02, #04, #09, #10, #12, #18, #21 saqlangan.

**Auditdan oldin topilgan muammolar:**

| # | Muammo | Xavf | Holat |
|---|--------|------|-------|
| M1 | O'lik importlar: `date`, `load_group`, `delete_group`, `get_lang`, `get_rank`, `LANGS` | 🟢 Past | ✅ O'chirildi |
| M2 | `api_habits_add` ichida takroriy `import uuid` (modul boshida bor) | 🟢 Past | ✅ Tuzatildi (`re` qoldirildi) |
| M3 | `api_habits_edit` repeat_count kamayganda `done_today_count`/`last_done` reset bo'lmaydi | 🟡 O'rta | ⏭️ Tegilmadi — bot ekvivalenti yo'q, nomuvofiqlik isbotlanmadi |
| M4 | Guruh hujjati race condition (`find_one`→`replace_one`, lock yo'q) | 🟡 O'rta | ⏭️ Strategik → S5 ga yozildi |

### Tuzatish M1 — O'lik importlar olib tashlandi (Qoida #12)

`grep` butun fayl bo'ylab tasdiqladi (import qatoridan tashqari 0 marta ishlatilgan):
- `date` (`from datetime import` dan) — `datetime`/`timedelta`/`timezone` qoldi.
- `load_group`, `delete_group` (`from database import` dan) — guruh `mongo_db["groups"]` orqali to'g'ridan-to'g'ri ishlanadi; `save_group` ishlatiladi, qoldi.
- `get_lang`, `get_rank` (`from helpers import` dan) — `today_uz5` ishlatiladi, qoldi.
- `LANGS` (`from texts import LANGS`) — butun qator o'chdi.

### Tuzatish M2 — Takroriy `uuid` import (api_habits_add)

461-qator `import uuid, re as _re` → `import re as _re`. Modul-darajadagi `import uuid` (6-qator) `api_habits_add` 497-qatorda (`uuid.uuid4()`) ishlaydi — ichki takror keraksiz edi. `re as _re` saqlandi (regex validatsiya uchun kerak). `api_groups` ichidagi `import uuid as _uuid` (618) — alohida nom, tegilmadi (M2 emas).

### M3 — nima uchun tegilmadi (Qoida #04)

`callbacks_habits.py` to'liq o'qildi — **bot tomonida odat TAHRIRLASH handleri yo'q** (faqat cancel/shield/delete/checkin). Demak `api_habits_edit` (WebApp) ning bot ekvivalenti mavjud emas → Qoida #10 sinxronlik buzilishi yo'q. `done_today_count >= repeat_count` faqat "bugun bajarilgan" ko'rinishiga ta'sir qiladi, ball QAYTA BERILMAYDI (checkin alohida endpoint). Real zarar past, haqiqiy bug isbotlanmadi → keraksiz "yaxshilik" qilinmadi. Kelajak audit uchun eslatma sifatida qoldirildi.

### M4 — Strategik (S5)

Guruh hujjati `find_one`→`replace_one` patterni lock'siz. S1 faqat user hujjatini qamraydi. Per-group lock yoki MongoDB atomic kerak → S1 db_lock sessiyasiga qo'shildi (qarang: 🎯 STRATEGIK MUAMMOLAR / S5).

### Bug YO'Q tasdiqlangan joylar
- `api_habits_add` — `HABIT_LIMIT` tekshiruvi, regex vaqt validatsiya, `repeat_count` clamp (1..100), city `create_building` try/except, `schedule_habit` try/except ✅
- `api_profile_update` (PUT) — har maydon uzunlik/turi validatsiya (`display_name`≤60, `phone`≤20, `bio`≤200, `lang` whitelist, `photo_url`≤500000) ✅
- `api_user_public_profile` — privat maydonlar qaytmaydi, rate_limit, `user_not_found` 404 ✅
- `api_habits_delete` — city `delete_building_for_habit` + `unschedule` try/except, topilmadi 404 ✅
- `api_groups` POST — admin guruh limiti (3 ta), bo'sh nom tekshiruvi ✅
- Rating `today_done` — izoh `callbacks_habits.py:451-452` ga ishora qiladi (simple: `last_done==today`, repeat: `done_today_count>=repeat_count`) ✅

### Test scenario (Qoida #15)
Modul import qilinadi → `register_core_routes(app)` → barcha endpoint avvalgidek ishlaydi. O'chirilgan simvollar hech qaerda ishlatilmagan → xulq o'zgarmaydi. `py_compile` ✅.

### Revert reja (Qoida #16)
- Import bloki (6-19 atrofida): `date`, `load_group`/`delete_group`, `get_lang`/`get_rank`, `from texts import LANGS` qatorlarini qaytarish.
- `api_habits_add` 461-qator: `import re as _re` → `import uuid, re as _re`.
- Hammasi mustaqil — qisman revert mumkin.

### Strategik muammoga ta'sir
S1–S4 ga aloqasiz. Yangi **S5** qo'shildi (guruh race) — hal qilinmadi, faqat qayd etildi.

## 📦 BU SESSIYADA O'ZGARGAN FAYLLAR (#12)
**Backend (1 fayl):**
- `flask_routes_core.py` — 5 o'lik import o'chirildi (M1), takroriy `uuid` import tuzatildi (M2)

**Hujjat:** `README.md` (`flask_routes_core` jadval qatori — import izohi), `SESSION_LOG_audit.md` (#12 qaydi + S5 strategik muammo)

## ⚠️ DEPLOY ESLATMASI (#12)
- ✅ Backend 1 fayli (`flask_routes_core.py`) GitHub'ga yuklanishi kerak
- ✅ README + SESSION_LOG **YANGILANDI** — yuklash kerak
- ❌ Cache-bust SHART EMAS — frontend tegilmadi
- ❌ Yangi fayl YO'Q

## ✅ #13 — `menus.py` auditi → menu2 (eski guruh menyusi) o'lik kod tozalandi (YAKUNLANDI)

**Audit yo'nalishi:** `menus.py` (~167 qator). Audit davomida aniqlandi: `menu2_dict`/`build_menu2_text`/`send_menu2` — eski "2-menyu (guruh sahifasi)" qoldig'i. Tekshiruv zanjiri (`callbacks_menu.py`, `handlers_callbacks.py`, `index.html`, `bot_setup.py`) tasdiqladi: `menu2_open` callbackini **hech bir tugma yubormaydi** (1-menyu faqat WebApp "Kirish" tugmasi) → butun zanjir o'lik.

**Tuzatish:**
- `callbacks_menu.py` — `menu2_open` bloki (290-298) + `from menus import send_menu2` (14) o'chirildi (346→334)
- `menus.py` — `menu2_dict`/`build_menu2_text`/`send_menu2` 3 funksiya + yetim `send_message_colored` import + docstring yangilandi (169→104)

**Bug topildi (qoldirildi — Qoida #04):** `callbacks_menu.py:312,324,328` `ADMIN_ID` import qilinmagan → `dismiss_ball_notif`/`admin_confirm_ball_*` da `NameError`. Guruh tozalashga aloqasiz — kelajak audit uchun.

**Eslatma:** Bu audit foydalanuvchi xohishi bilan to'liq guruh tizimini olib tashlashga (#14) o'sib ketdi.

## ✅ #14 — BUTUN GURUH TIZIMI olib tashlandi, ildizi bilan (YAKUNLANDI)

**Sabab:** Foydalanuvchi qarori — guruh (habit-group) funksiyasi butunlay olib tashlansin (bot + WebApp). Do'st, challenge, shop, statistika, shahar TIRIK qoldi.

**Qamrov:** 7 qatlam — UI menyu → callback handler → wizard state → API endpoint → cron job → DB funksiya → MongoDB kolleksiya ta'rifi.

**O'chirilgan fayllar (2):** `groups.py` (~269), `callbacks_groups.py` (564) — to'liq.

**Tozalangan fayllar (17):**
- **Bot:** `handlers_callbacks.py` (dispatch+import, 7→6 sub-handler), `handlers_text.py` (5 guruh state + pending-guruh blok + 3 import, 972→802), `habit_bot.py` (`import groups`), `callbacks_menu.py` (#13), `menus.py` (#13), `handlers_commands.py` (`load_group`/`save_group` import + deep-link `grp_` guruhga qo'shilish blok + pending-guruh blok, 409→334)
- **API/cron:** `flask_routes_core.py` (4 `api_groups*` endpoint + yetim importlar `save_group`/`add_points_history`/`mongo_db`/`bot`, 818→612), `scheduler.py` (`group_daily_reset` funksiya + `daily_reset` guruh bloki + `SYSTEM_JOB_TAGS` + `_is_member_done` helper + yetim importlar, 972→890), `flask_routes_data.py` (`load_group`/`save_group` yetim import), `flask_routes_extra.py` (`load_group`/`save_group` yetim import)
- **DB:** `database.py` (`load_group`/`save_group`/`delete_group` + `groups_col` import, 395→370), `config.py` (`groups_col` ta'rifi + index)
- **Frontend:** `app-social.js` (13 guruh funksiya + `setGroupSub`, `setStatSub` dan yetim `loadGroups()` chaqiruvi, 1460→1198), `app-core.js` (premium "guruh" bandi 3 til + izoh), `strings.js` (`groups:` blok 3 til + `grp_*`/`confirm_del_group`/`ph_group_name`/`tab_grp_friend`/`tab_groups` — 3 til balansda, 1271→1169), `app-stats.js` (izoh), `index.html` (gsub tab tugmalari + `#groups-content`, `#friends-content` ochiq qilindi, cache-bust 4 fayl → v=617)

**Test scenario (Qoida #15):** Bot ishga tushadi (groups import yo'q) → WebApp ochiladi → "Do'st" sub-tab faqat do'stni ko'rsatadi (`setStatSub` `loadFriends()` chaqiradi) → guruh API'lariga murojaat yo'q. Barcha fayl `py_compile`/`node --check` ✅. `strings.js` 3 til balansda (16 kategoriya har biri).

**Revert reja (Qoida #16):** Katta o'zgarish — git revert orqali. Har fayl mustaqil, lekin `groups.py`/`callbacks_groups.py` qaytarilsa, ularni chaqiruvchilar (dispatch, import) ham qaytarilishi kerak.

**Strategik muammolarga ta'sir:** S1 (race) qamrovidan guruh checkin (`flask_routes_core`) chiqdi. S5 (guruh race) endi **mavzusiz** — guruh yo'q. S2 dan `flask_routes_extra` challenge qoldi (tirik). S4 (milestone) o'zgarmadi.

## 🔴 CRASH SABOQI (#14 — deploy paytida)

**Nima bo'ldi:** `database.py` dan `load_group`/`save_group` o'chirilgach, bot Railway'da `ImportError: cannot import name 'load_group' from 'database'` bilan crash bo'ldi (10:21, qayta-qayta restart). Sabab: **3 ta fayl** (`handlers_commands.py`, `flask_routes_data.py`, `flask_routes_extra.py`) hali `load_group`/`save_group` ni import qilardi — lekin ular dastlabki audit qamroviga kirmagan edi (ko'rilmagan fayllar).

**Tuzatish:** 3 faylda import o'chirildi (`flask_routes_data`/`extra` da yetim import edi; `handlers_commands` da deep-link + pending-guruh bloklari ham bor edi). Bot ishga tushdi.

**🔑 KELAJAK QOIDASI (Qoida #09 kengaytmasi):** `database.py`/`config.py` dan **eksport qilinadigan funksiya yoki o'zgaruvchi** o'chirishdan OLDIN — butun repo bo'ylab `grep -rn "funksiya_nomi" *.py` qilib BARCHA import qiluvchilarni topish SHART. Faqat ko'rilgan fayllar bilan cheklanish xato — import xatosi butun botni yiqitadi. Eng xavfli iboralar: `load_group`, `save_group`, `from groups`, `callbacks_groups`, `send_menu2`, `groups_col`. **Deploy tartibi:** past qatlam (DB/config) o'zgarishi yuqori qatlam (import qiluvchilar) bilan BIR vaqtda yuklanishi shart.

## 📦 BU SESSIYADA O'ZGARGAN FAYLLAR (#13 + #14)
**O'chirilgan (2):** `groups.py`, `callbacks_groups.py`
**Backend (12):** `menus.py`, `callbacks_menu.py`, `handlers_callbacks.py`, `handlers_text.py`, `habit_bot.py`, `flask_routes_core.py`, `scheduler.py`, `database.py`, `config.py`, `handlers_commands.py`, `flask_routes_data.py`, `flask_routes_extra.py`
**Frontend (5):** `index.html`, `app-social.js`, `app-core.js`, `strings.js`, `app-stats.js`
**Hujjat:** `README.md` (fayl xaritasi, bog'liqlik jadvali, §208/220/229/242/259/278/474/481/484/499 + L3 qatlam), `SESSION_LOG_audit.md` (#13+#14 qaydi)

## ⚠️ DEPLOY ESLATMASI (#13 + #14)
- ⚠️ **HAMMASI BIR VAQTDA** (yarim holatda yuklamang — `ImportError` xavfi)
- 🗑️ GitHub'dan O'CHIR: `groups.py`, `callbacks_groups.py`
- ✅ YUKLA: 14 fayl (9 backend + 5 frontend) + README + SESSION_LOG
- ✅ Cache-bust: `index.html` da 4 fayl → v=617 (strings, app-core, app-stats, app-social)
- ❌ Yangi fayl YO'Q

## ✅ #15 — `callbacks_menu.py` `ADMIN_ID` import bug (YAKUNLANDI)

**Sabab:** Audit #13 da topilgan, qoida #04 sababli o'sha sessiyada qoldirilgan bug — `callbacks_menu.py` `ADMIN_ID` ni 3 joyda ishlatardi (302, 314, 318) lekin import qilmagan → `dismiss_ball_notif` yoki `admin_confirm_ball_*` bosilganda `NameError: name 'ADMIN_ID' is not defined`.

**Ta'sir doirasi (Qoida #09):** Faqat shu 2 handler zarar ko'rardi. `dismiss_ball_notif` — foydalanuvchi ball bildirishnomasidagi tugmani bosganda adminga "tasdiqladi" xabari yuborilmasdi (crash). `admin_confirm_ball_*` — admin tasdiqlash tugmasini bosganda crash.

**Tuzatish:** `callbacks_menu.py` 10-qatorga `from config import ADMIN_ID` qo'shildi. `callbacks_admin.py:11` aynan shu patternni ishlatadi (`from config import ADMIN_ID`). `config.py:13` da `ADMIN_ID` ta'riflangan. Bog'liqlik xaritasi L0 qatlam — `config` hech narsa import qilmaydi → circular import xavfi yo'q.

**Test scenario (Qoida #15):**
- Foydalanuvchi ball bildirishnomasidagi tugmani bosadi → adminga xabar yuboriladi (302) ✅ (avval crash edi)
- Admin "✅ Tasdiqlash" bosadi → `uid == ADMIN_ID` o'tadi (314) → xabar 5s keyin o'chiriladi (318) ✅

**Revert reja (Qoida #16):** 10-qatordagi `from config import ADMIN_ID` ni o'chirish kifoya. Mustaqil.

**Strategik muammolarga ta'sir:** S1–S4 ga aloqasiz. Faqat import qo'shildi, mantiq tegilmadi.

## 📦 BU SESSIYADA O'ZGARGAN FAYLLAR (#15)
**Backend (1 fayl):**
- `callbacks_menu.py` — `from config import ADMIN_ID` import qo'shildi (10-qator)

**Hujjat:** `README.md` (bog'liqlik jadvali — `callbacks_menu` `import qiladi` ustuniga `config` qo'shildi), `SESSION_LOG_audit.md` (#15 qaydi)

## ⚠️ DEPLOY ESLATMASI (#15)
- ✅ Backend 1 fayli (`callbacks_menu.py`) GitHub'ga yuklanishi kerak
- ✅ README + SESSION_LOG yangilandi — yuklash kerak
- ❌ Cache-bust SHART EMAS — frontend tegilmadi
- ❌ Yangi fayl YO'Q

## ✅ #16 — `points_logic.py` auditi → TOZA (TUZATISH YO'Q)

**Audit yo'nalishi:** `points_logic.py` (75 qator, sof funksiyalar) — kichik/xavfsiz, strategik infratuzilma talab qilmaydi. Tegilgan fayl: YO'Q (audit-only). Tekshirish uchun o'qildi: `flask_routes_data.py` (chaqiruvchi — `apply_pet_dog_bonus`/`apply_item_bonuses` qanday ishlatilishini ko'rish, Qoida #09/#10/#11). Qoidalar #02, #04 saqlandi.

**`apply_item_bonuses` — TOZA:**
- `total_percent` to'g'ri stack (badge + car), `<= 0` da erta qaytadi.
- `effect.get("value", 0)` / `effect.get("type")` — None-safe.
- B variant kafolat (`max(boosted, base_points + 1)`) izoh bilan mos.

**`apply_pet_dog_bonus` — TOZA (shubha qilingan double-bonus bug EMAS):**
Chaqiruvchi (`flask_routes_data.py`) 4 joyda ishlatadi:
- DONE (199 repeat, 254 simple): `is_undo=False` shartsiz, lekin funksiya ichidagi `last_bonus_date != today` guard kunlik faqat 1 marta beradi (2-odat qayta bermaydi).
- UNDO (169 repeat, 229 simple): `is_undo=True` faqat `if not _still_done` (bugun boshqa odat qolmagan) bo'lganda → bonus faqat oxirgi odat undo'da qaytariladi.

**Simmetriya tasdiqlandi (net = 1 marta):** 1-odat done `+bonus` → 2-odat done `0` (guard) → 2-odat undo (`_still_done=true`, qaytarmaydi) → 1-odat undo (`_still_done=false`, `-bonus`, `last_bonus_date=""`) → qayta checkin `+bonus` (to'g'ri). `apply_item_bonuses` ham done/undo da symmetric (`_base`/`_undo_base` bir xil foiz).

**Test scenario (Qoida #15):** pet_dog faol foydalanuvchi 2 odatli kuni → 1-checkin `+bonus`, 2-checkin `0`, 2-undo bonus qoladi, 1-undo `-bonus` (net 0), qayta checkin `+bonus`. Mantiq to'g'ri.

**Revert reja (Qoida #16):** Yo'q — kod o'zgarmadi.

**Strategik muammolarga ta'sir:** S1–S4 ga aloqasiz. `apply_pet_dog_bonus`/`apply_item_bonuses` `save_user` qilmaydi (chaqiruvchi qiladi) → S1 (race) `flask_routes_data` qamrovida qoladi, bu fayl alohida xavf qo'shmaydi.

## 📦 BU SESSIYADA O'ZGARGAN FAYLLAR (#16)
**Kod:** YO'Q (audit-only — `points_logic.py` toza topildi).
**Hujjat:** `SESSION_LOG_audit.md` (#16 qaydi). README tegilmadi (kod o'zgarmadi, Qoida #21).

## ⚠️ DEPLOY ESLATMASI (#16)
- ❌ Kod fayli YO'Q — deploy SHART EMAS.
- ✅ `SESSION_LOG_audit.md` yangilandi (ixtiyoriy — faqat audit tarixi).
- ❌ Cache-bust SHART EMAS.

## ✅ #17 — S4 streak milestone sinxronlashtirildi (YAKUNLANDI)

**Sabab:** S4 strategik muammo — bot tomonida streak milestone ball BERMASDI (faqat WebApp berardi), duplicate guard yo'q (har checkin spam), `STREAK_MILESTONES` ikki xil (bot tuple 8 ta, WebApp dict 5 ta). Kanal asosidagi adolatsizlik. Foydalanuvchi qarori: bot 8 milestone'ni saqlash (3 kun erta motivatsiya, 180/365 sodiqlik), WebApp 8 taga kengaytiriladi.

**Qamrov:** 5 fayl, 4 bosqich (Qoida #23 — bosqichli).

**Bosqich 1 — `config.py`:** Yangi `STREAK_MILESTONES` dict (8 ta: 3✨/7🔥/14⚡/30💎/60🏆/100👑/180🌟/365🎖️ — `emoji`+`bonus` 5/10/20/50/100/200/300/500), `HABIT_LIMIT` dan keyin, CITY dan oldin. `title` qasddan QO'SHILMADI — lokalizatsiya `texts.py` orqali. Yagona manba.

**Bosqich 2 — `callbacks_checkin.py` (bot toggle_/skip_):** `from config import STREAK_MILESTONES` (lokal tuple o'chirildi). `_check_streak_milestone` dict'dan oladi, faqat XABAR yuboradi (emoji + `{days}`+`{bonus}` `.format`). Ball berish 2 blokda (repeat 164-172, simple 334-342): global streak `+1` ichida, `if streak in STREAK_MILESTONES` + `streak_milestones_sent` guard → `bonus` ball + `add_points_history` + thread (xabar). ASOSIY thread'da (S1 race'dan qochish), mavjud `save_user`'dan oldin — alohida save YO'Q.

**Bosqich 2b — `callbacks_checkin_done.py` (bot done_/bildirishnoma):** `from config import STREAK_MILESTONES` (`add_points_history` allaqachon import edi). Xuddi shu ball+guard mantiq 2 blokda (repeat 64-72, simple 160-168). `_check_streak_milestone` ni avvalgidek import qiladi (circular import tartibi buzilmadi — README:541).

**Bosqich 3 — `flask_routes_data.py` (WebApp api_checkin):** Lokal 5-elementli dict o'chirildi → `from config import STREAK_MILESTONES` (8 ta). Mavjud guard+ball+history bloki to'g'ri edi, faqat `ms["title"]` (config'da yo'q) → `T(uid, "streak_milestone_title", days=...)` (lokalizatsiya, Qoida #22 — avval o'zbekcha hardcode `app-pages.js` popup'da rus/ingliz userga ham ko'rinardi).

**Bosqich 4 — `texts.py`:** (a) yangi kalit `streak_milestone_title` 3 til (`{days}` — WebApp popup sarlavhasi); (b) `streak_milestone` matniga `🎁 *+{bonus} ⭐* qo'shildi!` qatori 3 til (bot xabarida bonus ko'rsatish — WebApp popup bilan izchil); (c) matn boshidagi qattiq `🔥` olib tashlandi 3 til → milestone emojisi DINAMIK (`ms["emoji"]` chaqiruvchida prefiks; avval `🔥 🔥`/`🎖️ 🔥` dublikat edi).

**`T()` izmosi tasdiqlandi (`helpers.py:22`):** `return text.format(**kwargs) if kwargs else text` → `T(uid, key, kwarg=...)` (format ichkarida) VA `T(uid, key).format(...)` (xom qaytaradi) ikkalasi xavfsiz. `flask_routes_data` kwarg uslubi, `callbacks_checkin` `.format` uslubi — ikkalasi to'g'ri.

**Test scenario (Qoida #15):** Bot 7-kun streak → `+10` ball, "🔥 Tabriklaymiz! 7 kunlik streak! 🎁 +10 ⭐ ball" + `sent=[7]` → o'sha kun 2-odat checkin: `streak_last_date==today` → milestone blok ishlamaydi (takror yo'q) → ertasi WebApp: `7 in sent` → bermaydi (sinxron). EN user WebApp 30-kun → popup "💎 30-day streak! +50 ⭐". Yangi 3/180/365 endi 3 kanalda. Hammasi `py_compile` ✅, 3 til `{days}`+`{bonus}` balansda, dublikat emoji yo'q.

**Revert reja (Qoida #16):** Har fayl mustaqil. Eng oson — 5 faylni eski versiyaga qaytarish. Yoki: config dict o'chirish + 3 faylda `from config import STREAK_MILESTONES` olib tuple/lokal-dict qaytarish + 4 blokdan milestone-bonus olib `threading.Thread` ni guard'siz tiklash + texts.py 3 yangi qator + `streak_milestone` eski matn.

**Strategik muammolarga ta'sir:** S4 → ⚪ YOPILDI. S1 (race) — milestone ball asosiy thread'da `save_user`'dan oldin qo'shildi, alohida save YO'Q → S1 qamroviga YANGI race qo'shilmadi (mavjud checkin save patterniga qo'shildi). S2/S3 ga aloqasiz.

## 📦 BU SESSIYADA O'ZGARGAN FAYLLAR (#17)
**Backend (4 fayl):** `config.py` (STREAK_MILESTONES dict), `callbacks_checkin.py` (import+2 blok ball+guard), `callbacks_checkin_done.py` (import+2 blok ball+guard), `flask_routes_data.py` (lokal dict→config import + title lokalizatsiya)
**Lokalizatsiya (1 fayl):** `texts.py` (`streak_milestone` +bonus +dinamik emoji, yangi `streak_milestone_title` — 3 til)
**Tegilmagan (faqat o'qildi):** `app-pages.js`, `helpers.py`
**Hujjat:** `README.md` (§47 fayl daraxti config, §207 config STREAK_MILESTONES bloki, dependency jadval — `callbacks_checkin`/`callbacks_checkin_done`/`flask_routes_data` → import ustuniga `config`), `SESSION_LOG_audit.md` (#17 qaydi, S4 → ⚪)

## ⚠️ DEPLOY ESLATMASI (#17)
- 🔴 **5 fayl BIR VAQTDA** (CRASH SABOQI #14): `callbacks_checkin`/`_done`/`flask_routes_data` `from config import STREAK_MILESTONES` qiladi — config eski qolsa `ImportError` → bot crash.
- ✅ YUKLA: `config.py`, `callbacks_checkin.py`, `callbacks_checkin_done.py`, `flask_routes_data.py`, `texts.py` + README + SESSION_LOG
- ❌ Cache-bust SHART EMAS — frontend (`app-pages.js`, `strings.js`) tegilmadi
- ❌ Yangi fayl YO'Q

## ✅ #18 — S1/S2 infratuzilma (`db_lock.py`) + `handlers_text.py` migratsiya (BOSQICH 1-2 YAKUNLANDI)

**Sabab:** S1 (race condition) + S2 (transfer atomic emas) — eng muhim strategik muammo. Variant 2 (per-user `threading.Lock`) tanlandi (S1 qaydidagi tavsiya: oson, tez, 1 instance uchun yetarli).

**Qamrov:** Bosqichli (Qoida #23). Bosqich 1 — infratuzilma. Bosqich 2 — `handlers_text.py` (eng xavfli, ball transfer + Stars). Qolgan fayllar keyingi bosqichlarda.

**Bosqich 1 — `db_lock.py` (YANGI FAYL, L0 qatlam):**
- `get_user_lock(uid)` — lazy per-user lock (int/str uid bir xil lock).
- `user_lock(uid, timeout=3)` — `with` context manager (bitta user); timeout'da `TimeoutError`, `finally`'da release.
- `two_user_locks(a, b, timeout=3)` — transfer uchun (ikki user). **Deadlock-safe:** lock ordering (kichik uid avval) — A→B va B→A teskari transferlar bir vaqtda deadlock qilmaydi. `a==b` → bitta lock (o'z-o'zini bloklamaydi).
- **MUHIM qaror:** lock `load_user`/`save_user` ICHIGA qo'yilmadi (faqat save'ni qulflash race'ni to'xtatmaydi — lock o'qishdan oldin olinib yozishdan keyin qo'yilishi shart). `database.py` tegilmadi (Qoida #02/#04). Chaqiruvchi `with` bilan butun `load→modify→save` blokini o'raydi.
- **Cheklov (halol qayd):** faqat 1 process (Railway 1 instance). 2+ instance → MongoDB atomic ($inc) kerak (S1 Variant 1, kelajak).

**Bosqich 2 — `handlers_text.py` (4 blok o'raldi):**
1. 🔴 **Transfer** (`bozor_waiting_transfer_amount`): `two_user_locks(uid, target_id)`. `u` + `target_u` lock ICHIDA qayta o'qiladi (40-qatordagi `handle_text` boshidagi eski nusxa emas), balans tekshiruvi (`amount > my_points`) ham lock ichida → double-spend, over-spend, qabul qiluvchi yo'qolishi YOPILDI. S2 ham yopildi (ikki save bitta atomik zonada).
2. 🟡 **Admin ball berish** (`admin_waiting_points_amount`): `two_user_locks(uid, target_id)`. `target_u` lock ichida o'qiladi. `uid==target_id` (admin o'ziga) → `u=target_u` sinxron; `uid!=target_id` → admin `u` ham lock ichida qayta o'qiladi (state'dan boshqa maydon eskirmasin).
3. 🟡 **Referral bonus** (referrer): `user_lock(referrer_id)`. `u_ref` lock ichida o'qiladi/yoziladi. Yangi user `u` o'ralmadi (Qoida #04 — hali faol emas, race past; butun reg blokini o'rash juda keng zona, lock ichida network chaqiruv yomon).
4. 🔴 **Stars to'lov** (`handle_successful_payment`): `user_lock(uid)`. **Idempotency tekshiruvi (`charge_id in stars_payments`) HAM lock ichida** — aks holda 2 duplicate event ikkalasi tekshiruvdan o'tib 2x mukofot berishi mumkin edi. Haqiqiy pul → eng muhim.

**Yangi matn kaliti (Qoida #22):** `texts.py` `err_server_busy` — 3 til (UZ/RU/EN). Lock timeout (3s)'da foydalanuvchiga ko'rsatiladi. Markazlashtirilgan — keyingi bosqichlar (`callbacks_shop`, `callbacks_checkin`) ham shu kalitni ishlatadi.

**Tegilmagan (Qoida #04):** `_run_broadcast` admin state save (faqat `state` maydoni, ball yo'q → past xavf). `callbacks_shop.py`, `callbacks_checkin*.py`, `flask_routes_*` — keyingi bosqichlar.

**Test scenario (Qoida #15):**
- Birlik: int/str bir lock ✅, with oladi/qaytaradi ✅, band lock→TimeoutError ✅, exception'da release ✅, two_user A==B bitta lock ✅, deadlock 100x teskari transfer ✅.
- Race stress: 50 parallel checkin lock'siz 250→35 (S1 isbot), lock bilan 250→250 ✅.
- Transfer integ: 30x parallel double-spend yo'q (jami 1000 saqlandi) ✅; A=100 ball, 5x50 urinish → faqat 2 o'tdi (over-spend yo'q) ✅.
- `py_compile`: `db_lock.py`, `handlers_text.py`, `texts.py` ✅. `err_server_busy` 3 til balansda ✅.

**Revert reja (Qoida #16):** Har fayl mustaqil. (1) `handlers_text.py` — 4 blokdan `with user_lock`/`two_user_locks` o'rashni olib, lock ichidagi qayta-`load_user`larni eski (lock'siz) holatga qaytarish + `from db_lock import` o'chirish. (2) `texts.py` — 3 `err_server_busy` qatorini o'chirish. (3) `db_lock.py` — butunlay o'chirish (hech kim import qilmay qoladi). Eng oson: `db_lock.py` o'chirish + `handlers_text.py` ni eski versiyaga qaytarish.

**Strategik muammolarga ta'sir:** S1 — `handlers_text.py` qamrovdan CHIQDI (✅). S2 — transfer atomik zona bo'ldi (✅ shu qism). Qolgan S1 joylari (`callbacks_shop`, `callbacks_checkin*`, `flask_routes_*`) ⏳ keyingi bosqich. S3/S4/S5 ga aloqasiz.

## 📦 BU SESSIYADA O'ZGARGAN FAYLLAR (#18)
**Yangi (1):** `db_lock.py` — per-user lock infratuzilma (L0 qatlam)
**Backend (1):** `handlers_text.py` — 4 blok lock bilan o'raldi + `from db_lock import` (32-qator)
**Lokalizatsiya (1):** `texts.py` — `err_server_busy` 3 til
**Hujjat:** `README.md` (fayl daraxti — `db_lock.py`; L0 qatlam; dependency jadval — `db_lock` qatori + `handlers_text` import ustuni), `SESSION_LOG_audit.md` (#18 qaydi, S1 jadval holat ustuni + migratsiya qaydi)

## ⚠️ DEPLOY ESLATMASI (#18)
- 🔴 **3 fayl BIR VAQTDA** (CRASH SABOQI #14): `handlers_text.py` `from db_lock import user_lock, two_user_locks` qiladi — `db_lock.py` yuklanmasa `ImportError` → bot crash. `texts.py` ham (`err_server_busy` kerak, aks holda `T()` bo'sh qaytaradi — crash emas, lekin xato matn).
- ✅ YUKLA: `db_lock.py` (YANGI), `handlers_text.py`, `texts.py` + README + SESSION_LOG
- ❌ Cache-bust SHART EMAS — frontend tegilmadi
- ✅ Yangi fayl BOR: `db_lock.py` (GitHub'ga qo'shing)

## ✅ #19 — S1 migratsiya davomi: `callbacks_shop.py` + `callbacks_checkin.py` + `callbacks_checkin_done.py`

**Sabab:** #18 da `db_lock.py` infratuzilma + `handlers_text.py` migratsiya tugagandi. #19 — S1 jadvalidagi keyingi ⏳ joylar: bozor (ball sarflash) va checkin (eng tez-tez chaqiriladigan ball oqimi).

**Qamrov:** 3 fayl, Variant 2 (per-user `threading.Lock`, #18 dagi pattern). Har joyda lock ICHIDA `load_user` QAYTA o'qiladi (tashqi/eski nusxa bilan ishlamaslik — #18 saboqi). `TimeoutError` (3s) → `err_server_busy` (#18 da tayyor, 3 til).

**`callbacks_shop.py` (3 blok):**
1. 🟡 `jonfix` — ball ayirish + tekshiruv (`jon_val>20`, `balls<jon_price`) `with user_lock(uid)` ichida; natija `fixed` flagiga (`already`/`no_pts`/`done`) → xabar/o'chirish lock'dan TASHQARIDA (network lock ichida emas, #18 referral qarori). `jonfix` S1 jadvalida alohida yo'q edi — Qoida #09 (xuddi `bozor_buy_jon` mantiqi) bo'yicha qamrandi.
2. 🟡 `bozor_buy_jon` — xuddi shu, `outcome` flagi (`high`/`no_pts`/`ok`).
3. 🟡 `bozor_reset_do` — `points=0` lock ichida, joriy balansdan reset (ayni vaqtdagi checkin yo'qolmaydi). Menyu qayta chizish + `u2=load_user` (faqat `main_msg_id`, 🟢) lock'dan tashqarida — Qoida #04 (tegilmadi).
- Tegilmagan: `menu_bozor`, `bozor_referral`, `bozor_transfer`, `bozor_reset_confirm` — faqat `main_msg_id`/`state` yozadi, ballsiz (🟢). `bot.get_me()` (134) — S3 alohida.

**`callbacks_checkin.py` (`toggle_`):** butun `load → modify → save → menyu` zonasi (`u=load_user`dan `send_main_menu` fallback'gача) `try: with user_lock(uid):` ichiga. `skip_` (ballsiz) va `done_` delegatsiyasi lock'dan TASHQARIDA. `from db_lock import user_lock`.

**`callbacks_checkin_done.py` (`done_`):** butun zonasi xuddi shunday lock bilan. `from db_lock import user_lock` — `callbacks_checkin` import'idan **OLDIN** (circular tartib saqlandi, README:543).

**MUHIM qarorlar (Qoida #21):**
- Checkin'da lock butun blokni (network ham ichida) qamraydi — `save_user` va `bot.send_message` aralashgan, ularni ajratish 350-qatorlik xavfli refaktor bo'lardi (Qoida #04/#23). Bu BIR user locki, network tez (~200-300ms), auto-delete `time.sleep(3)` THREAD'da (lock tashqarisida) → boshqa userlar bloklanmaydi.
- `_check_streak_milestone` thread'da `.start()` (lock ICHIDA chaqiriladi-yu, thread o'zi `user_lock` OLMAYDI) → deadlock yo'q. Tasdiqlandi: `achievements`, `city_logic`, `points_logic`, `scheduler` hech biri `user_lock` olmaydi (re-entrancy xavfi yo'q).
- `toggle_`→`done_` delegatsiyasi (handle_done_callbacks) lock'dan tashqarida chaqiriladi → nested lock yo'q (bitta `cdata` bir vaqtda toggle ham done ham bo'lolmaydi).

**Test scenario (Qoida #15):**
- Stub runtime: ikki checkin fayli birga import OK (circular buzilmadi). Checkin streak 6→7 → +5 base +10 milestone = 15 ball, `sent=[7]` guard ✅. Undo: 15→10, streak 7→6 ✅.
- Concurrency: 200 parallel `toggle_` bir userda — deadlock/crash YO'Q, lock serializatsiya qildi ✅.
- `py_compile`: `callbacks_shop.py`, `callbacks_checkin.py`, `callbacks_checkin_done.py` ✅.

**Revert reja (Qoida #16):** Har fayl mustaqil — eng oson 3 faylni eski versiyaga qaytarish. Yoki qo'lda: `from db_lock import user_lock` o'chirish + `try/with` o'rashni olib blok tanasini chapga indent qilish (checkin: −8 space) + `except TimeoutError` blokini o'chirish + shop flag-mantiqini (`fixed`/`outcome`) eski inline `if/return` ketma-ketligiga qaytarish.

**Strategik muammolarga ta'sir:** S1 — `callbacks_shop.py` + `callbacks_checkin.py` + `callbacks_checkin_done.py` qamrovdan CHIQDI (✅ jadvalda). Checkin lock asosiy thread'da, milestone ball undan oldin → S1 qamroviga yangi race qo'shilmadi. S2/S3/S4/S5 ga aloqasiz.

## 📦 BU SESSIYADA O'ZGARGAN FAYLLAR (#19)
**Backend (3):** `callbacks_shop.py` (3 blok lock + import), `callbacks_checkin.py` (toggle_ lock + import), `callbacks_checkin_done.py` (done_ lock + import)
**Tegilmagan (faqat o'qildi):** `db_lock.py` (imzo tasdiqlandi)
**Hujjat:** `README.md` (`db_lock` importerlar qatori; `callbacks_checkin`/`callbacks_checkin_done`/`callbacks_shop` import ustuniga `db_lock`; circular import eslatmasiga `db_lock` xavfsizligi), `SESSION_LOG_audit.md` (#19 qaydi, S1 jadval 4 qator → ✅ #19)

## ⚠️ DEPLOY ESLATMASI (#19)
- 🔴 **3 fayl bir vaqtda** + `db_lock.py` serverda bo'lishi shart (#18 dan bor). `texts.py` `err_server_busy` ham (#18 dan bor).
- ✅ YUKLA: `callbacks_shop.py`, `callbacks_checkin.py`, `callbacks_checkin_done.py` + README + SESSION_LOG
- ❌ Cache-bust SHART EMAS — frontend tegilmadi
- ❌ Yangi fayl YO'Q (`db_lock.py` allaqachon bor)

## 🔵 KEYINGI CHATGA (#20)

> #19 da S1 migratsiya davom etdi: `callbacks_shop.py` (jonfix/buy_jon/reset), `callbacks_checkin.py` (toggle_), `callbacks_checkin_done.py` (done_). S1 jadvalida holat ustuni — qaysi joylar qolgani ko'rsatilgan.
> **Audit ustuvorligi (S1 migratsiya davomi — qolgan ⏳):** 🟡 `flask_routes_data.py` (`api_checkin` — WebApp, bot toggle bilan sinxron bo'lishi shart). 🟡 `flask_routes_extra.py` — mavjud `_get_shop_lock` ni `db_lock` ga ko'chirib markazlashtirish (Qoida #17) + `api_friends_add` (mutual friends). 🟢 `flask_routes_core.py` (habits CRUD), `scheduler.py` (daily_reset/milestone cron).
> **Eslatma:** har bosqichda lock ICHIDA `load_user` QAYTA o'qilishi shart. `err_server_busy` kaliti tayyor (Flask'da 429 JSON javobi bilan ham ishlatilishi mumkin). Flask route'larda `TimeoutError` → `jsonify({"ok":False,...}), 429` (bot'dagi `answer_callback_query` o'rniga).
> **⏳ FOYDALANUVCHI SO'RAGAN (kutilmoqda):** inline tugma bosilganda XABAR O'CHSIN (3 xil o'chirish uslubini yagona standartga) — alohida sessiya.


