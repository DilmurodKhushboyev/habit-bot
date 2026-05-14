// ==============================================
// app-city.js — Shahar sahifasi (PHASE C3.1: grid + demo binolar)
// ==============================================
// Bog'liqlik:
//   - strings.js (S() funksiya — tarjima; C3.1 da ishlatilmaydi, C7 da kerak)
//   - app-core.js (loaded state — sahifa yuklanganini belgilash)
//   - config.py BUILDING_STAGE_THRESHOLDS bilan SINXRON (Qoida #11)
//
// PHASE C2.1: 30×30 = 900 katak isometric grid (statik, scroll bilan).
// PHASE C2.2/C2.3 (pan/zoom): YAGNI sababli o'tkazib yuborilgan.
// PHASE C3.1: demo binolar (2 tur — house/mosque, 5 stage), monoxrom oq clay
//             render uslubi (3 yuzli izometrik kublar, soya bilan hajm).
//             API YO'Q (C4 da demo data → GET /api/city/<uid> bilan almashtiriladi).
// PHASE C3.2+ da qolgan 8 bino + dekoratsiyalar qo'shiladi.
// ==============================================

// ── ISOMETRIC GRID KONSTANTLARI (Qoida #17 — magic number'larni markazlash) ──
// Klassik 2:1 isometric nisbat — eng keng tarqalgan va eng tabiiy ko'rinish.
// C2.3 (zoom) bularni dinamik o'zgartiradi, hozircha static.
const CITY_GRID_SIZE = 30;        // 30×30 = 900 katak (C2.1: 20→30 ga kengaytirildi)
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

// ── BINO STAGE KONSTANTLARI (Qoida #11 — backend bilan SINXRON) ──
// config.py BUILDING_STAGE_THRESHOLDS = [13, 26, 39, 52, 66]
// Bu chegaralar progress (kun) → stage (0-4) ni aniqlaydi.
// Birini o'zgartirsangiz — config.py ni ham (va aksincha).
const CITY_STAGE_THRESHOLDS = [13, 26, 39, 52, 66];

// Bino vizual o'lchamlari (izometrik kub) — Qoida #17 magic number markazlash
// Kub asosi katak romb kengligidan ozgina kichik (binolar orasida bo'shliq qoladi).
const CITY_BLD_BASE_W = 60;   // kub asos kengligi (px) — CITY_TILE_W=80 dan kichik
const CITY_BLD_BASE_H = 30;   // kub asos balandligi (px) — 2:1 nisbat saqlanadi
// Stage bo'yicha kub balandligi (vertikal — px). Stage 0 past poydevor, 4 to'liq.
const CITY_BLD_HEIGHTS = [14, 34, 58, 84, 84];  // stage 0..4 balandlik

