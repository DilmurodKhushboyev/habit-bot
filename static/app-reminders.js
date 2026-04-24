// ═══════════════════════════════════════════════════════════
// ESLATMALAR (bir martalik) — Today sahifa uchun
// Mavjud loadToday pattern'ni to'ldiradi, unga tegmaydi
// ═══════════════════════════════════════════════════════════

let _remModalMode = 'quick';  // 'quick' | 'full'
let _cachedReminders = [];    // Load qilinganlarni cache

// ── API YORDAMCHI (apiFetch'dan farqli — backend error body'ni o'qish uchun) ──
async function _remFetch(path, opts) {
  opts = opts || {};
  opts.headers = Object.assign({
    'Content-Type': 'application/json',
    'X-Init-Data': initData,
    'X-User-Id': userId,
  }, opts.headers || {});
  const res = await fetch(`${API}/${path}`, opts);
  let body = null;
  try { body = await res.json(); } catch(e) {}
  return { ok: res.ok, status: res.status, body: body };
}

// ── YUKLASH ──
async function loadReminderCards() {
  try {
    const r = await _remFetch(`reminders/${userId}`);
    if (r.ok && r.body && Array.isArray(r.body.reminders)) {
      _cachedReminders = r.body.reminders;
    } else {
      _cachedReminders = [];
    }
  } catch(e) {
    console.warn('[rem] load error:', e);
    _cachedReminders = [];
  }
  return _cachedReminders;
}

// ── RENDER: Today sahifasi uchun HTML qaytaradi ──
// Faqat pending va sent statusdagi eslatmalar ko'rinadi
function renderReminderSections(reminders) {
  if (!reminders || !reminders.length) return '';
  // Filter: pending yoki sent + done/expired/skipped yashirin
  const active = reminders.filter(r =>
    r.status === 'pending' || r.status === 'sent'
  );
  if (!active.length) return '';

  // Bugun/Keyin ajratish
  const now = new Date();
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const todayEnd   = todayStart + 86400000;  // +24 soat

  const todayRems = [];
  const upcomingRems = [];
  for (const r of active) {
    const dt = new Date(r.remind_at).getTime();
    if (isNaN(dt)) continue;
    if (dt >= todayStart && dt < todayEnd) todayRems.push(r);
    else if (dt >= todayEnd)               upcomingRems.push(r);
    // O'tgan vaqt — ko'rsatmaymiz (backend expired deb belgilaydi)
  }
  // Vaqt bo'yicha tartiblash (o'sish)
  todayRems.sort((a, b) => new Date(a.remind_at) - new Date(b.remind_at));
  upcomingRems.sort((a, b) => new Date(a.remind_at) - new Date(b.remind_at));

  let html = '';
  if (todayRems.length) {
    html += `<div class="rem-section-title">${S('today','rem_today_section')}</div>`;
    html += todayRems.map(_renderRemCard).join('');
  }
  if (upcomingRems.length) {
    html += `<div class="rem-section-title">${S('today','rem_upcoming_section')}</div>`;
    html += upcomingRems.map(_renderRemCard).join('');
  }
  return html;
}

function _renderRemCard(r) {
  const timeLabel = _formatRemTime(r.remind_at);
  const safeText = _escRemHtml(r.text || '');
  return `
    <div class="rem-card" id="rem-card-${r._id}">
      <div class="rem-card-icon">
        <svg width="16" height="16" viewBox="0 0 26 26" fill="none">
          <defs><linearGradient id="svgBell${r._id}" x1="0" y1="0" x2="26" y2="26" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#5DBE8E"/><stop offset="100%" stop-color="#2D8A5E"/></linearGradient></defs>
          <path d="M13 3C13 3 8 6 8 13v5H5l2 2h12l2-2h-3v-5c0-7-5-10-5-10z" fill="url(#svgBell${r._id})" opacity="0.85"/>
          <circle cx="13" cy="22" r="1.5" fill="url(#svgBell${r._id})"/>
        </svg>
      </div>
      <div class="rem-card-body">
        <div class="rem-card-text">${safeText}</div>
        <div class="rem-card-meta">${timeLabel}</div>
      </div>
      <div class="rem-card-actions">
        <button class="rem-card-done-btn" onclick="markReminderDone('${r._id}')" type="button" title="${S('today','rem_done_btn')}">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none"><path d="M5 12l5 5L20 7" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </button>
        <button class="rem-card-del-btn" onclick="deleteReminder('${r._id}')" type="button" title="${S('today','rem_del_btn')}">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none"><line x1="18" y1="6" x2="6" y2="18" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/><line x1="6" y1="6" x2="18" y2="18" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/></svg>
        </button>
      </div>
    </div>`;
}

function _escRemHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

