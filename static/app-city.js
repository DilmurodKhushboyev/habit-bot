// ==============================================
// app-city.js — Shahar sahifasi (PHASE C2.2: touch pan + inertia)
// ==============================================
// Bog'liqlik:
//   - strings.js (S() funksiya — tarjima; C2.2 da ishlatilmaydi, C3+ da kerak)
//   - app-core.js (loaded state — sahifa yuklanganini belgilash; switchTab orqali
//                  loaded.city = false bilan har safar qayta yuklanadi → markazga qaytadi)
//
// PHASE C2.2 vazifasi: drag-based pan (qo'l bilan kameraviy siljitish) + inertia
// (barmoq ko'tarilgandan keyin smooth davom etish) + boundary clamp (chetga yetganda to'xtash).
// Browser default scroll (overflow: auto) → SVG <g transform="translate(panX, panY)"> wrapper.
// PHASE C2.3 da bu fayl pinch-zoom bilan kengaytiriladi (scale qo'shiladi).
// ==============================================

// ── ISOMETRIC GRID KONSTANTLARI (Qoida #17 — magic number'larni markazlash) ──
// Klassik 2:1 isometric nisbat — eng keng tarqalgan va eng tabiiy ko'rinish.
// C2.3 (zoom) bularni dinamik o'zgartiradi, hozircha static.
const CITY_GRID_SIZE = 30;        // 30×30 = 900 katak
const CITY_TILE_W    = 80;        // Romb kenglik (px)
const CITY_TILE_H    = 40;        // Romb balandlik (px) — 2:1 nisbat
const CITY_PADDING   = 40;        // SVG ichida atrof bo'shliq

// ── PAN/INERTIA KONSTANTLARI (PHASE C2.2) ──
// Forest/Hay Day uslubi: barmoq ko'tarilgandan keyin kamera smooth davom etadi.
const PAN_FRICTION      = 0.92;   // Har frame velocity kamayishi (0.92 = ~30 frame'da to'xtaydi)
const MIN_VELOCITY      = 0.5;    // Bu darajadan past bo'lsa — inertia to'xtaydi (px/frame)
const VELOCITY_SAMPLES  = 5;      // Velocity hisoblash uchun oxirgi N ta touchmove namunasi
const MAX_OVERSCROLL    = 100;    // Grid chetidan tashqari maksimal siljish (px) — soft chegara
const TIME_WINDOW_MS    = 100;    // Velocity hisoblash uchun vaqt oynasi (oxirgi 100ms harakat)

// ── Isometric koordinata transformatsiyasi ──
// Standart isometric formula: (x, y) grid → ekrandagi (sx, sy) pozitsiya
//   sx = (x - y) * (TILE_W / 2)
//   sy = (x + y) * (TILE_H / 2)
function cityIsoX(x, y) {
  return (x - y) * (CITY_TILE_W / 2);
}
function cityIsoY(x, y) {
  return (x + y) * (CITY_TILE_H / 2);
}

// ── Pan state (modul ichida, har renderda yangidan boshlanadi) ──
// Sabab (§21): har shahar tabga kirishda fresh state kerak — eski velocity yoki pan
// pozitsiyasi qolib ketmasligi uchun. loadCity() ichida resetlanadi.
let _cityPanX = 0;          // Joriy gorizontal siljish (px)
let _cityPanY = 0;          // Joriy vertikal siljish (px)
let _cityVelX = 0;          // Inertia uchun gorizontal tezlik (px/frame)
let _cityVelY = 0;          // Inertia uchun vertikal tezlik (px/frame)
let _cityDragging = false;  // Hozir barmoq bosib turibdimi?
let _cityLastX = 0;         // Oxirgi touchmove X koordinatasi
let _cityLastY = 0;         // Oxirgi touchmove Y koordinatasi
let _citySamples = [];      // Oxirgi N ta {x, y, t} — velocity hisoblash uchun
let _cityRafId = null;      // requestAnimationFrame ID (inertia loop to'xtatish uchun)
let _cityCameraEl = null;   // SVG <g> elementi cache (har frame DOM query qilmaslik uchun)
let _cityBounds = null;     // {minPanX, maxPanX, minPanY, maxPanY} — boundary clamp uchun

