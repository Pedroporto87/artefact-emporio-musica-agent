const CATEGORY_ART = { 1: "🎸", 2: "🎸", 3: "🥁", 4: "🎹", 5: "🎶", 9: "🌺" };
const SUGGESTIONS = [
  "Quais violões vocês têm até R$1000?",
  "Quanto custa o Takamine GD20?",
  "Vocês estão abertos agora?",
  "Posso devolver um produto?",
];

const state = { products: [], categories: [], category: null, query: "", sessionId: loadSession() };
const brl = (v) => v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const $ = (id) => document.getElementById(id);

function loadSession() {
  try { return sessionStorage.getItem("marina-session"); } catch { return null; }
}
function saveSession(id) {
  try { sessionStorage.setItem("marina-session", id); } catch { /* sem storage: conversa só dura até recarregar */ }
}

function escapeHtml(text) {
  return text.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// Markdown mínimo da Marina (negrito, títulos, quebras). Escapa antes para não injetar HTML.
function renderReply(text) {
  return escapeHtml(text)
    .replace(/^#{1,6}\s*(.+)$/gm, "<strong>$1</strong>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\n/g, "<br>");
}

function normalize(text) {
  return text.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

/* ---------- Catálogo ---------- */

function priceHtml(p) {
  if (p.promotion) {
    return `<span class="old">${brl(p.price_brl)}</span><span class="now">${brl(p.promotion.discounted_price)}</span>
            <span class="pix">${p.promotion.name} · ${p.promotion.discount_percent}% OFF</span>`;
  }
  return `<span class="now">${brl(p.price_brl)}</span><span class="pix">${brl(p.pix_price)} no PIX</span>`;
}

function cardHtml(p) {
  const out = p.stock_quantity === 0;
  const badge = out
    ? `<span class="badge out">Sem estoque</span>`
    : p.promotion ? `<span class="badge">-${p.promotion.discount_percent}%</span>` : "";
  return `
    <article class="card" id="product-${p.product_id}">
      <div class="card-art" aria-hidden="true">${CATEGORY_ART[p.category_id] || "🎵"}
        <span class="cat">${escapeHtml(p.category)}</span>${badge}
      </div>
      <div class="card-body">
        <h3>${escapeHtml(p.name)}</h3>
        <p class="desc">${escapeHtml(p.description)}</p>
        <div class="price">${priceHtml(p)}</div>
        <span class="stock">${out ? "Indisponível no momento" : `${p.stock_quantity} em estoque`}</span>
        <button class="ask-btn" data-ask="${p.product_id}">Perguntar à Marina</button>
      </div>
    </article>`;
}

function renderCategories() {
  const all = [{ category_id: null, name: "Todos", product_count: state.products.length }, ...state.categories];
  $("categories").innerHTML = all.map((c) => `
    <button class="chip" data-category="${c.category_id ?? ""}" aria-pressed="${c.category_id === state.category}">
      ${escapeHtml(c.name)}<span class="count">${c.product_count}</span>
    </button>`).join("");
}

function renderGrid() {
  const q = normalize(state.query.trim());
  const visible = state.products.filter((p) =>
    (state.category === null || p.category_id === state.category) &&
    (!q || normalize(p.name).includes(q)));
  $("grid").innerHTML = visible.map(cardHtml).join("") || `<p class="muted">Nenhum produto encontrado.</p>`;
  $("result-count").textContent = `${visible.length} produto${visible.length === 1 ? "" : "s"}`;
}

function setCategory(id) {
  state.category = id;
  renderCategories();
  renderGrid();
}

function focusProduct(id) {
  const product = state.products.find((p) => p.product_id === id);
  if (!product) return;
  state.query = "";
  $("search").value = "";
  setCategory(product.category_id);
  const el = $(`product-${id}`);
  document.querySelectorAll(".card.highlight").forEach((c) => c.classList.remove("highlight"));
  el.classList.add("highlight");
  el.scrollIntoView({ behavior: "smooth", block: "center" });
  closeChatOnMobile();
}

function renderStatus(store) {
  const pill = $("store-status");
  pill.classList.toggle("open", store.loja_aberta_agora);
  pill.textContent = store.loja_aberta_agora
    ? `Aberto agora · hoje ${store.horario_de_hoje}`
    : `Fechado${store.feriado ? ` (${store.feriado})` : ""} · abre ${store.proxima_abertura}`;
}

/* ---------- Chat ---------- */

function addMessage(kind, html) {
  const el = document.createElement("div");
  el.className = `msg ${kind}`;
  el.innerHTML = html;
  $("messages").appendChild(el);
  $("messages").scrollTop = $("messages").scrollHeight;
  return el;
}

function addMiniCards(products) {
  if (!products.length) return;
  const wrap = document.createElement("div");
  wrap.className = "mini-cards";
  wrap.innerHTML = products.map((p) => {
    const price = p.promotion ? p.promotion.discounted_price : p.price_brl;
    const tail = p.stock_quantity === 0 ? `<span class="out">Sem estoque</span>` : `<span class="mini-price">${brl(price)}</span>`;
    return `<button class="mini" data-focus="${p.product_id}"><strong>${escapeHtml(p.name)}</strong>${tail}</button>`;
  }).join("");
  $("messages").appendChild(wrap);
  $("messages").scrollTop = $("messages").scrollHeight;
}

async function sendMessage(text) {
  text = text.trim();
  if (!text) return;
  $("suggestions").innerHTML = "";
  addMessage("user", escapeHtml(text));
  $("chat-input").value = "";
  const button = document.querySelector(".send-btn");
  button.disabled = true;
  const typing = addMessage("bot typing", "Marina está digitando…");
  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, session_id: state.sessionId }),
    });
    const data = await res.json();
    typing.remove();
    if (!res.ok) throw new Error(data.detail || "Erro ao falar com a Marina.");
    state.sessionId = data.session_id;
    saveSession(data.session_id);
    addMessage("bot", renderReply(data.reply));
    addMiniCards(data.products);
    data.products.forEach((p) => $(`product-${p.product_id}`)?.classList.add("highlight"));
  } catch (err) {
    typing.remove();
    addMessage("error", escapeHtml(err.message));
  } finally {
    button.disabled = false;
    $("chat-input").focus();
  }
}

