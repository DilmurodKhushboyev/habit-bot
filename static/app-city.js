// ==============================================
// app-city.js — Shahar sahifasi (PHASE C4: API integratsiya)
// ==============================================
// Bog'liqlik:
//   - app-city-buildings.js (bino render: cityBuildingStage, cityBuildingSVG,
//     renderCityBuildings — index.html da BU fayldan KEYIN yuklanadi)
//   - app-core.js (apiFetch — GET /api/city/<uid>; userId; S() msg.connection_error;
//     loaded state — sahifa yuklanganini belgilash)
//   - strings.js (S() funksiya — hozir faqat msg.connection_error; city.* C7 da)
//   - config.py BUILDING_STAGE_THRESHOLDS bilan SINXRON (Qoida #11)
//
// PHASE C2.1: 30×30 = 900 katak isometric grid (statik, scroll bilan).
// PHASE C2.2/C2.3 (pan/zoom): YAGNI sababli o'tkazib yuborilgan.
// PHASE C3.1: demo binolar (5 stage), monoxrom oq clay render uslubi.
// PHASE C3.2: 10 bino turi — barchasi BIR XIL standart kub (o'lcham/shakl farqi yo'q),
//             faqat stage bo'yicha balandlik o'zgaradi. Bino mantiqi
//             app-city-buildings.js da (Qoida #24).
// PHASE C3.3: dekoratsiyalar — KEYINGA QOLDIRILDI (kichik izometrik primitivlar
//             tanib bo'lmaydigan shakl berdi). API decorations massivi render
//             qilinmaydi (professional SVG ikonkalar kelguncha).
// PHASE C4:   _cityDemoData O'CHIRILDI — loadCity() endi async, GET /api/city/<uid>
//             chaqiradi. API javobi: {buildings:[{habit_id,type,x,y,progress,stage}],
//             decorations, insurance_active, ...}. API xato bo'lsa — xato holati
//             + "Qayta urinish" tugma (soxta demo data ko'rsatilmaydi).
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
// C3.5b: CITY_BLD_HEIGHTS massivi (stage bo'yicha balandlik) OLIB TASHLANDI.
// Endi bino balandligi UZLUKSIZ — progress (0-66 kun) ga chiziqli bog'langan.
// Balandlik mantiqi app-city-buildings.js da: cityBuildingHeight() funksiyasi,
// CITY_BLD_MIN_HEIGHT / CITY_BLD_FULL_HEIGHT / CITY_BLD_MAX_PROGRESS konstantalar.

// ── API DATA (C4) ──
// _cityDemoData O'CHIRILDI — endi haqiqiy GET /api/city/<uid> javobi ishlatiladi.
// API javob formati (flask_routes_city.py api_city_get):
//   { ok, grid_size, buildings: [{habit_id, type, x, y, progress, stage}],
//     decorations: [...], insurance_active, insurance_until, version }
// buildings massivi renderCityBuildings() ga uzatiladi (interfeys o'zgarmagan).
// decorations — C3.3 da KEYINGA QOLDIRILGAN, hozir render qilinmaydi (professional
// SVG ikonkalar kerak). Backend (place_decoration) tayyor turadi, C6 da ulanadi.

// Oxirgi muvaffaqiyatli yuklangan shahar javobi — C5 (bino bosish) shu yerdan
// bino ma'lumotini oladi (qayta API chaqirmasdan). C4 da faqat saqlanadi.
let _cityData = null;

// ── Asosiy yuklash funksiyasi (loadTab tomonidan chaqiriladi) ──
// GET /api/city/<uid> chaqiradi. Loading spinner index.html da #city-content
// ichida allaqachon bor — fetch tugaguncha ko'rinib turadi.
async function loadCity() {
  const container = document.getElementById('city-content');
  if (!container) return;
  try {
    const res = await apiFetch('city/' + userId);
    if (!res || !res.ok) throw new Error('city_load_failed');
    _cityData = res;
    renderCityGrid(container, res);
  } catch (e) {
    _cityData = null;
    renderCityError(container);
  }
}

// ── Xato holati renderi (C4) ──
// API ishlamasa — soxta demo data KO'RSATILMAYDI (chalkash UX: "mening
// shahrimda nega bu binolar?"). O'rniga aniq xato + "Qayta urinish" tugma.
// Tarjima: S('msg','connection_error') — strings.js da mavjud 3 tilli kalit
// (city.* kalitlari C7 da qo'shiladi — handoff rejasi).
function renderCityError(container) {
  const msg = S('msg', 'connection_error');
  container.innerHTML = `
    <div class="city-error">
      <div class="city-error-icon">📡</div>
      <div class="city-error-msg">${msg}</div>
      <button class="city-error-btn" onclick="loadCity()">↻</button>
    </div>
  `;
}

