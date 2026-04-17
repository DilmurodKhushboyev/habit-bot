// ── TELEGRAM WEB APP ──
const tg      = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
  // To'liq ekran rejimi (Telegram header'ni yashiradi)
  if (tg.requestFullscreen) tg.requestFullscreen();
  // Pastga tortib yopishni bloklash
  if (tg.disableVerticalSwipes) tg.disableVerticalSwipes();
  // Safe area: content Telegram paneli ostiga tushmasligi uchun
  function applySafeArea() {
    var si = tg.safeAreaInset || {};
    var ci = tg.contentSafeAreaInset || {};
    var top = (si.top || 0) + (ci.top || 0);
    // Fallback: agar safe area 0 qaytarsa — Telegram header balandligi ~56px
    if (top < 10) top = 56;
    document.documentElement.style.setProperty('--tg-safe-top', top + 'px');
  }
  applySafeArea();
  tg.onEvent('safeAreaChanged', applySafeArea);
  tg.onEvent('contentSafeAreaChanged', applySafeArea);
}
if (localStorage.getItem('sh_dark') === '1') {
  // Agar body hali parse qilinmagan bo'lsa (app-core.js <head> ichida yuklanadi) — DOMContentLoaded ni kutamiz
  if (document.body) {
    document.body.classList.add('dark');
  } else {
    document.addEventListener('DOMContentLoaded', function() {
      document.body.classList.add('dark');
    });
  }
}

const user     = tg?.initDataUnsafe?.user || { id: 0, first_name: 'Test' };
let   initData = tg?.initData || '';
let   userId   = user.id || 0;
const API      = window.location.origin + '/api';

// ── STATE ──
let loaded = { today: false, profile: false, habits: false, stats: false, achievements: false, reminders: false, bozor: false };
let data   = {};

// ── HEADER BALL SINXRON YANGILASH ──
// Markaziy helper — har qayerda (checkin, bozor, guruh, kelajakdagi yangi joylar)
// ball o'zgarganda shu funksiya chaqiriladi. Header displeyi + global state sinxron.
// Sabab: avval har joyda inline kod takrorlanardi (3-4 joyda), bozor/sotishda esa
// umuman yo'q edi — shuning uchun bozordan sotib olingandan keyin header eski
// qiymatda qolardi. Endi bitta joyda markazlashgan.
function updateHeaderPts(points) {
  if (points === undefined || points === null) return;
  const el = document.getElementById('header-pts');
  if (el) el.textContent = '⭐ ' + points;
  // Global state ham sinxron — boshqa sahifalar yangilangan qiymatni ko'radi
  if (data && data.today)   data.today.points   = points;
  if (data && data.profile) data.profile.points = points;
}

// ── TAB SWITCH ──
let _prevTab = 'today';
let _curTab  = 'today';

function showPremiumPage() {
  document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.getElementById('page-premium').classList.add('active');
  _prevTab = _curTab || 'today';
  _curTab  = 'premium';
  const backBar = document.getElementById('back-bar');
  if (backBar) backBar.style.display = 'flex';
  renderPremium();
}

