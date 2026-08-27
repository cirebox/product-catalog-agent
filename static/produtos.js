/**
 * Produtos — Gerenciamento de Produtos
 * CRUD completo com busca, filtros e paginação.
 */

const API = "";

// State
let currentPage = 1;
let editingRef = null;

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

function stockBadge(stock) {
  if (stock === 0) return '<span class="stock-badge stock-out">Esgotado</span>';
  if (stock <= 5) return `<span class="stock-badge stock-low">${stock} un.</span>`;
  return `<span class="stock-badge stock-ok">${stock} un.</span>`;
}

function calcPrice() {
  const cp = parseFloat(document.getElementById("form-cost-price").value) || 0;
  const mg = parseFloat(document.getElementById("form-margin").value) || 0;
  const price = cp > 0 && mg > 0 ? cp + (cp * mg / 100) : cp;
  document.getElementById("form-price").value = price > 0 ? price.toFixed(2) : "";
}

// --- Screen Navigation ---
function showList() {
  editingRef = null;
  document.getElementById("section-list").classList.remove("hidden");
  document.getElementById("section-form").classList.add("hidden");
  document.getElementById("section-detail").classList.add("hidden");
  loadProducts();
}

function showNew() {
  editingRef = null;
  document.getElementById("form-title").textContent = "Novo Produto";
  document.getElementById("btn-submit").textContent = "Salvar Produto";
  document.getElementById("form-ref").readOnly = false;
  document.getElementById("product-form").reset();
  document.getElementById("form-stock").value = "0";
  document.getElementById("form-price").value = "";

  document.getElementById("section-list").classList.add("hidden");
  document.getElementById("section-form").classList.remove("hidden");
  document.getElementById("section-detail").classList.add("hidden");
}

function showDetail() {
  document.getElementById("section-list").classList.add("hidden");
  document.getElementById("section-form").classList.add("hidden");
  document.getElementById("section-detail").classList.remove("hidden");
}

// --- Load Products ---
async function loadProducts(page = 1) {
  currentPage = page;
  const search = document.getElementById("search-input").value.trim();
  const category = document.getElementById("filter-category").value;

  try {
    const params = new URLSearchParams({ page, limit: 20 });
    if (search) params.set("search", search);
    if (category) params.set("category", category);

    const data = await apiFetch(`/v1/products?${params}`);
    const el = document.getElementById("products-list");

    if (data.items.length === 0) {
      show(el, '<p class="text-muted">Nenhum produto encontrado.</p>');
      document.getElementById("pagination").innerHTML = "";
      return;
    }

    const rows = data.items.map(p => `
      <div class="customer-item" onclick="openDetail('${p.ref}')">
        <div class="customer-info">
          <strong>${p.ref}</strong>
          <span class="text-muted">${p.description}</span>
          <span class="text-sm">
            ${formatBRL(p.price)} ${stockBadge(p.stock)}
            ${p.category ? `<span class="category-badge">${p.category}</span>` : ""}
          </span>
        </div>
        <span class="text-muted">→</span>
      </div>
    `).join("");

    show(el, rows);
    renderPagination(data.page, data.pages);
  } catch (e) {
    alert(`Erro: ${e.message}`);
  }
}

// --- Search via shared debounce ---
function debounceSearch() {
  debouncedSearch("search-input", () => loadProducts(1));
}

function renderPagination(page, pages) {
  if (pages <= 1) {
    document.getElementById("pagination").innerHTML = "";
    return;
  }

  let html = '<div class="pagination-btns">';
  if (page > 1) html += `<button class="btn-sm" onclick="loadProducts(${page - 1})">← Anterior</button>`;
  html += `<span class="text-muted">Página ${page} de ${pages}</span>`;
  if (page < pages) html += `<button class="btn-sm" onclick="loadProducts(${page + 1})">Próxima →</button>`;
  html += "</div>";

  document.getElementById("pagination").innerHTML = html;
}

// --- Load Categories from API ---
async function loadCategories() {
  try {
    const data = await apiFetch("/v1/categories");
    // Populate filter dropdown
    const select = document.getElementById("filter-category");
    data.forEach(cat => {
      const opt = document.createElement("option");
      opt.value = cat.name;
      opt.textContent = cat.name;
      select.appendChild(opt);
    });
    // Populate form dropdown
    const formSelect = document.getElementById("form-category");
    data.forEach(cat => {
      const opt = document.createElement("option");
      opt.value = cat.name;
      opt.textContent = cat.name;
      formSelect.appendChild(opt);
    });
  } catch (e) {
    console.error("Erro ao carregar categorias:", e);
  }
}

