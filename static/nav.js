/**
 * Shared Navigation — Product Catalog Agent
 * Hamburger menu with drawer navigation grouped by section.
 */

function renderNav(activePage) {
  const sections = [
    {
      title: "Atendimento",
      items: [
        { id: "chat", label: "Atendente", icon: "🤖" },
        { id: "pdv", label: "PDV", icon: "🛒" },
      ],
    },
    {
      title: "Cadastros",
      items: [
        { id: "clientes", label: "Clientes", icon: "👥" },
        { id: "produtos", label: "Produtos", icon: "📦" },
      ],
    },
    {
      title: "Relatórios",
      items: [
        { id: "historico", label: "Histórico", icon: "📋" },
        { id: "financeiro", label: "Financeiro", icon: "💰" },
      ],
    },
  ];

  // Find active label
  let activeLabel = "Atendente";
  for (const s of sections) {
    const found = s.items.find((p) => p.id === activePage);
    if (found) {
      activeLabel = found.label;
      break;
    }
  }

  // Create header structure
  const header = document.querySelector(".app-header");
  if (!header) return;

  header.innerHTML = `
    <button class="hamburger-btn" id="menu-toggle" aria-label="Menu">
      <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
        <path d="M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z"/>
      </svg>
    </button>
    <div class="header-profile">
      <div class="header-title">
        <span class="app-name">Maria Assistente</span>
        <div class="header-info">
          <span class="header-status online">Online</span>
        </div>
      </div>
    </div>
  `;

  // Create drawer overlay
  const drawer = document.createElement("div");
  drawer.className = "drawer-overlay hidden";
  drawer.id = "drawer-overlay";

  const navHtml = sections
    .map(
      (s) => `
    <div class="drawer-section">
      <div class="drawer-section-title">${s.title}</div>
      ${s.items
        .map(
          (p) => `
        <a href="/${p.id}" class="drawer-item ${p.id === activePage ? "active" : ""}">
          <span class="drawer-icon">${p.icon}</span>
          <span class="drawer-label">${p.label}</span>
        </a>
      `
        )
        .join("")}
    </div>
  `
    )
    .join("");

  drawer.innerHTML = `
    <div class="drawer-content">
      <div class="drawer-header">
        <span class="drawer-title">Menu</span>
        <button class="drawer-close" id="menu-close">✕</button>
      </div>
      <nav class="drawer-nav">${navHtml}</nav>
    </div>
  `;
  document.body.appendChild(drawer);

  // Toggle drawer
  const toggleBtn = document.getElementById("menu-toggle");
  const closeBtn = document.getElementById("menu-close");

  toggleBtn?.addEventListener("click", () => {
    drawer.classList.remove("hidden");
  });

  closeBtn?.addEventListener("click", () => {
    drawer.classList.add("hidden");
  });

  drawer?.addEventListener("click", (e) => {
    if (e.target === drawer) {
      drawer.classList.add("hidden");
    }
  });
}