// ── Asosiy yuklash funksiyasi (loadTab tomonidan chaqiriladi) ──
async function loadCity() {
  const container = document.getElementById('city-content');
  if (!container) return;
  // Eski inertia loop ishlayotgan bo'lsa to'xtatamiz (tab o'zgarganda)
  if (_cityRafId) { cancelAnimationFrame(_cityRafId); _cityRafId = null; }
  renderCityGrid(container);
}

// ── Statik isometric grid renderi (C2.2 — endi <g> wrapper bilan) ──
function renderCityGrid(container) {
  // SVG o'lchamlari — barcha kataklar to'liq sig'adigan kanvas
  // ENG ASOSIY: har bir romb cho'qqilari uchun joy ajratish kerak!
  //   - Eng chap cho'qqi: (x=0, y=29) → cx=-1160, romb chap nuqta: -1160 - 40 = -1200
  //   - Eng o'ng cho'qqi: (x=29, y=0) → cx=+1160, romb o'ng nuqta: +1160 + 40 = +1200
  //   - Eng tepa: (x=0, y=0) → cy=0
  //   - Eng past: (x=29, y=29) → cy=1160, romb pastki: 1160 + 40 = 1200
  const halfW   = CITY_GRID_SIZE * (CITY_TILE_W / 2);      // 1200
  const halfH   = CITY_GRID_SIZE * CITY_TILE_H;            // 1200
  const fullW   = (halfW + CITY_TILE_W / 2) * 2 + CITY_PADDING * 2;  // 2560
  const fullH   = halfH + CITY_TILE_H + CITY_PADDING * 2;            // 1320
  const viewX   = -(halfW + CITY_TILE_W / 2) - CITY_PADDING;  // -1280
  const viewY   = -CITY_PADDING;                              // -40

  // Har bir katakni alohida <polygon> sifatida chizamiz (C5 drop target uchun).
  let tilesHtml = '';
  for (let y = 0; y < CITY_GRID_SIZE; y++) {
    for (let x = 0; x < CITY_GRID_SIZE; x++) {
      const cx = cityIsoX(x, y);
      const cy = cityIsoY(x, y);
      const points = [
        `${cx},${cy}`,
        `${cx + CITY_TILE_W / 2},${cy + CITY_TILE_H / 2}`,
        `${cx},${cy + CITY_TILE_H}`,
        `${cx - CITY_TILE_W / 2},${cy + CITY_TILE_H / 2}`,
      ].join(' ');
      const parity = (x + y) % 2 === 0 ? 'a' : 'b';
      tilesHtml += `<polygon class="city-tile city-tile-${parity}" data-x="${x}" data-y="${y}" points="${points}"/>`;
    }
  }

  // C2.2 yangiligi: SVG ichida <g class="city-camera"> wrapper — pan transform shu g'da o'rnatiladi.
  // Sabab (§21): butun SVG'ni transform qilmaymiz, chunki kelajakda (C3) HUD elementlar
  // (zoom tugmalari, mini-map) wrapper tashqarisida qoladi — ular pan qilinmaydi.
  container.innerHTML = `
    <div class="city-canvas-wrap">
      <svg class="city-canvas"
           width="${fullW}" height="${fullH}"
           viewBox="${viewX} ${viewY} ${fullW} ${fullH}"
           xmlns="http://www.w3.org/2000/svg"
           aria-label="City grid">
        <g class="city-camera" transform="translate(0, 0)">
          ${tilesHtml}
        </g>
      </svg>
    </div>
  `;

  // DOM render tugagach — pan tizimini ishga tushiramiz
  requestAnimationFrame(() => {
    const wrap = container.querySelector('.city-canvas-wrap');
    if (!wrap) return;
    _cityCameraEl = wrap.querySelector('.city-camera');
    if (!_cityCameraEl) return;

    // Boundary clamp chegaralari (§17 — markazlash):
    //   SVG fullW=2560 px wrap clientWidth (taxminan 360px) dan ancha katta.
    //   Markazda: panX=0 → SVG markazi ekran markazida (viewBox -1280 dan boshlanadi).
    //   Chap chetga yetish: panX = -fullW/2 + clientWidth/2 = -1280 + 180 = -1100
    //   O'ng chetga yetish: panX = +fullW/2 - clientWidth/2 = +1100
    //   Soft overscroll: MAX_OVERSCROLL qo'shimcha siljish mumkin.
    const cw = wrap.clientWidth;
    const ch = wrap.clientHeight;
    _cityBounds = {
      // Pan diapazoni: foydalanuvchi grid'ning eng chap nuqtasini ekranning o'ng tomonigacha
      // tortmasin — qiymatlar shunday cheklanadi
      minPanX: -(fullW / 2) + cw / 2 - MAX_OVERSCROLL,
      maxPanX:  (fullW / 2) - cw / 2 + MAX_OVERSCROLL,
      minPanY: -(fullH / 2) + ch / 2 - MAX_OVERSCROLL,
      maxPanY:  (fullH / 2) - ch / 2 + MAX_OVERSCROLL,
    };

    // Boshlang'ich pozitsiya: markaz (panX=0, panY=0 → SVG markazi ekran markazida)
    _cityPanX = 0;
    _cityPanY = 0;
    _cityVelX = 0;
    _cityVelY = 0;
    _cityDragging = false;
    _citySamples = [];
    _applyCityTransform();

    // Touch handlerlarni ulash (har renderda yangi wrap → yangi handler)
    _attachCityTouchHandlers(wrap);
  });
}

