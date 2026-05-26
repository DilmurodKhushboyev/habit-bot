// ==============================================
// app-city.js — Shahar sahifasi (PHASE C4: API integratsiya)
// ==============================================
// Bog'liqlik:
//   - app-city-buildings.js (bino render: cityBuildingStage, cityBuildingSVG,
//     renderCityBuildings — index.html da BU fayldan KEYIN yuklanadi)
//   - app-core.js (apiFetch — GET /api/city/<uid>; userId; S() msg.connection_error;
//     loaded state — sahifa yuklanganini belgilash)
//   - strings.js (S() funksiya — hozir faqat msg.connection_error; city.* C7 da)
//   - config.py BUILDING_STAGE_THRESHOLDS bilan SINXRON (Qoida #11)
//
// PHASE C2.1: 30×30 = 900 katak isometric grid (statik, scroll bilan).
// PHASE C2.2/C2.3 (pan/zoom): YAGNI sababli o'tkazib yuborilgan.
// PHASE C3.1: demo binolar (5 stage), monoxrom oq clay render uslubi.
// PHASE C3.2: 10 bino turi — barchasi BIR XIL standart kub (o'lcham/shakl farqi yo'q),
//             faqat stage bo'yicha balandlik o'zgaradi. Bino mantiqi
//             app-city-buildings.js da (Qoida #24).
// PHASE C3.3: dekoratsiyalar — KEYINGA QOLDIRILDI (kichik izometrik primitivlar
//             tanib bo'lmaydigan shakl berdi). API decorations massivi render
//             qilinmaydi (professional SVG ikonkalar kelguncha).
// PHASE C4:   _cityDemoData O'CHIRILDI — loadCity() endi async, GET /api/city/<uid>
//             chaqiradi. API javobi: {buildings:[{habit_id,type,x,y,progress,stage}],
//             decorations, insurance_active, ...}. API xato bo'lsa — xato holati
//             + "Qayta urinish" tugma (soxta demo data ko'rsatilmaydi).
// ==============================================

// ── ISOMETRIC GRID KONSTANTLARI (Qoida #17 — magic number'larni markazlash) ──
// Klassik 2:1 isometric nisbat — eng keng tarqalgan va eng tabiiy ko'rinish.
// Bu konstantalar app-city-buildings.js da ham ishlatiladi (global scope).
const CITY_GRID_SIZE = 30;        // 30×30 = 900 katak (C2.1: 20→30 ga kengaytirildi)
const CITY_TILE_W    = 80;        // Romb kenglik (px)
const CITY_TILE_H    = 40;        // Romb balandlik (px) — 2:1 nisbat
const CITY_PADDING   = 40;        // SVG ichida atrof bo'shliq

// ── Katak shrink faktori (3D suzuvchi kub effekti) ──
// Har polygon vertex'i markazga shu factor bilan tortiladi → polygon'lar orasida
// tabiiy gap paydo bo'ladi → fon (canvas-wrap) gap'da ko'rinadi → "kublar suzayotgan"
// hissi. Qoida #17: hardcode emas, markazlashtirilgan konstanta.
// 0.92 = har vertex 8% ichkariga, ~3px gap (CITY_TILE_W=80 da). Bu Stripe/Linear
// premium minimalist 3D shahar referensiga mos (chiziq EMAS, gap+soya).
const CITY_TILE_SHRINK = 0.92;

// ── Isometric koordinata transformatsiyasi ──
// Standart isometric formula: (x, y) grid → ekrandagi (sx, sy) pozitsiya
//   sx = (x - y) * (TILE_W / 2)
//   sy = (x + y) * (TILE_H / 2)
// Natija: x=0,y=0 yuqori cho'qqida; x=19,y=19 pastki cho'qqida.
function cityIsoX(x, y) {
  return (x - y) * (CITY_TILE_W / 2);
}
function cityIsoY(x, y) {
  return (x + y) * (CITY_TILE_H / 2);
}

// ── BINO STAGE KONSTANTLARI (Qoida #11 — backend bilan SINXRON) ──
// config.py BUILDING_STAGE_THRESHOLDS = [13, 26, 39, 52, 66]
// Bu chegaralar progress (kun) → stage (0-4) ni aniqlaydi.
// Birini o'zgartirsangiz — config.py ni ham (va aksincha).
const CITY_STAGE_THRESHOLDS = [13, 26, 39, 52, 66];

// Bino vizual o'lchamlari (izometrik kub) — Qoida #17 magic number markazlash
// Kub asosi katak romb o'lchamidan kichik — binolar orasida bo'shliq qoladi,
// shahar "havodor" ko'rinadi va atrofni ko'rish osonroq (foydalanuvchi tanlovi).
const CITY_BLD_BASE_W = 60;   // kub asos kengligi (px) — CITY_TILE_W=80 dan kichik
const CITY_BLD_BASE_H = 30;   // kub asos balandligi (px) — CITY_TILE_H=40 dan kichik (2:1)
// C3.5b: CITY_BLD_HEIGHTS massivi (stage bo'yicha balandlik) OLIB TASHLANDI.
// Endi bino balandligi UZLUKSIZ — progress (0-66 kun) ga chiziqli bog'langan.
// Balandlik mantiqi app-city-buildings.js da: cityBuildingHeight() funksiyasi,
// CITY_BLD_MIN_HEIGHT / CITY_BLD_FULL_HEIGHT / CITY_BLD_MAX_PROGRESS konstantalar.

// ── ZOOM KONSTANTLARI (Qoida #17 — magic number'larni markazlash) ──
// CSS transform: scale(_cityZoom) .city-canvas SVG ga qo'llanadi.
// viewBox o'zgarmaydi — auto-scroll markazlash mantig'i va elementFromPoint
// (drag hit-testing, app-city-move.js) buzilmasin.
const CITY_ZOOM_MIN     = 0.6;
const CITY_ZOOM_MAX     = 1.6;
const CITY_ZOOM_STEP    = 0.1;
const CITY_ZOOM_DEFAULT = 1.0;
// Pinch sezgirligi: 2-barmoq orasidagi masofa qancha o'zgarsa zoom o'zgaradi.
// Tugmalar diskret (0.1 qadam), pinch esa uzluksiz — boshlang'ich masofaga nisbat
// olinadi (startDist / curDist), boshlang'ich zoom bilan ko'paytiriladi.
const CITY_PINCH_MIN_DIST = 30;  // px — kichikroq pinch e'tiborga olinmaydi (shovqin)