function renderPremium() {
  const d = data.profile || {};
  const isPrem = d.is_premium;
  const expires = d.premium_expires || '';
  const priceStars = d.price_stars || 20;
  const priceSom = d.price_som || 4900;
  const freeLimit = 3;
  const premLimit = 15;
  const lang = currentLang || 'uz';

  const titles = { uz: 'Super Habits Premium', en: 'Super Habits Premium', ru: 'Super Habits Premium' };
  const subtitles = {
    uz: 'Cheksiz odat, challenge va batafsil statistika',
    en: 'Unlimited habits, challenges & detailed stats',
    ru: '\u0411\u0435\u0437\u043b\u0438\u043c\u0438\u0442 \u043f\u0440\u0438\u0432\u044b\u0447\u0435\u043a, \u0432\u044b\u0437\u043e\u0432\u044b \u0438 \u043f\u043e\u0434\u0440\u043e\u0431\u043d\u0430\u044f \u0441\u0442\u0430\u0442\u0438\u0441\u0442\u0438\u043a\u0430',
  };
  const fList = {
    uz: [
      ['\u2705', 'Cheksiz odat (' + premLimit + ' tagacha)', 'Bepul: faqat ' + freeLimit + ' ta'],
      ['\u2705', "Challenge \u2014 do'st bilan raqobat", "Bepul: yo'q"],
      ['\u2705', 'Batafsil statistika va hisobot', 'Bepul: cheklangan'],
      ['\u2705', 'Guruh imkoniyatlari', 'Bepul: cheklangan'],
      ['\u2705', 'Kechki eslatma', "Bepul: yo'q"],
    ],
    en: [
      ['\u2705', 'Unlimited habits (up to ' + premLimit + ')', 'Free: only ' + freeLimit],
      ['\u2705', 'Challenges \u2014 compete with friends', 'Free: unavailable'],
      ['\u2705', 'Detailed stats & reports', 'Free: limited'],
      ['\u2705', 'Group features', 'Free: limited'],
      ['\u2705', 'Evening reminders', 'Free: unavailable'],
    ],
    ru: [
      ['\u2705', '\u041d\u0435\u043e\u0433\u0440\u0430\u043d\u0438\u0447\u0435\u043d\u043d\u044b\u0435 \u043f\u0440\u0438\u0432\u044b\u0447\u043a\u0438 (\u0434\u043e ' + premLimit + ')', '\u0411\u0435\u0441\u043f\u043b\u0430\u0442\u043d\u043e: \u0442\u043e\u043b\u044c\u043a\u043e ' + freeLimit],
      ['\u2705', '\u0412\u044b\u0437\u043e\u0432\u044b \u2014 \u0441\u043e\u0440\u0435\u0432\u043d\u043e\u0432\u0430\u043d\u0438\u044f \u0441 \u0434\u0440\u0443\u0437\u044c\u044f\u043c\u0438', '\u0411\u0435\u0441\u043f\u043b\u0430\u0442\u043d\u043e: \u043d\u0435\u0442'],
      ['\u2705', '\u041f\u043e\u0434\u0440\u043e\u0431\u043d\u0430\u044f \u0441\u0442\u0430\u0442\u0438\u0441\u0442\u0438\u043a\u0430 \u0438 \u043e\u0442\u0447\u0451\u0442\u044b', '\u0411\u0435\u0441\u043f\u043b\u0430\u0442\u043d\u043e: \u043e\u0433\u0440\u0430\u043d\u0438\u0447\u0435\u043d\u043e'],
      ['\u2705', '\u0424\u0443\u043d\u043a\u0446\u0438\u0438 \u0433\u0440\u0443\u043f\u043f', '\u0411\u0435\u0441\u043f\u043b\u0430\u0442\u043d\u043e: \u043e\u0433\u0440\u0430\u043d\u0438\u0447\u0435\u043d\u043e'],
      ['\u2705', '\u0412\u0435\u0447\u0435\u0440\u043d\u0438\u0435 \u043d\u0430\u043f\u043e\u043c\u0438\u043d\u0430\u043d\u0438\u044f', '\u0411\u0435\u0441\u043f\u043b\u0430\u0442\u043d\u043e: \u043d\u0435\u0442'],
    ],
  };

  const buyStarsLbl = { uz: '\u2b50 ' + priceStars + " Stars bilan to'lash", en: '\u2b50 Pay with ' + priceStars + ' Stars', ru: '\u2b50 \u041e\u043f\u043b\u0430\u0442\u0438\u0442\u044c ' + priceStars + ' Stars' };
  const buySomLbl   = { uz: '\ud83d\udcb3 ' + priceSom.toLocaleString() + " so'm bilan to'lash", en: '\ud83d\udcb3 Pay ' + priceSom.toLocaleString() + ' UZS', ru: '\ud83d\udcb3 \u041e\u043f\u043b\u0430\u0442\u0438\u0442\u044c ' + priceSom.toLocaleString() + ' \u0441\u0443\u043c' };
  const renewStarsLbl = { uz: '\ud83d\udd04 Stars bilan yangilash \u2014 ' + priceStars + ' Stars', en: '\ud83d\udd04 Renew with Stars \u2014 ' + priceStars + ' Stars', ru: '\ud83d\udd04 \u041e\u0431\u043d\u043e\u0432\u0438\u0442\u044c Stars \u2014 ' + priceStars + ' Stars' };
  const renewSomLbl   = { uz: "\ud83d\udd04 So'm bilan yangilash \u2014 " + priceSom.toLocaleString() + " so'm", en: '\ud83d\udd04 Renew UZS \u2014 ' + priceSom.toLocaleString() + ' UZS', ru: '\ud83d\udd04 \u041e\u0431\u043d\u043e\u0432\u0438\u0442\u044c \u0441\u0443\u043c \u2014 ' + priceSom.toLocaleString() + ' \u0441\u0443\u043c' };
  const activeNoteLbl = { uz: '\u2705 Premiumingiz faol!\n\ud83d\udcc5 ' + expires + ' gacha', en: '\u2705 Premium is active!\n\ud83d\udcc5 Until ' + expires, ru: '\u2705 Premium \u0430\u043a\u0442\u0438\u0432\u0435\u043d!\n\ud83d\udcc5 \u0414\u043e ' + expires };
  const freeNoteLbl   = { uz: 'Hozir: Bepul (' + freeLimit + ' ta odat)', en: 'Now: Free (' + freeLimit + ' habits)', ru: '\u0421\u0435\u0439\u0447\u0430\u0441: \u0411\u0435\u0441\u043f\u043b\u0430\u0442\u043d\u043e (' + freeLimit + ' \u043f\u0440\u0438\u0432\u044b\u0447\u0435\u043a)' };

  const featureRows = (fList[lang] || fList.uz).map(function(r) {
    return '<div style="display:flex;align-items:flex-start;gap:10px;padding:10px 0;border-bottom:1px solid var(--border)">'
      + '<span style="font-size:18px;min-width:24px;text-align:center">' + r[0] + '</span>'
      + '<div><div style="font-size:13px;font-weight:700;color:var(--text)">' + r[1] + '</div>'
      + '<div style="font-size:11px;color:var(--sub);margin-top:2px">' + r[2] + '</div></div></div>';
  }).join('');

  const starsLbl = isPrem ? (renewStarsLbl[lang]||renewStarsLbl.uz) : (buyStarsLbl[lang]||buyStarsLbl.uz);
  const somLbl   = isPrem ? (renewSomLbl[lang]  ||renewSomLbl.uz)   : (buySomLbl[lang]  ||buySomLbl.uz);

  document.getElementById('premium-content').innerHTML =
    '<div style="padding:16px 16px 80px">'
    + '<div style="text-align:center;padding:28px 16px 20px;background:linear-gradient(135deg,var(--card),var(--bg));border-radius:20px;margin-bottom:16px;box-shadow:var(--sh-sm)">'
    + '<div style="font-size:52px;margin-bottom:8px">\ud83d\udc8e</div>'
    + '<div style="font-size:20px;font-weight:800;color:var(--text);margin-bottom:6px">' + (titles[lang]||titles.uz) + '</div>'
    + '<div style="font-size:13px;color:var(--sub)">' + (subtitles[lang]||subtitles.uz) + '</div>'
    + (isPrem
        ? '<div style="margin-top:14px;padding:10px 16px;background:#4CAF7D22;border-radius:12px;color:#4CAF7D;font-size:13px;font-weight:700;white-space:pre-line">' + (activeNoteLbl[lang]||activeNoteLbl.uz) + '</div>'
        : '<div style="margin-top:14px;padding:8px 16px;background:var(--bg);border-radius:12px;color:var(--sub);font-size:12px">' + (freeNoteLbl[lang]||freeNoteLbl.uz) + '</div>')
    + '</div>'
    + '<div style="background:var(--card);border-radius:16px;padding:4px 16px 8px;margin-bottom:16px;box-shadow:var(--sh-sm)">' + featureRows + '</div>'
    + '<div style="background:linear-gradient(135deg,#F6C93E18,#A78BFA18);border-radius:16px;padding:14px 16px;margin-bottom:16px;border:1px solid #F6C93E33">'
    + '<div style="display:flex;justify-content:space-around;gap:10px">'
    + '<div style="text-align:center"><div style="font-size:18px;font-weight:800;color:var(--text)">\u2b50 ' + priceStars + '</div><div style="font-size:11px;color:var(--sub)">Telegram Stars</div></div>'
    + '<div style="width:1px;background:var(--border)"></div>'
    + '<div style="text-align:center"><div style="font-size:18px;font-weight:800;color:var(--text)">\ud83d\udcb3 ' + priceSom.toLocaleString() + '</div><div style="font-size:11px;color:var(--sub)">so\'m / UZS</div></div>'
    + '</div></div>'
    + '<button onclick="buyPremium(\'stars\')" type="button" style="width:100%;padding:14px;border-radius:14px;background:linear-gradient(90deg,#F6C93E,#A78BFA);color:#1a1a2e;font-size:15px;font-weight:700;border:none;cursor:pointer;box-shadow:0 4px 16px #F6C93E44;margin-bottom:10px">' + starsLbl + '</button>'
    + '<button onclick="buyPremium(\'som\')" type="button" style="width:100%;padding:14px;border-radius:14px;background:linear-gradient(90deg,#4CAF7D,#5B8DEF);color:#fff;font-size:15px;font-weight:700;border:none;cursor:pointer;box-shadow:0 4px 16px #4CAF7D44">' + somLbl + '</button>'
    + '</div>';
}

