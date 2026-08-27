/**
 * PDV — Ponto de Venda
 * JavaScript for PDV page with customer identification flow.
 */

const API = "";

// State
let selectedCustomer = null;
let saleItems = [];

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

// --- Screen Navigation ---
function showSelectCustomer() {
  selectedCustomer = null;
  document.getElementById("section-select-customer").classList.remove("hidden");
  document.getElementById("section-new-customer").classList.add("hidden");
  document.getElementById("section-sale").classList.add("hidden");
  loadRecentCustomers();
}

function showNewCustomerForm() {
  document.getElementById("section-select-customer").classList.add("hidden");
  document.getElementById("section-new-customer").classList.remove("hidden");
  document.getElementById("section-sale").classList.add("hidden");
}

function showSaleSection() {
  document.getElementById("section-select-customer").classList.add("hidden");
  document.getElementById("section-new-customer").classList.add("hidden");
  document.getElementById("section-sale").classList.remove("hidden");
  updateCustomerBadge();
  loadCustomerAlerts();
}

// --- Customer Search ---
async function searchCustomer(term) {
  if (!term) {
    hide("search-results");
    return;
  }

  try {
    const data = await apiFetch(`/v1/customers?search=${encodeURIComponent(term)}&limit=10`);
    const el = document.getElementById("search-results");

    if (data.items.length === 0) {
      show(el, `
        <p>Nenhum cliente encontrado.</p>
        <button class="btn btn-primary btn-sm" onclick="showNewCustomerForm()">Cadastrar novo</button>
      `);
      return;
    }

    const rows = data.items.map(c => `
      <div class="customer-item" onclick="selectCustomer('${c.id}')">
        <div class="customer-info">
          <strong>${c.name}</strong>
          <span class="text-muted">${c.phone}</span>
        </div>
      </div>
    `).join("");

    show(el, rows);
  } catch (e) {
    alert(`Erro: ${e.message}`);
  }
}

async function loadRecentCustomers() {
  try {
    const data = await apiFetch("/v1/customers/recent");
    const el = document.getElementById("recent-customers");

    if (data.length === 0) {
      show(el, '<p class="text-muted">Nenhum cliente cadastrado ainda.</p>');
      return;
    }

    const rows = data.map(c => `
      <div class="customer-item" onclick="selectCustomer('${c.id}')">
        <div class="customer-info">
          <strong>${c.name}</strong>
          <span class="text-muted">${c.phone}</span>
          ${c.last_sale_date ? `<span class="text-muted text-sm">Última compra: ${c.last_sale_date}</span>` : ""}
        </div>
      </div>
    `).join("");

    show(el, rows);
  } catch (e) {
    console.error("Erro ao carregar recentes:", e);
  }
}

async function selectCustomer(customerId) {
  try {
    selectedCustomer = await apiFetch(`/v1/customers/${customerId}`);
    showSaleSection();
  } catch (e) {
    alert(`Erro: ${e.message}`);
  }
}

function startCashSale() {
  selectedCustomer = null;
  showSaleSection();
}

// --- New Customer Form ---
document.getElementById("new-customer-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const body = {
    name: document.getElementById("new-name").value.trim(),
    phone: document.getElementById("new-phone").value.trim(),
    email: document.getElementById("new-email").value.trim() || null,
  };

  try {
    selectedCustomer = await apiFetch("/v1/customers", {
      method: "POST",
      body: JSON.stringify(body),
    });

    // Add initial note if provided
    const noteContent = document.getElementById("new-note").value.trim();
    if (noteContent) {
      await apiFetch(`/v1/customers/${selectedCustomer.id}/notes`, {
        method: "POST",
        body: JSON.stringify({ content: noteContent, note_type: "observacao" }),
      });
    }

    document.getElementById("new-customer-form").reset();
    showSaleSection();
  } catch (e) {
    alert(`Erro: ${e.message}`);
  }
});

