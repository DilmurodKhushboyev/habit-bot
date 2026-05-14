// ==============================================
// app-city-buildings.js — Shahar binolari (PHASE C3.2: shakl-asosida bino turlari)
// ==============================================
// Bog'liqlik:
//   - app-city.js (CITY_TILE_H, CITY_BLD_BASE_W/H, CITY_BLD_HEIGHTS,
//     CITY_STAGE_THRESHOLDS, cityIsoX/cityIsoY — shu fayldan import qilinadi)
//   - config.py BUILDING_TYPES (10 bino turi) va BUILDING_STAGE_THRESHOLDS bilan SINXRON
//
// VAZIFA: har bino turi o'ziga xos SHAKL/proporsiya bilan farqlanadi (matn/emoji yo'q,
//   oq clay estetikasi saqlanadi). C3.2 da 3 ta test bino: house/mosque/stadium.
//   C3.2 davomi: qolgan 7 tur (library/school/park/cafe/bank/hospital/studio).
//
// MUHIM (Qoida #24): bu fayl app-city.js dan AJRATILGAN — app-city.js 300 qatordan
//   oshmasligi uchun. index.html da app-city.js dan KEYIN yuklanadi (konstantalar
//   avval e'lon qilinishi kerak).
// ==============================================

// ── BINO SHAKL KONFIGURATSIYASI ──
// Har bino turi uchun: widthMul (asos kenglik koeffitsienti),
//   heightMul (balandlik koeffitsienti), cap (tepa qo'shimcha element turi).
// Qiymatlar app-city.js dagi CITY_BLD_BASE_W/H va CITY_BLD_HEIGHTS ga ko'paytiriladi.
//   widthMul=1.0 → standart kenglik, heightMul=1.0 → standart balandlik.
// cap turlari: 'none' (qo'shimcha yo'q), 'dome' (gumbaz — mosque), kelajakda ko'payadi.
// Qoida #17 — magic number'lar shu yerda markazlashgan.
const CITY_BLD_SHAPES = {
  // house: standart kub — barcha koeffitsient 1.0, qo'shimcha element yo'q
  house:   { widthMul: 1.0,  heightMul: 1.0,  cap: 'none' },
  // mosque: ingichka + baland + ustida gumbaz blok
  mosque:  { widthMul: 0.72, heightMul: 1.25, cap: 'dome' },
  // stadium: keng + past + yapaloq (oval taassurot)
  stadium: { widthMul: 1.35, heightMul: 0.5,  cap: 'none' },
};
// Fallback shakl — noma'lum tur kelsa (eski data yoki xato) standart kub ishlatiladi.
const CITY_BLD_SHAPE_DEFAULT = { widthMul: 1.0, heightMul: 1.0, cap: 'none' };

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

// ── Izometrik kub polygonlarini hisoblash (yordamchi) ──
// cx, cy: kub PASTKI markazi. bw/bh: asos yarim o'lchamlari. h: vertikal balandlik.
// Qaytaradi: {topFace, leftFace, rightFace} — 3 yuz polygon points satrlari.
// Bu yordamchi gumbaz kabi qo'shimcha kublar uchun ham qayta ishlatiladi.
function cityCubeFaces(cx, cy, bw, bh, h) {
  // Asos 4 cho'qqi (izometrik romb)
  const baseRight  = `${cx + bw},${cy}`;
  const baseBottom = `${cx},${cy + bh}`;
  const baseLeft   = `${cx - bw},${cy}`;
  // Tepa yuz 4 cho'qqi (asos h ga ko'tarilgan)
  const upTop    = `${cx},${cy - bh - h}`;
  const upRight  = `${cx + bw},${cy - h}`;
  const upBottom = `${cx},${cy + bh - h}`;
  const upLeft   = `${cx - bw},${cy - h}`;
  return {
    topFace:   `${upTop} ${upRight} ${upBottom} ${upLeft}`,
    leftFace:  `${baseLeft} ${baseBottom} ${upBottom} ${upLeft}`,
    rightFace: `${baseBottom} ${baseRight} ${upRight} ${upBottom}`,
  };
}

