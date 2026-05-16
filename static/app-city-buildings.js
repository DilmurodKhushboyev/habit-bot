// ==============================================
// app-city-buildings.js — Shahar binolari (PHASE C3.5a: glass wireframe)
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
//   mantig'iga mos. Bino TURI faqat data-type atributida saqlanadi. Bino bilan
//   interaktivlik (long-press → ko'chirish) data-habit-id atributiga tayanadi.
//   (Avvalgi CITY_BLD_SHAPES o'lcham tizimi va cityCapSVG cap tizimi — o'chirildi.
//    Kerak bo'lsa git tarixida bor; "kerak bo'lar" deb o'lik kod saqlamaymiz.)
//
// PHASE C3.5a (glass wireframe): bino 2 qismdan iborat:
//   1. SOLID qism (qurilgan) — stage balandligida, to'liq rangli kub
//   2. GLASS qism (qurilmagan) — to'liq balandlikkacha bo'sh joy, shaffof yuzlar +
//      aniq qirra chiziqlari (shisha karkas). Foydalanuvchi "bino qaysi yo'nalishda
//      o'sayotganini" ko'radi → motivatsion vizual. Stage 4 da glass YO'Q.
//
// MUHIM (Qoida #24): bu fayl app-city.js dan AJRATILGAN. index.html da
//   app-city.js dan KEYIN yuklanadi (konstantalar avval e'lon qilinishi kerak).
// ==============================================

// ── To'liq qurilgan bino balandligi (Qoida #17 — magic number markazlash) ──
// Glass qism solid qism tepasidan shu balandlikkacha cho'ziladi.
// CITY_BLD_HEIGHTS[4] = 84 (app-city.js da) bilan AYNI QIYMAT — keyinroq
// CITY_BLD_HEIGHTS o'zgarsa, bu ham xuddi shunday yangilanishi kerak (Qoida #11).
const CITY_BLD_FULL_HEIGHT = 84;

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

// ── Bitta bino SVG'si (izometrik kub, SOLID + GLASS qatlamlar) ──
// type: bino turi (config.py BUILDING_TYPES kaliti — faqat data-type atributi uchun,
//   o'lchamga TA'SIR QILMAYDI).
// stage: 0-4 (cityBuildingStage natijasi) — solid kub balandligini belgilaydi.
// cx, cy: katak rombning MARKAZIY nuqtasi (cityIsoX/cityIsoY + romb markazi).
// habitId: bino bog'liq odat id'si — <g> ga data-habit-id atributi sifatida
//   yoziladi. Bino bilan interaktivlik (long-press → bino ko'chirish) shu
//   atributdan habit_id ni o'qib, move_item API'ga yuboradi.
//
// QATLAMLAR (C3.5a):
//   1. SOLID kub — qurilgan qism (stage balandligida)
//   2. GLASS kub — qurilmagan qism (solid TEPASIDAN to'liq balandlikkacha).
//      Stage 4 da glass chizilmaydi (bino to'liq qurilgan).
//
// Qaytaradi: <g> ichida solid 3 polygon + (agar stage<4) glass 3 polygon + qirralar.
function cityBuildingSVG(type, stage, cx, cy, habitId) {
  const bw = CITY_BLD_BASE_W / 2;          // asos yarim kengligi (barcha bino bir xil)
  const bh = CITY_BLD_BASE_H / 2;          // asos yarim balandligi (barcha bino bir xil)
  const hSolid = CITY_BLD_HEIGHTS[stage];  // solid kub balandligi

  // 1. SOLID kub (qurilgan qism) — pastdan hSolid balandlikgacha
  const solidFaces = cityCubeFaces(cx, cy, bw, bh, hSolid);

  let svg = `<g class="city-bld" data-type="${type}" data-stage="${stage}" data-habit-id="${habitId}">`;
  svg += `<polygon class="city-bld-left"  points="${solidFaces.leftFace}"/>`;
  svg += `<polygon class="city-bld-right" points="${solidFaces.rightFace}"/>`;
  svg += `<polygon class="city-bld-top"   points="${solidFaces.topFace}"/>`;

  // 2. GLASS kub (qurilmagan qism) — faqat stage < 4 bo'lsa
  // Glass kub PASTKI markazi = solid kub TEPASI = (cx, cy - hSolid)
  // Glass kub balandligi = to'liq balandlik - solid balandlik
  if (stage < 4) {
    const hGlass = CITY_BLD_FULL_HEIGHT - hSolid;  // qolgan balandlik
    if (hGlass > 0) {
      // Glass kub asosi solid tepasiga "yotqizilgan" — bh=0 (asos romb tekis chiziq)
      // bo'lmasligi uchun solid bilan AYNI bw/bh ishlatamiz. Glass kub PASTKI
      // markazi (cx, cy - hSolid) — solid tepa romb markazi.
      const glassFaces = cityCubeFaces(cx, cy - hSolid, bw, bh, hGlass);
      // Glass yuzlar (shaffof rangli) — orqa qirralar ko'rinib turishi uchun
      svg += `<polygon class="city-bld-glass-left"  points="${glassFaces.leftFace}"/>`;
      svg += `<polygon class="city-bld-glass-right" points="${glassFaces.rightFace}"/>`;
      svg += `<polygon class="city-bld-glass-top"   points="${glassFaces.topFace}"/>`;
      // Glass kub qirra chiziqlari (wireframe) — bino rangida, aniq ko'rinadi.
      // 8 ta qirra: 4 ta tepa romb + 4 ta vertikal (asosdan tepaga).
      // Asos qirralarini chizmaymiz — solid kub tepasi bilan ustma-ust tushadi.
      const gx = cx, gy = cy - hSolid;  // glass pastki markaz
      const gTop    = `${gx},${gy - bh - hGlass}`;
      const gTopR   = `${gx + bw},${gy - hGlass}`;
      const gTopB   = `${gx},${gy + bh - hGlass}`;
      const gTopL   = `${gx - bw},${gy - hGlass}`;
      const gBaseT  = `${gx},${gy - bh}`;
      const gBaseR  = `${gx + bw},${gy}`;
      const gBaseB  = `${gx},${gy + bh}`;
      const gBaseL  = `${gx - bw},${gy}`;
      // 4 tepa romb qirrasi
      svg += `<line class="city-bld-glass-edge" x1="${gTop.split(',')[0]}" y1="${gTop.split(',')[1]}" x2="${gTopR.split(',')[0]}" y2="${gTopR.split(',')[1]}"/>`;
      svg += `<line class="city-bld-glass-edge" x1="${gTopR.split(',')[0]}" y1="${gTopR.split(',')[1]}" x2="${gTopB.split(',')[0]}" y2="${gTopB.split(',')[1]}"/>`;
      svg += `<line class="city-bld-glass-edge" x1="${gTopB.split(',')[0]}" y1="${gTopB.split(',')[1]}" x2="${gTopL.split(',')[0]}" y2="${gTopL.split(',')[1]}"/>`;
      svg += `<line class="city-bld-glass-edge" x1="${gTopL.split(',')[0]}" y1="${gTopL.split(',')[1]}" x2="${gTop.split(',')[0]}" y2="${gTop.split(',')[1]}"/>`;
      // 4 vertikal qirra (asos → tepa)
      svg += `<line class="city-bld-glass-edge" x1="${gBaseT.split(',')[0]}" y1="${gBaseT.split(',')[1]}" x2="${gTop.split(',')[0]}" y2="${gTop.split(',')[1]}"/>`;
      svg += `<line class="city-bld-glass-edge" x1="${gBaseR.split(',')[0]}" y1="${gBaseR.split(',')[1]}" x2="${gTopR.split(',')[0]}" y2="${gTopR.split(',')[1]}"/>`;
      svg += `<line class="city-bld-glass-edge" x1="${gBaseB.split(',')[0]}" y1="${gBaseB.split(',')[1]}" x2="${gTopB.split(',')[0]}" y2="${gTopB.split(',')[1]}"/>`;
      svg += `<line class="city-bld-glass-edge" x1="${gBaseL.split(',')[0]}" y1="${gBaseL.split(',')[1]}" x2="${gTopL.split(',')[0]}" y2="${gTopL.split(',')[1]}"/>`;
    }
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
    // b.habit_id ham uzatiladi — data-habit-id atributi orqali bino bilan
    //   interaktivlik (long-press ko'chirish) habit_id ni topadi.
    html += cityBuildingSVG(b.type, stage, cx, cy, b.habit_id);
  }
  return html;
}