// --- Form Submit ---
document.getElementById("product-form").addEventListener("submit", async (e) => {
  e.preventDefault();

  const body = {
    ref: document.getElementById("form-ref").value.trim(),
    description: document.getElementById("form-description").value.trim(),
    cost_price: parseFloat(document.getElementById("form-cost-price").value) || 0,
    margin: parseFloat(document.getElementById("form-margin").value) || 0,
    price: parseFloat(document.getElementById("form-price").value) || 0,
    stock: parseInt(document.getElementById("form-stock").value) || 0,
    category: document.getElementById("form-category").value || "",
    manufacturer: document.getElementById("form-manufacturer").value.trim() || "",
    material: document.getElementById("form-material").value.trim() || "",
    size: document.getElementById("form-size").value.trim() || "",
  };

  try {
    if (editingRef) {
      // Update (não envia ref)
      const { ref, ...updateData } = body;
      await apiFetch(`/v1/products/${editingRef}`, {
        method: "PUT",
        body: JSON.stringify(updateData),
      });
    } else {
      // Create
      await apiFetch("/v1/products", {
        method: "POST",
        body: JSON.stringify(body),
      });
    }
    showList();
  } catch (e) {
    alert(`Erro: ${e.message}`);
  }
});

// --- Detail ---
let currentProduct = null;

async function openDetail(ref) {
  try {
    currentProduct = await apiFetch(`/v1/products/${ref}`);
    document.getElementById("detail-ref").textContent = currentProduct.ref;

    const commission = currentProduct.cost_price > 0 ? currentProduct.price - currentProduct.cost_price : 0;

    let html = `
      <div class="product-info-grid">
        <div><strong>Descrição:</strong> ${currentProduct.description}</div>
        <div><strong>Preço de Custo:</strong> ${formatBRL(currentProduct.cost_price || 0)}</div>
        <div><strong>Margem:</strong> ${currentProduct.margin || 0}%</div>
        <div><strong>Preço de Venda:</strong> ${formatBRL(currentProduct.price)}</div>
        ${commission > 0 ? `<div><strong>Comissão/un.:</strong> <span style="color:var(--wa-green)">${formatBRL(commission)}</span></div>` : ""}
        <div><strong>Estoque:</strong> ${stockBadge(currentProduct.stock)}</div>
        ${currentProduct.category ? `<div><strong>Categoria:</strong> ${currentProduct.category}</div>` : ""}
        ${currentProduct.manufacturer ? `<div><strong>Fabricante:</strong> ${currentProduct.manufacturer}</div>` : ""}
        ${currentProduct.material ? `<div><strong>Material:</strong> ${currentProduct.material}</div>` : ""}
        ${currentProduct.size ? `<div><strong>Tamanhos:</strong> ${currentProduct.size}</div>` : ""}
        <div class="text-muted text-sm">Criado em: ${formatDateTime(currentProduct.created_at)}</div>
      </div>
    `;

    show("detail-info", html);
    showDetail();
  } catch (e) {
    alert(`Erro: ${e.message}`);
  }
}

function editCurrent() {
  if (!currentProduct) return;

  editingRef = currentProduct.ref;
  document.getElementById("form-title").textContent = `Editar ${currentProduct.ref}`;
  document.getElementById("btn-submit").textContent = "Atualizar Produto";
  document.getElementById("form-ref").value = currentProduct.ref;
  document.getElementById("form-ref").readOnly = true;
  document.getElementById("form-description").value = currentProduct.description;
  document.getElementById("form-cost-price").value = currentProduct.cost_price || 0;
  document.getElementById("form-margin").value = currentProduct.margin || 0;
  document.getElementById("form-price").value = currentProduct.price || 0;
  document.getElementById("form-stock").value = currentProduct.stock;
  document.getElementById("form-category").value = currentProduct.category || "";
  document.getElementById("form-manufacturer").value = currentProduct.manufacturer || "";
  document.getElementById("form-material").value = currentProduct.material || "";
  document.getElementById("form-size").value = currentProduct.size || "";

  document.getElementById("section-list").classList.add("hidden");
  document.getElementById("section-form").classList.remove("hidden");
  document.getElementById("section-detail").classList.add("hidden");
}

// --- Stock Modal ---
function openStockModal() {
  if (!currentProduct) return;
  document.getElementById("stock-current").textContent =
    `Estoque atual de ${currentProduct.ref}: ${currentProduct.stock} unidades`;
  document.getElementById("stock-qty").value = 1;
  document.getElementById("modal-stock").classList.remove("hidden");
}

async function confirmReduceStock() {
  if (!currentProduct) return;
  const qty = parseInt(document.getElementById("stock-qty").value) || 0;
  if (qty <= 0) {
    alert("Informe uma quantidade válida.");
    return;
  }

  try {
    await apiFetch(`/v1/products/${currentProduct.ref}/reduce`, {
      method: "POST",
      body: JSON.stringify({ quantity: qty }),
    });
    closeModal("modal-stock");
    // Recarregar detalhe
    await openDetail(currentProduct.ref);
  } catch (e) {
    alert(`Erro: ${e.message}`);
  }
}

