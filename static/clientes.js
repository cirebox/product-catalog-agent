/**
 * Clientes — Gerenciamento de Clientes
 * JavaScript for Clientes page with tabs.
 */

const API = "";

// State
let currentCustomerId = null;

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
function showList() {
  document.getElementById("section-list").classList.remove("hidden");
  document.getElementById("section-new").classList.add("hidden");
  document.getElementById("section-detail").classList.add("hidden");
  loadCustomers();
}

function showNewCustomer() {
  document.getElementById("section-list").classList.add("hidden");
  document.getElementById("section-new").classList.remove("hidden");
  document.getElementById("section-detail").classList.add("hidden");
}

function showDetail() {
  document.getElementById("section-list").classList.add("hidden");
  document.getElementById("section-new").classList.add("hidden");
  document.getElementById("section-detail").classList.remove("hidden");
}

// --- Customer List ---
async function loadCustomers(search = "") {
  try {
    const data = await apiFetch(`/v1/customers?search=${encodeURIComponent(search)}&limit=50`);
    const el = document.getElementById("customers-list");

    if (data.items.length === 0) {
      show(el, '<p class="text-muted">Nenhum cliente encontrado.</p>');
      return;
    }

    const rows = data.items.map(c => `
      <div class="customer-item" onclick="openCustomer('${c.id}')">
        <div class="customer-info">
          <strong>${c.name}</strong>
          <span class="text-muted">${c.phone}</span>
          ${c.email ? `<span class="text-muted text-sm">${c.email}</span>` : ""}
        </div>
        <span class="text-muted">→</span>
      </div>
    `).join("");

    show(el, rows);
  } catch (e) {
    alert(`Erro: ${e.message}`);
  }
}

// --- Search via shared debounce ---
function debounceSearch() {
  debouncedSearch("search-input", (term) => loadCustomers(term));
}

// --- New Customer ---
document.getElementById("new-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const body = {
    name: document.getElementById("form-name").value.trim(),
    phone: document.getElementById("form-phone").value.trim(),
    email: document.getElementById("form-email").value.trim() || null,
  };

  try {
    await apiFetch("/v1/customers", {
      method: "POST",
      body: JSON.stringify(body),
    });
    document.getElementById("new-form").reset();
    showList();
  } catch (e) {
    alert(`Erro: ${e.message}`);
  }
});

// --- Customer Detail ---
async function openCustomer(customerId) {
  currentCustomerId = customerId;
  showDetail();

  try {
    const customer = await apiFetch(`/v1/customers/${customerId}`);
    document.getElementById("detail-name").textContent = customer.name;
    show("detail-info", `
      📱 ${customer.phone} ${customer.email ? `| 📧 ${customer.email}` : ""}<br>
      📅 Cliente desde: ${customer.created_at}
    `);

    // Load tabs
    await loadHistory();
    await loadNotes();
    await loadCredit();
    switchTab("history");
  } catch (e) {
    alert(`Erro: ${e.message}`);
  }
}

// --- Tabs ---
function switchTab(tabName) {
  // Update tab buttons
  document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
  document.querySelector(`[data-tab="${tabName}"]`).classList.add("active");

  // Update tab content
  document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
  document.getElementById(`tab-${tabName}`).classList.add("active");
}

// --- History Tab ---
async function loadHistory() {
  const el = document.getElementById("tab-history");
  try {
    const data = await apiFetch(`/v1/sales?customer_id=${currentCustomerId}&limit=20`);

    if (data.items.length === 0) {
      show(el, '<p class="text-muted">Nenhuma venda registrada.</p>');
      return;
    }

    const rows = data.items.map(sale => {
      const itemsList = sale.items.map(i =>
        `${i.quantity}x ${i.product_name} (${i.variant_color || ""}/${i.variant_size || ""}) ${formatBRL(i.subtotal)}`
      ).join("<br>");

      const statusIcon = sale.payment_status === "pago" ? "✅" : "⏳";

      return `
        <div class="sale-card">
          <div class="sale-card-header">
            <strong>🧾 Venda #${sale.id.substring(0, 8)}</strong>
            <span>${sale.sale_date}</span>
          </div>
          <div class="sale-card-body">
            ${sale.items.length} itens • ${formatBRL(sale.total)}
            <br>Pagamento: ${sale.payment_method.toUpperCase()} ${statusIcon}
            ${sale.due_date ? `<br>Vencimento: ${sale.due_date}` : ""}
          </div>
          <div class="sale-card-items">${itemsList}</div>
          ${sale.payment_status === "pendente" ? `
            <div class="sale-card-actions">
              <button class="btn btn-sm" onclick="openPayModal('${sale.id}', ${sale.total})">✅ Marcar Pago</button>
            </div>
          ` : ""}
        </div>
      `;
    }).join("");

    show(el, rows);
  } catch (e) {
    show(el, '<p class="text-muted">Erro ao carregar histórico.</p>');
  }
}