// Global state — tab almashtirilganda zoom darajasi saqlanadi (loadCity qayta
// chaqirilsa ham foydalanuvchining tanlovi yo'qolmasin). applyCityZoom har
// renderCityGrid oxirida chaqiriladi — DOM yangidan yaratilsa ham zoom qaytadi.
let _cityZoom = CITY_ZOOM_DEFAULT;

// Pinch holati — touchstart paytida 2 barmoq tegsa boshlanadi, touchend da tozalanadi
let _cityPinchState = null;

// ── BINO ANIMATSIYA KONSTANTALARI (yangi — Qoida #17) ──
// Bino yangi qo'shilganda CSS @keyframes orqali pastdan ko'tariladi.
// CSS animation davomiyligi 500ms — shundan keyin .city-bld--new klassi olib
// tashlanadi (DOM toza saqlanadi). Spring kurva CSS da (cubic-bezier oxirida sakrab).
// localStorage kalit: shahar har foydalanuvchi uchun bir xil device'da bir xil joyda.
const CITY_BLD_ANIM_DURATION   = 500;  // ms — CSS @keyframes davomiyligi bilan SINXRON
const CITY_SEEN_BUILDINGS_KEY  = 'city_seen_buildings';  // localStorage kaliti

// ── "Yangi bino" aniqlash (localStorage bilan) ──
// renderCityBuildings (app-city-buildings.js) chaqirilishidan AVVAL — qaysi
// habit_id lar yangi ekanini aniqlaymiz. Render paytida har bino uchun klass
// qo'shiladi. Animatsiya tugagach (CITY_BLD_ANIM_DURATION ms), habit_id ro'yxatga
// qo'shiladi — keyingi safar tab ochilganda animatsiya YO'Q (Qoida: animatsiya
// faqat 1-marta, har tab almashtirishda emas).
// Qaytaradi: Set — bilan tezroq tekshirish (.has, O(1))
function _getCitySeenBuildings() {
  try {
    const raw = localStorage.getItem(CITY_SEEN_BUILDINGS_KEY);
    if (!raw) return new Set();
    const arr = JSON.parse(raw);
    return new Set(Array.isArray(arr) ? arr : []);
  } catch (e) {
    // localStorage o'chirilgan/buzilgan — bo'sh Set qaytaramiz (xavfsiz fallback)
    return new Set();
  }
}

// Bir habit_id ni "ko'rilgan" deb belgilash (animatsiya tugagach chaqiriladi).
// Set ni Array ga aylantirib JSON saqlaymiz (5MB limit — minglab habit_id lar
// uchun yetarli, har biri taxminan 25 belgi).
function _markBuildingSeen(habitId) {
  try {
    const seen = _getCitySeenBuildings();
    if (seen.has(habitId)) return;  // allaqachon bor — qayta yozish shart emas
    seen.add(habitId);
    localStorage.setItem(CITY_SEEN_BUILDINGS_KEY, JSON.stringify(Array.from(seen)));
  } catch (e) { /* quota/disabled — jim o'tkazib yuboramiz */ }
}

// ── Zoom darajasini DOM ga qo'llash + tugmalar disabled holatini boshqarish ──
// .city-canvas (SVG) ga transform: scale(_cityZoom). transform-origin: center
// CSS da. Min/max chegaraga yetilganda tegishli tugma disabled bo'ladi (vizual
// va funksional — pointer-events:none CSS da).
function applyCityZoom() {
  const svg = document.querySelector('.city-canvas');
  if (svg) svg.style.transform = 'scale(' + _cityZoom.toFixed(3) + ')';
  // Tugmalar disabled holati (chegara yetildi → tegishli tugma o'chadi)
  const btnIn  = document.getElementById('city-zoom-in');
  const btnOut = document.getElementById('city-zoom-out');
  if (btnIn) {
    if (_cityZoom >= CITY_ZOOM_MAX - 1e-6) btnIn.setAttribute('aria-disabled', 'true');
    else btnIn.removeAttribute('aria-disabled');
  }
  if (btnOut) {
    if (_cityZoom <= CITY_ZOOM_MIN + 1e-6) btnOut.setAttribute('aria-disabled', 'true');
    else btnOut.removeAttribute('aria-disabled');
  }
  // Indikator matnini yangilash — joriy zoom darajasi % da (masalan "120%").
  // Math.round — pinch paytida silliq raqamlar ("100% → 105% → 112%"...),
  // .toFixed emas (chunki "112.3%" shovqinli). textContent — XSS xavfsiz.
  const reset = document.getElementById('city-zoom-reset');
  if (reset) reset.textContent = Math.round(_cityZoom * 100) + '%';
  // Tugmalar aria-label tarjimasi (S() har til o'zgarganda yangi qiymat beradi)
  if (typeof S === 'function') {
    if (btnIn)  btnIn.setAttribute('aria-label',  S('city', 'zoom_in'));
    if (btnOut) btnOut.setAttribute('aria-label', S('city', 'zoom_out'));
    if (reset)  reset.setAttribute('aria-label',  S('city', 'zoom_reset'));
    // C7: Recenter tugma ham shu yerda — applyCityZoom har til o'zgarganda chaqiriladi
    const recenter = document.getElementById('city-recenter');
    if (recenter) recenter.setAttribute('aria-label', S('city', 'recenter'));
  }
}

// ── Tugma onclick'lari (index.html dan chaqiriladi) ──
// Haptic light — Telegram WebApp da mavjud (mavjud pattern, masalan
// app-city-move.js da medium ishlatilgan).
function cityZoomIn() {
  if (_cityZoom >= CITY_ZOOM_MAX - 1e-6) return;
  _cityZoom = Math.min(CITY_ZOOM_MAX, _cityZoom + CITY_ZOOM_STEP);
  applyCityZoom();
  // Tooltip ochiq bo'lsa yopiladi (zoom paytida bino ekranda joyini o'zgartiradi)
  if (typeof _hideCityTooltip === 'function' && _cityActiveTooltip) _hideCityTooltip();
  try {
    if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.HapticFeedback) {
      window.Telegram.WebApp.HapticFeedback.impactOccurred('light');
    }
  } catch (e) { /* haptic ixtiyoriy — xato butun zoom'ni buzmasin */ }
}
function cityZoomOut() {
  if (_cityZoom <= CITY_ZOOM_MIN + 1e-6) return;
  _cityZoom = Math.max(CITY_ZOOM_MIN, _cityZoom - CITY_ZOOM_STEP);
  applyCityZoom();
  if (typeof _hideCityTooltip === 'function' && _cityActiveTooltip) _hideCityTooltip();
  try {
    if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.HapticFeedback) {
      window.Telegram.WebApp.HapticFeedback.impactOccurred('light');
    }
  } catch (e) { /* haptic ixtiyoriy */ }
}

