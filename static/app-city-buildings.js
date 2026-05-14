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

// ── Eslatma kelajakdagi bosqichlar uchun ──
// PHASE C3.2: ✅ binolar — bir xil standart kub, faqat stage bo'yicha balandlik
// PHASE C3.3: ⏭️ dekoratsiyalar — KEYINGA QOLDIRILDI. Sabab: kichik izometrik
//   primitivlar bilan tanib bo'ladigan daraxt/mashina/favvora yasash qiyin,
//   natija abstrakt/bee'xshov chiqdi. Kelajakda professional SVG ikonkalar bilan
//   qilinadi (kod bilan emas). Backend place_decoration/DECORATION_TYPES tayyor turadi.
// PHASE C3.4: premium CSS polish (soyalar, 3D effekt finetune)
// PHASE C5:   bino bosish — data-type/data-stage atributlari modal uchun tayyor
//             (modal'da bino turi nomi, emoji, progress ko'rsatiladi)
// BACKEND (alohida bosqich): find_empty_slot (city_logic.py) — yangi bino atrofida
//   bittadan bo'sh katak qoldirish qoidasi. Hozir faqat band bo'lmagan katak topadi;
//   "atrofi ham bo'sh" qoidasi keyin qo'shiladi (create_building + place_decoration
//   ikkalasiga ta'sir qiladi — Qoida #9-10).