async function buyPremium(type) {
  try {
    const res = await apiFetch('premium/' + userId + '/buy', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ type: type }),
    });
    const json = await res.json().catch(function() { return {}; });
    if (!json.ok) {
      const errMsg = { uz: '❌ Xatolik yuz berdi', en: '❌ Error occurred', ru: '❌ Произошла ошибка' };
      showToast(errMsg[currentLang] || errMsg.uz, true);
      return;
    }
    if (type === 'som') {
      // To'lov URL bor bo'lsa — ochish
      if (json.click_url) { window.open(json.click_url, '_blank'); }
      else if (json.payme_url) { window.open(json.payme_url, '_blank'); }
      // URL yo'q bo'lsa — bot chatiga yo'naltirish (chek yuborish uchun)
      else if (json.bot_username) {
        try { window.Telegram.WebApp.openTelegramLink('https://t.me/' + json.bot_username); }
        catch(_) { window.open('https://t.me/' + json.bot_username, '_blank'); }
      }
      // Toast
      const adminNote = {
        uz: "To'lovdan so'ng chekni botga yuboring!",
        en: 'After payment, send the receipt to the bot!',
        ru: 'После оплаты отправьте чек в бот!',
      };
      showToast(adminNote[currentLang] || adminNote.uz);
    }
    // Stars uchun Telegram o'zi invoice oynasini ochadi
  } catch(e) {
    console.error('buyPremium:', e);
  }
}


