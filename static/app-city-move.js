// ==============================================
// app-city-move.js — Long-press → bino ko'chirish (drag & drop)
// ==============================================
// Bog'liqlik:
//   - app-city.js (renderCityGrid initCityMoveHandlers ni chaqiradi;
//     CITY_GRID_SIZE/CITY_TILE_W/CITY_TILE_H konstantalari; cityIsoX/Y formulasi)
//   - app-city-buildings.js (.city-bld <g> data-habit-id atributi — bino ID)
//   - app-core.js (apiFetch — POST /api/city/<uid>/move; userId; S; showToast;
//     tg.HapticFeedback — Telegram vibrate)
//   - strings.js (S('city','move_failed'), S('city','moved'))
//   - city_logic.py move_item (backend) — habit_id qabul qiladi (Qoida #11)
//
// VAZIFA: foydalanuvchi binoni 2 soniya bosib tursa →
//   1) "ko'chirish rejimi" yoqiladi (bino opacity oshadi, haptic medium)
//   2) Barmoq bilan boshqa katakka sudraydi (bino barmoq ortidan ergashadi)
//   3) Qo'yib yuborsa → POST /api/city/<uid>/move {item_id, x, y}
//   4) Backend muvaffaqiyatda → bino yangi joyda qoladi (pinned=True qo'yiladi)
//   5) Backend "occupied" yoki xato → bino eski joyiga qaytadi + toast
//
// SCROLL BILAN KONFLIKT:
//   - Bosish (0-2s): scroll bloklanMAYDI (foydalanuvchi accidental press qilsa
//     scroll ishlashda davom etadi). touchmove'da agar foydalanuvchi ko'p
//     surilsa (LONGPRESS_MAX_MOVE'dan ko'p) → bu scroll deb hisoblanib,
//     long-press bekor qilinadi.
//   - Drag rejim faol (2s o'tdi): scroll BLOKLANADI (preventDefault touchmove'da).
//     Aks holda bino bilan birga sahifa ham scroll qilinardi.
// ==============================================

// ── KONFIGURATSIYA ──
const LONGPRESS_MS       = 600;   // bosish vaqti (ms) — 2s o'rniga 600ms (UX: Hay Day patterni, foydalanuvchi 2s kutmaydi)
const LONGPRESS_MAX_MOVE = 10;    // scroll deb hisoblanish chegarasi (px) bosish boshlangan nuqtadan
const DRAG_OPACITY       = 0.55;  // drag paytida BINO eski joyida shaffof

// ── HOLAT (har renderCityGrid'da reset bo'ladi) ──
let _moveState = null;
// Strukturasi (drag faol bo'lganda):
// {
//   container, svg,           // DOM ssilkalar (cleanup uchun)
//   habitId, building,        // ko'chirilayotgan bino
//   gridG,                    // bino <g> element (.city-bld) — original SVG
//   startX, startY,           // touchstart pixel (clientX/Y)
//   timerId,                  // setTimeout id (longpress)
//   active: false,            // drag rejim faolmi (true → 2s o'tdi)
//   targetX, targetY,         // hozirgi nishon katak (grid koord)
//   ghost,                    // drag paytidagi "ghost" bino (vizual)
//   highlightRect,            // drag paytida nishon katak ustidagi highlight
//   lock: false,              // API so'rovi davom etyapti (double-tap himoya)
// }

// ── Ghost qatlami (drag paytida bino barmoq ortidan ergashadi) ──
// Ghost = SVG <g> nusxa (original bino opacity DRAG_OPACITY ga tushadi).
// Ghost svg root'iga qo'shiladi va matritsa orqali siljitadi.
function _cityCreateGhost(state) {
  // Original <g> ning clone'ini olamiz (3 polygon)
  const ghost = state.gridG.cloneNode(true);
  ghost.classList.add('city-bld-ghost');
  ghost.removeAttribute('data-habit-id');  // ghost interaktiv emas
  // Original ga "ko'tarilgan" klassi qo'shiladi (xirashadi)
  state.gridG.classList.add('city-bld-dragging');
  state.svg.appendChild(ghost);  // SVG oxiri = eng ustki qatlam
  state.ghost = ghost;
}

