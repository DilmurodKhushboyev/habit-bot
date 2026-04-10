// ── PROFIL ──
async function loadProfile() {
  try {
    const d = await apiFetch(`profile/${userId}`);
    // photo_url ni DB ga saqlaymiz (Telegram WebApp orqali)
    const photoUrl = user.photo_url || '';
    if (photoUrl && !d.photo_url) {
      fetch(`${API}/profile/${userId}`, {
        method: 'PUT',
        headers: {'Content-Type':'application/json','X-Init-Data':initData,'X-User-Id':userId},
        body: JSON.stringify({ photo_url: photoUrl })
      }).catch(() => {});
    }
    renderProfile(d);
  } catch(e) {
    document.getElementById('profile-content').innerHTML =
      `<div class="empty-state"><div class="icon"><svg width="28" height="28" viewBox="0 0 24 24" fill="none"><defs><linearGradient id="svgWarn" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#F6C93E"/><stop offset="100%" stop-color="#E07040"/></linearGradient></defs><path d="M12 3L2 21h20L12 3z" stroke="url(#svgWarn)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/><path d="M12 10v5M12 17.5v.5" stroke="url(#svgWarn)" stroke-width="2" stroke-linecap="round"/></svg></div>${S('msg','data_error')}.</div>`;
  }
}