// --- Customer Badge ---
function updateCustomerBadge() {
  const el = document.getElementById("customer-badge-text");
  if (selectedCustomer) {
    el.textContent = `${selectedCustomer.name} — ${selectedCustomer.phone}`;
  } else {
    el.textContent = "Venda sem cliente (avulso)";
  }
}

// --- Customer Alerts ---
async function loadCustomerAlerts() {
  const el = document.getElementById("customer-alerts");
  if (!selectedCustomer) {
    hide(el);
    return;
  }

  try {
    const alerts = await apiFetch(`/v1/customers/${selectedCustomer.id}/alerts`);
    let html = "";

    if (alerts.pinned_notes.length > 0) {
      html += '<div class="alerts-section"><strong>📌 Observações:</strong><ul>';
      alerts.pinned_notes.forEach(n => {
        html += `<li>${n.content}</li>`;
      });
      html += "</ul></div>";
    }

    if (alerts.open_special_orders.length > 0) {
      html += '<div class="alerts-section"><strong>🟡 Pedidos especiais abertos:</strong><ul>';
      alerts.open_special_orders.forEach(n => {
        html += `<li>${n.content}</li>`;
      });
      html += "</ul></div>";
    }

    if (html) {
      show(el, html);
    } else {
      hide(el);
    }
  } catch (e) {
    console.error("Erro ao carregar alertas:", e);
  }
}

// --- Item Lookup ---
async function lookupItem(term = null) {
  const query = (term === null ? document.getElementById("item-ref").value : term).trim();
  if (!query) {
    hide("item-preview");
    return;
  }

  try {
    const result = await apiFetch(`/v1/products/search?query=${encodeURIComponent(query)}`);
    const items = result.items || [];
    if (items.length === 0) throw new Error("Produto não encontrado");

    const qty = parseInt(document.getElementById("item-qty").value) || 1;

    if (items.length === 1) {
      // Single result: show directly
      const p = items[0];
      show("item-preview", `
        <strong>${p.ref}</strong> — ${p.description}<br>
        Preço: ${formatBRL(p.price)} | Estoque: ${p.stock}
        <button class="btn-sm" style="margin-left:12px" onclick="addItem('${p.ref}', '${p.description.replace(/'/g, "\\'")}', ${p.price}, ${p.stock}, ${qty}, ${p.cost_price || 0})">Adicionar</button>
      `);
    } else {
      // Multiple results: show list for selection
      const rows = items.map(p => `
        <div class="product-search-item">
          <div class="product-search-info">
            <strong>${p.ref}</strong> — ${p.description}<br>
            <span class="text-muted">Preço: ${formatBRL(p.price)} | Estoque: ${p.stock}</span>
          </div>
          <button class="btn-sm" onclick="addItem('${p.ref}', '${p.description.replace(/'/g, "\\'")}', ${p.price}, ${p.stock}, ${qty}, ${p.cost_price || 0})">Adicionar</button>
        </div>
      `).join("");
      show("item-preview", `<strong>${items.length} produtos encontrados:</strong>${rows}`);
    }
  } catch (e) {
    show("item-preview", `<span class="text-muted">${e.message}</span>`);
  }
}

function addItem(ref, description, price, stock, qty, costPrice) {
  if (qty > stock) {
    alert(`Estoque insuficiente. Disponível: ${stock}`);
    return;
  }

  // Check if item already exists
  const existing = saleItems.find(i => i.ref === ref);
  if (existing) {
    existing.quantity += qty;
  } else {
    saleItems.push({ ref, description, price, cost_price: costPrice || 0, quantity: qty });
  }

  renderSaleItems();
  hide("item-preview");
  document.getElementById("item-ref").value = "";
  document.getElementById("item-qty").value = 1;
}

function removeItem(ref) {
  saleItems = saleItems.filter(i => i.ref !== ref);
  renderSaleItems();
}

