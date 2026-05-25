// ==============================================
// app-city-buildings.js — Shahar binolari (PHASE C3.5c: odat nomi label)
// ==============================================
// Bog'liqlik:
//   - app-city.js (CITY_TILE_H, CITY_BLD_BASE_W/H, CITY_STAGE_THRESHOLDS,
//     cityIsoX/cityIsoY — shu fayldan import qilinadi)
//   - config.py BUILDING_TYPES (10 bino turi) va BUILDING_STAGE_THRESHOLDS bilan SINXRON
//
// VAZIFA: barcha bino BIR XIL standart kub — o'lcham/shakl farqi YO'Q.
//   QAROR (C3.2): har odat 66 kunda shakllanadi. Agar binolar har xil bo'lsa,
//   foydalanuvchi chalg'iydi. Bir xil bo'lsa — diqqat faqat QURILISH BOSQICHIGA
//   qaratiladi: "odatimni qanchalik yaxshi quryapman?". Bu habit tracker
//   mantig'iga mos. Bino TURI faqat data-type atributida saqlanadi. Bino bilan
//   interaktivlik (long-press → ko'chirish) data-habit-id atributiga tayanadi.
//   (Avvalgi CITY_BLD_SHAPES o'lcham tizimi va cityCapSVG cap tizimi — o'chirildi.
//    Kerak bo'lsa git tarixida bor; "kerak bo'lar" deb o'lik kod saqlamaymiz.)
//
// PHASE C3.5a (glass — qurilmagan qism vizualizatsiyasi): bino 2 qismdan iborat:
//   1. SOLID qism (qurilgan) — to'liq rangli kub
//   2. GLASS qism (qurilmagan) — to'liq balandlikkacha bo'sh joy, solid bino
//      yuzlari bilan AYNI rang, lekin yarim shaffof (CSS fill-opacity 0.5).
//      Foydalanuvchi "binom kelajakda qanday ko'rinishini" yarim ko'radi →
//      motivatsion vizual. (Avval wireframe qirra chiziqlar bor edi — binolar
//      yaqin turganda chiziqlar bir-biriga aralashib shovqin yaratardi.
//      C3.5d da olib tashlandi, yuzlarning o'zi 50% xira qilindi.)
//
// PHASE C3.5b (uzluksiz balandlik): solid qism balandligi STAGE'ga emas,
//   PROGRESS'ga (kun soni 0-66) chiziqli bog'langan. Sabab: stage tizimida
//   9-kun va 12-kun bir xil ko'rinardi (ikkalasi ham stage 0). Endi HAR kun
//   farq qiladi — 1 ortiqcha bajarilgan kun ham seziladi. cityBuildingHeight()
//   funksiyasi: progress 1 → CITY_BLD_MIN_HEIGHT (8px), progress 66 →
//   CITY_BLD_FULL_HEIGHT (84px), oraliq — chiziqli interpolyatsiya.
//   stage HALI ham hisoblanadi — faqat data-stage atributi uchun (kelajakda
//   kerak bo'lishi mumkin; balandlikka TA'SIR QILMAYDI).
//
// MUHIM (Qoida #24): bu fayl app-city.js dan AJRATILGAN. index.html da
//   app-city.js dan KEYIN yuklanadi (konstantalar avval e'lon qilinishi kerak).
// ==============================================

// ── Bino balandlik konstantalari (Qoida #17 — magic number markazlash) ──
// CITY_BLD_FULL_HEIGHT: progress 66 (to'liq shakllangan odat) dagi balandlik.
//   Glass qism solid qism tepasidan shu balandlikkacha cho'ziladi.
// CITY_BLD_MIN_HEIGHT: progress 1 (endigina boshlangan odat) dagi balandlik.
//   0 emas — 1 kun bajargan foydalanuvchi ham kichik poydevor ko'rishi kerak.
//   progress 0 (umuman bajarilmagan) — alohida holat, height 0 (pastda).
const CITY_BLD_FULL_HEIGHT = 84;
const CITY_BLD_MIN_HEIGHT  = 8;
const CITY_BLD_MAX_PROGRESS = 66;   // to'liq shakllangan odat (config.py bilan SINXRON)

