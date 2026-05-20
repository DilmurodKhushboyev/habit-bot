// ==============================================
// app-city-modal.js — Shahar bino bosish modali (PHASE C5: change_type)
// ==============================================
// Bog'liqlik:
//   - app-city.js (_cityData kesh — bino ma'lumoti shu yerdan olinadi qayta API
//     chaqirmasdan; loadCity() — change_type'dan keyin qayta yuklash; CITY_GRID_SIZE
//     emas, lekin renderCityGrid index.html da BU fayldan OLDIN yuklanadi)
//   - app-city-buildings.js (cityBuildingStage — progress→stage; .city-bld <g>
//     data-habit-id/data-type/data-progress atributlari shu fayl tomonidan yoziladi)
//   - app-core.js (apiFetch — POST /api/city/<uid>/change_type; userId; S())
//   - strings.js (S('city',...) — bino nomlari, stage nomlari, modal matnlari — C5/C7)
//   - config.py BUILDING_TYPES bilan SINXRON (Qoida #11) — pastdagi CITY_BUILDING_TYPES
//
// VAZIFA: foydalanuvchi shahar gridida binoni bossa → modal ochiladi:
//   bino turi (emoji + nom), progress (kun / 66), stage nomi, va 10 turdan
//   tanlash gridi (change_type). Tur tanlansa → POST /api/city/<uid>/change_type
//   → muvaffaqiyatda loadCity() qayta chaqiriladi (grid yangilanadi).
//
// MUHIM (Qoida #24): bu fayl app-city.js / app-city-buildings.js dan AJRATILGAN.
//   index.html da app-city-buildings.js dan KEYIN yuklanadi.
//
// SCROLL KONFLIKT (handoff eslatma): `click` event ishlatiladi (touchstart+touchend
//   emas) — grid diagonal scroll bilan to'qnashmaydi. Long-press (bino ko'chirish)
//   C5 da QILINMAYDI — touch pan yo'q (C2.2 o'tkazib yuborilgan), ko'chirish C6+ da.
// ==============================================

// ── BINO TURLARI (Qoida #11 — config.py BUILDING_TYPES bilan SINXRON) ──
// config.py: BUILDING_TYPES = {"stadium": {"emoji": "🏟️", "name_key": "city_bld_stadium"}, ...}
// Bu yerda name_key O'RNIGA strings.js kaliti (S('city', name)) — frontend tarjima.
// Tartib config.py bilan bir xil. Birini o'zgartirsangiz — config.py ni ham (Qoida #11).
const CITY_BUILDING_TYPES = [
  { type: 'stadium',  emoji: '🏟️', name: 'bld_stadium'  },
  { type: 'library',  emoji: '📚', name: 'bld_library'  },
  { type: 'mosque',   emoji: '🕌', name: 'bld_mosque'   },
  { type: 'school',   emoji: '🎓', name: 'bld_school'   },
  { type: 'park',     emoji: '🌳', name: 'bld_park'     },
  { type: 'cafe',     emoji: '☕', name: 'bld_cafe'     },
  { type: 'bank',     emoji: '🏦', name: 'bld_bank'     },
  { type: 'hospital', emoji: '🏥', name: 'bld_hospital' },
  { type: 'studio',   emoji: '🎨', name: 'bld_studio'   },
  { type: 'house',    emoji: '🏠', name: 'bld_house'    },
];

// ── STAGE NOMLARI (Qoida #11 — config.py BUILDING_STAGE_THRESHOLDS izohlari bilan) ──
// config.py: Stage 0 foundation, 1 skeleton, 2 walls, 3 roof, 4 complete.
// Indeks = stage raqami (cityBuildingStage natijasi 0-4).
const CITY_STAGE_NAME_KEYS = [
  'stage_foundation', 'stage_skeleton', 'stage_walls', 'stage_roof', 'stage_complete',
];

// Max progress (kun) — config.py BUILDING_DAYS=66 bilan sinxron, "kun / 66" uchun.
const CITY_BUILDING_DAYS = 66;

// change_type so'rovi davom etayotganini bildiruvchi lock (double-tap himoya, §shop pattern)
let _cityModalLock = false;

