// ==============================================
// app-city-buildings.js — Shahar binolari (PHASE C3.2: shakl-asosida bino turlari)
// ==============================================
// Bog'liqlik:
//   - app-city.js (CITY_TILE_H, CITY_BLD_BASE_W/H, CITY_BLD_HEIGHTS,
//     CITY_STAGE_THRESHOLDS, cityIsoX/cityIsoY — shu fayldan import qilinadi)
//   - config.py BUILDING_TYPES (10 bino turi) va BUILDING_STAGE_THRESHOLDS bilan SINXRON
//
// VAZIFA: har bino turi BIR XIL toza kub uslubida — faqat O'LCHAM (widthMul/heightMul)
//   bilan farqlanadi. Murakkab cap (gumbaz/tom) olib tashlandi — estetik bir butunlik
//   + texnik soddalik + diqqat STAGE'da. Bino TURINI bilish C5 da modal orqali.
//   cityCapSVG funksiyasi kodda saqlanadi (kelajakda qayta yoqish uchun).
//
// MUHIM (Qoida #24): bu fayl app-city.js dan AJRATILGAN — app-city.js 300 qatordan
//   oshmasligi uchun. index.html da app-city.js dan KEYIN yuklanadi (konstantalar
//   avval e'lon qilinishi kerak).
// ==============================================

