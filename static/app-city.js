// ==============================================
// app-city.js — Shahar sahifasi (PHASE C1: placeholder)
// ==============================================
// Bog'liqlik:
//   - strings.js (S() funksiya — tarjima)
//   - app-core.js (loaded state — sahifa yuklanganini belgilash)
//
// PHASE C1 vazifasi: sahifa konteyneri ko'rinadi, "Tez orada..." matni 3 tilda.
// PHASE C2+ da bu fayl kengaytiriladi (isometric grid, binolar, API integratsiya).
// ==============================================

// ── Asosiy yuklash funksiyasi (loadTab tomonidan chaqiriladi) ──
async function loadCity() {
  const container = document.getElementById('city-content');
  if (!container) return;
  renderCityPlaceholder(container);
}

// ── Placeholder render (C1 — tez orada) ──
function renderCityPlaceholder(container) {
  const title       = S('city', 'title');
  const comingSoon  = S('city', 'coming_soon');
  const description = S('city', 'description');

  container.innerHTML = `
    <div class="city-placeholder">
      <div class="city-placeholder-icon">
        <svg width="96" height="96" viewBox="0 0 96 96" fill="none" aria-hidden="true">
          <defs>
            <linearGradient id="cityTopGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="#6BCB9C"/>
              <stop offset="100%" stop-color="#4CAF7D"/>
            </linearGradient>
            <linearGradient id="cityLeftGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="#3D9669"/>
              <stop offset="100%" stop-color="#2D8A5E"/>
            </linearGradient>
            <linearGradient id="cityRightGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="#2E7A52"/>
              <stop offset="100%" stop-color="#1F5C3D"/>
            </linearGradient>
          </defs>

          <!-- Yer (isometric platforma soyasi) -->
          <ellipse cx="48" cy="84" rx="34" ry="6" fill="#000000" opacity="0.08"/>

          <!-- 1. CHAP BINO (kichik uy) -->
          <!-- Tomi -->
          <path d="M14 58 L26 52 L38 58 L26 64 Z" fill="url(#cityTopGrad)"/>
          <!-- Chap yon (yorug') -->
          <path d="M14 58 L14 72 L26 78 L26 64 Z" fill="url(#cityLeftGrad)"/>
          <!-- O'ng yon (soyali) -->
          <path d="M38 58 L38 72 L26 78 L26 64 Z" fill="url(#cityRightGrad)"/>
          <!-- Chap yon deraza -->
          <rect x="17" y="65" width="3" height="4" fill="#FFFFFF" opacity="0.55" rx="0.3" transform="skewY(26.5)"/>
          <!-- O'ng yon deraza -->
          <rect x="30" y="78" width="3" height="4" fill="#FFFFFF" opacity="0.4" rx="0.3" transform="skewY(-26.5)"/>

          <!-- 2. MARKAZIY BINO (baland — sahar markazi) -->
          <!-- Tomi -->
          <path d="M36 38 L52 30 L68 38 L52 46 Z" fill="url(#cityTopGrad)"/>
          <!-- Chap yon (yorug') -->
          <path d="M36 38 L36 66 L52 74 L52 46 Z" fill="url(#cityLeftGrad)"/>
          <!-- O'ng yon (soyali) -->
          <path d="M68 38 L68 66 L52 74 L52 46 Z" fill="url(#cityRightGrad)"/>
          <!-- Chap yon derazalari (3 qatorda) -->
          <rect x="40" y="46" width="3" height="3" fill="#FFFFFF" opacity="0.6" rx="0.3" transform="skewY(26.5)"/>
          <rect x="46" y="46" width="3" height="3" fill="#FFFFFF" opacity="0.6" rx="0.3" transform="skewY(26.5)"/>
          <rect x="40" y="55" width="3" height="3" fill="#FFFFFF" opacity="0.6" rx="0.3" transform="skewY(26.5)"/>
          <rect x="46" y="55" width="3" height="3" fill="#FFFFFF" opacity="0.6" rx="0.3" transform="skewY(26.5)"/>
          <!-- O'ng yon derazalari -->
          <rect x="56" y="74" width="3" height="3" fill="#FFFFFF" opacity="0.4" rx="0.3" transform="skewY(-26.5)"/>
          <rect x="62" y="74" width="3" height="3" fill="#FFFFFF" opacity="0.4" rx="0.3" transform="skewY(-26.5)"/>
          <rect x="56" y="83" width="3" height="3" fill="#FFFFFF" opacity="0.4" rx="0.3" transform="skewY(-26.5)"/>
          <rect x="62" y="83" width="3" height="3" fill="#FFFFFF" opacity="0.4" rx="0.3" transform="skewY(-26.5)"/>

          <!-- 3. O'NG BINO (o'rtacha) -->
          <!-- Tomi -->
          <path d="M62 52 L74 46 L86 52 L74 58 Z" fill="url(#cityTopGrad)"/>
          <!-- Chap yon (yorug') -->
          <path d="M62 52 L62 68 L74 74 L74 58 Z" fill="url(#cityLeftGrad)"/>
          <!-- O'ng yon (soyali) -->
          <path d="M86 52 L86 68 L74 74 L74 58 Z" fill="url(#cityRightGrad)"/>
          <!-- Chap yon derazasi -->
          <rect x="65" y="58" width="3" height="3" fill="#FFFFFF" opacity="0.55" rx="0.3" transform="skewY(26.5)"/>
          <rect x="65" y="65" width="3" height="3" fill="#FFFFFF" opacity="0.55" rx="0.3" transform="skewY(26.5)"/>
          <!-- O'ng yon derazasi -->
          <rect x="78" y="71" width="3" height="3" fill="#FFFFFF" opacity="0.4" rx="0.3" transform="skewY(-26.5)"/>
          <rect x="78" y="78" width="3" height="3" fill="#FFFFFF" opacity="0.4" rx="0.3" transform="skewY(-26.5)"/>
        </svg>
      </div>
      <div class="city-placeholder-title">${title}</div>
      <div class="city-placeholder-soon">${comingSoon}</div>
      <div class="city-placeholder-desc">${description}</div>
    </div>
  `;
}

// ── Eslatma kelajakdagi bosqichlar uchun ──
// PHASE C2: renderCityGrid() — 20x20 isometric grid
// PHASE C3: renderBuildings(buildings) — binolar va dekoratsiyalar
// PHASE C4: loadCityFromAPI() — GET /api/city/<uid>
// PHASE C5: handleBuildingDrag(), handleBuildingClick() — interaktivlik
// PHASE C6: renderDecorationsShop() — bozor modal
// PHASE C7: tarjimalar strings.js'ga qo'shiladi
// PHASE C8: premium CSS polish (beige/gold accent, 3D rendering)