// ── Ghost'ni clientX/Y bo'yicha joylashtirish ──
// SVG ichida ghost'ni clientX/Y ga olib kelish: screenCTM.inverse() bilan
// pixel→SVG koord, keyin transform="translate(...)" qo'yamiz.
function _cityMoveGhost(state, clientX, clientY) {
  const pt = state.svg.createSVGPoint();
  pt.x = clientX; pt.y = clientY;
  const ctm = state.svg.getScreenCTM();
  if (!ctm) return;
  const svgPt = pt.matrixTransform(ctm.inverse());
  // Ghost original cx,cy ga nisbatan offset bilan harakatlanadi.
  // _moveState.origCx/Cy ni hisoblamaymiz — ghost o'z transform'ini
  // delta bilan emas, mutlaq pozitsiya bilan oladi: clone bino o'zining
  // ichki polygon'lariga ega, biz uni svg koord'iga "olib boramiz" deltani
  // delta-x, delta-y orqali. Buning uchun startSvgPt ni saqlaymiz.
  if (!state.startSvgPt) {
    state.startSvgPt = { x: svgPt.x, y: svgPt.y };
  }
  const dx = svgPt.x - state.startSvgPt.x;
  const dy = svgPt.y - state.startSvgPt.y;
  state.ghost.setAttribute('transform', `translate(${dx},${dy})`);
}

// ── ClientX/Y → grid (gx, gy) katak ──
// DOM hit-testing yondashuvi: matematik teskari iso formula chegara
// kataklarda noaniqlik beradi (4 katak orasida tushib qoladi). SVG polygon
// hit-testing orqali kursor ostidagi haqiqiy .city-tile elementni topamiz —
// SVG romb shaklini aniq biladi va kataklar orasidagi chegarani to'g'ri ajratadi.
// .city-tile har polygon'da data-x va data-y atributlari bor (app-city.js).
// Ghost o'rtada tursa elementFromPoint ghost'ni qaytaradi — uni pointer-events:none
// bilan o'tkazib yuboramiz (CSS allaqachon shunday). Bino o'zi ham pointer-events:none
// (.city-bld-dragging klassi orqali) — drag paytida tile'lar "ko'rinadi".
function _cityClientToGrid(state, clientX, clientY) {
  const el = document.elementFromPoint(clientX, clientY);
  if (!el) return null;
  // Kursor ostida .city-tile bormi? (boshqa element bo'lsa — null)
  const tile = el.closest && el.closest('.city-tile');
  if (!tile) return null;
  const gx = parseInt(tile.getAttribute('data-x'), 10);
  const gy = parseInt(tile.getAttribute('data-y'), 10);
  if (!Number.isFinite(gx) || !Number.isFinite(gy)) return null;
  return { x: gx, y: gy };
}

// ── Nishon katak highlight (qaysi katakka qo'yiladi) ──
function _cityUpdateHighlight(state, target) {
  if (!state.highlightRect) {
    // Birinchi marta — yaratamiz
    state.highlightRect = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
    state.highlightRect.setAttribute('class', 'city-tile-highlight');
    state.svg.insertBefore(state.highlightRect, state.ghost);  // ghost ostida
  }
  if (!target) {
    state.highlightRect.setAttribute('points', '');
    return;
  }
  // Nishon katakning 4 cho'qqisi — app-city.js render mantiqi bilan AYNAN BIR XIL:
  // top=(cx,cy), right=(cx+W/2,cy+H/2), bottom=(cx,cy+H), left=(cx-W/2,cy+H/2)
  const cx = cityIsoX(target.x, target.y);
  const cy = cityIsoY(target.x, target.y);
  const points = [
    `${cx},${cy}`,                                     // top
    `${cx + CITY_TILE_W / 2},${cy + CITY_TILE_H / 2}`, // right
    `${cx},${cy + CITY_TILE_H}`,                       // bottom
    `${cx - CITY_TILE_W / 2},${cy + CITY_TILE_H / 2}`, // left
  ].join(' ');
  state.highlightRect.setAttribute('points', points);
  // Band katakka qo'ymoqchi bo'lsa qizil, bo'sh bo'lsa yashil
  const occupied = _cityIsOccupied(target.x, target.y, state.habitId);
  state.highlightRect.classList.toggle('city-tile-invalid', occupied);
}