// ── Zoom reset (indikator tugmasi onclick'i) ──
// Foydalanuvchi 1 bosish bilan asl holatga (1.0x) qaytsin — pinch chalkash holatdan
// qutulish uchun (masalan, 147% da qolib ketdi, "qanday qaytaman?" muammosi).
// CSS .city-canvas da `transition: transform 0.18s ease` borligi sababli — silliq
// animatsiya bilan qaytadi (tugma → 1.0 sakrash YOK, smooth).
function cityZoomReset() {
  if (Math.abs(_cityZoom - CITY_ZOOM_DEFAULT) < 1e-6) return;  // allaqachon 1.0x da
  _cityZoom = CITY_ZOOM_DEFAULT;
  applyCityZoom();
  if (typeof _hideCityTooltip === 'function' && _cityActiveTooltip) _hideCityTooltip();
  try {
    if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.HapticFeedback) {
      window.Telegram.WebApp.HapticFeedback.impactOccurred('light');
    }
  } catch (e) { /* haptic ixtiyoriy */ }
}

// ── Markazga qaytish (C7 — yangi) ──
// Foydalanuvchi pinch/scroll bilan adashganda — bitta bosish bilan "bosh sahifa"ga:
//   1. Zoom 1.0x ga qaytadi (CSS transform smooth animatsiya — .city-canvas
//      transition: transform 0.18s ease bor)
//   2. Scroll grid markaziga keladi (renderCityGrid'dagi auto-center mantig'i bilan AYNAN
//      bir xil hisob — Qoida #11 izchillik: wrap.scrollWidth/2)
//   3. Tooltip ochiq bo'lsa yopiladi (bino joyini o'zgartirdi)
//   4. Haptic light feedback (boshqa tugmalardek)
//
// SMOOTH SCROLL: scrollTo({behavior: 'smooth'}) — browser native, GPU compositing.
// iOS Safari 15.4+ va Telegram WebView qo'llab-quvvatlaydi. Eski browser'larda
// darhol siljitadi (graceful degradation — funksiya baribir ishlaydi).
function cityRecenter() {
  // Tooltip yopish (zoom va scroll o'zgaradi)
  if (typeof _hideCityTooltip === 'function' && _cityActiveTooltip) _hideCityTooltip();

  // 1. Zoom 1.0x ga qaytish (agar boshqacha bo'lsa)
  if (Math.abs(_cityZoom - CITY_ZOOM_DEFAULT) >= 1e-6) {
    _cityZoom = CITY_ZOOM_DEFAULT;
    applyCityZoom();
  }

  // 2. Scroll markazga (smooth)
  // .city-canvas-wrap querySelector orqali — har render uchun yangi DOM bo'lishi mumkin,
  // saqlangan ssilka eskirgan bo'lishi mumkin (Qoida #13 — shared state ehtiyot).
  const wrap = document.querySelector('.city-canvas-wrap');
  if (wrap) {
    // scrollTo native smooth — try/catch chunki eski browser'larda behavior bo'lmasa
    // throw qiladi (xato butun funksiyani buzmasin)
    try {
      wrap.scrollTo({
        left: (wrap.scrollWidth  - wrap.clientWidth)  / 2,
        top:  (wrap.scrollHeight - wrap.clientHeight) / 2,
        behavior: 'smooth',
      });
    } catch (e) {
      // Fallback: oddiy assignment (darhol siljiydi, lekin ishlaydi)
      wrap.scrollLeft = (wrap.scrollWidth  - wrap.clientWidth)  / 2;
      wrap.scrollTop  = (wrap.scrollHeight - wrap.clientHeight) / 2;
    }
  }

  // 3. Haptic feedback
  try {
    if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.HapticFeedback) {
      window.Telegram.WebApp.HapticFeedback.impactOccurred('light');
    }
  } catch (e) { /* haptic ixtiyoriy */ }
}

// ── Pinch-zoom (2 barmoq) — capture rejimida, app-city-move.js dan oldin ──
// MUHIM (Qoida #09 — ta'sir doirasi):
//   app-city-move.js .city-canvas ga touchstart handler ulagan (long-press drag).
//   Pinch handler .city-canvas-wrap ga CAPTURE rejimida ulanadi — bubbling'dan
//   AVVAL ishlaydi. 2 barmoq tegsa:
//     1) Agar drag boshlanmagan bo'lsa: stopPropagation() — drag handler
//        umuman chaqirilmaydi
//     2) Agar drag allaqachon faollashgan bo'lsa (1 barmoq long-press → 2-barmoq):
//        dispatchEvent('touchcancel') orqali drag bekor qilinadi (move.js onTouchCancel),
//        keyin pinch boshlanadi
// Bu yondashuv app-city-move.js ga TEGMASLIKka imkon beradi (Qoida #02).
function _initCityPinch(container) {
  if (!container) return;
  const wrap = container.querySelector('.city-canvas-wrap');
  const svg  = container.querySelector('.city-canvas');
  if (!wrap || !svg) return;

  function _pinchDist(t1, t2) {
    const dx = t2.clientX - t1.clientX;
    const dy = t2.clientY - t1.clientY;
    return Math.sqrt(dx * dx + dy * dy);
  }

  function onPinchStart(e) {
    if (!e.touches || e.touches.length !== 2) return;
    const dist = _pinchDist(e.touches[0], e.touches[1]);
    if (dist < CITY_PINCH_MIN_DIST) return;  // juda yaqin — shovqin
    // Tooltip ochiq bo'lsa yopiladi (pinch paytida bino joyini o'zgartiradi)
    if (typeof _hideCityTooltip === 'function' && _cityActiveTooltip) _hideCityTooltip();
    // Agar app-city-move.js da drag faol bo'lsa (long-press 600ms o'tgan) — bekor qilamiz
    try {
      svg.dispatchEvent(new TouchEvent('touchcancel', { bubbles: true, cancelable: true }));
    } catch (err) { /* eski browserlar TouchEvent constructor'ni qo'llab-quvvatlamasligi mumkin */ }
    e.stopPropagation();  // app-city-move.js touchstart chaqirilmasin
    _cityPinchState = {
      startDist: dist,
      startZoom: _cityZoom,
    };
  }

  function onPinchMove(e) {
    if (!_cityPinchState) return;
    if (!e.touches || e.touches.length !== 2) return;
    e.preventDefault();   // sahifa scroll/bouncing'ini to'xtatish
    e.stopPropagation();
    const dist = _pinchDist(e.touches[0], e.touches[1]);
    const ratio = dist / _cityPinchState.startDist;
    let newZoom = _cityPinchState.startZoom * ratio;
    // Min/max chegaralar
    if (newZoom < CITY_ZOOM_MIN) newZoom = CITY_ZOOM_MIN;
    if (newZoom > CITY_ZOOM_MAX) newZoom = CITY_ZOOM_MAX;
    _cityZoom = newZoom;
    applyCityZoom();
  }

  function onPinchEnd(e) {
    if (!_cityPinchState) return;
    // Pinch tugadi (barcha barmoqlar olindi yoki 1 ga tushdi)
    if (!e.touches || e.touches.length < 2) {
      _cityPinchState = null;
    }
  }

  // Capture rejimi (true) — bubbling'dan oldin parent'da ushlash.
  // app-city-move.js .city-canvas ga ulangan — capture parent'da bubbling'dan
  // oldin ishlaydi → biz birinchi navbatda 2 barmoqni ushlab olamiz.
  // passive: false — preventDefault ishlasin (pinch paytida sahifa scroll'ini to'xtatish).
  wrap.addEventListener('touchstart',  onPinchStart, { passive: false, capture: true });
  wrap.addEventListener('touchmove',   onPinchMove,  { passive: false, capture: true });
  wrap.addEventListener('touchend',    onPinchEnd,   { passive: true,  capture: true });
  wrap.addEventListener('touchcancel', onPinchEnd,   { passive: true,  capture: true });
}