function _formatRemTime(iso) {
  if (!iso) return '';
  try {
    const dt = new Date(iso);
    if (isNaN(dt.getTime())) return '';
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const tomorrow = new Date(today.getTime() + 86400000);
    const dtDay = new Date(dt.getFullYear(), dt.getMonth(), dt.getDate());
    const hh = String(dt.getHours()).padStart(2,'0');
    const mm = String(dt.getMinutes()).padStart(2,'0');
    const timeStr = `${hh}:${mm}`;
    if (dtDay.getTime() === today.getTime())    return `${S('rem_modal','today_btn')} ${timeStr}`;
    if (dtDay.getTime() === tomorrow.getTime()) return `${S('rem_modal','tomorrow_btn')} ${timeStr}`;
    const d = String(dt.getDate()).padStart(2,'0');
    const mo = String(dt.getMonth()+1).padStart(2,'0');
    return `${d}.${mo} ${timeStr}`;
  } catch(e) { return ''; }
}

// ── BAJARILDI (+2 ball + karta yo'qolish animation) ──
async function markReminderDone(rid) {
  const card = document.getElementById('rem-card-' + rid);
  if (card) card.classList.add('done-anim');  // Fade-out animation boshlash
  try {
    const r = await _remFetch(`reminders/${userId}/${rid}/done`, { method: 'PATCH' });
    if (r.ok && r.body && r.body.ok) {
      _showTodayToast(S('rem_modal','ok_done'), 'ok');
      // 400ms kutish (fade-out tugashi uchun) → Today sahifani yangilash
      setTimeout(() => {
        loaded.today = false;
        loadToday();
      }, 400);
    } else {
      if (card) card.classList.remove('done-anim');
      _showTodayToast(S('rem_modal','err_generic'), 'err');
    }
  } catch(e) {
    if (card) card.classList.remove('done-anim');
    console.error('[rem] done error:', e);
    _showTodayToast(S('rem_modal','err_generic'), 'err');
  }
}

// ── O'CHIRISH ──
async function deleteReminder(rid) {
  const card = document.getElementById('rem-card-' + rid);
  if (card) card.classList.add('done-anim');
  try {
    const r = await _remFetch(`reminders/${userId}/${rid}`, { method: 'DELETE' });
    if (r.ok && r.body && r.body.ok) {
      _showTodayToast(S('rem_modal','ok_deleted'), 'ok');
      setTimeout(() => {
        loaded.today = false;
        loadToday();
      }, 400);
    } else {
      if (card) card.classList.remove('done-anim');
      _showTodayToast(S('rem_modal','err_generic'), 'err');
    }
  } catch(e) {
    if (card) card.classList.remove('done-anim');
    console.error('[rem] delete error:', e);
    _showTodayToast(S('rem_modal','err_generic'), 'err');
  }
}

// ── YARATISH MODALI ──
function openReminderModal() {
  _remModalMode = 'quick';
  // Default vaqt: hozirdan +1 soat, dumaloq 00 daqiqa
  const now = new Date();
  const def = new Date(now.getTime() + 60*60*1000);
  def.setMinutes(0, 0, 0);
  const hh = String(def.getHours()).padStart(2,'0');
  const mm = String(def.getMinutes()).padStart(2,'0');
  const timeStr = `${hh}:${mm}`;
  const dd   = String(def.getDate()).padStart(2,'0');
  const MM   = String(def.getMonth()+1).padStart(2,'0');
  const yyyy = def.getFullYear();
  const dateStr = `${yyyy}-${MM}-${dd}`;

  const overlay = document.createElement('div');
  overlay.className = 'rem-modal-overlay show';
  overlay.id = 'rem-modal';
  overlay.dataset.day = 'today';
  overlay.onclick = function(e) { if (e.target === overlay) closeReminderModal(); };
  overlay.innerHTML = `
    <div class="rem-modal-box" onclick="event.stopPropagation()">
      <div class="rem-modal-title">${S('rem_modal','title')}</div>

      <label class="rem-modal-label">${S('rem_modal','text_label')}</label>
      <textarea class="rem-modal-input rem-modal-textarea" id="rem-text-inp" maxlength="200" placeholder="${S('rem_modal','text_ph')}" oninput="_updateRemCharCount()"></textarea>
      <div class="rem-char-count"><span id="rem-char-cnt">0</span>/200</div>

      <label class="rem-modal-label">${S('rem_modal','mode_label')}</label>
      <div class="rem-mode-toggle">
        <button class="rem-mode-btn active" id="rem-mode-q" onclick="setRemMode('quick')" type="button">${S('rem_modal','mode_quick')}</button>
        <button class="rem-mode-btn" id="rem-mode-f" onclick="setRemMode('full')" type="button">${S('rem_modal','mode_full')}</button>
      </div>

      <div id="rem-q-wrap">
        <label class="rem-modal-label">${S('rem_modal','when_label')}</label>
        <div class="rem-day-row">
          <button class="rem-day-btn active" id="rem-d-today" onclick="setRemDay('today')" type="button">${S('rem_modal','today_btn')}</button>
          <button class="rem-day-btn" id="rem-d-tomorrow" onclick="setRemDay('tomorrow')" type="button">${S('rem_modal','tomorrow_btn')}</button>
        </div>
        <label class="rem-modal-label">${S('rem_modal','time_label')}</label>
        <input class="rem-modal-input" type="time" id="rem-time-q" value="${timeStr}">
      </div>

      <div id="rem-f-wrap" style="display:none">
        <label class="rem-modal-label">${S('rem_modal','date_label')}</label>
        <input class="rem-modal-input" type="date" id="rem-date-f" value="${dateStr}">
        <label class="rem-modal-label">${S('rem_modal','time_label')}</label>
        <input class="rem-modal-input" type="time" id="rem-time-f" value="${timeStr}">
      </div>

      <div class="rem-modal-actions">
        <button class="rem-modal-cancel" onclick="closeReminderModal()" type="button">${S('rem_modal','cancel')}</button>
        <button class="rem-modal-save" id="rem-save-btn" onclick="saveReminder()" type="button">${S('rem_modal','save')}</button>
      </div>
    </div>`;
  document.body.appendChild(overlay);
  setTimeout(() => { const i = document.getElementById('rem-text-inp'); if (i) i.focus(); }, 100);
}

