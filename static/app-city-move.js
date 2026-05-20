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
const LONGPRESS_MS       = 600;   // bosish vaqti (ms) — Hay Day patterni
const LONGPRESS_MAX_MOVE = 10;    // scroll deb hisoblanish chegarasi (px) bosish boshlangan nuqtadan

// ── HOLAT (har renderCityGrid'da reset bo'ladi) ──
let _moveState = null;
// Strukturasi (drag faol bo'lganda):
// {
//   container, svg,           // DOM ssilkalar (cleanup uchun)
//   habitId, building,        // ko'chirilayotgan bino
//   gridG,                    // bino <g> element (.city-bld) — original SVG
//   startX, startY,           // touchstart pixel (clientX/Y)
//   timerId,                  // setTimeout id (longpress)
//   active: false,            // drag rejim faolmi (true → 600ms o'tdi)
//   targetX, targetY,         // hozirgi nishon katak (grid koord)
//   ring,                     // bino atrofidagi halqa polygon (bosildi belgisi)
//   ghost,                    // drag paytidagi "ghost" bino (vizual clone)
//   highlightRect,            // drag paytida nishon katak ustidagi highlight
//   lock: false,              // API so'rovi davom etyapti (double-tap himoya)
// }

// ── Ghost qatlami (drag paytida bino barmoq ortidan ergashadi) ──
// Ghost = SVG <g> nusxa. Original bino visibility:hidden — ghost yagona ko'rinadi.
// MUHIM (Qoida #21): asl <g> ga opacity/transform qo'shilMASIN — filter:drop-shadow
// bilan to'qnashib qaltirash beradi (mobile WebView GPU compositor xatosi).
// visibility:hidden transition bermaydi, darhol yashirinadi, qaltirashsiz.
function _cityCreateGhost(state) {
  const ghost = state.gridG.cloneNode(true);
  ghost.classList.add('city-bld-ghost');
  ghost.removeAttribute('data-habit-id');  // ghost interaktiv emas
  state.gridG.classList.add('city-bld-hidden');  // asl bino yashirinadi
  state.svg.appendChild(ghost);  // SVG oxiri = eng ustki qatlam
  state.ghost = ghost;
}

// ── Halqa qatlami (bosildi/drag belgisi — alohida polygon, binoga teginmaydi) ──
// Bino katagi atrofida romb shaklida halqa chiziladi. CSS:
// - .city-bld-ring: ko'k, ingichka, pulse animatsiya (bosildi)
// - .city-bld-ring[data-active="1"]: yashil, qalin, animatsiyasiz (drag faol)
// Binoga teginmaydi → filter:drop-shadow qaltirash sababi yo'q (Qoida #21).
function _cityCreateRing(state) {
  const ring = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
  ring.setAttribute('class', 'city-bld-ring');
  const cx = cityIsoX(state.building.x, state.building.y);
  const cy = cityIsoY(state.building.x, state.building.y);
  // Romb cho'qqilari .city-tile bilan AYNAN BIR XIL (app-city.js render mantiqi)
  const points = [
    `${cx},${cy}`,                                     // top
    `${cx + CITY_TILE_W / 2},${cy + CITY_TILE_H / 2}`, // right
    `${cx},${cy + CITY_TILE_H}`,                       // bottom
    `${cx - CITY_TILE_W / 2},${cy + CITY_TILE_H / 2}`, // left
  ].join(' ');
  ring.setAttribute('points', points);
  // Tile qatlami ustiga, lekin bino ostiga joylashtiramiz (z-tartibi):
  // SVG'da bu — birinchi .city-bld dan oldin insertBefore. Lekin oddiy yo'l:
  // appendChild — eng ustga. Bino vizual jihatdan kub bo'lib halqa tashqarisida
  // ko'rinadi (kub asosi tile bilan teng, halqa stroke esa tashqi chiziq).
  state.svg.appendChild(ring);
  state.ring = ring;
}

