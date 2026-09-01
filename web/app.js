const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];

function fmtUsd(n) {
  if (n == null || Number.isNaN(n)) return "—";
  const abs = Math.abs(n);
  if (abs >= 1e6) return "$" + (n / 1e6).toFixed(2) + "M";
  if (abs >= 1e3) return "$" + (n / 1e3).toFixed(1) + "k";
  return "$" + Number(n).toFixed(0);
}
function shortAddr(a) {
  if (!a) return "—";
  return a.slice(0, 6) + "…" + a.slice(-4);
}
function chgEl(v) {
  if (v == null) return "—";
  const cls = v >= 0 ? "up" : "dn";
  const s = (v >= 0 ? "+" : "") + Number(v).toFixed(1) + "%";
  return `<span class="${cls}">${s}</span>`;
}
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function tokenCell(t) {
  return `<div class="sym">$${escapeHtml(t.sym || "?")}</div><div class="name">${escapeHtml(t.name || "")}</div><div class="addr">${escapeHtml(shortAddr(t.addr))}</div>`;
}
function renderTape(rows, tbody) {
  tbody.innerHTML = (rows || []).map(t => `<tr><td>${tokenCell(t)}</td><td class="r">${fmtUsd(t.mc)}</td><td class="r">${fmtUsd(t.vol)}</td><td class="r">${chgEl(t.chg)}</td><td class="r">${escapeHtml(t.safety || "—")}</td></tr>`).join("");
}
function renderPairs(rows, tbody) {
  tbody.innerHTML = (rows || []).map(t => `<tr><td>${tokenCell(t)}</td><td class="r">${fmtUsd(t.mc)}</td><td class="r">${fmtUsd(t.vol)}</td><td class="r">${chgEl(t.chg)}</td><td class="r">${escapeHtml(t.age || "—")}</td></tr>`).join("");
}
function renderDips(rows, el) {
  if (!rows || !rows.length) {
    el.className = "empty";
    el.textContent = "No dip setups now. Filters: drop ≤ -20%, mcap ≥ $50k, liq ≥ $15k.";
    return;
  }
  el.className = "";
  el.innerHTML = `<table><thead><tr><th>Token</th><th class="r">MC</th><th class="r">Vol</th><th class="r">Chg</th></tr></thead><tbody>${rows.map(t => `<tr><td>${tokenCell(t)}</td><td class="r">${fmtUsd(t.mc)}</td><td class="r">${fmtUsd(t.vol)}</td><td class="r">${chgEl(t.chg)}</td></tr>`).join("")}</tbody></table>`;
}
let STATE = {};
async function loadState() {
  const res = await fetch("/api/state");
  STATE = await res.json();
  paint();
}
function paint() {
  const s = STATE || {};
  $("#st-online").textContent = s.online ? "online" : "offline";
  $("#st-time").textContent = s.updated_at || "—";
  $("#st-wallets").textContent = "wallets " + (s.wallet_count ?? (s.wallets || []).length);
  $("#st-cache").textContent = (s.cache_count ?? 0) + " cache";
  const w = s.wallet || {};
  $("#w-addr").textContent = shortAddr(w.address);
  $("#w-bal").textContent = fmtUsd(w.balance_usd);
  const pnl = w.pnl_usd || 0;
  $("#w-pnl").textContent = pnl === 0 ? "+$0" : ((pnl >= 0 ? "+" : "") + fmtUsd(pnl));
  renderTape(s.safe_tape, $("#tape-body"));
  renderPairs(s.new_pairs, $("#pairs-body"));
  renderPairs(s.new_pairs, $("#pairs-body-2"));
  renderDips(s.dips, $("#dips-home"));
  renderDips(s.dips, $("#dips-full"));
  $("#wallets-list").innerHTML = (s.wallets || []).map(w => `<div class="row2"><span>${escapeHtml(shortAddr(w.address))} · ${escapeHtml(w.label || "")}</span><span>${fmtUsd(w.usd)}</span></div>`).join("") || `<div class="empty">No wallets.</div>`;
  $("#xwatch-list").innerHTML = (s.x_watch || []).map(x => `<div class="row2"><span>@${escapeHtml(x.handle)}</span><span class="up">${escapeHtml(x.status || "allow")}</span></div>`).join("") || `<div class="empty">No handles.</div>`;
}
function showTab(id) {
  $$(".tab").forEach(t => t.classList.toggle("active", t.dataset.tab === id));
  $$(".panel").forEach(p => p.classList.toggle("active", p.id === "panel-" + id));
}
async function scan(kind) {
  await fetch("/api/scan", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ kind }) });
  await loadState();
}
function addMsg(role, text, results) {
  const log = $("#agent-log");
  const div = document.createElement("div");
  div.className = "msg " + (role === "user" ? "user" : "bot");
  let extra = "";
  if (results && results.length) {
    extra = "<ul class='results'>" + results.map(r => {
      const label = r.kind === "wallet" ? `wallet ${shortAddr(r.address || r.addr)}` : `$${r.sym || "?"} ${shortAddr(r.addr)}`;
      return `<li>${escapeHtml(label)} — ${escapeHtml(r.note || "")}</li>`;
    }).join("") + "</ul>";
  }
  div.innerHTML = `<div class="k">${role}</div>${escapeHtml(text)}${extra}`;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}
async function askAgent(message) {
  addMsg("user", message);
  const res = await fetch("/api/agent", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message }) });
  const data = await res.json();
  addMsg("agent", data.reply || "", data.results);
}
$("#tabs").addEventListener("click", e => {
  const t = e.target.closest(".tab");
  if (t) showTab(t.dataset.tab);
});
$("#btn-refresh").onclick = () => loadState();
$("#btn-wallets").onclick = () => scan("wallets");
$("#btn-dip").onclick = () => scan("dip");
$("#btn-agent").onclick = () => { showTab("agent"); $("#agent-input").focus(); };
$("#agent-form").addEventListener("submit", e => {
  e.preventDefault();
  const v = $("#agent-input").value.trim();
  if (!v) return;
  $("#agent-input").value = "";
  askAgent(v);
});
loadState().catch(err => { $("#st-online").textContent = "offline"; console.error(err); });
