// ==============================================
// app-city.js — Shahar sahifasi (PHASE C2.1: statik 20×20 isometric grid)
// ==============================================
// Bog'liqlik:
//   - strings.js (S() funksiya — tarjima; C2.1 da ishlatilmaydi, C3+ da kerak)
//   - app-core.js (loaded state — sahifa yuklanganini belgilash)
//
// PHASE C2.1 vazifasi: 20×20 = 400 katak isometric grid SVG sifatida render bo'ladi.
// Pan/zoom YO'Q (C2.2/C2.3 da keladi), binolar YO'Q (C3 da), API YO'Q (C4 da).
// PHASE C3+ da bu fayl kengaytiriladi (binolar, dekoratsiyalar, drag&drop).
// ==============================================

// ── ISOMETRIC GRID KONSTANTLARI (Qoida #17 — magic number'larni markazlash) ──
// Klassik 2:1 isometric nisbat — eng keng tarqalgan va eng tabiiy ko'rinish.
// C2.3 (zoom) bularni dinamik o'zgartiradi, hozircha static.
const CITY_GRID_SIZE = 20;        // 20×20 = 400 katak (backend CITY_GRID_SIZE bilan moslangan)
const CITY_TILE_W    = 80;        // Romb kenglik (px)
const CITY_TILE_H    = 40;        // Romb balandlik (px) — 2:1 nisbat
const CITY_PADDING   = 40;        // SVG ichida atrof bo'shliq

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

// ── Asosiy yuklash funksiyasi (loadTab tomonidan chaqiriladi) ──
async function loadCity() {
  const container = document.getElementById('city-content');
  if (!container) return;
  renderCityGrid(container);
}

// ── Statik isometric grid renderi (C2.1) ──
function renderCityGrid(container) {
  // SVG o'lchamlari — barcha kataklar to'liq sig'adigan kanvas
  // ENG ASOSIY: har bir romb cho'qqilari uchun joy ajratish kerak!
  //   - Eng chap cho'qqi: (x=0, y=19) → cx=-760, romb chap nuqta: -760 - 40 = -800
  //   - Eng o'ng cho'qqi: (x=19, y=0) → cx=+760, romb o'ng nuqta: +760 + 40 = +800
  //   - Eng tepa: (x=0, y=0) → cy=0 (romb tepa cho'qqisi)
  //   - Eng past: (x=19, y=19) → cy=760, romb pastki: 760 + 40 = 800
  const halfW   = CITY_GRID_SIZE * (CITY_TILE_W / 2);      // 800 — markazdan eng uzoq cx
  const halfH   = CITY_GRID_SIZE * CITY_TILE_H;            // 800 — eng pastki cy
  // Romb cho'qqilarini ham hisobga olib, padding qo'shamiz
  const fullW   = (halfW + CITY_TILE_W / 2) * 2 + CITY_PADDING * 2;  // (800+40)*2 + 80 = 1760
  const fullH   = halfH + CITY_TILE_H + CITY_PADDING * 2;            // 800 + 40 + 80 = 920
  // viewBox markazlash: chap chetdagi rombning chap cho'qqisidan boshlanadi
  const viewX   = -(halfW + CITY_TILE_W / 2) - CITY_PADDING;  // -880
  const viewY   = -CITY_PADDING;                              // -40

  // Har bir katakni alohida <polygon> sifatida chizamiz.
  // Sabab: kelajakda C5 da har katakni alohida bosish/drop target qilish kerak,
  // shuning uchun hozirdanoq individual element strategiyasi.
  let tilesHtml = '';
  for (let y = 0; y < CITY_GRID_SIZE; y++) {
    for (let x = 0; x < CITY_GRID_SIZE; x++) {
      const cx = cityIsoX(x, y);
      const cy = cityIsoY(x, y);
      // Romb 4 cho'qqi: top, right, bottom, left
      const points = [
        `${cx},${cy}`,                                    // top
        `${cx + CITY_TILE_W / 2},${cy + CITY_TILE_H / 2}`, // right
        `${cx},${cy + CITY_TILE_H}`,                       // bottom
        `${cx - CITY_TILE_W / 2},${cy + CITY_TILE_H / 2}`, // left
      ].join(' ');
      // Checkerboard pattern: (x+y) juft → light, toq → slightly darker
      // Bu Forest stilidagi yengil naqsh — ko'z chizmaydi, lekin grid yaqqol ko'rinadi
      const parity = (x + y) % 2 === 0 ? 'a' : 'b';
      tilesHtml += `<polygon class="city-tile city-tile-${parity}" data-x="${x}" data-y="${y}" points="${points}"/>`;
    }
  }

  container.innerHTML = `
    <div class="city-canvas-wrap">
      <svg class="city-canvas"
           width="${fullW}" height="${fullH}"
           viewBox="${viewX} ${viewY} ${fullW} ${fullH}"
           xmlns="http://www.w3.org/2000/svg"
           aria-label="City grid">
        ${tilesHtml}
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
}

// ── Eslatma kelajakdagi bosqichlar uchun ──
// PHASE C2.2: touch pan (drag bilan kamera siljishi)
// PHASE C2.3: pinch-to-zoom (yoki tugmalar)
// PHASE C2.4: virtual rendering (faqat ekrandagi katak chiziladi — agar kerak bo'lsa)
// PHASE C3:   renderBuildings(buildings) — 10 bino × 5 stage SVG
// PHASE C4:   loadCityFromAPI() — GET /api/city/<uid>
// PHASE C5:   handleBuildingDrag(), handleBuildingClick() — interaktivlik
// PHASE C6:   renderDecorationsShop() — bozor modal
// PHASE C7:   tarjimalar strings.js'ga qo'shiladi
// PHASE C8:   premium CSS polish (beige/gold accent, 3D rendering)