// ── Nishon katak band emasmi? (_cityData keshidan, qayta API yo'q) ──
// O'zining hozirgi joyi mustasno (xuddi shu binoni o'sha joyiga qo'ysa — bo'sh).
function _cityIsOccupied(x, y, ownHabitId) {
  if (!_cityData) return false;
  for (const b of _cityData.buildings || []) {
    if (b.habit_id === ownHabitId) continue;
    if (b.x === x && b.y === y) return true;
  }
  for (const d of _cityData.decorations || []) {
    if (d.x === x && d.y === y) return true;
  }
  return false;
}

// ── Long-press taymeri tugadi — drag rejimni faollashtirish ──
function _cityActivateDrag(state) {
  state.active = true;
  state.timerId = null;
  // Vizual: ghost yaratamiz, original xirashadi
  _cityCreateGhost(state);
  // Telegram haptic (mavjud pattern — app-core.js'da `light`, biz `medium` ishlatamiz)
  try {
    if (window.tg && window.tg.HapticFeedback) {
      window.tg.HapticFeedback.impactOccurred('medium');
    }
  } catch (e) { /* sukut */ }
}

// ── Long-press bekor qilish (drag faollashishidan oldin) ──
function _cityCancelPress(state) {
  if (state.timerId) {
    clearTimeout(state.timerId);
    state.timerId = null;
  }
}

// ── Drag tugatish — API chaqirig'i yoki bekor qilish ──
async function _cityFinishDrag(state) {
  // Ghost va highlight'ni olib tashlash
  if (state.ghost && state.ghost.parentNode) state.ghost.parentNode.removeChild(state.ghost);
  if (state.highlightRect && state.highlightRect.parentNode) state.highlightRect.parentNode.removeChild(state.highlightRect);
  state.gridG.classList.remove('city-bld-dragging');

  const target = state.targetX != null ? { x: state.targetX, y: state.targetY } : null;
  // Hech qaerga qo'yilmadi yoki band joy → bekor (eski joyda qoladi)
  if (!target) return;
  if (_cityIsOccupied(target.x, target.y, state.habitId)) {
    if (typeof showToast === 'function') showToast(S('city', 'move_failed'), true);
    return;
  }
  // Eski joy bilan bir xil → server'ga chiqmasdan ham success (Qoida #14: API'ga
  // ortiqcha so'rov yubormaymiz). Lekin pinned belgisi qo'yilishi uchun chaqiramiz.
  // Backend move_item bir xil koordda ham pinned=True qo'yadi (city_logic.py).

  if (state.lock) return;
  state.lock = true;
  try {
    const res = await apiFetch('city/' + userId + '/move', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ item_id: state.habitId, x: target.x, y: target.y }),
    });
    if (!res || !res.ok) throw new Error('move_failed');
    // Lokal keshni yangilash (qayta loadCity'siz darhol to'g'ri ko'rinadi)
    if (state.building) {
      state.building.x = target.x;
      state.building.y = target.y;
      state.building.pinned = true;
    }
    if (typeof showToast === 'function') showToast(S('city', 'moved'));
    // Grid'ni qayta yuklash — eski (cur_x, cur_y) bo'shadi, yangi pozitsiya
    // to'g'ri ko'rinadi (lokal _cityData allaqachon yangilangan, lekin DOM eski).
    if (typeof loadCity === 'function') await loadCity();
  } catch (e) {
    if (typeof showToast === 'function') showToast(S('city', 'move_failed'), true);
    // loadCity chaqirmaymiz — eski joy DOM'da saqlanib qoladi (bekor qilish hissi)
  } finally {
    state.lock = false;
  }
}