// ── Eslatma kelajakdagi bosqichlar uchun ──
// PHASE C3.2:  ✅ binolar — bir xil standart kub, faqat stage bo'yicha balandlik
// PHASE C3.3:  ⏭️ dekoratsiyalar — KEYINGA QOLDIRILDI. Sabab: kichik izometrik
//   primitivlar bilan tanib bo'ladigan daraxt/mashina/favvora yasash qiyin,
//   natija abstrakt/bee'xshov chiqdi. Kelajakda professional SVG ikonkalar bilan
//   qilinadi (kod bilan emas). Backend place_decoration/DECORATION_TYPES tayyor turadi.
// PHASE C3.4:  premium CSS polish (soyalar, 3D effekt finetune)
// PHASE C3.5a: ✅ glass wireframe — qurilmagan qism shaffof yuz + qirra chiziq
//   (motivatsion vizual: "binom qaysi balandlikka o'sayotganini ko'rib turaman").
//   Stage 4 da glass yo'q. style.css ga yangi class kerak (.city-bld-glass-*,
//   .city-bld-glass-edge) — Qoida #11 consistency.
// PHASE C3.5b: ⏭️ bino ustida odat nomi (label) — habit_name manbasi aniqlangach
//   alohida bosqich. Variant: backend api_city_get ga habit_name qo'shish YOKI
//   frontend _habitsCache (agar mavjud bo'lsa) dan o'qish.
// PHASE C5:    ✅ data-habit-id atributi <g> da tayyor — bino bilan interaktivlik
//              (long-press → bino ko'chirish) shu atributdan habit_id ni o'qiydi.
//              Bino bosish modali (change_type) — A varianti bilan OLIB TASHLANDI.
// BACKEND (alohida bosqich): find_empty_slot (city_logic.py) — yangi bino atrofida
//   bittadan bo'sh katak qoldirish qoidasi. Hozir faqat band bo'lmagan katak topadi;
//   "atrofi ham bo'sh" qoidasi keyin qo'shiladi (create_building + place_decoration
//   ikkalasiga ta'sir qiladi — Qoida #9-10).