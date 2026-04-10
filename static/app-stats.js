// ── STATISTIKA ──

// Reyting sahifasi uchun (page-stats) — faqat rating + guruh/do'st
async function loadStats() {
  _friendsLoaded = false;
  setStatSub(_statSub || 'rating');
  obMarkDone('stats');
}

// Statistika sahifasi uchun (page-habits → yangi statistika tab)
async function loadStatsPage() {
  try {
    const d = await apiFetch(`stats/${userId}`);
    data.stats = d;
    renderStats(d);
  } catch(e) {
    document.getElementById('stats-detail-content').innerHTML =
      `<div class="empty-state"><div class="icon"><svg width="28" height="28" viewBox="0 0 24 24" fill="none"><defs><linearGradient id="svgWarn" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#F6C93E"/><stop offset="100%" stop-color="#E07040"/></linearGradient></defs><path d="M12 3L2 21h20L12 3z" stroke="url(#svgWarn)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/><path d="M12 10v5M12 17.5v.5" stroke="url(#svgWarn)" stroke-width="2" stroke-linecap="round"/></svg></div>${S('msg','data_error')}.<br><small>${e}</small></div>`;
  }
}

function renderStats(d) {
  const { summary, weekly, heatmap, days_30, habit_stats, today, trend } = d;


  // ── Summary card data (Variant C — Mini Charts v2) ──
  const todayDone  = summary.today_done  || 0;
  const todayTotal = summary.today_total || 1;
  const todayPct   = todayTotal ? Math.round(todayDone / todayTotal * 100) : 0;
  const todayLeft  = Math.max(0, todayTotal - todayDone);

  const bestStreak = summary.best_streak || Math.max(summary.streak, 1);

  const topName = summary.top_habit_name || S('stats','no_habits');
  const topPct  = summary.top_habit_pct  || 0;

  const worstName = summary.worst_habit_name || '';
  const worstPct  = summary.worst_habit_pct  || 0;
  const worstColor = worstPct <= 20 ? '#E05252' : worstPct <= 40 ? '#E07040' : '#D4963A';

  // Streak sparkline: haftalik bajarilish % dan (weekly array)
  const streakSpark = (() => {
    if (!weekly || weekly.length < 2) return {line:'', area:'', last:null};
    const W = 120, H = 30, pad = 2;
    const vals = weekly.map(w => w.total ? Math.round(w.count / w.total * 100) : 0);
    const maxV = Math.max(...vals, 1);
    const pts = vals.map((v, i) => ({
      x: pad + (i / (vals.length - 1)) * (W - 2 * pad),
      y: pad + (1 - v / maxV) * (H - 2 * pad)
    }));
    const line = pts.map((p, i) => (i === 0 ? 'M' : 'L') + p.x.toFixed(1) + ',' + p.y.toFixed(1)).join(' ');
    const area = line + ' L' + pts[pts.length-1].x.toFixed(1) + ',' + H + ' L' + pts[0].x.toFixed(1) + ',' + H + ' Z';
    return {line, area, last: pts[pts.length-1]};
  })();

  // Bugungi mini bars
  const todayBars = [];
  for (let i = 0; i < todayTotal; i++) todayBars.push(i < todayDone);

  // SVG icon helpers (professional gradient icons)
  const svgTarget = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none"><defs><linearGradient id="siTgt" x1="0" y1="24" x2="24" y2="0"><stop offset="0%" stop-color="#4CAF7D"/><stop offset="100%" stop-color="#6EDAA0"/></linearGradient></defs><circle cx="12" cy="12" r="10" stroke="url(#siTgt)" stroke-width="2"/><circle cx="12" cy="12" r="6" stroke="url(#siTgt)" stroke-width="2"/><circle cx="12" cy="12" r="2.5" fill="url(#siTgt)"/></svg>';
  const svgFire = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none"><defs><linearGradient id="siFlm" x1="0" y1="24" x2="24" y2="0"><stop offset="0%" stop-color="#E07040"/><stop offset="100%" stop-color="#F6C93E"/></linearGradient></defs><path d="M12 23c-4.97 0-8-3.58-8-7.5 0-3.07 2.17-5.77 4.5-7.5.5-.37 1.2.1 1.05.7-.42 1.64.22 3.16 1.45 3.8.36.19.8-.04.84-.44.52-4.78 3.66-7.56 4.66-8.06.47-.23 1.02.17.9.68-.58 2.44.52 4.82 2.6 5.82.36.17.57.54.57.93 0 2.87-.5 5.07-2.07 7.07C16.5 21 14.5 23 12 23z" fill="url(#siFlm)"/></svg>';
  const svgWarn = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none"><defs><linearGradient id="siWrn" x1="0" y1="24" x2="24" y2="0"><stop offset="0%" stop-color="#E05252"/><stop offset="100%" stop-color="#E07040"/></linearGradient></defs><path d="M12 3L2 21h20L12 3z" stroke="url(#siWrn)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="url(#siWrn)" fill-opacity=".12"/><path d="M12 10v5" stroke="url(#siWrn)" stroke-width="2.5" stroke-linecap="round"/><circle cx="12" cy="17.5" r="1.2" fill="url(#siWrn)"/></svg>';
  const svgTrophy = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none"><defs><linearGradient id="siTrp" x1="0" y1="24" x2="24" y2="0"><stop offset="0%" stop-color="#D4963A"/><stop offset="100%" stop-color="#FFE566"/></linearGradient></defs><path d="M6 4h12v2c0 4-2.5 7-5 8v2h2a2 2 0 012 2H7a2 2 0 012-2h2v-2c-2.5-1-5-4-5-8V4z" fill="url(#siTrp)" fill-opacity=".15" stroke="url(#siTrp)" stroke-width="1.8"/><path d="M6 6H4a1 1 0 00-1 1v1c0 2 1.5 3.5 3 4" stroke="url(#siTrp)" stroke-width="1.8" stroke-linecap="round"/><path d="M18 6h2a1 1 0 011 1v1c0 2-1.5 3.5-3 4" stroke="url(#siTrp)" stroke-width="1.8" stroke-linecap="round"/></svg>';
  const svgStar = '<svg width="10" height="10" viewBox="0 0 24 24" fill="none"><path d="M12 2l3 7h7l-5.5 4.5 2 7L12 16l-6.5 4.5 2-7L2 9h7z" fill="#E07040"/></svg>';

  // Donut helper — ikki odat kartasi uchun bir xil chart
  const donutSVG = (pct, gradId, c1, c2, textColor) => {
    const r = 28, circ = 2 * Math.PI * r;
    return '<svg width="72" height="72" viewBox="0 0 72 72">'
      + '<circle cx="36" cy="36" r="' + r + '" fill="none" stroke="var(--bg)" stroke-width="5" class="sc-ring-bg"/>'
      + '<circle cx="36" cy="36" r="' + r + '" fill="none" stroke="url(#' + gradId + ')" stroke-width="5"'
      + ' stroke-dasharray="' + (circ * pct / 100).toFixed(1) + ' ' + circ.toFixed(1) + '"'
      + ' stroke-dashoffset="' + (circ * 0.25).toFixed(1) + '" stroke-linecap="round" class="sc-ring-fill"/>'
      + '<defs><linearGradient id="' + gradId + '" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="' + c1 + '"/><stop offset="100%" stop-color="' + c2 + '"/></linearGradient></defs>'
      + '<text x="36" y="41" text-anchor="middle" font-size="15" font-weight="800" fill="' + textColor + '" font-family="DM Mono,monospace">' + pct + '%</text>'
      + '</svg>';
  };

  const sumHtml = `
    <div class="summary-grid">

      <!-- 1. BUGUNGI NATIJA — mini bar chart -->
      <div class="sc-card sc-card-anim" style="--sc-color:#4CAF7D">
        <div class="sc-header">
          <div>
            <div class="sc-val">${todayDone}<span class="sc-val-sub">/${todayTotal}</span></div>
            <div class="sc-lbl">${S('stats','today_momentum')}</div>
          </div>
          <div class="sc-badge-icon">${svgTarget}</div>
        </div>
        <div class="sc-chart">
          ${todayTotal <= 12
            ? '<div class="sc-mini-bars">' + todayBars.map((done, i) => '<div class="sc-mini-bar ' + (done ? 'sc-done' : '') + '" style="animation-delay:' + (i * 60) + 'ms"></div>').join('') + '</div>'
            : '<div style="width:100%;display:flex;flex-direction:column;justify-content:flex-end;gap:4px"><div style="height:10px;border-radius:5px;background:var(--bg);box-shadow:var(--sh-in);overflow:hidden"><div style="height:100%;border-radius:5px;background:linear-gradient(90deg,#6EDAA0,#4CAF7D);width:' + todayPct + '%;transition:width .6s ease"></div></div></div>'
          }
        </div>
        <div class="sc-foot">${todayPct}% &middot; ${todayLeft > 0 ? todayLeft + ' ' + S('stats','left_today') : S('stats','all_done')}</div>
      </div>

      <!-- 2. STREAK — sparkline (haftalik bajarilish %) -->
      <div class="sc-card sc-card-anim" style="--sc-color:#E07040">
        <div class="sc-header">
          <div>
            <div class="sc-val">${summary.streak}</div>
            <div class="sc-lbl">${S('stats','streak_label')}</div>
          </div>
          <div class="sc-badge-icon">${svgFire}</div>
        </div>
        <div class="sc-chart">
          <svg width="100%" viewBox="0 0 120 42" preserveAspectRatio="none" style="display:block;overflow:visible">
            <defs>
              <linearGradient id="scSparkFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#E07040" stop-opacity="0.25"/><stop offset="100%" stop-color="#E07040" stop-opacity="0"/></linearGradient>
              <linearGradient id="scSparkLine" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stop-color="#F6C93E"/><stop offset="100%" stop-color="#E07040"/></linearGradient>
            </defs>
            ${streakSpark.area ? '<path d="' + streakSpark.area + '" fill="url(#scSparkFill)"/>' : ''}
            ${streakSpark.line ? '<path d="' + streakSpark.line + '" fill="none" stroke="url(#scSparkLine)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>' : ''}
            ${streakSpark.last ? '<circle cx="' + streakSpark.last.x.toFixed(1) + '" cy="' + streakSpark.last.y.toFixed(1) + '" r="3" fill="#E07040" stroke="#fff" stroke-width="1.5"/>' : ''}
            ${(() => { const dAbbr = S('stats','day_abbr') || ['Ya','Du','Se','Ch','Pa','Ju','Sh']; const wLen = weekly ? weekly.length : 0; if (wLen < 2) return ''; return weekly.map((w, wi) => { const xp = 2 + (wi / (wLen - 1)) * 116; return '<text x="'+xp.toFixed(1)+'" y="40" text-anchor="middle" font-size="7" fill="var(--sub)" font-weight="600">'+dAbbr[new Date(w.date).getDay()]+'</text>'; }).join(''); })()}
          </svg>
        </div>
        <div class="sc-foot">${svgStar} ${S('stats','record_label')}: ${bestStreak}</div>
      </div>

      <!-- 3. ENG ZAIF ODAT — donut -->
      <div class="sc-card sc-card-anim" style="--sc-color:${worstColor}">
        <div class="sc-header">
          <div>
            <div class="sc-val" style="color:${worstColor}">${worstPct}%</div>
            <div class="sc-lbl">${S('stats','worst_habit')}</div>
          </div>
          <div class="sc-badge-icon">${svgWarn}</div>
        </div>
        <div class="sc-chart" style="align-items:center;justify-content:center">
          ${donutSVG(worstPct, 'scDonutW', worstColor, '#E07040', worstColor)}
        </div>
        <div class="sc-foot sc-foot-trunc">${worstName || S('stats','no_habits')}</div>
      </div>

      <!-- 4. ENG BARQAROR ODAT — donut -->
      <div class="sc-card sc-card-anim" style="--sc-color:#4CAF7D">
        <div class="sc-header">
          <div>
            <div class="sc-val" style="color:#4CAF7D">${topPct}%</div>
            <div class="sc-lbl">${S('stats','top_habit')}</div>
          </div>
          <div class="sc-badge-icon">${svgTrophy}</div>
        </div>
        <div class="sc-chart" style="align-items:center;justify-content:center">
          ${donutSVG(topPct, 'scDonutT', '#6EDAA0', '#4CAF7D', '#4CAF7D')}
        </div>
        <div class="sc-foot sc-foot-trunc">${topName}</div>
      </div>

    </div>`;
  // ── Bar chart (haftalik) ──
  const maxCount = Math.max(...weekly.map(w => w.total), 1);
  const dayLabels = S('stats','day_abbr') || ['Ya','Du','Se','Ch','Pa','Ju','Sh'];
  const barsHtml = weekly.map((w, i) => {
    const pct   = w.total ? Math.round(w.count / w.total * 100) : 0;
    const hPx   = pct > 0 ? Math.max(8, Math.round(pct * 0.7)) : 4;
    const color = pct >= 80 ? '#4CAF7D' : pct >= 40 ? '#5B8DEF' : pct > 0 ? '#E07040' : '#C8CBD8';
    const isToday = w.date === today;
    return `
      <div class="bar-col">
        <div class="bar-num" style="color:${pct > 0 ? color : 'var(--sub)'}">${pct > 0 ? pct + '%' : '·'}</div>
        <div class="bar-fill" style="height:${hPx}px;background:${color};${isToday ? 'box-shadow:0 0 0 2px '+color+'44,var(--sh-sm)' : ''}"></div>
        <div class="bar-lbl" style="${isToday ? 'color:var(--text);font-weight:700' : ''}">${dayLabels[new Date(w.date).getDay()]}</div>
      </div>`;
  }).join('');

  const barChartHtml = `
    <div class="bar-chart">
      <div class="bar-chart-title">${S('stats','week_chart')}</div>
      <div class="bars">${barsHtml}</div>
    </div>`;

  // ── 30 kunlik area chart ──
  const monthlyDays = d.monthly || weekly;
  const areaChartHtml = (() => {
    if (!monthlyDays || monthlyDays.length < 2) return '';
    const W = 320, H = 100, padX = 10, padY = 8;
    const pcts = monthlyDays.map(w => w.total ? Math.round(w.count / w.total * 100) : 0);
    const maxPct = Math.max(...pcts, 1);
    const avg = Math.round(pcts.reduce((a,b)=>a+b,0) / pcts.length);
    const pts = pcts.map((p, i) => ({
      x: padX + (i / (pcts.length - 1)) * (W - 2 * padX),
      y: padY + (1 - p / maxPct) * (H - 2 * padY)
    }));
    let pathD = 'M' + pts[0].x + ',' + pts[0].y;
    for (let i = 1; i < pts.length; i++) {
      const cp = (pts[i].x - pts[i-1].x) / 2.5;
      pathD += ' C' + (pts[i-1].x+cp) + ',' + pts[i-1].y + ' ' + (pts[i].x-cp) + ',' + pts[i].y + ' ' + pts[i].x + ',' + pts[i].y;
    }
    const areaD = pathD + ' L' + pts[pts.length-1].x + ',' + (H-padY) + ' L' + pts[0].x + ',' + (H-padY) + ' Z';
    const gridLines = [25,50,75].map(g => {
      const gy = padY + (1 - g/maxPct) * (H - 2*padY);
      return (gy > padY && gy < H-padY) ? '<line x1="'+padX+'" y1="'+gy.toFixed(1)+'" x2="'+(W-padX)+'" y2="'+gy.toFixed(1)+'" stroke="var(--sub)" stroke-width="0.5" opacity="0.2" stroke-dasharray="4 3"/>' : '';
    }).join('');
    const dateLabels = [0,9,19,29].filter(i => i < monthlyDays.length).map(i => {
      const x = padX + (i/(pcts.length-1)) * (W-2*padX);
      const dd = new Date(monthlyDays[i].date).getDate();
      return '<text x="'+x.toFixed(1)+'" y="'+(H+2)+'" text-anchor="middle" font-size="9" fill="var(--sub)" font-weight="600">'+dd+'</text>';
    }).join('');
    const last = pts[pts.length-1];
    const lastPct = pcts[pcts.length-1];
    const dotColor = lastPct >= 80 ? '#4CAF7D' : lastPct >= 40 ? '#5B8DEF' : '#E07040';
    return '<div class="bar-chart" style="padding-bottom:18px">'
      + '<div class="bar-chart-title">' + S('stats','month_chart') + '</div>'
      + '<div style="display:flex;align-items:center;gap:12px;margin-bottom:8px">'
      + '<div style="font-size:28px;font-weight:900;color:var(--text);font-family:DM Mono,monospace">' + avg + '%</div>'
      + '<div style="font-size:10px;color:var(--sub);line-height:1.4">' + S('stats','avg_30') + '</div></div>'
      + '<svg width="100%" viewBox="0 0 '+W+' '+(H+10)+'" preserveAspectRatio="none">'
      + '<defs><linearGradient id="areaFill30" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#4CAF7D" stop-opacity="0.3"/><stop offset="100%" stop-color="#4CAF7D" stop-opacity="0.02"/></linearGradient>'
      + '<linearGradient id="lineG30" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stop-color="#5B8DEF"/><stop offset="100%" stop-color="#4CAF7D"/></linearGradient></defs>'
      + gridLines
      + '<path d="'+areaD+'" fill="url(#areaFill30)"/>'
      + '<path d="'+pathD+'" fill="none" stroke="url(#lineG30)" stroke-width="2.5" stroke-linecap="round"/>'
      + '<circle cx="'+last.x.toFixed(1)+'" cy="'+last.y.toFixed(1)+'" r="4" fill="'+dotColor+'" stroke="#fff" stroke-width="2"/>'
      + '<text x="'+(last.x > W-40 ? last.x-6 : last.x+6).toFixed(1)+'" y="'+(last.y-8).toFixed(1)+'" font-size="9" font-weight="800" fill="'+dotColor+'" text-anchor="'+(last.x > W-40 ? 'end' : 'start')+'" font-family="DM Mono,monospace">'+lastPct+'%</text>'
      + dateLabels + '</svg></div>';
  })();

  // ── Haftalik tendensiya ──
  let trendHtml = '';
  if (trend) {
    const dir   = trend.direction;
    const diff  = Math.abs(trend.diff);
    const arrow = dir === 'up'   ? '↑' : dir === 'down' ? '↓' : '→';
    const aColor= dir === 'up'   ? '#4CAF7D' : dir === 'down' ? '#E07040' : '#8A8FA8';
    const msg   = dir === "up"   ? S('msg','week_better') :
                  dir === "down" ? S('msg','week_worse') :
                                   S('msg','week_same');
    const barThis = Math.max(2, trend.this_week);
    const barPrev = Math.max(2, trend.prev_week);
    const barMax  = Math.max(barThis, barPrev, 1);

    trendHtml = `
      <div class="trend-card">
        <div class="trend-header">
          <div class="trend-title">${S('stats','weekly_trend')}</div>
          <div class="trend-diff-pill" style="background:${aColor}15;color:${aColor}">
            <span style="font-size:16px;line-height:1">${arrow}</span>
            ${diff > 0 ? diff + '%' : ''}
          </div>
        </div>
        <div class="trend-compare">
          <div class="trend-compare-item">
            <div class="trend-compare-label">${S('msg','prev_week')}</div>
            <div class="trend-compare-bar"><div class="trend-compare-bar-fill" style="background:#C8CBD8;width:${Math.round(barPrev/barMax*100)}%"></div></div>
            <div class="trend-compare-val" style="color:var(--sub)">${trend.prev_week}%</div>
          </div>
          <div class="trend-compare-item">
            <div class="trend-compare-label">${S('stats','this_week')}</div>
            <div class="trend-compare-bar"><div class="trend-compare-bar-fill" style="background:${aColor};width:${Math.round(barThis/barMax*100)}%"></div></div>
            <div class="trend-compare-val" style="color:${aColor}">${trend.this_week}%</div>
          </div>
        </div>
        <div class="trend-msg" style="color:${aColor}">${msg}</div>
      </div>`; 
  }

  // ── Heatmap (30 kun — GitHub style) ──
  // monthly arraydan har kunning % ni hisoblash
  const monthlyMap = {};
  (monthlyDays || []).forEach(m => { monthlyMap[m.date] = m.total ? Math.round(m.count / m.total * 100) : 0; });

  // Kunlarni hafta kunlari bo'yicha joylashtirish (Du=0, Ya=6)
  const hmDayLabels = S('stats','hm_week_days') || ['Du','Se','Ch','Pa','Ju','Sh','Ya'];

  // 30 kunlik celllar — har biri hm-lv0/lv1/lv2/lv3
  const hmCells = days_30.map(d => {
    const pctVal = monthlyMap[d] || (heatmap[d] ? 70 : 0);
    const lvl = pctVal === 0 ? '' : pctVal < 40 ? 'hm-lv1' : pctVal < 80 ? 'hm-lv2' : 'hm-lv3';
    const isToday = d === today;
    return `<div class="hm-cell ${lvl} ${isToday ? 'today-cell' : ''}" title="${d}: ${pctVal}%"></div>`;
  });

  // Birinchi kunning hafta kuni (0=Du, 6=Ya for our layout; JS getDay: 0=Su)
  const firstDate = new Date(days_30[0]);
  const firstDayJS = firstDate.getDay(); // 0=Su, 1=Mo, ... 6=Sa
  // Bizning grid: Du=0 row, Se=1, ... Ya=6
  const firstDayRow = firstDayJS === 0 ? 6 : firstDayJS - 1;

  // Bo'sh celllar qo'shish (birinchi kun to'g'ri qatorga tushishi uchun)
  const padCells = Array(firstDayRow).fill('<div class="hm-cell" style="visibility:hidden"></div>');
  const allHmCells = [...padCells, ...hmCells].join('');

  // Hafta kun nomlari (7 ta)
  const dayLabelsHtml = hmDayLabels.map(l => `<span>${l}</span>`).join('');

  const heatmapHtml = `
    <div class="heatmap-wrap">
      <div class="heatmap-title">${S('stats','heatmap_title')}</div>
      <div class="heatmap-outer">
        <div class="heatmap-day-labels">${dayLabelsHtml}</div>
        <div class="heatmap-grid">${allHmCells}</div>
      </div>
      <div style="display:flex;justify-content:space-between;align-items:center;margin-top:8px">
        <div class="heatmap-legend">
          <div class="hm-leg" style="background:var(--bg);box-shadow:var(--sh-in)"></div> ${S('stats','hm_not_done')}
          <div class="hm-leg hm-lv1" style="margin-left:8px"></div> ${S('stats','hm_partial')}
          <div class="hm-leg hm-lv3" style="margin-left:8px"></div> ${S('stats','hm_full')}
        </div>
        <div style="font-size:9px;color:var(--sub);font-weight:600">${todayDone}/${todayTotal} ${S('stats','today_momentum').toLowerCase()}</div>
      </div>
    </div>`;

  // ── Har bir odat ──
  let habitCardsHtml = '';
  (habit_stats || []).forEach((h, hIdx) => {
    const pctColor = h.percent >= 80 ? '#4CAF7D' : h.percent >= 50 ? '#5B8DEF' : '#E07040';

    // ── Donut chart (percent) ──
    const r = 22; const circ = 2 * Math.PI * r;
    const dash = circ * h.percent / 100;
    const donutId = `dnt-${hIdx}`;
    const donutSvg = `<svg width="56" height="56" viewBox="0 0 56 56">
      <circle cx="28" cy="28" r="${r}" fill="none" stroke="#C8CBD8" stroke-width="5"/>
      <circle cx="28" cy="28" r="${r}" fill="none" stroke="${pctColor}" stroke-width="5"
        stroke-dasharray="${dash.toFixed(1)} ${circ.toFixed(1)}"
        stroke-dashoffset="${(circ/4).toFixed(1)}" stroke-linecap="round"/>
      <text x="28" y="33" text-anchor="middle" font-size="11" font-weight="800"
        fill="${pctColor}" font-family="DM Mono,monospace">${h.percent}%</text>
    </svg>`;

    // ── Mini bar chart (7 kunlik week_dots) ──
    const dayLbls = S('stats','day_abbr') || ['Ya','Du','Se','Ch','Pa','Ju','Sh'];
    const miniBars = (h.week_dots || []).map((v, i) => {
      const barH = v ? 28 : 6;
      const barC = v ? pctColor : '#C8CBD8';
      const today_d = new Date(); today_d.setDate(today_d.getDate() - (6 - i));
      const lbl = dayLbls[today_d.getDay()];
      return `<div class="hstat-minibar-col">
        <div class="hstat-minibar-fill" style="height:${barH}px;background:${barC}"></div>
        <div class="hstat-minibar-day">${lbl}</div>
      </div>`;
    }).join('');

    habitCardsHtml += `
      <div class="hstat-card">
        <div class="hstat-top">
          <div class="hstat-icon">${h.icon}</div>
          <div class="hstat-info">
            <div class="hstat-name">${h.name}</div>
            <div class="hstat-sub"><svg width="13" height="13" viewBox="0 0 20 20" fill="none" style="display:inline;vertical-align:middle"><defs><linearGradient id="svgFire${hIdx}" x1="10" y1="0" x2="10" y2="20" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#F6C93E"/><stop offset="100%" stop-color="#E07040"/></linearGradient></defs><path d="M10 2C10 2 14 6 14 10C14 12 13 13.5 11.5 14.5C12 13 11.5 11.5 10.5 11C11 13 9.5 15 8 15.5C9 14 8.5 12 7 11C5.5 12.5 6 15 7 16.5C5.5 15.5 4 13.5 4 11C4 7 8 4 10 2Z" fill="url(#svgFire${hIdx})"/></svg> ${h.streak} ${S('stats','streak_suffix')}</div>
          </div>
        </div>
        <div class="hstat-nums">
          <div class="hstat-num-box">
            <div class="hstat-num-val">${h.done_7}</div>
            <div class="hstat-num-lbl">${S('msg','streak_days').replace('{n}','7')}</div>
          </div>
          <div class="hstat-num-box">
            <div class="hstat-num-val">${h.done_30}</div>
            <div class="hstat-num-lbl">${S('msg','streak_days').replace('{n}','30')}</div>
          </div>
          <div class="hstat-num-box">
            <div class="hstat-num-val">${h.total_done}</div>
            <div class="hstat-num-lbl">${S('stats','total_label')}</div>
          </div>
        </div>
        <div class="hstat-charts-row">
          <div class="hstat-donut-wrap">
            ${donutSvg}
            <div class="hstat-donut-lbl">${S('stats','completion')}</div>
          </div>
          <div class="hstat-minibar-wrap">
            <div class="hstat-minibar-lbl">${S('stats','last7')}</div>
            <div class="hstat-minibar-bars">${miniBars}</div>
          </div>
        </div>
        ${(() => {
          const d66 = h.days_66_done || 0;
          const total66 = 66;
          const pct66 = Math.round(d66 / total66 * 100);
          const c66 = d66 >= 66 ? '#4CAF7D' : d66 >= 33 ? '#5B8DEF' : '#E07040';
          const left66 = Math.max(0, 66 - d66);
          const label66 = d66 >= 66
            ? S('msg','habit_formed')
            : S('msg','days_left').replace('{n}', left66);
          return `<div style="margin-top:10px">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
              <div style="font-size:9px;color:var(--sub);text-transform:uppercase;letter-spacing:1px;font-weight:600">🎯 ${S('msg','calc_66')}</div>
              <div style="font-size:10px;font-weight:700;color:${c66}">${d66}/66 · ${label66}</div>
            </div>
            <div style="height:6px;border-radius:3px;background:var(--bg);box-shadow:var(--sh-in);overflow:hidden">
              <div style="height:100%;border-radius:3px;width:${pct66}%;background:linear-gradient(90deg,${c66}99,${c66});transition:width .6s ease"></div>
            </div>
          </div>`;
        })()}
      </div>`;
  });

  document.getElementById('stats-detail-content').innerHTML = `
    <div class="section-title">${S('stats','general')}</div>
    ${sumHtml}
    ${barChartHtml}
    ${trendHtml}
    ${areaChartHtml}
    ${heatmapHtml}
    <button type="button" onclick="generateShareCard()" id="share-card-btn"
      style="width:100%;padding:14px 16px;border:none;border-radius:16px;cursor:pointer;
        background:linear-gradient(135deg,#5B8DEF,#A78BFA);color:#fff;
        font-size:13px;font-weight:700;display:flex;align-items:center;justify-content:center;gap:8px;
        margin-bottom:8px;box-shadow:0 4px 12px #5B8DEF33">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M4 12v7a2 2 0 002 2h12a2 2 0 002-2v-7M16 6l-4-4-4 4M12 2v13" stroke="#fff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
      ${S('stats','share_btn')}
    </button>
    <canvas id="share-canvas" style="display:none"></canvas>
    <div style="margin-top:16px">
      <button type="button" onclick="toggleHabitStats()" id="habit-stats-btn"
        style="width:100%;display:flex;align-items:center;justify-content:space-between;
          padding:13px 16px;border:none;cursor:pointer;border-radius:16px;
          background:var(--bg);box-shadow:var(--sh-sm);text-align:left">
        <div style="display:flex;align-items:center;gap:8px">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><defs><linearGradient id="svgHStat" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#4CAF7D"/><stop offset="100%" stop-color="#5B8DEF"/></linearGradient></defs><rect x="8" y="2" width="8" height="4" rx="1" stroke="url(#svgHStat)" stroke-width="1.5"/><rect x="4" y="4" width="16" height="18" rx="2" stroke="url(#svgHStat)" stroke-width="1.5"/><path d="M8 11h8M8 15h5" stroke="url(#svgHStat)" stroke-width="1.5" stroke-linecap="round"/></svg>
          <span style="font-size:12px;font-weight:700;color:var(--text);text-transform:uppercase;letter-spacing:1px">${S('stats','per_habit')}</span>
        </div>
        <svg id="habit-stats-chevron" width="16" height="16" viewBox="0 0 24 24" fill="none"
          style="transition:transform .3s;flex-shrink:0;transform:rotate(0deg)">
          <path d="M6 9l6 6 6-6" stroke="var(--sub)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>
      <div id="habit-stats-body" style="display:none;margin-top:8px">
        ${habitCardsHtml || '<div class="empty-state"><div class="icon">\u{1F4CB}</div>' + S('msg','no_habits_yet') + '</div>'}
      </div>
    </div>`;
}