// ── BINO TAP → INFO TOOLTIP (C6 — yangi) ──
// Foydalanuvchi binoga qisqa tap qilsa — kichik tooltip ochiladi (nom, progress,
// foiz). DRAG bilan to'qnashuv yo'q — sabab: browser drag paytida (touchmove
// preventDefault chaqiriladi app-city-move.js da) `click` event'ni emit qilmaydi.
// Demak `click` da tooltip ochish DRAG holatida ishlamaydi — avtomatik xavfsiz
// (Qoida #09 — mavjud handlerga tegmaymiz).
//
// Tooltip — HTML overlay (SVG <text> emas), position:fixed → zoom transform
// ta'sir qilmaydi, har doim bir o'lchamda turadi.
// Yopilish: boshqa joyga click | 4s timeout | yangi bino tap.

const CITY_TOOLTIP_TIMEOUT = 4000;  // ms — avtomatik yopilish
let _cityActiveTooltip = null;      // {el, habitId, timerId, gridG}

// Tooltip yopish (har joydan chaqirilishi mumkin — toza universal)
function _hideCityTooltip() {
  if (!_cityActiveTooltip) return;
  const t = _cityActiveTooltip;
  _cityActiveTooltip = null;  // darhol holatdan o'chiramiz (ikki marta chaqirilmasin)
  if (t.timerId) clearTimeout(t.timerId);
  if (t.gridG) t.gridG.classList.remove('city-bld--selected');
  if (t.el && t.el.parentNode) {
    // CSS hide animatsiya (150ms) → keyin DOM dan olib tashlash
    t.el.classList.add('city-bld-tooltip--hiding');
    setTimeout(() => {
      if (t.el && t.el.parentNode) t.el.parentNode.removeChild(t.el);
    }, 160);
  }
}

