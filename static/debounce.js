/**
 * debounce.js — Utilitários compartilhados
 *
 * Uso debounce:
 *   <input oninput="debouncedSearch('search-input', myCallback)">
 *
 * Uso formato data:
 *   formatDateTime(timestamp) → "25/08/2026 14:30"
 *   formatDate(dateStr)       → "25/08/2026"
 */

// --- Debounce Search ---
const SearchDefaults = { minChars: 3, delay: 300 };
const _searchTimers = {};

function debouncedSearch(inputId, callback, opts = {}) {
  const { minChars = SearchDefaults.minChars, delay = SearchDefaults.delay } = opts;
  clearTimeout(_searchTimers[inputId]);
  const input = document.getElementById(inputId);
  if (!input) return;
  const term = input.value.trim();
  if (term.length < minChars) {
    if (typeof callback === "function") callback("");
    return;
  }
  _searchTimers[inputId] = setTimeout(() => {
    if (typeof callback === "function") callback(term);
  }, delay);
}

// --- Date/Time Formatting (dd/MM/yyyy hh:mm) ---
function formatDateTime(ts) {
  if (!ts) return "-";
  const d = new Date(ts.includes("T") ? ts : ts + "T00:00:00");
  const dd = String(d.getDate()).padStart(2, "0");
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const yyyy = d.getFullYear();
  const hh = String(d.getHours()).padStart(2, "0");
  const mi = String(d.getMinutes()).padStart(2, "0");
  return `${dd}/${mm}/${yyyy} ${hh}:${mi}`;
}

function formatDate(dateStr) {
  if (!dateStr) return "-";
  const parts = dateStr.split("T")[0].split("-");
  if (parts.length !== 3) return dateStr;
  return `${parts[2]}/${parts[1]}/${parts[0]}`;
}