function closeReminderModal() {
  const el = document.getElementById('rem-modal');
  if (el) el.remove();
}

function _updateRemCharCount() {
  const el  = document.getElementById('rem-text-inp');
  const cnt = document.getElementById('rem-char-cnt');
  if (el && cnt) cnt.textContent = (el.value || '').length;
}

function setRemMode(mode) {
  _remModalMode = mode;
  const q = document.getElementById('rem-mode-q');
  const f = document.getElementById('rem-mode-f');
  if (q) q.classList.toggle('active', mode === 'quick');
  if (f) f.classList.toggle('active', mode === 'full');
  const qw = document.getElementById('rem-q-wrap');
  const fw = document.getElementById('rem-f-wrap');
  if (qw) qw.style.display = mode === 'quick' ? 'block' : 'none';
  if (fw) fw.style.display = mode === 'full'  ? 'block' : 'none';
}

function setRemDay(day) {
  const m = document.getElementById('rem-modal');
  if (m) m.dataset.day = day;
  const t = document.getElementById('rem-d-today');
  const tm = document.getElementById('rem-d-tomorrow');
  if (t)  t.classList.toggle('active', day === 'today');
  if (tm) tm.classList.toggle('active', day === 'tomorrow');
}

// ── SAQLASH ──
async function saveReminder() {
  const textEl = document.getElementById('rem-text-inp');
  const text = (textEl && textEl.value || '').trim();
  if (!text) {
    alert(S('rem_modal','err_empty'));
    return;
  }

  // remind_at hisoblash
  let remindAt;
  if (_remModalMode === 'quick') {
    const m   = document.getElementById('rem-modal');
    const day = (m && m.dataset.day) || 'today';
    const tStr = document.getElementById('rem-time-q').value;
    if (!tStr) { alert(S('rem_modal','err_time')); return; }
    const [hh, mm] = tStr.split(':').map(Number);
    const now = new Date();
    const target = new Date(now.getFullYear(), now.getMonth(), now.getDate(), hh, mm, 0, 0);
    if (day === 'tomorrow') target.setDate(target.getDate() + 1);
    remindAt = target.toISOString();
  } else {
    const dStr = document.getElementById('rem-date-f').value;
    const tStr = document.getElementById('rem-time-f').value;
    if (!dStr || !tStr) { alert(S('rem_modal','err_time')); return; }
    const target = new Date(`${dStr}T${tStr}:00`);
    if (isNaN(target.getTime())) { alert(S('rem_modal','err_generic')); return; }
    remindAt = target.toISOString();
  }

  // O'tgan vaqt tekshiruvi (1 daqiqa tolerance)
  if (new Date(remindAt).getTime() - Date.now() < -60000) {
    alert(S('rem_modal','err_past'));
    return;
  }

  const saveBtn = document.getElementById('rem-save-btn');
  if (saveBtn) saveBtn.disabled = true;

  try {
    const r = await _remFetch(`reminders/${userId}`, {
      method: 'POST',
      body: JSON.stringify({ text: text, remind_at: remindAt })
    });
    if (r.ok && r.body && r.body.ok) {
      closeReminderModal();
      _showTodayToast(S('rem_modal','ok_created'), 'ok');
      loaded.today = false;
      loadToday();
    } else {
      const errKey = (r.body && r.body.error) ? r.body.error : ('http_' + r.status);
      alert(S('rem_modal','err_generic') + ' (' + errKey + ')');
      if (saveBtn) saveBtn.disabled = false;
    }
  } catch(e) {
    console.error('[rem] save error:', e);
    alert(S('rem_modal','err_generic') + '\n' + (e && e.message ? e.message : ''));
    if (saveBtn) saveBtn.disabled = false;
  }
}

// ── TODAY TOAST yordamchi (mavjud toast-today element'ini ishlatadi) ──
function _showTodayToast(text, kind) {
  const t = document.getElementById('toast-today');
  if (!t) return;
  t.textContent = text;
  t.className = 'toast show' + (kind === 'err' ? ' err' : '');
  setTimeout(() => { t.className = 'toast'; }, 2200);
}