// ── Bino label (odat nomi) konstantasi (C3.5c — Qoida #17) ──
// CITY_BLD_LABEL_MAX: label'da ko'rsatiladigan maksimal belgi soni. Uzun
//   odat nomi bino tagiga sig'maydi — bundan oshsa "…" bilan qisqartiriladi.
const CITY_BLD_LABEL_MAX = 12;

// ── progress (kun) → solid kub balandligi (px) — UZLUKSIZ (C3.5b) ──
// Chiziqli interpolyatsiya: progress 1 → MIN (8px), progress 66 → FULL (84px).
// progress 0 → 0 (bino yo'q, faqat glass karkas ko'rinadi).
// progress > 66 bo'lsa ham FULL bilan cheklanadi (xavfsizlik).
function cityBuildingHeight(progress) {
  const p = Math.max(0, Math.min(CITY_BLD_MAX_PROGRESS, progress || 0));
  if (p <= 0) return 0;
  // p=1 → MIN, p=66 → FULL. Oraliq chiziqli:
  //   height = MIN + (p - 1) / (MAX - 1) * (FULL - MIN)
  const ratio = (p - 1) / (CITY_BLD_MAX_PROGRESS - 1);
  return CITY_BLD_MIN_HEIGHT + ratio * (CITY_BLD_FULL_HEIGHT - CITY_BLD_MIN_HEIGHT);
}

// ── progress (kun) → stage (0-4) ──
// config.py BUILDING_STAGE_THRESHOLDS bilan SINXRON (Qoida #11).
// progress <= 13 → stage 0, <= 26 → 1, <= 39 → 2, <= 52 → 3, qolgani → 4.
// C3.5b: stage endi BALANDLIKKA TA'SIR QILMAYDI — faqat data-stage atributi
//   uchun hisoblanadi (kelajakda kerak bo'lishi mumkin). Balandlik —
//   cityBuildingHeight() (uzluksiz).
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

// ── Label matnini tayyorlash (C3.5c — yordamchi) ──
// raw: odat nomi (foydalanuvchi yozgan — har qanday belgi bo'lishi mumkin).
// Qaytaradi: xavfsiz, qisqartirilgan matn (SVG <text> ichiga qo'yish uchun).
//   1. Bo'sh/yo'q bo'lsa — bo'sh string (label chizilmaydi).
//   2. CITY_BLD_LABEL_MAX dan uzun bo'lsa — kesilib "…" qo'shiladi.
//   3. XSS himoyasi: <, >, & belgilari HTML entity'ga aylantiriladi
//      (innerHTML orqali SVG quriladi — escape SHART).
function cityLabelText(raw) {
  let s = (raw == null) ? '' : String(raw).trim();
  if (!s) return '';
  if (s.length > CITY_BLD_LABEL_MAX) {
    s = s.slice(0, CITY_BLD_LABEL_MAX) + '…';
  }
  // HTML/SVG escape — innerHTML orqali quriladi (Qoida #06 — apostrof emas,
  // lekin <>& belgilari SVG'ni buzishi mumkin).
  return s.replace(/&/g, '&amp;')
          .replace(/</g, '&lt;')
          .replace(/>/g, '&gt;');
}