function renderProfile(d) {
  data.profile = d;
  const jon = d.jon ?? 100;
  const jonColor = jon >= 70 ? '#4CAF7D' : jon >= 40 ? '#D4963A' : '#E05050';
  const initial = (d.name || '?')[0].toUpperCase();
  const lang = d.lang || 'uz';
  currentLang = lang;
  localStorage.setItem('sh_lang', lang);
  updateNavLabels();
  const photoUrl = d.photo_url || user.photo_url || '';

  // Avatar: rasm yoki harf
  const avatarHtml = photoUrl
    ? `<img src="${photoUrl}" style="width:56px;height:56px;border-radius:50%;object-fit:cover;box-shadow:var(--sh-sm)" onerror="this.outerHTML='<div class=\\'avatar\\'>${initial}</div>'">`
    : `<div class="avatar">${initial}</div>`;

  // Qo'shilgan sana
  const joinedStr = d.joined_at ? (() => {
    const months = S('profile','month_abbr') || ['','Yan','Fev','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    const p = d.joined_at.split('-');
    return p[2] + ' ' + (months[+p[1]] || p[1]) + ' ' + p[0];
  })() : '—';

  const rankTxt = d.rank ? `#${d.rank} / ${d.total_users || '?'}` : '';
  const vipBadge = d.is_vip
    ? '<span style="background:#5B8DEF22;color:#5B8DEF;border-radius:8px;padding:2px 8px;font-size:11px;font-weight:700;margin-left:6px"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" style="display:inline;vertical-align:middle;margin-right:3px"><defs><linearGradient id="svgVip" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#5B8DEF"/><stop offset="100%" stop-color="#A78BFA"/></linearGradient></defs><path d="M12 2l1.8 5.5H20l-4.9 3.6 1.8 5.5L12 13l-4.9 3.6 1.8-5.5L4 7.5h6.2z" fill="url(#svgVip)"/></svg> VIP</span>'
    : '';

  // ── VAQTINCHA O'CHIRILGAN: Premium badge (Free/Premium yozuvi) ──
  // Bot mukammal darajaga yetgandan keyin qayta yoqiladi.
  const premiumBadge = '';

  // Yutuqlar progress
  const achPct = d.total_ach ? Math.round(d.earned_ach / d.total_ach * 100) : 0;
  const achColor = achPct >= 80 ? '#4CAF7D' : achPct >= 40 ? '#5B8DEF' : '#E07040';

  // Til tugmalari
  const langBtns = [
    {id:'uz', label:"🇺🇿 O'zbek"},
    {id:'ru', label:'🇷🇺 Русский'},
    {id:'en', label:'🇬🇧 English'},
  ].map(l => `<button class="rep-btn ${lang===l.id?'active':''}" id="lang-${l.id}" onclick="setLang('${l.id}')" type="button">${l.label}</button>`).join('');

  document.getElementById('profile-content').innerHTML = `
    <!-- Profil karta -->
    <div class="profile-card">
      <div class="profile-top">
        ${avatarHtml}
        <div style="flex:1;min-width:0">
          <div class="profile-name">${d.display_name || d.name || S('msg','default_user')}${vipBadge}${premiumBadge}${d.active_badge ? ' <span title="Badge">'+d.active_badge+'</span>' : ''}</div>
          <div style="font-size:11px;color:var(--sub);margin-top:2px"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" style="display:inline;vertical-align:middle;margin-right:3px"><defs><linearGradient id="gTrophy" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#F6C93E"/><stop offset="100%" stop-color="#E07040"/></linearGradient></defs><path d="M8 21h8M12 17v4M5 3h14v8a7 7 0 01-14 0V3z" stroke="url(#gTrophy)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/><path d="M5 6H2v3a3 3 0 003 3M19 6h3v3a3 3 0 01-3 3" stroke="url(#gTrophy)" stroke-width="2" stroke-linecap="round" fill="none"/></svg>${rankTxt} ${S('msg','rank_position')}</div>
          <div style="font-size:10px;color:var(--sub);margin-top:2px"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" style="display:inline;vertical-align:middle;margin-right:3px"><defs><linearGradient id="gCalSm" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#5B8DEF"/><stop offset="100%" stop-color="#4CAF7D"/></linearGradient></defs><rect x="3" y="5" width="18" height="16" rx="3" stroke="url(#gCalSm)" stroke-width="2"/><path d="M3 10h18M8 3v4M16 3v4" stroke="url(#gCalSm)" stroke-width="2" stroke-linecap="round"/></svg>${joinedStr} ${S('msg','since_date')}</div>
        </div>
        ${d.active_pet ? `<div style="font-size:36px;line-height:1" title="Pet">${d.active_pet}</div>` : ''}
      </div>

      ${d.items_count > 0 ? `
      <div class="profile-chips">
        <div class="profile-chip" style="cursor:pointer" onclick="openUserInventory(${JSON.stringify(d.display_name || d.name || '').replace(/"/g,'&quot;')}, ${JSON.stringify(d.items_list || []).replace(/"/g,'&quot;')})">
          <span style="font-size:14px">🎒</span>
          <span class="profile-chip-accent" style="color:#A78BFA">${d.items_count} ${S('inventory','badge_label')}</span>
        </div>
      </div>` : ''}

      ${d.bio
        ? `<div class="profile-bio">${d.bio.replace(/</g,'&lt;').replace(/>/g,'&gt;')}</div>`
        : `<div class="profile-bio-empty" onclick="openEditProfile()">
             <div class="profile-bio-empty-icon">✨</div>
             <div class="profile-bio-empty-text">
               <div class="profile-bio-empty-title">${S('profile','bio_empty_title')}</div>
               <div class="profile-bio-empty-hint">${S('profile','bio_empty_hint')}</div>
             </div>
             <div class="profile-bio-empty-arrow">›</div>
           </div>`}

      <div class="profile-bar-row">
        <span class="profile-bar-label"><svg width="14" height="14" viewBox="0 0 20 20" fill="none" style="display:inline;vertical-align:middle;margin-right:2px"><defs><linearGradient id="svgHeart" x1="0" y1="0" x2="20" y2="20" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#FF6B8A"/><stop offset="100%" stop-color="#E07040"/></linearGradient></defs><path d="M10 17C10 17 2 12 2 6.5A4.5 4.5 0 0110 4a4.5 4.5 0 018 2.5C18 12 10 17 10 17z" fill="url(#svgHeart)"/></svg> ${S('profile','jon_label')}</span>
        <span class="profile-bar-value" style="color:${jonColor}">${jon}%</span>
      </div>
      <div class="jon-bar-bg"><div class="jon-bar-fill" style="width:${jon}%;background:${jonColor}"></div></div>

      ${d.total_ach ? `
      <div class="profile-bar-row">
        <span class="profile-bar-label"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" style="display:inline;vertical-align:middle;margin-right:2px"><defs><linearGradient id="svgAchT" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#F6C93E"/><stop offset="100%" stop-color="#E07040"/></linearGradient></defs><path d="M12 2l1.8 5.5H20l-4.9 3.6 1.8 5.5L12 13l-4.9 3.6 1.8-5.5L4 7.5h6.2z" fill="url(#svgAchT)"/></svg> ${S('profile','achievements')}</span>
        <span class="profile-bar-value" style="color:${achColor}">${d.earned_ach}/${d.total_ach} (${achPct}%)</span>
      </div>
      <div class="jon-bar-bg"><div class="jon-bar-fill" style="width:${achPct}%;background:${achColor}"></div></div>
      ` : ''}
    </div>

    <!-- Do'st taklif qilish — MODAL (shop-modal pattern ishlatilgan) -->
    <div class="shop-modal-overlay" id="ref-modal" onclick="if(event.target===this)closeReferralModal()">
      <div class="shop-modal-box" style="max-width:340px;text-align:left">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px">
          <div style="display:flex;align-items:center;gap:8px">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none"><defs><linearGradient id="svgRefMd" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#4CAF7D"/><stop offset="100%" stop-color="#5B8DEF"/></linearGradient></defs><circle cx="9" cy="7" r="3.5" fill="url(#svgRefMd)" opacity="0.85"/><circle cx="16.5" cy="7.5" r="2.8" fill="url(#svgRefMd)" opacity="0.6"/><path d="M1.5 20c0-3.5 3-6.5 7.5-6.5s7.5 3 7.5 6.5" stroke="url(#svgRefMd)" stroke-width="2" stroke-linecap="round" fill="none"/><path d="M17 14c2.5.5 5 2.5 5 5" stroke="url(#svgRefMd)" stroke-width="1.8" stroke-linecap="round" fill="none" opacity="0.6"/></svg>
            <div style="font-size:16px;font-weight:700;color:var(--text)">${S('msg','ref_title')}</div>
          </div>
          <button onclick="closeReferralModal()" type="button" style="background:none;border:none;color:var(--sub);cursor:pointer;padding:4px"><svg width="16" height="16" viewBox="0 0 24 24" fill="none"><line x1="18" y1="6" x2="6" y2="18" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/><line x1="6" y1="6" x2="18" y2="18" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/></svg></button>
        </div>

        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">
          <div>
            <div style="font-size:13px;font-weight:700;color:var(--text)">${S('msg','ref_count').replace('{n}', d.ref_count || 0)}</div>
            <div style="font-size:11px;color:var(--sub);margin-top:2px">${S('msg','ref_reward')}</div>
          </div>
          <div style="text-align:right">
            <div style="font-size:20px;font-weight:700;color:var(--green);font-family:'DM Mono',monospace">+${(d.ref_count || 0) * 50}</div>
            <div style="font-size:9px;color:var(--sub)">${S('msg','ref_total_pts')}</div>
          </div>
        </div>

        ${(function() {
          var svgShield = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" style="display:inline;vertical-align:middle"><defs><linearGradient id="svgMsS2" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#5B8DEF"/><stop offset="100%" stop-color="#A78BFA"/></linearGradient></defs><path d="M12 3L4 7v5c0 5 4 9 8 10 4-1 8-5 8-10V7L12 3z" fill="url(#svgMsS2)" opacity="0.9"/></svg>';
          var svgStar   = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" style="display:inline;vertical-align:middle"><defs><linearGradient id="svgMsT2" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#F6C93E"/><stop offset="100%" stop-color="#E07040"/></linearGradient></defs><path d="M12 2l2.4 7.4H22l-6.2 4.5 2.4 7.4L12 17l-6.2 4.3 2.4-7.4L2 9.4h7.6z" fill="url(#svgMsT2)"/></svg>';
          var svgVip    = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" style="display:inline;vertical-align:middle"><defs><linearGradient id="svgMsV2" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#5B8DEF"/><stop offset="100%" stop-color="#A78BFA"/></linearGradient></defs><path d="M6 3h12l4 6-10 12L2 9z" fill="url(#svgMsV2)" opacity="0.9"/></svg>';
          var svgDone   = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" style="display:inline;vertical-align:middle"><defs><linearGradient id="svgMsD2" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#4CAF7D"/><stop offset="100%" stop-color="#2D8A5E"/></linearGradient></defs><circle cx="12" cy="12" r="9" fill="url(#svgMsD2)" opacity="0.15"/><path d="M7 12l4 4 6-7" stroke="url(#svgMsD2)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>';
          var svgEmpty  = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" style="display:inline;vertical-align:middle"><circle cx="12" cy="12" r="9" stroke="#C8CBD8" stroke-width="2"/></svg>';
          var milestones = [
            { n: 5,  icon: svgShield, title: S('msg','ref_milestone_shield') },
            { n: 10, icon: svgStar,   title: S('msg','ref_milestone_bonus') },
            { n: 20, icon: svgVip,    title: 'VIP' },
          ];
          var rc = d.ref_count || 0;
          var next = milestones.find(function(m){ return rc < m.n; });
          var rows = milestones.map(function(m) {
            var done = rc >= m.n;
            return '<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">'
              + (done ? svgDone : svgEmpty)
              + '<span style="font-size:11px;color:' + (done ? 'var(--green)' : 'var(--sub)') + '">' + m.n + ' ' + S('msg','milestone_unit') + ' ' + m.icon + ' ' + m.title + '</span>'
              + '</div>';
          }).join('');
          var nextTxt = next
            ? '<div style="font-size:11px;color:var(--accent);margin-top:6px"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" style="display:inline;vertical-align:middle;margin-right:3px"><defs><linearGradient id="svgHglass2" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#F6C93E"/><stop offset="100%" stop-color="#E07040"/></linearGradient></defs><path d="M6 2h12M6 22h12M7 2v4c0 2.5 2 4.5 5 6-3 1.5-5 3.5-5 6v4M17 2v4c0 2.5-2 4.5-5 6 3 1.5 5 3.5 5 6v4" stroke="url(#svgHglass2)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M9.5 16.5c0-1.5 1.2-2.5 2.5-3.2 1.3.7 2.5 1.7 2.5 3.2v3.5h-5v-3.5z" fill="url(#svgHglass2)" opacity="0.4"/></svg>' + S('msg','ref_next').replace('{n}', (next.n - rc)) + '</div>'
            : '<div style="font-size:11px;color:var(--green);margin-top:6px">' + S('msg','ref_all_done') + '</div>';
          return '<div style="background:var(--bg);border-radius:10px;padding:10px 12px;box-shadow:var(--sh-in);margin-bottom:12px">' + rows + nextTxt + '</div>';
        })()}

        <div style="background:var(--bg);border-radius:10px;padding:10px 12px;box-shadow:var(--sh-in);font-size:11px;color:var(--sub);word-break:break-all;margin-bottom:10px;font-family:'DM Mono',monospace">${d.ref_link || ''}</div>

        <button id="copy-ref-btn" data-link="${(d.ref_link || '').replace(/"/g, '&quot;')}" type="button"
          style="width:100%;padding:12px;border:none;border-radius:12px;background:linear-gradient(135deg,#4CAF7D,#5B8DEF);color:#fff;font-size:13px;font-weight:700;cursor:pointer">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" style="display:inline;vertical-align:middle;margin-right:5px"><rect x="9" y="9" width="13" height="13" rx="2" stroke="#fff" stroke-width="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" stroke="#fff" stroke-width="2" stroke-linecap="round"/></svg>
          ${S('msg','copy_ref')}
        </button>
      </div>
    </div>

    <!-- Sozlamalar -->
    <div class="section-title"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" style="display:inline;vertical-align:middle;margin-right:5px"><defs><linearGradient id="svgGear" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#8A8FA8"/><stop offset="100%" stop-color="#5B8DEF"/></linearGradient></defs><circle cx="12" cy="12" r="3.5" stroke="url(#svgGear)" stroke-width="2"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.93 4.93l2.12 2.12M16.95 16.95l2.12 2.12M4.93 19.07l2.12-2.12M16.95 7.05l2.12-2.12" stroke="url(#svgGear)" stroke-width="2" stroke-linecap="round"/></svg> ${S('profile','settings')}</div>
    <div style="margin-bottom:8px">
      <div class="rem-card" style="cursor:pointer" onclick="openEditProfile()">
        <div class="rem-top" style="margin-bottom:0">
          <div class="rem-icon"><svg width="22" height="22" viewBox="0 0 26 26" fill="none"><defs><linearGradient id="svgPenLg" x1="0" y1="0" x2="26" y2="26" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#A78BFA"/><stop offset="100%" stop-color="#5B8DEF"/></linearGradient></defs><path d="M17 4L22 9L10 21L4 22L5 16L17 4Z" fill="url(#svgPenLg)" opacity="0.85"/><path d="M15 6L20 11" stroke="white" stroke-width="1.2" stroke-linecap="round" opacity="0.6"/></svg></div><div class="rem-name" style="font-size:12px">${S('profile','edit_profile')}</div>
          <div style="color:var(--sub);font-size:18px">›</div>
        </div>
      </div>
    </div>
    <div class="rem-card" style="margin-top:4px;cursor:pointer" onclick="openLangModal()">
      <div class="rem-top" style="margin-bottom:0">
        <div class="rem-icon"><svg width="22" height="22" viewBox="0 0 26 26" fill="none"><defs><linearGradient id="svgGlobLg" x1="0" y1="0" x2="26" y2="26" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#5B8DEF"/><stop offset="100%" stop-color="#4CAF7D"/></linearGradient></defs><circle cx="13" cy="13" r="10" stroke="url(#svgGlobLg)" stroke-width="2"/><ellipse cx="13" cy="13" rx="4.5" ry="10" stroke="url(#svgGlobLg)" stroke-width="1.5"/><path d="M3 13h20M3 9h20M3 17h20" stroke="url(#svgGlobLg)" stroke-width="1.2" opacity="0.5"/></svg></div>
        <div class="rem-name">${S('profile','bot_lang')}</div>
        <div style="color:var(--sub);font-size:18px">›</div>
      </div>
    </div>
    <!-- Do'st taklif qilish — tugma (sozlamalar patternida, Bot tilidan keyin) -->
    <div class="rem-card" style="margin-top:4px;cursor:pointer" onclick="openReferralModal()">
      <div class="rem-top" style="margin-bottom:0">
        <div class="rem-icon"><svg width="22" height="22" viewBox="0 0 26 26" fill="none"><defs><linearGradient id="svgRefLg" x1="0" y1="0" x2="26" y2="26" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#4CAF7D"/><stop offset="100%" stop-color="#5B8DEF"/></linearGradient></defs><circle cx="9" cy="9" r="3.8" fill="url(#svgRefLg)" opacity="0.85"/><circle cx="18" cy="9.5" r="3" fill="url(#svgRefLg)" opacity="0.6"/><path d="M2 22c0-3.8 3.2-7 7-7s7 3.2 7 7" stroke="url(#svgRefLg)" stroke-width="2" stroke-linecap="round" fill="none"/><path d="M18 16c2.8.5 5.5 2.8 5.5 5.5" stroke="url(#svgRefLg)" stroke-width="1.8" stroke-linecap="round" fill="none" opacity="0.6"/></svg></div>
        <div>
          <div class="rem-name">${S('msg','ref_title')}</div>
          <div style="font-size:10px;color:var(--sub)">${S('msg','ref_count').replace('{n}', d.ref_count || 0)} · +${(d.ref_count || 0) * 50} ${S('msg','ref_total_pts')}</div>
        </div>
        <div style="color:var(--sub);font-size:18px;margin-left:auto">›</div>
      </div>
    </div>
    <div class="rem-card" style="margin-top:4px;cursor:pointer" onclick="switchTab('reminders',null)">
      <div class="rem-top" style="margin-bottom:0">
        <div class="rem-icon"><svg width="22" height="22" viewBox="0 0 26 26" fill="none"><defs><linearGradient id="svgBellLg" x1="0" y1="0" x2="26" y2="26" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#F6C93E"/><stop offset="100%" stop-color="#E07040"/></linearGradient></defs><path d="M13 3C13 3 8 6 8 13v5H5l2 2h12l2-2h-3v-5c0-7-5-10-5-10z" fill="url(#svgBellLg)" opacity="0.85"/><circle cx="13" cy="22" r="1.5" fill="url(#svgBellLg)"/></svg></div><div class="rem-name">${S('profile','reminders')}</div>
        <div style="color:var(--sub);font-size:18px">›</div>
      </div>
    </div>

    <div class="rem-card" style="margin-top:4px">
      <div class="rem-top" style="margin-bottom:0;justify-content:space-between">
        <div style="display:flex;align-items:center;gap:10px">
          <div class="rem-icon"><svg width="22" height="22" viewBox="0 0 26 26" fill="none"><defs><linearGradient id="svgMoonLg" x1="0" y1="0" x2="26" y2="26" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#A78BFA"/><stop offset="100%" stop-color="#5B8DEF"/></linearGradient></defs><path d="M21 14.5A9 9 0 1111.5 5a7 7 0 009.5 9.5z" fill="url(#svgMoonLg)" opacity="0.9"/></svg></div>
          <div>
            <div class="rem-name">${S('profile','evening')}</div>
            <div style="font-size:10px;color:var(--sub)">${S('profile','evening_sub')}</div>
          </div>
        </div>
        <label style="position:relative;display:inline-block;width:44px;height:24px;cursor:pointer">
          <input type="checkbox" id="evening-toggle" onchange="saveEveningNotify(this.checked)" style="opacity:0;width:0;height:0">
          <span id="evening-slider" style="position:absolute;inset:0;border-radius:24px;background:var(--bg);box-shadow:var(--sh-in);transition:.3s"></span>
          <span id="evening-knob" style="position:absolute;left:3px;top:3px;width:18px;height:18px;border-radius:50%;background:var(--sub);box-shadow:var(--sh-sm);transition:.3s"></span>
        </label>
      </div>
    </div>
    <div class="rem-card" style="margin-top:4px">
      <div class="rem-top" style="margin-bottom:0;justify-content:space-between">
        <div style="display:flex;align-items:center;gap:10px">
          <div class="rem-icon"><svg width="22" height="22" viewBox="0 0 26 26" fill="none"><defs><linearGradient id="svgStarsLg" x1="0" y1="0" x2="26" y2="26" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#F6C93E"/><stop offset="100%" stop-color="#A78BFA"/></linearGradient></defs><circle cx="8" cy="8" r="2.2" fill="url(#svgStarsLg)"/><circle cx="18" cy="5" r="1.4" fill="url(#svgStarsLg)" opacity="0.7"/><circle cx="20" cy="16" r="1.8" fill="url(#svgStarsLg)" opacity="0.85"/><circle cx="6" cy="19" r="1.2" fill="url(#svgStarsLg)" opacity="0.6"/><circle cx="13" cy="13" r="3" fill="url(#svgStarsLg)" opacity="0.5"/></svg></div>
          <div>
            <div class="rem-name">${S('profile','dark_mode')}</div>
            <div style="font-size:10px;color:var(--sub)">${S('msg','dark_mode_desc')}</div>
          </div>
        </div>
        <label style="position:relative;display:inline-block;width:44px;height:24px;cursor:pointer">
          <input type="checkbox" id="dark-toggle" onchange="saveDarkMode(this.checked)" style="opacity:0;width:0;height:0">
          <span id="dark-slider" style="position:absolute;inset:0;border-radius:24px;background:var(--bg);box-shadow:var(--sh-in);transition:.3s"></span>
          <span id="dark-knob" style="position:absolute;left:3px;top:3px;width:18px;height:18px;border-radius:50%;background:var(--sub);box-shadow:var(--sh-sm);transition:.3s"></span>
        </label>
      </div>
    </div>
    <a href="https://t.me/Super_habits" target="_blank" class="rem-card" style="margin-top:4px;display:flex;align-items:center;gap:10px;text-decoration:none;border-radius:14px 14px 0 0">
      <div class="rem-top" style="margin-bottom:0;width:100%">
        <div class="rem-icon"><svg width="22" height="22" viewBox="0 0 26 26" fill="none"><defs><linearGradient id="svgTgCh" x1="0" y1="0" x2="26" y2="26" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#5B8DEF"/><stop offset="100%" stop-color="#A78BFA"/></linearGradient></defs><path d="M22 4L3 11.5L10 14M22 4L15 22L10 14M22 4L10 14" stroke="url(#svgTgCh)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></div>
        <div style="flex:1">
          <div class="rem-name">${S('profile','channel')}</div>
          <div style="font-size:10px;color:var(--sub)">@Super_habits</div>
        </div>
        <div style="color:var(--sub);font-size:18px">›</div>
      </div>
    </a>
    <div style="border-radius:0 0 14px 14px;padding:9px 14px 10px;background:linear-gradient(90deg,#5B8DEF22,#A78BFA22,#5B8DEF22);box-shadow:var(--sh-sm)">
      <div style="font-size:11px;font-weight:700;font-family:'DM Sans',sans-serif;letter-spacing:0.01em;background:linear-gradient(90deg,#5B8DEF,#A78BFA,#4CAF7D,#5B8DEF);background-size:300% auto;-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;animation:shimmerSlide 3s linear infinite">
        ${S('msg','channel_sub')}
      </div>
    </div>
    <div style="margin:8px 0 4px;text-align:center">
      <button type="button" onclick="localStorage.removeItem('sh_ob_v3');maybeShowOnboard()" style="background:none;border:none;font-size:12px;color:var(--sub);cursor:pointer;padding:6px 12px;font-family:inherit;text-decoration:underline;display:inline-flex;align-items:center;gap:5px"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 4v6h-6"/><path d="M1 20v-6h6"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10"/><path d="M20.49 15a9 9 0 0 1-14.85 3.36L1 14"/></svg> ${S('profile','onboarding')}</button>
    </div>
    <div class="toast" id="toast-profile"></div>

    <!-- Bot tili modal -->
    <div class="modal-overlay" id="lang-modal">
      <div class="modal">
        <div class="modal-handle"></div>
        <button class="modal-close" onclick="closeLangModal()"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" style="display:block"><line x1="18" y1="6" x2="6" y2="18" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/><line x1="6" y1="6" x2="18" y2="18" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/></svg></button>
        <div class="modal-title"><svg width="18" height="18" viewBox="0 0 26 26" fill="none" style="display:inline;vertical-align:middle;margin-right:6px"><defs><linearGradient id="svgGlobH" x1="0" y1="0" x2="26" y2="26" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#5B8DEF"/><stop offset="100%" stop-color="#4CAF7D"/></linearGradient></defs><circle cx="13" cy="13" r="10" stroke="url(#svgGlobH)" stroke-width="2"/><ellipse cx="13" cy="13" rx="4.5" ry="10" stroke="url(#svgGlobH)" stroke-width="1.5"/><path d="M3 13h20M3 9h20M3 17h20" stroke="url(#svgGlobH)" stroke-width="1.2" opacity="0.5"/></svg>${S('profile','lang_modal_title')}</div>
        <div style="display:flex;flex-direction:column;gap:10px;margin-top:8px" id="lang-modal-btns"></div>
        <button class="rem-save-btn" style="margin-top:16px" onclick="saveLang()" type="button" id="lang-save-btn"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" style="display:inline;vertical-align:middle;margin-right:5px"><defs><linearGradient id="svgSave" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#4CAF7D"/><stop offset="100%" stop-color="#2D8A5E"/></linearGradient></defs><path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z" stroke="url(#svgSave)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M17 21v-8H7v8M7 3v5h8" stroke="url(#svgSave)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg><span id="lang-save-txt">${S('profile','save_btn')}</span></button>
      </div>
    </div>

    <!-- Ma'lumotlarni tahrirlash modal -->
    <div class="modal-overlay" id="edit-profile-modal">
      <div class="modal">
        <div class="modal-handle"></div>
        <button class="modal-close" onclick="closeEditProfile()"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" style="display:block"><line x1="18" y1="6" x2="6" y2="18" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/><line x1="6" y1="6" x2="18" y2="18" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/></svg></button>
        <div class="modal-title" id="edit-profile-title">Ma'lumotlarni tahrirlash</div>
        <div class="field" style="text-align:center;margin-bottom:16px">
          <div id="ep-avatar-wrap" style="display:inline-block;position:relative;cursor:pointer" onclick="document.getElementById('ep-photo-input').click()">
            <div id="ep-avatar" style="width:72px;height:72px;border-radius:50%;background:var(--bg);box-shadow:var(--sh-sm);display:flex;align-items:center;justify-content:center;font-size:28px;font-weight:700;color:var(--text);overflow:hidden;margin:0 auto"></div>
            <div style="position:absolute;bottom:0;right:0;width:22px;height:22px;border-radius:50%;background:var(--text);display:flex;align-items:center;justify-content:center;font-size:12px"><svg width="12" height="12" viewBox="0 0 26 26" fill="none"><defs><linearGradient id="svgPenB" x1="0" y1="0" x2="26" y2="26" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#ffffff"/><stop offset="100%" stop-color="#E0E0E0"/></linearGradient></defs><path d="M17 4L22 9L10 21L4 22L5 16L17 4Z" fill="url(#svgPenB)" opacity="0.95"/></svg></div>
          </div>
          <input type="file" id="ep-photo-input" accept="image/*" style="display:none" onchange="previewEpPhoto(this)">
          <div style="font-size:10px;color:var(--sub);margin-top:6px">${S('profile','click_photo')}</div>
        </div>
        <div class="field">
          <label>${S('msg','name_label')}</label>
          <input id="ep-name" type="text" placeholder="${S('msg','name_placeholder')}" maxlength="60">
        </div>
        <div class="field">
          <label>${S('profile','bio_label')}</label>
          <textarea id="ep-bio" placeholder="${S('profile','bio_placeholder')}" maxlength="200" rows="3" style="width:100%;resize:vertical;font-family:inherit;font-size:13px;padding:10px 12px;border:none;border-radius:12px;background:var(--bg);box-shadow:var(--sh-in);color:var(--text);outline:none"></textarea>
          <div style="font-size:10px;color:var(--sub);text-align:right;margin-top:2px"><span id="ep-bio-count">0</span>/200</div>
        </div>
        <div class="field">
          <label>${S('profile','phone_label')}</label>
          <input id="ep-phone" type="tel" placeholder="+998 90 123 45 67" maxlength="20">
        </div>
        <button class="save-btn" onclick="saveEditProfile()" type="button"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" style="display:inline;vertical-align:middle;margin-right:5px"><defs><linearGradient id="svgSave" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#4CAF7D"/><stop offset="100%" stop-color="#2D8A5E"/></linearGradient></defs><path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z" stroke="url(#svgSave)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M17 21v-8H7v8M7 3v5h8" stroke="url(#svgSave)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg><span id="edit-save-txt">${S('profile','save_btn')}</span></button>
      </div>
    </div>`;
  setTimeout(function() {
    var tog = document.getElementById("evening-toggle");
    if (tog) { tog.checked = (d.evening_notify !== false); updateToggleVisual(tog.checked); }
    var dtog = document.getElementById("dark-toggle");
    if (dtog) {
      var darkVal = (d.dark_mode === true) || (localStorage.getItem('sh_dark') === '1');
      if (d.dark_mode === true) { localStorage.setItem('sh_dark', '1'); document.body.classList.add('dark'); }
      else if (d.dark_mode === false && d.hasOwnProperty('dark_mode')) { localStorage.removeItem('sh_dark'); document.body.classList.remove('dark'); }
      dtog.checked = darkVal;
      updateDarkToggleVisual(darkVal);
    }
    var copyBtn = document.getElementById("copy-ref-btn");
    if (copyBtn) {
      copyBtn.addEventListener("click", function() {
        copyRefLink(this.getAttribute("data-link") || "");
      });
    }
  }, 30);
}

// ── DO'ST TAKLIF QILISH MODAL ──
function openReferralModal() {
  var m = document.getElementById('ref-modal');
  if (m) {
    m.classList.add('show');
    try { if (window.tg && tg.HapticFeedback) tg.HapticFeedback.impactOccurred('light'); } catch(e) {}
  }
}
function closeReferralModal() {
  var m = document.getElementById('ref-modal');
  if (m) m.classList.remove('show');
}

// ── PROFIL TAHRIRLASH ──
let _epPhotoDataUrl = null;

function openEditProfile() {
  const d = data.profile || {};
  const epTitle = document.getElementById('edit-profile-title');
  if (epTitle) epTitle.textContent = S('msg','edit_profile_title');
  const photoUrl = d.photo_url || user.photo_url || '';
  const initial  = ((d.display_name || d.name || '?')[0]).toUpperCase();
  const epAv = document.getElementById('ep-avatar');
  if (epAv) {
    if (photoUrl) epAv.innerHTML = `<img src="${photoUrl}" style="width:100%;height:100%;object-fit:cover">`;
    else epAv.textContent = initial;
  }
  const epName  = document.getElementById('ep-name');
  const epPhone = document.getElementById('ep-phone');
  if (epName)  epName.value  = d.display_name || d.name || '';
  if (epPhone) epPhone.value = d.phone || '';
  const epBio = document.getElementById('ep-bio');
  if (epBio) {
    epBio.value = d.bio || '';
    const cnt = document.getElementById('ep-bio-count');
    if (cnt) cnt.textContent = epBio.value.length;
    epBio.oninput = function() { if (cnt) cnt.textContent = this.value.length; };
  }
  _epPhotoDataUrl = null;
  document.getElementById('edit-profile-modal')?.classList.add('open');
}
function closeEditProfile() {
  document.getElementById('edit-profile-modal')?.classList.remove('open');
}
function previewEpPhoto(input) {
  const file = input.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = e => {
    const img = new Image();
    img.onload = () => {
      // Canvas orqali 200x200 ga resize + JPEG 70% compress
      const size = 200;
      const canvas = document.createElement('canvas');
      canvas.width = size; canvas.height = size;
      const ctx = canvas.getContext('2d');
      // Markazdan kvadrat qirqish (crop)
      const min = Math.min(img.width, img.height);
      const sx = (img.width - min) / 2;
      const sy = (img.height - min) / 2;
      ctx.drawImage(img, sx, sy, min, min, 0, 0, size, size);
      _epPhotoDataUrl = canvas.toDataURL('image/jpeg', 0.7);
      const epAv = document.getElementById('ep-avatar');
      if (epAv) epAv.innerHTML = `<img src="${_epPhotoDataUrl}" style="width:100%;height:100%;object-fit:cover">`;
    };
    img.src = e.target.result;
  };
  reader.readAsDataURL(file);
}
async function saveEditProfile() {
  const name  = document.getElementById('ep-name')?.value.trim();
  const phone = document.getElementById('ep-phone')?.value.trim();
  const bio   = document.getElementById('ep-bio')?.value.trim();
  const body  = {};
  if (name)           body.display_name = name;
  if (phone)          body.phone        = phone;
  if (bio !== undefined && bio !== null) body.bio = bio;
  if (_epPhotoDataUrl) body.photo_url   = _epPhotoDataUrl;
  if (!Object.keys(body).length) { closeEditProfile(); return; }
  const btn = document.getElementById('edit-save-txt')?.parentElement;
  if (btn) { btn.disabled = true; document.getElementById('edit-save-txt').textContent = S('profile','saving'); }
  try {
    const res = await fetch(`${API}/profile/${userId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', 'X-Init-Data': initData, 'X-User-Id': userId },
      body: JSON.stringify(body)
    });
    const rj = await res.json().catch(() => ({}));
    const t = document.getElementById('toast-profile');
    if (!res.ok || rj.ok === false) {
      if (btn) { btn.disabled = false; document.getElementById('edit-save-txt').textContent = S('profile','save_btn'); }
      if (t) { t.textContent = '❌ ' + (rj.error || S('msg','error_label')); t.classList.add('show'); setTimeout(() => t.classList.remove('show'), 2000); }
      return;
    }
    closeEditProfile();
    if (btn) { btn.disabled = false; document.getElementById('edit-save-txt').textContent = S('profile','save_btn'); }
    loaded.profile = false;
    await loadProfile();
    if (t) { t.textContent = S('profile','saved'); t.classList.add('show'); setTimeout(() => t.classList.remove('show'), 2000); }
  } catch(e) {
    const btn2 = document.getElementById('edit-save-txt')?.parentElement;
    if (btn2) { btn2.disabled = false; document.getElementById('edit-save-txt').textContent = S('profile','save_btn'); }
    const t = document.getElementById('toast-profile');
    if (t) { t.textContent = '❌ ' + S('msg','error_label'); t.classList.add('show'); setTimeout(() => t.classList.remove('show'), 2000); }
  }
}

function updateToggleVisual(checked) {
  const slider = document.getElementById('evening-slider');
  const knob   = document.getElementById('evening-knob');
  if (!slider || !knob) return;
  slider.style.background = checked ? 'var(--green)' : 'var(--bg)';
  knob.style.background   = checked ? '#fff' : 'var(--sub)';
  knob.style.left         = checked ? '23px' : '3px';
}

function updateDarkToggleVisual(checked) {
  const slider = document.getElementById('dark-slider');
  const knob   = document.getElementById('dark-knob');
  if (!slider || !knob) return;
  slider.style.background = checked ? '#A78BFA' : 'var(--bg)';
  knob.style.background   = checked ? '#fff' : 'var(--sub)';
  knob.style.left         = checked ? '23px' : '3px';
}

function saveDarkMode(val) {
  updateDarkToggleVisual(val);
  if (val) {
    localStorage.setItem('sh_dark', '1');
    document.body.classList.add('dark');
  } else {
    localStorage.removeItem('sh_dark');
    document.body.classList.remove('dark');
  }
  fetch(`${API}/profile/${userId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', 'X-Init-Data': initData, 'X-User-Id': userId },
    body: JSON.stringify({ dark_mode: val })
  }).catch(() => {});
  const t = document.getElementById('toast-profile');
  if (t) { t.textContent = val ? '🌙 ' + S('msg','dark_on') : '☀️ ' + S('msg','dark_off'); t.className = 'toast show'; setTimeout(()=>t.className='toast',2500); }
}

async function saveEveningNotify(val) {
  updateToggleVisual(val);
  try {
    await fetch(`${API}/profile/${userId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', 'X-Init-Data': initData, 'X-User-Id': userId },
      body: JSON.stringify({ evening_notify: val })
    });
    const t = document.getElementById('toast-profile');
    if (t) { t.textContent = val ? S('msg','evening_on') : S('msg','evening_off'); t.className = 'toast show'; setTimeout(()=>t.className='toast',2500); }
  } catch(e) { showToast(S('friends','error'), true); }
}


function updateNavLabels() {
  const ids = ['today','stats','habits','bozor','profile'];
  ids.forEach(id => {
    const el = document.querySelector('#nav-' + id + ' .nav-label');
    if (el) el.textContent = S('nav', id);
  });
  // Static button labels
  const saveTxt = S('profile','save_btn');
  ['lang-save-txt','edit-save-txt','habit-save-txt'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.textContent = saveTxt;
  });
  // Habit form labels
  const habitLbls = [
    ['lbl-habit-name', S('habits','name_label')],
    ['lbl-habit-type', S('habits','type_label')],
    ['lbl-per-day-hint', S('habits','per_day_hint')],
    ['lbl-time', S('habits','time_label')],
    ['lbl-icon-pick', S('habits','icon_label')],
  ];
  habitLbls.forEach(([id, txt]) => {
    const el = document.getElementById(id);
    if (el) el.textContent = txt;
  });
  // Badge popup default & PTR text
  const bp = document.getElementById('bp-title');
  if (bp && !bp.innerHTML.includes('<svg')) bp.textContent = S('msg','badge_new');
  // Back button label
  const backLbl = document.getElementById('back-label');
  if (backLbl) backLbl.textContent = S('msg','back');
  // Loading spinners
  document.querySelectorAll('.loading-text').forEach(el => el.textContent = S('msg','loading'));
  const ptr = document.getElementById('ptr-text');
  if (ptr && ptr.textContent.indexOf('...') < 0) ptr.textContent = S('msg','ptr_pull');
  // Sub-tab labels (SVG + text node)
  const _st = (id, key) => {
    const el = document.getElementById(id);
    if (!el) return;
    const nodes = [...el.childNodes].filter(n => n.nodeType === 3 && n.textContent.trim());
    if (nodes.length) nodes[nodes.length-1].textContent = S('msg', key);
  };
  _st('ssub-rating', 'tab_rating');
  _st('ssub-stats', 'tab_stats');
  _st('ssub-friends', 'tab_grp_friend');
  _st('gsub-groups', 'tab_groups');
  _st('gsub-friends', 'tab_friends');
  // Loading spinners
  document.querySelectorAll('.loading').forEach(el => {
    const sp = el.querySelector('.spinner');
    if (sp && el.childNodes.length > 1) {
      const tn = [...el.childNodes].filter(n => n.nodeType === 3);
      if (tn.length) tn[tn.length-1].textContent = S('msg','loading');
    }
  });
}

function setLang(val) {
  selectedLang = val;
  ['uz','ru','en'].forEach(l => {
    const btn = document.getElementById('lang-' + l);
    if (btn) btn.classList.toggle('active', l === val);
  });
}

function openLangModal() {
  const langs = [
    {id:'uz', label:"🇺🇿 O'zbek"},
    {id:'ru', label:'🇷🇺 Русский'},
    {id:'en', label:'🇬🇧 English'},
  ];
  const current = document.querySelector('[id^="lang-"].active')?.id?.replace('lang-','') || currentLang || 'uz';
  const btns = langs.map(l => `
    <button class="rep-btn ${current===l.id?'active':''}" id="lang-${l.id}"
      onclick="document.querySelectorAll('#lang-modal-btns .rep-btn').forEach(b=>b.classList.remove('active'));this.classList.add('active');setLang('${l.id}')"
      type="button" style="width:100%;padding:12px;font-size:14px">${l.label}</button>
  `).join('');
  document.getElementById('lang-modal-btns').innerHTML = btns;
  document.getElementById('lang-modal').classList.add('open');
}
function closeLangModal() {
  document.getElementById('lang-modal').classList.remove('open');
}
async function saveLang() {
  if (!selectedLang) return;
  const btn = document.getElementById('lang-save-btn');
  if (btn) { btn.textContent = S('profile','saving'); btn.disabled = true; }
  try {
    const res = await fetch(`${API}/profile/${userId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', 'X-Init-Data': initData, 'X-User-Id': userId },
      body: JSON.stringify({ lang: selectedLang })
    });
    const r = await res.json();
    if (!r.ok) throw new Error(r.error);
    currentLang = selectedLang;
    localStorage.setItem('sh_lang', selectedLang);
    closeLangModal();
    const t = document.getElementById('toast-profile');
    if (t) { t.textContent = S('msg','lang_changed'); t.className = 'toast show'; setTimeout(()=>t.className='toast',2500); }
    // Barcha sahifalar cache'ini tozalash — til o'zgarganda qayta yuklansin
    Object.keys(loaded).forEach(k => loaded[k] = false);
    updateNavLabels();
    await loadProfile();
    // Agar boshqa tab ochiq bo'lsa — uni ham qayta render qilish
    const activeTab = document.querySelector('.page.active')?.id?.replace('page-','');
    if (activeTab && activeTab !== 'profile') {
      const tabFns = {today:loadToday, stats:loadStats, habits:loadHabits, bozor:loadShop};
      if (tabFns[activeTab]) await tabFns[activeTab]();
    }
  } catch(e) {
    if (btn) { btn.textContent = S('profile','save'); btn.disabled = false; }
  }
}

// ── Referral link nusxalash ──
function copyRefLink(link) {
  if (!link) return;
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(link).then(() => {
      const t = document.getElementById('toast-profile');
      if (t) { t.textContent = S('msg','copy_link'); t.className = 'toast show'; setTimeout(() => t.className = 'toast', 2500); }
    }).catch(() => {
      _fallbackCopyRef(link);
    });
  } else {
    _fallbackCopyRef(link);
  }
}
function _fallbackCopyRef(link) {
  const ta = document.createElement('textarea');
  ta.value = link; ta.style.position = 'fixed'; ta.style.opacity = '0';
  document.body.appendChild(ta); ta.select();
  try { document.execCommand('copy'); } catch(e) {}
  document.body.removeChild(ta);
  const t = document.getElementById('toast-profile');
  if (t) { t.textContent = S('msg','copy_link'); t.className = 'toast show'; setTimeout(() => t.className = 'toast', 2500); }
}