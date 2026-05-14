// ==============================================
// app-city.js — Shahar sahifasi (PHASE C3.2: grid + demo binolar)
// ==============================================
// Bog'liqlik:
//   - app-city-buildings.js (bino render: cityBuildingStage, cityBuildingSVG,
//     renderCityBuildings — index.html da BU fayldan KEYIN yuklanadi)
//   - strings.js (S() funksiya — tarjima; hozir ishlatilmaydi, C7 da kerak)
//   - app-core.js (loaded state — sahifa yuklanganini belgilash)
//   - config.py BUILDING_STAGE_THRESHOLDS bilan SINXRON (Qoida #11)
//
// PHASE C2.1: 30×30 = 900 katak isometric grid (statik, scroll bilan).
// PHASE C2.2/C2.3 (pan/zoom): YAGNI sababli o'tkazib yuborilgan.
// PHASE C3.1: demo binolar (5 stage), monoxrom oq clay render uslubi.
// PHASE C3.2: 10 bino turi — barchasi BIR XIL standart kub (o'lcham/shakl farqi yo'q),
//             faqat stage bo'yicha balandlik o'zgaradi. Bino mantiqi
//             app-city-buildings.js da (Qoida #24). Demo data — binolar orasida
//             2 katak masofa. API YO'Q (C4 da GET /api/city/<uid> bilan almashtiriladi).
// ==============================================

// ── ISOMETRIC GRID KONSTANTLARI (Qoida #17 — magic number'larni markazlash) ──
// Klassik 2:1 isometric nisbat — eng keng tarqalgan va eng tabiiy ko'rinish.
// Bu konstantalar app-city-buildings.js da ham ishlatiladi (global scope).
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
// Kub asosi katak romb o'lchamidan kichik — binolar orasida bo'shliq qoladi,
// shahar "havodor" ko'rinadi va atrofni ko'rish osonroq (foydalanuvchi tanlovi).
const CITY_BLD_BASE_W = 60;   // kub asos kengligi (px) — CITY_TILE_W=80 dan kichik
const CITY_BLD_BASE_H = 30;   // kub asos balandligi (px) — CITY_TILE_H=40 dan kichik (2:1)
// Stage bo'yicha kub balandligi (vertikal — px). Stage 0 past poydevor, 4 to'liq.
const CITY_BLD_HEIGHTS = [14, 34, 58, 84, 84];  // stage 0..4 balandlik

// ── DEMO DATA (C4 da GET /api/city/<uid> javobi bilan almashtiriladi) ──
// Backend formatida: buildings massivi. Har bino: {habit_id, type, x, y, progress}.
// progress (0-66 kun) → cityBuildingStage() orqali stage'ga aylantiriladi.
// Grid markazi 14-16 atrofida — auto-scroll shu yerni ko'rsatadi.
//
// JOYLASHUV QOIDASI: binolar orasida kamida 2 katak masofa — har bino aniq
//   ko'rinadi, bir-birini to'smaydi. Bu C5 (bino siljitish) uchun ham asos:
//   o'yinlarda bino atrofida bo'sh joy bo'lishi kerak. Hozir bu demo data'da
//   qo'lda; backend find_empty_slot bu qoidani majburlashi — alohida bosqich.
//
// Binolar 3 katak qadam bilan joylashgan (x va y bo'yicha) — orasida 2 bo'sh katak.
// Har xil stage — qurilish bosqichlari ko'rinadi.
const _cityDemoData = {
  buildings: [
    { habit_id: "demo1", type: "mosque",  x: 12, y: 12, progress: 66 }, // stage 4
    { habit_id: "demo2", type: "house",   x: 15, y: 12, progress: 48 }, // stage 3
    { habit_id: "demo3", type: "library", x: 18, y: 12, progress: 33 }, // stage 2
    { habit_id: "demo4", type: "school",  x: 12, y: 15, progress: 20 }, // stage 1
    { habit_id: "demo5", type: "bank",    x: 15, y: 15, progress: 5  }, // stage 0
    { habit_id: "demo6", type: "cafe",    x: 18, y: 15, progress: 66 }, // stage 4
    { habit_id: "demo7", type: "park",    x: 12, y: 18, progress: 48 }, // stage 3
    { habit_id: "demo8", type: "studio",  x: 15, y: 18, progress: 33 }, // stage 2
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
//  BINOLAR — app-city-buildings.js ga AJRATILGAN (Qoida #24)
// ════════════════════════════════════════════════
// cityBuildingStage(), cityBuildingSVG(), renderCityBuildings() va bino shakl
// konfiguratsiyalari app-city-buildings.js da. Bu fayl ulardan FAQAT renderCityGrid
// ichida foydalanadi (yuqorida `renderCityBuildings(_cityDemoData.buildings)`).
// index.html da app-city-buildings.js shu fayldan KEYIN yuklanadi — chunki u shu
// yerdagi konstantalarga (CITY_TILE_H, CITY_BLD_*, cityIsoX/Y) bog'liq.

// ── Eslatma kelajakdagi bosqichlar uchun ──
// PHASE C2.2/C2.3: touch pan/zoom — YAGNI sababli o'tkazib yuborilgan
// PHASE C3.1: ✅ demo binolar (5 stage, oq clay render)
// PHASE C3.2: ✅ shakl-asosida bino turlari (app-city-buildings.js) — SHU YERDA
// PHASE C3.3: 5 dekoratsiya (tree/flower/car/bench/fountain)
// PHASE C3.4: premium CSS polish (soyalar, 3D effekt finetune)
// PHASE C4:   loadCityFromAPI() — GET /api/city/<uid> (_cityDemoData ni almashtiradi)
// PHASE C5:   bino bosish modali (change_type) + bino ko'chirish (long-press)
// PHASE C6:   renderDecorationsShop() — bozor modal
// PHASE C7:   tarjimalar strings.js'ga qo'shiladi (10 bino + 5 dekoratsiya nomlari)
// PHASE C8:   premium CSS polish (beige/gold accent — agar kerak bo'lsa)