// ── Halqani drag faol holatga o'tkazish (ko'k → yashil, ingichka → qalin) ──
function _cityActivateRing(state) {
  if (state.ring) state.ring.setAttribute('data-active', '1');
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
// bilan o'tkazib yuboramiz (CSS allaqachon shunday). Asl bino visibility:hidden
// (.city-bld-hidden klassi orqali) — drag paytida tile'lar "ko'rinadi".
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
  // Vizual: ghost yaratiladi (asl bino visibility:hidden), halqa yashil/qalin holatga
  _cityCreateGhost(state);
  _cityActivateRing(state);
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
// FLASH + RE-RENDER YECHIMI (Qoida #21): loadCity butun grid'ni qayta yaratardi
// — bu auto-scroll'ni qayta ishga tushirib sahifa siljishini va foydalanuvchi
// barmog'i ostidagi <g> ni yo'qotardi (tez ketma-ket drag mumkin emas edi).
// O'rniga DOM IN-PLACE yangilash:
//   - Asl <g> ga transform="translate(dx,dy)" qo'shiladi (bepul SVG operation,
//     barcha ichki polygon'lar avtomatik siljiydi)
//   - Ghost olib tashlanadi, asl bino visibility'dan chiqariladi → yangi joyda ko'rinadi
//   - Lokal _cityData yangilanadi → keyingi drag'lar to'g'ri data'ni ko'radi
//   - loadCity CHAQIRILMAYDI → sahifa siljimaydi, DOM butunligicha qoladi
// Z-order (painter's algorithm) keyingi loadCity'da (boshqa sabab bilan)
// to'g'rilanadi — vaqtinchalik nomos joylashish ko'rinmaydi (binolar siyrak).
async function _cityFinishDrag(state) {
  // Halqa va highlight'ni darhol olib tashlaymiz — drag tugadi
  if (state.ring && state.ring.parentNode) state.ring.parentNode.removeChild(state.ring);
  if (state.highlightRect && state.highlightRect.parentNode) state.highlightRect.parentNode.removeChild(state.highlightRect);

  const target = state.targetX != null ? { x: state.targetX, y: state.targetY } : null;

  // Bekor qilish funksiyasi (rollback): ghost o'chadi, asl bino qaytadi
  function _cancelMove() {
    if (state.ghost && state.ghost.parentNode) state.ghost.parentNode.removeChild(state.ghost);
    state.gridG.classList.remove('city-bld-hidden');
  }

  // Hech qaerga qo'yilmadi → bekor (eski joyda qoladi, toast yo'q)
  if (!target) { _cancelMove(); return; }
  // Band joy → bekor + toast
  if (_cityIsOccupied(target.x, target.y, state.habitId)) {
    _cancelMove();
    if (typeof showToast === 'function') showToast(S('city', 'move_failed'), true);
    return;
  }

  // Ghost'ni nishon katak markaziga snap qilamiz (foydalanuvchi ko'rishi uchun).
  // dx,dy — original (building.x, building.y) dan target (target.x, target.y) gacha iso delta.
  const dx = cityIsoX(target.x, target.y) - cityIsoX(state.building.x, state.building.y);
  const dy = cityIsoY(target.x, target.y) - cityIsoY(state.building.x, state.building.y);
  state.ghost.setAttribute('transform', `translate(${dx},${dy})`);

  if (state.lock) return;
  state.lock = true;
  try {
    const res = await apiFetch('city/' + userId + '/move', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ item_id: state.habitId, x: target.x, y: target.y }),
    });
    if (!res || !res.ok) throw new Error('move_failed');

    // MUVAFFAQIYAT: DOM IN-PLACE yangilash (loadCity'siz):
    // 1) Asl <g> ga transform qo'shamiz — barcha ichki polygon'lar yangi joyga siljiydi
    state.gridG.setAttribute('transform', `translate(${dx},${dy})`);
    // 2) Ghost'ni olib tashlaymiz
    if (state.ghost && state.ghost.parentNode) state.ghost.parentNode.removeChild(state.ghost);
    // 3) Asl bino visibility'dan chiqariladi — yangi joyda ko'rinadi
    state.gridG.classList.remove('city-bld-hidden');
    // 4) Lokal _cityData.buildings yangilash — keyingi drag/render uchun to'g'ri ma'lumot
    if (state.building) {
      state.building.x = target.x;
      state.building.y = target.y;
      state.building.pinned = true;
    }
    if (typeof showToast === 'function') showToast(S('city', 'moved'));
  } catch (e) {
    // API xato — rollback: ghost olib tashlanadi, asl bino qaytadi, toast
    _cancelMove();
    if (typeof showToast === 'function') showToast(S('city', 'move_failed'), true);
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
      timerId: null, ghost: null, ring: null, highlightRect: null,
      startSvgPt: null, lock: false,
    };
    // Vizual: bino atrofida halqa (alohida polygon — binoga teginmaymiz, qaltirash yo'q)
    _cityCreateRing(_moveState);
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
        // Foydalanuvchi scroll qilyapti — long-press bekor, halqa o'chadi
        _cityCancelPress(_moveState);
        if (_moveState.ring && _moveState.ring.parentNode) {
          _moveState.ring.parentNode.removeChild(_moveState.ring);
        }
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
    if (_moveState.active) {
      _cityFinishDrag(_moveState);  // ghost+ring+highlight+hidden klass — ichida tozalanadi
    } else {
      _cityCancelPress(_moveState);
      // Drag hech faollashmadi — faqat halqani o'chiramiz (gridG ga klass qo'shilmagan)
      if (_moveState.ring && _moveState.ring.parentNode) {
        _moveState.ring.parentNode.removeChild(_moveState.ring);
      }
    }
    _moveState = null;
  }

  // touchcancel — sistema gestureni uzdi (telefon qo'ng'irog'i va h.k.)
  function onTouchCancel(e) {
    if (!_moveState) return;
    _cityCancelPress(_moveState);
    // Hamma vizual elementlarni tozalash (drag faol bo'lsa ham, bo'lmasa ham)
    if (_moveState.ring && _moveState.ring.parentNode) {
      _moveState.ring.parentNode.removeChild(_moveState.ring);
    }
    if (_moveState.ghost && _moveState.ghost.parentNode) {
      _moveState.ghost.parentNode.removeChild(_moveState.ghost);
    }
    if (_moveState.highlightRect && _moveState.highlightRect.parentNode) {
      _moveState.highlightRect.parentNode.removeChild(_moveState.highlightRect);
    }
    if (_moveState.gridG) _moveState.gridG.classList.remove('city-bld-hidden');
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
