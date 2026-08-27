/**
 * Financeiro — Dashboard de Cobrança
 * Lista consolidada de clientes com fiado pendente.
 */

const API = "";

// State
let allData = { customers: [], summary: {} };

// --- Helpers ---
function formatBRL(value) {
  return `R$ ${Number(value).toFixed(2).replace(".", ",")}`;
}

function show(el, html) {
  if (typeof el === "string") el = document.getElementById(el);
  el.innerHTML = html;
  el.classList.remove("hidden");
}

function hide(el) {
  if (typeof el === "string") el = document.getElementById(el);
  el.innerHTML = "";
  el.classList.add("hidden");
}

async function apiFetch(path, opts = {}) {
  const res = await fetch(API + path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Erro na API");
  }
  if (res.status === 204) return null;
  return res.json();
}

// --- Load Data ---
async function loadData() {
  try {
    allData = await apiFetch("/v1/customers/credit/pending");
    renderSummary();
    renderList();
  } catch (e) {
    alert(`Erro: ${e.message}`);
  }
}

// --- Summary ---
function renderSummary() {
  const { summary } = allData;
  const html = `
    <div class="summary-card">
      <div class="summary-value">${summary.total_customers || 0}</div>
      <div class="summary-label">Clientes devendo</div>
    </div>
    <div class="summary-card">
      <div class="summary-value">${formatBRL(summary.total_pending || 0)}</div>
      <div class="summary-label">Total pendente</div>
    </div>
    <div class="summary-card">
      <div class="summary-value">${formatBRL(summary.total_overdue || 0)}</div>
      <div class="summary-label">🔴 Atrasado</div>
    </div>
    <div class="summary-card">
      <div class="summary-value">${formatBRL((summary.total_pending || 0) - (summary.total_overdue || 0))}</div>
      <div class="summary-label">🟢 Em dia</div>
    </div>
  `;
  show("summary-cards", html);
}

// --- List ---
function renderList() {
  const search = document.getElementById("search-input").value.trim().toLowerCase();
  const filterStatus = document.getElementById("filter-status").value;
  const el = document.getElementById("customers-list");

  let customers = allData.customers || [];

  // Filtrar por busca
  if (search) {
    customers = customers.filter(c =>
      c.customer_name.toLowerCase().includes(search) ||
      c.customer_phone.includes(search)
    );
  }

  // Filtrar por status
  if (filterStatus === "atrasado") {
    customers = customers.filter(c => c.has_overdue);
  } else if (filterStatus === "em_dia") {
    customers = customers.filter(c => !c.has_overdue);
  }

  if (customers.length === 0) {
    show(el, '<p class="text-muted">Nenhum cliente com fiado pendente.</p>');
    return;
  }

  const rows = customers.map(c => `
    <div class="customer-item" onclick="openDetail('${c.customer_id}')">
      <div class="customer-info">
        <strong>${c.customer_name}</strong>
        <span class="text-muted">${c.customer_phone}</span>
        <span class="text-sm">
          ${c.has_overdue ? "🔴 Atrasado" : "🟢 Em dia"} ·
          ${c.sales.length} venda(s) ·
          ${formatBRL(c.total_pending)}
        </span>
      </div>
      <span class="text-muted">→</span>
    </div>
  `).join("");

  show(el, rows);
}

// --- Search via shared debounce ---
function debounceSearch() {
  debouncedSearch("search-input", () => renderList());
}