// --- Notes Tab ---
async function loadNotes() {
  const el = document.getElementById("tab-notes");
  try {
    const notes = await apiFetch(`/v1/customers/${currentCustomerId}/notes`);
    let html = `
      <button class="btn btn-primary" onclick="openNoteModal()" style="margin-bottom:12px">
        ➕ Adicionar Observação
      </button>
    `;

    // Pinned notes
    const pinned = notes.filter(n => n.pinned);
    if (pinned.length > 0) {
      html += '<h4 class="section-subtitle">📌 Fixadas</h4>';
      html += pinned.map(n => renderNote(n)).join("");
    }

    // Special orders
    const special = notes.filter(n => n.note_type === "pedido_especial");
    if (special.length > 0) {
      html += '<h4 class="section-subtitle">Pedidos Especiais</h4>';
      html += special.map(n => renderNote(n)).join("");
    }

    // General observations
    const general = notes.filter(n => n.note_type === "observacao" && !n.pinned);
    if (general.length > 0) {
      html += '<h4 class="section-subtitle">Observações Gerais</h4>';
      html += general.map(n => renderNote(n)).join("");
    }

    // Preferences
    const prefs = notes.filter(n => n.note_type === "preferencia" && !n.pinned);
    if (prefs.length > 0) {
      html += '<h4 class="section-subtitle">Preferências</h4>';
      html += prefs.map(n => renderNote(n)).join("");
    }

    show(el, html);
  } catch (e) {
    show(el, '<p class="text-muted">Erro ao carregar observações.</p>');
  }
}

function renderNote(note) {
  const typeIcons = {
    observacao: "💬",
    preferencia: "📌",
    pedido_especial: "🟡",
  };
  const icon = typeIcons[note.note_type] || "📝";

  let statusBadge = "";
  if (note.note_type === "pedido_especial") {
    const statusColors = { aberto: "🟡", atendido: "🟢", cancelado: "🔴" };
    statusBadge = ` <span class="badge-${note.status}">${statusColors[note.status] || ""} ${note.status}</span>`;
  }

  let actions = "";
  if (note.note_type === "pedido_especial") {
    if (note.status === "aberto") {
      actions += `<button class="btn-sm" onclick="updateNoteStatus(${note.id}, 'atendido')">✅ Atendido</button>`;
      actions += `<button class="btn-sm" onclick="updateNoteStatus(${note.id}, 'cancelado')">❌ Cancelar</button>`;
    }
  }
  actions += `<button class="btn-sm" onclick="togglePin(${note.id}, ${note.pinned})">${note.pinned ? "Desafixar" : "📌 Fixar"}</button>`;
  actions += `<button class="btn-sm" onclick="deleteNote(${note.id})">🗑️</button>`;

  return `
    <div class="note-card ${note.pinned ? "pinned" : ""}">
      <div class="note-header">
        <span>${icon} ${note.note_type === "pedido_especial" ? "Pedido Especial" : note.note_type === "preferencia" ? "Preferência" : "Observação"}</span>
        ${statusBadge}
      </div>
      <div class="note-content">${note.content}</div>
      <div class="note-footer">
        <span class="text-muted text-sm">${note.created_at}</span>
        <div class="note-actions">${actions}</div>
      </div>
    </div>
  `;
}

// --- Note CRUD ---
function openNoteModal() {
  document.getElementById("note-content").value = "";
  document.getElementById("note-pinned").checked = false;
  document.querySelectorAll('input[name="note-type"]').forEach(r => r.checked = r.value === "observacao");
  document.getElementById("modal-note").classList.remove("hidden");
}

function closeModal(modalId) {
  document.getElementById(modalId).classList.add("hidden");
}