// ── BINO SHAKL KONFIGURATSIYASI ──
// QAROR (C3.2): binolar BIR XIL toza kub uslubida — faqat O'LCHAM bilan farqlanadi.
//   Murakkab cap (gumbaz/tom/xoch) OLIB TASHLANDI — sabab: (1) estetik bir butunlik
//   (referens oq city kabi toza), (2) texnik soddalik (1 funksiya, kam xato),
//   (3) foydalanuvchi diqqati STAGE/progress'da bo'lishi kerak (habit tracker mantig'i).
//   Bino TURINI aniq bilish C5 da — bino bosilganda modal (nom, emoji, progress).
//
// Har bino turi uchun: widthMul (asos kenglik koeff.), heightMul (balandlik koeff.).
//   Qiymatlar app-city.js dagi CITY_BLD_BASE_W/H va CITY_BLD_HEIGHTS ga ko'paytiriladi.
//   widthMul=1.0 → standart, heightMul=1.0 → standart.
// cap maydoni saqlanadi (hammasi 'none') — cityCapSVG funksiyasi kodda qoladi,
//   kelajakda (masalan C8 polish) xohlansa qayta yoqish oson.
// Qoida #17 — magic number'lar shu yerda markazlashgan.
const CITY_BLD_SHAPES = {
  // Monumental: baland + biroz ingichka
  mosque:   { widthMul: 0.92, heightMul: 1.15, cap: 'none' },
  bank:     { widthMul: 0.92, heightMul: 1.15, cap: 'none' },
  // Keng + past: yer egallaydi
  stadium:  { widthMul: 1.35, heightMul: 0.55, cap: 'none' },
  park:     { widthMul: 1.30, heightMul: 0.45, cap: 'none' },
  // Jamoat binosi: biroz keng + o'rta balandlik
  library:  { widthMul: 1.12, heightMul: 0.9,  cap: 'none' },
  school:   { widthMul: 1.12, heightMul: 0.9,  cap: 'none' },
  hospital: { widthMul: 1.12, heightMul: 0.95, cap: 'none' },
  // Standart kub
  house:    { widthMul: 1.0,  heightMul: 1.0,  cap: 'none' },
  cafe:     { widthMul: 0.9,  heightMul: 0.8,  cap: 'none' },
  studio:   { widthMul: 1.0,  heightMul: 1.0,  cap: 'none' },
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

// ── Cap (tepa qo'shimcha element) SVG'si ──
// capType: 'roof' | 'pyramid' | 'corners' | 'none'
// cx, cy: ASOSIY kub pastki markazi. bw/bh: asosiy kub asos yarim o'lchamlari.
// topY: asosiy kub tepa yuzi balandligi (cy - h) — cap shu ustiga quriladi.
// Qaytaradi: cap polygonlari (yuzlar bir xil city-bld-* klasslar bilan — oq clay).
// Har cap turi izometrik proyeksiyada to'g'ri ko'rinishi uchun alohida hisoblanadi.
function cityCapSVG(capType, cx, cy, bw, bh, topY) {
  if (capType === 'roof') {
    // Qiya tom: kub tepa rombi ustida "tizzali" tom (ridge).
    // Ridge — old-orqa diagonali (tTop↔tBottom) bo'ylab, lekin TEPAGA ko'tarilgan.
    // Izometrikda to'g'ri ko'rinishi uchun: ridge ikki uchi tTop va tBottom
    //   nuqtalaridan vertikal ravishda ridgeH ga ko'tariladi.
    const ridgeH = bh * 1.6;  // tom balandligi (asos yarim balandligiga bog'liq)
    // Kub tepa romb cho'qqilari (topY balandlikda):
    const tTop    = `${cx},${topY - bh}`;       // orqa cho'qqi
    const tRight  = `${cx + bw},${topY}`;       // o'ng cho'qqi
    const tBottom = `${cx},${topY + bh}`;       // old cho'qqi
    const tLeft   = `${cx - bw},${topY}`;       // chap cho'qqi
    // Ridge ikki uchi: tTop va tBottom ustidan ridgeH balandlikda.
    // Ikkalasi ham o'z nuqtasidan TIK yuqoriga ko'tariladi → ridge old-orqa
    //   yo'nalishida, izometrikda tabiiy qiya tom ko'rinadi.
    const ridgeBack  = `${cx},${topY - bh - ridgeH}`;  // tTop ustida
    const ridgeFront = `${cx},${topY + bh - ridgeH}`;  // tBottom ustida
    // Tom 2 ko'rinadigan yuzi:
    //   chap nishab: tLeft → tBottom → ridgeFront → ridgeBack → tTop → tLeft
    //   (chap tomon to'liq trapetsiya — tLeft va tTop orqali)
    const roofLeft  = `${tLeft} ${tTop} ${ridgeBack} ${ridgeFront} ${tBottom}`;
    const roofRight = `${tBottom} ${ridgeFront} ${ridgeBack} ${tTop} ${tRight}`;
    let s = `<polygon class="city-bld-left"  points="${roofLeft}"/>`;
    s += `<polygon class="city-bld-right" points="${roofRight}"/>`;
    return s;
  }
  if (capType === 'pyramid') {
    // Uchli gumbaz: kub tepa rombidan markazga ko'tarilgan piramida (4 yuz, 2 ko'rinadi).
    const pyrH = bh * 2.0;  // piramida balandligi
    const tTop    = `${cx},${topY - bh}`;
    const tRight  = `${cx + bw},${topY}`;
    const tBottom = `${cx},${topY + bh}`;
    const tLeft   = `${cx - bw},${topY}`;
    const apex    = `${cx},${topY - pyrH}`;  // piramida cho'qqisi
    // 2 ko'rinadigan yuz: chap (tLeft-tBottom-apex), o'ng (tBottom-tRight-apex)
    const pyrLeft  = `${tLeft} ${tBottom} ${apex}`;
    const pyrRight = `${tBottom} ${tRight} ${apex}`;
    let s = `<polygon class="city-bld-left"  points="${pyrLeft}"/>`;
    s += `<polygon class="city-bld-right" points="${pyrRight}"/>`;
    return s;
  }
  // 'corners' va 'none' — qo'shimcha element yo'q (kub o'zi yetarli).
  // stadium 'corners' — keng+past proporsiya o'zi oval taassurot beradi.
  return '';
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
  // C3.2 QARORI: barcha bino 'none' — cap chizilmaydi (toza kub uslubi).
  // Bu shart va cityCapSVG funksiyasi KODDA QOLADI — kelajakda (masalan C8 polish)
  // biror bino turiga cap qo'shilsa, faqat CITY_BLD_SHAPES da cap qiymatini
  // o'zgartirish kifoya (qolgan mantiq tayyor).
  if (shape.cap !== 'none' && stage >= 2) {
    const topY = cy - h;  // asosiy kub tepa yuzi balandligi — cap shu ustiga quriladi
    svg += cityCapSVG(shape.cap, cx, cy, bw, bh, topY);
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
// PHASE C3.2: ✅ 10 bino turi — bir xil toza kub, o'lcham bilan farqlanadi (cap yo'q)
// PHASE C3.3: 5 dekoratsiya (tree/flower/car/bench/fountain) — alohida funksiya
// PHASE C3.4: premium CSS polish (soyalar, 3D effekt finetune)
// PHASE C5:   bino bosish — data-type/data-stage atributlari modal uchun tayyor
//             (modal'da bino turi nomi, emoji, progress ko'rsatiladi)
// Kelajak (ixtiyoriy): cityCapSVG kodda — biror bino turiga cap qaytarilsa,
//   CITY_BLD_SHAPES da cap qiymatini o'zgartirish kifoya.
