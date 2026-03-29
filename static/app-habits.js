// ── ODATLAR ──
const ICON_CATS = {
  '⭐ Sevimli': ['✅','🎯','💪','🧘','📚','🏃','💧','😴','🌅','🙏','🧠','🌿','✍️','🎸','🚴','🏋️','📝','💊','🍎','🌟'],
  '💪 Sport':  ['🏃','🚴','🏋️','🤸','⛹️','🏊','🎽','🥊','🏆','🥅','⚽','🏀','🎾','🏸','🏓','🎿','🧗','🤾','🏌️','🤺','🥋','🛹','🏄','🤼','🎣','🧜','🚵','🏇','🤽','🤿'],
  '📖 Ta\'lim': ['📚','📖','✍️','📝','🖊️','📓','📒','📔','📕','📗','📘','📙','📐','📏','🔬','🔭','🧪','🧫','🧬','💡','🖥️','⌨️','🖱️','📊','📈','📉','🗂️','📋','📌','📍'],
  '🍏 Sog\'liq': ['🍎','🥗','🥦','🥕','🍇','🍓','🫐','🥑','🍌','🍋','🥝','🍅','🥒','🌽','🫑','🧄','🧅','🥬','🥑','💊','🩺','🩻','🧬','🫁','🫀','🦷','👁️','🧴','🚿','🛁'],
  '🧘 Ruhiyat': ['🧘','🙏','🫶','💆','💭','🌈','☮️','🕊️','🌸','🌺','🌻','🌼','🍀','🌾','🌙','⭐','✨','💫','🌠','🎆','🎇','🧿','🪬','💎','🫧','🕯️','🪷','🌊','🏔️','🌄'],
  '😊 His':    ['😊','😄','🥰','😎','🤩','😤','💪','🙌','👏','🤝','🫂','❤️','💖','💪','🔥','⚡','🌊','💨','🎉','🎊','🏅','🥇','🎖️','🏵️','🎗️','🎁','🎀','🎈','🎪','🎭'],
  '🏠 Turmush':['🧹','🧺','🧻','🪣','🧽','🪥','🛏️','🛋️','🪑','🚪','🪟','🏠','🏡','🌳','🌲','🌴','🪴','🌵','🐕','🐈','🐠','🐦','🐇','🌻','🌹','🌷','💐','🪨','🪵','🔑'],
  '💼 Ish':    ['💼','📊','📈','💰','🏦','💳','📱','💻','⌨️','🖨️','📠','📟','☎️','📧','📨','📩','📬','📭','📮','🗃️','🗄️','🗑️','📎','🖇️','📐','📏','✂️','🗃️','🖊️','🖋️'],
  '🎨 Ijod':   ['🎨','🖌️','🖍️','✏️','🎭','🎬','🎥','📸','🎵','🎶','🎤','🎧','🎼','🎹','🥁','🎷','🎺','🪕','🎻','🎮','🕹️','🃏','🎲','🧩','♟️','🎯','🎳','🪀','🪁','🎣'],
  '🚀 Texno':  ['🚀','💻','📱','⌨️','🖥️','🖨️','🖱️','💾','💿','📀','📷','📹','🎥','📡','🔋','🔌','💡','🔦','🕯️','🧲','⚙️','🔧','🔨','🪛','🔩','⚗️','🧪','🔬','🔭','📡'],
};
const _ICON_CAT_KEYS = {'⭐ Sevimli':'cat_fav','💪 Sport':'cat_sport','📖 Ta\'lim':'cat_edu','🍏 Sog\'liq':'cat_health','🧘 Ruhiyat':'cat_spirit','😊 His':'cat_emotion','🏠 Turmush':'cat_home','💼 Ish':'cat_work','🎨 Ijod':'cat_art','🚀 Texno':'cat_tech'};
function _iconCatLabel(key) { const k = _ICON_CAT_KEYS[key]; return k ? key.slice(0,2)+' '+S('habits',k) : key; }
let _iconCat = Object.keys(ICON_CATS)[0];
const ICONS = Object.values(ICON_CATS).flat();
let editingHabitId = null;