// ── NAV BALL + NOTCH ──
function drawNavNotch(cx) {
  var nav = document.getElementById('bottom-nav');
  var svgPath = document.getElementById('nav-bg-path');
  var svgEl = document.getElementById('nav-bg');
  if (!nav || !svgPath || !svgEl) return;

  var w = nav.offsetWidth;
  var h = nav.offsetHeight;
  svgEl.setAttribute('viewBox', '0 0 ' + w + ' ' + h);
  svgEl.setAttribute('width', w);
  svgEl.setAttribute('height', h);

  // Notch parameters — ball floats above panel, notch wraps its bottom
  var r = 46;   // notch half-width (wider to fully wrap 62px ball + gap)
  var d = 34;   // notch depth (deep enough so panel curves around ball bottom)
  var top = 6;  // top edge offset

  var nleft = cx - r;
  var nright = cx + r;

  // Smooth cubic bezier notch — panel wraps around the ball
  var path = 'M0,' + top
    + ' L' + Math.max(0, nleft) + ',' + top
    + ' C' + (nleft + r * 0.3) + ',' + top + ' ' + (nleft + r * 0.4) + ',' + (top + d) + ' ' + cx + ',' + (top + d)
    + ' C' + (nright - r * 0.4) + ',' + (top + d) + ' ' + (nright - r * 0.3) + ',' + top + ' ' + Math.min(w, nright) + ',' + top
    + ' L' + w + ',' + top
    + ' L' + w + ',' + h
    + ' L0,' + h + ' Z';

  svgPath.setAttribute('d', path);
}