function toggleHabitStats() {
  const body    = document.getElementById('habit-stats-body');
  const chevron = document.getElementById('habit-stats-chevron');
  const isOpen  = body.style.display !== 'none';
  body.style.display      = isOpen ? 'none' : 'block';
  chevron.style.transform = isOpen ? 'rotate(0deg)' : 'rotate(180deg)';
}

async function generateShareCard() {
  const btn = document.getElementById('share-card-btn');
  let _btnOrigHTML = '';
  if (btn) {
    _btnOrigHTML = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" style="animation:spin 1s linear infinite"><circle cx="12" cy="12" r="10" stroke="#fff3" stroke-width="3"/><path d="M12 2a10 10 0 0 1 10 10" stroke="#fff" stroke-width="3" stroke-linecap="round"/></svg> ' + ({"uz":"Yuklanmoqda...","ru":"Загрузка...","en":"Loading..."}[currentLang] || "Yuklanmoqda...");
  }
  try {
    const d = data.stats;
    if (!d) return;
    const s = d.summary;
    const w = d.weekly || [];
    const monthlyDays = d.monthly || w;
    const name = data.profile?.display_name || data.profile?.name || user.first_name || 'User';

    // ── Story format: 1080x1920 (9:16) ──
    const W = 1080, H = 1920;
    const pad=50, cW=W-pad*2, gap=20;

    const canvas = document.getElementById('share-canvas') || document.createElement('canvas');
    canvas.width = W; canvas.height = H;
    const ctx = canvas.getContext('2d');

    // ── Theme detection ──
    const isDark = document.body.classList.contains('dark');
    const P = isDark ? {
      bg1:'#1E2130', bg2:'#181B28', surface:'#252840', raised:'#2A2D42',
      text:'#E8EAF2', sub:'#6B6E80', sub2:'#4A4D60',
      shDark:'#13151F', shLight:'#2D3048',
    } : {
      bg1:'#E0E3EA', bg2:'#D6D9E0', surface:'#E8EBF2', raised:'#ECEEF5',
      text:'#3A3D4A', sub:'#8A8D9A', sub2:'#B0B3BE',
      shDark:'#B8BBCA', shLight:'#FFFFFF',
    };
    const accent='#E07040', accent2='#5B8DEF', green='#4CAF7D', gold='#D4963A', purple='#A78BFA';

    // ── Solid background ──
    ctx.fillStyle = P.bg1;
    ctx.fillRect(0, 0, W, H);

    // ── Subtle noise ──
    ctx.globalAlpha = isDark ? 0.03 : 0.04;
    ctx.fillStyle = isDark ? '#fff' : '#000';
    for (let nx=0;nx<W;nx+=4) for (let ny=0;ny<H;ny+=4) { if(Math.random()>0.7) ctx.fillRect(nx,ny,2,2); }
    ctx.globalAlpha = 1;

    // ── Helpers ──
    function rrect(x,y,w,h,r) {
      ctx.beginPath();
      ctx.moveTo(x+r,y); ctx.lineTo(x+w-r,y); ctx.quadraticCurveTo(x+w,y,x+w,y+r);
      ctx.lineTo(x+w,y+h-r); ctx.quadraticCurveTo(x+w,y+h,x+w-r,y+h);
      ctx.lineTo(x+r,y+h); ctx.quadraticCurveTo(x,y+h,x,y+h-r);
      ctx.lineTo(x,y+r); ctx.quadraticCurveTo(x,y,x+r,y);
      ctx.closePath();
    }
    function neuCard(x,y,w,h,r) {
      ctx.shadowColor=P.shDark; ctx.shadowBlur=14; ctx.shadowOffsetX=6; ctx.shadowOffsetY=6;
      rrect(x,y,w,h,r); ctx.fillStyle=P.surface; ctx.fill();
      ctx.shadowColor=P.shLight; ctx.shadowBlur=14; ctx.shadowOffsetX=-6; ctx.shadowOffsetY=-6;
      rrect(x,y,w,h,r); ctx.fillStyle=P.surface; ctx.fill();
      ctx.shadowColor='transparent'; ctx.shadowBlur=0; ctx.shadowOffsetX=0; ctx.shadowOffsetY=0;
    }
    const FS="'DM Sans', sans-serif", FM="'DM Mono', monospace";

    // ── SVG Icon drawer ──
    function drawIcon(type,cx,cy,sz,clr) {
      ctx.save(); ctx.translate(cx,cy);
      const sc=sz/24; ctx.scale(sc,sc);
      ctx.fillStyle=clr; ctx.strokeStyle=clr;
      ctx.lineWidth=2; ctx.lineCap='round'; ctx.lineJoin='round';
      if(type==='fire'){
        ctx.beginPath();ctx.moveTo(0,-10);ctx.bezierCurveTo(4,-6,8,-2,8,4);ctx.bezierCurveTo(8,8,5,11,2,12);
        ctx.bezierCurveTo(3,10,2,7,0,6);ctx.bezierCurveTo(-2,8,-3,11,-1,12);ctx.bezierCurveTo(-5,11,-8,8,-8,4);
        ctx.bezierCurveTo(-8,-2,-4,-6,0,-10);ctx.closePath();ctx.fill();
      } else if(type==='star'){
        ctx.beginPath();for(let i=0;i<5;i++){const a1=(i*72-90)*Math.PI/180;const a2=((i*72+36)-90)*Math.PI/180;ctx.lineTo(Math.cos(a1)*10,Math.sin(a1)*10);ctx.lineTo(Math.cos(a2)*4.5,Math.sin(a2)*4.5);}ctx.closePath();ctx.fill();
      } else if(type==='check'){
        ctx.beginPath();ctx.arc(0,0,10,0,Math.PI*2);ctx.globalAlpha=0.2;ctx.fill();ctx.globalAlpha=1;
        ctx.beginPath();ctx.arc(0,0,10,0,Math.PI*2);ctx.lineWidth=2;ctx.stroke();
        ctx.beginPath();ctx.moveTo(-5,0);ctx.lineTo(-1.5,4);ctx.lineTo(5.5,-4);ctx.lineWidth=2.5;ctx.stroke();
      } else if(type==='clipboard'){
        rrect(-7,-10,14,19,2);ctx.lineWidth=1.8;ctx.stroke();rrect(-3,-12,6,4,1.5);ctx.fill();
        ctx.beginPath();ctx.moveTo(-4,0);ctx.lineTo(4,0);ctx.lineWidth=1.5;ctx.stroke();
        ctx.beginPath();ctx.moveTo(-4,4);ctx.lineTo(2,4);ctx.stroke();
      } else if(type==='trend_up'){
        ctx.beginPath();ctx.moveTo(-9,6);ctx.lineTo(-2,-1);ctx.lineTo(2,3);ctx.lineTo(9,-5);ctx.lineWidth=2.5;ctx.stroke();
        ctx.beginPath();ctx.moveTo(5,-5);ctx.lineTo(9,-5);ctx.lineTo(9,-1);ctx.lineWidth=2.5;ctx.stroke();
      } else if(type==='trophy'){
        ctx.beginPath();ctx.moveTo(-6,-8);ctx.lineTo(-5,0);ctx.bezierCurveTo(-4,5,4,5,5,0);ctx.lineTo(6,-8);ctx.closePath();ctx.fill();
        ctx.beginPath();ctx.arc(-7,-4,3,-Math.PI*0.5,Math.PI*0.5);ctx.lineWidth=1.8;ctx.stroke();
        ctx.beginPath();ctx.arc(7,-4,3,Math.PI*0.5,-Math.PI*0.5);ctx.lineWidth=1.8;ctx.stroke();
        ctx.beginPath();ctx.moveTo(0,3);ctx.lineTo(0,7);ctx.lineWidth=2;ctx.stroke();
        ctx.beginPath();ctx.moveTo(-4,7);ctx.lineTo(4,7);ctx.lineWidth=2.5;ctx.stroke();
      } else if(type==='bar_chart'){
        rrect(-8,0,4,8,1);ctx.fill();rrect(-2,-5,4,13,1);ctx.fill();rrect(4,-9,4,17,1);ctx.fill();
      } else if(type==='target'){
        ctx.beginPath();ctx.arc(0,0,10,0,Math.PI*2);ctx.lineWidth=2;ctx.stroke();
        ctx.beginPath();ctx.arc(0,0,6,0,Math.PI*2);ctx.lineWidth=2;ctx.stroke();
        ctx.beginPath();ctx.arc(0,0,2.5,0,Math.PI*2);ctx.fill();
      } else if(type==='warn'){
        ctx.beginPath();ctx.moveTo(0,-10);ctx.lineTo(-10,8);ctx.lineTo(10,8);ctx.closePath();
        ctx.globalAlpha=0.15;ctx.fill();ctx.globalAlpha=1;ctx.lineWidth=2;ctx.stroke();
        ctx.beginPath();ctx.moveTo(0,-3);ctx.lineTo(0,3);ctx.lineWidth=2.5;ctx.stroke();
        ctx.beginPath();ctx.arc(0,6,1.2,0,Math.PI*2);ctx.fill();
      }
      ctx.restore();
    }

    // ── Donut helper (Canvas) ──
    function drawDonut(cx,cy,r,pct,clr1,clr2,textClr) {
      ctx.beginPath();ctx.arc(cx,cy,r,0,Math.PI*2);
      ctx.strokeStyle=isDark?P.raised:P.bg2;ctx.lineWidth=5;ctx.stroke();
      if(pct>0){
        const startA=-Math.PI/2, endA=startA+(Math.PI*2*pct/100);
        ctx.beginPath();ctx.arc(cx,cy,r,startA,endA);
        const dg=ctx.createLinearGradient(cx-r,cy-r,cx+r,cy+r);
        dg.addColorStop(0,clr1);dg.addColorStop(1,clr2);
        ctx.strokeStyle=dg;ctx.lineWidth=5;ctx.lineCap='round';ctx.stroke();ctx.lineCap='butt';
      }
      const dFontSz = Math.max(12, Math.round(r * 0.7));
      ctx.font=`800 ${dFontSz}px ${FM}`;ctx.fillStyle=textClr;ctx.textAlign='center';
      ctx.fillText(pct+'%',cx,cy+Math.round(dFontSz/3.5));
    }

    // ── Decorative accent circles ──
    ctx.globalAlpha=isDark?0.04:0.06;
    ctx.fillStyle=accent2; ctx.beginPath();ctx.arc(900,180,250,0,Math.PI*2);ctx.fill();
    ctx.fillStyle=green; ctx.beginPath();ctx.arc(180,1500,200,0,Math.PI*2);ctx.fill();
    ctx.fillStyle=purple; ctx.beginPath();ctx.arc(850,H-400,180,0,Math.PI*2);ctx.fill();
    ctx.globalAlpha=1;

    // ── Layout ──
    let Y=50;

    // ── 1. HEADER ──
    ctx.fillStyle=P.text; ctx.font=`700 36px ${FS}`; ctx.textAlign='center';
    ctx.fillText('\u{1F331} Super Habits', W/2, Y); Y+=32;
    ctx.fillStyle=P.sub; ctx.font=`400 22px ${FS}`;
    ctx.fillText(S('stats','share_title'), W/2, Y); Y+=40;
    ctx.fillStyle=P.text; ctx.font=`800 44px ${FS}`;
    ctx.fillText(name, W/2, Y); Y+=28;
    const nowD=new Date();
    const dateStr=nowD.toLocaleDateString(currentLang==='ru'?'ru-RU':currentLang==='en'?'en-US':'uz-UZ',{day:'numeric',month:'long',year:'numeric'});
    ctx.fillStyle=P.sub; ctx.font=`400 20px ${FS}`;
    ctx.fillText(dateStr, W/2, Y); Y+=34;

    // ── 2. BUGUNGI NATIJA (keng card) ──
    const todayDone  = s.today_done  || 0;
    const todayTotal = s.today_total || 1;
    const todayPct   = todayTotal ? Math.round(todayDone / todayTotal * 100) : 0;
    const todayH = 90;
    neuCard(pad,Y,cW,todayH,16);
    drawIcon('target',pad+34,Y+todayH/2+2,20,green);
    ctx.textAlign='left'; ctx.font=`700 15px ${FS}`; ctx.fillStyle=P.sub;
    ctx.fillText(S('stats','today_momentum').toUpperCase(), pad+58, Y+30);
    const todayValTxt = todayDone + '/' + todayTotal;
    ctx.font=`900 36px ${FM}`; ctx.fillStyle=green;
    ctx.fillText(todayValTxt, pad+58, Y+66);
    const tvW=ctx.measureText(todayValTxt).width;
    ctx.font=`600 17px ${FS}`; ctx.fillStyle=P.sub;
    ctx.fillText(todayPct+'%', pad+58+tvW+12, Y+66);
    // Mini bars
    const mbX=pad+cW-180, mbY=Y+22, mbW=140, mbH=46;
    const mbCount=Math.max(todayTotal,1);
    const mbBarW=Math.min(12, (mbW-4)/mbCount);
    for(let i=0;i<mbCount;i++){
      const bx=mbX+(i*(mbBarW+2));
      const done=i<todayDone;
      const bh=done?mbH:10;
      const by=mbY+mbH-bh;
      rrect(bx,by,mbBarW,bh,3);
      ctx.fillStyle=done?green:(isDark?P.raised:P.bg2);ctx.fill();
    }
    Y+=todayH+gap;

    // ── 3. STREAK CARD (keng) ──
    const streakH = 80;
    const bestStreak = s.best_streak || s.streak || 0;
    neuCard(pad,Y,cW,streakH,16);
    drawIcon('fire',pad+34,Y+streakH/2,20,accent);
    ctx.textAlign='left'; ctx.font=`700 16px ${FS}`; ctx.fillStyle=P.sub;
    ctx.fillText(S('stats','share_streak').toUpperCase(), pad+58, Y+28);
    ctx.font=`900 36px ${FM}`; ctx.fillStyle=accent;
    ctx.fillText(String(s.streak), pad+58, Y+62);
    const skW=ctx.measureText(String(s.streak)).width;
    ctx.font=`500 17px ${FS}`; ctx.fillStyle=P.sub;
    ctx.fillText(S('stats','record_label')+': '+bestStreak, pad+58+skW+16, Y+62);
    Y+=streakH+gap;

    // ── 4. ENG ZAIF + ENG BARQAROR ODAT (2x1) ──
    const worstName = s.worst_habit_name || '';
    const worstPct  = s.worst_habit_pct  || 0;
    const worstIcon = s.worst_habit_icon || '';
    const worstColor = worstPct <= 20 ? '#E05252' : worstPct <= 40 ? '#E07040' : '#D4963A';
    const topName = s.top_habit_name || '';
    const topPct  = s.top_habit_pct  || 0;
    const topIcon = s.top_habit_icon || '';
    const habitInfoW = (cW-gap)/2, habitInfoH = 110;

    // Eng zaif
    neuCard(pad, Y, habitInfoW, habitInfoH, 16);
    drawIcon('warn', pad+30, Y+28, 18, worstColor);
    ctx.textAlign='left'; ctx.font=`600 13px ${FS}`; ctx.fillStyle=P.sub;
    ctx.fillText(S('stats','worst_habit').toUpperCase(), pad+50, Y+34);
    drawDonut(pad+habitInfoW-44, Y+habitInfoH/2+10, 20, worstPct, worstColor, '#E07040', worstColor);
    ctx.textAlign='left';
    if(worstIcon){ctx.font='26px serif';ctx.fillText(worstIcon,pad+20,Y+68);}
    ctx.font=`700 15px ${FS}`; ctx.fillStyle=P.text;
    const wNameX = worstIcon ? pad+52 : pad+20;
    const wDisplayName = worstName || S('stats','no_habits');
    ctx.font=`700 15px ${FS}`;
    let wTrunc = wDisplayName;
    while(ctx.measureText(wTrunc).width > habitInfoW-120 && wTrunc.length > 3) wTrunc = wTrunc.slice(0,-1);
    if(wTrunc !== wDisplayName) wTrunc += '...';
    ctx.fillText(wTrunc, wNameX, Y+68);
    ctx.font=`800 22px ${FM}`; ctx.fillStyle=worstColor;
    ctx.fillText(worstPct+'%', wNameX, Y+94);

    // Eng barqaror
    const topX = pad+habitInfoW+gap;
    neuCard(topX, Y, habitInfoW, habitInfoH, 16);
    drawIcon('trophy', topX+30, Y+28, 18, green);
    ctx.textAlign='left'; ctx.font=`600 13px ${FS}`; ctx.fillStyle=P.sub;
    ctx.fillText(S('stats','top_habit').toUpperCase(), topX+50, Y+34);
    drawDonut(topX+habitInfoW-44, Y+habitInfoH/2+10, 20, topPct, '#6EDAA0', '#4CAF7D', green);
    ctx.textAlign='left';
    if(topIcon){ctx.font='26px serif';ctx.fillText(topIcon,topX+20,Y+68);}
    ctx.font=`700 15px ${FS}`; ctx.fillStyle=P.text;
    const tNameX = topIcon ? topX+52 : topX+20;
    const tDisplayName = topName || S('stats','no_habits');
    ctx.font=`700 15px ${FS}`;
    let tTrunc = tDisplayName;
    while(ctx.measureText(tTrunc).width > habitInfoW-120 && tTrunc.length > 3) tTrunc = tTrunc.slice(0,-1);
    if(tTrunc !== tDisplayName) tTrunc += '...';
    ctx.fillText(tTrunc, tNameX, Y+68);
    ctx.font=`800 22px ${FM}`; ctx.fillStyle=green;
    ctx.fillText(topPct+'%', tNameX, Y+94);
    Y+=habitInfoH+gap;

    // ── 5. TREND CARD ──
    const tr=d.trend||{};
    const trendH=85;
    neuCard(pad,Y,cW,trendH,16);
    ctx.textAlign='left'; ctx.font=`700 16px ${FS}`; ctx.fillStyle=P.sub;
    drawIcon('trend_up',pad+30,Y+26,18,accent2);
    ctx.fillText(S('stats','weekly_trend').toUpperCase(), pad+50, Y+32);
    const twPct=tr.this_week||0, pwPct=tr.prev_week||0;
    const twClr=twPct>=60?green:twPct>=30?accent2:accent;
    ctx.font=`800 30px ${FM}`; ctx.fillStyle=twClr;
    ctx.fillText(twPct+'%', pad+26, Y+68);
    const twNW=ctx.measureText(twPct+'%').width;
    ctx.font=`500 16px ${FS}`; ctx.fillStyle=P.sub;
    ctx.fillText(S('stats','this_week'), pad+26+twNW+8, Y+68);
    const diff=tr.diff||0, dir=tr.direction||'same';
    const diffClr=dir==='up'?green:dir==='down'?'#E05050':accent2;
    const diffArr=dir==='up'?'\u2191':dir==='down'?'\u2193':'\u2192';
    const diffTxt=diffArr+' '+(diff>0?'+':'')+diff+'%';
    ctx.font=`800 20px ${FM}`;
    const dTW=ctx.measureText(diffTxt).width;
    const pX=pad+cW-dTW-40;
    rrect(pX-10,Y+50,dTW+20,28,10); ctx.fillStyle=diffClr+'18'; ctx.fill();
    rrect(pX-10,Y+50,dTW+20,28,10); ctx.strokeStyle=diffClr+'40'; ctx.lineWidth=1; ctx.stroke();
    ctx.fillStyle=diffClr; ctx.textAlign='left'; ctx.fillText(diffTxt,pX,Y+70);
    ctx.font=`400 14px ${FS}`; ctx.fillStyle=P.sub2; ctx.textAlign='right';
    ctx.fillText(S('stats','prev_week_pct')+': '+pwPct+'%', pad+cW-20, Y+32);
    Y+=trendH+gap;

    // ── 6. WEEKLY BAR CHART ──
    const avgPct=w.length?Math.round(w.reduce((a2,dd)=>a2+(dd.total?dd.count/dd.total*100:0),0)/w.length):0;
    const chartH2=200;
    neuCard(pad-10,Y-10,cW+20,chartH2+70,18);
    ctx.textAlign='left'; ctx.font=`700 16px ${FS}`; ctx.fillStyle=P.sub;
    ctx.fillText(S('stats','week_chart').toUpperCase(), pad+14, Y+14);
    const barGap3=14, barW3=(cW-20-barGap3*6)/7;
    const dayAbbr=S('stats','day_abbr')||['Ya','Du','Se','Ch','Pa','Ju','Sh'];
    const cTop=Y+30, cBot=Y+chartH2-10, cArea=cBot-cTop;
    ctx.globalAlpha=isDark?0.06:0.1;ctx.strokeStyle=P.sub;ctx.lineWidth=1;
    for(let gl=0;gl<=4;gl++){const gy3=cBot-(cArea*gl/4);ctx.beginPath();ctx.moveTo(pad+10,gy3);ctx.lineTo(pad+cW-10,gy3);ctx.stroke();}
    ctx.globalAlpha=1;
    w.forEach((day,i)=>{
      const pctD=day.total?Math.round(day.count/day.total*100):0;
      const bH2=Math.max(6,cArea*pctD/100);
      const bx2=pad+10+i*(barW3+barGap3);
      const by2=cBot-bH2;
      const clr2=pctD>=80?green:pctD>=40?accent2:pctD>0?accent:(isDark?'#2A2D42':'#D0D3DE');
      if(pctD>0){ctx.globalAlpha=isDark?0.15:0.08;rrect(bx2+3,by2+3,barW3,bH2,8);ctx.fillStyle=isDark?'#000':'#B8BBCA';ctx.fill();ctx.globalAlpha=1;}
      rrect(bx2,by2,barW3,bH2,8);
      const bg4=ctx.createLinearGradient(bx2,by2,bx2,by2+bH2);bg4.addColorStop(0,clr2);bg4.addColorStop(1,clr2+(isDark?'66':'88'));ctx.fillStyle=bg4;ctx.fill();
      if(pctD>0){rrect(bx2+3,by2,barW3-6,Math.min(bH2,10),6);ctx.fillStyle=isDark?'rgba(255,255,255,0.08)':'rgba(255,255,255,0.30)';ctx.fill();}
      if(pctD>0){ctx.font=`800 16px ${FM}`;ctx.fillStyle=clr2;ctx.textAlign='center';ctx.fillText(pctD+'%',bx2+barW3/2,by2-8);}
      ctx.font=`600 15px ${FS}`;ctx.fillStyle=P.sub;ctx.textAlign='center';
      ctx.fillText(dayAbbr[new Date(day.date).getDay()], bx2+barW3/2, cBot+22);
    });
    const avgLY=cBot-cArea*avgPct/100;
    ctx.setLineDash([6,4]);ctx.strokeStyle=purple+(isDark?'55':'77');ctx.lineWidth=1.5;
    ctx.beginPath();ctx.moveTo(pad+10,avgLY);ctx.lineTo(pad+cW-10,avgLY);ctx.stroke();ctx.setLineDash([]);
    const avgLbl2=avgPct+'% avg';ctx.font=`700 13px ${FM}`;
    const avgLW2=ctx.measureText(avgLbl2).width;
    rrect(pad+cW-avgLW2-36,avgLY-16,avgLW2+18,22,6);ctx.fillStyle=purple+'15';ctx.fill();
    ctx.fillStyle=purple;ctx.textAlign='right';ctx.fillText(avgLbl2,pad+cW-20,avgLY-1);
    Y+=chartH2+56;

    // ── 7. 30-KUN AREA CHART ──
    if (monthlyDays && monthlyDays.length >= 2) {
      const aW=cW, aH=150, aPadX=16, aPadY=10;
      const pcts30 = monthlyDays.map(md => md.total ? Math.round(md.count / md.total * 100) : 0);
      const maxP30 = Math.max(...pcts30, 1);
      const avg30 = Math.round(pcts30.reduce((a,b)=>a+b,0) / pcts30.length);

      neuCard(pad-10,Y-10,cW+20,aH+90,18);
      ctx.textAlign='left'; ctx.font=`700 16px ${FS}`; ctx.fillStyle=P.sub;
      ctx.fillText(S('stats','month_chart').toUpperCase(), pad+14, Y+14);
      ctx.font=`900 28px ${FM}`; ctx.fillStyle=P.text;
      const avg30Txt = avg30+'%';
      ctx.fillText(avg30Txt, pad+14, Y+44);
      const avg30W = ctx.measureText(avg30Txt).width;
      ctx.font=`400 14px ${FS}`; ctx.fillStyle=P.sub;
      ctx.fillText(S('stats','avg_30'), pad+18+avg30W, Y+44);

      const chartTop=Y+56, chartBot=chartTop+aH;
      const pts30=pcts30.map((p,i)=>({
        x: pad+aPadX+(i/(pcts30.length-1))*(aW-2*aPadX),
        y: chartTop+aPadY+(1-p/maxP30)*(aH-2*aPadY)
      }));
      // Area fill
      ctx.beginPath();ctx.moveTo(pts30[0].x,pts30[0].y);
      for(let i=1;i<pts30.length;i++){
        const cp=(pts30[i].x-pts30[i-1].x)/2.5;
        ctx.bezierCurveTo(pts30[i-1].x+cp,pts30[i-1].y,pts30[i].x-cp,pts30[i].y,pts30[i].x,pts30[i].y);
      }
      ctx.lineTo(pts30[pts30.length-1].x,chartBot);ctx.lineTo(pts30[0].x,chartBot);ctx.closePath();
      const aFill=ctx.createLinearGradient(0,chartTop,0,chartBot);
      aFill.addColorStop(0,green+'40');aFill.addColorStop(1,green+'05');
      ctx.fillStyle=aFill;ctx.fill();
      // Line
      ctx.beginPath();ctx.moveTo(pts30[0].x,pts30[0].y);
      for(let i=1;i<pts30.length;i++){
        const cp=(pts30[i].x-pts30[i-1].x)/2.5;
        ctx.bezierCurveTo(pts30[i-1].x+cp,pts30[i-1].y,pts30[i].x-cp,pts30[i].y,pts30[i].x,pts30[i].y);
      }
      const lineG30=ctx.createLinearGradient(pts30[0].x,0,pts30[pts30.length-1].x,0);
      lineG30.addColorStop(0,accent2);lineG30.addColorStop(1,green);
      ctx.strokeStyle=lineG30;ctx.lineWidth=3;ctx.stroke();
      // End dot
      const lastP=pts30[pts30.length-1];
      const lastPct30=pcts30[pcts30.length-1];
      const dotClr30=lastPct30>=80?green:lastPct30>=40?accent2:accent;
      ctx.beginPath();ctx.arc(lastP.x,lastP.y,5,0,Math.PI*2);ctx.fillStyle=dotClr30;ctx.fill();
      ctx.beginPath();ctx.arc(lastP.x,lastP.y,5,0,Math.PI*2);ctx.strokeStyle='#fff';ctx.lineWidth=2;ctx.stroke();
      ctx.font=`800 16px ${FM}`;ctx.fillStyle=dotClr30;
      ctx.textAlign=lastP.x>pad+aW-60?'end':'start';
      ctx.fillText(lastPct30+'%',lastP.x+(lastP.x>pad+aW-60?-8:8),lastP.y-12);
      // Date labels
      ctx.textAlign='center';ctx.font=`600 14px ${FS}`;ctx.fillStyle=P.sub;
      [0,9,19,29].filter(i=>i<monthlyDays.length).forEach(i=>{
        const x=pts30[i].x;
        ctx.fillText(new Date(monthlyDays[i].date).getDate()+'', x, chartBot+22);
      });
      Y+=aH+80;
    }

    // ── 8. HEATMAP (GitHub style) ──
    if (d.days_30 && d.days_30.length) {
      const hmH = 190;
      neuCard(pad-10, Y-10, cW+20, hmH+40, 18);
      ctx.textAlign='left'; ctx.font=`700 16px ${FS}`; ctx.fillStyle=P.sub;
      ctx.fillText(S('stats','heatmap_title').toUpperCase(), pad+14, Y+18);

      const monthlyMap={};
      (monthlyDays||[]).forEach(m=>{monthlyMap[m.date]=m.total?Math.round(m.count/m.total*100):0;});
      const hmDayLbls=S('stats','hm_week_days')||['Du','Se','Ch','Pa','Ju','Sh','Ya'];
      const days30=d.days_30;
      const firstDJS=new Date(days30[0]).getDay();
      const firstRow=firstDJS===0?6:firstDJS-1;

      const cellSz=22, cellGap=3;
      const gridX=pad+44, gridY=Y+36;
      // Day labels
      ctx.font=`600 13px ${FS}`; ctx.fillStyle=P.sub; ctx.textAlign='right';
      for(let r=0;r<7;r++) ctx.fillText(hmDayLbls[r], gridX-6, gridY+r*(cellSz+cellGap)+cellSz/2+3);
      // Cells
      const allCells=[...Array(firstRow).fill(null),...days30];
      allCells.forEach((dd,idx)=>{
        const row=idx%7, col=Math.floor(idx/7);
        const cx=gridX+col*(cellSz+cellGap), cy=gridY+row*(cellSz+cellGap);
        if(!dd){return;}
        const pctVal=monthlyMap[dd]||(d.heatmap&&d.heatmap[dd]?70:0);
        const lvClr=pctVal===0?(isDark?P.raised:P.bg2):pctVal<40?green+'55':pctVal<80?green+'99':green;
        rrect(cx,cy,cellSz,cellSz,4);ctx.fillStyle=lvClr;ctx.fill();
        if(dd===d.today){ctx.strokeStyle=accent2;ctx.lineWidth=1.5;rrect(cx,cy,cellSz,cellSz,4);ctx.stroke();}
      });
      // Legend (grid o'ng tomonida, vertical)
      const maxCol = Math.ceil(allCells.length / 7);
      const legX = gridX + maxCol*(cellSz+cellGap) + 30;
      ctx.textAlign='left';
      const legColors=[isDark?P.raised:P.bg2, green+'55', green+'99', green];
      const legLabels=[S('stats','hm_not_done'),S('stats','hm_partial'),'',S('stats','hm_full')];
      let legItemY = gridY + 10;
      legColors.forEach((lc,li)=>{
        if(!legLabels[li]) return;
        rrect(legX, legItemY, 10, 10, 2); ctx.fillStyle=lc; ctx.fill();
        ctx.font=`500 11px ${FS}`; ctx.fillStyle=P.sub;
        ctx.fillText(legLabels[li], legX+16, legItemY+9);
        legItemY += 22;
      });
      Y+=hmH+40;
    }

    // ── DIVIDER ──
    Y+=14;
    const divGrad2=ctx.createLinearGradient(240,0,W-240,0);
    divGrad2.addColorStop(0,P.sub+'00');divGrad2.addColorStop(0.5,P.sub+'40');divGrad2.addColorStop(1,P.sub+'00');
    ctx.strokeStyle=divGrad2;ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(240,Y);ctx.lineTo(W-240,Y);ctx.stroke();

    // ── FOOTER ──
    const footerY = Y+40;
    ctx.textAlign='center';
    ctx.font=`400 20px ${FS}`;ctx.fillStyle=P.sub2;
    ctx.fillText(S('stats','share_footer'), W/2, footerY);
    ctx.font=`700 24px ${FS}`;
    const fGrad=ctx.createLinearGradient(W/2-140,0,W/2+140,0);
    fGrad.addColorStop(0,accent2);fGrad.addColorStop(1,purple);
    ctx.fillStyle=fGrad;
    ctx.fillText('@Super_habits_bot', W/2, footerY+34);

    // ── Canvas balandligini kerakli joyga trim qilish ──
    const finalH = footerY + 80;
    if (finalH < H) {
      const trimmed = document.createElement('canvas');
      trimmed.width = W; trimmed.height = finalH;
      const tCtx = trimmed.getContext('2d');
      tCtx.drawImage(canvas, 0, 0);
      canvas.width = W; canvas.height = finalH;
      ctx.drawImage(trimmed, 0, 0);
    }

    // ── Telegram chatga yuborish ──
    await new Promise((resolve) => {
      canvas.toBlob(async function(blob) {
        if (!blob) { resolve(); return; }
        try {
          const formData = new FormData();
          formData.append('photo', blob, 'weekly.png');
          const res = await fetch(`${API}/share-card/${userId}`, {
            method: 'POST',
            headers: { 'X-Init-Data': initData, 'X-User-Id': String(userId) },
            body: formData
          });
          const r = await res.json();
          if (r.ok) {
            if (window.Telegram?.WebApp?.close) window.Telegram.WebApp.close();
          }
        } catch(se) {
          console.warn('Share error:', se);
        }
        resolve();
      }, 'image/png');
    });

  } catch(e) {
    console.warn('Share card error:', e);
  } finally {
    if (btn) { btn.disabled = false; btn.innerHTML = _btnOrigHTML; }
  }
}