async function refreshHabitsJon() {
  try {
    const d = await apiFetch(`habits/${userId}`);
    const jonPct = Math.round(d.jon ?? 100);
    const jonEl = document.getElementById('habits-jon-ring');
    if (jonEl) jonEl.innerHTML = jonRingHTML(jonPct, 72);
  } catch(e) { console.error('refreshHabitsJon:', e); }
}

async function loadHabits() {
  try {
    const d = await apiFetch(`habits/${userId}`);
    renderHabits(d.habits || [], d.jon ?? 100);
    if ((d.habits || []).length > 0) obMarkDone('habit');
  } catch(e) {
    document.getElementById('habits-content').innerHTML =
      `<div class="empty-state"><div class="icon"><svg width="28" height="28" viewBox="0 0 24 24" fill="none"><defs><linearGradient id="svgWarn" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#F6C93E"/><stop offset="100%" stop-color="#E07040"/></linearGradient></defs><path d="M12 3L2 21h20L12 3z" stroke="url(#svgWarn)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/><path d="M12 10v5M12 17.5v.5" stroke="url(#svgWarn)" stroke-width="2" stroke-linecap="round"/></svg></div>${S('msg','data_error')}.</div>`;
  }
}

function renderHabits(habits, jon = 100) {
  const _esc = (s) => s.replace(/'/g, "\\'");
  let rows = '';
  habits.forEach(h => {
    const editArgs = `'${h.id}','${_esc(h.name)}','${h.icon||'✅'}','${h.time||'vaqtsiz'}','${h.type||'simple'}',${h.repeat_count||1},'${encodeURIComponent(JSON.stringify(h.times||[]))}'`;
    rows += `
      <div class="habit-card" id="hcard-${h.id}">
        <div class="habit-card-actions-bg">
          <button class="hswipe-btn hswipe-edit" onclick="openEdit(${editArgs})">
            <svg width="18" height="18" viewBox="0 0 26 26" fill="none"><path d="M17 4L22 9L10 21L4 22L5 16L17 4Z" fill="#fff" opacity="0.9"/></svg>
            <span>${S('habits','edit_btn')}</span>
          </button>
          <button class="hswipe-btn hswipe-del" onclick="deleteHabit('${h.id}')">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M10 11v6M14 11v6" stroke="#fff" stroke-width="2" stroke-linecap="round"/></svg>
            <span>${S('habits','delete_btn')}</span>
          </button>
        </div>
        <div class="habit-card-front" data-hid="${h.id}">
          <div class="habit-card-icon">${h.icon||'<svg width="22" height="22" viewBox="0 0 24 24" fill="none"><defs><linearGradient id="svgDefIcon" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#4CAF7D"/><stop offset="100%" stop-color="#2D8A5E"/></linearGradient></defs><circle cx="12" cy="12" r="9" fill="url(#svgDefIcon)" opacity="0.2"/><path d="M7 12l4 4 6-7" stroke="url(#svgDefIcon)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>'}</div>
          <div class="habit-card-info">
            <div class="habit-card-name">${h.name}</div>
            <div class="habit-card-meta"><svg width="13" height="13" viewBox="0 0 20 20" fill="none" style="display:inline;vertical-align:middle"><defs><linearGradient id="svgClock" x1="0" y1="0" x2="20" y2="20" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#5B8DEF"/><stop offset="100%" stop-color="#A78BFA"/></linearGradient></defs><circle cx="10" cy="10" r="8" stroke="url(#svgClock)" stroke-width="2"/><path d="M10 6V10L13 12" stroke="url(#svgClock)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg> ${h.time||'vaqtsiz'} &nbsp;<svg width="13" height="13" viewBox="0 0 20 20" fill="none" style="display:inline;vertical-align:middle"><defs><linearGradient id="svgFire" x1="10" y1="0" x2="10" y2="20" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#F6C93E"/><stop offset="100%" stop-color="#E07040"/></linearGradient></defs><path d="M10 2C10 2 14 6 14 10C14 12 13 13.5 11.5 14.5C12 13 11.5 11.5 10.5 11C11 13 9.5 15 8 15.5C9 14 8.5 12 7 11C5.5 12.5 6 15 7 16.5C5.5 15.5 4 13.5 4 11C4 7 8 4 10 2Z" fill="url(#svgFire)"/></svg> ${S('msg','streak_days').replace('{n}', h.streak)}</div>
          </div>
          <button class="habit-dots-btn" onclick="event.stopPropagation();toggleHabitDrop('${h.id}')">
            <svg width="4" height="16" viewBox="0 0 4 16" fill="currentColor"><circle cx="2" cy="2" r="2"/><circle cx="2" cy="8" r="2"/><circle cx="2" cy="14" r="2"/></svg>
          </button>
          <div class="habit-dropdown" id="hdrop-${h.id}">
            <button class="habit-dropdown-item" onclick="event.stopPropagation();closeAllHabitDrops();openEdit(${editArgs})">
              <svg width="15" height="15" viewBox="0 0 26 26" fill="none"><path d="M17 4L22 9L10 21L4 22L5 16L17 4Z" fill="var(--accent2)" opacity="0.85"/></svg>
              ${S('habits','edit_btn')}
            </button>
            <button class="habit-dropdown-item danger" onclick="event.stopPropagation();closeAllHabitDrops();deleteHabit('${h.id}')">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none"><path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6" stroke="var(--red)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M10 11v6M14 11v6" stroke="var(--red)" stroke-width="2" stroke-linecap="round"/></svg>
              ${S('habits','delete_btn')}
            </button>
          </div>
        </div>
      </div>`;
  });

  const jonPct = Math.round(jon);
  const jonDoira = jonRingHTML(jonPct, 72);

  const iconGrid = `
    <div class="icon-cat-tabs" id="icon-cat-tabs">
      ${Object.keys(ICON_CATS).map((cat, i) =>
        `<button type="button" class="icon-cat-btn${cat === _iconCat ? ' active' : ''}"
          onclick="selectIconCat(this,${i})">${_iconCatLabel(cat)}</button>`
      ).join('')}
    </div>
    <div class="icon-grid" id="icon-grid-inner">
      ${ICON_CATS[_iconCat].map(ic =>
        `<div class="icon-opt" data-icon="${ic}" onclick="selectIcon(this)">${ic}</div>`
      ).join('')}
    </div>`;

  document.getElementById('habits-content').innerHTML = `
    <div>
      <button class="add-btn" onclick="openAdd()" type="button">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" style="display:inline;vertical-align:middle"><path d="M12 5v14M5 12h14" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/></svg>
        ${S('habits','add_new')}
      </button>
      <div class="section-title">${S('habits','title')} (${habits.length})</div>
      ${rows || `<div class="empty-state"><div class="icon"><svg width="28" height="28" viewBox="0 0 24 24" fill="none"><defs><linearGradient id="svgClip" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#8A8FA8"/><stop offset="100%" stop-color="#5B8DEF"/></linearGradient></defs><rect x="8" y="2" width="8" height="4" rx="1" stroke="url(#svgClip)" stroke-width="1.5"/><rect x="4" y="4" width="16" height="18" rx="2" stroke="url(#svgClip)" stroke-width="1.5"/><path d="M8 11h8M8 15h5" stroke="url(#svgClip)" stroke-width="1.5" stroke-linecap="round"/></svg></div>${S('habits','empty')}</div>`}
    </div>

    <div class="toast" id="toast"></div>

    <div class="modal-overlay" id="habit-modal">
      <div class="modal">
        <div class="modal-handle"></div>
        <button class="modal-close" onclick="closeModal()"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" style="display:block"><line x1="18" y1="6" x2="6" y2="18" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/><line x1="6" y1="6" x2="18" y2="18" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/></svg></button>
        <div class="modal-title" id="modal-title">Yangi odat</div>
        <div class="field">
          <label id="lbl-habit-name">Nomi</label>
          <input id="h-name" type="text" placeholder="Masalan: Kitob o'qish" maxlength="60">
        </div>
        <div class="field">
          <label id="lbl-habit-type">Kuniga necha marta?</label>
          <div style="display:flex;align-items:center;gap:10px">
            <input id="h-repeat-count" type="number" min="1" max="99" value="1" onchange="_onRepeatCountChange()" oninput="_onRepeatCountChange()" style="width:70px;text-align:center;font-size:16px;font-weight:700">
            <span style="font-size:11px;color:var(--sub);line-height:1.3" id="lbl-per-day-hint">1 = oddiy, 2+ = kuniga bir necha marta</span>
          </div>
        </div>
        <div class="field">
          <label id="lbl-time">${S('habits','time_label')}</label>
          <div id="h-times-list"></div>
          <button type="button" class="rep-btn" style="width:100%;margin-top:6px;justify-content:center" onclick="addHabitTime()">${S('reminders','add_time')}</button>
        </div>
        <div class="field">
          <label id="lbl-icon-pick">Icon tanlang</label>
          ${iconGrid}
        </div>
        <button class="save-btn" onclick="saveHabit()"><span id="habit-save-txt">${S("profile","save_btn")}</span></button>
      </div>
    </div>`;

  // Swipe handlerlarni ulash
  setTimeout(() => _initHabitSwipe(), 50);
}

function selectIconCat(btn, idx) {
  const cat = Object.keys(ICON_CATS)[idx];
  _iconCat = cat;
  document.querySelectorAll('.icon-cat-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  const grid = document.getElementById('icon-grid-inner');
  if (grid) {
    grid.innerHTML = ICON_CATS[cat].map(ic =>
      `<div class="icon-opt" data-icon="${ic}" onclick="selectIcon(this)">${ic}</div>`
    ).join('');
  }
}

function selectIcon(el) {
  document.querySelectorAll('.icon-opt').forEach(e => e.classList.remove('selected'));
  el.classList.add('selected');
}
let _returnToToday = false;

async function openAddFromToday() {
  _returnToToday = true;
  await loadHabits();
  // habit-modal ni body ga ko'chirish — page-today ustida ko'rinsin
  const modal = document.getElementById('habit-modal');
  if (modal && modal.parentElement !== document.body) {
    document.body.appendChild(modal);
  }
  openAdd();
}

function _translateHabitModal() {
  const m = (id, key, sub) => { const el = document.getElementById(id); if (el) el.textContent = S(key, sub); };
  m('lbl-habit-name', 'habits', 'name_label');
  m('lbl-habit-type', 'habits', 'type_label');
  m('lbl-per-day-hint', 'habits', 'per_day_hint');
  m('lbl-time', 'habits', 'time_label');
  m('lbl-icon-pick', 'habits', 'icon_label');
  const hn = document.getElementById('h-name');
  if (hn) hn.placeholder = S('msg','ph_habit_name');
}
function openAdd() {
  // Premium limit tekshiruvi
  const _habitCount = (data.today && data.today.habits) ? data.today.habits.length : (data.profile && data.profile.habit_limit !== undefined ? 0 : 0);
  const _allHabits = data.habits ? data.habits.length : (_habitCount);
  const _limit = data.profile && data.profile.habit_limit !== undefined ? data.profile.habit_limit : (data.profile && data.profile.is_premium ? 15 : 3);
  const _isPrem = data.profile && data.profile.is_premium;
  // habits sahifasidan ochilganda habits.length dan foydalanamiz
  const _currentCount = (typeof habits !== 'undefined' && habits) ? habits.length : _allHabits;
  if (_currentCount >= _limit) {
    if (_isPrem) {
      showToast(S('habits','limit_reached') || '⚠️ Maksimal limit!', true);
    } else {
      showPremiumPage();
    }
    return;
  }
  editingHabitId = null;
  document.getElementById('modal-title').textContent = S('habits','add_new');
  _translateHabitModal();
  document.getElementById('h-name').value = '';
  const rcEl = document.getElementById('h-repeat-count');
  if (rcEl) rcEl.value = 1;
  _buildTimeInputs(1, []);
  document.querySelectorAll('.icon-opt').forEach(e => e.classList.remove('selected'));
  document.querySelector('.icon-opt')?.classList.add('selected');
  document.getElementById('habit-modal').classList.add('open');
  setTimeout(() => {
    const inp = document.getElementById('h-name');
    if (inp) inp.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, 320);
}
async function openEdit(id, name, icon, time, type, repeatCount, timesJson) {
  // Modal renderHabits() ichida yaratiladi — sahifa ochilmagan bo'lsa yo'q bo'ladi
  // Shuning uchun avval modal mavjudligini tekshiramiz
  if (!document.getElementById('habit-modal')) {
    _returnToToday = true;
    await loadHabits();
    // Modal yaratilgandan keyin body ga ko'chirish
    const m = document.getElementById('habit-modal');
    if (m && m.parentElement !== document.body) document.body.appendChild(m);
  } else {
    // Habits sahifasida emas — body ga ko'chirish
    const m = document.getElementById('habit-modal');
    if (m && m.parentElement !== document.body) document.body.appendChild(m);
  }
  editingHabitId = id;
  document.getElementById('modal-title').textContent = S('habits','edit_title');
  _translateHabitModal();
  document.getElementById('h-name').value = name;
  const rcEl = document.getElementById('h-repeat-count');
  if (rcEl) rcEl.value = repeatCount || 1;
  // Vaqtlarni parse qilish
  let times = [];
  try { times = JSON.parse(decodeURIComponent(timesJson || '[]')); } catch(e) { times = []; }
  if (!times.length && time && time !== 'vaqtsiz') times = [time];
  _buildTimeInputs(repeatCount || 1, times);
  document.querySelectorAll('.icon-opt').forEach(e => {
    e.classList.toggle('selected', e.dataset.icon === icon);
  });
  document.getElementById('habit-modal').classList.add('open');
  setTimeout(() => {
    const inp = document.getElementById('h-name');
    if (inp) inp.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, 320);
}
function closeModal() {
  document.getElementById('habit-modal').classList.remove('open');
  if (_returnToToday) {
    _returnToToday = false;
    switchTab('today', document.getElementById('nav-today'));
  }
}

function showToast(msg, err=false) {
  const t = document.getElementById('toast');
  if (!t) return;
  t.textContent = msg; t.className = 'toast show' + (err?' err':'');
  setTimeout(() => t.className = 'toast', 2500);
}

function setHabitType(type) {
  // Legacy — no-op, toggle removed
}

async function saveHabit() {
  const saveBtn = document.getElementById('habit-save-txt');
  if (saveBtn && saveBtn.dataset.saving === '1') return;
  const name = document.getElementById('h-name').value.trim();
  const icon = document.querySelector('.icon-opt.selected')?.dataset.icon || '✅';
  const repeatCount = parseInt(document.getElementById('h-repeat-count').value) || 1;
  const isRepeat = repeatCount >= 2;

  // Barcha vaqt inputlarini yigʻish
  const timesArr = [];
  const timesList = document.getElementById('h-times-list');
  if (timesList) {
    timesList.querySelectorAll('input[type=time]').forEach(inp => {
      if (inp.value) timesArr.push(inp.value);
    });
  }
  const timeFinal = timesArr.length > 0 ? timesArr[0] : 'vaqtsiz';

  if (!name) { showToast(S('msg','enter_name'), true); return; }

  // Takror son validatsiyasi
  if (repeatCount < 1 || repeatCount > 99) {
    showToast(S('msg','bad_repeat'), true); return;
  }

  // Vaqt validatsiyasi — barcha kiritilgan vaqtlarni tekshirish
  const timePattern = /^\d{2}:\d{2}$/;
  for (const tv of timesArr) {
    if (!timePattern.test(tv)) {
      showToast(S('msg','bad_time'), true); return;
    }
    const [hh, mm] = tv.split(':').map(Number);
    if (hh > 23 || mm > 59) {
      showToast(S('msg','err_bad_time_range'), true); return;
    }
  }

  // Barcha validatsiyalar o'tdi — tugmani bloklash
  if (saveBtn) { saveBtn.dataset.saving = '1'; saveBtn.textContent = S('habits','saving') || S('profile','saving'); }
  try {
    if (editingHabitId) {
      const res = await fetch(`${API}/habits/${userId}/${editingHabitId}`, {
        method: 'PUT',
        headers: {'Content-Type':'application/json','X-Init-Data':initData,'X-User-Id':userId},
        body: JSON.stringify({name, icon, time: timeFinal, type: isRepeat ? 'repeat' : 'simple', repeat_count: repeatCount, repeat_times: isRepeat ? timesArr : []})
      });
      const rj = await res.json().catch(() => ({}));
      if (!res.ok || rj.ok === false) { showToast('❌ ' + (rj.error || S('msg','error_label')), true); return; }
      showToast(S('profile','saved'));
    } else {
      const res = await fetch(`${API}/habits/${userId}`, {
        method: 'POST',
        headers: {'Content-Type':'application/json','X-Init-Data':initData,'X-User-Id':userId},
        body: JSON.stringify({name, icon, time: timeFinal, type: isRepeat ? 'repeat' : 'simple', repeat_count: repeatCount, repeat_times: isRepeat ? timesArr : []})
      });
      const rj = await res.json().catch(() => ({}));
      if (!res.ok || rj.ok === false) { showToast('❌ ' + (rj.error || S('msg','error_label')), true); return; }
      showToast('✅ Qoʼshildi!');
    }
    const wasFromToday = _returnToToday;
    closeModal();
    if (wasFromToday) {
      loaded.today = false;
      await loadToday();
    } else {
      loaded.habits = false;
      await loadHabits();
    }
  } catch(e) { showToast(S('friends','error'), true); }
  finally {
    if (saveBtn) { saveBtn.dataset.saving = ''; saveBtn.textContent = S('habits','save_btn') || S('profile','save_btn'); }
  }
}

async function deleteHabit(id) {
  if (!confirm(S('msg','confirm_del_habit'))) return;
  try {
    const res = await fetch(`${API}/habits/${userId}/${id}`, {
      method: 'DELETE', headers: {'X-Init-Data': initData, 'X-User-Id': userId}
    });
    const rj = await res.json().catch(() => ({}));
    if (!res.ok || rj.ok === false) { showToast('❌ ' + (rj.error || S('msg','error_label')), true); return; }
    showToast('🗑️ O\'chirildi!');
    loaded.habits = false;
    await loadHabits();
  } catch(e) { showToast(S('msg','error_label'), true); }
}

// ── DINAMIK VAQT INPUTLARI (odat yaratish/tahrirlash uchun) ──
function _buildTimeInputs(count, existingTimes) {
  const list = document.getElementById('h-times-list');
  if (!list) return;
  const n = Math.max(1, count);
  let html = '';
  for (let i = 0; i < n; i++) {
    const val = (existingTimes && existingTimes[i]) || '';
    html += '<div class="time-row" id="ht-row-' + i + '">'
      + '<span class="time-lbl">' + S('msg','time_slot_n').replace('{n}', i + 1) + '</span>'
      + '<input class="time-input" type="time" id="ht-val-' + i + '" value="' + val + '">'
      + '</div>';
  }
  list.innerHTML = html;
}

function addHabitTime() {
  const list = document.getElementById('h-times-list');
  if (!list) return;
  const rows = list.querySelectorAll('.time-row');
  if (rows.length >= 20) return;
  const i = rows.length;
  // repeat_count ni ham oshirish
  const rcEl = document.getElementById('h-repeat-count');
  if (rcEl && parseInt(rcEl.value) < i + 1) rcEl.value = i + 1;
  const div = document.createElement('div');
  div.className = 'time-row';
  div.id = 'ht-row-' + i;
  div.innerHTML = '<span class="time-lbl">' + S('msg','time_slot_n').replace('{n}', i + 1) + '</span>'
    + '<input class="time-input" type="time" id="ht-val-' + i + '">';
  list.appendChild(div);
}

function _onRepeatCountChange() {
  const rc = parseInt(document.getElementById('h-repeat-count').value) || 1;
  const list = document.getElementById('h-times-list');
  if (!list) return;
  // Mavjud vaqtlarni saqlash
  const existing = [];
  list.querySelectorAll('input[type=time]').forEach(function(inp) {
    existing.push(inp.value || '');
  });
  _buildTimeInputs(rc, existing);
}

// ── SWIPE-TO-REVEAL (chapga surish) ──
function _initHabitSwipe() {
  document.querySelectorAll('.habit-card-front').forEach(front => {
    let startX = 0, curX = 0, swiping = false, startY = 0, locked = false;
    front.addEventListener('touchstart', e => {
      closeAllHabitDrops();
      closeAllHabitSwipes(front);
      startX = e.touches[0].clientX;
      startY = e.touches[0].clientY;
      curX = 0; swiping = true; locked = false;
      front.style.transition = 'none';
    }, {passive: true});

    front.addEventListener('touchmove', e => {
      if (!swiping) return;
      const dx = e.touches[0].clientX - startX;
      const dy = e.touches[0].clientY - startY;
      // Vertikal scroll bo'lsa — swipeni bekor qilish
      if (!locked) {
        if (Math.abs(dy) > Math.abs(dx) && Math.abs(dy) > 8) { swiping = false; front.style.transition = ''; front.style.transform = ''; return; }
        if (Math.abs(dx) > 8) locked = true;
      }
      curX = dx;
      if (curX > 0) curX = 0;
      if (curX < -130) curX = -130;
      front.style.transform = 'translateX(' + curX + 'px)';
    }, {passive: true});

    front.addEventListener('touchend', () => {
      if (!swiping) return;
      swiping = false;
      front.style.transition = '';
      if (curX < -50) {
        front.classList.add('swiped');
      } else {
        front.classList.remove('swiped');
      }
      front.style.transform = '';
    });
  });
}

function closeAllHabitSwipes(except) {
  document.querySelectorAll('.habit-card-front.swiped').forEach(f => {
    if (f !== except) f.classList.remove('swiped');
  });
}

// ── 3-NUQTA DROPDOWN ──
function toggleHabitDrop(hid) {
  const drop = document.getElementById('hdrop-' + hid);
  if (!drop) return;
  const wasOpen = drop.classList.contains('open');
  closeAllHabitDrops();
  closeAllHabitSwipes();
  if (!wasOpen) drop.classList.add('open');
}

function closeAllHabitDrops() {
  document.querySelectorAll('.habit-dropdown.open').forEach(d => d.classList.remove('open'));
}

// Global tap — dropdown va swipeni yopish
document.addEventListener('click', e => {
  if (!e.target.closest('.habit-dots-btn') && !e.target.closest('.habit-dropdown')) {
    closeAllHabitDrops();
  }
  if (!e.target.closest('.habit-card')) {
    closeAllHabitSwipes();
  }
});