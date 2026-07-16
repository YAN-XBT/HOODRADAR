/* HOODRADAR desk UI v2 — defensive */
(function () {
  "use strict";

  function $(id) {
    return document.getElementById(id);
  }

  function setHtml(id, html) {
    const el = $(id);
    if (!el) return;
    el.innerHTML = html;
  }

  function setText(id, text) {
    const el = $(id);
    if (!el) return;
    el.textContent = text;
  }

  function toast(msg, err) {
    const t = $("toast");
    if (!t) return;
    t.textContent = msg;
    t.classList.toggle("err", !!err);
    t.classList.remove("hidden");
    setTimeout(function () {
      t.classList.add("hidden");
    }, 4500);
  }

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function money(n) {
    if (n == null || n === "" || isNaN(Number(n))) return "—";
    var x = Number(n);
    var sign = x < 0 ? "-" : "";
    var a = Math.abs(x);
    if (a >= 1e6) return sign + "$" + (a / 1e6).toFixed(2) + "M";
    if (a >= 1e3) return sign + "$" + (a / 1e3).toFixed(1) + "k";
    return sign + "$" + a.toFixed(0);
  }

  function pct(n) {
    if (n == null || n === "" || isNaN(Number(n))) return "";
    return Number(n).toFixed(1) + "%";
  }

  function shortAddr(a) {
    if (!a || a.length < 12) return a || "";
    return a.slice(0, 6) + "…" + a.slice(-4);
  }

  function logoSrc(url) {
    if (!url) return "";
    // local proxy — GMGN CDN often 403 in raw <img>
    return "/api/logo?u=" + encodeURIComponent(url);
  }

  function twUrl(u) {
    if (!u) return "";
    var s = String(u).trim();
    if (!s) return "";
    if (s.indexOf("http") === 0) return s;
    return "https://x.com/" + s.replace(/^@/, "");
  }

  function socialBtns(opts, minimal) {
    opts = opts || {};
    var ca = opts.ca || "";
    var gmgn = ca ? "https://gmgn.ai/robinhood/token/" + ca : "";
    var exp =
      opts.explorer ||
      (ca ? "https://robinhoodchain.blockscout.com/token/" + ca : "");
    var tw = twUrl(opts.twitter);
    var web = opts.website || "";
    var tg = opts.telegram || "";

    function chip(href, label, cls) {
      if (!href) return '<span class="chip disabled">' + label + "</span>";
      return (
        '<a class="chip ' +
        cls +
        '" href="' +
        esc(href) +
        '" target="_blank" rel="noopener">' +
        label +
        "</a>"
      );
    }

    if (minimal) {
      return (
        '<div class="btns">' +
        chip(gmgn, "GMGN", "gmgn") +
        chip(exp, "Exp", "exp") +
        "</div>"
      );
    }

    return (
      '<div class="btns">' +
      chip(gmgn, "GMGN", "gmgn") +
      chip(tw, "X / Twitter", "x") +
      chip(web, "Website", "web") +
      chip(tg, "Telegram", "tg") +
      chip(exp, "Explorer", "exp") +
      "</div>"
    );
  }

  function walletLinks(addr) {
    if (!addr) return "";
    return (
      '<div class="btns">' +
      '<a class="chip gmgn" href="https://gmgn.ai/robinhood/address/' +
      esc(addr) +
      '" target="_blank" rel="noopener">GMGN</a>' +
      '<a class="chip exp" href="https://robinhoodchain.blockscout.com/address/' +
      esc(addr) +
      '" target="_blank" rel="noopener">Explorer</a>' +
      "</div>"
    );
  }

  /* tabs */
  document.querySelectorAll(".tab").forEach(function (btn) {
    btn.addEventListener("click", function () {
      document.querySelectorAll(".tab").forEach(function (b) {
        b.classList.remove("active");
      });
      document.querySelectorAll(".panel").forEach(function (p) {
        p.classList.remove("active");
      });
      btn.classList.add("active");
      var panel = $("panel-" + btn.getAttribute("data-tab"));
      if (panel) panel.classList.add("active");
    });
  });

  function renderWalletsList(targetId, wallets, expanded) {
    var el = $(targetId);
    if (!el) return;
    if (!wallets || !wallets.length) {
      el.innerHTML =
        '<div class="hit"><em>No wallet board yet — click Scan wallets or Run all.</em></div>';
      return;
    }
    var html = "";
    var max = Math.min(wallets.length, 20);
    for (var i = 0; i < max; i++) {
      var w = wallets[i];
      var addr = w.address || "";
      var buys = (w.recent_buys || []).slice(0, expanded ? 5 : 2);
      var buyLine = buys
        .map(function (b) {
          return "$" + esc(b.symbol || "?") + " " + money(b.volume_usd);
        })
        .join(" · ");
      html +=
        '<div class="wrow">' +
        '<div class="wrank">' +
        (i + 1) +
        "</div>" +
        "<div>" +
        '<div class="waddr" title="' +
        esc(addr) +
        '">' +
        esc(expanded ? addr : shortAddr(addr)) +
        "</div>" +
        '<div class="wstats">trades ' +
        esc(w.trade_count != null ? w.trade_count : "—") +
        " · vol " +
        money(w.volume) +
        "</div>" +
        (buyLine ? '<div class="wbuy">recent: <span>' + buyLine + "</span></div>" : "") +
        (expanded ? walletLinks(addr) : "") +
        (expanded ? '<div class="ca" style="margin-top:8px">' + esc(addr) + "</div>" : "") +
        "</div>" +
        '<div class="wpnl">' +
        money(w.pnl) +
        "</div>" +
        "</div>";
    }
    el.innerHTML = html;
  }

  function sparkSvg(closes, w, h) {
    w = w || 160;
    h = h || 42;
    if (!closes || closes.length < 2) {
      return (
        '<svg class="spark-svg" viewBox="0 0 ' +
        w +
        " " +
        h +
        '" preserveAspectRatio="none"><text x="8" y="' +
        (h / 2 + 4) +
        '" fill="#4a5c52" font-size="10">no chart</text></svg>'
      );
    }
    var min = Math.min.apply(null, closes);
    var max = Math.max.apply(null, closes);
    var span = max - min || 1;
    var n = closes.length;
    var pts = [];
    for (var i = 0; i < n; i++) {
      var x = (i / (n - 1)) * (w - 4) + 2;
      var y = h - 4 - ((closes[i] - min) / span) * (h - 8);
      pts.push(x.toFixed(1) + "," + y.toFixed(1));
    }
    var up = closes[closes.length - 1] >= closes[0];
    var col = up ? "#3dffa8" : "#ff5c5c";
    var fill = up ? "rgba(61,255,168,.12)" : "rgba(255,92,92,.12)";
    var area =
      "2," +
      (h - 2) +
      " " +
      pts.join(" ") +
      " " +
      (w - 2) +
      "," +
      (h - 2);
    return (
      '<svg class="spark-svg" viewBox="0 0 ' +
      w +
      " " +
      h +
      '" preserveAspectRatio="none">' +
      '<polygon points="' +
      area +
      '" fill="' +
      fill +
      '"/>' +
      '<polyline points="' +
      pts.join(" ") +
      '" fill="none" stroke="' +
      col +
      '" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round"/>' +
      "</svg>"
    );
  }

  function hydrateSparks(root) {
    var scope = root || document;
    var nodes = scope.querySelectorAll
      ? scope.querySelectorAll(".spark[data-addr]")
      : [];
    var list = [];
    for (var i = 0; i < nodes.length; i++) list.push(nodes[i]);
    // limit concurrent to avoid hammering API
    var queue = list.slice(0, 18);
    queue.forEach(function (el) {
      var addr = el.getAttribute("data-addr") || "";
      if (!addr || el.getAttribute("data-loaded") === "1") return;
      el.setAttribute("data-loaded", "1");
      el.innerHTML = '<div class="spark-wait">…</div>';
      fetch("/api/spark?a=" + encodeURIComponent(addr) + "&h=24&r=1h", {
        cache: "no-store",
      })
        .then(function (r) {
          return r.json();
        })
        .then(function (d) {
          if (!d || !d.ok || !d.closes || d.closes.length < 2) {
            el.innerHTML = sparkSvg([]);
            return;
          }
          el.innerHTML = sparkSvg(d.closes);
        })
        .catch(function () {
          el.innerHTML = sparkSvg([]);
        });
    });
  }

  function sparkSlot(ca) {
    if (!ca) return "";
    return (
      '<div class="spark" data-addr="' + esc(ca.toLowerCase()) + '"></div>'
    );
  }

  function renderDipHits(targetId, d, compact) {
    var el = $(targetId);
    if (!el) return;
    if (!d) {
      el.innerHTML = '<div class="hit"><em>No dip scan yet.</em></div>';
      return;
    }
    var hits = d.hits || [];
    if (!hits.length) {
      el.innerHTML =
        '<div class="hit"><em>No dip hits ≥20% (empty window is OK).</em></div>';
      return;
    }
    var max = compact ? 8 : 12;
    var html = "";
    for (var i = 0; i < Math.min(hits.length, max); i++) {
      var h = hits[i];
      var ca = h.address || "";
      html +=
        '<article class="hit">' +
        "<h3>$" +
        esc(h.symbol) +
        ' <span style="color:var(--muted);font-weight:500">' +
        esc(compact ? "" : h.name || "") +
        '</span> <span class="dump"> ' +
        esc(pct(h.drop_pct)) +
        "</span></h3>" +
        '<div class="meta">' +
        money(h.market_cap) +
        " mcap · " +
        money(h.liquidity) +
        " liq</div>" +
        sparkSlot(ca) +
        (compact
          ? ""
          : '<div class="ca">' +
            esc(ca) +
            "</div>") +
        socialBtns(
          {
            ca: ca,
            twitter: h.twitter_username || h.twitter,
            website: h.website,
            telegram: h.telegram,
          },
          compact
        ) +
        "</article>";
    }
    el.innerHTML = html;
    hydrateSparks(el);
  }

  function renderSmart(state) {
    var d = state.smart_buys;
    var brief =
      (state.briefs && state.briefs.smart_buys) || (d && d.brief) || "";
    setText("smart-brief", brief || "(no smart brief yet)");

    if (!d) {
      setText("smart-meta", "No rh_smart_buys.json yet.");
      setHtml("smart-hits", "");
      setHtml("smart-dropped", "");
      setHtml(
        "home-smart",
        '<div class="hit"><em>No smart scan yet.</em></div>'
      );
      return;
    }

    var cards = d.cards || [];
    var dropped = d.dropped_unsafe || [];
    setText(
      "smart-meta",
      [
        d.window_minutes != null ? d.window_minutes + "m" : "smart",
        "wallets " + (d.wallets_scanned != null ? d.wallets_scanned : "—"),
        "raw " + (d.raw_buys != null ? d.raw_buys : "—"),
        "safe " + cards.length,
        "dropped " +
          (d.dropped_unsafe_count != null
            ? d.dropped_unsafe_count
            : dropped.length),
        (d.generated_at || "").slice(0, 19),
      ].join(" · ")
    );

    var byTok = {};
    var order = [];
    for (var i = 0; i < cards.length; i++) {
      var c = cards[i];
      var ca = (c.token || "").toLowerCase();
      if (!ca) continue;
      if (!byTok[ca]) {
        byTok[ca] = {
          token: c.token,
          symbol: c.symbol,
          mcap: c.mcap,
          links: c.links || {},
          story: c.token_story || {},
          buyers: [],
        };
        order.push(ca);
      }
      byTok[ca].buyers.push(c);
    }

    var seen = {};
    var uniqDrop = [];
    for (var j = 0; j < dropped.length; j++) {
      var x = dropped[j];
      var tca = (x.token || "").toLowerCase();
      if (tca && seen[tca]) continue;
      if (tca) seen[tca] = true;
      uniqDrop.push(x);
    }

    if (uniqDrop.length) {
      var dh = "<h3>⛔ DROPPED unsafe / honeypot</h3>";
      for (var k = 0; k < Math.min(uniqDrop.length, 8); k++) {
        var u = uniqDrop[k];
        var sec = u.security || {};
        var why = [];
        if (sec.is_honeypot) why.push("HONEYPOT");
        if (sec.is_show_alert) why.push("Unsafe");
        dh +=
          '<div style="margin-bottom:10px"><strong>$' +
          esc(u.symbol || "?") +
          '</strong><div class="ca">' +
          esc(u.token || "") +
          '</div><div style="font-size:.8rem">' +
          esc(why.join(" · ") || "flagged") +
          "</div>" +
          socialBtns({ ca: u.token }) +
          "</div>";
      }
      setHtml("smart-dropped", dh);
    } else {
      setHtml("smart-dropped", "");
    }

    function cardHtml(g, compact) {
      var story = g.story || {};
      var whtml = "";
      var buyers = g.buyers || [];
      var bm = compact ? 2 : 8;
      for (var b = 0; b < Math.min(buyers.length, bm); b++) {
        var bb = buyers[b];
        whtml +=
          "<div>buy " +
          money(bb.amount_usd) +
          " · PnL " +
          money(bb.wallet_pnl) +
          "<code>" +
          esc(bb.wallet || "") +
          "</code></div>";
      }
      return (
        '<article class="hit"><h3>$' +
        esc(g.symbol || "?") +
        '</h3><div class="meta">' +
        money(g.mcap) +
        " mcap · " +
        buyers.length +
        ' buy(s)</div><div class="ca">' +
        esc(g.token || "") +
        "</div>" +
        socialBtns({
          ca: g.token,
          twitter: story.twitter || g.links.twitter,
          website: story.website || g.links.website,
          telegram: story.telegram,
        }) +
        (compact ? "" : '<div class="wallets">' + whtml + "</div>") +
        "</article>"
      );
    }

    if (!order.length) {
      setHtml(
        "smart-hits",
        '<div class="hit"><em>No safe buys in window.</em></div>'
      );
      setHtml(
        "home-smart",
        '<div class="hit"><em>No safe buys.</em></div>'
      );
      return;
    }

    var full = "";
    var home = "";
    for (var n = 0; n < order.length && n < 12; n++) {
      full += cardHtml(byTok[order[n]], false);
      if (n < 3) home += cardHtml(byTok[order[n]], true);
    }
    setHtml("smart-hits", full);
    setHtml("home-smart", home);
  }

  function renderHot(state) {
    var d = state.hot_search;
    var brief =
      (state.briefs && state.briefs.hot_search) || (d && d.brief) || "";
    setText("hot-brief", brief || "(no hot search yet — Run hot)");

    if (!d || !(d.tokens && d.tokens.length)) {
      setText("hot-meta", "No hot_search.json yet.");
      setHtml(
        "hot-hits",
        '<div class="hit"><em>Click Run hot to load GMGN hot search (RH).</em></div>'
      );
      setHtml(
        "home-hot",
        '<div class="hit"><em>No hot search yet.</em></div>'
      );
      return;
    }

    var tokens = d.tokens || [];
    setText(
      "hot-meta",
      [
        "interval " + (d.interval || "24h"),
        "count " + tokens.length,
        (d.generated_at || "").slice(0, 19),
      ].join(" · ")
    );

    function row(t, compact) {
      var ca = t.address || "";
      var rank = t.rank != null ? t.rank : "";
      var ch = t.price_change_percent;
      var chs = ch == null || isNaN(Number(ch)) ? "" : Number(ch).toFixed(1) + "%";
      var dumpCls = ch != null && Number(ch) < 0 ? "dump" : "";
      return (
        '<article class="hit">' +
        "<h3>#" +
        esc(rank) +
        " $" +
        esc(t.symbol || "?") +
        " " +
        (chs
          ? '<span class="' + dumpCls + '"> ' + esc(chs) + "</span>"
          : "") +
        "</h3>" +
        '<div class="meta">' +
        money(t.market_cap) +
        " · " +
        money(t.volume) +
        " vol · v" +
        esc(t.visiting_count != null ? t.visiting_count : "—") +
        "</div>" +
        sparkSlot(ca) +
        (compact
          ? ""
          : '<div class="ca">' + esc(ca) + "</div>") +
        socialBtns(
          {
            ca: ca,
            twitter: t.twitter_username,
            website: t.website,
            telegram: t.telegram,
          },
          compact
        ) +
        "</article>"
      );
    }

    var full = "";
    var home = "";
    for (var i = 0; i < tokens.length && i < 40; i++) {
      full += row(tokens[i], false);
      if (i < 12) home += row(tokens[i], true);
    }
    setHtml("hot-hits", full);
    setHtml("home-hot", home);
    hydrateSparks($("hot-hits"));
    hydrateSparks($("home-hot"));
  }

  function renderAll(state) {
    state = state || {};
    var wallets =
      (state.wallets && state.wallets.top_wallets) || [];

    renderWalletsList("home-wallets", wallets, false);
    renderWalletsList("wallets-full", wallets, true);
    renderHot(state);

    var dip =
      state.buy_the_dip_24h ||
      state.buy_the_dip_1h ||
      state.buy_the_dip ||
      null;

    if (dip) {
      setText(
        "dip-meta",
        [
          dip.interval ? "interval " + dip.interval : "dip",
          "scanned " + (dip.scanned != null ? dip.scanned : "—"),
          "hits " + ((dip.hits && dip.hits.length) || 0),
          (dip.generated_at || "").slice(0, 19),
        ].join(" · ")
      );
    } else {
      setText("dip-meta", "No dip data");
    }

    renderDipHits("dip-hits", dip, false);
    renderDipHits("home-dip", dip, true);

    var dbrief =
      (state.briefs &&
        (state.briefs.buy_the_dip_24h || state.briefs.buy_the_dip)) ||
      (dip && dip.brief) ||
      "";
    setText("dip-brief", dbrief || "(no brief)");

    setText(
      "wallets-brief",
      (state.briefs && state.briefs.wallets) ||
        (state.wallets && state.wallets.brief) ||
        "(no wallet brief)"
    );

    renderSmart(state);
  }

  function load() {
    var st = $("status");
    fetch("/api/state?_=" + Date.now(), { cache: "no-store" })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (data) {
        var nW =
          (data.wallets && data.wallets.top_wallets && data.wallets.top_wallets.length) ||
          0;
        if (st) {
          st.innerHTML =
            '<span class="pill ok">online</span>' +
            '<span class="pill">' +
            esc((data.time || "").slice(0, 19)) +
            " UTC</span>" +
            '<span class="pill">wallets ' +
            nW +
            "</span>" +
            '<span class="pill">' +
            esc(((data.cache && data.cache.length) || 0) + " cache") +
            "</span>" +
            '<span class="pill">research only</span>';
        }
        try {
          renderAll(data);
        } catch (re) {
          if (st) {
            st.innerHTML =
              '<span class="pill bad">render error · ' +
              esc(re.message || re) +
              "</span>";
          }
          console.error(re);
        }
      })
      .catch(function (e) {
        if (st) {
          st.innerHTML =
            '<span class="pill bad">offline · ' +
            esc(e.message || e) +
            "</span>";
        }
        console.error(e);
      });
  }

  function scan(kind) {
    var ids = [
      "btn-dip",
      "btn-smart",
      "btn-all",
      "btn-refresh",
      "btn-wallets",
      "btn-hot",
    ];
    ids.forEach(function (id) {
      var b = $(id);
      if (b) b.disabled = true;
    });
    toast("Running " + kind + "…");
    fetch("/api/scan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ kind: kind }),
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (!data.ok) throw new Error(data.error || "scan failed");
        toast(kind + " done");
        load();
      })
      .catch(function (e) {
        toast(String(e.message || e), true);
      })
      .finally(function () {
        ids.forEach(function (id) {
          var b = $(id);
          if (b) b.disabled = false;
        });
      });
  }

  function bind(id, fn) {
    var el = $(id);
    if (el) el.onclick = fn;
  }

  bind("btn-refresh", function () {
    load();
  });
  bind("btn-dip", function () {
    scan("dip");
  });
  bind("btn-smart", function () {
    scan("smart");
  });
  bind("btn-wallets", function () {
    scan("wallets");
  });
  bind("btn-hot", function () {
    scan("hot");
  });
  bind("btn-all", function () {
    scan("all");
  });

  load();
  setInterval(load, 30000);
})();
