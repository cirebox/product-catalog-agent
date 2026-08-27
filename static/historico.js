/**
 * Histórico de Vendas — Gerenciamento de Vendas
 * Lista com filtros por período e status, detalhe da venda.
 */

const API = "";

// State
let currentPage = 1;

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

function paymentBadge(status) {
  if (status === "pago") return '<span class="payment-badge payment-pago">Pago</span>';
  if (status === "pendente") return '<span class="payment-badge payment-pendente">Pendente</span>';
  return `<span class="payment-badge payment-atrasado">${status}</span>`;
}

// --- Load Sales ---
async function loadSales(page = 1) {
  currentPage = page;
  const dateFrom = document.getElementById("filter-date-from").value;
  const dateTo = document.getElementById("filter-date-to").value;
  const status = document.getElementById("filter-status").value;

  try {
    const params = new URLSearchParams({ page, limit: 20 });
    if (dateFrom) params.set("date_from", dateFrom);
    if (dateTo) params.set("date_to", dateTo);
    if (status) params.set("payment_status", status);

    const data = await apiFetch(`/v1/sales?${params}`);
    const el = document.getElementById("sales-list");

    // Calcular resumo
    updateSummary(data.items);

    if (data.items.length === 0) {
      show(el, '<p class="text-muted">Nenhuma venda encontrada para o período selecionado.</p>');
      document.getElementById("pagination").innerHTML = "";
      return;
    }

    const rows = data.items.map(sale => {
      const itemCount = sale.items?.length || 0;
      const customerName = sale.customer_name || "Cliente avulso";

      return `
        <div class="sale-card" onclick="openDetail('${sale.id}')">
          <div class="sale-card-header">
            <strong>#${sale.id.substring(0, 8)}</strong>
            ${paymentBadge(sale.payment_status)}
          </div>
          <div class="sale-card-body">
            ${customerName} · ${itemCount} itens · ${formatBRL(sale.total)}
          </div>
          <div class="sale-card-footer">
            <span>${formatDate(sale.sale_date)}</span>
            <span>${sale.payment_method.toUpperCase()}</span>
          </div>
        </div>
      `;
    }).join("");

    show(el, rows);
    renderPagination(data.page, data.pages);
  } catch (e) {
    alert(`Erro: ${e.message}`);
  }
}

// --- Summary ---
function updateSummary(sales) {
  const total = sales.reduce((sum, s) => sum + s.total, 0);
  const count = sales.length;
  const paid = sales.filter(s => s.payment_status === "pago").length;
  const pending = sales.filter(s => s.payment_status === "pendente").length;
  const pendingTotal = sales
    .filter(s => s.payment_status === "pendente")
    .reduce((sum, s) => sum + s.total, 0);

  const html = `
    <div class="summary-card">
      <div class="summary-value">${count}</div>
      <div class="summary-label">Vendas</div>
    </div>
    <div class="summary-card">
      <div class="summary-value">${formatBRL(total)}</div>
      <div class="summary-label">Faturamento</div>
    </div>
    <div class="summary-card">
      <div class="summary-value">${paid}</div>
      <div class="summary-label">Pagas</div>
    </div>
    <div class="summary-card">
      <div class="summary-value">${pending}</div>
      <div class="summary-label">Pendentes</div>
    </div>
    <div class="summary-card">
      <div class="summary-value">${formatBRL(pendingTotal)}</div>
      <div class="summary-label">Em aberto</div>
    </div>
  `;

  show("summary-cards", html);
}

// --- Pagination ---
function renderPagination(page, pages) {
  if (pages <= 1) {
    document.getElementById("pagination").innerHTML = "";
    return;
  }

  let html = '<div class="pagination-btns">';
  if (page > 1) html += `<button class="btn-sm" onclick="loadSales(${page - 1})">← Anterior</button>`;
  html += `<span class="text-muted">Página ${page} de ${pages}</span>`;
  if (page < pages) html += `<button class="btn-sm" onclick="loadSales(${page + 1})">Próxima →</button>`;
  html += "</div>";

  document.getElementById("pagination").innerHTML = html;
}

