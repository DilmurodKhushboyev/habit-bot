// ── GURUHLAR ──
async function loadGroups() {
  try {
    const d = await apiFetch(`groups/${userId}`);
    renderGroups(d);
  } catch(e) {
    document.getElementById('groups-content').innerHTML =
      `<div class="empty-state"><div class="icon"><svg width="28" height="28" viewBox="0 0 24 24" fill="none"><defs><linearGradient id="svgWarn" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#FBBF24"/><stop offset="100%" stop-color="#F59E0B"/></linearGradient></defs><path d="M12 3L2 21h20L12 3z" stroke="url(#svgWarn)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/><path d="M12 10v5M12 17.5v.5" stroke="url(#svgWarn)" stroke-width="2" stroke-linecap="round"/></svg></div>${S('msg','data_error')}.</div>`;
  }
}

function toggleGroup(id) {
  const detail = document.getElementById('gdetail-' + id);
  const arrow  = document.getElementById('garrow-' + id);
  if (!detail) return;
  const open = detail.style.display === 'block';
  detail.style.display = open ? 'none' : 'block';
  if (arrow) arrow.textContent = open ? '▾' : '▴';
}

function renderGroups(d) {
  const groups = d.groups || [];
  let html = '';
  groups.forEach(g => {
    if (!g.id && g.gid) g.id = g.gid;
    const allMembers = (g.members || []);
    const membersHtml = allMembers.map((m, i) =>
      `<div class="member-row">
        <span>${i < 3 ? [`<svg width="22" height="22" viewBox="0 0 24 24" fill="none" style="display:inline;vertical-align:middle"><defs><linearGradient id="svgGold" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#F6E27A"/><stop offset="100%" stop-color="#D4963A"/></linearGradient></defs><circle cx="12" cy="12" r="10" fill="url(#svgGold)"/><text x="12" y="16" text-anchor="middle" font-size="11" font-weight="700" fill="white" font-family="sans-serif">1</text></svg>`,`<svg width="22" height="22" viewBox="0 0 24 24" fill="none" style="display:inline;vertical-align:middle"><defs><linearGradient id="svgSilv" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#E8E8E8"/><stop offset="100%" stop-color="#A0A8B8"/></linearGradient></defs><circle cx="12" cy="12" r="10" fill="url(#svgSilv)"/><text x="12" y="16" text-anchor="middle" font-size="11" font-weight="700" fill="white" font-family="sans-serif">2</text></svg>`,`<svg width="22" height="22" viewBox="0 0 24 24" fill="none" style="display:inline;vertical-align:middle"><defs><linearGradient id="svgBronz" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#E8A87C"/><stop offset="100%" stop-color="#A0522D"/></linearGradient></defs><circle cx="12" cy="12" r="10" fill="url(#svgBronz)"/><text x="12" y="16" text-anchor="middle" font-size="11" font-weight="700" fill="white" font-family="sans-serif">3</text></svg>`][i] : (i+1)+'.'} ${m.name}</span>
        <span style="color:var(--sub);font-size:12px">${m.points} ${S('groups','points_label')}</span>
      </div>`
    ).join('');

    html += `
      <div class="rem-card" id="gcard-${g.id}" style="cursor:pointer">
        <div class="rem-top" onclick="toggleGroup('${g.id}')">
          <div class="rem-icon"><svg width="22" height="22" viewBox="0 0 26 26" fill="none"><defs><linearGradient id="svgUsers" x1="0" y1="0" x2="26" y2="26" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#059669"/><stop offset="100%" stop-color="#34D399"/></linearGradient></defs><circle cx="10" cy="9" r="4" fill="url(#svgUsers)"/><circle cx="18" cy="10" r="3" fill="url(#svgUsers)" opacity="0.6"/><path d="M2 22c0-4 3.6-7 8-7s8 3 8 7" stroke="url(#svgUsers)" stroke-width="2" fill="none"/><path d="M18 15c2.5.5 5 2.5 5 5" stroke="url(#svgUsers)" stroke-width="1.5" stroke-linecap="round" fill="none" opacity="0.6"/></svg></div>
          <div style="flex:1">
            <div style="font-size:14px;font-weight:700;color:var(--text)">${g.name}</div>
            <div style="font-size:11px;color:var(--sub);margin-top:2px"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" style="display:inline;vertical-align:middle;margin-right:3px"><defs><linearGradient id="svgPin" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#059669"/><stop offset="100%" stop-color="#34D399"/></linearGradient></defs><path d="M12 2a5 5 0 015 5c0 4-5 10-5 10S7 11 7 7a5 5 0 015-5z" fill="url(#svgPin)" opacity="0.85"/><circle cx="12" cy="7" r="2" fill="white" opacity="0.8"/></svg> ${g.habit_name} · ${g.member_count} ${S('groups','member_unit')} ${g.is_admin ? '· 👑 ' + S('groups','admin_label') : ''}${g.streak > 0 ? ` · 🔥 ${g.streak} ${S('profile','kun')}` : ''}</div>
          </div>
          <span id="garrow-${g.id}" style="font-size:16px;color:var(--sub);padding:0 4px">▾</span>
          ${g.is_admin ? `<button class="hbtn" onclick="event.stopPropagation();deleteGroup('${g.id}')" title="${S('msg','delete_btn')}"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" style="display:inline;vertical-align:middle"><defs><linearGradient id="svgTrash" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#FF6B8A"/><stop offset="100%" stop-color="#059669"/></linearGradient></defs><path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6" stroke="url(#svgTrash)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M10 11v6M14 11v6" stroke="url(#svgTrash)" stroke-width="2" stroke-linecap="round"/></svg></button>` : ''}
        </div>
        <div id="gdetail-${g.id}" style="display:none">
          ${membersHtml ? `<div style="margin-top:10px;display:flex;flex-direction:column;gap:6px">${membersHtml}</div>` : `<div style="font-size:12px;color:var(--sub);margin-top:8px;text-align:center">${S('groups','no_members')}</div>`}
          ${g.invite_link ? `
          <button class="rem-save-btn" style="margin-top:10px" onclick="copyInvite('${g.invite_link}')" type="button">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" style="display:inline;vertical-align:middle;margin-right:5px"><defs><linearGradient id="svgLink" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#059669"/><stop offset="100%" stop-color="#10B981"/></linearGradient></defs><path d="M10 14a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71" stroke="url(#svgLink)" stroke-width="2" stroke-linecap="round"/><path d="M14 10a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71" stroke="url(#svgLink)" stroke-width="2" stroke-linecap="round"/></svg>${S('msg','copy_invite')}
          </button>` : ''}
        </div>
        ${(() => {
          const wg = g.weekly_goal || 0;
          const wd = g.weekly_done || 0;
          const wt = g.weekly_total || 1;
          const wpct = wg > 0 ? Math.min(100, Math.round(wd / wg * 100)) : Math.round(wd / wt * 100);
          const wc = wpct >= 100 ? '#10B981' : wpct >= 50 ? '#059669' : '#059669';
          const goalTxt = wg > 0 ? `${wd}/${wg}` : `${wd} ta`;
          const goalLabel = wg > 0 ? (wd >= wg ? S('msg','grp_goal_done') : S('msg','grp_goal_left').replace('{n}', wg - wd)) : S('msg','grp_goal_none');
          return `<div style="margin-top:8px;padding-top:8px;border-top:1px solid var(--bg)">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:5px">
              <div style="font-size:9px;color:var(--sub);text-transform:uppercase;letter-spacing:1px;font-weight:600">${S('msg','grp_weekly')}</div>
              <div style="display:flex;align-items:center;gap:6px">
                <span style="font-size:10px;font-weight:700;color:${wc}">${goalTxt} · ${goalLabel}</span>
                ${g.is_admin ? '<button onclick="event.stopPropagation();setGroupGoal(\'' + g.id + '\', ' + wg + ')" type="button" style="background:none;border:none;color:var(--sub);font-size:11px;cursor:pointer;padding:0 2px">✏️</button>' : ''}
              </div>
            </div>
            <div style="height:5px;border-radius:3px;background:var(--bg);box-shadow:var(--sh-in);overflow:hidden">
              <div style="height:100%;border-radius:3px;width:${wpct}%;background:linear-gradient(90deg,${wc}99,${wc});transition:width .5s ease"></div>
            </div>
          </div>`;
        })()}
        <div style="margin-top:8px;border-top:1px solid var(--bg);padding-top:8px;display:flex;gap:8px;align-items:center">
          <button onclick="event.stopPropagation();groupCheckin('${g.id}', this)" type="button"
            id="gcheckin-${g.id}"
            style="flex:1;padding:10px;border:none;border-radius:12px;font-size:13px;font-weight:700;cursor:pointer;transition:all .2s;
              ${g.done_today_me
                ? 'background:var(--bg);color:var(--green);box-shadow:var(--sh-in)'
                : 'background:linear-gradient(135deg,#10B981,#047857);color:#fff'}">
            ${g.done_today_me ? S('msg','grp_done_btn') : S('msg','grp_do_btn')}
          </button>
          <button onclick="event.stopPropagation();openGroupHabitAdd('${g.id}')" type="button"
            style="background:none;border:none;color:var(--accent);font-size:12px;font-weight:600;cursor:pointer;padding:2px 8px;white-space:nowrap">
            ＋ ${S('groups','habit_name')}
          </button>
        </div>
      </div>`;
  });

  document.getElementById('groups-content').innerHTML = `
    <button class="add-btn" onclick="openGroupAdd()">${S('msg','grp_add_btn')}</button>
    <div class="section-title">${S('groups','title')} (${groups.length})</div>
    ${html || `<div class="empty-state"><div class="icon"><svg width="28" height="28" viewBox="0 0 26 26" fill="none"><defs><linearGradient id="svgUsrEm" x1="0" y1="0" x2="26" y2="26" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#059669"/><stop offset="100%" stop-color="#34D399"/></linearGradient></defs><circle cx="10" cy="9" r="4" fill="url(#svgUsrEm)"/><circle cx="18" cy="10" r="3" fill="url(#svgUsrEm)" opacity="0.6"/><path d="M2 22c0-4 3.6-7 8-7s8 3 8 7" stroke="url(#svgUsrEm)" stroke-width="2" fill="none"/><path d="M18 15c2.5.5 5 2.5 5 5" stroke="url(#svgUsrEm)" stroke-width="1.5" stroke-linecap="round" fill="none" opacity="0.6"/></svg></div>${S('groups','empty')}</div>`}
    <div class="toast" id="toast-group"></div>

    <div class="modal-overlay" id="group-modal">
      <div class="modal">
        <div class="modal-handle"></div>
        <button class="modal-close" onclick="closeGroupModal()"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" style="display:block"><line x1="18" y1="6" x2="6" y2="18" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/><line x1="6" y1="6" x2="18" y2="18" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/></svg></button>
        <div class="modal-title">${S('msg','grp_new_title')}</div>
        <div class="field">
          <label>${S('groups','group_name')}</label>
          <input id="g-name" type="text" placeholder="Masalan: Kitob klubi" maxlength="40">
        </div>
        <div class="field">
          <label>${S('groups','habit_name')}</label>
          <input id="g-habit" type="text" placeholder="Masalan: Kitob o'qish" maxlength="60">
        </div>
        <div class="field">
          <label>${S('habits','time_label')}</label>
          <input id="g-time" type="time">
        </div>
        <button class="save-btn" onclick="saveGroup()" type="button">${S('groups','create')}</button>
      </div>
    </div>`;
}

function openGroupAdd() {
  const gn = document.getElementById('g-name');
  if (gn) gn.placeholder = S('msg','ph_group_name');
  const gh = document.getElementById('g-habit');
  if (gh) gh.placeholder = S('msg','ph_habit_name');
  document.getElementById('group-modal').classList.add('open');
}
function openGroupHabitAdd(gid) {
  // Guruhga odat qo'shish — hozircha invite link ochadi
  const card = document.getElementById('gcard-' + gid);
  if (!card) return;
  const detail = document.getElementById('gdetail-' + gid);
  if (detail && detail.style.display !== 'block') toggleGroup(gid);
  showToastGroup(S('msg','grp_soon'));
}
async function setGroupGoal(gid, currentGoal) {
  const val = prompt(S('msg','weekly_goal'), currentGoal || '');
  if (val === null) return;
  const goal = parseInt(val);
  if (isNaN(goal) || goal < 0) { showToastGroup('❌ Noto\u02bcg\u02bcri qiymat'); return; }
  try {
    const r = await apiFetch(`groups/${userId}/${gid}/goal`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ goal })
    });
    if (r.ok) { showToastGroup(S('msg','grp_goal_saved').replace('{n}', goal)); loaded.stats = false; loadGroups(); }
    else showToastGroup('❌ ' + (r.error || S('msg','error_label')));
  } catch(e) { showToastGroup('❌ ' + S('msg','network_error')); }
}

function showToastGroup(msg) {
  const t = document.getElementById('toast-group');
  if (!t) return;
  t.textContent = msg; t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2500);
}
function closeGroupModal() {
  document.getElementById('group-modal').classList.remove('open');
}

async function saveGroup() {
  const name  = (document.getElementById('g-name').value || '').trim();
  const habit = (document.getElementById('g-habit').value || '').trim();
  const time  = document.getElementById('g-time').value || 'vaqtsiz';
  if (!name)  { showGroupToast(S('msg','grp_enter_name'), true); return; }
  if (!habit) { showGroupToast(S('msg','grp_enter_habit'), true); return; }
  try {
    const res = await fetch(`${API}/groups/${userId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Init-Data': initData, 'X-User-Id': userId },
      body: JSON.stringify({ name, habit_name: habit, habit_time: time })
    });
    const r = await res.json();
    if (!r.ok) throw new Error(r.error);
    closeGroupModal();
    showGroupToast(S('msg','grp_created'));
    if (r.invite_link) {
      setTimeout(() => {
        if (navigator.clipboard) navigator.clipboard.writeText(r.invite_link);
        showGroupToast(S('friends','copy_link'));
      }, 1000);
    }
    loaded.groups = false;
    await loadGroups();
  } catch(e) { showGroupToast(S('msg','error_label') + ': ' + e.message, true); }
}

async function deleteGroup(gid) {
  if (!confirm(S('msg','confirm_del_group'))) return;
  try {
    const res = await fetch(`${API}/groups/${userId}/${gid}`, {
      method: 'DELETE', headers: { 'X-Init-Data': initData, 'X-User-Id': userId }
    });
    const r = await res.json();
    if (!r.ok) throw new Error(r.error);
    showGroupToast(S('msg','grp_deleted'));
    loaded.groups = false;
    await loadGroups();
  } catch(e) { showGroupToast(S('msg','error_label') + ': ' + e.message, true); }
}

function copyInvite(link) {
  if (navigator.clipboard) navigator.clipboard.writeText(link);
  showGroupToast(S('friends','copy_link'));
}

function showGroupToast(msg, err=false) {
  const t = document.getElementById('toast-group');
  if (!t) return;
  t.textContent = msg; t.className = 'toast show' + (err?' err':'');
  setTimeout(() => t.className = 'toast', 2500);
}

async function groupCheckin(gid, btn) {
  if (btn) { btn.disabled = true; btn.textContent = '⏳...'; }
  try {
    const res = await fetch(`${API}/groups/${userId}/${gid}/checkin`, {
      method: 'POST',
      headers: { 'X-Init-Data': initData, 'X-User-Id': userId }
    });
    const r = await res.json();
    if (!r.ok) throw new Error(r.error);
    if (r.done) {
      if (btn) {
        btn.style.background = 'var(--bg)';
        btn.style.color = 'var(--green)';
        btn.style.boxShadow = 'var(--sh-in)';
        btn.textContent = S('msg','grp_done_btn');
      }
      showGroupToast(S('msg','grp_checkin').replace('{pts}','5').replace('{streak}', r.streak || 1) + (r.all_done ? S('msg','grp_all_done') : ''));
      loaded.today = false;
      if (r.points !== undefined) {
        const ptsEl = document.getElementById('header-pts');
        if (ptsEl) ptsEl.textContent = '⭐ ' + r.points;
      }
    } else {
      if (btn) {
        btn.style.background = 'linear-gradient(135deg,#10B981,#047857)';
        btn.style.color = '#fff';
        btn.style.boxShadow = '';
        btn.textContent = S('msg','grp_do_btn');
      }
      showGroupToast(S('msg','grp_undone'));
      if (r.points !== undefined) {
        const ptsEl = document.getElementById('header-pts');
        if (ptsEl) ptsEl.textContent = '⭐ ' + r.points;
      }
    }
  } catch(e) {
    showGroupToast('❌ ' + (e.message || S('msg','error_label')), true);
    if (btn) { btn.disabled = false; btn.textContent = S('msg','grp_do_btn'); }
  } finally {
    if (btn) btn.disabled = false;
  }
}

// ── STATISTIKA SUB-TAB ──
let _statSub = 'stats';
let _friendsLoaded = false;

function setStatSub(sub) {
  _statSub = sub;
  ['stats','rating','friends'].forEach(s => {
    document.getElementById('ssub-' + s)?.classList.toggle('active', sub === s);
    document.getElementById('ssub-panel-' + s).style.display = sub === s ? '' : 'none';
  });
  if (sub === 'rating') {
    loadRating();
  }
  if (sub === 'friends' && !_friendsLoaded) {
    _friendsLoaded = true;
    loadGroups();
    loadFriends();
  }
}

// ── DO'STLAR ──
let _groupSub = 'groups';
function setGroupSub(sub) {
  _groupSub = sub;
  ['groups','friends'].forEach(s => {
    document.getElementById('gsub-'+s)?.classList.toggle('active', sub === s);
    const el = document.getElementById(s+'-content');
    if (el) el.style.display = sub === s ? '' : 'none';
  });
}

async function loadFriends() {
  try {
    const [d, ch] = await Promise.all([
      apiFetch(`friends/${userId}`),
      apiFetch(`challenges/${userId}`).catch((e) => { console.warn('[challenges] yuklanmadi:', e); return { received: [] }; })
    ]);
    d._received_challenges = ch.received || [];
    renderFriends(d);
  } catch(e) {
    document.getElementById('friends-content').innerHTML =
      `<div class="empty-state"><div class="icon"><svg width="28" height="28" viewBox="0 0 24 24" fill="none"><defs><linearGradient id="svgWarn" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#FBBF24"/><stop offset="100%" stop-color="#F59E0B"/></linearGradient></defs><path d="M12 3L2 21h20L12 3z" stroke="url(#svgWarn)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/><path d="M12 10v5M12 17.5v.5" stroke="url(#svgWarn)" stroke-width="2" stroke-linecap="round"/></svg></div>${S('msg','data_error')}.</div>`;
  }
}

function renderFriends(d) {
  const friends = d.friends || [];
  const pending = (d._received_challenges || []).filter(c => c.status === 'pending');

  // ── Kiruvchi challengelar panel ──
  let challHtml = '';
  if (pending.length > 0) {
    const rows = pending.map(c => `
      <div style="background:var(--bg);border-radius:12px;padding:10px 12px;margin-bottom:8px;box-shadow:var(--sh-sm)">
        <div style="font-size:13px;font-weight:700;color:var(--text);margin-bottom:2px">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" style="display:inline;vertical-align:middle;margin-right:4px"><defs><linearGradient id="svgTgtCh" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#34D399"/><stop offset="100%" stop-color="#059669"/></linearGradient></defs><circle cx="12" cy="12" r="9" stroke="url(#svgTgtCh)" stroke-width="2"/><circle cx="12" cy="12" r="5" stroke="url(#svgTgtCh)" stroke-width="2"/><circle cx="12" cy="12" r="2" fill="url(#svgTgtCh)"/></svg>${S('msg','ch_challenged').replace('{name}', c.from_name)}
        </div>
        <div style="font-size:11px;color:var(--sub);margin-bottom:8px">${S('msg','ch_info_line').replace('{habit}',c.habit_name).replace('{days}',c.days).replace('{bet}',c.bet)}</div>
        <div style="display:flex;gap:8px">
          <button onclick="acceptChallenge('${c.id}')" type="button"
            style="flex:1;padding:8px;border:none;border-radius:10px;background:linear-gradient(135deg,#10B981,#047857);color:#fff;font-size:12px;font-weight:700;cursor:pointer">
            ${S('msg','ch_accept')}
          </button>
          <button onclick="rejectChallenge('${c.id}')" type="button"
            style="flex:1;padding:8px;border:none;border-radius:10px;background:var(--bg);color:var(--sub);font-size:12px;font-weight:600;cursor:pointer;box-shadow:var(--sh-sm)">
            ${S('msg','ch_reject')}
          </button>
        </div>
      </div>`).join('');
    challHtml = `
      <div class="rem-card" style="margin-bottom:8px">
        <div style="font-size:12px;font-weight:700;color:var(--accent);margin-bottom:8px">${S('msg','challenge_incoming')} (${pending.length})</div>
        ${rows}
      </div>`;
  }
  const emptyFriendsHtml = '<div class="empty-state"><div class="icon">\uD83E\uDD1D</div>' + S('friends','empty') + '</div>';
  let html = '';
  friends.forEach(f => {
    const mutualColor = f.mutual_streak >= 7 ? '#10B981' : f.mutual_streak >= 3 ? '#059669' : '#059669';
    html += `
      <div class="rem-card">
        <div class="rem-top">
          <div class="rem-icon" style="font-size:28px">${f.name[0]?.toUpperCase() || '?'}</div>
          <div style="flex:1">
            <div style="font-size:14px;font-weight:700;color:var(--text)">${f.name}</div>
            <div style="font-size:11px;color:var(--sub);margin-top:2px">⭐ ${f.points} ${S('friends','points_label')} · <svg width="13" height="13" viewBox="0 0 20 20" fill="none" style="display:inline;vertical-align:middle"><defs><linearGradient id="gFireF" x1="0" y1="0" x2="20" y2="20" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#34D399"/><stop offset="100%" stop-color="#059669"/></linearGradient></defs><path d="M10 2C10 2 14 6 14 10C14 12 13 13.5 11.5 14.5C12 13 11.5 11.5 10.5 11C11 13 9.5 15 8 15.5C9 14 8.5 12 7 11C5.5 12.5 6 15 7 16.5C5.5 15.5 4 13.5 4 11C4 7 8 4 10 2Z" fill="url(#gFireF)"/></svg> ${f.streak} ${S('friends','streak_label')}</div>
          </div>
          <div style="text-align:center">
            <div style="font-size:11px;color:var(--sub)">${S('friends','mutual_streak')}</div>
            <div style="font-size:18px;font-weight:700;color:${mutualColor};font-family:'DM Mono',monospace">${f.mutual_streak}</div>
            <div style="font-size:9px;color:var(--sub)">${S('msg','friend_streak_day')} <svg width="13" height="13" viewBox="0 0 20 20" fill="none" style="display:inline;vertical-align:middle"><defs><linearGradient id="svgFire" x1="10" y1="0" x2="10" y2="20" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#34D399"/><stop offset="100%" stop-color="#059669"/></linearGradient></defs><path d="M10 2C10 2 14 6 14 10C14 12 13 13.5 11.5 14.5C12 13 11.5 11.5 10.5 11C11 13 9.5 15 8 15.5C9 14 8.5 12 7 11C5.5 12.5 6 15 7 16.5C5.5 15.5 4 13.5 4 11C4 7 8 4 10 2Z" fill="url(#svgFire)"/></svg></div>
          </div>
        </div>
        <div style="display:flex;align-items:center;gap:8px;margin-top:8px">
          <div style="flex:1;height:6px;border-radius:3px;background:var(--bg);box-shadow:var(--sh-in);overflow:hidden">
            <div style="height:100%;border-radius:3px;background:${f.done_today?'var(--green)':'#059669'};width:${f.done_today?100:0}%"></div>
          </div>
          <span style="font-size:10px;color:var(--sub)">${f.done_today ? S('msg','done_today') : S('msg','not_done_today')}</span>
        </div>
        <div style="display:flex;gap:6px;margin-top:10px">
          <button class="rem-save-btn" style="flex:1" onclick="openChallenge(${f.id},'${f.name}')" type="button"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" style="display:inline;vertical-align:middle;margin-right:5px"><defs><linearGradient id="svgTgtBtn" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#34D399"/><stop offset="100%" stop-color="#059669"/></linearGradient></defs><circle cx="12" cy="12" r="9" stroke="url(#svgTgtBtn)" stroke-width="2"/><circle cx="12" cy="12" r="5" stroke="url(#svgTgtBtn)" stroke-width="2"/><circle cx="12" cy="12" r="2" fill="url(#svgTgtBtn)"/></svg>${S('friends','challenge')}</button>
          <button class="rem-save-btn" style="flex:1;background:var(--bg);color:var(--sub);box-shadow:var(--sh-in)" onclick="removeFriend(${f.id})" type="button"><svg width="12" height="12" viewBox="0 0 20 20" fill="none" style="display:inline;vertical-align:middle;margin-right:4px"><line x1="15" y1="5" x2="5" y2="15" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/><line x1="5" y1="5" x2="15" y2="15" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/></svg>${S('friends','remove')}</button>
        </div>
      </div>`;
  });

  document.getElementById('friends-content').innerHTML = challHtml + `
    <div class="rem-card">
      <div style="font-size:13px;font-weight:700;color:var(--text);margin-bottom:8px">🔍 ${S('msg','friend_search')}</div>
      <div style="display:flex;gap:8px">
        <input id="friend-search-inp" type="text" placeholder="${S('msg','search_placeholder')}" maxlength="30"
          style="flex:1;padding:8px 12px;border-radius:10px;border:none;background:var(--bg);box-shadow:var(--sh-in);color:var(--text);font-size:13px;outline:none"
          oninput="onFriendSearchInput(this.value)">
        <button class="rem-save-btn" style="padding:8px 14px" onclick="searchFriends()" type="button">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" style="display:inline;vertical-align:middle"><circle cx="11" cy="11" r="7" stroke="#fff" stroke-width="2"/><path d="M20 20l-3-3" stroke="#fff" stroke-width="2" stroke-linecap="round"/></svg>
        </button>
      </div>
      <div id="friend-search-results" style="margin-top:8px"></div>
    </div>
    <div class="rem-card" style="background:linear-gradient(135deg,#05966922,#10B98122)">
      <div style="display:flex;align-items:center;gap:12px">
        <div style="display:flex;justify-content:center"><svg width="36" height="36" viewBox="0 0 40 40" fill="none"><defs><linearGradient id="svgInvLg" x1="0" y1="0" x2="40" y2="40" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#10B981"/><stop offset="100%" stop-color="#059669"/></linearGradient><linearGradient id="svgInvHt" x1="0" y1="0" x2="20" y2="20" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#34D399"/><stop offset="100%" stop-color="#059669"/></linearGradient></defs><circle cx="13" cy="11" r="4" fill="url(#svgInvLg)" opacity="0.85"/><circle cx="27" cy="11" r="4" fill="url(#svgInvLg)" opacity="0.6"/><path d="M3 28c0-5.5 4.5-10 10-10h4" stroke="url(#svgInvLg)" stroke-width="2.2" stroke-linecap="round" fill="none"/><path d="M37 28c0-5.5-4.5-10-10-10h-4" stroke="url(#svgInvLg)" stroke-width="2.2" stroke-linecap="round" fill="none" opacity="0.7"/><path d="M20 20c0-1.1-.4-2.1-1-2.8a3 3 0 00-4.2 0 3 3 0 000 4.2L20 27l5.2-5.6a3 3 0 000-4.2 3 3 0 00-4.2 0c-.6.7-1 1.7-1 2.8z" fill="url(#svgInvHt)" opacity="0.9"/></svg></div>
        <div style="flex:1">
          <div style="font-size:13px;font-weight:700;color:var(--text)">${S('msg','friend_invite')}</div>
          <div style="font-size:11px;color:var(--sub);margin-top:3px">${S('friends','link_hint')}</div>
        </div>
      </div>
      <button class="rem-save-btn" style="margin-top:12px" onclick="copyFriendLink('${d.invite_link}')" type="button">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" style="display:inline;vertical-align:middle;margin-right:4px"><defs><linearGradient id="svgLnkSm" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#059669"/><stop offset="100%" stop-color="#10B981"/></linearGradient></defs><path d="M10 14a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71" stroke="url(#svgLnkSm)" stroke-width="2" stroke-linecap="round"/><path d="M14 10a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71" stroke="url(#svgLnkSm)" stroke-width="2" stroke-linecap="round"/></svg>${S('msg','copy_invite')}
      </button>
    </div>
    <div class="section-title">${S('msg','friend_list').replace('{n}', friends.length)}</div>
    ${html || emptyFriendsHtml}
    <div class="toast" id="toast-friends"></div>`;
}

function copyFriendLink(link) {
  if (!link) return;
  if (navigator.clipboard) navigator.clipboard.writeText(link);
  const t = document.getElementById('toast-friends');
  if (t) { t.textContent = S('friends','copy_link'); t.className = 'toast show'; setTimeout(()=>t.className='toast',2500); }
}

function copyRefLink(link) {
  if (!link) return;
  if (navigator.clipboard) navigator.clipboard.writeText(link);
  showToast(S('friends','copy_link'));
}

async function removeFriend(fid) {
  if (!confirm(S('msg','confirm_friend'))) return;
  try {
    await fetch(`${API}/friends/${userId}/remove/${fid}`, {
      method: 'DELETE', headers: { 'X-Init-Data': initData, 'X-User-Id': userId }
    });
    await loadFriends();
  } catch(e) { showToast(S('friends','error'), true); }
}

// ── FRIEND SEARCH ──
let _friendSearchTimer = null;
function onFriendSearchInput(val) {
  clearTimeout(_friendSearchTimer);
  if (val.trim().length < 2) {
    document.getElementById('friend-search-results').innerHTML = '';
    return;
  }
  _friendSearchTimer = setTimeout(() => searchFriends(), 500);
}

async function searchFriends() {
  const inp = document.getElementById('friend-search-inp');
  if (!inp) return;
  const q = inp.value.trim();
  if (q.length < 2) return;
  const resEl = document.getElementById('friend-search-results');
  resEl.innerHTML = '<div style="font-size:12px;color:var(--sub);text-align:center;padding:8px">' + S('friends','searching') + '</div>';
  try {
    const d = await apiFetch(`friends/${userId}/search?q=${encodeURIComponent(q)}`);
    const results = d.results || [];
    if (!results.length) {
      resEl.innerHTML = '<div style="font-size:12px;color:var(--sub);text-align:center;padding:8px">' + S('friends','not_found') + '</div>';
      return;
    }
    resEl.innerHTML = results.map(r => `
      <div style="display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid var(--bg)">
        ${r.photo
          ? `<img src="${r.photo}" style="width:34px;height:34px;border-radius:50%;object-fit:cover;flex-shrink:0">`
          : `<div style="width:34px;height:34px;border-radius:50%;background:linear-gradient(135deg,#059669,#10B981);display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:14px;font-weight:700;color:#fff">${(r.name[0]||'?').toUpperCase()}</div>`}
        <div style="flex:1;min-width:0">
          <div style="font-size:13px;font-weight:700;color:var(--text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${r.name}${r.username ? ' <span style="font-size:10px;color:var(--sub)">@'+r.username+'</span>' : ''}</div>
          <div style="font-size:10px;color:var(--sub)">⭐ ${r.points} · 🔥 ${S('msg','streak_days').replace('{n}',r.streak)}</div>
        </div>
        ${r.is_friend
          ? "<div style=\"font-size:10px;color:var(--green);font-weight:600;flex-shrink:0\">" + S('msg','friend_badge') + "</div>"
          : `<button class="rem-save-btn" style="padding:5px 12px;font-size:11px;flex-shrink:0" onclick="addFriend(${r.id},'${r.name.replace(/'/g,"\'")}',this)" type="button">${S('msg','add_friend_btn')}</button>`}
      </div>`).join('');
  } catch(e) {
    resEl.innerHTML = '<div style="font-size:12px;color:#059669;text-align:center;padding:8px">' + S('friends','error') + '</div>';
  }
}

async function addFriend(fid, fname, btn) {
  if (btn) { btn.disabled = true; btn.textContent = '...'; }
  try {
    const d = await apiFetch(`friends/${userId}/add/${fid}`, { method: 'POST' });
    if (d.ok) {
      if (btn) { btn.textContent = S('msg','friend_badge'); btn.style.background = 'var(--green)'; }
      showToast(S('msg','friend_added').replace('{name}', fname));
      loaded.achievements = false;
    } else {
      if (btn) { btn.disabled = false; btn.textContent = S('msg','add_friend_btn'); }
      showToast(d.error || S('msg','error_label'), true);
    }
  } catch(e) {
    if (btn) { btn.disabled = false; btn.textContent = S('msg','add_friend_btn'); }
    showToast(S('friends','error'), true);
  }
}

// ── SHOP ──
let _shopData = null;
let _shopContentId = 'bozor-content';
let _shopCat  = 'all';

async function loadShop() {
  try {
    const d = await apiFetch(`shop/${userId}`);
    _shopData = d;
    renderShop(d);
  } catch(e) {
    document.getElementById('bozor-content').innerHTML =
      `<div class="empty-state"><div class="icon"><svg width="28" height="28" viewBox="0 0 24 24" fill="none"><defs><linearGradient id="svgWarn" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#FBBF24"/><stop offset="100%" stop-color="#F59E0B"/></linearGradient></defs><path d="M12 3L2 21h20L12 3z" stroke="url(#svgWarn)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/><path d="M12 10v5M12 17.5v.5" stroke="url(#svgWarn)" stroke-width="2" stroke-linecap="round"/></svg></div>${S('msg','data_error')}</div>`;
  }
}

function renderShop(d) {
  const items    = (d.items || []);
  const points   = d.points || 0;
  const inventory = d.inventory || {};

  // Inventory bo'limi — faqat sotib olinganlar
  const owned_items = items.filter(i => (i.owned || 0) > 0 || (inventory[i.id] || 0) > 0);
  const activePet   = d.active_pet   || '';
  const activeBadge = d.active_badge || '';
  const activeCar   = d.active_car   || '';

  let invHtml = '';
  if (owned_items.length > 0) {
    const invCards = owned_items.map(item => {
      const qty     = item.owned || inventory[item.id] || 0;
      const canAct  = ['pet','badge','car'].includes(item.cat);
      const isActive = (item.cat==='pet' && activePet===item.id)
                    || (item.cat==='badge' && activeBadge===item.id)
                    || (item.cat==='car' && activeCar===item.id);
      const _sellPrices = {badge_fire:100,badge_star:125,badge_secret:300,pet_cat:150,pet_dog:175,pet_rabbit:150,car_sport:250,shield_1:50,shield_3:125,bonus_2x:75,bonus_3x:150,xp_booster:200};
      const sellRefund = _sellPrices[item.id] || 0;
      return `<div style="display:flex;align-items:center;gap:10px;padding:10px 14px;
        background:var(--bg);border-radius:14px;box-shadow:${isActive?'0 0 0 2px #10B981':'var(--sh-sm)'};margin-bottom:6px">
        <div style="font-size:28px;line-height:1">${item.emoji}</div>
        <div style="flex:1;min-width:0">
          <div style="font-size:13px;font-weight:700;color:var(--text)">${item.name}</div>
          <div style="font-size:10px;color:var(--sub);margin-top:1px">${qty} ${S('shop','items_unit')}${sellRefund ? ' · <span style="color:#059669">' + S('msg','sell_price').replace('{n}', sellRefund) + '</span>' : ''}</div>
        </div>
        ${isActive
          ? `<button onclick="activateItem('${item.id}', true)" type="button"
              style="padding:6px 12px;border:none;border-radius:10px;font-size:11px;font-weight:700;
                cursor:pointer;background:#10B98122;color:#10B981">
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" style="display:inline;vertical-align:middle;margin-right:3px"><path d="M7 12l4 4 6-7" stroke="#10B981" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>${S('shop','active_label')}
            </button>`
          : canAct
            ? `<button onclick="activateItem('${item.id}')" type="button"
                style="padding:6px 12px;border:none;border-radius:10px;font-size:11px;font-weight:700;
                  cursor:pointer;background:var(--bg);box-shadow:var(--sh-sm);color:var(--text)">
                ${S('shop','activate_btn')}
              </button>`
            : `<div style="font-size:10px;color:var(--sub)">${item.cat==='protection'?`<svg width="13" height="13" viewBox="0 0 24 24" fill="none" style="display:inline;vertical-align:middle;margin-right:3px"><defs><linearGradient id="svgShSm" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#059669"/><stop offset="100%" stop-color="#34D399"/></linearGradient></defs><path d="M12 3L4 7v5c0 5 4 9 8 10 4-1 8-5 8-10V7L12 3z" fill="url(#svgShSm)" opacity="0.85"/></svg>${S('shop','protection')}`:item.cat==='bonus'?`<svg width="13" height="13" viewBox="0 0 24 24" fill="none" style="display:inline;vertical-align:middle;margin-right:3px"><defs><linearGradient id="svgBtSm" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#34D399"/><stop offset="100%" stop-color="#059669"/></linearGradient></defs><path d="M13 2L4 14h7l-1 8 9-12h-7l1-8z" fill="url(#svgBtSm)"/></svg>${S('shop','bonus')}`:(`<svg width="13" height="13" viewBox="0 0 24 24" fill="none" style="display:inline;vertical-align:middle;margin-right:3px"><defs><linearGradient id="svgGift" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#34D399"/><stop offset="100%" stop-color="#34D399"/></linearGradient></defs><rect x="3" y="10" width="18" height="12" rx="2" stroke="url(#svgGift)" stroke-width="2"/><path d="M3 10h18v3H3zM12 10V22M12 10c0 0-2-5 0-7 1-1 3-1 3 1s-2 3-3 6M12 10c0 0 2-5 0-7-1-1-3-1-3 1s2 3 3 6" stroke="url(#svgGift)" stroke-width="1.5" stroke-linecap="round"/></svg>${S('shop','gift')}`)}</div>`
        }
        ${sellRefund ? `<button onclick="sellItem('${item.id}', '${item.name}', ${sellRefund})" type="button"
          style="padding:5px 10px;border:none;border-radius:10px;font-size:10px;font-weight:700;
            cursor:pointer;background:#EF444418;color:#EF4444;white-space:nowrap;flex-shrink:0">
          💰 ${S('msg','sell_title')}
        </button>` : ''}
      </div>`;
    }).join('');
    invHtml = `
      <div class="section-title"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" style="display:inline;vertical-align:middle;margin-right:5px"><defs><linearGradient id="svgBox" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#10B981"/><stop offset="100%" stop-color="#059669"/></linearGradient></defs><path d="M3 9l9-6 9 6v12a1 1 0 01-1 1H4a1 1 0 01-1-1V9z" stroke="url(#svgBox)" stroke-width="2" stroke-linejoin="round"/><path d="M9 21V12h6v9" stroke="url(#svgBox)" stroke-width="2" stroke-linecap="round"/></svg> ${S('shop','inventory')}</div>
      ${invCards}`;
  }

  const visItems = items.filter(i => _shopCat === 'all' || i.cat === _shopCat);
  const cats = [
    ['all',S('bozor','all')],['protection','<svg width="13" height="13" viewBox="0 0 24 24" fill="none" style="display:inline;vertical-align:middle;margin-right:3px"><defs><linearGradient id="svgShSm" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#059669"/><stop offset="100%" stop-color="#34D399"/></linearGradient></defs><path d="M12 3L4 7v5c0 5 4 9 8 10 4-1 8-5 8-10V7L12 3z" fill="url(#svgShSm)" opacity="0.85"/></svg>'+S('bozor','protection')],['bonus','<svg width="13" height="13" viewBox="0 0 24 24" fill="none" style="display:inline;vertical-align:middle;margin-right:3px"><defs><linearGradient id="svgBtSm" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#34D399"/><stop offset="100%" stop-color="#059669"/></linearGradient></defs><path d="M13 2L4 14h7l-1 8 9-12h-7l1-8z" fill="url(#svgBtSm)"/></svg>'+S('bozor','bonus')],
    ['badge','🏅 '+S('shop','cat_badge')],['pet','🐾 '+S('shop','cat_pet')],['car','🚗 '+S('shop','cat_car')],['gift',[S('shop','gift')]]
  ];
  const catBtns = cats.map(([k,l]) =>
    `<button onclick="setShopCat('${k}')" class="period-btn${_shopCat===k?' active':''}"
      style="font-size:11px;padding:6px 10px" type="button">${l}</button>`
  ).join('');

  let html = visItems.map(item => {
    const hasBall  = item.price_ball  > 0;
    const hasStars = item.price_stars > 0;
    const cantBuy  = !item.can_buy;
    const noMoney  = hasBall && points < item.price_ball;

    return `<div class="rem-card" style="position:relative${cantBuy?';opacity:.6':''}">
      <div style="display:flex;align-items:flex-start;gap:12px">
        <div style="font-size:36px;line-height:1">${item.emoji}</div>
        <div style="flex:1">
          <div style="font-size:14px;font-weight:700;color:var(--text)">${item.name}</div>
          <div style="font-size:11px;color:var(--sub);margin-top:3px;line-height:1.4">${item.desc}</div>
          ${item.owned > 0 ? `<div style="font-size:10px;color:var(--green);margin-top:4px"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" style="display:inline;vertical-align:middle;margin-right:3px"><defs><linearGradient id="svgChkI" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#10B981"/><stop offset="100%" stop-color="#047857"/></linearGradient></defs><circle cx="12" cy="12" r="9" fill="url(#svgChkI)" opacity="0.15"/><path d="M7 12l4 4 6-7" stroke="url(#svgChkI)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>${S('shop','you_have')} ${item.owned} ${S('shop','items_unit')}</div>` : ''}
        </div>
      </div>
      <div style="margin-top:10px">
        ${hasBall ? `
          ${!cantBuy ? `<div style="width:100%;background:var(--bg);border-radius:8px;overflow:hidden;margin-bottom:6px;box-shadow:var(--sh-in)">
            <div style="height:6px;border-radius:8px;background:linear-gradient(90deg,#059669,#10B981);width:${Math.min(100,Math.round(points/item.price_ball*100))}%;transition:width .4s"></div>
          </div>` : ''}
          <button onclick="buyItem('${item.id}','ball')" ${cantBuy||noMoney?'disabled':''} type="button"
          style="width:100%;padding:9px 6px;border:none;border-radius:10px;font-size:12px;font-weight:700;cursor:${cantBuy||noMoney?'not-allowed':'pointer'};
          background:${cantBuy?'var(--bg)':noMoney?'var(--bg)':'linear-gradient(135deg,#059669,#10B981)'};
          color:${cantBuy||noMoney?'var(--sub)':'#fff'};box-shadow:${cantBuy||noMoney?'var(--sh-in)':'none'}">
          ${cantBuy?'<svg width="13" height="13" viewBox="0 0 24 24" fill="none" style="display:inline;vertical-align:middle;margin-right:3px"><defs><linearGradient id="svgChkI" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#10B981"/><stop offset="100%" stop-color="#047857"/></linearGradient></defs><circle cx="12" cy="12" r="9" fill="url(#svgChkI)" opacity="0.15"/><path d="M7 12l4 4 6-7" stroke="url(#svgChkI)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>'+S('shop','already_bought'):'⭐ '+item.price_ball+' '+S('shop','points_unit')}
        </button>` : ''}
        ${hasStars ? `<button onclick="buyItem('${item.id}','stars')" ${cantBuy?'disabled':''} type="button"
          style="flex:1;padding:9px 6px;border:none;border-radius:10px;font-size:12px;font-weight:700;cursor:${cantBuy?'not-allowed':'pointer'};
          background:${cantBuy?'var(--bg)':'linear-gradient(135deg,#34D399,#059669)'};
          color:${cantBuy?'var(--sub)':'#fff'};box-shadow:${cantBuy?'var(--sh-in)':'none'}">
          ${cantBuy?'<svg width="13" height="13" viewBox="0 0 24 24" fill="none" style="display:inline;vertical-align:middle;margin-right:3px"><defs><linearGradient id="svgChkI" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#10B981"/><stop offset="100%" stop-color="#047857"/></linearGradient></defs><circle cx="12" cy="12" r="9" fill="url(#svgChkI)" opacity="0.15"/><path d="M7 12l4 4 6-7" stroke="url(#svgChkI)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>'+S('shop','already_bought'):'⭐ '+item.price_stars+' Stars'}
        </button>` : ''}
      </div>
    </div>`;
  }).join('');

  document.getElementById(_shopContentId || 'shop-content').innerHTML = `
    <div style="background:linear-gradient(135deg,#05966922,#10B98122);border-radius:16px;padding:14px 16px;margin-bottom:4px;display:flex;align-items:center;gap:10px">
      <div style="font-size:28px">⭐</div>
      <div>
        <div style="font-size:11px;color:var(--sub)">${S('shop','your_points')}</div>
        <div style="font-size:22px;font-weight:700;color:var(--text)">${points.toLocaleString()} ${S('shop','points_unit')}</div>
      </div>
    </div>
    ${invHtml}
    <div class="section-title"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" style="display:inline;vertical-align:middle;margin-right:5px"><defs><linearGradient id="svgCart2" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#10B981"/><stop offset="100%" stop-color="#047857"/></linearGradient></defs><path d="M2 3h2.5L7 15H19L21 7H5.5" stroke="url(#svgCart2)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><circle cx="9" cy="19" r="2" fill="url(#svgCart2)"/><circle cx="17" cy="19" r="2" fill="url(#svgCart2)"/></svg> ${S('shop','shop_title')}</div>
    <div style="display:flex;gap:6px;overflow-x:auto;padding:4px 0 8px;scrollbar-width:none">${catBtns}</div>
    ${html || '<div class="empty-state"><div class="icon"><svg width="28" height="28" viewBox="0 0 24 24" fill="none"><defs><linearGradient id="svgCartEm" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#10B981"/><stop offset="100%" stop-color="#047857"/></linearGradient></defs><path d="M2 3h2.5L7 15H19L21 7H5.5" stroke="url(#svgCartEm)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><circle cx="9" cy="19" r="2" fill="url(#svgCartEm)"/><circle cx="17" cy="19" r="2" fill="url(#svgCartEm)"/></svg></div>'+S('shop','empty_cat')+'</div>'}
    <div class="toast" id="toast-shop"></div>`;
}

function setShopCat(cat) {
  _shopCat = cat;
  if (_shopData) renderShop(_shopData);
}

async function buyItem(itemId, method) {
  if (method === 'stars') {
    try {
      const res = await fetch(`${API}/shop/${userId}/stars_invoice`, {
        method: 'POST',
        headers: {'Content-Type':'application/json','X-Init-Data':initData,'X-User-Id':userId},
        body: JSON.stringify({ item_id: itemId })
      });
      const r = await res.json();
      const toast = document.getElementById('toast-shop');
      if (!r.ok) {
        if (toast) { toast.textContent = '❌ ' + (r.error || S('msg','error_label')); toast.className = 'toast show'; setTimeout(()=>toast.className='toast',3000); }
      } else {
        if (toast) { toast.textContent = '⭐ ' + S('msg','payment_opened'); toast.className = 'toast show'; setTimeout(()=>toast.className='toast',3500); }
      }
    } catch(e) {
      showToast('❌ ' + S('msg','network_error'), true);
    }
    return;
  }
  try {
    const res = await fetch(`${API}/shop/${userId}/buy`, {
      method: 'POST',
      headers: {'Content-Type':'application/json','X-Init-Data':initData,'X-User-Id':userId},
      body: JSON.stringify({ item_id: itemId, method })
    });
    const r = await res.json();
    if (!r.ok) { showToast('❌ ' + (r.error || S('msg','error_label')), true); return; }
    // Ma'lumotlarni yangilash
    if (_shopData) {
      _shopData.points = r.points;
      const item = _shopData.items.find(i => i.id === itemId);
      if (item) { item.owned = r.owned; item.can_buy = item.owned < item.max_own; }
      renderShop(_shopData);
    }
    // Global profil balini ham yangilash (boshqa sahifalarda koʻrinishi uchun)
    if (data.profile && typeof r.points === 'number') {
      data.profile.points = r.points;
    }
    // Profil cache tozalash — keyingi ochilishda yangi ball koʻrinadi
    loaded.profile = false;
    const toast = document.getElementById('toast-shop');
    if (toast) { toast.textContent = S('shop','buy_success'); toast.className = 'toast show'; setTimeout(()=>toast.className='toast',2500); }
  } catch(e) { showToast('❌ ' + S('msg','network_error'), true); }
}

async function sellItem(itemId, itemName, refund) {
  // confirm() Telegram WebApp da ishlamaydi — showPopup ishlatamiz
  const _doSell = async () => {
  try {
    // apiFetch !res.ok da throw qiladi, shuning uchun to'g'ridan fetch ishlatamiz
    const res = await fetch(`${API}/shop/${userId}/sell`, {
      method: 'POST',
      headers: {'Content-Type':'application/json','X-Init-Data':initData,'X-User-Id':userId},
      body: JSON.stringify({item_id: itemId})
    });
    const r = await res.json().catch(() => ({}));
    const _toast = document.getElementById('toast-shop');
    if (!res.ok || r.ok === false) {
      if (_toast) { _toast.textContent = '❌ ' + (r.error || S('msg','error_label')); _toast.className = 'toast show err'; setTimeout(()=>_toast.className='toast',3000); }
      return;
    }
    if (_toast) { _toast.textContent = S('msg','sold_toast').replace('{n}', r.refund); _toast.className = 'toast show'; setTimeout(()=>_toast.className='toast',2500); }
    if (_shopData) {
      _shopData.points = r.points;
      // Global profil balini ham yangilash
      if (data.profile && typeof r.points === 'number') {
        data.profile.points = r.points;
      }
      // Profil cache tozalash — keyingi ochilishda yangi ball koʻrinadi
      loaded.profile = false;
      // inventory dict narsalari
      const inv = _shopData.inventory || {};
      if (inv[itemId] > 1) inv[itemId]--;
      else delete inv[itemId];
      // counter fieldlar (shield/bonus/xp)
      if (itemId === 'shield_1' || itemId === 'shield_3') {
        const item = (_shopData.items || []).find(i => i.id === itemId);
        if (item) item.owned = Math.max(0, (item.owned || 1) - 1);
      }
      if (itemId === 'bonus_2x') _shopData.bonus_2x_active = false;
      if (itemId === 'bonus_3x') _shopData.bonus_3x_active = false;
      if (itemId === 'xp_booster') {
        const item = (_shopData.items || []).find(i => i.id === 'xp_booster');
        if (item) item.owned = 0;
      }
      // aktiv deaktivatsiya
      if (itemId.startsWith('pet_'))   _shopData.active_pet   = _shopData.active_pet   === itemId ? '' : _shopData.active_pet;
      if (itemId.startsWith('badge_')) _shopData.active_badge = _shopData.active_badge === itemId ? '' : _shopData.active_badge;
      if (itemId.startsWith('car_'))   _shopData.active_car   = _shopData.active_car   === itemId ? '' : _shopData.active_car;
      renderShop(_shopData);
    }
  } catch(e) {
    const _t = document.getElementById('toast-shop');
    if (_t) { _t.textContent = '❌ ' + S('msg','error_label') + ': ' + e.message; _t.className = 'toast show err'; setTimeout(()=>_t.className='toast',3000); }
  }
  };
  if (window.Telegram?.WebApp?.showPopup) {
    window.Telegram.WebApp.showPopup({
      title: S('msg','sell_title'),
      message: S('msg','sell_confirm').replace('{name}', itemName).replace('{n}', refund),
      buttons: [{id:'ok', type:'ok'}, {id:'cancel', type:'cancel'}]
    }, (btnId) => { if (btnId === 'ok') _doSell(); });
  } else {
    if (confirm(S('msg','sell_confirm').replace('{name}', itemName).replace('{n}', refund))) _doSell();
  }
}

async function activateItem(itemId, deactivate = false) {
  try {
    const res = await fetch(`${API}/shop/${userId}/activate`, {
      method: 'POST',
      headers: {'Content-Type':'application/json','X-Init-Data':initData,'X-User-Id':userId},
      body: JSON.stringify({ item_id: itemId, deactivate: deactivate })
    });
    const r = await res.json();
    if (!r.ok) { showToast('❌ ' + (r.error || S('msg','error_label')), true); return; }
    // Local state yangilash
    if (_shopData) {
      const item = _shopData.items.find(i => i.id === itemId);
      if (item) {
        if (item.cat === 'pet')   _shopData.active_pet   = deactivate ? '' : itemId;
        if (item.cat === 'badge') _shopData.active_badge = deactivate ? '' : itemId;
        if (item.cat === 'car')   _shopData.active_car   = deactivate ? '' : itemId;
      }
      renderShop(_shopData);
    }
    const toast = document.getElementById('toast-shop');
    const msg = deactivate ? S('shop','deactivate_success') : S('shop','activate_success');
    if (toast) { toast.textContent = msg; toast.className = 'toast show'; setTimeout(()=>toast.className='toast',2000); }
  } catch(e) { showToast('❌ ' + S('msg','network_error'), true); }
}

// ── CHALLENGE ──
function openChallenge(fid, fname) {
  document.getElementById('ch-receiver-id').value  = fid;
  document.getElementById('ch-receiver-name').textContent = fname;
  const _m = (id, k) => { const el = document.getElementById(id); if (el) el.textContent = S('msg', k); };
  _m('ch-lbl-title', 'ch_title');
  _m('ch-lbl-opponent', 'ch_opponent');
  _m('ch-lbl-habit', 'ch_habit_name');
  _m('ch-lbl-duration', 'ch_duration');
  _m('ch-lbl-bet', 'ch_bet');
  _m('ch-lbl-info', 'ch_bet_info');
  _m('ch-lbl-send', 'ch_send_btn');
  const chInput = document.getElementById('ch-habit');
  if (chInput) chInput.placeholder = S('msg','ph_habit_name');
  document.getElementById('challenge-modal').classList.add('open');
}
function closeChallengeModal() {
  document.getElementById('challenge-modal').classList.remove('open');
}

async function sendChallenge() {
  const fid       = document.getElementById('ch-receiver-id').value;
  const habitName = (document.getElementById('ch-habit').value || '').trim();
  const days      = parseInt(document.getElementById('ch-days').value) || 7;
  const bet       = parseInt(document.getElementById('ch-bet').value) || 50;
  const btn       = document.getElementById('ch-send-btn');
  if (!habitName) { showToast(S('msg','enter_habit_name'), true); return; }
  if (btn) { btn.textContent = S('shop','sending'); btn.disabled = true; }
  try {
    const res = await fetch(`${API}/challenges/${userId}/send`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Init-Data': initData, 'X-User-Id': userId },
      body: JSON.stringify({ receiver_id: parseInt(fid), habit_name: habitName, days, bet })
    });
    const r = await res.json();
    if (!r.ok) throw new Error(r.error);
    closeChallengeModal();
    const t = document.getElementById('toast-friends');
    if (t) { t.textContent = S('msg','ch_sent'); t.className = 'toast show'; setTimeout(()=>t.className='toast',2500); }
  } catch(e) {
    showToast('❌ ' + (e.message || S('msg','error_label')), true);
  } finally {
    if (btn) { btn.textContent = S('shop','challenge_send'); btn.disabled = false; }
  }
}

async function acceptChallenge(cid) {
  try {
    const res = await fetch(`${API}/challenges/${userId}/${cid}/accept`, {
      method: 'POST',
      headers: { 'X-Init-Data': initData, 'X-User-Id': userId }
    });
    const r = await res.json();
    if (!r.ok) throw new Error(r.error);
    showToast(S('msg','ch_accepted'));
    loaded.friends = false;
    loadFriends();
  } catch(e) {
    showToast('❌ ' + (e.message || S('msg','error_label')), true);
  }
}

async function rejectChallenge(cid) {
  try {
    const res = await fetch(`${API}/challenges/${userId}/${cid}/reject`, {
      method: 'POST',
      headers: { 'X-Init-Data': initData, 'X-User-Id': userId }
    });
    const r = await res.json();
    if (!r.ok) throw new Error(r.error);
    showToast(S('msg','ch_rejected'));
    loaded.friends = false;
    loadFriends();
  } catch(e) {
    showToast('❌ ' + (e.message || S('msg','error_label')), true);
  }
}

// ── ONBOARDING ──
const OB_KEY = 'sh_ob_v3'; // localStorage key: JSON {habit,stats}

const OB_TEXT = {
  uz: {
    title: '👋 Xush kelibsiz!',
    sub: 'Boshlash uchun 2 ta qadamni bajaring.',
    close: 'Keyinroq',
    steps: [
      { key:'habit', icon:'☀️', title:'Birinchi odatni yarating!', desc:'Yuqoridagi "+ Odat yaratish" tugmasini bosing.', tab:'today',
        hint: { icon:'☀️', title:'Yangi odat yarating!', desc:'Sahifaning yuqori qismidagi "+ Odat yaratish" tugmasini bosing, nom va vaqt kiriting, keyin "Saqlash" bosing.', arrow:'👆 "+ Odat yaratish" tugmasini bosing.' } },
      { key:'stats', icon:'⭐', title:'Reytingga qarang!', desc:'Reytingdagi o\'z darajangizni kuzatib boring.', tab:'stats',
        hint: { icon:'⭐', title:'Reytingdagi o\'rningiz!', desc:'Bu sahifada barcha foydalanuvchilar orasidagi o\'rningizni ko\'rasiz. Har kuni odat bajaring — yuqorilashing!', arrow:'👇 O\'z o\'rningizni toping.' } },
    ]
  },
  ru: {
    title: '👋 Добро пожаловать!',
    sub: 'Выполните 2 шага для начала.',
    close: 'Позже',
    steps: [
      { key:'habit', icon:'☀️', title:'Создайте первую привычку!', desc:'Нажмите кнопку "+ Создать привычку" вверху.', tab:'today',
        hint: { icon:'☀️', title:'Создайте привычку!', desc:'Нажмите кнопку "+ Создать привычку" в верхней части страницы, введите название и время, затем нажмите "Сохранить".', arrow:'👆 Нажмите "+ Создать привычку".' } },
      { key:'stats', icon:'⭐', title:'Посмотрите рейтинг!', desc:'Следите за своим уровнем в рейтинге.', tab:'stats',
        hint: { icon:'⭐', title:'Ваше место в рейтинге!', desc:'На этой странице вы видите своё место среди всех пользователей. Выполняйте привычки — поднимайтесь выше!', arrow:'👇 Найдите своё место в списке.' } },
    ]
  },
  en: {
    title: '👋 Welcome!',
    sub: 'Complete 2 steps to get started.',
    close: 'Later',
    steps: [
      { key:'habit', icon:'☀️', title:'Create your first habit!', desc:'Tap the "+ Create habit" button at the top.', tab:'today',
        hint: { icon:'☀️', title:'Create a habit!', desc:'Tap the "+ Create habit" button at the top of the page, enter a name and time, then tap "Save".', arrow:'👆 Tap "+ Create habit" button.' } },
      { key:'stats', icon:'⭐', title:'Check the leaderboard!', desc:'Track your level in the leaderboard.', tab:'stats',
        hint: { icon:'⭐', title:'Your leaderboard rank!', desc:'This page shows your position among all users. Complete habits daily to climb higher!', arrow:'👇 Find your position in the list.' } },
    ]
  }
};

function getObState() {
  try { return JSON.parse(localStorage.getItem(OB_KEY)) || {}; } catch(e) { return {}; }
}
function saveObState(state) {
  localStorage.setItem(OB_KEY, JSON.stringify(state));
}

function obMarkDone(key) {
  const state = getObState();
  if (state[key] || state._done) return;
  state[key] = true;
  saveObState(state);
  // Re-render if modal is visible
  if (document.getElementById('onboard-modal').style.display === 'block') {
    renderOnboard();
  }
  // Check if all done
  const lang = (currentLang && OB_TEXT[currentLang]) ? currentLang : 'uz';
  const allDone = OB_TEXT[lang].steps.every(s => state[s.key]);
  if (allDone) setTimeout(() => closeOnboard(true), 800);
}

function renderOnboard() {
  const lang = (currentLang && OB_TEXT[currentLang]) ? currentLang : 'uz';
  const txt = OB_TEXT[lang];
  const state = getObState();
  const done = txt.steps.filter(s => state[s.key]).length;

  document.getElementById('ob-title').textContent = txt.title;
  document.getElementById('ob-sub').textContent   = txt.sub;
  document.getElementById('ob-close').textContent = txt.close;

  // Dots
  document.getElementById('ob-dots').innerHTML = txt.steps.map((s, i) => {
    const isDone = !!state[s.key];
    const cls = isDone ? 'done' : (i === done ? 'active' : '');
    return `<div class="ob-dot ${cls}"></div>`;
  }).join('');

  // Steps
  const stepsEl = document.getElementById('ob-steps');
  stepsEl.innerHTML = txt.steps.map(s => {
    const isDone = !!state[s.key];
    return `<div class="ob-step${isDone ? ' done' : ''}" onclick="obStepClick('${s.key}','${s.tab}')">
      <div class="ob-check">${isDone ? '✓' : s.icon}</div>
      <div class="ob-text">
        <div class="ob-step-title">${s.title}</div>
        <div class="ob-step-desc">${s.desc}</div>
      </div>
      <div class="ob-arrow">›</div>
    </div>`;
  }).join('');
}

function obStepClick(key, tab) {
  closeOnboard();
  const navEl = document.getElementById('nav-' + tab);
  if (navEl) switchTab(tab, navEl);
  // Habit qadami: odat qo'shish formasini darhol ochamiz
  if (key === 'habit') setTimeout(openAdd, 150);
  // Hint ko'rsatish
  const lang = (currentLang && OB_TEXT[currentLang]) ? currentLang : 'uz';
  const step = OB_TEXT[lang].steps.find(s => s.key === key);
  if (step && step.hint) setTimeout(() => showObHint(step.hint), key === 'habit' ? 500 : 0);
}

let _obHintTimer = null;
function showObHint(hint) {
  document.getElementById('obh-icon').textContent  = hint.icon;
  document.getElementById('obh-title').textContent = hint.title;
  document.getElementById('obh-desc').textContent  = hint.desc;
  document.getElementById('obh-arrow').textContent = hint.arrow;
  const el = document.getElementById('ob-hint');
  el.style.display = 'block';
  if (_obHintTimer) clearTimeout(_obHintTimer);
  _obHintTimer = setTimeout(hideObHint, 8000);
}
function hideObHint() {
  document.getElementById('ob-hint').style.display = 'none';
  if (_obHintTimer) { clearTimeout(_obHintTimer); _obHintTimer = null; }
}

function closeOnboard(permanent) {
  document.getElementById('onboard-modal').style.display   = 'none';
  document.getElementById('onboard-backdrop').style.display = 'none';
}

function maybeShowOnboard(todayData) {
  const lang = (currentLang && OB_TEXT[currentLang]) ? currentLang : 'uz';
  const state = getObState();
  // Agar odatlar bo'sh bo'lsa — habit qadamini qayta ko'rsat (done deb belgilama)
  if (todayData && (!todayData.habits || todayData.habits.length === 0)) {
    delete state.habit;
    saveObState(state);
  }
  const allDone = OB_TEXT[lang].steps.every(s => state[s.key]);
  if (allDone) return;
  renderOnboard();
  document.getElementById('onboard-modal').style.display   = 'block';
  document.getElementById('onboard-backdrop').style.display = 'block';
}

// ── START ──
// Klaviatura chiqganda aktiv input ko'rinsin
if (window.visualViewport) {
  window.visualViewport.addEventListener('resize', () => {
    const active = document.activeElement;
    if (active && (active.tagName === 'INPUT' || active.tagName === 'TEXTAREA')) {
      setTimeout(() => active.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);
    }
  });
}
// Foydalanuvchi WebApp ga qaytganda (bot bildirishnomasidan) today ni yangilash
document.addEventListener('visibilitychange', function() {
  if (document.visibilityState === 'visible' && userId) {
    loaded.today = false;
    if (_curTab === 'today') loadToday();
  }
});

window.onload = function() {
  // Saqlangan tilni darhol qo'llash (loading matnlari uchun)
  updateNavLabels();
  // Telegram WebApp userId tayyor bo'lishini kutamiz
  if (!userId || userId === 0) {
    let tries = 0;
    const waitUid = setInterval(() => {
      const u = window.Telegram?.WebApp?.initDataUnsafe?.user;
      if (u && u.id) { clearInterval(waitUid); location.reload(); return; }
      if (++tries >= 30) {
        clearInterval(waitUid);
        document.getElementById('today-content').innerHTML =
          '<div class="empty-state"><div class="icon">⚠️</div>' +
          '<div>' + S('msg','err_reopen') + '</div>' +
          '<button onclick="location.reload()" style="margin-top:14px;padding:10px 20px;border-radius:12px;border:none;background:var(--card);box-shadow:var(--sh);font-family:inherit;font-size:13px;font-weight:600;cursor:pointer;color:var(--text)">' + S('msg','btn_refresh') + '</button></div>';
      }
    }, 100);
    return;
  }
  loadToday();
};

// ── OVOZ EFFEKTLARI (Web Audio API) ──
function playHabitSound(isDone) {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    if (isDone) {
      // ✅ Trend "celebration chime" — yumshoq marimba uslubida ko'tariluvchi akkord
      const notes = [
        { freq: 587.33, delay: 0,    dur: 0.4,  vol: 0.22 },
        { freq: 739.99, delay: 0.08, dur: 0.35, vol: 0.20 },
        { freq: 880.00, delay: 0.16, dur: 0.45, vol: 0.18 },
        { freq: 1174.66, delay: 0.28, dur: 0.5, vol: 0.12 }
      ];
      notes.forEach(n => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        const filter = ctx.createBiquadFilter();
        osc.connect(filter);
        filter.connect(gain);
        gain.connect(ctx.destination);
        osc.type = 'sine';
        filter.type = 'lowpass';
        filter.frequency.setValueAtTime(3000, ctx.currentTime);
        filter.frequency.exponentialRampToValueAtTime(800, ctx.currentTime + n.delay + n.dur);
        osc.frequency.setValueAtTime(n.freq, ctx.currentTime + n.delay);
        gain.gain.setValueAtTime(0, ctx.currentTime + n.delay);
        gain.gain.linearRampToValueAtTime(n.vol, ctx.currentTime + n.delay + 0.015);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + n.delay + n.dur);
        osc.start(ctx.currentTime + n.delay);
        osc.stop(ctx.currentTime + n.delay + n.dur);
      });
      // Shimmer layer — yuqori oktava pads
      const shimmer = ctx.createOscillator();
      const sGain = ctx.createGain();
      shimmer.connect(sGain);
      sGain.connect(ctx.destination);
      shimmer.type = 'triangle';
      shimmer.frequency.setValueAtTime(1760, ctx.currentTime + 0.12);
      sGain.gain.setValueAtTime(0, ctx.currentTime + 0.12);
      sGain.gain.linearRampToValueAtTime(0.06, ctx.currentTime + 0.14);
      sGain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.7);
      shimmer.start(ctx.currentTime + 0.12);
      shimmer.stop(ctx.currentTime + 0.75);
    } else {
      // ❌ Soft "whomp-down" — yumshoq pasayish, xunuk lekin shovqinsiz
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      const filter = ctx.createBiquadFilter();
      osc.connect(filter);
      filter.connect(gain);
      gain.connect(ctx.destination);
      osc.type = 'triangle';
      filter.type = 'lowpass';
      filter.frequency.setValueAtTime(600, ctx.currentTime);
      filter.frequency.exponentialRampToValueAtTime(150, ctx.currentTime + 0.3);
      osc.frequency.setValueAtTime(330, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(110, ctx.currentTime + 0.25);
      gain.gain.setValueAtTime(0.18, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3);
      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + 0.35);
      // Ikkinchi "thud" qatlam
      const osc2 = ctx.createOscillator();
      const g2 = ctx.createGain();
      osc2.connect(g2);
      g2.connect(ctx.destination);
      osc2.type = 'sine';
      osc2.frequency.setValueAtTime(180, ctx.currentTime + 0.05);
      osc2.frequency.exponentialRampToValueAtTime(60, ctx.currentTime + 0.2);
      g2.gain.setValueAtTime(0.12, ctx.currentTime + 0.05);
      g2.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.25);
      osc2.start(ctx.currentTime + 0.05);
      osc2.stop(ctx.currentTime + 0.3);
    }
    setTimeout(() => ctx.close(), 1500);
  } catch(e) { console.error('audio:', e); }
}

// Repeat odat progress ovozi — har bir qadam uchun ko'tariluvchi "pop"
function playProgressSound(step, total) {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const ratio = step / total;
    // Qadamga qarab chastota ko'tariladi — 440 dan 880 gacha
    const baseFreq = 440 + (ratio * 440);
    // Asosiy "pop" nota
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    const filter = ctx.createBiquadFilter();
    osc.connect(filter);
    filter.connect(gain);
    gain.connect(ctx.destination);
    osc.type = 'sine';
    filter.type = 'lowpass';
    filter.frequency.setValueAtTime(2500, ctx.currentTime);
    filter.frequency.exponentialRampToValueAtTime(600, ctx.currentTime + 0.25);
    osc.frequency.setValueAtTime(baseFreq, ctx.currentTime);
    osc.frequency.linearRampToValueAtTime(baseFreq * 1.02, ctx.currentTime + 0.08);
    gain.gain.setValueAtTime(0, ctx.currentTime);
    gain.gain.linearRampToValueAtTime(0.2, ctx.currentTime + 0.01);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.25);
    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + 0.28);
    // Ikkinchi harmonik — ring effekti
    const osc2 = ctx.createOscillator();
    const g2 = ctx.createGain();
    osc2.connect(g2);
    g2.connect(ctx.destination);
    osc2.type = 'triangle';
    osc2.frequency.setValueAtTime(baseFreq * 2, ctx.currentTime);
    g2.gain.setValueAtTime(0, ctx.currentTime);
    g2.gain.linearRampToValueAtTime(0.06, ctx.currentTime + 0.01);
    g2.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.18);
    osc2.start(ctx.currentTime);
    osc2.stop(ctx.currentTime + 0.2);
    setTimeout(() => ctx.close(), 800);
  } catch(e) { console.error('audio:', e); }
}

// ── PULL TO REFRESH (barcha sahifalar uchun) ──
(function() {
  var startY = 0;
  var pulling = false;
  var threshold = 72;
  // PTR ishlamaydigan ichki sahifalar
  var skipTabs = ['achievements', 'reminders', 'premium'];

  document.addEventListener('touchstart', function(e) {
    if (skipTabs.indexOf(_curTab) !== -1) return;
    if (window.scrollY > 0) return;
    startY = e.touches[0].clientY;
    pulling = true;
  }, { passive: true });

  document.addEventListener('touchmove', function(e) {
    if (!pulling) return;
    if (skipTabs.indexOf(_curTab) !== -1) { pulling = false; return; }
    var dist = e.touches[0].clientY - startY;
    if (dist <= 0) { pulling = false; return; }
    var ind = document.getElementById('ptr-indicator');
    var txt = document.getElementById('ptr-text');
    if (!ind) return;
    ind.classList.add('visible');
    ind.classList.remove('spinning');
    txt.textContent = dist >= threshold ? S('msg','ptr_release') : S('msg','ptr_pull');
    document.getElementById('ptr-spinner').style.transform = 'rotate(' + Math.min(dist * 2.5, 360) + 'deg)';
  }, { passive: true });

  document.addEventListener('touchend', function(e) {
    if (!pulling) return;
    pulling = false;
    var dist = e.changedTouches[0].clientY - startY;
    var ind = document.getElementById('ptr-indicator');
    if (!ind) return;
    if (dist >= threshold && skipTabs.indexOf(_curTab) === -1) {
      ind.classList.add('spinning');
      document.getElementById('ptr-text').textContent = S('msg','ptr_loading');
      loaded[_curTab] = false;
      loadTab(_curTab).finally(function() {
        ind.classList.remove('visible', 'spinning');
      });
    } else {
      ind.classList.remove('visible', 'spinning');
    }
  }, { passive: true });
})();

// ── BOTTOM PULL TO REFRESH (barcha sahifalar uchun) ──
(function() {
  var startY = 0;
  var pulling = false;
  var threshold = 72;
  var skipTabs = ['achievements', 'reminders', 'premium'];

  function isAtBottom() {
    return (window.innerHeight + window.scrollY) >= (document.body.scrollHeight - 5);
  }

  document.addEventListener('touchstart', function(e) {
    if (skipTabs.indexOf(_curTab) !== -1) return;
    if (!isAtBottom()) return;
    startY = e.touches[0].clientY;
    pulling = true;
  }, { passive: true });

  document.addEventListener('touchmove', function(e) {
    if (!pulling) return;
    if (skipTabs.indexOf(_curTab) !== -1) { pulling = false; return; }
    // Pastga tortish = barmaq yuqoriga ketadi = dist manfiy
    var dist = startY - e.touches[0].clientY;
    if (dist <= 0) { pulling = false; return; }
    var ind = document.getElementById('ptr-bottom');
    var txt = document.getElementById('ptr-bottom-text');
    if (!ind) return;
    ind.classList.add('visible');
    ind.classList.remove('spinning');
    txt.textContent = dist >= threshold ? S('msg','ptr_release') : S('msg','ptr_pull');
    document.getElementById('ptr-bottom-spinner').style.transform = 'rotate(' + Math.min(dist * 2.5, 360) + 'deg)';
  }, { passive: true });

  document.addEventListener('touchend', function(e) {
    if (!pulling) return;
    pulling = false;
    var dist = startY - e.changedTouches[0].clientY;
    var ind = document.getElementById('ptr-bottom');
    if (!ind) return;
    if (dist >= threshold && skipTabs.indexOf(_curTab) === -1) {
      ind.classList.add('spinning');
      document.getElementById('ptr-bottom-text').textContent = S('msg','ptr_loading');
      loaded[_curTab] = false;
      loadTab(_curTab).finally(function() {
        ind.classList.remove('visible', 'spinning');
      });
    } else {
      ind.classList.remove('visible', 'spinning');
    }
  }, { passive: true });
})();