function openChat() {
  $("chat").classList.add("open");
  document.body.classList.add("chat-open");
  $("chat-input").focus();
}
function closeChatOnMobile() {
  $("chat").classList.remove("open");
  document.body.classList.remove("chat-open");
}

/* ---------- Início ---------- */

function bindEvents() {
  $("categories").addEventListener("click", (e) => {
    const chip = e.target.closest(".chip");
    if (chip) setCategory(chip.dataset.category ? Number(chip.dataset.category) : null);
  });
  $("search").addEventListener("input", (e) => { state.query = e.target.value; renderGrid(); });
  $("grid").addEventListener("click", (e) => {
    const btn = e.target.closest("[data-ask]");
    if (!btn) return;
    const p = state.products.find((x) => x.product_id === Number(btn.dataset.ask));
    openChat();
    sendMessage(`Me fala mais sobre o ${p.name}`);
  });
  $("messages").addEventListener("click", (e) => {
    const mini = e.target.closest("[data-focus]");
    if (mini) focusProduct(Number(mini.dataset.focus));
  });
  $("suggestions").addEventListener("click", (e) => {
    if (e.target.matches("button")) sendMessage(e.target.textContent);
  });
  $("chat-form").addEventListener("submit", (e) => { e.preventDefault(); sendMessage($("chat-input").value); });
  $("chat-open").addEventListener("click", openChat);
  $("chat-close").addEventListener("click", closeChatOnMobile);
}

async function init() {
  bindEvents();
  addMessage("bot", "Oi! Eu sou a Marina, assistente do Empório da Música 🎵<br>Posso te ajudar a encontrar um instrumento, ver preços, consultar um pedido ou tirar dúvidas sobre a loja.");
  $("suggestions").innerHTML = SUGGESTIONS.map((s) => `<button type="button">${escapeHtml(s)}</button>`).join("");
  try {
    const res = await fetch("/api/catalog");
    const data = await res.json();
    state.products = data.products;
    state.categories = data.categories;
    renderStatus(data.store);
    renderCategories();
    renderGrid();
  } catch {
    $("grid").innerHTML = `<p class="muted">Não foi possível carregar o catálogo.</p>`;
  }
}

init();