// ── Bitta bino SVG'si (izometrik kub, 3 yuz: tepa + chap + o'ng) ──
// type: bino turi (config.py BUILDING_TYPES kaliti)
// stage: 0-4 (cityBuildingStage natijasi)
// cx, cy: katak rombning MARKAZIY nuqtasi (cityIsoX/cityIsoY + romb markazi)
// Qaytaradi: <g> ichida polygonlar — monoxrom oq clay, soya bilan hajm.
// Bino TURI shakl koeffitsientlari (CITY_BLD_SHAPES) orqali farqlanadi.
function cityBuildingSVG(type, stage, cx, cy) {
  const shape = CITY_BLD_SHAPES[type] || CITY_BLD_SHAPE_DEFAULT;
  // Asos o'lchamlari shakl koeffitsienti bilan
  const bw = (CITY_BLD_BASE_W / 2) * shape.widthMul;   // asos yarim kengligi
  const bh = (CITY_BLD_BASE_H / 2) * shape.widthMul;   // asos yarim balandligi (proporsiya saqlanadi)
  const h  = CITY_BLD_HEIGHTS[stage] * shape.heightMul; // kub vertikal balandligi

  // Asosiy kub 3 yuzi
  const faces = cityCubeFaces(cx, cy, bw, bh, h);

  let svg = `<g class="city-bld" data-type="${type}" data-stage="${stage}">`;
  svg += `<polygon class="city-bld-left"  points="${faces.leftFace}"/>`;
  svg += `<polygon class="city-bld-right" points="${faces.rightFace}"/>`;
  svg += `<polygon class="city-bld-top"   points="${faces.topFace}"/>`;

  // ── Tepa qo'shimcha element (cap) ──
  // Faqat stage >= 2 (devorlar ko'tarilgandan keyin) ko'rinadi — qurilish mantiqiy.
  if (shape.cap === 'dome' && stage >= 2) {
    // Gumbaz: asosiy kub ustida kichik kub (mosque uchun).
    // Kichik kub markazi: asosiy kub TEPA markazi (cy - h).
    const domeBw = bw * 0.5;
    const domeBh = bh * 0.5;
    const domeH  = bh * 1.1;  // gumbaz balandligi asos balandligiga bog'liq
    const domeFaces = cityCubeFaces(cx, cy - h, domeBw, domeBh, domeH);
    svg += `<polygon class="city-bld-left"  points="${domeFaces.leftFace}"/>`;
    svg += `<polygon class="city-bld-right" points="${domeFaces.rightFace}"/>`;
    svg += `<polygon class="city-bld-top"   points="${domeFaces.topFace}"/>`;
  }

  svg += `</g>`;
  return svg;
}

// ── Barcha binolarni render qilish (painter's algorithm) ──
// buildings: [{habit_id, type, x, y, progress}, ...]
// MUHIM: orqadagi binolar AVVAL chiziladi — old binolar ularni qisman to'sadi.
// Birlamchi kalit: (x + y) — izometric "chuqurlik" (kichik = orqada/tepada).
// Ikkilamchi kalit: x — depth teng bo'lsa, kichik x orqada (chap-orqa),
//   katta x oldinda (o'ng-old) chiziladi (izometric proyeksiya mantig'i).
function renderCityBuildings(buildings) {
  if (!Array.isArray(buildings) || buildings.length === 0) return '';
  // Nusxa ustida sort (asl massivga tegmaymiz — Qoida #13 shared state)
  const sorted = buildings.slice().sort((a, b) => {
    const depthDiff = (a.x + a.y) - (b.x + b.y);
    if (depthDiff !== 0) return depthDiff;
    return a.x - b.x;  // depth teng → kichik x avval (orqada)
  });
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
// PHASE C3.2 (hozir): 3 test bino — house/mosque/stadium. Yoqsa qolgan 7 tur qo'shiladi.
// PHASE C3.2 davomi: library/school/park/cafe/bank/hospital/studio shakllari
// PHASE C3.3: 5 dekoratsiya (tree/flower/car/bench/fountain) — alohida funksiya
// PHASE C3.4: premium CSS polish (soyalar, 3D effekt finetune)
// PHASE C5:   bino bosish — data-type/data-stage atributlari modal uchun tayyor