// ── DEMO DATA (C4 da GET /api/city/<uid> javobi bilan almashtiriladi) ──
// Backend formatida: buildings massivi. Har bino: {habit_id, type, x, y, progress}.
// progress (0-66 kun) → cityBuildingStage() orqali stage'ga aylantiriladi.
// Grid markazi 14-16 atrofida — auto-scroll shu yerni ko'rsatadi.
const _cityDemoData = {
  buildings: [
    { habit_id: "demo1", type: "house",  x: 14, y: 14, progress: 5  },  // stage 0
    { habit_id: "demo2", type: "house",  x: 16, y: 15, progress: 33 },  // stage 2
    { habit_id: "demo3", type: "mosque", x: 13, y: 16, progress: 48 },  // stage 3
    { habit_id: "demo4", type: "mosque", x: 15, y: 13, progress: 66 },  // stage 4
    { habit_id: "demo5", type: "house",  x: 17, y: 17, progress: 20 },  // stage 1
  ],
};

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
  //   - Eng chap cho'qqi: (x=0, y=29) → cx=-1160, romb chap nuqta: -1160 - 40 = -1200
  //   - Eng o'ng cho'qqi: (x=29, y=0) → cx=+1160, romb o'ng nuqta: +1160 + 40 = +1200
  //   - Eng tepa: (x=0, y=0) → cy=0 (romb tepa cho'qqisi)
  //   - Eng past: (x=29, y=29) → cy=1160, romb pastki: 1160 + 40 = 1200
  const halfW   = CITY_GRID_SIZE * (CITY_TILE_W / 2);      // 1200 — markazdan eng uzoq cx
  const halfH   = CITY_GRID_SIZE * CITY_TILE_H;            // 1200 — eng pastki cy
  // Romb cho'qqilarini ham hisobga olib, padding qo'shamiz
  const fullW   = (halfW + CITY_TILE_W / 2) * 2 + CITY_PADDING * 2;  // (1200+40)*2 + 80 = 2560
  const fullH   = halfH + CITY_TILE_H + CITY_PADDING * 2;            // 1200 + 40 + 80 = 1320
  // viewBox markazlash: chap chetdagi rombning chap cho'qqisidan boshlanadi
  const viewX   = -(halfW + CITY_TILE_W / 2) - CITY_PADDING;  // -1280
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

  // Binolar layer'i: grid kataklaridan KEYIN chiziladi (ustida ko'rinadi).
  // C3.1 da demo data, C4 da API javobidan keladi.
  const buildingsHtml = renderCityBuildings(_cityDemoData.buildings);

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
}

// ════════════════════════════════════════════════
//  PHASE C3.1 — BINOLAR (demo data, monoxrom oq clay render)
// ════════════════════════════════════════════════

// ── progress (kun) → stage (0-4) ──
// config.py BUILDING_STAGE_THRESHOLDS bilan SINXRON (Qoida #11).
// progress <= 13 → stage 0, <= 26 → 1, <= 39 → 2, <= 52 → 3, qolgani → 4.
function cityBuildingStage(progress) {
  const p = Math.max(0, Math.min(CITY_STAGE_THRESHOLDS[4], progress || 0));
  for (let s = 0; s < CITY_STAGE_THRESHOLDS.length; s++) {
    if (p <= CITY_STAGE_THRESHOLDS[s]) return s;
  }
  return 4;  // xavfsizlik fallback (p > 66 bo'lsa ham)
}

// ── Bitta bino SVG'si (izometrik kub, 3 yuz: tepa + chap + o'ng) ──
// type: bino turi (config.py BUILDING_TYPES kaliti — C3.1 da house/mosque)
// stage: 0-4 (cityBuildingStage natijasi)
// cx, cy: katak rombning MARKAZIY nuqtasi (cityIsoX/cityIsoY + romb markazi)
// Qaytaradi: <g> ichida polygonlar (tepa/chap/o'ng yuz) — monoxrom oq, soya bilan hajm.
function cityBuildingSVG(type, stage, cx, cy) {
  const h  = CITY_BLD_HEIGHTS[stage];           // kub vertikal balandligi
  const bw = CITY_BLD_BASE_W / 2;               // asos yarim kengligi
  const bh = CITY_BLD_BASE_H / 2;               // asos yarim balandligi
  // Kub asosining 4 cho'qqisi (izometrik romb), cx/cy — pastki markaz:
  //   top (orqa), right (o'ng), bottom (old), left (chap)
  const baseTop    = `${cx},${cy - bh}`;
  const baseRight  = `${cx + bw},${cy}`;
  const baseBottom = `${cx},${cy + bh}`;
  const baseLeft   = `${cx - bw},${cy}`;
  // Kub TEPA yuzi cho'qqilari (asos cho'qqilari h ga ko'tarilgan):
  const upTop    = `${cx},${cy - bh - h}`;
  const upRight  = `${cx + bw},${cy - h}`;
  const upBottom = `${cx},${cy + bh - h}`;
  const upLeft   = `${cx - bw},${cy - h}`;

  // 3 yuz polygonlari:
  //   - top: eng yorug' (upTop, upRight, upBottom, upLeft)
  //   - left yuz (old-chap, o'rta soya): baseLeft, baseBottom, upBottom, upLeft
  //   - right yuz (old-o'ng, eng quyuq soya): baseBottom, baseRight, upRight, upBottom
  const topFace   = `${upTop} ${upRight} ${upBottom} ${upLeft}`;
  const leftFace  = `${baseLeft} ${baseBottom} ${upBottom} ${upLeft}`;
  const rightFace = `${baseBottom} ${baseRight} ${upRight} ${upBottom}`;

  let svg = `<g class="city-bld" data-type="${type}" data-stage="${stage}">`;
  svg += `<polygon class="city-bld-left"  points="${leftFace}"/>`;
  svg += `<polygon class="city-bld-right" points="${rightFace}"/>`;
  svg += `<polygon class="city-bld-top"   points="${topFace}"/>`;

  // Stage 4 (complete): kichik detal — bino emoji belgisi tepa yuzda.
  // Hozircha matn (emoji) — C3.2+ da haqiqiy SVG detal bilan almashtirilishi mumkin.
  if (stage === 4) {
    const emoji = (type === 'mosque') ? '\u{1F54C}' : '\u{1F3E0}';  // 🕌 / 🏠
    svg += `<text class="city-bld-emoji" x="${cx}" y="${cy - bh - h + 2}" `
         + `text-anchor="middle" dominant-baseline="middle">${emoji}</text>`;
  }
  svg += `</g>`;
  return svg;
}