// ── Transform qo'llash (har frame yoki touchmove'da) ──
function _applyCityTransform() {
  if (!_cityCameraEl) return;
  _cityCameraEl.setAttribute('transform', `translate(${_cityPanX}, ${_cityPanY})`);
}

// ── Boundary clamp: pan qiymatlarini diapazon ichida ushlab turish ──
function _clampCityPan() {
  if (!_cityBounds) return;
  if (_cityPanX < _cityBounds.minPanX) _cityPanX = _cityBounds.minPanX;
  if (_cityPanX > _cityBounds.maxPanX) _cityPanX = _cityBounds.maxPanX;
  if (_cityPanY < _cityBounds.minPanY) _cityPanY = _cityBounds.minPanY;
  if (_cityPanY > _cityBounds.maxPanY) _cityPanY = _cityBounds.maxPanY;
}

// ── Touch handlerlar (§21 — pan logikasi) ──
function _attachCityTouchHandlers(wrap) {
  wrap.addEventListener('touchstart', _cityOnTouchStart, { passive: false });
  wrap.addEventListener('touchmove',  _cityOnTouchMove,  { passive: false });
  wrap.addEventListener('touchend',   _cityOnTouchEnd,   { passive: true  });
  wrap.addEventListener('touchcancel',_cityOnTouchEnd,   { passive: true  });
}

function _cityOnTouchStart(e) {
  if (e.touches.length !== 1) return;  // C2.3 da multi-touch (pinch) qo'shiladi
  // Eski inertia loop'ni to'xtatamiz — foydalanuvchi yangi drag boshladi
  if (_cityRafId) { cancelAnimationFrame(_cityRafId); _cityRafId = null; }
  _cityDragging = true;
  _cityVelX = 0;
  _cityVelY = 0;
  const t = e.touches[0];
  _cityLastX = t.clientX;
  _cityLastY = t.clientY;
  _citySamples = [{ x: t.clientX, y: t.clientY, t: performance.now() }];
}