// --- Sale Detail ---
async function openDetail(saleId) {
  try {
    const sale = await apiFetch(`/v1/sales/${saleId}`);

    let itemsHtml = "";
    if (sale.items && sale.items.length > 0) {
      let totalCommission = 0;
      itemsHtml = sale.items.map(item => {
        const commission = (item.cost_price || 0) > 0
          ? (item.unit_price - item.cost_price) * item.quantity
          : 0;
        totalCommission += commission;
        return `
          <div class="sale-detail-item">
            <span>${item.quantity}x ${item.product_name || item.product_id}</span>
            <span>${formatBRL(item.subtotal || item.quantity * item.unit_price)}</span>
            ${commission > 0 ? `<span class="text-sm" style="color:var(--wa-green)">+${formatBRL(commission)}</span>` : ""}
          </div>
        `;
      }).join("");
      if (totalCommission > 0) {
        itemsHtml += `
          <div class="sale-detail-item" style="border-top:1px solid var(--wa-border);padding-top:8px;margin-top:4px">
            <strong>Comissão total</strong>
            <strong style="color:var(--wa-green)">${formatBRL(totalCommission)}</strong>
          </div>
        `;
      }
    } else {
      itemsHtml = '<p class="text-muted">Sem itens registrados</p>';
    }

    const html = `
      <div class="sale-detail-header">
        <div>
          <strong>Venda #${sale.id.substring(0, 8)}</strong><br>
          <span class="text-muted">${formatDate(sale.sale_date)}</span>
        </div>
        ${paymentBadge(sale.payment_status)}
      </div>

      <div class="form-group">
        <label>Cliente</label>
        <div>${sale.customer_name || "Cliente avulso"}</div>
        ${sale.customer_phone ? `<div class="text-sm text-muted">${sale.customer_phone}</div>` : ""}
      </div>

      <div class="form-group">
        <label>Itens</label>
      </div>
      <div class="sale-detail-items">
        ${itemsHtml}
      </div>

      <div class="sale-detail-total">
        <span>Total</span>
        <span>${formatBRL(sale.total)}</span>
      </div>

      ${sale.discount > 0 ? `
        <div class="form-group">
          <label>Desconto</label>
          <div>${formatBRL(sale.discount)}</div>
        </div>
      ` : ""}

      <div class="form-group">
        <label>Pagamento</label>
        <div>${sale.payment_method.toUpperCase()}</div>
        ${sale.payment_days ? `<div class="text-sm text-muted">Prazo: ${sale.payment_days} dias</div>` : ""}
        ${sale.due_date ? `<div class="text-sm text-muted">Vencimento: ${formatDate(sale.due_date)}</div>` : ""}
      </div>

      ${sale.paid_date ? `
        <div class="form-group">
          <label>Pago em</label>
          <div>${formatDate(sale.paid_date)} ${sale.paid_amount ? `- ${formatBRL(sale.paid_amount)}` : ""}</div>
        </div>
      ` : ""}
    `;

    show("sale-detail-content", html);
    document.getElementById("modal-detail").classList.remove("hidden");
  } catch (e) {
    alert(`Erro: ${e.message}`);
  }
}

// --- Clear Filters ---
function clearFilters() {
  document.getElementById("filter-date-from").value = "";
  document.getElementById("filter-date-to").value = "";
  document.getElementById("filter-status").value = "";
  loadSales(1);
}

// --- Modal ---
function closeModal(modalId) {
  document.getElementById(modalId).classList.add("hidden");
}

// --- Init: Set default date range (last 30 days) ---
function initDates() {
  const today = new Date();
  const thirtyDaysAgo = new Date(today);
  thirtyDaysAgo.setDate(today.getDate() - 30);

  document.getElementById("filter-date-to").value = today.toISOString().split("T")[0];
  document.getElementById("filter-date-from").value = thirtyDaysAgo.toISOString().split("T")[0];
}

initDates();
loadSales();