// ── XSS himoya: bino turini topib bo'lmasa fallback uchun ──
function _cityEscHtml(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

// ── Bino turi konfiguratsiyasini kalit bo'yicha topish ──
// Topilmasa (eski/noma'lum tur) — null qaytaradi, chaqiruvchi fallback qiladi.
function _cityFindTypeConfig(type) {
  for (const t of CITY_BUILDING_TYPES) {
    if (t.type === type) return t;
  }
  return null;
}

// ── Grid'ga bino bosish handlerini ulash (renderCityGrid oxirida chaqiriladi) ──
// `click` event — diagonal scroll bilan to'qnashmaydi (handoff eslatma).
// SVG <g class="city-bld"> ichidagi <polygon> bosilsa ham — closest() bilan
// ota <g> topiladi, undan data-habit-id o'qiladi.
// data-swipeInit kabi double-bind himoya: renderCityGrid har safar yangi DOM
// yaratadi, shuning uchun guard shart emas — lekin ehtiyot uchun konteynerga
// bitta delegated listener qo'yamiz.
function initCityBuildingClick(container) {
  if (!container) return;
  const svg = container.querySelector('.city-canvas');
  if (!svg) return;
  svg.addEventListener('click', function (e) {
    const g = e.target.closest('.city-bld');
    if (!g) return;  // bino emas, bo'sh katak bosildi — e'tibor bermaymiz
    const habitId = g.getAttribute('data-habit-id');
    if (!habitId) return;
    openCityBuildingModal(habitId);
  });
}

// ── Bino bosish modalini ochish ──
// habitId — .city-bld <g> data-habit-id atributidan. Bino ma'lumoti _cityData
// keshidan topiladi (qayta API chaqirilmaydi — handoff: "_cityData dan habit_id
// bo'yicha topadi").
function openCityBuildingModal(habitId) {
  // _cityData app-city.js da global — null bo'lsa (xato holati) modal ochilmaydi
  if (!_cityData || !Array.isArray(_cityData.buildings)) return;
  let building = null;
  for (const b of _cityData.buildings) {
    if (String(b.habit_id) === String(habitId)) { building = b; break; }
  }
  if (!building) return;  // bino topilmadi (kesh eskirgan) — sukut

  // Eski modal qolgan bo'lsa olib tashlaymiz (double-open himoya)
  closeCityBuildingModal();

  const overlay = document.createElement('div');
  overlay.className = 'shop-modal-overlay city-modal-overlay';
  overlay.id = 'city-bld-modal';
  overlay.innerHTML = _renderCityModalBody(building);

  // Overlay'ning o'zi (fon) bosilsa — yopiladi (shop modal patterni)
  overlay.addEventListener('click', function (e) {
    if (e.target === overlay) closeCityBuildingModal();
  });

  document.body.appendChild(overlay);
  // requestAnimationFrame → .show klassi fade/scale animatsiyani ishga tushiradi
  requestAnimationFrame(function () { overlay.classList.add('show'); });
}

// ── Modal ichki HTML'i ──
// building: {habit_id, type, x, y, progress, stage} — _cityData.buildings elementi.
function _renderCityModalBody(building) {
  const cfg = _cityFindTypeConfig(building.type);
  // Noma'lum tur (eski user) — fallback: 🏠 + xom kalit nomi
  const emoji = cfg ? cfg.emoji : '🏠';
  const name  = cfg ? S('city', cfg.name) : _cityEscHtml(building.type);

  // Progress 0-66 ga clamp (xavfsizlik — backend yuborgan qiymat)
  const progress = Math.max(0, Math.min(CITY_BUILDING_DAYS, building.progress || 0));
  // Stage: app-city-buildings.js cityBuildingStage (progress→0-4) bilan SINXRON
  const stage = cityBuildingStage(progress);
  const stageName = S('city', CITY_STAGE_NAME_KEYS[stage] || CITY_STAGE_NAME_KEYS[0]);
  const pct = Math.round(progress / CITY_BUILDING_DAYS * 100);

  // 10 turli grid — joriy tur .selected klassi bilan belgilanadi.
  // data-type — cityChangeType muvaffaqiyatdan keyin .selected ni ko'chirish uchun o'qiydi.
  let gridHtml = '';
  for (const t of CITY_BUILDING_TYPES) {
    const isCur = t.type === building.type;
    gridHtml += `
      <button class="city-type-btn${isCur ? ' selected' : ''}" type="button"
              data-type="${t.type}"
              onclick="cityChangeType('${_cityEscHtml(building.habit_id)}','${t.type}')">
        <span class="city-type-emoji">${t.emoji}</span>
        <span class="city-type-name">${S('city', t.name)}</span>
      </button>`;
  }

  return `
    <div class="shop-modal-box city-modal-box">
      <button class="city-modal-close" type="button" onclick="closeCityBuildingModal()" aria-label="close">✕</button>
      <div class="city-modal-emoji">${emoji}</div>
      <div class="city-modal-title">${name}</div>
      <div class="city-modal-stage">${stageName}</div>
      <div class="city-modal-progress">
        <div class="city-modal-progress-row">
          <span class="city-modal-progress-days">${progress} / ${CITY_BUILDING_DAYS} ${S('city', 'modal_day')}</span>
          <span class="city-modal-progress-pct">${pct}%</span>
        </div>
        <div class="city-modal-progress-track">
          <div class="city-modal-progress-fill" style="width:${pct}%"></div>
        </div>
      </div>
      <div class="city-modal-section-label">${S('city', 'modal_change_type')}</div>
      <div class="city-type-grid">${gridHtml}</div>
    </div>
  `;
}

// ── Modalni yopish ──
// .show klassini olib tashlaydi (fade-out), keyin DOM'dan o'chiradi.
function closeCityBuildingModal() {
  const overlay = document.getElementById('city-bld-modal');
  if (!overlay) return;
  overlay.classList.remove('show');
  // CSS transition .2s — shundan keyin DOM'dan olib tashlaymiz
  setTimeout(function () {
    if (overlay && overlay.parentNode) overlay.parentNode.removeChild(overlay);
  }, 220);
}

// ── Bino turini o'zgartirish (change_type) ──
// POST /api/city/<uid>/change_type body {habit_id, building_type}.
// Backend tayyor (flask_routes_city.py — javob: {ok, building_type, progress}).
//
// MUHIM (C5 FIX): barcha bino BIR XIL oq kub (C3.2 qarori) — turi o'zgarsa ham
//   grid'dagi kub VIZUAL O'ZGARMAYDI (faqat data-type atributi). Shuning uchun
//   foydalanuvchi o'zgarishni faqat MODAL ichida ko'radi. Yechim: muvaffaqiyatdan
//   keyin modal'dagi .selected klassi yangi tugmaga ko'chiriladi (darhol ko'rinadi,
//   showToast bor-yo'qligiga bog'liq emas). _cityData ham lokal yangilanadi.
async function cityChangeType(habitId, newType) {
  if (_cityModalLock) return;  // change_type davom etyapti — ikkinchi bosish bekor

  // Joriy bino _cityData keshidan topiladi
  let building = null;
  if (_cityData && Array.isArray(_cityData.buildings)) {
    for (const b of _cityData.buildings) {
      if (String(b.habit_id) === String(habitId)) { building = b; break; }
    }
  }
  // Joriy tur tanlangan bo'lsa — o'zgartirishga hojat yo'q (API ham chaqirilmaydi)
  if (building && building.type === newType) return;

  _cityModalLock = true;
  // Bosilgan tugmaga "kutilmoqda" holati (visual feedback — showToast'ga bog'liq emas)
  const overlay = document.getElementById('city-bld-modal');
  const grid = overlay ? overlay.querySelector('.city-type-grid') : null;
  if (grid) grid.classList.add('city-type-grid-loading');

  try {
    const res = await apiFetch('city/' + userId + '/change_type', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ habit_id: habitId, building_type: newType }),
    });
    if (!res || !res.ok) throw new Error('change_type_failed');

    // Muvaffaqiyat — backend javobidagi building_type ni ishonchli manba deb olamiz
    const confirmedType = res.building_type || newType;
    // 1) _cityData keshini lokal yangilash (qayta GET'siz ham to'g'ri qoladi)
    if (building) building.type = confirmedType;
    // 2) Modal'dagi .selected klassini yangi tugmaga ko'chirish — DARHOL ko'rinadi
    if (grid) {
      const btns = grid.querySelectorAll('.city-type-btn');
      btns.forEach(function (btn) {
        const isSel = btn.getAttribute('data-type') === confirmedType;
        btn.classList.toggle('selected', isSel);
      });
    }
    // 3) Toast (agar showToast global bo'lsa) — ikkilamchi feedback
    if (typeof showToast === 'function') showToast(S('city', 'type_changed'));
    // 4) Grid'ni qayta yuklash — data-type atributi yangilanadi (vizual bir xil
    //    bo'lsa-da, keyingi bosishlar to'g'ri turdan boshlanadi). loadCity _cityData
    //    ni ham qayta to'ldiradi — lekin biz allaqachon lokal yangiladik (yuqorida).
    if (typeof loadCity === 'function') await loadCity();
  } catch (e) {
    // Xato — modal ochiq qoladi. showToast bor bo'lsa toast, bo'lmasa grid silkinadi.
    if (typeof showToast === 'function') {
      showToast(S('msg', 'connection_error'), true);
    } else if (grid) {
      // Fallback feedback: grid qisqa "silkinish" animatsiyasi (showToast yo'q bo'lsa)
      grid.classList.add('city-type-grid-error');
      setTimeout(function () { grid.classList.remove('city-type-grid-error'); }, 500);
    }
  } finally {
    _cityModalLock = false;
    if (grid) grid.classList.remove('city-type-grid-loading');
  }
}

// ── Eslatma kelajakdagi bosqichlar uchun ──
// PHASE C5:   ✅ bino bosish modali — turi/nomi/progress/stage + change_type grid — SHU YERDA
// PHASE C6:   dekoratsiya bozor modali (buy_decoration, buy_insurance)
// PHASE C7:   tarjimalar to'liq kengaytirish (C5 da city.* kalitlar qo'shildi)
// Bino ko'chirish (move): touch pan yo'q (C2.2 o'tkazib yuborilgan) — long-press
//   pattern keyingi bosqichlarda, hozir change_type yetarli (handoff: "ixtiyoriy").
