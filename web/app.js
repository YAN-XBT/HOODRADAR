const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];

const LS_KEY = "hoodradar.walletPanel";
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

function logoSrc(t) {
  const u = (t && t.logo) || "";
  if (!u) return "";
  if (/^https?:\/\//i.test(u) || u.toLowerCase().startsWith("ipfs://")) {
    return "/api/img?u=" + encodeURIComponent(u);
  }
  return "";
}

function socialHref(kind, val) {
  const v = String(val || "").trim();
  if (!v) return "";
  if (/^https?:\/\//i.test(v)) return v;
  if (kind === "twitter") return "https://x.com/" + v.replace(/^@/, "");
  if (kind === "telegram") return "https://t.me/" + v.replace(/^@/, "").replace(/^https:\/\/t\.me\//i, "");
  if (kind === "website") return v.includes("://") ? v : "https://" + v;
  if (kind === "discord") return v.includes("discord") ? (v.startsWith("http") ? v : "https://" + v) : "https://discord.gg/" + v;
  if (kind === "farcaster") return /^https?:/i.test(v) ? v : "https://warpcast.com/" + v.replace(/^@/, "");
  return v;
}

function socialsHtml(t) {
  const s = (t && t.socials) || {};
  const keys = [
    ["twitter", "X"],
    ["telegram", "TG"],
    ["website", "web"],
    ["discord", "dc"],
    ["farcaster", "fc"],
  ];
  const bits = [];
  for (const [k, lab] of keys) {
    const v = s[k];
    if (!v || !String(v).trim()) continue;
    bits.push(`<a class="soc" href="${escapeHtml(socialHref(k, v))}" target="_blank" rel="noopener">${lab}</a>`);
  }
  return bits.length ? `<div class="socs">${bits.join("")}</div>` : "";
}

function tokenCell(t) {
  const src = logoSrc(t);
  const initial = escapeHtml(String(t.sym || "?").slice(0, 1).toUpperCase());
  const img = src
    ? `<img class="tok-img" src="${escapeHtml(src)}" alt="" width="24" height="24" onerror="this.replaceWith(Object.assign(document.createElement('span'),{className:'tok-ph',textContent:'${initial}'}))">`
    : `<span class="tok-ph">${initial}</span>`;
  return `<div class="tok">
    ${img}
    <div class="tok-meta">
      <div class="sym">$${escapeHtml(t.sym || "?")}</div>
      <div class="name">${escapeHtml(t.name || "")}</div>
      <div class="addr">${escapeHtml(shortAddr(t.addr))}</div>
      ${socialsHtml(t)}
    </div>
  </div>`;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function emptyPairs(tbody, cols, msg) {
  tbody.innerHTML = `<tr><td colspan="${cols}" class="empty">${escapeHtml(msg)}</td></tr>`;
}

function progEl(t) {
  const p = t && t.progress;
  if (p == null || Number.isNaN(Number(p))) return "—";
  return Math.round(Number(p) * 100) + "%";
}

function renderPairs(rows, tbody, opts) {
  const withProg = !!(opts && opts.progress);
  const cols = withProg ? 6 : 5;
  const msg = (opts && opts.empty) || "No pairs yet.";
  if (!tbody) return;
  if (!rows || !rows.length) {
    emptyPairs(tbody, cols, msg);
    return;
  }
  tbody.innerHTML = rows.map(t => `
    <tr>
      <td>${tokenCell(t)}</td>
      ${withProg ? `<td class="r">${escapeHtml(progEl(t))}</td>` : ""}
      <td class="r">${fmtUsd(t.mc)}</td>
      <td class="r">${fmtUsd(t.vol)}</td>
      <td class="r">${chgEl(t.chg)}</td>
      <td class="r">${escapeHtml(t.age || "—")}</td>
    </tr>`).join("");
}

function relTime(iso, ts) {
  let sec = null;
  if (ts) sec = Math.max(0, (Date.now() / 1000) - Number(ts));
  else if (iso) {
    const d = Date.parse(iso);
    if (!Number.isNaN(d)) sec = Math.max(0, (Date.now() - d) / 1000);
  }
  if (sec == null) return "";
  if (sec < 90) return Math.floor(sec) + "s";
  if (sec < 3600) return Math.floor(sec / 60) + "m";
  if (sec < 86400) return Math.floor(sec / 3600) + "h";
  return Math.floor(sec / 86400) + "d";
}

function renderXFeed(data) {
  const el = $("#xwatch-list");
  const meta = $("#xfeed-meta");
  const posts = (data && data.posts) || STATE.x_feed || [];
  const err = (data && data.error) != null ? data.error : STATE.x_feed_error;
  const handles = (data && data.handles) || (STATE.x_watch || []).map(x => x.handle);
  const src = (data && data.source) || STATE.x_feed_source;
  if (meta) meta.textContent = src ? ("via " + src) : "public RSS · no X API key";
  if (!posts.length) {
    el.className = "xfeed empty";
    const hs = (handles || []).map(h => "@" + h).join(" · ");
    el.textContent = (err || "X feed unreachable (no API key)") + (hs ? " — " + hs : "");
    return;
  }
  el.className = "xfeed";
  el.innerHTML = posts.map(p => {
    const handle = p.handle || "";
    const name = p.name || handle;
    const initial = escapeHtml(String(handle || "?").slice(0, 1).toUpperCase());
    const media = p.media ? `<img class="x-media" src="${escapeHtml("/api/img?u=" + encodeURIComponent(p.media))}" alt="" onerror="this.remove()">` : "";
    return `<a class="x-card" href="${escapeHtml(p.url || "https://x.com/" + handle)}" target="_blank" rel="noopener">
      <div class="x-av">${initial}</div>
      <div class="x-body">
        <div class="x-head">
          <span class="x-name">${escapeHtml(name)}</span>
          <span class="x-handle">@${escapeHtml(handle)}</span>
          <span class="x-time">${escapeHtml(relTime(p.iso, p.ts))}</span>
        </div>
        <div class="x-text">${escapeHtml(p.text || "")}</div>
        ${media}
      </div>
    </a>`;
  }).join("");
}

let TREND_W = "1m";
let TREND_TIMER = 0;
let TREND_ERR = "";

function fmtHolders(n) {
  if (n == null || Number.isNaN(Number(n))) return "—";
  const v = Number(n);
  if (v >= 1e6) return (v / 1e6).toFixed(1) + "M";
  if (v >= 1e3) return (v / 1e3).toFixed(1) + "k";
  return String(Math.round(v));
}

function renderTrending(rows, tbody, compact, err) {
  if (!tbody) return;
  const cols = 8;
  if (!rows || !rows.length) {
    emptyPairs(tbody, cols, err || "set GMGN_API_KEY");
    return;
  }
  const slice = compact ? rows.slice(0, 8) : rows;
  tbody.innerHTML = slice.map(t => `
    <tr>
      <td>${tokenCell(t)}<div class="name">${escapeHtml(t.age || "")}</div></td>
      <td class="r">${fmtUsd(t.mc)}</td>
      <td class="r">${fmtUsd(t.ath_mc)}</td>
      <td class="r">${fmtUsd(t.liq)}</td>
      <td class="r">${fmtUsd(t.vol)}</td>
      <td class="r">${escapeHtml(String(t.swaps != null ? t.swaps : "—"))}</td>
      <td class="r">${fmtHolders(t.holders)}</td>
      <td class="r">${chgEl(t.chg)}</td>
    </tr>`).join("");
}

async function loadTrending() {
  const w = TREND_W || "1m";
  try {
    const res = await fetch("/api/trending?interval=" + encodeURIComponent(w));
    const data = await res.json();
    TREND_ERR = data.error || "";
    const rows = data.rows || [];
    const meta = $("#trending-meta");
    if (meta) meta.textContent = TREND_ERR ? TREND_ERR : ((data.source || "gmgn") + " · " + (data.interval || w) + " · " + rows.length + " tokens");
    renderTrending(rows, $("#trending-home"), true, TREND_ERR);
    renderTrending(rows, $("#trending-body"), false, TREND_ERR);
    $$(".trend-btn").forEach(b => b.classList.toggle("on", b.dataset.tw === TREND_W));
  } catch (err) {
    console.error(err);
    TREND_ERR = "set GMGN_API_KEY";
    renderTrending([], $("#trending-home"), true, TREND_ERR);
    renderTrending([], $("#trending-body"), false, TREND_ERR);
  }
}

function startTrendPoll() {
  if (TREND_TIMER) clearInterval(TREND_TIMER);
  loadTrending().catch(() => {});
  TREND_TIMER = setInterval(() => loadTrending().catch(() => {}), 20000);
}

function renderDips(rows, el) {
  if (!rows || !rows.length) {
    el.className = "empty";
    el.textContent = "No dip setups now. Filters: drop ≤ -20%, mcap ≥ $50k, liq ≥ $15k.";
    return;
  }
  el.className = "";
  el.innerHTML = `<table><thead><tr><th>Token</th><th class="r">MC</th><th class="r">Vol</th><th class="r">Chg</th></tr></thead>
    <tbody>${rows.map(t => `<tr><td>${tokenCell(t)}</td><td class="r">${fmtUsd(t.mc)}</td><td class="r">${fmtUsd(t.vol)}</td><td class="r">${chgEl(t.chg)}</td></tr>`).join("")}</tbody></table>`;
}

let STATE = {};
let toastTimer = 0;

function showToast(text) {
  const el = $("#toast");
  el.textContent = text;
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.hidden = true; }, 2600);
}

function loadPanelGeom() {
  try {
    return JSON.parse(localStorage.getItem(LS_KEY) || "{}");
  } catch {
    return {};
  }
}

function savePanelGeom(extra) {
  const panel = $("#wallet-float");
  const prev = loadPanelGeom();
  const next = {
    open: !panel.hidden,
    left: panel.style.left || prev.left || "",
    top: panel.style.top || prev.top || "",
    width: panel.style.width || prev.width || "",
    height: panel.style.height || prev.height || "",
    ...extra,
  };
  localStorage.setItem(LS_KEY, JSON.stringify(next));
}

function applyPanelGeom() {
  const panel = $("#wallet-float");
  const g = loadPanelGeom();
  panel.style.left = g.left || "24px";
  panel.style.top = g.top || "96px";
  if (g.width) panel.style.width = g.width;
  if (g.height) panel.style.height = g.height;
  setPanelOpen(!!g.open, false);
}

function setPanelOpen(open, persist = true) {
  const panel = $("#wallet-float");
  panel.hidden = !open;
  $("#btn-pnl").classList.toggle("on", open);
  if (persist) savePanelGeom({ open });
}

function initWalletChrome() {
  const panel = $("#wallet-float");
  const drag = $("#wallet-drag");
  const resize = $("#wallet-resize");

  applyPanelGeom();

  $("#btn-pnl").onclick = () => setPanelOpen(panel.hidden);
  $("#wallet-close").onclick = () => setPanelOpen(false);

  let dragState = null;
  drag.addEventListener("pointerdown", e => {
    if (e.target.closest(".x")) return;
    e.preventDefault();
    drag.setPointerCapture(e.pointerId);
    const rect = panel.getBoundingClientRect();
    dragState = { dx: e.clientX - rect.left, dy: e.clientY - rect.top };
  });
  drag.addEventListener("pointermove", e => {
    if (!dragState) return;
    const x = Math.max(0, e.clientX - dragState.dx);
    const y = Math.max(0, e.clientY - dragState.dy);
    panel.style.left = x + "px";
    panel.style.top = y + "px";
  });
  const endDrag = () => {
    if (!dragState) return;
    dragState = null;
    savePanelGeom();
  };
  drag.addEventListener("pointerup", endDrag);
  drag.addEventListener("pointercancel", endDrag);

  let rs = null;
  resize.addEventListener("pointerdown", e => {
    e.preventDefault();
    e.stopPropagation();
    resize.setPointerCapture(e.pointerId);
    const rect = panel.getBoundingClientRect();
    rs = { x: e.clientX, y: e.clientY, w: rect.width, h: rect.height };
  });
  resize.addEventListener("pointermove", e => {
    if (!rs) return;
    const w = Math.max(180, rs.w + (e.clientX - rs.x));
    const h = Math.max(120, rs.h + (e.clientY - rs.y));
    panel.style.width = w + "px";
    panel.style.height = h + "px";
  });
  const endRs = () => {
    if (!rs) return;
    rs = null;
    savePanelGeom();
  };
  resize.addEventListener("pointerup", endRs);
  resize.addEventListener("pointercancel", endRs);
}

async function loadState() {
  const res = await fetch("/api/state");
  STATE = await res.json();
  paint();
}

function paint() {
  const s = STATE || {};
  const w = s.wallet || {};
  $("#w-addr").textContent = shortAddr(w.address);
  $("#w-bal").textContent = fmtUsd(w.balance_usd);
  const pnl = w.pnl_usd || 0;
  $("#w-pnl").textContent = pnl === 0 ? "+$0" : (pnl >= 0 ? "+" : "") + fmtUsd(pnl);

  const migrated = s.pairs_migrated || [];
  const about = s.pairs_about || [];
  renderPairs(migrated, $("#migrated-body"), { empty: "No migrated pairs ≥ $20k yet." });
  renderPairs(migrated, $("#migrated-body-2"), { empty: "No migrated pairs ≥ $20k yet." });
  renderPairs(about, $("#about-body"), { progress: true, empty: "No about-to-migrate pairs ≥ $20k yet." });
  renderPairs(about, $("#about-body-2"), { progress: true, empty: "No about-to-migrate pairs ≥ $20k yet." });
  renderDips(s.dips, $("#dips-home"));
  renderDips(s.dips, $("#dips-full"));
  renderXFeed({ posts: s.x_feed, error: s.x_feed_error, source: s.x_feed_source, handles: (s.x_watch || []).map(x => x.handle) });

  $("#wallets-list").innerHTML = (s.wallets || []).map(row =>
    `<div class="row2"><span>${escapeHtml(shortAddr(row.address))} · ${escapeHtml(row.label || "")}</span><span>${fmtUsd(row.usd)} <span class="up">${row.pnl >= 0 ? "+" : ""}${fmtUsd(row.pnl)}</span></span></div>`
  ).join("") || `<div class="empty">No wallets.</div>`;
}

function showTab(id) {
  $$(".tab").forEach(t => t.classList.toggle("active", t.dataset.tab === id));
  $$(".panel").forEach(p => p.classList.toggle("active", p.id === "panel-" + id));
}

async function scan(kind) {
  try {
    const res = await fetch("/api/scan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ kind }),
    });
    const data = await res.json().catch(() => ({}));
    showToast(data.message || data.error || "scan done");
  } catch (err) {
    console.error(err);
    showToast("scan failed");
  }
  await loadState().catch(() => {});
}

