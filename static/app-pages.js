// ── BUGUN ──
async function loadToday() {
  try {
    const d = await apiFetch(`today/${userId}`);
    data.today = d;
    if (d.lang && d.lang !== currentLang) {
      currentLang = d.lang;
      localStorage.setItem('sh_lang', d.lang);
      updateNavLabels();
    }
    renderToday(d);
    // Header points — today javobidan olinadi
    if (d.points !== undefined) {
      document.getElementById('header-pts').textContent = '⭐ ' + d.points;
    }
    // Onboarding: data kelgandan keyin tekshiramiz
    maybeShowOnboard(d);
  } catch(e) {
    document.getElementById('today-content').innerHTML =
      `<div class="empty-state">
        <div class="icon"><svg width="28" height="28" viewBox="0 0 24 24" fill="none"><defs><linearGradient id="svgWarn" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#F6C93E"/><stop offset="100%" stop-color="#E07040"/></linearGradient></defs><path d="M12 3L2 21h20L12 3z" stroke="url(#svgWarn)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/><path d="M12 10v5M12 17.5v.5" stroke="url(#svgWarn)" stroke-width="2" stroke-linecap="round"/></svg></div>
        <div>${S('msg','data_error')}</div>
        <small style="color:var(--sub);margin-top:8px;display:block">${e}</small>
        <button onclick="loaded.today=false;loadToday()" style="margin-top:14px;padding:10px 20px;border-radius:12px;border:none;background:var(--bg);box-shadow:var(--sh-sm);font-family:inherit;font-size:13px;font-weight:600;cursor:pointer;color:var(--text)">${S('today','retry')}</button>
      </div>`;
  }
}