// Tooltip ko'rsatish — gridG (SVG <g>) va building (api ma'lumotidan)
function _showCityTooltip(gridG, building) {
  // Avval mavjud tooltip yopiladi (yangi bino bosildi)
  _hideCityTooltip();

  // Ekran koordinata: binoning SVG ichidagi joyini clientRect'ga aylantiramiz.
  // getBoundingClientRect() <g> ning oxirgi vizual chegarasini qaytaradi
  // (zoom transform ham hisobga olinadi — natija to'g'ri ekran piksellari).
  const rect = gridG.getBoundingClientRect();
  if (rect.width === 0 || rect.height === 0) return;  // bino vizual jihatdan yo'q

  // Progress hisoblash (defensiv — null/undefined himoyasi)
  const progress = Math.max(0, Math.min(66, building.progress || 0));
  const percent  = Math.round((progress / 66) * 100);
  const name     = building.habit_name || '';

  // Tarjima kalitlari (S funksiya — strings.js)
  const kunWord    = (typeof S === 'function') ? S('city', 'kun_dan') : 'kun';
  const tayyorWord = (typeof S === 'function') ? S('city', 'tayyor') : 'tayyor';

  // XSS himoya — name foydalanuvchi yozgan matn (xavfli HTML bo'lishi mumkin)
  const safeName = String(name)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  // Tooltip DOM yaratish
  const el = document.createElement('div');
  el.className = 'city-bld-tooltip';
  el.innerHTML = `
    <div class="city-bld-tooltip-title">${safeName}</div>
    <div class="city-bld-tooltip-bar">
      <div class="city-bld-tooltip-bar-fill" style="width:${percent}%"></div>
    </div>
    <div class="city-bld-tooltip-stats">${progress} / 66 ${kunWord}  ·  ${percent}% ${tayyorWord}</div>
  `;

  // Joylashuv: bino tepasida, markazlashtirilgan. Avval body'ga qo'shamiz
  // (offsetWidth/Height olish uchun), keyin pozitsiya beramiz.
  document.body.appendChild(el);
  const tw = el.offsetWidth;
  const th = el.offsetHeight;

  // ── 4 TOMONLAMA JOYLASHUV (Qoida #21) ──
  // Tooltip bino atrofida 4 ta variantdan birini tanlaydi:
  //   1. TOP    — bino tepasida (default, eng yaxshi UX — yuqoriga qaraydi)
  //   2. BOTTOM — bino pastida (tepada joy yo'q bo'lsa)
  //   3. RIGHT  — bino o'ngida (yuqori/past ham yo'q bo'lsa)
  //   4. LEFT   — bino chapida (faqat o'ngda joy yo'q bo'lsa)
  // Har holatda uchburchak (::after) binoga ko'rsatadi — CSS data-placement
  // atributiga qarab to'g'ri tomonga joylashadi.
  //
  // GAP — bino bilan tooltip orasidagi bo'shliq (uchburchak uchun 14px yetadi).
  const GAP = 14;
  const margin = 8;  // ekran chetidan chekinish
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const HEADER_SAFE = 70;  // yuqorida header taxminan 70px — ostida bo'lmasin
  const FOOTER_SAFE = 80;  // pastda bottom-nav + safe-area

  // Bino markazlari (clientRect koordinatlari)
  const bcx = rect.left + rect.width / 2;   // bino markazi X
  const bcy = rect.top  + rect.height / 2;  // bino markazi Y

  // Har variant uchun: tooltip joylashuvi va u sig'adi-yo'qligini tekshiramiz.
  // Sig'di = ekrandan tashqari chiqmaydi (margin'ni hisobga olib).
  function _fitsTop() {
    return (rect.top - th - GAP) >= HEADER_SAFE;
  }
  function _fitsBottom() {
    return (rect.bottom + th + GAP) <= (vh - FOOTER_SAFE);
  }
  function _fitsRight() {
    return (rect.right + tw + GAP) <= (vw - margin);
  }
  function _fitsLeft() {
    return (rect.left - tw - GAP) >= margin;
  }

  let placement, left, top;
  if (_fitsTop()) {
    placement = 'top';
    left = bcx - tw / 2;
    top  = rect.top - th - GAP;
  } else if (_fitsBottom()) {
    placement = 'bottom';
    left = bcx - tw / 2;
    top  = rect.bottom + GAP;
  } else if (_fitsRight()) {
    placement = 'right';
    left = rect.right + GAP;
    top  = bcy - th / 2;
  } else if (_fitsLeft()) {
    placement = 'left';
    left = rect.left - tw - GAP;
    top  = bcy - th / 2;
  } else {
    // Hech qaerga sig'maydi (juda kichik ekran yoki katta tooltip) — top fallback,
    // ekran chegarasi clamp bilan to'g'rilanadi (vizual nomos, lekin ko'rinadi)
    placement = 'top';
    left = bcx - tw / 2;
    top  = rect.top - th - GAP;
  }

  // Ekran chegarasi himoyasi (clamp — chetdan margin chekinish)
  // Yuqori/past joylashuvda — gorizontal clamp (uchburchak bino markazidan
  // ozgina chetga siljishi mumkin, lekin tooltip ekranda ko'rinadi)
  // Chap/o'ng joylashuvda — vertikal clamp
  if (placement === 'top' || placement === 'bottom') {
    if (left < margin) left = margin;
    if (left + tw > vw - margin) left = vw - tw - margin;
  } else {
    if (top < HEADER_SAFE) top = HEADER_SAFE;
    if (top + th > vh - FOOTER_SAFE) top = vh - FOOTER_SAFE - th;
  }

  el.setAttribute('data-placement', placement);  // CSS uchburchakni shu atributga qarab joylashtiradi
  el.style.left = left + 'px';
  el.style.top  = top + 'px';

  // Bino "tanlangan" vizual holati
  gridG.classList.add('city-bld--selected');

  // Avtomatik yopilish (4s)
  const timerId = setTimeout(_hideCityTooltip, CITY_TOOLTIP_TIMEOUT);

  // Holat saqlash
  _cityActiveTooltip = {
    el,
    habitId: building.habit_id,
    timerId,
    gridG,
  };

  // Haptic — selection feedback (yengil)
  try {
    if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.HapticFeedback) {
      window.Telegram.WebApp.HapticFeedback.selectionChanged();
    }
  } catch (e) { /* ixtiyoriy */ }
}

// Tap handler ulash — renderCityGrid oxirida chaqiriladi
function _initCityTap(container) {
  if (!container) return;
  const svg = container.querySelector('.city-canvas');
  if (!svg) return;

  // click event — browser drag paytida emit qilmaydi (touchmove preventDefault
  // tufayli) → drag bilan to'qnashuv tabiiy ravishda yo'q (Qoida #09).
  svg.addEventListener('click', function (e) {
    const g = e.target.closest('.city-bld');
    if (!g) {
      // Bino tashqarisida click — agar tooltip ochiq bo'lsa, yopamiz
      if (_cityActiveTooltip) _hideCityTooltip();
      return;
    }
    const habitId = g.getAttribute('data-habit-id');
    if (!habitId) return;

    // Bir xil binoni qayta tap — tooltip yopiladi (toggle xulq — UX standart)
    if (_cityActiveTooltip && String(_cityActiveTooltip.habitId) === String(habitId)) {
      _hideCityTooltip();
      return;
    }

    // _cityData keshidan bino ma'lumotini topish (app-city-move.js bilan bir xil pattern)
    let building = null;
    if (_cityData && Array.isArray(_cityData.buildings)) {
      for (const b of _cityData.buildings) {
        if (String(b.habit_id) === String(habitId)) { building = b; break; }
      }
    }
    if (!building) return;
    _showCityTooltip(g, building);
  });

  // Boshqa joylarda click → tooltip yopilsin (document level — body bosish)
  // Faqat 1 marta document'ga ulaymiz (har renderCityGrid emas — leak xavfi)
  if (!window._cityTooltipOutsideHandlerInstalled) {
    document.addEventListener('click', function (e) {
      if (!_cityActiveTooltip) return;
      // Agar click .city-canvas ichida bo'lsa — yuqoridagi svg handler hal qiladi
      // (toggle yoki yangi bino). Bu yerda faqat tashqaridagi click'lar uchun.
      if (e.target.closest('.city-canvas')) return;
      // Tooltip ustidagi click'da ham yopamiz (pointer-events:none allaqachon,
      // lekin defensiv tekshiruv)
      if (e.target.closest('.city-bld-tooltip')) return;
      _hideCityTooltip();
    }, true);  // capture — boshqa handlerlar oldin
    window._cityTooltipOutsideHandlerInstalled = true;
  }

  // Scroll yoki zoom paytida tooltip yopiladi (bino joyi ekranda o'zgaradi)
  const wrap = container.querySelector('.city-canvas-wrap');
  if (wrap) {
    wrap.addEventListener('scroll', function () {
      if (_cityActiveTooltip) _hideCityTooltip();
    }, { passive: true });
  }
}