// ── Bitta bino SVG'si (izometrik kub, SOLID + GLASS qatlamlar + LABEL) ──
// type: bino turi (config.py BUILDING_TYPES kaliti — faqat data-type atributi uchun,
//   o'lchamga TA'SIR QILMAYDI).
// progress: bajarilgan kun soni (0-66) — solid kub balandligini UZLUKSIZ belgilaydi
//   (C3.5b: stage emas — progress; har kun farq qiladi).
// cx, cy: katak rombning MARKAZIY nuqtasi (cityIsoX/cityIsoY + romb markazi).
// habitId: bino bog'liq odat id'si — <g> ga data-habit-id atributi sifatida
//   yoziladi. Bino bilan interaktivlik (long-press → bino ko'chirish) shu
//   atributdan habit_id ni o'qib, move_item API'ga yuboradi.
// habitName: odat nomi (foydalanuvchi yozgan, tarjima QILINMAYDI) — bino USTIDA
//   <text> label sifatida ko'rsatiladi (C3.5c). Uzun bo'lsa qisqartiriladi.
//
// QATLAMLAR (C3.5a + C3.5b + C3.5c):
//   1. SOLID kub — qurilgan qism (progress'ga mos UZLUKSIZ balandlikda)
//   2. GLASS kub — qurilmagan qism (solid TEPASIDAN to'liq balandlikkacha).
//      progress 66 ga yetganda glass chizilmaydi (bino to'liq qurilgan).
//   3. LABEL — odat nomi, bino ustida (<text>). <g> ICHIDA — bino
//      ko'chirilganda (drag) label ham birga harakatlanadi.
//
// data-stage atributi uchun cityBuildingStage() ham chaqiriladi (balandlikka
//   ta'sir qilmaydi — faqat atribut; kelajakda kerak bo'lishi mumkin).
//
// Qaytaradi: <g> ichida solid 3 polygon + (agar progress<66) glass + label <text>.
function cityBuildingSVG(type, progress, cx, cy, habitId, habitName) {
  const bw = CITY_BLD_BASE_W / 2;          // asos yarim kengligi (barcha bino bir xil)
  const bh = CITY_BLD_BASE_H / 2;          // asos yarim balandligi (barcha bino bir xil)
  const hSolid = cityBuildingHeight(progress);  // solid kub balandligi (UZLUKSIZ — C3.5b)
  const stage  = cityBuildingStage(progress);   // faqat data-stage atributi uchun

  // 1. SOLID kub (qurilgan qism) — pastdan hSolid balandlikgacha
  const solidFaces = cityCubeFaces(cx, cy, bw, bh, hSolid);

  let svg = `<g class="city-bld" data-type="${type}" data-stage="${stage}" data-habit-id="${habitId}">`;
  svg += `<polygon class="city-bld-left"  points="${solidFaces.leftFace}"/>`;
  svg += `<polygon class="city-bld-right" points="${solidFaces.rightFace}"/>`;
  svg += `<polygon class="city-bld-top"   points="${solidFaces.topFace}"/>`;

  // 2. GLASS kub (qurilmagan qism) — solid tepasidan to'liq balandlikkacha
  // Glass kub PASTKI markazi = solid kub TEPASI = (cx, cy - hSolid)
  // Glass kub balandligi = to'liq balandlik - solid balandlik
  // hGlass <= 0 bo'lsa (progress 66 — to'liq qurilgan) glass chizilmaydi.
  {
    const hGlass = CITY_BLD_FULL_HEIGHT - hSolid;  // qolgan balandlik
    if (hGlass > 0) {
      // Glass kub asosi solid tepasiga "yotqizilgan" — bh=0 (asos romb tekis chiziq)
      // bo'lmasligi uchun solid bilan AYNI bw/bh ishlatamiz. Glass kub PASTKI
      // markazi (cx, cy - hSolid) — solid tepa romb markazi.
      const glassFaces = cityCubeFaces(cx, cy - hSolid, bw, bh, hGlass);
      // Glass yuzlar (C3.5d): solid bino YUZLARI bilan AYNI rang, yarim shaffof
      //   (fill-opacity 0.5 — CSS da). Wireframe qirra chiziqlar OLIB TASHLANDI —
      //   binolar yaqin turganda chiziqlar bir-biriga aralashib vizual shovqin
      //   yaratardi. Endi glass kub xuddi solid kub "kelajakdagi koʻrinishidek"
      //   yarim ko'rinadi — toza, motivatsion vizual.
      svg += `<polygon class="city-bld-glass-left"  points="${glassFaces.leftFace}"/>`;
      svg += `<polygon class="city-bld-glass-right" points="${glassFaces.rightFace}"/>`;
      svg += `<polygon class="city-bld-glass-top"   points="${glassFaces.topFace}"/>`;
    }
  }

  // 3. LABEL — odat nomi, bino USTIDA (<text>) — C3.5c.
  // Variant A: barcha label GLASS karkas cho'qqisi tepasida — bir xil tekislik
  //   (binolar har xil balandlikda bo'lsa ham label tartibli, o'qilishi oson).
  // Glass karkas cho'qqisi = asos romb tepa cho'qqisi (cy - bh) dan to'liq
  //   balandlik (CITY_BLD_FULL_HEIGHT) yuqorida. Label undan yana 10px tepada.
  // text-anchor=middle — matn cx ga nisbatan markazlashadi.
  const label = cityLabelText(habitName);
  if (label) {
    const labelY = cy - bh - CITY_BLD_FULL_HEIGHT - 10;  // glass cho'qqi + 10px tepada
    svg += `<text class="city-bld-label" x="${cx}" y="${labelY}" text-anchor="middle">${label}</text>`;
  }

  svg += `</g>`;
  return svg;
}