function moveNavBall(targetEl, animate) {
  var ball = document.getElementById('nav-ball');
  var ballIcon = document.getElementById('nav-ball-icon');
  var ballLabel = document.getElementById('nav-ball-label');
  var nav  = document.getElementById('bottom-nav');
  if (!ball || !nav || !targetEl) return;

  var navRect = nav.getBoundingClientRect();
  var tRect   = targetEl.getBoundingClientRect();
  var halfBall = 31; // 62/2
  var targetX = tRect.left - navRect.left + tRect.width / 2 - halfBall;
  var centerX = tRect.left - navRect.left + tRect.width / 2;

  // Clone active tab icon + label into ball
  var srcIcon = targetEl.querySelector('.nav-icon');
  var srcLabel = targetEl.querySelector('.nav-label');
  if (srcIcon && ballIcon) {
    ballIcon.innerHTML = srcIcon.innerHTML;
  }
  if (srcLabel && ballLabel) {
    ballLabel.textContent = srcLabel.textContent;
  }

  if (!animate || ball._lastX === undefined) {
    ball.style.transform = 'translate(' + targetX + 'px, 0)';
    ball._lastX = targetX;
    drawNavNotch(centerX);
    return;
  }

  var startX = ball._lastX;
  var midX   = (startX + targetX) / 2;

  // Animate notch sliding with ball
  var startCx = startX + halfBall;
  var endCx   = centerX;
  var notchStart = performance.now();
  var notchDur = 480;
  function animateNotch(now) {
    var t = Math.min((now - notchStart) / notchDur, 1);
    var ease = 1 - Math.pow(1 - t, 3);
    var cx = startCx + (endCx - startCx) * ease;
    drawNavNotch(cx);
    if (t < 1) requestAnimationFrame(animateNotch);
  }
  requestAnimationFrame(animateNotch);

  ball.classList.remove('jumping');
  ball.style.setProperty('--ball-sx', startX + 'px');
  ball.style.setProperty('--ball-mid', midX + 'px');
  ball.style.setProperty('--ball-ex', targetX + 'px');

  void ball.offsetWidth;
  ball.classList.add('jumping');

  ball.addEventListener('animationend', function onEnd() {
    ball.classList.remove('jumping');
    ball.style.transform = 'translate(' + targetX + 'px, 0)';
    ball._lastX = targetX;
    ball.removeEventListener('animationend', onEnd);
    // Toʻlqin (ripple) effekti — shar tushganda panel jilvalanadi
    spawnNavRipple(centerX);
  });

  ball._lastX = targetX;
}

function spawnNavRipple(cx) {
  var nav = document.getElementById('bottom-nav');
  if (!nav) return;
  var size = 60;
  for (var i = 0; i < 2; i++) {
    var rip = document.createElement('div');
    rip.className = 'nav-ripple' + (i === 1 ? ' ripple-2' : '');
    rip.style.width = size + 'px';
    rip.style.height = size + 'px';
    rip.style.left = (cx - size / 2) + 'px';
    rip.style.top = '-6px';
    nav.appendChild(rip);
    rip.addEventListener('animationend', function() { this.remove(); });
  }
}

let _tabLoading = false;

function switchTab(tab, el) {
  // Agar tab hali yuklanayotgan bo'lsa — takroriy bosishni e'tiborsiz qoldir
  if (_tabLoading) return;
  document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
  if (el) el.classList.add('active');
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.getElementById('page-' + tab).classList.add('active');
  _prevTab = _curTab;
  _curTab  = tab;
  // Ichki sahifalarda orqa tugma
  const backPages = ['achievements','reminders'];
  const backBar   = document.getElementById('back-bar');
  if (backBar) backBar.style.display = backPages.includes(tab) ? 'flex' : 'none';
  // Nav ball
  var navTarget = el || document.getElementById('nav-' + tab);
  if (navTarget) moveNavBall(navTarget, true);
  if (!loaded[tab]) loadTab(tab);
  else if (tab === 'habits') { loaded.habits = false; loadTab('habits'); }
  else if (tab === 'profile') { loaded.profile = false; loadTab('profile'); }
  else if (tab === 'bozor') { loaded.bozor = false; loadTab('bozor'); }
  else refreshHabitsJon();
}

function goBack() {
  const navEl = document.getElementById('nav-' + _prevTab);
  switchTab(_prevTab, navEl);
}

async function loadTab(tab) {
  _tabLoading = true;
  try {
    if (tab === 'today')        await loadToday();
    if (tab === 'stats')        await loadStats();
    if (tab === 'achievements') await loadAchievements();
    if (tab === 'reminders')    await loadReminders();
    if (tab === 'profile')      await loadProfile();
    if (tab === 'habits')       await loadStatsPage();
    if (tab === 'bozor') {
      await loadShop();
    }
    loaded[tab] = true;
  } finally {
    _tabLoading = false;
  }
}

// ── FETCH ──
async function apiFetch(endpoint, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 20000);
  try {
    const res = await fetch(`${API}/${endpoint}`, {
      ...options,
      headers: { 'X-Init-Data': initData, 'X-User-Id': userId, ...(options.headers || {}) },
      signal: controller.signal,
    });
    clearTimeout(timer);
    if (!res.ok) throw new Error(res.status);
    return res.json();
  } catch(e) {
    clearTimeout(timer);
    if (e.name === "AbortError") throw new Error(S('msg','connection_error'));
    throw e;
  }
}