// ── Statik isometric grid renderi (C2.1) + binolar (C4: API data) ──
// cityData — GET /api/city/<uid> javobi. cityData.buildings massivi
// renderCityBuildings() ga uzatiladi. cityData.decorations hozir ishlatilmaydi
// (C3.3 KEYINGA QOLDIRILGAN).
function renderCityGrid(container, cityData) {
  // SVG o'lchamlari — barcha kataklar to'liq sig'adigan kanvas
  // ENG ASOSIY: har bir romb cho'qqilari uchun joy ajratish kerak!
  //   - Eng chap cho'qqi: (x=0, y=29) → cx=-1160, romb chap nuqta: -1160 - 40 = -1200
  //   - Eng o'ng cho'qqi: (x=29, y=0) → cx=+1160, romb o'ng nuqta: +1160 + 40 = +1200
  //   - Eng tepa: (x=0, y=0) → cy=0 (romb tepa cho'qqisi)
  //   - Eng past: (x=29, y=29) → cy=1160, romb pastki: 1160 + 40 = 1200
  const halfW   = CITY_GRID_SIZE * (CITY_TILE_W / 2);      // 1200 — markazdan eng uzoq cx
  const halfH   = CITY_GRID_SIZE * CITY_TILE_H;            // 1200 — eng pastki cy
  // C3.5c: bino USTIDAGI label uchun tepada qo'shimcha joy. Eng yuqori bino
  //   (x=0,y=0) uchun label y ≈ cy - bh - FULL_HEIGHT - 10 ≈ -89 (manfiy).
  //   Standart viewY=-40 da label kesilardi — CITY_LABEL_HEADROOM bilan
  //   viewBox tepasi kengaytiriladi (bino tepa balandlik 84 + label + bo'shliq).
  const CITY_LABEL_HEADROOM = 110;
  // Romb cho'qqilarini ham hisobga olib, padding qo'shamiz
  const fullW   = (halfW + CITY_TILE_W / 2) * 2 + CITY_PADDING * 2;  // (1200+40)*2 + 80 = 2560
  // fullH: pastki padding + grid + tepa padding + label uchun headroom
  const fullH   = halfH + CITY_TILE_H + CITY_PADDING * 2 + CITY_LABEL_HEADROOM;  // 1430
  // viewBox markazlash: chap chetdagi rombning chap cho'qqisidan boshlanadi
  const viewX   = -(halfW + CITY_TILE_W / 2) - CITY_PADDING;  // -1280
  // viewY: standart padding + label headroom (tepada label kesilmasligi uchun)
  const viewY   = -CITY_PADDING - CITY_LABEL_HEADROOM;        // -150

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
  // C4: API javobidan keladi (_cityDemoData o'chirilgan). buildings yo'q yoki
  // bo'sh bo'lsa — bo'sh string (yangi user, hali bino yo'q → faqat grid).
  const apiBuildings = (cityData && Array.isArray(cityData.buildings))
    ? cityData.buildings : [];
  const buildingsHtml = renderCityBuildings(apiBuildings);

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

  // C5: bino bilan interaktivlik (long-press → bino ko'chirish) — keyingi qadamda
  //   shu yerga handler ulanadi. .city-bld <g> da data-habit-id atributi tayyor
  //   turadi (app-city-buildings.js) — move_item API'ga habit_id yuborish uchun.
  if (typeof initCityMoveHandlers === 'function') {
    initCityMoveHandlers(container);
  }
}

// ════════════════════════════════════════════════
//  BINOLAR — app-city-buildings.js ga AJRATILGAN (Qoida #24)
// ════════════════════════════════════════════════
// cityBuildingStage(), cityBuildingSVG(), renderCityBuildings() va bino shakl
// konfiguratsiyalari app-city-buildings.js da. Bu fayl ulardan FAQAT renderCityGrid
// ichida foydalanadi (yuqorida `renderCityBuildings(apiBuildings)`).
// index.html da app-city-buildings.js shu fayldan KEYIN yuklanadi — chunki u shu
// yerdagi konstantalarga (CITY_TILE_H, CITY_BLD_*, cityIsoX/Y) bog'liq.

// ── Eslatma kelajakdagi bosqichlar uchun ──
// PHASE C2.2/C2.3: touch pan/zoom — YAGNI sababli o'tkazib yuborilgan
// PHASE C3.1: ✅ demo binolar (5 stage, oq clay render)
// PHASE C3.2: ✅ shakl-asosida bino turlari (app-city-buildings.js)
// PHASE C3.3: 5 dekoratsiya — KEYINGA QOLDIRILGAN (professional SVG ikonkalar kerak)
// PHASE C3.4: ✅ premium CSS polish (soyalar, 3D effekt)
// PHASE C4:   ✅ loadCity() async — GET /api/city/<uid> (_cityDemoData o'chirildi) — SHU YERDA
// PHASE C5:   ✅ find_empty_slot markazga yig'ish (backend) + gap qoidasi.
//             ✅ Long-press → bino ko'chirish (drag & drop) — app-city-move.js da.
//             Bino bosish modali (change_type) — A varianti bilan olib tashlangan.
// PHASE C6:   renderDecorationsShop() — dekoratsiya bozor modali (buy_decoration, buy_insurance)
// PHASE C7:   tarjimalar strings.js'ga qo'shiladi (10 bino + 5 dekoratsiya nomlari, city.* kalitlar)
// PHASE C8:   premium CSS polish (qo'shimcha — agar kerak bo'lsa)