// ── API DATA (C4) ──
// _cityDemoData O'CHIRILDI — endi haqiqiy GET /api/city/<uid> javobi ishlatiladi.
// API javob formati (flask_routes_city.py api_city_get):
//   { ok, grid_size, buildings: [{habit_id, type, x, y, progress, stage}],
//     decorations: [...], insurance_active, insurance_until, version }
// buildings massivi renderCityBuildings() ga uzatiladi (interfeys o'zgarmagan).
// decorations — C3.3 da KEYINGA QOLDIRILGAN, hozir render qilinmaydi (professional
// SVG ikonkalar kerak). Backend (place_decoration) tayyor turadi, C6 da ulanadi.

// Oxirgi muvaffaqiyatli yuklangan shahar javobi — C5 (bino bosish) shu yerdan
// bino ma'lumotini oladi (qayta API chaqirmasdan). C4 da faqat saqlanadi.
let _cityData = null;

// ── Asosiy yuklash funksiyasi (loadTab tomonidan chaqiriladi) ──
// GET /api/city/<uid> chaqiradi. Loading spinner index.html da #city-content
// ichida allaqachon bor — fetch tugaguncha ko'rinib turadi.
async function loadCity() {
  const container = document.getElementById('city-content');
  if (!container) return;
  try {
    const res = await apiFetch('city/' + userId);
    if (!res || !res.ok) throw new Error('city_load_failed');
    _cityData = res;
    renderCityGrid(container, res);
    updateCityNameHeader(res.name);
  } catch (e) {
    _cityData = null;
    renderCityError(container);
    updateCityNameHeader(null);
  }
}

// ── Xato holati renderi (C4) ──
// API ishlamasa — soxta demo data KO'RSATILMAYDI (chalkash UX: "mening
// shahrimda nega bu binolar?"). O'rniga aniq xato + "Qayta urinish" tugma.
// Tarjima: S('msg','connection_error') — strings.js da mavjud 3 tilli kalit
// (city.* kalitlari C7 da qo'shiladi — handoff rejasi).
function renderCityError(container) {
  const msg = S('msg', 'connection_error');
  container.innerHTML = `
    <div class="city-error">
      <div class="city-error-icon">📡</div>
      <div class="city-error-msg">${msg}</div>
      <button class="city-error-btn" onclick="loadCity()">↻</button>
    </div>
  `;
}