// ── Barcha binolarni render qilish (painter's algorithm) ──
// buildings: [{habit_id, type, x, y, progress, habit_name}, ...]
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
    // Katak rombning markaziy nuqtasi: cityIsoX/Y top cho'qqini beradi,
    // markazga yetish uchun +CITY_TILE_H/2 (romb vertikal markazi).
    const cx = cityIsoX(b.x, b.y);
    const cy = cityIsoY(b.x, b.y) + CITY_TILE_H / 2;
    // C3.5b: cityBuildingSVG endi progress (kun soni) qabul qiladi — balandlik
    //   uzluksiz hisoblanadi. stage cityBuildingSVG ichida data-stage uchun
    //   hisoblanadi (bu yerda alohida chaqirish kerak emas).
    // C3.5c: b.habit_name (API javobida) — bino ustidagi label.
    // b.habit_id ham uzatiladi — data-habit-id atributi orqali bino bilan
    //   interaktivlik (long-press ko'chirish) habit_id ni topadi.
    html += cityBuildingSVG(b.type, b.progress, cx, cy, b.habit_id, b.habit_name);
  }
  return html;
}

// ── Eslatma kelajakdagi bosqichlar uchun ──
// PHASE C3.2:  ✅ binolar — bir xil standart kub
// PHASE C3.3:  ⏭️ dekoratsiyalar — KEYINGA QOLDIRILDI. Sabab: kichik izometrik
//   primitivlar bilan tanib bo'ladigan daraxt/mashina/favvora yasash qiyin,
//   natija abstrakt/bee'xshov chiqdi. Kelajakda professional SVG ikonkalar bilan
//   qilinadi (kod bilan emas). Backend place_decoration/DECORATION_TYPES tayyor turadi.
// PHASE C3.4:  premium CSS polish (soyalar, 3D effekt finetune)
// PHASE C3.5a: ✅ glass — qurilmagan qism shaffof yuz (motivatsion vizual).
//   style-city.css da .city-bld-glass-* class'lar.
// PHASE C3.5d: ✅ wireframe qirra chiziqlar OLIB TASHLANDI — binolar yaqin
//   turganda 8 ta chiziq har bino tepasida vizual shovqin yaratardi. Endi
//   glass yuzlar solid yuzlar bilan AYNI rangda, fill-opacity 0.5 — toza
//   "yarim shaffof bino" effekti. .city-bld-glass-edge CSS klassi olib tashlandi.
// PHASE C3.5b: ✅ uzluksiz balandlik — solid kub balandligi stage'ga emas,
//   progress'ga (0-66 kun) chiziqli bog'langan. cityBuildingHeight() funksiyasi.
//   Har bajarilgan kun farq qiladi. cityBuildingStage() saqlangan — faqat
//   data-stage atributi uchun (balandlikka ta'sir qilmaydi).
// PHASE C3.5c: ✅ odat nomi label — bino ustida <text> (foydalanuvchi yozgan
//   nom, tarjima qilinmaydi; 12 belgidan uzun bo'lsa "…" bilan qisqartiriladi).
//   Backend api_city_get javobiga habit_name qo'shilgan. style-city.css da
//   .city-bld-label class. Label <g> ichida — drag paytida bino bilan ko'chadi.
// PHASE C5:    ✅ data-habit-id atributi <g> da tayyor — bino bilan interaktivlik
//              (long-press → bino ko'chirish) shu atributdan habit_id ni o'qiydi.
//              Bino bosish modali (change_type) — A varianti bilan OLIB TASHLANDI.
// BACKEND (alohida bosqich): find_empty_slot (city_logic.py) — yangi bino atrofida
//   bittadan bo'sh katak qoldirish qoidasi. Hozir faqat band bo'lmagan katak topadi;
//   "atrofi ham bo'sh" qoidasi keyin qo'shiladi (create_building + place_decoration
//   ikkalasiga ta'sir qiladi — Qoida #9-10).