function _cityOnTouchMove(e) {
  if (!_cityDragging || e.touches.length !== 1) return;
  // §21 — preventDefault: browser default scroll/swipe'larni butunlay bloklash
  // (touch-action: none CSS bilan birgalikda — ikki qatlamli himoya)
  e.preventDefault();
  const t = e.touches[0];
  const dx = t.clientX - _cityLastX;
  const dy = t.clientY - _cityLastY;
  _cityPanX += dx;
  _cityPanY += dy;
  _clampCityPan();
  _applyCityTransform();
  _cityLastX = t.clientX;
  _cityLastY = t.clientY;
  // Velocity uchun namuna saqlaymiz (oxirgi N ta)
  _citySamples.push({ x: t.clientX, y: t.clientY, t: performance.now() });
  if (_citySamples.length > VELOCITY_SAMPLES) _citySamples.shift();
}

function _cityOnTouchEnd(e) {
  if (!_cityDragging) return;
  _cityDragging = false;
  // Velocity hisoblash: oxirgi TIME_WINDOW_MS ichidagi harakatga qarab (px/frame, 60fps)
  // Formula: (oxirgi.pos - boshlang'ich.pos) / (frame'lar soni) — px/16.67ms
  const now = performance.now();
  // TIME_WINDOW_MS ichidagi eng eski namunani topamiz
  let oldest = _citySamples[0];
  for (let i = _citySamples.length - 1; i >= 0; i--) {
    if (now - _citySamples[i].t > TIME_WINDOW_MS) break;
    oldest = _citySamples[i];
  }
  const last = _citySamples[_citySamples.length - 1];
  const dt = last.t - oldest.t;
  if (dt > 10) {  // Juda qisqa vaqt — velocity ishonchsiz
    // px/ms → px/frame (16.67ms)
    _cityVelX = (last.x - oldest.x) / dt * 16.67;
    _cityVelY = (last.y - oldest.y) / dt * 16.67;
  } else {
    _cityVelX = 0;
    _cityVelY = 0;
  }
  // Inertia loop ishga tushiramiz (agar velocity yetarli bo'lsa)
  if (Math.abs(_cityVelX) > MIN_VELOCITY || Math.abs(_cityVelY) > MIN_VELOCITY) {
    _cityInertiaLoop();
  }
}

// ── Inertia loop: barmoq ko'tarilgandan keyin smooth davom etish ──
function _cityInertiaLoop() {
  _cityPanX += _cityVelX;
  _cityPanY += _cityVelY;
  _clampCityPan();
  _applyCityTransform();
  _cityVelX *= PAN_FRICTION;
  _cityVelY *= PAN_FRICTION;
  // To'xtatish sharti: ikkala velocity ham minimum darajadan past
  if (Math.abs(_cityVelX) < MIN_VELOCITY && Math.abs(_cityVelY) < MIN_VELOCITY) {
    _cityRafId = null;
    return;
  }
  _cityRafId = requestAnimationFrame(_cityInertiaLoop);
}

// ── Eslatma kelajakdagi bosqichlar uchun ──
// PHASE C2.3: pinch-to-zoom — _cityScale state qo'shiladi, touchstart 2 barmoq tekshiriladi
// PHASE C2.4: virtual rendering (agar 900 katak sekin bo'lsa — faqat ekrandagilar chiziladi)
// PHASE C3:   renderBuildings(buildings) — 10 bino × 5 stage SVG (city-camera <g> ichiga qo'shiladi)
// PHASE C4:   loadCityFromAPI() — GET /api/city/<uid>
// PHASE C5:   handleBuildingDrag(), handleBuildingClick() — interaktivlik
// PHASE C6:   renderDecorationsShop() — bozor modal
// PHASE C7:   tarjimalar strings.js'ga qo'shiladi
// PHASE C8:   premium CSS polish (beige/gold accent, 3D rendering)