function renderSaleItems() {
  const el = document.getElementById("sale-items-list");
  if (saleItems.length === 0) {
    el.innerHTML = '<p class="text-muted">Nenhum item adicionado.</p>';
    updateSaleTotal();
    return;
  }

  const rows = saleItems.map(item => `
    <div class="sale-item-row">
      <div class="sale-item-info">
        <span class="sale-item-ref">${item.ref}</span>
        <span class="sale-item-desc">${item.description}</span>
        <span class="sale-item-qty">${item.quantity}x ${formatBRL(item.price)}</span>
      </div>
      <div class="sale-item-actions">
        <span>${formatBRL(item.quantity * item.price)}</span>
        <button class="btn-icon" onclick="removeItem('${item.ref}')">✕</button>
      </div>
    </div>
  `).join("");

  el.innerHTML = rows;
  updateSaleTotal();
}

function updateSaleTotal() {
  const subtotal = saleItems.reduce((sum, i) => sum + i.price * i.quantity, 0);
  const discount = parseFloat(document.getElementById("sale-discount").value) || 0;
  const total = Math.max(0, subtotal - discount);

  document.getElementById("sale-subtotal").textContent = formatBRL(subtotal);
  document.getElementById("sale-total").textContent = formatBRL(total);
}

function togglePaymentDays() {
  const method = document.getElementById("payment-method").value;
  const group = document.getElementById("payment-days-group");
  if (method === "prazo") {
    group.classList.remove("hidden");
    if (!selectedCustomer) {
      alert("Venda a prazo requer cliente identificado.");
      document.getElementById("payment-method").value = "pix";
    }
  } else {
    group.classList.add("hidden");
  }
}

// --- Register Sale ---
async function registerSale() {
  if (saleItems.length === 0) {
    alert("Adicione pelo menos um item.");
    return;
  }

  const paymentMethod = document.getElementById("payment-method").value;

  if (paymentMethod === "prazo" && !selectedCustomer) {
    alert("Venda a prazo requer cliente identificado.");
    return;
  }

  const body = {
    items: saleItems.map(i => ({
      ref: i.ref,
      description: i.description,
      price: i.price,
      cost_price: i.cost_price || 0,
      quantity: i.quantity,
    })),
    payment_method: paymentMethod,
    discount: parseFloat(document.getElementById("sale-discount").value) || 0,
    customer_id: selectedCustomer?.id || null,
  };

  if (paymentMethod === "prazo") {
    body.payment_days = parseInt(document.getElementById("payment-days").value);
  }

  try {
    const sale = await apiFetch("/v1/sales", {
      method: "POST",
      body: JSON.stringify(body),
    });

    alert(`Venda registrada!\nTotal: ${formatBRL(sale.total)}\nPagamento: ${sale.payment_method}`);

    // Reset
    saleItems = [];
    document.getElementById("sale-discount").value = 0;
    renderSaleItems();
    showSelectCustomer();
  } catch (e) {
    alert(`Erro: ${e.message}`);
  }
}

// --- Modal: Confirm Payment ---
let pendingPaymentSaleId = null;

function openPayModal(saleId, total) {
  pendingPaymentSaleId = saleId;
  document.getElementById("pay-sale-info").textContent = `Venda: ${saleId} — Total: ${formatBRL(total)}`;
  document.getElementById("pay-date").value = new Date().toISOString().split("T")[0];
  document.getElementById("pay-amount").value = total;
  document.getElementById("modal-pay").classList.remove("hidden");
}

function closeModal(modalId) {
  document.getElementById(modalId).classList.add("hidden");
}

async function confirmPayment() {
  if (!pendingPaymentSaleId) return;

  const body = {
    paid_date: document.getElementById("pay-date").value,
    paid_amount: parseFloat(document.getElementById("pay-amount").value),
    payment_method: document.getElementById("pay-method").value,
  };

  try {
    await apiFetch(`/v1/sales/${pendingPaymentSaleId}/pay`, {
      method: "POST",
      body: JSON.stringify(body),
    });
    alert("Pagamento confirmado!");
    closeModal("modal-pay");
  } catch (e) {
    alert(`Erro: ${e.message}`);
  }
}

// --- Init ---
loadRecentCustomers();