// ── Barcha binolarni render qilish (painter's algorithm) ──
// buildings: [{habit_id, type, x, y, progress}, ...]
// MUHIM: orqadagi binolar AVVAL chiziladi — old binolar ularni qisman to'sadi.
// Saralash kaliti: (x + y) — izometric "chuqurlik" (kichik = orqada/tepada).
function renderCityBuildings(buildings) {
  if (!Array.isArray(buildings) || buildings.length === 0) return '';
  // Nusxa ustida sort (asl massivga tegmaymiz — Qoida #13 shared state)
  const sorted = buildings.slice().sort((a, b) => (a.x + a.y) - (b.x + b.y));
  let html = '';
  for (const b of sorted) {
    const stage = cityBuildingStage(b.progress);
    // Katak rombning markaziy nuqtasi: cityIsoX/Y top cho'qqini beradi,
    // markazga yetish uchun +CITY_TILE_H/2 (romb vertikal markazi).
    const cx = cityIsoX(b.x, b.y);
    const cy = cityIsoY(b.x, b.y) + CITY_TILE_H / 2;
    html += cityBuildingSVG(b.type, stage, cx, cy);
  }
  return html;
}

// ── Eslatma kelajakdagi bosqichlar uchun ──
// PHASE C2.2/C2.3: touch pan/zoom — YAGNI sababli o'tkazib yuborilgan
// PHASE C3.1: ✅ demo binolar (house/mosque, 5 stage, oq clay render) — SHU YERDA
// PHASE C3.2: qolgan 8 bino turi (stadium/library/school/park/cafe/bank/hospital/studio)
// PHASE C3.3: 5 dekoratsiya (tree/flower/car/bench/fountain)
// PHASE C3.4: premium CSS polish (soyalar, 3D effekt finetune)
// PHASE C4:   loadCityFromAPI() — GET /api/city/<uid> (_cityDemoData ni almashtiradi)
// PHASE C5:   bino bosish modali (change_type) + bino ko'chirish (long-press)
// PHASE C6:   renderDecorationsShop() — bozor modal
// PHASE C7:   tarjimalar strings.js'ga qo'shiladi (10 bino + 5 dekoratsiya nomlari)
// PHASE C8:   premium CSS polish (beige/gold accent — agar kerak bo'lsa)