// ── BINOGA TOUCH HANDLERLAR ULASH (renderCityGrid oxirida chaqiriladi) ──
function initCityMoveHandlers(container) {
  if (!container) return;
  const svg = container.querySelector('.city-canvas');
  if (!svg) return;

  // touchstart — bino bosildi (yoki bo'sh katak — e'tibor bermaymiz)
  function onTouchStart(e) {
    if (_moveState && _moveState.active) return;  // boshqa drag davom etyapti
    const g = e.target.closest('.city-bld');
    if (!g) return;
    const habitId = g.getAttribute('data-habit-id');
    if (!habitId) return;

    // Bino ma'lumotini _cityData keshidan topish
    let building = null;
    if (_cityData && Array.isArray(_cityData.buildings)) {
      for (const b of _cityData.buildings) {
        if (String(b.habit_id) === String(habitId)) { building = b; break; }
      }
    }
    if (!building) return;

    const touch = e.touches ? e.touches[0] : e;
    _moveState = {
      container, svg, habitId, building, gridG: g,
      startX: touch.clientX, startY: touch.clientY,
      active: false, targetX: null, targetY: null,
      timerId: null, ghost: null, highlightRect: null,
      startSvgPt: null, lock: false,
    };
    // Vizual: ozgina ko'tarilgan klass (bosish his'i)
    g.classList.add('city-bld-pressing');
    // Long-press taymer
    _moveState.timerId = setTimeout(function () {
      if (_moveState) _cityActivateDrag(_moveState);
    }, LONGPRESS_MS);
  }

  // touchmove — barmoq surilyapti
  function onTouchMove(e) {
    if (!_moveState) return;
    const touch = e.touches ? e.touches[0] : e;

    if (!_moveState.active) {
      // Drag hali yo'q — siljish chegarasini tekshiramiz (scroll deb bilamiz)
      const dx = touch.clientX - _moveState.startX;
      const dy = touch.clientY - _moveState.startY;
      if (Math.abs(dx) > LONGPRESS_MAX_MOVE || Math.abs(dy) > LONGPRESS_MAX_MOVE) {
        // Foydalanuvchi scroll qilyapti — long-press bekor
        _cityCancelPress(_moveState);
        _moveState.gridG.classList.remove('city-bld-pressing');
        _moveState = null;
      }
      return;  // scroll'ga preventDefault qilmaymiz
    }

    // Drag faol — scroll'ni bloklaymiz va ghost'ni siljitamiz
    e.preventDefault();  // sahifa scroll'ini to'xtatish
    _cityMoveGhost(_moveState, touch.clientX, touch.clientY);
    const target = _cityClientToGrid(_moveState, touch.clientX, touch.clientY);
    if (target) {
      _moveState.targetX = target.x;
      _moveState.targetY = target.y;
    } else {
      _moveState.targetX = null;
      _moveState.targetY = null;
    }
    _cityUpdateHighlight(_moveState, target);
  }

  // touchend — barmoq olindi
  function onTouchEnd(e) {
    if (!_moveState) return;
    _moveState.gridG.classList.remove('city-bld-pressing');
    if (_moveState.active) {
      _cityFinishDrag(_moveState);
    } else {
      _cityCancelPress(_moveState);
    }
    _moveState = null;
  }

  // touchcancel — sistema gestureni uzdi (telefon qo'ng'irog'i va h.k.)
  function onTouchCancel(e) {
    if (!_moveState) return;
    _moveState.gridG.classList.remove('city-bld-pressing');
    _cityCancelPress(_moveState);
    if (_moveState.active && _moveState.ghost && _moveState.ghost.parentNode) {
      _moveState.ghost.parentNode.removeChild(_moveState.ghost);
    }
    if (_moveState.highlightRect && _moveState.highlightRect.parentNode) {
      _moveState.highlightRect.parentNode.removeChild(_moveState.highlightRect);
    }
    if (_moveState.gridG) _moveState.gridG.classList.remove('city-bld-dragging');
    _moveState = null;
  }

  // touchmove uchun passive:false — preventDefault ishlasin (drag faol bo'lganda)
  svg.addEventListener('touchstart', onTouchStart, { passive: true });
  svg.addEventListener('touchmove',  onTouchMove,  { passive: false });
  svg.addEventListener('touchend',   onTouchEnd,   { passive: true });
  svg.addEventListener('touchcancel', onTouchCancel, { passive: true });
}

// ── Eslatma kelajak bosqichlar uchun ──
// C5 LONG-PRESS:   ✅ touch handler + drag visual + drop API — SHU YERDA
// KELAJAK:         pointer events (desktop/stylus) — hozir touch yetadi
//                  (Telegram WebApp 99% mobil). Kerak bo'lsa qo'shamiz.