function addMsg(role, text, results) {
  const log = $("#agent-log");
  const div = document.createElement("div");
  div.className = "msg " + (role === "user" ? "user" : "bot");
  let extra = "";
  if (results && results.length) {
    extra = "<ul class='results'>" + results.map(r => {
      const label = r.kind === "wallet"
        ? `wallet ${shortAddr(r.address || r.addr)}`
        : `$${r.sym || "?"} ${shortAddr(r.addr)}`;
      return `<li>${escapeHtml(label)} — ${escapeHtml(r.note || "")}</li>`;
    }).join("") + "</ul>";
  }
  div.innerHTML = `<div class="k">${role}</div>${escapeHtml(text)}${extra}`;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}

async function askAgent(message) {
  addMsg("user", message);
  const res = await fetch("/api/agent", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  const data = await res.json();
  addMsg("agent", data.reply || "", data.results);
}

$("#tabs").addEventListener("click", e => {
  const t = e.target.closest(".tab");
  if (t) showTab(t.dataset.tab);
});

document.addEventListener("click", e => {
  const b = e.target.closest(".trend-btn");
  if (!b) return;
  TREND_W = b.dataset.tw || "1m";
  $$(".trend-btn").forEach(x => x.classList.toggle("on", x.dataset.tw === TREND_W));
  loadTrending().catch(() => {});
});

async function loadXFeed() {
  try {
    const res = await fetch("/api/xfeed");
    const data = await res.json();
    STATE.x_feed = data.posts || [];
    STATE.x_feed_error = data.error;
    STATE.x_feed_source = data.source;
    if (data.handles) STATE.x_watch = data.handles.map(h => ({ handle: h, status: "allow" }));
    renderXFeed(data);
  } catch (err) {
    console.error(err);
    renderXFeed({ posts: [], error: "X feed unreachable (no API key)", handles: (STATE.x_watch || []).map(x => x.handle) });
  }
}

$("#btn-refresh").onclick = async () => {
  await loadState().catch(() => {});
  await loadXFeed().catch(() => {});
  await loadTrending().catch(() => {});
};
$("#btn-wallets").onclick = () => scan("wallets");
$("#btn-dip").onclick = () => scan("dip");
$("#btn-agent").onclick = () => {
  showTab("agent");
  $("#agent-input").focus();
};

$("#agent-form").addEventListener("submit", e => {
  e.preventDefault();
  const v = $("#agent-input").value.trim();
  if (!v) return;
  $("#agent-input").value = "";
  askAgent(v);
});

initWalletChrome();

loadState().then(() => loadXFeed()).then(() => startTrendPoll()).catch(err => {
  console.error(err);
});
