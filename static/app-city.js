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
        <svg width="80" height="80" viewBox="0 0 80 80" fill="none" aria-hidden="true">
          <defs>
            <linearGradient id="cityIconGrad" x1="0" y1="0" x2="80" y2="80" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stop-color="#5DBE8E"/>
              <stop offset="100%" stop-color="#2D8A5E"/>
            </linearGradient>
          </defs>
          <path d="M14 56 L40 38 L66 56 L66 70 L14 70 Z" fill="url(#cityIconGrad)" opacity="0.85"/>
          <rect x="22" y="48" width="8" height="8" fill="#FFFFFF" opacity="0.55" rx="1"/>
          <rect x="36" y="44" width="8" height="12" fill="#FFFFFF" opacity="0.55" rx="1"/>
          <rect x="50" y="48" width="8" height="8" fill="#FFFFFF" opacity="0.55" rx="1"/>
          <path d="M40 14 L40 38" stroke="url(#cityIconGrad)" stroke-width="2.5" stroke-linecap="round" opacity="0.4"/>
          <circle cx="40" cy="14" r="3" fill="url(#cityIconGrad)"/>
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