// --- Detail Modal ---
function openDetail(customerId) {
  const customer = allData.customers.find(c => c.customer_id === customerId);
  if (!customer) return;

  const salesHtml = customer.sales.map(s => `
    <div class="sale-card">
      <div class="sale-card-header">
        <strong>#${s.sale_id.substring(0, 8)}</strong>
        ${s.status === "atrasado"
          ? `<span class="payment-badge payment-atrasado">🔴 ${s.days_overdue} dias atrasado</span>`
          : '<span class="payment-badge payment-pendente">🟢 Em dia</span>'
        }
      </div>
      <div class="sale-card-body">
        ${formatBRL(s.total)} · Vencimento: ${formatDate(s.due_date)}
      </div>
    </div>
  `).join("");

  const html = `
    <div class="customer-detail-info">
      <div><strong>${customer.customer_name}</strong></div>
      <div>📱 ${customer.customer_phone}</div>
      <div>💰 Total pendente: <strong>${formatBRL(customer.total_pending)}</strong></div>
    </div>
    <h4 class="section-subtitle">Vendas Pendentes</h4>
    ${salesHtml}
  `;

  show("detail-content", html);
  document.getElementById("modal-detail").classList.remove("hidden");
}

// --- Generate Report ---
function generateReport() {
  const { customers, summary } = allData;
  if (!customers || customers.length === 0) {
    alert("Nenhum cliente com fiado pendente.");
    return;
  }

  const today = new Date().toLocaleDateString("pt-BR");
  let report = `📋 RELATÓRIO DE COBRANÇA\n`;
  report += `📅 Gerado em: ${today}\n`;
  report += `━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n`;
  report += `📊 RESUMO\n`;
  report += `Clientes devendo: ${summary.total_customers}\n`;
  report += `Total pendente: ${formatBRL(summary.total_pending)}\n`;
  report += `Atrasado: ${formatBRL(summary.total_overdue)}\n\n`;
  report += `━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n`;

  customers.forEach((c, i) => {
    const status = c.has_overdue ? "🔴 ATRASADO" : "🟢 Em dia";
    report += `${i + 1}. ${c.customer_name}\n`;
    report += `   📱 ${c.customer_phone}\n`;
    report += `   💰 Total: ${formatBRL(c.total_pending)} — ${status}\n`;

    c.sales.forEach(s => {
      const sStatus = s.status === "atrasado" ? `${s.days_overdue}d atrasado` : `até ${formatDate(s.due_date)}`;
      report += `   • #${s.sale_id.substring(0, 8)} — ${formatBRL(s.total)} — ${sStatus}\n`;
    });
    report += `\n`;
  });

  report += `━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n`;
  report += `Total: ${formatBRL(summary.total_pending)}\n`;

  show("report-content", report);
  document.getElementById("modal-report").classList.remove("hidden");
}

// --- Copy Report ---
function copyReport() {
  const text = document.getElementById("report-content").textContent;
  navigator.clipboard.writeText(text).then(() => {
    alert("Relatório copiado!");
  }).catch(() => {
    // Fallback
    const textarea = document.createElement("textarea");
    textarea.value = text;
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    document.body.removeChild(textarea);
    alert("Relatório copiado!");
  });
}

// --- Share WhatsApp ---
function shareWhatsApp() {
  const { customers, summary } = allData;
  if (!customers || customers.length === 0) {
    alert("Nenhum cliente com fiado pendente.");
    return;
  }

  let msg = `📋 *RELATÓRIO DE COBRANÇA*\n`;
  msg += `📅 ${new Date().toLocaleDateString("pt-BR")}\n\n`;

  customers.forEach((c, i) => {
    const status = c.has_overdue ? "🔴 ATRASADO" : "🟢 Em dia";
    msg += `*${c.customer_name}*\n`;
    msg += `📱 ${c.customer_phone}\n`;
    msg += `💰 ${formatBRL(c.total_pending)} — ${status}\n\n`;
  });

  msg += `━━━━━━━━━━━━━━━━━━\n`;
  msg += `Total: *${formatBRL(summary.total_pending)}*\n`;

  const encoded = encodeURIComponent(msg);
  window.open(`https://wa.me/?text=${encoded}`, "_blank");
}

// --- Modal ---
function closeModal(modalId) {
  document.getElementById(modalId).classList.add("hidden");
}

// --- Init ---
loadData();