// ── PROGRESS RING SVG ──
function ringHTML(percent, size = 80) {
  const r = (size - 12) / 2;
  const circ = 2 * Math.PI * r;
  const dash = circ * Math.min(percent, 100) / 100;
  const gap  = circ - dash;
  const color = percent >= 100 ? '#2D8A5E' : percent >= 50 ? '#4CAF7D' : '#7DC29A';
  const offset = circ * 0.25;
  return `<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
    <circle cx="${size/2}" cy="${size/2}" r="${r}" fill="none" stroke="#C8CBD8" stroke-width="7"/>
    <circle cx="${size/2}" cy="${size/2}" r="${r}" fill="none" stroke="${color}" stroke-width="7"
      stroke-dasharray="${dash} ${gap}"
      stroke-dashoffset="${offset}"
      stroke-linecap="round"/>
    <text x="${size/2}" y="${size/2 + 6}" text-anchor="middle"
      font-family="DM Mono,monospace" font-size="18" font-weight="600" fill="#3A3D4A">${percent}%</text>
  </svg>`;
}

function jonRingHTML(jon, size = 80) {
  const r = (size - 12) / 2;
  const circ = 2 * Math.PI * r;
  const dash = circ * Math.min(jon, 100) / 100;
  const gap  = circ - dash;
  const color = jon >= 60 ? '#4CAF7D' : jon >= 30 ? '#7DC29A' : '#E05050';
  const offset = circ * 0.25;
  return `<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
    <circle cx="${size/2}" cy="${size/2}" r="${r}" fill="none" stroke="#C8CBD8" stroke-width="7"/>
    <circle cx="${size/2}" cy="${size/2}" r="${r}" fill="none" stroke="${color}" stroke-width="7"
      stroke-dasharray="${dash} ${gap}"
      stroke-dashoffset="${offset}"
      stroke-linecap="round"/>
    <text x="${size/2}" y="${size/2 + 6}" text-anchor="middle"
      font-family="DM Mono,monospace" font-size="18" font-weight="600" fill="#3A3D4A">${jon}%</text>
  </svg>`;
}