async function saveNote() {
  const noteType = document.querySelector('input[name="note-type"]:checked').value;
  const content = document.getElementById("note-content").value.trim();
  const pinned = document.getElementById("note-pinned").checked;

  if (!content) {
    alert("Preencha o conteúdo.");
    return;
  }

  try {
    await apiFetch(`/v1/customers/${currentCustomerId}/notes`, {
      method: "POST",
      body: JSON.stringify({ note_type: noteType, content, pinned }),
    });
    closeModal("modal-note");
    await loadNotes();
  } catch (e) {
    alert(`Erro: ${e.message}`);
  }
}

async function togglePin(noteId, currentlyPinned) {
  try {
    await apiFetch(`/v1/customers/${currentCustomerId}/notes/${noteId}/pin`, {
      method: "PUT",
    });
    await loadNotes();
  } catch (e) {
    alert(`Erro: ${e.message}`);
  }
}

async function updateNoteStatus(noteId, status) {
  try {
    await apiFetch(`/v1/customers/${currentCustomerId}/notes/${noteId}/status`, {
      method: "PUT",
      body: JSON.stringify({ status }),
    });
    await loadNotes();
  } catch (e) {
    alert(`Erro: ${e.message}`);
  }
}

async function deleteNote(noteId) {
  if (!confirm("Excluir esta observação?")) return;
  try {
    await apiFetch(`/v1/customers/${currentCustomerId}/notes/${noteId}`, {
      method: "DELETE",
    });
    await loadNotes();
  } catch (e) {
    alert(`Erro: ${e.message}`);
  }
}

// --- Credit Tab ---
async function loadCredit() {
  const el = document.getElementById("tab-credit");
  try {
    const data = await apiFetch(`/v1/customers/${currentCustomerId}/credit`);

    let html = `<div class="credit-summary">Total pendente: <strong>${formatBRL(data.total_pending)}</strong></div>`;

    // Pending
    if (data.pending.length > 0) {
      html += '<h4 class="section-subtitle">Pendentes</h4>';
      data.pending.forEach(sale => {
        const statusIcon = sale.status === "atrasado" ? "🔴 VENCIDO" : "🟢 Em dia";
        const dueInfo = sale.status === "atrasado"
          ? `Vencimento: ${sale.due_date} (${sale.days_overdue} dias atrás)`
          : `Vencimento: ${sale.due_date}`;

        html += `
          <div class="credit-card ${sale.status}">
            <div class="credit-card-header">
              <strong>${statusIcon}</strong>
            </div>
            <div class="credit-card-body">
              Pedido #${sale.id.substring(0, 8)} • ${formatBRL(sale.total)}<br>
              Prazo: ${sale.payment_days} dias<br>
              ${dueInfo}
            </div>
            <div class="credit-card-actions">
              <button class="btn btn-sm" onclick="openPayModal('${sale.id}', ${sale.total})">✅ Marcar Pago</button>
            </div>
          </div>
        `;
      });
    }

    // History
    if (data.history.length > 0) {
      html += '<h4 class="section-subtitle">Histórico de pagamentos</h4>';
      data.history.forEach(sale => {
        html += `
          <div class="credit-history-item">
            #${sale.id.substring(0, 8)}  ${formatBRL(sale.total)}  ${sale.payment_method.toUpperCase()}  ✅ Pago ${sale.paid_date}
          </div>
        `;
      });
    }

    if (data.pending.length === 0 && data.history.length === 0) {
      html += '<p class="text-muted">Nenhuma venda a prazo.</p>';
    }

    show(el, html);
  } catch (e) {
    show(el, '<p class="text-muted">Erro ao carregar fiado.</p>');
  }
}

// --- Modal: Confirm Payment ---
let pendingPaymentSaleId = null;

function openPayModal(saleId, total) {
  pendingPaymentSaleId = saleId;
  document.getElementById("modal-pay")?.classList.remove("hidden");
}

async function confirmPayment() {
  if (!pendingPaymentSaleId) return;

  const body = {
    paid_date: new Date().toISOString().split("T")[0],
    paid_amount: 0,
    payment_method: "pix",
  };

  try {
    await apiFetch(`/v1/sales/${pendingPaymentSaleId}/pay`, {
      method: "POST",
      body: JSON.stringify(body),
    });
    alert("Pagamento confirmado!");
    closeModal("modal-pay");
    await loadHistory();
    await loadCredit();
  } catch (e) {
    alert(`Erro: ${e.message}`);
  }
}

// --- Init ---
loadCustomers();