// ── REYTING ──
// ── REYTING STATE ──
let _ratSort   = 'points';
let _ratPeriod = 'week';

async function loadRating() {
  try {
    const d = await apiFetch(`rating?sort=${_ratSort}&period=${_ratPeriod}&uid=${userId}`);
    data.rating = d;
    renderRating(d);
  } catch(e) {
    document.getElementById('rating-content').innerHTML =
      `<div class="empty-state"><div class="icon"><svg width="28" height="28" viewBox="0 0 24 24" fill="none"><defs><linearGradient id="svgWarn" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#F6C93E"/><stop offset="100%" stop-color="#E07040"/></linearGradient></defs><path d="M12 3L2 21h20L12 3z" stroke="url(#svgWarn)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/><path d="M12 10v5M12 17.5v.5" stroke="url(#svgWarn)" stroke-width="2" stroke-linecap="round"/></svg></div>${S('msg','data_error')}.</div>`;
  }
}

function setRatSort(s)   { _ratSort   = s; loadRating(); }
function setRatPeriod(p) { _ratPeriod = p; loadRating(); }

function userAvatarHTML(u, size = 32) {
  const initial = (u.name || '?')[0].toUpperCase();
  const clickStyle = u.is_me ? 'cursor:pointer;' : '';
  const clickAttr  = u.is_me ? " onclick=\"switchTab('profile',document.getElementById('nav-profile'))\"" : '';
  if (u.photo_url) {
    return `<img src="${u.photo_url}"${clickAttr} style="${clickStyle}width:${size}px;height:${size}px;border-radius:50%;object-fit:cover;flex-shrink:0"
      onerror="this.outerHTML='<div style=\\'${clickStyle}width:${size}px;height:${size}px;border-radius:50%;background:var(--bg);box-shadow:var(--sh-sm);display:flex;align-items:center;justify-content:center;font-size:${Math.round(size*0.4)}px;font-weight:700;color:var(--text);flex-shrink:0\\'>${initial}</div>'">`;
  }
  return `<div${clickAttr} style="${clickStyle}width:${size}px;height:${size}px;border-radius:50%;background:var(--bg);box-shadow:var(--sh-sm);
    display:flex;align-items:center;justify-content:center;font-size:${Math.round(size*0.4)}px;font-weight:700;color:var(--text);flex-shrink:0">${initial}</div>`;
}