// ── Statik isometric grid renderi (C2.1) + binolar (C4: API data) ──
// cityData — GET /api/city/<uid> javobi. cityData.buildings massivi
// renderCityBuildings() ga uzatiladi. cityData.decorations hozir ishlatilmaydi
// (C3.3 KEYINGA QOLDIRILGAN).
function renderCityGrid(container, cityData) {
  // SVG o'lchamlari — barcha kataklar to'liq sig'adigan kanvas
  // ENG ASOSIY: har bir romb cho'qqilari uchun joy ajratish kerak!
  //   - Eng chap cho'qqi: (x=0, y=29) → cx=-1160, romb chap nuqta: -1160 - 40 = -1200
  //   - Eng o'ng cho'qqi: (x=29, y=0) → cx=+1160, romb o'ng nuqta: +1160 + 40 = +1200
  //   - Eng tepa: (x=0, y=0) → cy=0 (romb tepa cho'qqisi)
  //   - Eng past: (x=29, y=29) → cy=1160, romb pastki: 1160 + 40 = 1200
  const halfW   = CITY_GRID_SIZE * (CITY_TILE_W / 2);      // 1200 — markazdan eng uzoq cx
  const halfH   = CITY_GRID_SIZE * CITY_TILE_H;            // 1200 — eng pastki cy
  // C3.5c: bino USTIDAGI label uchun tepada qo'shimcha joy. Eng yuqori bino
  //   (x=0,y=0) uchun label y ≈ cy - bh - FULL_HEIGHT - 10 ≈ -89 (manfiy).
  //   Standart viewY=-40 da label kesilardi — CITY_LABEL_HEADROOM bilan
  //   viewBox tepasi kengaytiriladi (bino tepa balandlik 84 + label + bo'shliq).
  const CITY_LABEL_HEADROOM = 110;
  // Romb cho'qqilarini ham hisobga olib, padding qo'shamiz
  const fullW   = (halfW + CITY_TILE_W / 2) * 2 + CITY_PADDING * 2;  // (1200+40)*2 + 80 = 2560
  // fullH: pastki padding + grid + tepa padding + label uchun headroom
  const fullH   = halfH + CITY_TILE_H + CITY_PADDING * 2 + CITY_LABEL_HEADROOM;  // 1430
  // viewBox markazlash: chap chetdagi rombning chap cho'qqisidan boshlanadi
  const viewX   = -(halfW + CITY_TILE_W / 2) - CITY_PADDING;  // -1280
  // viewY: standart padding + label headroom (tepada label kesilmasligi uchun)
  const viewY   = -CITY_PADDING - CITY_LABEL_HEADROOM;        // -150

  // Har bir katakni alohida <polygon> sifatida chizamiz.
  // Sabab: kelajakda C5 da har katakni alohida bosish/drop target qilish kerak,
  // shuning uchun hozirdanoq individual element strategiyasi.
  let tilesHtml = '';
  for (let y = 0; y < CITY_GRID_SIZE; y++) {
    for (let x = 0; x < CITY_GRID_SIZE; x++) {
      const cx = cityIsoX(x, y);
      const cy = cityIsoY(x, y);
      // Romb markazi: top (cx,cy) va bottom (cx, cy+H) oʻrtasi → (cx, cy + H/2)
      // Har vertex'ni markazga CITY_TILE_SHRINK bilan tortamiz:
      //   newVertex = center + (oldVertex - center) * SHRINK
      // Natija: polygon biroz kichkina, qoʻshni polygon bilan orasida gap (~3px).
      const mx = cx;
      const my = cy + CITY_TILE_H / 2;
      const dx = (CITY_TILE_W / 2) * CITY_TILE_SHRINK;
      const dy = (CITY_TILE_H / 2) * CITY_TILE_SHRINK;
      // Romb 4 cho'qqi (shrinklangan): top, right, bottom, left
      const points = [
        `${mx},${my - dy}`,         // top    (markazdan yuqoriga)
        `${mx + dx},${my}`,         // right  (markazdan o'ngga)
        `${mx},${my + dy}`,         // bottom (markazdan pastga)
        `${mx - dx},${my}`,         // left   (markazdan chapga)
      ].join(' ');
      // Checkerboard parity saqlangan (data-attribute uchun, fill bir xil oq)
      // shaxmat YOʻQ — CSS da tile-a va tile-b bir xil rang (#FFFFFF)
      const parity = (x + y) % 2 === 0 ? 'a' : 'b';
      tilesHtml += `<polygon class="city-tile city-tile-${parity}" data-x="${x}" data-y="${y}" points="${points}"/>`;
    }
  }

  // Binolar layer'i: grid kataklaridan KEYIN chiziladi (ustida ko'rinadi).
  // C4: API javobidan keladi (_cityDemoData o'chirilgan). buildings yo'q yoki
  // bo'sh bo'lsa — bo'sh string (yangi user, hali bino yo'q → faqat grid).
  const apiBuildings = (cityData && Array.isArray(cityData.buildings))
    ? cityData.buildings : [];

  // ── Yangi binolarni aniqlash (animatsiya uchun) ──
  // localStorage'dagi "ko'rilgan binolar" ro'yxati bilan solishtirish. ICHida
  // bo'lmagan har bir habit_id YANGI hisoblanadi → renderCityBuildings()
  // .city-bld--new klassini qo'shadi → CSS @keyframes pastdan ko'tariladi.
  // window._cityNewBuildingIds — global (app-city-buildings.js bir xil scope'da
  // ishlamaydi, har fayl alohida yuklanadi — window orqali ulashish — Qoida #13).
  // _markBuildingSeen() animatsiya tugagach (setTimeout pastda) chaqiriladi.
  const seenSet = _getCitySeenBuildings();
  const newIds = new Set();
  for (const b of apiBuildings) {
    if (b && b.habit_id != null && !seenSet.has(b.habit_id)) {
      newIds.add(b.habit_id);
    }
  }
  window._cityNewBuildingIds = newIds;  // renderCityBuildings shu yerdan o'qiydi

  const buildingsHtml = renderCityBuildings(apiBuildings);

  container.innerHTML = `
    <div class="city-canvas-wrap">
      <svg class="city-canvas"
           width="${fullW}" height="${fullH}"
           viewBox="${viewX} ${viewY} ${fullW} ${fullH}"
           xmlns="http://www.w3.org/2000/svg"
           aria-label="City grid">
        ${tilesHtml}
        ${buildingsHtml}
      </svg>
    </div>
  `;

  // Auto-scroll grid markaziga (Forest/Hay Day stilida — foydalanuvchi
  // tab'ga kirganda darhol shahar markazini ko'radi, cho'qqilarni emas).
  // requestAnimationFrame — DOM render tugagach scroll qilish uchun.
  requestAnimationFrame(() => {
    const wrap = container.querySelector('.city-canvas-wrap');
    if (!wrap) return;
    wrap.scrollLeft = (wrap.scrollWidth  - wrap.clientWidth)  / 2;
    wrap.scrollTop  = (wrap.scrollHeight - wrap.clientHeight) / 2;
  });

  // C5: bino bilan interaktivlik (long-press → bino ko'chirish) — keyingi qadamda
  //   shu yerga handler ulanadi. .city-bld <g> da data-habit-id atributi tayyor
  //   turadi (app-city-buildings.js) — move_item API'ga habit_id yuborish uchun.
  if (typeof initCityMoveHandlers === 'function') {
    initCityMoveHandlers(container);
  }

  // ZOOM (yangi): pinch handler'larni ulash + saqlangan zoom darajasini qaytarish.
  // _initCityPinch CAPTURE rejimida ulanadi → app-city-move.js touchstart'idan
  // OLDIN ishlaydi (2 barmoq bo'lsa, drag handler chaqirilmaydi — Qoida #09).
  // applyCityZoom — _cityZoom global state (boshqa tab'dan qaytganda saqlangan).
  _initCityPinch(container);
  applyCityZoom();

  // TAP TOOLTIP (yangi C6): bino qisqa bosilsa info pop-up. Drag va pinch bilan
  // to'qnashuv yo'q — browser drag/pinch paytida click event'ni emit qilmaydi.
  _initCityTap(container);

  // ── Yangi bino animatsiyasi tugagach: "ko'rilgan" deb belgilash + klassni
  //    DOM'dan olib tashlash. Sabab: agar klass qolib ketsa, transform: scale()
  //    qiymati `.city-bld--new { animation }` bilan kelajakda boshqa transform'larni
  //    (drag paytida ghost yoki hover effekti) buzishi mumkin. Animatsiya tugagach
  //    klass kerak emas — toza DOM. (Qoida #11 — tozalaydigan joy ishlayaptimi.)
  if (newIds.size > 0) {
    setTimeout(() => {
      for (const id of newIds) {
        _markBuildingSeen(id);
        // DOM'dan klassni olib tashlash (agar bino hali ham SVG'da bo'lsa)
        const el = document.querySelector(`.city-bld[data-habit-id="${id}"]`);
        if (el) el.classList.remove('city-bld--new');
      }
    }, CITY_BLD_ANIM_DURATION + 50);  // +50ms — animatsiya to'liq tugaganiga ishonch
  }
}

// ════════════════════════════════════════════════
//  BINOLAR — app-city-buildings.js ga AJRATILGAN (Qoida #24)
// ════════════════════════════════════════════════
// cityBuildingStage(), cityBuildingSVG(), renderCityBuildings() va bino shakl
// konfiguratsiyalari app-city-buildings.js da. Bu fayl ulardan FAQAT renderCityGrid
// ichida foydalanadi (yuqorida `renderCityBuildings(apiBuildings)`).
// index.html da app-city-buildings.js shu fayldan KEYIN yuklanadi — chunki u shu
// yerdagi konstantalarga (CITY_TILE_H, CITY_BLD_*, cityIsoX/Y) bog'liq.

// ── Eslatma kelajakdagi bosqichlar uchun ──
// PHASE C2.2: touch pan — .city-canvas-wrap overflow:auto + touch-action:pan-x pan-y
//             orqali browser native scroll bilan amalga oshirilgan (alohida kod yo'q)
// PHASE C2.3: ✅ zoom (+/- tugmalar + pinch) — SHU YERDA, CSS transform: scale()
//             .city-canvas ga. Oraliq: 0.6x — 1.6x, qadam: 0.1x
// PHASE C3.1: ✅ demo binolar (5 stage, oq clay render)
// PHASE C3.2: ✅ shakl-asosida bino turlari (app-city-buildings.js)
// PHASE C3.3: 5 dekoratsiya — KEYINGA QOLDIRILGAN (professional SVG ikonkalar kerak)
// PHASE C3.4: ✅ premium CSS polish (soyalar, 3D effekt)
// PHASE C4:   ✅ loadCity() async — GET /api/city/<uid> (_cityDemoData o'chirildi) — SHU YERDA
// PHASE C5:   ✅ find_empty_slot markazga yig'ish (backend) + gap qoidasi.
//             ✅ Long-press → bino ko'chirish (drag & drop) — app-city-move.js da.
//             Bino bosish modali (change_type) — A varianti bilan olib tashlangan.
// PHASE C6:   renderDecorationsShop() — dekoratsiya bozor modali (buy_decoration, buy_insurance)
// PHASE C7:   tarjimalar strings.js'ga qo'shiladi (10 bino + 5 dekoratsiya nomlari, city.* kalitlar)
// PHASE C8:   ✅ Shahar nomi (yuqori chap header + modal) — SHU YERDA pastda