// ──────────────────────────────────────────────────────────
// INVENTORY SVG IKONLAR (v460)
// Bozor, reyting va profil sahifalarida ishlatiladi
// Markaziy mapping — 14 ta mahsulot uchun line-art SVG
// Rang .inv-icon CSS klassidan (currentColor) — yashil --accent
// Ishlatish: getInvIcon('pet_cat', 'sm' | 'md' | 'lg')
// ──────────────────────────────────────────────────────────
var INV_ICON_PATHS = {
  // Himoya
  jon_restore:   '<path d="M12 3l8 3v6c0 5-3.5 9-8 10-4.5-1-8-5-8-10V6l8-3z"/><path d="M9 12l2 2 4-4"/>',
  streak_shield: '<path d="M12 3l8 3v6c0 5-3.5 9-8 10-4.5-1-8-5-8-10V6l8-3z"/><path d="M12 8v6"/><path d="M9 11h6"/>',

  // Badge (nishon)
  badge_fire:    '<path d="M12 3s4 4 4 8c0 2.5-1.8 4.5-4 4.5S8 13.5 8 11c0-1.5.8-2.8 1.5-3.5C10 10 11 10 11.5 8.5 12 7 12 5 12 3z"/><path d="M10 17c0 2 .9 3.5 2 3.5s2-1.5 2-3.5"/>',
  badge_star:    '<path d="M12 3l2.6 5.6 6 .6-4.5 4.2 1.3 6.1L12 16.8 6.6 19.5l1.3-6.1L3.4 9.2l6-.6L12 3z"/>',
  badge_secret:  '<path d="M6 9l2-4h8l2 4-8 11L6 9z"/><path d="M6 9h12"/><path d="M10 9l2 11 2-11"/>',

  // Pets (uy hayvonlari)
  pet_cat:       '<path d="M6 11l-2-5 4 2h8l4-2-2 5"/><path d="M4 12c0 5 3.5 8 8 8s8-3 8-8c0-2-.7-3.7-1.8-5"/><circle cx="9" cy="13" r=".8" fill="currentColor" stroke="none"/><circle cx="15" cy="13" r=".8" fill="currentColor" stroke="none"/><path d="M11 16c.3.4.7.6 1 .6s.7-.2 1-.6"/><path d="M12 14.5l-.8 1h1.6z" fill="currentColor" stroke="none"/>',
  pet_dog:       '<path d="M5 8l-1 5c0 4 3.5 7 8 7s8-3 8-7l-1-5-3 2H8L5 8z"/><path d="M5 8l-1-3 3 1M19 8l1-3-3 1"/><circle cx="9.5" cy="13" r=".8" fill="currentColor" stroke="none"/><circle cx="14.5" cy="13" r=".8" fill="currentColor" stroke="none"/><path d="M10.5 16h3"/><path d="M12 15v1"/>',
  pet_rabbit:    '<path d="M8 11c-1-2-2-5-2-7 0-1 1-1 1.5 0 1 2 1.5 4 1.5 6"/><path d="M16 11c1-2 2-5 2-7 0-1-1-1-1.5 0-1 2-1.5 4-1.5 6"/><path d="M6 15c0-3 2.5-5 6-5s6 2 6 5c0 3-2.5 5-6 5s-6-2-6-5z"/><circle cx="10" cy="15" r=".7" fill="currentColor" stroke="none"/><circle cx="14" cy="15" r=".7" fill="currentColor" stroke="none"/><path d="M11 17.5h2"/>',

  // Car (mashina)
  car_sport:     '<path d="M3 14l2-5c.3-.8 1-1 2-1h10c1 0 1.7.2 2 1l2 5"/><path d="M3 14v4h18v-4"/><path d="M3 14h18"/><circle cx="7" cy="17" r="1.5" fill="currentColor" stroke="none"/><circle cx="17" cy="17" r="1.5" fill="currentColor" stroke="none"/><path d="M7 11h10"/>',

  // Gift (sovgʻa)
  gift_box:      '<rect x="3" y="9" width="18" height="12" rx="1.5"/><path d="M3 13h18"/><path d="M12 9v12"/><path d="M12 9c-1.5-2-3.5-3-4.5-2s-.5 2 1 2.5c1 .3 2 .3 3.5-.5zM12 9c1.5-2 3.5-3 4.5-2s.5 2-1 2.5c-1 .3-2 .3-3.5-.5z"/>',

  // Bonus
  bonus_2x:      '<path d="M13 3L4 14h7l-1 7 9-11h-7l1-7z"/><text x="17" y="20" font-size="7" font-weight="700" fill="currentColor" stroke="none" font-family="sans-serif">2×</text>',
  bonus_3x:      '<path d="M13 3L4 14h7l-1 7 9-11h-7l1-7z"/><text x="17" y="20" font-size="7" font-weight="700" fill="currentColor" stroke="none" font-family="sans-serif">3×</text>',
  xp_booster:    '<circle cx="12" cy="13" r="7"/><path d="M12 9v4l2.5 2"/><path d="M12 3v2M9 3h6"/><path d="M19 6l-1.5 1.5M5 6l1.5 1.5"/>',

  // Fallback — noma'lum item (xalta)
  _fallback:     '<path d="M6 8h12l1 12c0 1-.5 1.5-1.5 1.5h-11c-1 0-1.5-.5-1.5-1.5L6 8z"/><path d="M9 8V6c0-1.5 1.3-3 3-3s3 1.5 3 3v2"/><path d="M9 12h6"/>',
};

// getInvIcon(itemId, size) — itemId ning SVG ikoni qaytaradi
// size: 'sm' (14px banda), 'md' (32px modal), 'lg' (40px bozor)
// active: true bo'lsa .is-active klassi qo'shiladi (glow effekti)
function getInvIcon(itemId, size, active) {
  var sz = (size === 'md' || size === 'lg') ? size : 'sm';
  var path = INV_ICON_PATHS[itemId] || INV_ICON_PATHS._fallback;
  var cls = 'inv-icon inv-icon-' + sz + (active ? ' is-active' : '');
  return '<span class="' + cls + '" data-item="' + itemId + '">'
    + '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">'
    + path
    + '</svg></span>';
}


// ── INIT NAV BALL + NOTCH on load ──
document.addEventListener('DOMContentLoaded', function() {
  var firstActive = document.querySelector('.nav-item.active');
  if (firstActive) setTimeout(function() { moveNavBall(firstActive, false); }, 80);
});
window.addEventListener('resize', function() {
  var act = document.querySelector('.nav-item.active');
  if (act) moveNavBall(act, false);
});