function renderRating(d) {
  const { today, days, day_labels: lbls, users, caller_entry, total_users, sort_by, period } = d;
  const maxScore  = users.length ? Math.max(...users.map(u => u.score), 1) : 1;
  const maxPoints = users.length ? Math.max(...users.map(u => u.points), 1) : 1;
  const maxStreak = users.length ? Math.max(...users.map(u => u.streak), 1) : 1;
  function calcPct(u) {
    if (sort_by === 'points') return Math.round((u.points / maxPoints) * 100);
    if (sort_by === 'streak') return Math.round((u.streak / maxStreak) * 100);
    return Math.round((u.score / maxScore) * 100);
  }

  const medals = [
    `<svg width="28" height="32" viewBox="0 0 28 32" fill="none" xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="mgRib1a" x1="0" y1="0" x2="28" y2="8" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#F6C94E"/><stop offset="100%" stop-color="#E8A020"/></linearGradient><linearGradient id="mgGold" x1="0" y1="14" x2="28" y2="32" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#FFE566"/><stop offset="100%" stop-color="#C8820A"/></linearGradient><linearGradient id="mgGoldS" x1="4" y1="16" x2="24" y2="30" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#FFF0A0"/><stop offset="100%" stop-color="#E8A020"/></linearGradient></defs><rect x="9" y="0" width="5" height="14" rx="2" fill="url(#mgRib1a)" transform="rotate(-15 9 0)"/><rect x="14" y="0" width="5" height="14" rx="2" fill="#E8A020" transform="rotate(15 18 0)"/><circle cx="14" cy="22" r="9" fill="url(#mgGold)"/><circle cx="14" cy="22" r="7" fill="url(#mgGoldS)"/><text x="14" y="27" text-anchor="middle" font-size="9" font-weight="800" fill="#7A4A00" font-family="sans-serif">1</text></svg>`,
    `<svg width="28" height="32" viewBox="0 0 28 32" fill="none" xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="mgRib2a" x1="0" y1="0" x2="28" y2="8" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#C8D0E0"/><stop offset="100%" stop-color="#8898B0"/></linearGradient><linearGradient id="mgSilv" x1="0" y1="14" x2="28" y2="32" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#E8EEF8"/><stop offset="100%" stop-color="#8898B0"/></linearGradient><linearGradient id="mgSilvS" x1="4" y1="16" x2="24" y2="30" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#F4F8FF"/><stop offset="100%" stop-color="#A0B0C8"/></linearGradient></defs><rect x="9" y="0" width="5" height="14" rx="2" fill="url(#mgRib2a)" transform="rotate(-15 9 0)"/><rect x="14" y="0" width="5" height="14" rx="2" fill="#8898B0" transform="rotate(15 18 0)"/><circle cx="14" cy="22" r="9" fill="url(#mgSilv)"/><circle cx="14" cy="22" r="7" fill="url(#mgSilvS)"/><text x="14" y="27" text-anchor="middle" font-size="9" font-weight="800" fill="#445566" font-family="sans-serif">2</text></svg>`,
    `<svg width="28" height="32" viewBox="0 0 28 32" fill="none" xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="mgRib3a" x1="0" y1="0" x2="28" y2="8" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#D4956A"/><stop offset="100%" stop-color="#8B4513"/></linearGradient><linearGradient id="mgBronz" x1="0" y1="14" x2="28" y2="32" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#E8A87C"/><stop offset="100%" stop-color="#7A3A10"/></linearGradient><linearGradient id="mgBronzS" x1="4" y1="16" x2="24" y2="30" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#F4C8A0"/><stop offset="100%" stop-color="#A0522D"/></linearGradient></defs><rect x="9" y="0" width="5" height="14" rx="2" fill="url(#mgRib3a)" transform="rotate(-15 9 0)"/><rect x="14" y="0" width="5" height="14" rx="2" fill="#8B4513" transform="rotate(15 18 0)"/><circle cx="14" cy="22" r="9" fill="url(#mgBronz)"/><circle cx="14" cy="22" r="7" fill="url(#mgBronzS)"/><text x="14" y="27" text-anchor="middle" font-size="9" font-weight="800" fill="#4A1A00" font-family="sans-serif">3</text></svg>`
  ];
  const podiumColors = ['#D4963A','#9AA0B0','#C08A40'];

  // ── Podium (top 3) ──
  const top3 = users.slice(0, 3);
  const podiumOrder = [1, 0, 2]; // 2nd, 1st, 3rd visually
  let podiumHtml = '<div style="display:flex;align-items:flex-end;justify-content:center;gap:8px;padding:20px 8px 8px">';
  podiumOrder.forEach(idx => {
    const u = top3[idx];
    if (!u) return;
    const h  = idx === 0 ? 90 : idx === 1 ? 70 : 56;
    const col = podiumColors[idx];
    const isMe = u.is_me;
    podiumHtml += `
      <div style="flex:1;max-width:110px;text-align:center">
        <div style="display:flex;justify-content:center;margin-bottom:6px;position:relative">
          ${userAvatarHTML(u, idx===0?48:38)}
          <span style="position:absolute;bottom:-8px;right:calc(50% - ${idx===0?40:32}px)">${u.pet || medals[idx]}</span>
        </div>
        <div style="font-size:${idx===0?'13px':'11px'};font-weight:700;color:${isMe?'#5B8DEF':'var(--text)'};margin-bottom:2px">${u.name.split(' ')[0]}</div>
        ${u.badge ? `<div style="font-size:10px">${u.badge}</div>` : ''}
        <div style="font-size:10px;color:${col};font-weight:700;margin-bottom:6px">
          ${sort_by==='points'?u.points+' ⭐':sort_by==='streak'?u.streak+'&nbsp;' + `<svg width="13" height="13" viewBox="0 0 20 20" fill="none" style="display:inline;vertical-align:middle"><defs><linearGradient id="svgFireX" x1="10" y1="0" x2="10" y2="20" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#F6C93E"/><stop offset="100%" stop-color="#E07040"/></linearGradient></defs><path d="M10 2C10 2 14 6 14 10C14 12 13 13.5 11.5 14.5C12 13 11.5 11.5 10.5 11C11 13 9.5 15 8 15.5C9 14 8.5 12 7 11C5.5 12.5 6 15 7 16.5C5.5 15.5 4 13.5 4 11C4 7 8 4 10 2Z" fill="url(#svgFireX)"/></svg>`:u.score+' '+S('profile','kun')}
        </div>
        <div style="height:${h}px;background:linear-gradient(180deg,${col}44,${col}22);
          border-radius:10px 10px 0 0;border:2px solid ${col}44;
          display:flex;flex-direction:column;align-items:center;justify-content:flex-end;padding-bottom:6px;gap:3px">
          <div style="display:flex;align-items:center;gap:3px;flex-wrap:wrap;justify-content:center">
            ${u.habits_count ? `<div style="font-size:8px;font-weight:700;color:${col};background:${col}22;border-radius:4px;padding:1px 4px;white-space:nowrap"><svg width="9" height="9" viewBox="0 0 24 24" fill="none" style="display:inline;vertical-align:middle"><rect x="8" y="2" width="8" height="4" rx="1" stroke="${col}" stroke-width="2"/><rect x="4" y="4" width="16" height="18" rx="2" stroke="${col}" stroke-width="2"/><path d="M8 11h8M8 15h5" stroke="${col}" stroke-width="2" stroke-linecap="round"/></svg> ${u.habits_count}</div>` : ''}
            ${(j=>{const e=j>=80?'❤️':j>=50?'🧡':j>=20?'💛':'🖤';return `<div style="font-size:8px;font-weight:700;color:${col};background:${col}22;border-radius:4px;padding:1px 4px;white-space:nowrap">${e} ${j}%</div>`;})(u.jon??100)}
          </div>
          ${u.active_items ? `<div class="rat-podium-inv" style="font-size:9px;width:100%;padding:0 2px;margin-top:2px"><div>${u.active_items}</div></div>` : ''}
          <div style="font-size:16px;font-weight:800;color:${col}">${idx+1}</div>
        </div>
      </div>`;
  });
  podiumHtml += '</div>';

  // ── 4–10 qator ──
  let rowsHtml = '';
  users.slice(3).forEach((u, i) => {
    const rank   = i + 4;
    const pct    = calcPct(u);
    const isMe   = u.is_me;
    const subLbl = sort_by==='points'?u.points+' ⭐':sort_by==='streak'?u.streak+'&nbsp;' + `<svg width="13" height="13" viewBox="0 0 20 20" fill="none" style="display:inline;vertical-align:middle"><defs><linearGradient id="svgFireX" x1="10" y1="0" x2="10" y2="20" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#F6C93E"/><stop offset="100%" stop-color="#E07040"/></linearGradient></defs><path d="M10 2C10 2 14 6 14 10C14 12 13 13.5 11.5 14.5C12 13 11.5 11.5 10.5 11C11 13 9.5 15 8 15.5C9 14 8.5 12 7 11C5.5 12.5 6 15 7 16.5C5.5 15.5 4 13.5 4 11C4 7 8 4 10 2Z" fill="url(#svgFireX)"/></svg>`:u.score+' '+S('profile','kun');
    rowsHtml += `
      <div style="display:flex;align-items:center;gap:10px;padding:10px 14px;
        border-radius:14px;margin-bottom:4px;background:var(--bg);
        box-shadow:${isMe?'0 0 0 2px #5B8DEF':'var(--sh-sm)'}">
        <div style="width:24px;height:24px;border-radius:50%;background:linear-gradient(135deg,#8BA7D6,#A0B4D8);display:flex;align-items:center;justify-content:center;flex-shrink:0;box-shadow:2px 2px 5px #B8BBCA,-2px -2px 5px #fff"><span style="font-size:10px;font-weight:800;color:#fff">${rank}</span></div>
        ${userAvatarHTML(u, 34)}
        <div style="flex:1;min-width:0">
          <div style="display:flex;align-items:center;gap:5px">
            <div style="font-size:13px;font-weight:700;color:${isMe?'#5B8DEF':'var(--text)'};white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex:1">${u.name}${u.badge?' '+u.badge:''}</div>
            ${u.habits_count ? `<div style="flex-shrink:0;font-size:9px;font-weight:700;color:#4CAF7D;background:#4CAF7D18;border-radius:6px;padding:2px 5px;white-space:nowrap"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" style="display:inline;vertical-align:middle"><defs><linearGradient id=\"svgClipRat\" x1=\"0\" y1=\"0\" x2=\"24\" y2=\"24\" gradientUnits=\"userSpaceOnUse\"><stop offset=\"0%\" stop-color=\"#4CAF7D\"/><stop offset=\"100%\" stop-color=\"#5B8DEF\"/></linearGradient></defs><rect x=\"8\" y=\"2\" width=\"8\" height=\"4\" rx=\"1\" fill=\"url(#svgClipRat)\"/><rect x=\"4\" y=\"4\" width=\"16\" height=\"18\" rx=\"2\" fill=\"url(#svgClipRat)\" opacity=\"0.15\"/><rect x=\"4\" y=\"4\" width=\"16\" height=\"18\" rx=\"2\" stroke=\"url(#svgClipRat)\" stroke-width=\"1.5\"/><path d=\"M8 11h8M8 15h5\" stroke=\"url(#svgClipRat)\" stroke-width=\"1.5\" stroke-linecap=\"round\"/></svg> ${u.habits_count}</div>` : ''}
            ${(j=>{const e=j>=80?"❤️":j>=50?"🧡":j>=20?"💛":"🖤";return `<div style="flex-shrink:0;font-size:9px;font-weight:700;color:var(--sub);background:var(--bg);box-shadow:var(--sh-in);border-radius:6px;padding:2px 5px;white-space:nowrap">${e} ${j}%</div>`;})(u.jon??100)}
          </div>
          ${u.active_items ? `<div class="rat-inv-scroll" style="font-size:11px;margin-top:4px"><div style="background:#A78BFA18;border-radius:6px;padding:2px 5px">${u.active_items}</div></div>` : ''}
          <div style="height:4px;border-radius:2px;background:var(--bg);box-shadow:var(--sh-in);margin-top:5px;overflow:hidden">
            <div style="height:100%;border-radius:2px;background:#5B8DEF;width:${pct}%;transition:width .4s"></div>
          </div>
        </div>
        <div style="font-size:12px;font-weight:700;color:var(--sub);text-align:right">${subLbl}</div>
      </div>`;
  });

  // ── O'zim (top10 dan tashqarida) ──
  let myRowHtml = '';
  if (caller_entry) {
    const u   = caller_entry;
    const pct = calcPct(u);
    const sub = sort_by==='points'?u.points+' ⭐':sort_by==='streak'?u.streak+'&nbsp;' + `<svg width="13" height="13" viewBox="0 0 20 20" fill="none" style="display:inline;vertical-align:middle"><defs><linearGradient id="svgFireX" x1="10" y1="0" x2="10" y2="20" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#F6C93E"/><stop offset="100%" stop-color="#E07040"/></linearGradient></defs><path d="M10 2C10 2 14 6 14 10C14 12 13 13.5 11.5 14.5C12 13 11.5 11.5 10.5 11C11 13 9.5 15 8 15.5C9 14 8.5 12 7 11C5.5 12.5 6 15 7 16.5C5.5 15.5 4 13.5 4 11C4 7 8 4 10 2Z" fill="url(#svgFireX)"/></svg>`:u.score+' '+S('profile','kun');
    myRowHtml = `
      <div style="margin-top:4px;border-top:1px solid var(--bg);padding-top:8px">
        <div style="font-size:10px;color:var(--sub);margin-bottom:4px;padding-left:4px">${S('rating','my_rank')}</div>
        <div style="display:flex;align-items:center;gap:10px;padding:10px 14px;
          border-radius:14px;background:var(--bg);box-shadow:0 0 0 2px #5B8DEF">
          <div style="width:24px;height:24px;border-radius:50%;background:linear-gradient(135deg,#5B8DEF,#4CAF7D);display:flex;align-items:center;justify-content:center;flex-shrink:0;box-shadow:0 0 0 2px #5B8DEF44"><span style="font-size:10px;font-weight:800;color:#fff">${u.rank}</span></div>
          ${userAvatarHTML(u, 34)}
          <div style="flex:1;min-width:0">
            <div style="display:flex;align-items:center;gap:5px">
              <div style="font-size:13px;font-weight:700;color:#5B8DEF;flex:1">${u.name}</div>
              ${u.habits_count ? `<div style="flex-shrink:0;font-size:9px;font-weight:700;color:#4CAF7D;background:#4CAF7D18;border-radius:6px;padding:2px 5px;white-space:nowrap"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" style="display:inline;vertical-align:middle"><defs><linearGradient id=\"svgClipRat\" x1=\"0\" y1=\"0\" x2=\"24\" y2=\"24\" gradientUnits=\"userSpaceOnUse\"><stop offset=\"0%\" stop-color=\"#4CAF7D\"/><stop offset=\"100%\" stop-color=\"#5B8DEF\"/></linearGradient></defs><rect x=\"8\" y=\"2\" width=\"8\" height=\"4\" rx=\"1\" fill=\"url(#svgClipRat)\"/><rect x=\"4\" y=\"4\" width=\"16\" height=\"18\" rx=\"2\" fill=\"url(#svgClipRat)\" opacity=\"0.15\"/><rect x=\"4\" y=\"4\" width=\"16\" height=\"18\" rx=\"2\" stroke=\"url(#svgClipRat)\" stroke-width=\"1.5\"/><path d=\"M8 11h8M8 15h5\" stroke=\"url(#svgClipRat)\" stroke-width=\"1.5\" stroke-linecap=\"round\"/></svg> ${u.habits_count}</div>` : ''}
              ${(j=>{const e=j>=80?"❤️":j>=50?"🧡":j>=20?"💛":"🖤";return `<div style="flex-shrink:0;font-size:9px;font-weight:700;color:var(--sub);background:var(--bg);box-shadow:var(--sh-in);border-radius:6px;padding:2px 5px;white-space:nowrap">${e} ${j}%</div>`;})(u.jon??100)}
            </div>
            ${u.active_items ? `<div class="rat-inv-scroll" style="font-size:11px;margin-top:4px"><div style="background:#A78BFA18;border-radius:6px;padding:2px 5px">${u.active_items}</div></div>` : ''}
            <div style="height:4px;border-radius:2px;background:var(--bg);box-shadow:var(--sh-in);margin-top:5px;overflow:hidden">
              <div style="height:100%;border-radius:2px;background:#5B8DEF;width:${pct}%"></div>
            </div>
          </div>
          <div style="font-size:12px;font-weight:700;color:#5B8DEF">${sub}</div>
        </div>
      </div>`;
  }

  // ── Sort va Period switch ──
  const sorts   = [['points',S('rating','sort_points')],['streak','<svg width="14" height="14" viewBox="0 0 20 20" fill="none" style="display:inline;vertical-align:middle;margin-right:4px"><defs><linearGradient id="gPFire" x1="0" y1="0" x2="20" y2="20" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#F6C93E"/><stop offset="100%" stop-color="#E07040"/></linearGradient></defs><path d="M10 2C10 2 14 6 14 10C14 12 13 13.5 11.5 14.5C12 13 11.5 11.5 10.5 11C11 13 9.5 15 8 15.5C9 14 8.5 12 7 11C5.5 12.5 6 15 7 16.5C5.5 15.5 4 13.5 4 11C4 7 8 4 10 2Z" fill="url(#gPFire)"/></svg>'+S('rating','sort_streak')],['active','<svg width="14" height="14" viewBox="0 0 24 24" fill="none" style="display:inline;vertical-align:middle;margin-right:4px"><defs><linearGradient id="gPCal" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#5B8DEF"/><stop offset="100%" stop-color="#4CAF7D"/></linearGradient></defs><rect x="3" y="5" width="18" height="16" rx="3" stroke="url(#gPCal)" stroke-width="2"/><path d="M3 10h18M8 3v4M16 3v4" stroke="url(#gPCal)" stroke-width="2" stroke-linecap="round"/></svg>'+S('rating','sort_active')]];
  const periods = [['week',S('rating','period_week')],['month',S('rating','period_month')],['all',S('rating','period_all')]];
  const sortBtns = sorts.map(([k,l]) =>
    `<button onclick="setRatSort('${k}')" type="button"
      style="flex:1;padding:7px 4px;border:none;cursor:pointer;font-size:11px;font-weight:${sort_by===k?'700':'500'};
        background:${sort_by===k?'var(--bg)':'transparent'};
        box-shadow:${sort_by===k?'var(--sh-sm)':'none'};
        border-radius:10px;color:${sort_by===k?'var(--text)':'var(--sub)'};
        transition:all .2s;white-space:nowrap">${l}</button>`).join('');
  const perBtns = periods.map(([k,l]) =>
    `<button onclick="setRatPeriod('${k}')" type="button"
      style="flex:1;padding:7px 4px;border:none;cursor:pointer;font-size:11px;font-weight:${period===k?'700':'500'};
        background:${period===k?'var(--bg)':'transparent'};
        box-shadow:${period===k?'var(--sh-sm)':'none'};
        border-radius:10px;color:${period===k?'var(--text)':'var(--sub)'};
        transition:all .2s;white-space:nowrap">${l}</button>`).join('');

  document.getElementById('rating-content').innerHTML = `
    <div style="display:flex;align-items:center;gap:6px;background:var(--bg);border-radius:14px;
      box-shadow:var(--sh-in);padding:4px;margin-bottom:8px">
      ${sortBtns}
      <div style="width:1px;height:20px;background:var(--sub);opacity:.2;flex-shrink:0"></div>
      ${perBtns}
    </div>
    <div style="font-size:10px;color:var(--sub);text-align:right;margin-bottom:4px">
      ${S('rating','total_users').replace('{n}', total_users)}
    </div>
    ${users.length >= 3 ? podiumHtml : ''}
    ${rowsHtml}
    ${myRowHtml}`;
}