function renderToday(d) {
  const { habits, done_count, total, percent, today } = d;
  const currentJon = d.jon ?? 100;
  const dt = new Date(today);
  const _dayNamesMap = {
    uz:['Yakshanba','Dushanba','Seshanba','Chorshanba','Payshanba','Juma','Shanba'],
    ru:['Воскресенье','Понедельник','Вторник','Среда','Четверг','Пятница','Суббота'],
    en:['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'],
  };
  const _monthsMap = {
    uz:['Yanvar','Fevral','Mart','Aprel','May','Iyun','Iyul','Avgust','Sentabr','Oktabr','Noyabr','Dekabr'],
    ru:['Янв','Фев','Мар','Апр','Май','Июн','Июл','Авг','Сен','Окт','Ноя','Дек'],
    en:['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'],
  };
  const dayNames = _dayNamesMap[currentLang] || _dayNamesMap['uz'];
  const months   = _monthsMap[currentLang]   || _monthsMap['uz'];
  const dateStr  = `${dt.getDate()} ${months[dt.getMonth()]} — ${dayNames[dt.getDay()]}`;
  const allDone  = done_count === total && total > 0;

  // Vaqt bo'yicha sort: vaqtsiz eng oxirga, bajarilganlar done bo'lmaganlardan keyin
  const sortedHabits = [...(habits || [])].sort((a, b) => {
    // 1. Bajarilgan/bajarilmagan (bajarilmaganlar tepada)
    if (a.done !== b.done) return a.done ? 1 : -1;
    // 2. Vaqt bo'yicha o'sish tartibida (vaqtsiz eng oxirga)
    const ta = a.time && a.time !== 'vaqtsiz' ? a.time : '99:99';
    const tb = b.time && b.time !== 'vaqtsiz' ? b.time : '99:99';
    return ta.localeCompare(tb);
  });
  let cardsHtml = '';
  sortedHabits.forEach(h => {
    const rc  = h.repeat_count || 1;
    const tc  = h.today_count  || 0;
    const isRepeat = rc > 1;
    // Tugma: bitta bo'lsa SVG-tick, ko'p bo'lsa 3/5
    const btnContent = h.done ? '<svg width="14" height="14" viewBox="0 0 20 20" fill="none" style="display:inline;vertical-align:middle"><path d="M4 10l5 5 7-8" stroke="#ffffff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>' : (isRepeat && tc > 0 ? tc+'/'+rc : '');
    // Progress dots (repeat uchun)
    let dotsHtml = '';
    if (isRepeat) {
      dotsHtml = '<div class="repeat-dots" style="display:flex;gap:3px;margin-top:4px">'
        + Array.from({length: rc}, (_,i) =>
            '<div style="width:8px;height:8px;border-radius:50%;background:'+(i<tc?'var(--green)':'var(--bg)')+';box-shadow:'+(i<tc?'none':'var(--sh-in)')+'"></div>'
          ).join('') + '</div>';
    }
    const _esc = (s) => (s||'').replace(/'/g, "\\'");
    cardsHtml += `
      <div class="checkin-card ${h.done ? 'done' : ''}" id="ccard-${h.id}">
        <div class="checkin-actions-bg">
          <button class="cswipe-btn cswipe-edit" onclick="event.stopPropagation();openEdit('${h.id}','${_esc(h.name)}','${h.icon||'✅'}','${h.time||'vaqtsiz'}','${h.type||'simple'}',${h.repeat_count||1},'${encodeURIComponent(JSON.stringify(h.times||[]))}')">
            <svg width="18" height="18" viewBox="0 0 26 26" fill="none"><path d="M17 4L22 9L10 21L4 22L5 16L17 4Z" fill="#fff" opacity="0.9"/></svg>
            <span>${S('habits','edit_btn')}</span>
          </button>
          <button class="cswipe-btn cswipe-del" onclick="event.stopPropagation();deleteHabit('${h.id}')">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M10 11v6M14 11v6" stroke="#fff" stroke-width="2" stroke-linecap="round"/></svg>
            <span>${S('habits','delete_btn')}</span>
          </button>
        </div>
        <div class="checkin-front" data-hid="${h.id}" onclick="checkinFromFront('${h.id}', this)">
          <div class="checkin-icon">${h.icon || '<svg width="22" height="22" viewBox="0 0 24 24" fill="none"><defs><linearGradient id="svgDefIcon" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#4CAF7D"/><stop offset="100%" stop-color="#2D8A5E"/></linearGradient></defs><circle cx="12" cy="12" r="9" fill="url(#svgDefIcon)" opacity="0.2"/><path d="M7 12l4 4 6-7" stroke="url(#svgDefIcon)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>'}</div>
          <div class="checkin-info">
            <div class="checkin-name">${h.name}</div>
            <div class="checkin-meta">${isRepeat ? rc+' '+S('today','times_per_day')+' · ' : (h.time !== 'vaqtsiz' ? `<svg width="13" height="13" viewBox="0 0 20 20" fill="none" style="display:inline;vertical-align:middle"><defs><linearGradient id="svgClock" x1="0" y1="0" x2="20" y2="20" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#5B8DEF"/><stop offset="100%" stop-color="#A78BFA"/></linearGradient></defs><circle cx="10" cy="10" r="8" stroke="url(#svgClock)" stroke-width="2"/><path d="M10 6V10L13 12" stroke="url(#svgClock)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg> `+h.time+' · ' : '')}<svg width="13" height="13" viewBox="0 0 20 20" fill="none" style="display:inline;vertical-align:middle"><defs><linearGradient id="svgFire" x1="10" y1="0" x2="10" y2="20" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#F6C93E"/><stop offset="100%" stop-color="#E07040"/></linearGradient></defs><path d="M10 2C10 2 14 6 14 10C14 12 13 13.5 11.5 14.5C12 13 11.5 11.5 10.5 11C11 13 9.5 15 8 15.5C9 14 8.5 12 7 11C5.5 12.5 6 15 7 16.5C5.5 15.5 4 13.5 4 11C4 7 8 4 10 2Z" fill="url(#svgFire)"/></svg> ${h.streak} ${S('today','days_streak')}</div>
            ${dotsHtml}
            ${(() => {
              const d66 = h.days_66_done || 0;
              const pct66 = Math.min(100, Math.round(d66 / 66 * 100));
              const c66 = '#4CAF7D';
              const left66 = Math.max(0, 66 - d66);
              const label66 = d66 >= 66 ? S('msg','habit_formed') : S('msg','days_left').replace('{n}', left66);
              return '<div style="margin-top:5px" onclick="event.stopPropagation()">'
                + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:2px">'
                + '<div style="font-size:8px;color:var(--sub);font-weight:600;letter-spacing:.5px">\uD83C\uDFAF ' + d66 + '/66</div>'
                + '<div style="font-size:7px;font-weight:600;color:' + c66 + '">' + label66 + '</div>'
                + '</div>'
                + '<div style="height:3px;border-radius:2px;background:var(--bg);box-shadow:var(--sh-in);overflow:hidden">'
                + '<div style="height:100%;border-radius:2px;width:' + pct66 + '%;background:linear-gradient(90deg,' + c66 + '99,' + c66 + ');transition:width .6s ease"></div>'
                + '</div></div>';
            })()}
          </div>
          <button class="checkin-dots-btn" id="cdots-${h.id}" onclick="event.stopPropagation();toggleCheckinDrop('${h.id}')">
            <svg class="dots-icon" width="4" height="16" viewBox="0 0 4 16" fill="currentColor"><circle cx="2" cy="2" r="2"/><circle cx="2" cy="8" r="2"/><circle cx="2" cy="14" r="2"/></svg>
            <svg class="x-icon" width="16" height="16" viewBox="0 0 24 24" fill="none"><line x1="18" y1="6" x2="6" y2="18" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/><line x1="6" y1="6" x2="18" y2="18" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/></svg>
          </button>
          <button class="checkin-btn" id="cbtn-${h.id}" onclick="event.stopPropagation();checkin('${h.id}', document.getElementById('ccard-${h.id}'))" style="${isRepeat && !h.done && tc>0 ? 'font-size:11px;font-weight:700' : ''}">${btnContent}</button>
          <div class="checkin-dropdown" id="cdrop-${h.id}">
            <button class="checkin-dropdown-close" onclick="event.stopPropagation();closeAllCheckinDrops()">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none"><line x1="18" y1="6" x2="6" y2="18" stroke="var(--red)" stroke-width="2.5" stroke-linecap="round"/><line x1="6" y1="6" x2="18" y2="18" stroke="var(--red)" stroke-width="2.5" stroke-linecap="round"/></svg>
            </button>
            <button class="checkin-dropdown-item" onclick="event.stopPropagation();closeAllCheckinDrops();openEdit('${h.id}','${_esc(h.name)}','${h.icon||'✅'}','${h.time||'vaqtsiz'}','${h.type||'simple'}',${h.repeat_count||1},'${encodeURIComponent(JSON.stringify(h.times||[]))}')">
              <svg width="15" height="15" viewBox="0 0 26 26" fill="none"><path d="M17 4L22 9L10 21L4 22L5 16L17 4Z" fill="var(--accent2)" opacity="0.85"/></svg>
              ${S('habits','edit_btn')}
            </button>
            <button class="checkin-dropdown-item danger" onclick="event.stopPropagation();closeAllCheckinDrops();deleteHabit('${h.id}')">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none"><path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6" stroke="var(--red)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M10 11v6M14 11v6" stroke="var(--red)" stroke-width="2" stroke-linecap="round"/></svg>
              ${S('habits','delete_btn')}
            </button>
          </div>
          <div class="confetti-pop" id="pop-${h.id}">✨</div>
        </div>
      </div>`;
  });

  document.getElementById('today-content').innerHTML = `
    <div class="all-done-banner ${allDone ? 'show' : ''}" id="all-done-banner">
      <div class="bd-icon"><svg width="32" height="32" viewBox="0 0 32 32" fill="none"><defs><linearGradient id="svgParty" x1="0" y1="32" x2="32" y2="0" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#F6C93E"/><stop offset="100%" stop-color="#A78BFA"/></linearGradient></defs><path d="M4 28L14 4l14 14L4 28z" fill="url(#svgParty)" opacity="0.85"/><circle cx="24" cy="6" r="2" fill="#F6C93E"/><circle cx="28" cy="12" r="1.5" fill="#A78BFA"/><circle cx="20" cy="4" r="1" fill="#4CAF7D"/><path d="M22 10l2-3M26 8l3-1M24 14l3 1" stroke="#F6C93E" stroke-width="1.5" stroke-linecap="round"/></svg></div>
      <div class="bd-title">${S('today','all_done')}</div>
      <div class="bd-sub">${S('today','all_done_sub')} <svg width="13" height="13" viewBox="0 0 20 20" fill="none" style="display:inline;vertical-align:middle"><defs><linearGradient id="svgFireX" x1="10" y1="0" x2="10" y2="20" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#F6C93E"/><stop offset="100%" stop-color="#E07040"/></linearGradient></defs><path d="M10 2C10 2 14 6 14 10C14 12 13 13.5 11.5 14.5C12 13 11.5 11.5 10.5 11C11 13 9.5 15 8 15.5C9 14 8.5 12 7 11C5.5 12.5 6 15 7 16.5C5.5 15.5 4 13.5 4 11C4 7 8 4 10 2Z" fill="url(#svgFireX)"/></svg></div>
    </div>

    <div class="today-hero">
      <div class="today-date">${dateStr}</div>
      <div style="display:flex;justify-content:center;gap:24px;align-items:center;margin:16px 0 4px">
        <div style="display:flex;flex-direction:column;align-items:center;gap:4px">
          <div class="prog-ring-wrap" style="margin:0" id="prog-ring">${ringHTML(percent)}</div>
          <div style="font-size:10px;color:var(--sub);font-weight:600;letter-spacing:.5px">${S('today','habit_label')}</div>
        </div>
        <div style="display:flex;flex-direction:column;align-items:center;gap:4px">
          <div class="prog-ring-wrap" style="margin:0" id="jon-ring">${jonRingHTML(currentJon)}</div>
          <div style="font-size:10px;color:var(--sub);font-weight:600;letter-spacing:.5px">${S('today','life_label')}</div>
        </div>
      </div>
      <div class="today-sub" id="prog-sub">${done_count} / ${total} ${S('today','progress_sub')}</div>
    </div>

    <div style="display:flex;gap:8px;justify-content:center;margin:12px 0 4px">
      <button onclick="openAddFromToday()" type="button" style="font-size:13px;font-weight:600;color:#4CAF7D;background:none;border:none;cursor:pointer;padding:4px 8px">${S('today','add_habit')}</button>

    </div>

    <div class="section-title">${S('today','section_title')}</div>
    <div style="font-size:11px;color:var(--green);margin:-6px 0 10px 2px">${S('today','tap_hint')}</div>
    ${cardsHtml || '<div class="empty-state"><div class="icon"><svg width="28" height="28" viewBox="0 0 24 24" fill="none"><defs><linearGradient id="svgClip" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#8A8FA8"/><stop offset="100%" stop-color="#5B8DEF"/></linearGradient></defs><rect x="8" y="2" width="8" height="4" rx="1" stroke="url(#svgClip)" stroke-width="1.5"/><rect x="4" y="4" width="16" height="18" rx="2" stroke="url(#svgClip)" stroke-width="1.5"/><path d="M8 11h8M8 15h5" stroke="url(#svgClip)" stroke-width="1.5" stroke-linecap="round"/></svg></div>' + S('msg','no_habits_yet') + '</div>'}
    <div class="toast" id="toast-today"></div>`;

  // Swipe handlerlarni ulash
  setTimeout(() => _initCheckinSwipe(), 50);
}

async function checkin(hid, cardEl) {
  const btn = document.getElementById('cbtn-' + hid);
  const pop = document.getElementById('pop-' + hid);
  if (btn) btn.disabled = true;
  try {
    const res = await fetch(`${API}/checkin/${userId}/${hid}`, {
      method: 'POST',
      headers: { 'X-Init-Data': initData, 'X-User-Id': userId }
    });
    if (!res.ok) throw new Error(S('msg','server_error') + ': ' + res.status);
    const ct = res.headers.get('content-type') || '';
    if (!ct.includes('application/json')) throw new Error(S('msg','connection_error'));
    const result = await res.json();
    if (!result.ok) throw new Error(result.error);
    const isDone = result.done;
    const wasFullyDone = cardEl.classList.contains('done');

    cardEl.classList.toggle('done', isDone);
    if (btn) { btn.innerHTML = isDone ? '<svg width="14" height="14" viewBox="0 0 20 20" fill="none" style="display:inline;vertical-align:middle"><path d="M4 10l5 5 7-8" stroke="#ffffff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>' : ''; }

    // Meta va tugmani yangilash
    const rc  = result.repeat_count || 1;
    const tc  = result.today_count  || 0;
    if (btn) {
      btn.innerHTML = isDone ? '<svg width="14" height="14" viewBox="0 0 20 20" fill="none" style="display:inline;vertical-align:middle"><path d="M4 10l5 5 7-8" stroke="#ffffff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>' : (rc > 1 && tc > 0 ? tc+'/'+rc : '');
      btn.style.fontSize = (rc > 1 && !isDone && tc > 0) ? '11px' : '';
    }
    // Progress dots yangilash
    const info = cardEl.querySelector('.checkin-info');
    if (info && rc > 1) {
      let dots = info.querySelector('.repeat-dots');
      if (!dots) { dots = document.createElement('div'); dots.className='repeat-dots'; dots.style.cssText='display:flex;gap:3px;margin-top:4px'; info.appendChild(dots); }
      dots.innerHTML = Array.from({length: rc}, (_,i) =>
        '<div style="width:8px;height:8px;border-radius:50%;background:'+(i<tc?'var(--green)':'var(--bg)')+';box-shadow:'+(i<tc?'none':'var(--sh-in)')+'"></div>'
      ).join('');
    }
    const metaEl = cardEl.querySelector('.checkin-meta');
    if (metaEl) {
      const isRepeat = rc > 1;
      metaEl.innerHTML = isRepeat ? `${rc} ${S('today','times_per_day')} · <svg width="13" height="13" viewBox="0 0 20 20" fill="none" style="display:inline;vertical-align:middle"><defs><linearGradient id="svgFire" x1="10" y1="0" x2="10" y2="20" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#F6C93E"/><stop offset="100%" stop-color="#E07040"/></linearGradient></defs><path d="M10 2C10 2 14 6 14 10C14 12 13 13.5 11.5 14.5C12 13 11.5 11.5 10.5 11C11 13 9.5 15 8 15.5C9 14 8.5 12 7 11C5.5 12.5 6 15 7 16.5C5.5 15.5 4 13.5 4 11C4 7 8 4 10 2Z" fill="url(#svgFire)"/></svg> ${result.streak} ${S('today','days_streak')}` : `<svg width="13" height="13" viewBox="0 0 20 20" fill="none" style="display:inline;vertical-align:middle"><defs><linearGradient id="svgFire" x1="10" y1="0" x2="10" y2="20" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#F6C93E"/><stop offset="100%" stop-color="#E07040"/></linearGradient></defs><path d="M10 2C10 2 14 6 14 10C14 12 13 13.5 11.5 14.5C12 13 11.5 11.5 10.5 11C11 13 9.5 15 8 15.5C9 14 8.5 12 7 11C5.5 12.5 6 15 7 16.5C5.5 15.5 4 13.5 4 11C4 7 8 4 10 2Z" fill="url(#svgFire)"/></svg> ${result.streak} ${S('today','days_streak')}`;
    }

    if (isDone && pop) {
      pop.classList.add('show');
      setTimeout(() => pop.classList.remove('show'), 600);
    }

    // Ring yangilash
    if (data.today) {
      const habit = (data.today.habits || []).find(h => h.id === hid);
      const wasDone = habit ? habit.done : false;
      if (isDone && !wasDone) data.today.done_count += 1;
      else if (!isDone && wasDone) data.today.done_count -= 1;
      data.today.done_count = Math.max(0, Math.min(data.today.total, data.today.done_count));
      const pct = data.today.total ? Math.round(data.today.done_count / data.today.total * 100) : 0;
      const ringEl = document.getElementById('prog-ring');
      if (ringEl) ringEl.innerHTML = ringHTML(pct);
      const subEl = document.getElementById('prog-sub');
      if (subEl) subEl.textContent = `${data.today.done_count} / ${data.today.total} ${S('today','progress_sub')}`;
      if (habit) { habit.done = isDone; habit.streak = result.streak; }
    }

    if (result.all_done) {
      const b = document.getElementById('all-done-banner');
      if (b) b.classList.add('show');
    } else {
      const b = document.getElementById('all-done-banner');
      if (b) b.classList.remove('show');
    }

    if (result.points !== undefined) {
      const ptsEl = document.getElementById("header-pts");
      if (ptsEl) ptsEl.textContent = "⭐ " + result.points;
      if (data.today) data.today.points = result.points;
    }

    const rc2 = result.repeat_count || 1;
    const tc2 = result.today_count  || 0;
    const isUndo = !isDone && tc2 === 0 && wasFullyDone;
    if (isDone || isUndo) {
      const earnedAbs = Math.abs(result.earned ?? (isDone ? 5 : -5));
      const diffTxt = isDone ? `+${earnedAbs} ⭐` : `-${earnedAbs} ⭐`;
      showTodayToast(isDone ? S('msg','done_toast') + ' ' + diffTxt : S('msg','undone_toast') + ' ' + diffTxt);
      playHabitSound(isDone);
    } else if (rc2 > 1 && tc2 > 0 && tc2 < rc2) {
      // Repeat odat oraliq progress — ko'tariluvchi "pop" ovozi
      playProgressSound(tc2, rc2);
    }
    loaded.profile = false; loaded.rating = false; loaded.achievements = false; loaded.stats = false;
    if (document.getElementById('page-stats')?.classList.contains('active')) { loadStats(); }
    // Bajarilgan odat pastga, bekor qilingan odat tepaga
    const container = cardEl.parentNode;
    if (container) {
      if (isDone) {
        // Pastga: barcha done bo'lmagan kartalardan keyin qo'y
        const undoneCards = [...container.querySelectorAll('.checkin-card:not(.done)')];
        if (undoneCards.length > 0) {
          setTimeout(() => container.appendChild(cardEl), 300);
        }
      } else if (isUndo) {
        // Tepaga: birinchi done kartadan oldin qo'y
        const firstDone = container.querySelector('.checkin-card.done');
        if (firstDone && firstDone !== cardEl) {
          setTimeout(() => container.insertBefore(cardEl, firstDone), 300);
        }
      }
    }
    // Yangi badge popup
    if (isDone && result.new_badges && result.new_badges.length) {
      result.new_badges.forEach(b => showBadgePopup(b.icon, b.title, S('achievements','new_badge')));
    }
    // Streak milestone popup
    if (isDone && result.streak_milestone) {
      const sm = result.streak_milestone;
      setTimeout(() => showBadgePopup(sm.emoji, sm.title, `+${sm.bonus} ⭐ ${S('msg','bonus_ball')}`), result.new_badges && result.new_badges.length ? 1500 : 0);
    }
  } catch(e) {
    showTodayToast('❌ ' + S('msg','error_label') + ': ' + e.message, true);
  } finally {
    if (btn) btn.disabled = false;
  }
}

function showTodayToast(msg, err = false) {
  const t = document.getElementById('toast-today');
  if (!t) return;
  t.textContent = msg;
  t.className = 'toast show' + (err ? ' err' : '');
  setTimeout(() => { t.className = 'toast'; }, 2500);
}

// ── ESLATMALAR ──
async function loadReminders() {
  try {
    const d = await apiFetch(`habits/${userId}`);
    data.reminders = d.habits || [];
    renderReminders(d.habits || []);
  } catch(e) {
    document.getElementById('reminders-content').innerHTML =
      `<div class="empty-state"><div class="icon"><svg width="28" height="28" viewBox="0 0 24 24" fill="none"><defs><linearGradient id="svgWarn" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#F6C93E"/><stop offset="100%" stop-color="#E07040"/></linearGradient></defs><path d="M12 3L2 21h20L12 3z" stroke="url(#svgWarn)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/><path d="M12 10v5M12 17.5v.5" stroke="url(#svgWarn)" stroke-width="2" stroke-linecap="round"/></svg></div>${S('msg','data_error')}.</div>`;
  }
}

function renderReminders(habits) {
  if (!habits.length) {
    document.getElementById('reminders-content').innerHTML =
      `<div class="empty-state"><div class="icon"><svg width="28" height="28" viewBox="0 0 24 24" fill="none"><defs><linearGradient id="svgClip" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#8A8FA8"/><stop offset="100%" stop-color="#5B8DEF"/></linearGradient></defs><rect x="8" y="2" width="8" height="4" rx="1" stroke="url(#svgClip)" stroke-width="1.5"/><rect x="4" y="4" width="16" height="18" rx="2" stroke="url(#svgClip)" stroke-width="1.5"/><path d="M8 11h8M8 15h5" stroke="url(#svgClip)" stroke-width="1.5" stroke-linecap="round"/></svg></div>${S('reminders','empty')}</div>`;
    return;
  }

  const cardsHtml = habits.map(h => {
    const enabled      = h.reminder_enabled !== false;
    const repeat       = h.repeat || 'daily';
    const times        = Array.isArray(h.times) ? h.times : (h.time && h.time !== 'vaqtsiz' ? [h.time] : []);
    const repeatCount  = times.length || 1;
    const reps = [
      {id:'daily',    label:S('msg','rem_everyday')},
      {id:'weekdays', label:S('msg','rem_weekdays')},
      {id:'weekends', label:S('msg','rem_weekends')},
    ];

    // Vaqtlar ro'yxati HTML
    const timesListHtml = times.map((t, i) => `
      <div class="time-row" id="trow-${h.id}-${i}">
        <span class="time-lbl">${S('msg','time_slot_n').replace('{n}', i+1)}</span>
        <input class="time-input" type="time" id="tval-${h.id}-${i}" value="${t}">
        <button class="time-clear" onclick="removeTime('${h.id}',${i})" type="button" title="${S('msg','delete_btn')}"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" style="display:block"><line x1="18" y1="6" x2="6" y2="18" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/><line x1="6" y1="6" x2="18" y2="18" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/></svg></button>
      </div>`).join('');

    return `
      <div class="rem-card ${!enabled ? 'disabled' : ''}" id="remcard-${h.id}">
        <div class="rem-top">
          <div class="rem-icon">${h.icon || '<svg width="22" height="22" viewBox="0 0 24 24" fill="none"><defs><linearGradient id="svgDefIcon" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#4CAF7D"/><stop offset="100%" stop-color="#2D8A5E"/></linearGradient></defs><circle cx="12" cy="12" r="9" fill="url(#svgDefIcon)" opacity="0.2"/><path d="M7 12l4 4 6-7" stroke="url(#svgDefIcon)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>'}</div>
          <div style="flex:1">
            <div class="rem-name">${h.name}</div>
            <div style="font-size:11px;color:var(--sub);margin-top:2px">${repeatCount} ${S('reminders','repeat_meta')}</div>
          </div>
          <div class="toggle-wrap">
            <label class="toggle" onclick="toggleReminder('${h.id}', this)">
              <input type="checkbox" id="tog-${h.id}" ${enabled ? 'checked' : ''}>
              <div class="toggle-track"></div>
              <div class="toggle-thumb"></div>
            </label>
          </div>
        </div>
        <div class="rem-body" id="rembody-${h.id}">
          <div class="repeat-row">
            <span class="repeat-lbl">${S('msg','repeat_day')}</span>
            <div class="repeat-opts">
              ${reps.map(r => `<button class="rep-btn ${repeat===r.id?'active':''}" id="rep-${h.id}-${r.id}" onclick="setRepeat('${h.id}','${r.id}')" type="button">${r.label}</button>`).join('')}
            </div>
          </div>
          <div id="times-list-${h.id}">${timesListHtml}</div>
          <button class="rep-btn" style="width:100%;margin-top:6px;justify-content:center" onclick="addTime('${h.id}')" type="button">${S('reminders','add_time')}</button>
          <button class="rem-save-btn" id="rsave-${h.id}" onclick="saveReminder('${h.id}')" type="button" style="margin-top:8px">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" style="display:inline;vertical-align:middle;margin-right:5px"><defs><linearGradient id="svgSave" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#4CAF7D"/><stop offset="100%" stop-color="#2D8A5E"/></linearGradient></defs><path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z" stroke="url(#svgSave)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M17 21v-8H7v8M7 3v5h8" stroke="url(#svgSave)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>${S('profile','save_btn')}
          </button>
        </div>
      </div>`;
  }).join('');

  document.getElementById('reminders-content').innerHTML = `
    <div class="rem-info-card">
      <div class="rem-info-icon"><svg width="28" height="28" viewBox="0 0 26 26" fill="none"><defs><linearGradient id="svgBellInf" x1="0" y1="0" x2="26" y2="26" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#F6C93E"/><stop offset="100%" stop-color="#E07040"/></linearGradient></defs><path d="M13 3C13 3 8 6 8 13v5H5l2 2h12l2-2h-3v-5c0-7-5-10-5-10z" fill="url(#svgBellInf)" opacity="0.85"/><circle cx="13" cy="22" r="1.5" fill="url(#svgBellInf)"/></svg></div>
      <div class="rem-info-text">
        <div class="rem-info-title">${S('reminders','reminder_settings')}</div>
        <div class="rem-info-sub">${S('msg','rem_info')}</div>
      </div>
    </div>
    <div class="section-title">${S('reminders','habits_count')} (${habits.length})</div>
    ${cardsHtml}
    <div class="toast" id="toast-rem"></div>`;
}

function toggleReminder(hid, labelEl) {
  const card   = document.getElementById('remcard-' + hid);
  const body   = document.getElementById('rembody-' + hid);
  const tog    = document.getElementById('tog-' + hid);
  const enabled = tog.checked;
  card.classList.toggle('disabled', !enabled);
  body.style.opacity       = enabled ? '1' : '0.4';
  body.style.pointerEvents = enabled ? 'auto' : 'none';
  // rep butonlarni ham disable/enable
  ['daily','weekdays','weekends'].forEach(r => {
    const btn = document.getElementById(`rep-${hid}-${r}`);
    if (btn) btn.disabled = !enabled;
  });
}

function setRepeat(hid, val) {
  ['daily','weekdays','weekends'].forEach(r => {
    const btn = document.getElementById(`rep-${hid}-${r}`);
    if (btn) {
      btn.classList.toggle('active', r === val);
    }
  });
  // rem-body pointer-events ni tiklash
  const body = document.getElementById('rembody-' + hid);
  if (body) body.style.pointerEvents = 'auto';
}

function clearTime(hid) {
  const inp = document.getElementById('time-' + hid);
  if (inp) inp.value = '';
}

function addTime(hid) {
  const list = document.getElementById('times-list-' + hid);
  if (!list) return;
  const rows = list.querySelectorAll('.time-row');
  if (rows.length >= 10) return;
  const i = rows.length;
  const div = document.createElement('div');
  div.className = 'time-row';
  div.id = 'trow-' + hid + '-' + i;
  div.innerHTML = `<span class="time-lbl">${S('msg','time_slot_n').replace('{n}', i+1)}</span>
    <input class="time-input" type="time" id="tval-${hid}-${i}">
    <button class="time-clear" onclick="removeTime('${hid}',${i})" type="button" title="${S('msg','delete_btn')}"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" style="display:block"><line x1="18" y1="6" x2="6" y2="18" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/><line x1="6" y1="6" x2="18" y2="18" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/></svg></button>`;
  list.appendChild(div);
}

function removeTime(hid, idx) {
  const row = document.getElementById('trow-' + hid + '-' + idx);
  if (row) row.remove();
  // Qayta raqamlash
  const list = document.getElementById('times-list-' + hid);
  if (!list) return;
  list.querySelectorAll('.time-row').forEach((r, i) => {
    r.id = 'trow-' + hid + '-' + i;
    const lbl = r.querySelector('.time-lbl');
    if (lbl) lbl.textContent = S('msg','time_slot_n').replace('{n}', i+1);
    const inp = r.querySelector('input[type=time]');
    if (inp) inp.id = 'tval-' + hid + '-' + i;
    const btn = r.querySelector('.time-clear');
    if (btn) btn.setAttribute('onclick', "removeTime('" + hid + "'," + i + ")");
  });
}

async function saveReminder(hid) {
  const tog    = document.getElementById('tog-' + hid);
  const timeEl = document.getElementById('time-' + hid);
  const saveBtn= document.getElementById('rsave-' + hid);
  const enabled = tog ? tog.checked : true;
  const time    = timeEl ? timeEl.value : '';
  const repeat  = ['daily','weekdays','weekends'].find(r => {
    const btn = document.getElementById(`rep-${hid}-${r}`);
    return btn && btn.classList.contains('active');
  }) || 'daily';

  if (saveBtn) { saveBtn.textContent = S('profile','saving'); saveBtn.disabled = true; }

  // Vaqtlar ro'yxatini yig'ish
  const timesList = document.getElementById('times-list-' + hid);
  const timesArr = [];
  if (timesList) {
    timesList.querySelectorAll('input[type=time]').forEach(inp => {
      if (inp.value) timesArr.push(inp.value);
    });
  }
  const firstTime = timesArr[0] || '';

  try {
    const res = await fetch(`${API}/reminder/${userId}/${hid}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', 'X-Init-Data': initData, 'X-User-Id': userId },
      body: JSON.stringify({
        time:    firstTime || 'vaqtsiz',
        times:   timesArr,
        enabled: enabled,
        repeat:  repeat,
      })
    });
    const result = await res.json();
    if (!result.ok) throw new Error(result.error);

    if (saveBtn) {
      saveBtn.textContent = S('profile','saved');
      saveBtn.classList.add('saved');
      setTimeout(() => {
        saveBtn.textContent = S('profile','save');
        saveBtn.classList.remove('saved');
        saveBtn.disabled = false;
      }, 2000);
    }
    showRemToast(enabled && time ? S('msg','rem_set_on').replace('{time}', time) : S('msg','rem_set_off'));
    loaded.habits = false;
  } catch(e) {
    if (saveBtn) { saveBtn.textContent = S('profile','save'); saveBtn.disabled = false; }
    showRemToast('❌ ' + S('msg','error_label') + ': ' + e.message, true);
  }
}

function showRemToast(msg, err = false) {
  const t = document.getElementById('toast-rem');
  if (!t) return;
  t.textContent = msg;
  t.className = 'toast show' + (err ? ' err' : '');
  setTimeout(() => { t.className = 'toast'; }, 2500);
}

// ── YUTUQLAR ──
let achFilter = 'all';

async function loadAchievements() {
  try {
    const d = await apiFetch(`achievements/${userId}`);
    data.achievements = d;
    renderAchievements(d, achFilter);
  } catch(e) {
    document.getElementById('achievements-content').innerHTML =
      `<div class="empty-state"><div class="icon"><svg width="28" height="28" viewBox="0 0 24 24" fill="none"><defs><linearGradient id="svgWarn" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#F6C93E"/><stop offset="100%" stop-color="#E07040"/></linearGradient></defs><path d="M12 3L2 21h20L12 3z" stroke="url(#svgWarn)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/><path d="M12 10v5M12 17.5v.5" stroke="url(#svgWarn)" stroke-width="2" stroke-linecap="round"/></svg></div>${S('msg','data_error')}.</div>`;
  }
}

function renderAchievements(d, filter = 'all') {
  const { achievements, cats, earned_count, total_count } = d;

  // Ring SVG
  const pct  = total_count ? Math.round(earned_count / total_count * 100) : 0;
  const r    = 34; const circ = 2 * Math.PI * r;
  const dash = circ * pct / 100;
  const ringColor = pct >= 80 ? '#4CAF7D' : pct >= 40 ? '#5B8DEF' : '#E07040';
  const ringSvg = `<svg width="80" height="80" viewBox="0 0 80 80">
    <circle cx="40" cy="40" r="${r}" fill="none" stroke="#C8CBD8" stroke-width="6"/>
    <circle cx="40" cy="40" r="${r}" fill="none" stroke="${ringColor}" stroke-width="6"
      stroke-dasharray="${dash} ${circ}" stroke-dashoffset="${circ/4}" stroke-linecap="round"/>
  </svg>`;

  const sumHtml = `
    <div class="ach-summary">
      <div class="ach-ring-wrap">
        ${ringSvg}
        <div class="ach-ring-center">
          <div class="ach-ring-num">${pct}%</div>
        </div>
      </div>
      <div class="ach-sum-info">
        <div class="ach-sum-title">${S('achievements','title')}</div>
        <div class="ach-sum-sub">${earned_count} / ${total_count} ${S('achievements','earned_of')}</div>
      </div>
    </div>`;

  // Category tabs
  const allCats = [{id:'all',label:S('today','all_filter')}, ...cats];
  const catTabsHtml = allCats.map(c => `
    <button class="ach-cat-btn ${filter === c.id ? 'active' : ''}"
      onclick="filterAch('${c.id}')">${c.label}</button>`
  ).join('');

  // Cards
  const filtered = filter === 'all' ? achievements : achievements.filter(a => a.cat === filter);

  // Avval qozonilganlar
  const sorted = [...filtered].sort((a,b) => b.earned - a.earned);

  const cardsHtml = sorted.map(a => {
    const progPct   = a.req ? Math.round(a.current / a.req * 100) : 0;
    const progColor = a.earned ? '#4CAF7D' : progPct >= 50 ? '#5B8DEF' : '#E07040';
    return `
      <div class="ach-card ${a.earned ? 'earned' : 'locked'}">
        <div class="ach-badge">
          ${a.icon}
          ${a.earned ? '<div class="ach-badge-check"><svg width="16" height="16" viewBox="0 0 20 20" fill="none" style="display:inline;vertical-align:middle"><defs><linearGradient id="svgTick" x1="0" y1="0" x2="20" y2="20" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#4CAF7D"/><stop offset="100%" stop-color="#2D8A5E"/></linearGradient></defs><path d="M4 10l5 5 7-8" stroke="url(#svgTick)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg></div>' : ''}
        </div>
        <div class="ach-info">
          <div class="ach-title">${a.title}</div>
          <div class="ach-desc">${a.desc}</div>
          ${!a.earned ? `
          <div class="ach-prog-wrap">
            <div class="ach-prog-bg">
              <div class="ach-prog-fill" style="width:${progPct}%;background:${progColor}"></div>
            </div>
            <div class="ach-prog-txt">${a.current} / ${a.req}</div>
          </div>` : ''}
        </div>
      </div>`;
  }).join('');

  document.getElementById('achievements-content').innerHTML = `
    ${sumHtml}
    <div class="ach-cat-tabs">${catTabsHtml}</div>
    ${cardsHtml || `<div class="empty-state"><div class="icon"><svg width="28" height="28" viewBox="0 0 24 24" fill="none"><defs><linearGradient id="svgLock" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#8A8FA8"/><stop offset="100%" stop-color="#A78BFA"/></linearGradient></defs><rect x="5" y="11" width="14" height="10" rx="2" stroke="url(#svgLock)" stroke-width="2"/><path d="M8 11V7a4 4 0 018 0v4" stroke="url(#svgLock)" stroke-width="2" stroke-linecap="round"/><circle cx="12" cy="16" r="1.5" fill="url(#svgLock)"/></svg></div>${S('achievements','empty')}</div>`}`;
}

function filterAch(cat) {
  achFilter = cat;
  if (data.achievements) renderAchievements(data.achievements, cat);
}

// Badge popup (check-in dan keyin)
let popupQueue = [];
let popupBusy  = false;

function showBadgePopup(icon, title, desc) {
  popupQueue.push({icon, title, desc});
  if (!popupBusy) nextPopup();
}

function nextPopup() {
  if (!popupQueue.length) { popupBusy = false; return; }
  popupBusy = true;
  const {icon, title, desc} = popupQueue.shift();
  const el = document.getElementById('badge-popup');
  document.getElementById('bp-icon').textContent  = icon;
  document.getElementById('bp-title').innerHTML = '<svg width="16" height="16" viewBox="0 0 32 32" fill="none" style="display:inline;vertical-align:middle;margin-right:5px"><defs><linearGradient id="svgPartyJ" x1="0" y1="32" x2="32" y2="0" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#F6C93E"/><stop offset="100%" stop-color="#A78BFA"/></linearGradient></defs><path d="M4 28L14 4l14 14L4 28z" fill="url(#svgPartyJ)" opacity="0.85"/><circle cx="24" cy="6" r="2" fill="#F6C93E"/><circle cx="28" cy="12" r="1.5" fill="#A78BFA"/><circle cx="20" cy="4" r="1" fill="#4CAF7D"/></svg>' + title;
  document.getElementById('bp-sub').textContent   = desc;
  el.classList.add('show');
  setTimeout(() => {
    el.classList.remove('show');
    setTimeout(nextPopup, 400);
  }, 3000);
}

// ── CHECKIN CARD: SWIPE-TO-REVEAL ──
let _checkinSwiped = false; // swipe bo'lganda checkin qilmaslik uchun flag

function checkinFromFront(hid, frontEl) {
  // Agar swipe ochiq bo'lsa — yopamiz, checkin qilmaymiz
  if (frontEl.classList.contains('swiped')) {
    frontEl.classList.remove('swiped');
    // 3-nuqta vizual reset (✕ → ⋮)
    const dotsBtn = document.getElementById('cdots-' + hid);
    if (dotsBtn) dotsBtn.classList.remove('is-x');
    _checkinSwiped = false;
    return;
  }
  if (_checkinSwiped) { _checkinSwiped = false; return; }
  const card = document.getElementById('ccard-' + hid);
  if (card) checkin(hid, card);
}

function _initCheckinSwipe() {
  document.querySelectorAll('.checkin-front').forEach(front => {
    let startX = 0, curX = 0, swiping = false, startY = 0, locked = false;
    front.addEventListener('touchstart', e => {
      closeAllCheckinDrops();
      closeAllCheckinSwipes(front);
      startX = e.touches[0].clientX;
      startY = e.touches[0].clientY;
      curX = 0; swiping = true; locked = false;
      _checkinSwiped = false;
      front.style.transition = 'none';
    }, {passive: true});

    front.addEventListener('touchmove', e => {
      if (!swiping) return;
      const dx = e.touches[0].clientX - startX;
      const dy = e.touches[0].clientY - startY;
      // Vertikal scroll — swipeni bekor qilish
      if (!locked) {
        if (Math.abs(dy) > Math.abs(dx) && Math.abs(dy) > 8) {
          swiping = false; front.style.transition = ''; front.style.transform = ''; return;
        }
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
      // Agar harakat (swipe) bo'lmagan bo'lsa — tap, swiped holatga tegmaslik
      if (!locked) {
        front.style.transform = '';
        return;
      }
      const hid = front.getAttribute('data-hid');
      const dotsBtn = hid ? document.getElementById('cdots-' + hid) : null;
      if (curX < -50) {
        front.classList.add('swiped');
        if (dotsBtn) dotsBtn.classList.add('is-x'); // ⋮ → ✕
        _checkinSwiped = true; // checkin qilmaslik
      } else {
        front.classList.remove('swiped');
        if (dotsBtn) dotsBtn.classList.remove('is-x'); // ✕ → ⋮
      }
      front.style.transform = '';
    });
  });
}

function closeAllCheckinSwipes(except) {
  document.querySelectorAll('.checkin-front.swiped').forEach(f => {
    if (f !== except) {
      f.classList.remove('swiped');
      // 3-nuqta tugmasini ham vizual reset qilamiz (✕ → ⋮)
      const card = f.closest('.checkin-card');
      if (card) {
        const btn = card.querySelector('.checkin-dots-btn.is-x');
        if (btn) btn.classList.remove('is-x');
      }
    }
  });
}

// ── CHECKIN CARD: 3-NUQTA DROPDOWN ──
function toggleCheckinDrop(hid) {
  const card = document.getElementById('ccard-' + hid);
  if (!card) return;
  const front = card.querySelector('.checkin-front');
  if (!front) return;
  const dotsBtn = document.getElementById('cdots-' + hid);
  const wasOpen = front.classList.contains('swiped');
  // Avval hammasini yopamiz (boshqa kartalar va dropdownlar)
  closeAllCheckinSwipes();
  closeAllCheckinDrops();
  // Barcha 3-nuqta tugmalardan is-x ni olib tashlaymiz (boshqa karta vizual reset)
  document.querySelectorAll('.checkin-dots-btn.is-x').forEach(b => b.classList.remove('is-x'));
  if (!wasOpen) {
    // Yopiq edi → ochamiz va 3-nuqta ni ✕ ga aylantiramiz
    front.classList.add('swiped');
    if (dotsBtn) dotsBtn.classList.add('is-x');
    _checkinSwiped = true;
  } else {
    // Ochiq edi → yopildi (closeAllCheckinSwipes orqali), flag tozalanadi
    _checkinSwiped = false;
  }
}

function closeAllCheckinDrops() {
  document.querySelectorAll('.checkin-dropdown.open').forEach(d => d.classList.remove('open'));
}