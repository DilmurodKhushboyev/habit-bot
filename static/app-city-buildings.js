// ==============================================
// app-city-buildings.js — Shahar binolari (PHASE C3.2: bir xil kub binolar)
// ==============================================
// Bog'liqlik:
//   - app-city.js (CITY_TILE_H, CITY_BLD_BASE_W/H, CITY_BLD_HEIGHTS,
//     CITY_STAGE_THRESHOLDS, cityIsoX/cityIsoY — shu fayldan import qilinadi)
//   - config.py BUILDING_TYPES (10 bino turi) va BUILDING_STAGE_THRESHOLDS bilan SINXRON
//
// VAZIFA: barcha bino BIR XIL standart kub — o'lcham/shakl farqi YO'Q.
//   QAROR (C3.2): har odat 66 kunda shakllanadi. Agar binolar har xil bo'lsa,
//   foydalanuvchi chalg'iydi. Bir xil bo'lsa — diqqat faqat QURILISH BOSQICHIGA
//   (stage) qaratiladi: "odatimni qanchalik yaxshi quryapman?". Bu habit tracker
//   mantig'iga mos. Bino TURI faqat data-type atributida saqlanadi — C5 da bino
//   bosilganda modal'da turi/nomi/progress ko'rsatiladi.
//   (Avvalgi CITY_BLD_SHAPES o'lcham tizimi va cityCapSVG cap tizimi — o'chirildi.
//    Kerak bo'lsa git tarixida bor; "kerak bo'lar" deb o'lik kod saqlamaymiz.)
//
// MUHIM (Qoida #24): bu fayl app-city.js dan AJRATILGAN. index.html da
//   app-city.js dan KEYIN yuklanadi (konstantalar avval e'lon qilinishi kerak).
// ==============================================

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
// type: bino turi (config.py BUILDING_TYPES kaliti — faqat data-type atributi uchun,
//   o'lchamga TA'SIR QILMAYDI. C5 modal shu atributdan turini o'qiydi).
// stage: 0-4 (cityBuildingStage natijasi) — kub balandligini belgilaydi.
// cx, cy: katak rombning MARKAZIY nuqtasi (cityIsoX/cityIsoY + romb markazi).
// Qaytaradi: <g> ichida 3 polygon (tepa/chap/o'ng yuz) — monoxrom oq clay.
// Barcha bino BIR XIL o'lcham — faqat stage bo'yicha balandlik o'zgaradi.
function cityBuildingSVG(type, stage, cx, cy) {
  const bw = CITY_BLD_BASE_W / 2;          // asos yarim kengligi (barcha bino bir xil)
  const bh = CITY_BLD_BASE_H / 2;          // asos yarim balandligi (barcha bino bir xil)
  const h  = CITY_BLD_HEIGHTS[stage];      // kub vertikal balandligi (stage bo'yicha)

  const faces = cityCubeFaces(cx, cy, bw, bh, h);

  let svg = `<g class="city-bld" data-type="${type}" data-stage="${stage}">`;
  svg += `<polygon class="city-bld-left"  points="${faces.leftFace}"/>`;
  svg += `<polygon class="city-bld-right" points="${faces.rightFace}"/>`;
  svg += `<polygon class="city-bld-top"   points="${faces.topFace}"/>`;
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

// ════════════════════════════════════════════════
//  PHASE C3.3 — DEKORATSIYALAR (tree/flower/car/bench/fountain)
// ════════════════════════════════════════════════
// Dekoratsiya ≠ bino: STAGE yo'q (doim bir xil), bozordan sotib olinadi,
//   odatdan kelmaydi. city_logic.py place_decoration: {type, x, y, placed_at}.
// Binolardan FARQI: (1) ancha kichik, (2) stage yo'q, (3) har turi o'ziga xos
//   shakl (daraxt daraxtga, mashina mashinaga o'xshashi kerak — mantiqiy).
//   Lekin SODDALIK saqlanadi: har biri 1-3 oddiy shakl, murakkab detal yo'q.
// Hammasi oq clay — binolar bilan bir uslubda (city-bld-* klasslar qayta ishlatiladi).

// Dekoratsiya asos o'lchami — binodan ANCHA kichik (Qoida #17 markazlash).
// Bino asosi 60×30; dekoratsiya ~28×14 — aniq farq ko'rinadi.
const CITY_DEC_BASE_W = 28;
const CITY_DEC_BASE_H = 14;

// ── Bitta dekoratsiya SVG'si ──
// type: 'tree' | 'flower' | 'car' | 'bench' | 'fountain' (config.py DECORATION_TYPES)
// cx, cy: katak rombning MARKAZIY nuqtasi.
// Qaytaradi: <g> ichida polygonlar — oq clay, har turi o'ziga xos oddiy shakl.
function cityDecorationSVG(type, cx, cy) {
  const dw = CITY_DEC_BASE_W / 2;   // dekoratsiya asos yarim kengligi
  const dh = CITY_DEC_BASE_H / 2;   // dekoratsiya asos yarim balandligi
  let svg = `<g class="city-dec" data-type="${type}">`;

  if (type === 'tree') {
    // Daraxt: ingichka past tana (kub) + uchli tojи (piramida).
    const trunkH = dh * 1.4;
    const trunk = cityCubeFaces(cx, cy, dw * 0.35, dh * 0.35, trunkH);
    svg += `<polygon class="city-bld-left"  points="${trunk.leftFace}"/>`;
    svg += `<polygon class="city-bld-right" points="${trunk.rightFace}"/>`;
    // Toj: tana ustida piramida (uchburchak 2 yuz)
    const topY = cy - trunkH;
    const tBottom = `${cx},${topY + dh}`;
    const tLeft   = `${cx - dw},${topY}`;
    const tRight  = `${cx + dw},${topY}`;
    const apex    = `${cx},${topY - dh * 2.6}`;
    svg += `<polygon class="city-bld-left"  points="${tLeft} ${tBottom} ${apex}"/>`;
    svg += `<polygon class="city-bld-right" points="${tBottom} ${tRight} ${apex}"/>`;
  } else if (type === 'flower') {
    // Gul: juda kichik — past kichik kub (tuproq) + ingichka tik (poya).
    const potH = dh * 0.7;
    const pot = cityCubeFaces(cx, cy, dw * 0.5, dh * 0.5, potH);
    svg += `<polygon class="city-bld-left"  points="${pot.leftFace}"/>`;
    svg += `<polygon class="city-bld-right" points="${pot.rightFace}"/>`;
    svg += `<polygon class="city-bld-top"   points="${pot.topFace}"/>`;
    // Poya: tuproq markazidan tepaga kichik kub
    const stem = cityCubeFaces(cx, cy - potH, dw * 0.18, dh * 0.18, dh * 1.2);
    svg += `<polygon class="city-bld-left"  points="${stem.leftFace}"/>`;
    svg += `<polygon class="city-bld-right" points="${stem.rightFace}"/>`;
    svg += `<polygon class="city-bld-top"   points="${stem.topFace}"/>`;
  } else if (type === 'car') {
    // Mashina: past keng kub (korpus) + ustida kichikroq past kub (kabina).
    const bodyH = dh * 0.9;
    const body = cityCubeFaces(cx, cy, dw * 1.1, dh * 1.1, bodyH);
    svg += `<polygon class="city-bld-left"  points="${body.leftFace}"/>`;
    svg += `<polygon class="city-bld-right" points="${body.rightFace}"/>`;
    svg += `<polygon class="city-bld-top"   points="${body.topFace}"/>`;
    const cabin = cityCubeFaces(cx, cy - bodyH, dw * 0.6, dh * 0.6, dh * 0.7);
    svg += `<polygon class="city-bld-left"  points="${cabin.leftFace}"/>`;
    svg += `<polygon class="city-bld-right" points="${cabin.rightFace}"/>`;
    svg += `<polygon class="city-bld-top"   points="${cabin.topFace}"/>`;
  } else if (type === 'bench') {
    // Skameyka: juda past keng yapaloq kub (oddiy — o'tirgich taassuroti).
    const benchH = dh * 0.5;
    const bench = cityCubeFaces(cx, cy, dw * 1.0, dh * 1.0, benchH);
    svg += `<polygon class="city-bld-left"  points="${bench.leftFace}"/>`;
    svg += `<polygon class="city-bld-right" points="${bench.rightFace}"/>`;
    svg += `<polygon class="city-bld-top"   points="${bench.topFace}"/>`;
    // Suyanchiq: orqada ingichka tik kub
    const back = cityCubeFaces(cx - dw * 0.5, cy - benchH + dh * 0.5,
                               dw * 0.5, dh * 0.5, dh * 0.9);
    svg += `<polygon class="city-bld-left"  points="${back.leftFace}"/>`;
    svg += `<polygon class="city-bld-right" points="${back.rightFace}"/>`;
    svg += `<polygon class="city-bld-top"   points="${back.topFace}"/>`;
  } else if (type === 'fountain') {
    // Favvora: past keng kub (havza) + markazida ingichka tik (suv ustuni).
    const basinH = dh * 0.6;
    const basin = cityCubeFaces(cx, cy, dw * 1.15, dh * 1.15, basinH);
    svg += `<polygon class="city-bld-left"  points="${basin.leftFace}"/>`;
    svg += `<polygon class="city-bld-right" points="${basin.rightFace}"/>`;
    svg += `<polygon class="city-bld-top"   points="${basin.topFace}"/>`;
    const jet = cityCubeFaces(cx, cy - basinH, dw * 0.2, dh * 0.2, dh * 1.6);
    svg += `<polygon class="city-bld-left"  points="${jet.leftFace}"/>`;
    svg += `<polygon class="city-bld-right" points="${jet.rightFace}"/>`;
    svg += `<polygon class="city-bld-top"   points="${jet.topFace}"/>`;
  } else {
    // Fallback: noma'lum dekoratsiya turi → kichik oddiy kub
    const box = cityCubeFaces(cx, cy, dw * 0.7, dh * 0.7, dh);
    svg += `<polygon class="city-bld-left"  points="${box.leftFace}"/>`;
    svg += `<polygon class="city-bld-right" points="${box.rightFace}"/>`;
    svg += `<polygon class="city-bld-top"   points="${box.topFace}"/>`;
  }

  svg += `</g>`;
  return svg;
}

// ── Barcha dekoratsiyalarni render qilish (painter's algorithm) ──
// decorations: [{type, x, y, placed_at}, ...]
// Binolar bilan BIR XIL painter mantig'i (depth → x). C3.3 da dekoratsiyalar
// binolardan ALOHIDA layer — renderCityGrid binolardan KEYIN chaqiradi
// (dekoratsiyalar kichik, binolar ustidan ko'rinmasligi uchun emas — aksincha,
//  bir xil painter qoidasi ikkala massivga alohida qo'llaniladi).
function renderCityDecorations(decorations) {
  if (!Array.isArray(decorations) || decorations.length === 0) return '';
  const sorted = decorations.slice().sort((a, b) => {
    const depthDiff = (a.x + a.y) - (b.x + b.y);
    if (depthDiff !== 0) return depthDiff;
    return a.x - b.x;
  });
  let html = '';
  for (const d of sorted) {
    const cx = cityIsoX(d.x, d.y);
    const cy = cityIsoY(d.x, d.y) + CITY_TILE_H / 2;
    html += cityDecorationSVG(d.type, cx, cy);
  }
  return html;
}

// ── Eslatma kelajakdagi bosqichlar uchun ──
// PHASE C3.2: ✅ binolar — bir xil standart kub, faqat stage bo'yicha balandlik
// PHASE C3.3: ✅ 5 dekoratsiya (tree/flower/car/bench/fountain) — stage yo'q, kichik
// PHASE C3.4: premium CSS polish (soyalar, 3D effekt finetune)
// PHASE C5:   bino bosish — data-type/data-stage atributlari modal uchun tayyor
//             (modal'da bino turi nomi, emoji, progress ko'rsatiladi)
// BACKEND (alohida bosqich): find_empty_slot (city_logic.py) — yangi bino atrofida
//   bittadan bo'sh katak qoldirish qoidasi. Hozir faqat band bo'lmagan katak topadi;
//   "atrofi ham bo'sh" qoidasi keyin qo'shiladi (create_building + place_decoration
//   ikkalasiga ta'sir qiladi — Qoida #9-10).