// --- Delete ---
function deleteCurrent() {
  if (!currentProduct) return;
  document.getElementById("delete-info").textContent =
    `Excluir produto ${currentProduct.ref} — ${currentProduct.description}?`;
  document.getElementById("modal-delete").classList.remove("hidden");
}

async function confirmDelete() {
  if (!currentProduct) return;

  try {
    await apiFetch(`/v1/products/${currentProduct.ref}`, { method: "DELETE" });
    closeModal("modal-delete");
    showList();
  } catch (e) {
    alert(`Erro: ${e.message}`);
  }
}

// --- Modal ---
function closeModal(modalId) {
  document.getElementById(modalId).classList.add("hidden");
}

// --- Category Management ---
function openCategoriesModal() {
  loadCategoriesList();
  document.getElementById("modal-categories").classList.remove("hidden");
}

async function loadCategoriesList() {
  try {
    const data = await apiFetch("/v1/categories");
    const el = document.getElementById("categories-list");
    if (data.length === 0) {
      el.innerHTML = '<p class="text-muted">Nenhuma categoria cadastrada.</p>';
      return;
    }
    const rows = data.map(cat => `
      <div class="customer-item">
        <div class="customer-info">
          <strong>${cat.name}</strong>
          ${cat.description ? `<span class="text-muted text-sm">${cat.description}</span>` : ""}
        </div>
        <button class="btn-icon" onclick="deleteCategory('${cat.name}')" title="Excluir">✕</button>
      </div>
    `).join("");
    el.innerHTML = rows;
  } catch (e) {
    alert(`Erro: ${e.message}`);
  }
}

async function addCategory() {
  const name = document.getElementById("new-category-name").value.trim();
  const description = document.getElementById("new-category-description").value.trim();
  if (!name) return;
  try {
    await apiFetch("/v1/categories", {
      method: "POST",
      body: JSON.stringify({ name, description }),
    });
    document.getElementById("new-category-name").value = "";
    document.getElementById("new-category-description").value = "";
    loadCategoriesList();
    document.getElementById("filter-category").innerHTML = '<option value="">Todas categorias</option>';
    document.getElementById("form-category").innerHTML = '<option value="">Selecione...</option>';
    loadCategories();
  } catch (e) {
    alert(`Erro: ${e.message}`);
  }
}

async function deleteCategory(name) {
  if (!confirm(`Excluir categoria "${name}"?`)) return;
  try {
    await apiFetch(`/v1/categories/${encodeURIComponent(name)}`, { method: "DELETE" });
    loadCategoriesList();
    document.getElementById("filter-category").innerHTML = '<option value="">Todas categorias</option>';
    document.getElementById("form-category").innerHTML = '<option value="">Selecione...</option>';
    loadCategories();
  } catch (e) {
    alert(`Erro: ${e.message}`);
  }
}

// --- CSV Import ---
function openImportModal() {
  document.getElementById("csv-file").value = "";
  hide("import-result");
  document.getElementById("modal-import").classList.remove("hidden");
}

async function importCSV() {
  const fileInput = document.getElementById("csv-file");
  const file = fileInput.files[0];
  if (!file) {
    alert("Selecione um arquivo CSV.");
    return;
  }

  const btn = document.getElementById("btn-import");
  btn.disabled = true;
  btn.textContent = "Importando...";

  try {
    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch("/v1/products/import-csv", {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "Erro na importação");
    }

    const result = await res.json();

    let html = `<div class="card" style="margin-top:12px;padding:12px">`;
    html += `<p>✅ <strong>${result.created}</strong> produto(s) criado(s)</p>`;
    html += `<p>🔄 <strong>${result.updated}</strong> produto(s) atualizado(s)</p>`;
    if (result.errors.length > 0) {
      html += `<p style="color:var(--wa-red)">❌ <strong>${result.errors.length}</strong> erro(s):</p>`;
      html += `<ul style="max-height:150px;overflow-y:auto;font-size:0.8rem">`;
      result.errors.forEach(e => {
        html += `<li>${e}</li>`;
      });
      html += `</ul>`;
    }
    html += `</div>`;

    show("import-result", html);
    loadProducts();
    // Reload categories in case new ones were imported
    document.getElementById("filter-category").innerHTML = '<option value="">Todas categorias</option>';
    document.getElementById("form-category").innerHTML = '<option value="">Selecione...</option>';
    loadCategories();
  } catch (e) {
    alert(`Erro: ${e.message}`);
  } finally {
    btn.disabled = false;
    btn.textContent = "Importar";
  }
}

// --- Init ---
loadCategories();
loadProducts();
