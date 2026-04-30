// ── BUGUN ──
async function loadToday() {
  try {
    // Today va eslatmalarni parallel yuklash (tezlik uchun)
    const [d, _] = await Promise.all([
      apiFetch(`today/${userId}`),
      loadReminderCards()  // _cachedReminders ni yangilaydi
    ]);
    data.today = d;
    if (d.lang && d.lang !== currentLang) {
      currentLang = d.lang;
      localStorage.setItem('sh_lang', d.lang);
      updateNavLabels();
    }
    renderToday(d);
    // Header points — today javobidan olinadi (markaziy helper orqali)
    updateHeaderPts(d.points);
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
            <div class="checkin-meta">${isRepeat ? rc+S('today','times_per_day')+' · ' : (h.time !== 'vaqtsiz' ? `<svg width="13" height="13" viewBox="0 0 20 20" fill="none" style="display:inline;vertical-align:middle"><defs><linearGradient id="svgClock" x1="0" y1="0" x2="20" y2="20" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#A8ADB5"/><stop offset="100%" stop-color="#8A8F98"/></linearGradient></defs><circle cx="10" cy="10" r="8" stroke="url(#svgClock)" stroke-width="2"/><path d="M10 6V10L13 12" stroke="url(#svgClock)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg> `+h.time+' · ' : '')}<svg width="13" height="13" viewBox="0 0 20 20" fill="none" style="display:inline;vertical-align:middle;opacity:${h.streak > 0 ? '1' : '0.5'}"><defs><linearGradient id="svgFire" x1="10" y1="0" x2="10" y2="20" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#A8ADB5"/><stop offset="100%" stop-color="#8A8F98"/></linearGradient></defs><path d="M10 2C10 2 14 6 14 10C14 12 13 13.5 11.5 14.5C12 13 11.5 11.5 10.5 11C11 13 9.5 15 8 15.5C9 14 8.5 12 7 11C5.5 12.5 6 15 7 16.5C5.5 15.5 4 13.5 4 11C4 7 8 4 10 2Z" fill="url(#svgFire)"/></svg> ${h.streak}</div>
            ${dotsHtml}
            ${(() => {
              const d66 = h.days_66_done || 0;
              const pct66 = Math.min(100, Math.round(d66 / 66 * 100));
              const c66 = '#4CAF7D';
              return '<div style="margin-top:6px" onclick="event.stopPropagation()">'
                + '<div style="height:3px;border-radius:2px;background:var(--bg);box-shadow:var(--sh-in);overflow:hidden">'
                + '<div style="height:100%;border-radius:2px;width:' + pct66 + '%;background:linear-gradient(90deg,' + c66 + '99,' + c66 + ');transition:width .6s ease"></div>'
                + '</div></div>';
            })()}
          </div>
          <button class="checkin-dots-btn" id="cdots-${h.id}" onclick="event.stopPropagation();toggleCheckinDrop('${h.id}')">
            <svg class="dots-icon" width="4" height="16" viewBox="0 0 4 16" fill="currentColor"><circle cx="2" cy="2" r="2"/><circle cx="2" cy="8" r="2"/><circle cx="2" cy="14" r="2"/></svg>
            <svg class="x-icon" width="16" height="16" viewBox="0 0 24 24" fill="none"><line x1="18" y1="6" x2="6" y2="18" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/><line x1="6" y1="6" x2="18" y2="18" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/></svg>
          </button>
          <button class="checkin-btn" id="cbtn-${h.id}" onclick="event.stopPropagation();checkin('${h.id}', document.getElementById('ccard-${h.id}'))" style="${isRepeat && !h.done && tc>0 ? 'font-size:11px;font-weight:700' : ''}">${!h.done ? '<svg class="habit-glow-ring" viewBox="0 0 50 50" preserveAspectRatio="xMidYMid meet"><circle class="habit-glow-circle" cx="25" cy="25" r="23" fill="none" stroke="#4CAF7D" stroke-width="2"/></svg>' : ''}<span class="checkin-btn-content">${btnContent}</span></button>
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
    <div class="all-done-banner" id="all-done-banner">
      <div class="bd-icon"><svg width="32" height="32" viewBox="0 0 32 32" fill="none"><defs><linearGradient id="svgParty" x1="0" y1="32" x2="32" y2="0" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#F6C93E"/><stop offset="100%" stop-color="#A78BFA"/></linearGradient></defs><path d="M4 28L14 4l14 14L4 28z" fill="url(#svgParty)" opacity="0.85"/><circle cx="24" cy="6" r="2" fill="#F6C93E"/><circle cx="28" cy="12" r="1.5" fill="#A78BFA"/><circle cx="20" cy="4" r="1" fill="#4CAF7D"/><path d="M22 10l2-3M26 8l3-1M24 14l3 1" stroke="#F6C93E" stroke-width="1.5" stroke-linecap="round"/></svg></div>
      <div class="bd-title">${S('today','all_done')}</div>
      <div class="bd-sub">${S('today','all_done_sub')} <svg width="13" height="13" viewBox="0 0 20 20" fill="none" style="display:inline;vertical-align:middle"><defs><linearGradient id="svgFireX" x1="10" y1="0" x2="10" y2="20" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#F6C93E"/><stop offset="100%" stop-color="#E07040"/></linearGradient></defs><path d="M10 2C10 2 14 6 14 10C14 12 13 13.5 11.5 14.5C12 13 11.5 11.5 10.5 11C11 13 9.5 15 8 15.5C9 14 8.5 12 7 11C5.5 12.5 6 15 7 16.5C5.5 15.5 4 13.5 4 11C4 7 8 4 10 2Z" fill="url(#svgFireX)"/></svg></div>
    </div>

    <div class="today-hero">
      <div class="hero-party-badge ${allDone ? 'show' : ''}" id="hero-party-badge">${_partySvg()}</div>
      <div class="today-date">${dateStr}</div>
      <div style="display:flex;justify-content:center;gap:24px;align-items:center;margin:16px 0 4px">
        <div style="display:flex;flex-direction:column;align-items:center;gap:4px">
          <div class="prog-ring-wrap" style="margin:0" id="prog-ring">${ringHTML(percent)}</div>
          <div style="font-size:10px;color:var(--sub);font-weight:600;letter-spacing:.5px" id="habit-label">${S('today','habit_label')} ${done_count}/${total}</div>
        </div>
        <div style="display:flex;flex-direction:column;align-items:center;gap:4px">
          <div class="prog-ring-wrap" style="margin:0" id="jon-ring">${jonRingHTML(currentJon)}</div>
          <div style="font-size:10px;color:var(--sub);font-weight:600;letter-spacing:.5px">${S('today','life_label')}</div>
        </div>
      </div>
    </div>

    <div style="display:flex;gap:8px;justify-content:center;margin:14px 0 6px;flex-wrap:wrap">
      <button onclick="openAddFromToday()" type="button" class="today-add-btn">${S('today','add_habit')}</button>
      <button onclick="openReminderModal()" type="button" class="today-add-rem-btn">${S('today','add_reminder')}</button>
    </div>

    <div class="section-title">${S('today','section_title')}</div>
    ${cardsHtml || '<div class="empty-state"><div class="icon"><svg width="28" height="28" viewBox="0 0 24 24" fill="none"><defs><linearGradient id="svgClip" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#8A8FA8"/><stop offset="100%" stop-color="#5B8DEF"/></linearGradient></defs><rect x="8" y="2" width="8" height="4" rx="1" stroke="url(#svgClip)" stroke-width="1.5"/><rect x="4" y="4" width="16" height="18" rx="2" stroke="url(#svgClip)" stroke-width="1.5"/><path d="M8 11h8M8 15h5" stroke="url(#svgClip)" stroke-width="1.5" stroke-linecap="round"/></svg></div>' + S('msg','no_habits_yet') + '</div>'}

    ${renderReminderSections(_cachedReminders)}

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
    // v468: banner + konfetti uchun avvalgi "hamma bajarildi" holatini saqlab qolamiz
    const wasAllDone = !!(data.today && data.today.total > 0 && data.today.done_count >= data.today.total);

    cardEl.classList.toggle('done', isDone);

    // Meta va tugmani yangilash
    const rc  = result.repeat_count || 1;
    const tc  = result.today_count  || 0;
    if (btn) {
      const mainContent = isDone ? '<svg width="14" height="14" viewBox="0 0 20 20" fill="none" style="display:inline;vertical-align:middle"><path d="M4 10l5 5 7-8" stroke="#ffffff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>' : (rc > 1 && tc > 0 ? tc+'/'+rc : '');
      // SVG glow ring-ga tegmaymiz (animatsiya uzluksiz davom etsin), faqat matn qismini yangilaymiz
      let contentSpan = btn.querySelector('.checkin-btn-content');
      if (!contentSpan) {
        contentSpan = document.createElement('span');
        contentSpan.className = 'checkin-btn-content';
        btn.appendChild(contentSpan);
      }
      contentSpan.innerHTML = mainContent;
      // Glow ring-ni kerak boʻlsa qoʻshish yoki olib tashlash
      let glowSvg = btn.querySelector('.habit-glow-ring');
      if (!isDone && !glowSvg) {
        // Undo: glow qayta kerak. Boshqa kartaning animatsiyasi bilan sinxronlash uchun
        // mavjud glow-ning computed stroke-dashoffset qiymatini olamiz
        const existingGlow = document.querySelector('.habit-glow-circle');
        const currentOffset = existingGlow ? getComputedStyle(existingGlow).strokeDashoffset : '0';
        btn.insertAdjacentHTML('afterbegin', '<svg class="habit-glow-ring" viewBox="0 0 50 50" preserveAspectRatio="xMidYMid meet"><circle class="habit-glow-circle" cx="25" cy="25" r="23" fill="none" stroke="#4CAF7D" stroke-width="2"/></svg>');
        const newCircle = btn.querySelector('.habit-glow-circle');
        if (newCircle && currentOffset && currentOffset !== '0px') {
          // Animatsiyani oʻsha nuqtadan davom ettirish
          const offsetNum = parseFloat(currentOffset);
          const progress = Math.abs(offsetNum % 144) / 144; // 0..1 oraligʻidagi joriy progres
          newCircle.style.animationDelay = (-progress * 3) + 's';
        }
      } else if (isDone && glowSvg) {
        glowSvg.remove();
      }
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
      metaEl.innerHTML = isRepeat ? `${rc}${S('today','times_per_day')} · <svg width="13" height="13" viewBox="0 0 20 20" fill="none" style="display:inline;vertical-align:middle"><defs><linearGradient id="svgFire" x1="10" y1="0" x2="10" y2="20" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#A8ADB5"/><stop offset="100%" stop-color="#8A8F98"/></linearGradient></defs><path d="M10 2C10 2 14 6 14 10C14 12 13 13.5 11.5 14.5C12 13 11.5 11.5 10.5 11C11 13 9.5 15 8 15.5C9 14 8.5 12 7 11C5.5 12.5 6 15 7 16.5C5.5 15.5 4 13.5 4 11C4 7 8 4 10 2Z" fill="url(#svgFire)"/></svg> ${result.streak}` : `<svg width="13" height="13" viewBox="0 0 20 20" fill="none" style="display:inline;vertical-align:middle"><defs><linearGradient id="svgFire" x1="10" y1="0" x2="10" y2="20" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#A8ADB5"/><stop offset="100%" stop-color="#8A8F98"/></linearGradient></defs><path d="M10 2C10 2 14 6 14 10C14 12 13 13.5 11.5 14.5C12 13 11.5 11.5 10.5 11C11 13 9.5 15 8 15.5C9 14 8.5 12 7 11C5.5 12.5 6 15 7 16.5C5.5 15.5 4 13.5 4 11C4 7 8 4 10 2Z" fill="url(#svgFire)"/></svg> ${result.streak}`;
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
      const labelEl = document.getElementById('habit-label');
      if (labelEl) labelEl.textContent = `${S('today','habit_label')} ${data.today.done_count}/${data.today.total}`;
      if (habit) { habit.done = isDone; habit.streak = result.streak; }
    }

    // v468: "Barchasi bajarildi!" karta — faqat yangi yutuq paytida chiqadi
    // (sahifa ochilganda 100% bo'lsa spam qilmaydi, render qilinishi boshida yashirin)
    if (result.all_done && !wasAllDone) {
      // Yangi 100%! → banner + konfetti + 3s keyin yuqoriga kollaps
      const b = document.getElementById('all-done-banner');
      if (b) {
        b.classList.remove('hiding');
        b.classList.add('show');
        // 3 soniyadan keyin avtomatik yuqoriga chiqib yo'qoladi
        setTimeout(() => {
          if (b.classList.contains('show')) {
            b.classList.add('hiding');
            // Animatsiya tugagach .show va .hiding ni olib tashlaymiz (qayta ishlatish uchun)
            setTimeout(() => { b.classList.remove('show'); b.classList.remove('hiding'); }, 600);
          }
        }, 3000);
      }
      _triggerConfetti();
      // v469: bayram emoji (🎉 SVG) — today-hero yuqori-o'ng burchakda
      const pb = document.getElementById('hero-party-badge');
      if (pb) pb.classList.add('show');
    } else if (!result.all_done) {
      // Undo holati: banner va bayram emoji darhol yashirin bo'lsin
      const b = document.getElementById('all-done-banner');
      if (b) { b.classList.remove('show'); b.classList.remove('hiding'); }
      // v469: bayram emoji — 100% dan chiqqanda olib tashlanadi
      const pb = document.getElementById('hero-party-badge');
      if (pb) pb.classList.remove('show');
    }
    // Izoh: agar result.all_done && wasAllDone bo'lsa (allaqachon banner chiqqan yoki
    // hali kollaps qilinayotgan bo'lsa) — hech narsa qilmaymiz, konfetti takror otilmaydi

    if (result.points !== undefined) {
      updateHeaderPts(result.points);
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
    // (kartalar oraligʻidagina koʻchadi — eslatmalar blokiga oʻtib ketmaydi)
    const container = cardEl.parentNode;
    if (container) {
      if (isDone) {
        // Pastga: barcha done bo'lmagan kartalardan keyin qo'y,
        // lekin oxirgi .checkin-card dan keyinga emas (aks holda eslatmalar ostiga tushadi)
        const undoneCards = [...container.querySelectorAll('.checkin-card:not(.done)')];
        if (undoneCards.length > 0) {
          setTimeout(() => {
            const allCards = [...container.querySelectorAll('.checkin-card')];
            const lastCard = allCards[allCards.length - 1];
            if (lastCard && lastCard !== cardEl) {
              // Oxirgi kartadan keyingi pozitsiyaga qo'yamiz (lastCard.nextSibling oldiga)
              // Bu .checkin-card lar bloki ichida qoldiradi, eslatmalar blokiga o'tmaydi
              container.insertBefore(cardEl, lastCard.nextSibling);
            } else {
              container.appendChild(cardEl);
            }
          }, 300);
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

// v469: Bayram emoji (🎉) SVG — NASA yashil palitra, today-hero yuqori-o'ng burchakda
// Faqat barcha odatlar bajarilganda (100%) ko'rinadi, pop + float animatsiyalar bilan
function _partySvg() {
  return '<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">'
    + '<defs>'
    +   '<linearGradient id="pbCone" x1="4" y1="28" x2="18" y2="14" gradientUnits="userSpaceOnUse">'
    +     '<stop offset="0%" stop-color="#2D8A5E"/>'
    +     '<stop offset="100%" stop-color="#4CAF7D"/>'
    +   '</linearGradient>'
    +   '<linearGradient id="pbLight" x1="4" y1="28" x2="16" y2="16" gradientUnits="userSpaceOnUse">'
    +     '<stop offset="0%" stop-color="#7DC29A"/>'
    +     '<stop offset="100%" stop-color="#A8D9BE"/>'
    +   '</linearGradient>'
    + '</defs>'
    // Party popper konus (cone) — chapdan pastga qaragan
    + '<path d="M4 28L14 6L22 14L4 28Z" fill="url(#pbCone)"/>'
    // Konus ichidagi och-yashil yorug'lik qismi
    + '<path d="M4 28L11 12L17 18L4 28Z" fill="url(#pbLight)" opacity="0.65"/>'
    // Atrofga tarqalayotgan zarrachalar (yashil nuqtalar va yulduzchalar)
    + '<circle cx="24" cy="6" r="1.8" fill="#4CAF7D"/>'
    + '<circle cx="28" cy="11" r="1.3" fill="#7DC29A"/>'
    + '<circle cx="20" cy="4" r="1.1" fill="#2D8A5E"/>'
    + '<circle cx="26" cy="18" r="1.2" fill="#4CAF7D"/>'
    + '<circle cx="29" cy="22" r="1" fill="#A8D9BE"/>'
    // Chiziq-zarrachalar (party popper'dan otilayotgan simlar)
    + '<path d="M22 10L25 7" stroke="#4CAF7D" stroke-width="1.6" stroke-linecap="round"/>'
    + '<path d="M25 13L29 14" stroke="#7DC29A" stroke-width="1.4" stroke-linecap="round"/>'
    + '<path d="M23 17L27 16" stroke="#2D8A5E" stroke-width="1.4" stroke-linecap="round"/>'
    // Yulduzcha (sparkle) aksent
    + '<path d="M22 4L22.6 5.4L24 6L22.6 6.6L22 8L21.4 6.6L20 6L21.4 5.4L22 4Z" fill="#A8D9BE"/>'
    + '</svg>';
}

// v468: Bayram konfettisi — barcha odatlar bajarilganda otiladi
// NASA yashil palitra (brand izchilligi — 19-qoida): 3 daraja yashil + bir xil mayda aksent
function _triggerConfetti() {
  // Agar oldingi konfetti hali ekranda bo'lsa — takroriy qo'shmaymiz
  if (document.querySelector('.confetti-container')) return;
  const container = document.createElement('div');
  container.className = 'confetti-container';
  const colors = ['#2D8A5E', '#4CAF7D', '#7DC29A', '#A8D9BE']; // yashil 4 daraja
  const count = 42; // zichlik: bayramona, lekin performance uchun cheklangan
  const vw = window.innerWidth || document.documentElement.clientWidth;
  for (let i = 0; i < count; i++) {
    const piece = document.createElement('div');
    piece.className = 'confetti-piece';
    const color = colors[Math.floor(Math.random() * colors.length)];
    const startX = Math.random() * vw;
    const drift = (Math.random() - 0.5) * 220; // chapga-o'ngga 110px oraliq
    const spin = (Math.random() * 720 + 360) * (Math.random() < 0.5 ? 1 : -1);
    const duration = 2.4 + Math.random() * 1.4; // 2.4-3.8s — asta kamayib to'xtasin
    const delay = Math.random() * 0.35; // zarlar bir-bir emas, tabiiy tarqalsin
    const w = 6 + Math.random() * 5; // 6-11px kenglik
    const h = 10 + Math.random() * 8; // 10-18px balandlik
    const shape = Math.random() < 0.3 ? '50%' : '2px'; // 30% yumaloq, 70% to'rtburchak
    piece.style.left = startX + 'px';
    piece.style.width = w + 'px';
    piece.style.height = h + 'px';
    piece.style.background = color;
    piece.style.borderRadius = shape;
    piece.style.animationDuration = duration + 's';
    piece.style.animationDelay = delay + 's';
    piece.style.setProperty('--drift', drift + 'px');
    piece.style.setProperty('--spin', spin + 'deg');
    container.appendChild(piece);
  }
  document.body.appendChild(container);
  // Konfetti tugagach containerni olib tashlaymiz (max duration + delay + zapas)
  setTimeout(() => { if (container.parentNode) container.parentNode.removeChild(container); }, 4500);
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

  // === Chess.com uslubi: oddiy sarlavha + counter (sumHtml/catTabsHtml olib tashlandi) ===
  // JS o'zgaruvchilar (cats, filterAch, achFilter) saqlanadi - kelajakda kerak bo'lishi mumkin

  const headerHtml = `
    <div class="ach-page-header">
      <div class="ach-page-title">${S('achievements','title')}</div>
      <div class="ach-page-counter">${earned_count} / ${total_count} ${S('achievements','earned_of')}</div>
    </div>`;

  // Cards
  const filtered = filter === 'all' ? achievements : achievements.filter(a => a.cat === filter);

  // Avval qozonilganlar
  const sorted = [...filtered].sort((a,b) => b.earned - a.earned);

  // Sana formatlash: "2026-04-25" → "25 Apr 2026" (joriy til month_abbr bilan)
  // window'ga chiqarilgan - openAchievementDetail() ham foydalanadi
  window._formatAchDate = (iso) => {
    if (!iso || typeof iso !== 'string') return '';
    const m = iso.match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (!m) return '';
    const year = m[1];
    const month = parseInt(m[2], 10);
    const day = parseInt(m[3], 10);
    const months = S('profile', 'month_abbr');
    const monStr = (Array.isArray(months) && months[month]) ? months[month] : String(month);
    return `${day} ${monStr} ${year}`;
  };

  // Yutuqlarni window'ga saqlaymiz - modal foydalanish uchun
  window._achievementsList = sorted;

  const cardsHtml = sorted.map(a => {
    // Qulflanganda emoji oʻrniga 🔒 koʻrsatamiz (emoji grayscale qilib boʻlmaydi)
    const iconContent = a.earned ? a.icon : '🔒';
    return `
      <div class="ach-card-mini ${a.earned ? 'earned' : 'locked'}" onclick="openAchievementDetail('${a.id}')">
        <div class="ach-mini-badge">
          ${iconContent}
          ${a.earned ? '<div class="ach-mini-check"><svg width="14" height="14" viewBox="0 0 20 20" fill="none"><defs><linearGradient id="svgTickMini-' + a.id + '" x1="0" y1="0" x2="20" y2="20" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#4CAF7D"/><stop offset="100%" stop-color="#2D8A5E"/></linearGradient></defs><path d="M4 10l5 5 7-8" stroke="url(#svgTickMini-' + a.id + ')" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg></div>' : ''}
        </div>
        <div class="ach-mini-title">${a.title}</div>
      </div>`;
  }).join('');

  document.getElementById('achievements-content').innerHTML = `
    ${headerHtml}
    ${cardsHtml ? `<div class="ach-grid">${cardsHtml}</div>` : `<div class="empty-state"><div class="icon"><svg width="28" height="28" viewBox="0 0 24 24" fill="none"><defs><linearGradient id="svgLock" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#8A8FA8"/><stop offset="100%" stop-color="#A78BFA"/></linearGradient></defs><rect x="5" y="11" width="14" height="10" rx="2" stroke="url(#svgLock)" stroke-width="2"/><path d="M8 11V7a4 4 0 018 0v4" stroke="url(#svgLock)" stroke-width="2" stroke-linecap="round"/><circle cx="12" cy="16" r="1.5" fill="url(#svgLock)"/></svg></div>${S('achievements','empty')}</div>`}`;
}

function filterAch(cat) {
  achFilter = cat;
  if (data.achievements) renderAchievements(data.achievements, cat);
}

// Yutuq batafsil modal (kartani bosganda ochiladi)
function openAchievementDetail(achId) {
  const list = window._achievementsList || [];
  const a = list.find(x => x.id === achId);
  if (!a) return;

  const earned = !!a.earned;
  const iconContent = earned ? a.icon : '🔒';
  const earnedDateStr = (earned && a.earned_at && window._formatAchDate) ? window._formatAchDate(a.earned_at) : '';
  const progPct = a.req ? Math.round(a.current / a.req * 100) : 0;
  const progColor = earned ? '#4CAF7D' : progPct >= 50 ? '#5B8DEF' : '#E07040';

  // Eski modal bor boʻlsa olib tashlaymiz
  const existing = document.getElementById('ach-detail-modal');
  if (existing) existing.remove();

  const modal = document.createElement('div');
  modal.id = 'ach-detail-modal';
  modal.className = 'ach-detail-backdrop';
  modal.onclick = (e) => { if (e.target === modal) closeAchievementDetail(); };

  modal.innerHTML = `
    <div class="ach-detail-card ${earned ? 'earned' : 'locked'}">
      <button class="ach-detail-close" onclick="closeAchievementDetail()" aria-label="${S('achievements','close')}">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M6 6l12 12M18 6L6 18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
      </button>
      <div class="ach-detail-badge ${earned ? 'earned' : 'locked'}">${iconContent}</div>
      ${earnedDateStr ? `<div class="ach-detail-date">${earnedDateStr}</div>` : ''}
      <div class="ach-detail-title">${a.title}</div>
      ${!earned ? `
        <div class="ach-detail-progress">
          <div class="ach-detail-prog-bg">
            <div class="ach-detail-prog-fill" style="width:${progPct}%;background:${progColor}"></div>
          </div>
          <div class="ach-detail-prog-txt">${a.current} / ${a.req}</div>
        </div>
      ` : ''}
    </div>
  `;
  document.body.appendChild(modal);
  // Animatsiya uchun keyingi frame'da .visible klassi
  requestAnimationFrame(() => modal.classList.add('visible'));
}

function closeAchievementDetail() {
  const modal = document.getElementById('ach-detail-modal');
  if (!modal) return;
  modal.classList.remove('visible');
  setTimeout(() => modal.remove(), 200);
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
  // Checkin faqat ✓ tugma orqali bo'ladi (kartning boshqa joyiga bosish hech narsa qilmaydi)
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
      // Yo'nalish qulflash: birinchi ustun yo'nalish g'olib
      if (!locked) {
        if (Math.abs(dy) > Math.abs(dx) && Math.abs(dy) > 8) {
          swiping = false; front.style.transition = ''; front.style.transform = ''; return;
        }
        if (Math.abs(dx) > 8) locked = true;
      }
      // Gorizontal qulflangach — vertikal scroll'ni to'xtatish (aks holda ikkalasi birga ishlaydi)
      if (locked && e.cancelable) e.preventDefault();
      curX = dx;
      if (curX > 0) curX = 0;
      if (curX < -130) curX = -130;
      front.style.transform = 'translateX(' + curX + 'px)';
    }, {passive: false});

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
