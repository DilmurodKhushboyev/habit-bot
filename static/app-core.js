// ── TELEGRAM WEB APP ──
const tg      = window.Telegram?.WebApp;
if (tg) { tg.ready(); tg.expand(); }
if (localStorage.getItem('sh_dark') === '1') document.body.classList.add('dark');

const user     = tg?.initDataUnsafe?.user || { id: 0, first_name: 'Test' };
const initData = tg?.initData || '';
const userId   = user.id || 0;
const API      = window.location.origin + '/api';

// ── STATE ──
let loaded = { today: false, profile: false, habits: false, stats: false, achievements: false, reminders: false, bozor: false };
let data   = {};

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
        ? '<div style="margin-top:14px;padding:10px 16px;background:#10B98122;border-radius:12px;color:#10B981;font-size:13px;font-weight:700;white-space:pre-line">' + (activeNoteLbl[lang]||activeNoteLbl.uz) + '</div>'
        : '<div style="margin-top:14px;padding:8px 16px;background:var(--bg);border-radius:12px;color:var(--sub);font-size:12px">' + (freeNoteLbl[lang]||freeNoteLbl.uz) + '</div>')
    + '</div>'
    + '<div style="background:var(--card);border-radius:16px;padding:4px 16px 8px;margin-bottom:16px;box-shadow:var(--sh-sm)">' + featureRows + '</div>'
    + '<div style="background:linear-gradient(135deg,#F6C93E18,#10B98118);border-radius:16px;padding:14px 16px;margin-bottom:16px;border:1px solid #F6C93E33">'
    + '<div style="display:flex;justify-content:space-around;gap:10px">'
    + '<div style="text-align:center"><div style="font-size:18px;font-weight:800;color:var(--text)">\u2b50 ' + priceStars + '</div><div style="font-size:11px;color:var(--sub)">Telegram Stars</div></div>'
    + '<div style="width:1px;background:var(--border)"></div>'
    + '<div style="text-align:center"><div style="font-size:18px;font-weight:800;color:var(--text)">\ud83d\udcb3 ' + priceSom.toLocaleString() + '</div><div style="font-size:11px;color:var(--sub)">so\'m / UZS</div></div>'
    + '</div></div>'
    + '<button onclick="buyPremium(\'stars\')" type="button" style="width:100%;padding:14px;border-radius:14px;background:linear-gradient(90deg,#F6C93E,#10B981);color:#1a1a2e;font-size:15px;font-weight:700;border:none;cursor:pointer;box-shadow:0 4px 16px #10B98144;margin-bottom:10px">' + starsLbl + '</button>'
    + '<button onclick="buyPremium(\'som\')" type="button" style="width:100%;padding:14px;border-radius:14px;background:linear-gradient(90deg,#10B981,#059669);color:#fff;font-size:15px;font-weight:700;border:none;cursor:pointer;box-shadow:0 4px 16px #10B98144">' + somLbl + '</button>'
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


function switchTab(tab, el) {
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
  if (!loaded[tab]) loadTab(tab);
  else if (tab === 'habits') { loaded.habits = false; loadTab('habits'); }
  else refreshHabitsJon();
}

function goBack() {
  const navEl = document.getElementById('nav-' + _prevTab);
  switchTab(_prevTab, navEl);
}

async function loadTab(tab) {
  if (tab === 'today')        await loadToday();
  if (tab === 'stats')        await loadStats();
  if (tab === 'achievements') await loadAchievements();
  if (tab === 'reminders')    await loadReminders();
  if (tab === 'profile')      await loadProfile();
  if (tab === 'habits')       await loadHabits();
  if (tab === 'bozor') {
    await loadShop();
  }
  loaded[tab] = true;
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
  const color = percent >= 100 ? '#10B981' : percent >= 50 ? '#059669' : '#F59E0B';
  const offset = circ * 0.25;
  return `<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
    <circle cx="${size/2}" cy="${size/2}" r="${r}" fill="none" stroke="#B4BDB8" stroke-width="7"/>
    <circle cx="${size/2}" cy="${size/2}" r="${r}" fill="none" stroke="${color}" stroke-width="7"
      stroke-dasharray="${dash} ${gap}"
      stroke-dashoffset="${offset}"
      stroke-linecap="round"/>
    <text x="${size/2}" y="${size/2 + 6}" text-anchor="middle"
      font-family="DM Mono,monospace" font-size="18" font-weight="600" fill="#1E3A2F">${percent}%</text>
  </svg>`;
}

function jonRingHTML(jon, size = 80) {
  const r = (size - 12) / 2;
  const circ = 2 * Math.PI * r;
  const dash = circ * Math.min(jon, 100) / 100;
  const gap  = circ - dash;
  const color = jon >= 60 ? '#10B981' : jon >= 30 ? '#F59E0B' : '#EF4444';
  const offset = circ * 0.25;
  return `<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
    <circle cx="${size/2}" cy="${size/2}" r="${r}" fill="none" stroke="#B4BDB8" stroke-width="7"/>
    <circle cx="${size/2}" cy="${size/2}" r="${r}" fill="none" stroke="${color}" stroke-width="7"
      stroke-dasharray="${dash} ${gap}"
      stroke-dashoffset="${offset}"
      stroke-linecap="round"/>
    <text x="${size/2}" y="${size/2 + 6}" text-anchor="middle"
      font-family="DM Mono,monospace" font-size="18" font-weight="600" fill="#1E3A2F">${jon}%</text>
  </svg>`;
}