// ════════════════════════════════════════════════
//  PHASE C8: SHAHAR NOMI (yuqori chap burchakda)
// ════════════════════════════════════════════════
// Vazifa: foydalanuvchi shaharga nom bera oladi. Tahrirlanadi.
// Markup: index.html #city-name-header (tugma) + #city-name-modal-overlay (modal)
// Backend: POST /api/city/<uid>/rename (flask_routes_city.py)
// Strings: city.name_* kalitlar (strings.js)

// ── Header matnini yangilash ──
// loadCity() muvaffaqiyatda chaqiradi. name=null/'' → placeholder (is-empty klassi).
// name=string → toza matn ko'rsatadi. textContent ishlatamiz (XSS himoyasi —
// backend ham tozalaydi, lekin frontend ham doim toza qaysi).
function updateCityNameHeader(name) {
  const btn = document.getElementById('city-name-header');
  const display = document.getElementById('city-name-display');
  if (!btn || !display) return;

  if (name && typeof name === 'string' && name.trim()) {
    display.textContent = name;
    btn.classList.remove('is-empty');
  } else {
    display.textContent = S('city', 'name_placeholder') || 'Shahringizni nomlang!';
    btn.classList.add('is-empty');
  }
}

// ── Modal ochish ──
// Tugmalar matni va placeholder strings.js'dan to'ldiriladi (har til o'zgarganda
// modal qayta ochilganda yangilanadi). Input qiymati joriy nom bilan to'ldiriladi
// (agar bor bo'lsa) — foydalanuvchi tahrir qila olishi uchun.
function openCityNameModal() {
  const overlay = document.getElementById('city-name-modal-overlay');
  const input = document.getElementById('city-name-modal-input');
  const titleEl = document.getElementById('city-name-modal-title');
  const hintEl = document.getElementById('city-name-modal-hint');
  const saveBtn = document.getElementById('city-name-modal-save');
  const cancelBtn = document.getElementById('city-name-modal-cancel');
  const errorEl = document.getElementById('city-name-modal-error');
  if (!overlay || !input) return;

  // Tarjimalarni to'ldirish
  if (titleEl)  titleEl.textContent  = S('city', 'name_modal_title')  || 'Shahar nomi';
  if (hintEl)   hintEl.textContent   = S('city', 'name_modal_hint')   || '';
  if (saveBtn)  saveBtn.textContent  = S('city', 'name_modal_save')   || 'Saqlash';
  if (cancelBtn)cancelBtn.textContent= S('city', 'name_modal_cancel') || 'Bekor';
  if (errorEl)  errorEl.textContent  = '';

  // Joriy nom (agar bor bo'lsa) — _cityData keshidan
  const currentName = (_cityData && typeof _cityData.name === 'string') ? _cityData.name : '';
  input.value = currentName;

  overlay.classList.add('is-open');

  // Focus input — kichik delay (transform animatsiyasi tugasin)
  setTimeout(() => {
    try { input.focus(); input.select(); } catch (e) {}
  }, 200);
}

// ── Modal yopish ──
function closeCityNameModal() {
  const overlay = document.getElementById('city-name-modal-overlay');
  if (!overlay) return;
  overlay.classList.remove('is-open');
}

// ── Saqlash: input qiymatini POST qiladi ──
// Validation frontend'da ham qiladi (UX — backend javobini kutmasdan) lekin
// backend ham tozalaydi (xavfsizlik — frontend bypass qilinmagan bo'lsin).
async function saveCityNameFromInput() {
  const input = document.getElementById('city-name-modal-input');
  const errorEl = document.getElementById('city-name-modal-error');
  const saveBtn = document.getElementById('city-name-modal-save');
  if (!input) return;

  const value = (input.value || '').trim();

  // Frontend validation
  if (!value) {
    // Til bo'yicha xato xabari (backend ham qaytaradi, lekin server urinish keraksiz)
    if (errorEl) {
      const langErrMap = {
        uz: "Nom bo'sh bo'lmasin",
        ru: 'Имя не может быть пустым',
        en: 'Name cannot be empty',
      };
      const lang = (typeof currentLang === 'string' && langErrMap[currentLang]) ? currentLang : 'uz';
      errorEl.textContent = langErrMap[lang];
    }
    return;
  }

  if (value.length > 30) {
    if (errorEl) {
      const langErrMap = {
        uz: 'Juda uzun (30 belgidan ko\u2018p emas)',
        ru: 'Слишком длинно (не более 30 символов)',
        en: 'Too long (max 30 characters)',
      };
      const lang = (typeof currentLang === 'string' && langErrMap[currentLang]) ? currentLang : 'uz';
      errorEl.textContent = langErrMap[lang];
    }
    return;
  }

  // Saqlash tugmasi vaqtinchalik disable (double-click oldini olish)
  if (saveBtn) saveBtn.setAttribute('disabled', 'true');

  try {
    const res = await apiFetch('city/' + userId + '/rename', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: value }),
    });

    if (res && res.ok) {
      // Muvaffaqiyat: keshni yangilash + header'ni yangilash + modal yopish
      if (_cityData) _cityData.name = res.name;
      updateCityNameHeader(res.name);
      closeCityNameModal();

      // Toast (agar mavjud bo'lsa) — boshqa joylardagi pattern bilan bir xil
      if (typeof showToast === 'function') {
        showToast(S('city', 'name_saved') || '\u2705');
      }
    } else {
      // Backend xato xabarini ko'rsatish
      if (errorEl) errorEl.textContent = (res && res.error) ? res.error : (S('msg', 'connection_error') || 'Error');
    }
  } catch (e) {
    if (errorEl) errorEl.textContent = S('msg', 'connection_error') || 'Connection error';
  } finally {
    if (saveBtn) saveBtn.removeAttribute('disabled');
  }
}
