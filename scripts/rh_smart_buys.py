#!/usr/bin/env python3
"""Robinhood Chain ONLY — high-PnL wallet buys on low-mcap / new tokens.

Stack:
  - Birdeye: top profit wallets (x-chain robinhood) + their recent buys
  - GMGN: token info + trenches/trending on chain=robinhood (mcap context)
  - NO sol/bsc/base/eth tracks

Usage:
  python3 scripts/rh_smart_buys.py --minutes 5 --max-mcap 200000
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__import__("os").environ.get("RH_DESK_ROOT") or Path(__file__).resolve().parents[1]).resolve()
sys.path.insert(0, str(ROOT / "scripts"))

from birdeye_client import load_api_key, request  # noqa: E402

CHAIN = "robinhood"
STABLES = {
    "USDC",
    "USDT",
    "USD1",
    "USDG",
    "ETH",
    "WETH",
    "DAI",
    "SOL",
    "WSOL",
}


def gmgn_cmd(*args: str) -> dict[str, Any] | list | None:
    env = os.environ.copy()
    tools_bin = str(ROOT / "tools/node_modules/.bin")
    env["PATH"] = tools_bin + ":" + env.get("PATH", "")
    try:
        r = subprocess.run(
            ["gmgn-cli", *args, "--raw"],
            capture_output=True,
            text=True,
            timeout=90,
            env=env,
        )
    except Exception as e:
        return {"error": str(e)}
    out = (r.stdout or "").strip()
    err = (r.stderr or "").strip()
    if not out:
        return {"error": err or "empty", "code": r.returncode}
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return {"error": "not_json", "raw": out[:400], "stderr": err[:300]}


def short_addr(a: str | None, n: int = 4) -> str:
    if not a:
        return "?"
    if len(a) <= n * 2 + 3:
        return a
    return f"{a[:n]}…{a[-n:]}"


def fmt_usd(x: Any) -> str:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return "n/a"
    if abs(v) >= 1_000_000:
        return f"${v/1_000_000:.2f}M"
    if abs(v) >= 1_000:
        return f"${v/1_000:.1f}k"
    if abs(v) >= 1:
        return f"${v:.0f}"
    return f"${v:.4f}"


def fmt_age(sec: int) -> str:
    if sec < 60:
        return f"{sec}s ago"
    if sec < 3600:
        return f"{sec // 60}m {sec % 60}s ago"
    return f"{sec // 3600}h ago"


def links(token: str | None, wallet: str | None, tx: str | None) -> dict[str, str]:
    out: dict[str, str] = {}
    if token:
        out["token_gmgn"] = f"https://gmgn.ai/robinhood/token/{token}"
        out["token_explorer"] = f"https://robinhoodchain.blockscout.com/token/{token}"
    if wallet:
        out["trader_gmgn"] = f"https://gmgn.ai/robinhood/address/{wallet}"
        out["trader_explorer"] = f"https://robinhoodchain.blockscout.com/address/{wallet}"
    if tx:
        out["tx"] = f"https://robinhoodchain.blockscout.com/tx/{tx}"
    return out


def mcap_from_gmgn_info(info: Any) -> float | None:
    if not isinstance(info, dict) or info.get("error"):
        return None
    d = info.get("data") if isinstance(info.get("data"), dict) else info
    price = None
    p = d.get("price")
    if isinstance(p, dict):
        try:
            price = float(p.get("price") or 0)
        except (TypeError, ValueError):
            price = None
    supply = None
    for sk in ("circulating_supply", "total_supply", "max_supply"):
        if d.get(sk) is not None:
            try:
                supply = float(str(d[sk]).replace(",", ""))
                break
            except (TypeError, ValueError):
                pass
    if price and supply:
        return price * supply
    for k in ("usd_market_cap", "market_cap", "mc", "marketcap"):
        if d.get(k) is not None:
            try:
                return float(d[k])
            except (TypeError, ValueError):
                pass
    return None


def token_security(addr: str) -> dict[str, Any]:
    """GMGN token security on Robinhood. Returns flags + risk verdict."""
    raw = gmgn_cmd("token", "security", "--chain", CHAIN, "--address", addr)
    if not isinstance(raw, dict) or raw.get("error"):
        return {
            "ok": False,
            "error": (raw or {}).get("error") if isinstance(raw, dict) else "no_data",
            "is_honeypot": None,
            "unsafe": False,  # unknown: soft-flag, don't hard-drop entire tape
            "soft_risk": True,
            "reasons": ["security API unavailable — verify manually"],
            "raw": raw,
        }
    d = raw.get("data") if isinstance(raw.get("data"), dict) else raw
    reasons: list[str] = []
    honeypot = d.get("is_honeypot")
    if honeypot is True or d.get("honeypot") in (1, "1", True):
        reasons.append("HONEYPOT (is_honeypot=true)")
    if d.get("is_show_alert") is True:
        reasons.append("GMGN show_alert=true (Unsafe banner)")
    if d.get("can_sell") in (0, "0") and d.get("can_not_sell") not in (None, 0, "0"):
        reasons.append("can_sell=0")
    # taxes
    try:
        sell_tax = float(d.get("sell_tax") or 0)
        buy_tax = float(d.get("buy_tax") or 0)
    except (TypeError, ValueError):
        sell_tax = buy_tax = 0.0
    if sell_tax >= 10:
        reasons.append(f"high sell_tax={sell_tax}")
    if buy_tax >= 10:
        reasons.append(f"high buy_tax={buy_tax}")
    if d.get("is_blacklist") is True or d.get("blacklist") == 1:
        reasons.append("blacklist flag")
    if d.get("is_open_source") is False or d.get("open_source") in (0, "0"):
        reasons.append("not open source")
    # renounced mint false can be risk on some chains
    if d.get("renounced_mint") is False and d.get("is_renounced") is not True:
        reasons.append("mint may not be renounced")
    lock = d.get("lock_summary") if isinstance(d.get("lock_summary"), dict) else {}
    try:
        lock_pct = float(lock.get("lock_percent") or 0)
    except (TypeError, ValueError):
        lock_pct = 0.0
    if lock.get("is_locked") is False and lock_pct == 0:
        reasons.append("LP not locked (lock_percent=0)")

    is_hp = honeypot is True or d.get("honeypot") in (1, "1", True)
    # hard unsafe: honeypot or alert
    unsafe = bool(is_hp or d.get("is_show_alert") is True or sell_tax >= 50)
    soft_risk = bool(reasons) and not unsafe

    return {
        "ok": True,
        "is_honeypot": is_hp,
        "is_show_alert": d.get("is_show_alert"),
        "can_sell": d.get("can_sell"),
        "buy_tax": d.get("buy_tax"),
        "sell_tax": d.get("sell_tax"),
        "is_open_source": d.get("is_open_source"),
        "top_10_holder_rate": d.get("top_10_holder_rate"),
        "lock_summary": lock,
        "unsafe": unsafe,
        "soft_risk": soft_risk,
        "reasons": reasons or (["no major flags"] if not unsafe else []),
        "raw": d,
    }


def token_story(info: Any) -> dict[str, Any]:
    story: dict[str, Any] = {
        "name": None,
        "symbol": None,
        "launchpad": None,
        "age": None,
        "mcap": None,
        "liquidity": None,
        "holders": None,
        "vol_5m": None,
        "vol_1h": None,
        "creator": None,
        "creator_status": None,
        "twitter": None,
        "website": None,
        "telegram": None,
        "why": [],
    }
    if not isinstance(info, dict) or info.get("error"):
        story["why"].append("Token metadata incomplete on GMGN RH")
        return story
    d = info.get("data") if isinstance(info.get("data"), dict) else info
    story["name"] = d.get("name")
    story["symbol"] = d.get("symbol")
    story["launchpad"] = d.get("launchpad_platform") or d.get("launchpad")
    story["holders"] = d.get("holder_count")
    story["liquidity"] = d.get("liquidity")
    story["mcap"] = mcap_from_gmgn_info(info)
    story["twitter"] = d.get("twitter_username") or d.get("twitter")
    story["website"] = d.get("website")
    story["telegram"] = d.get("telegram")
    p = d.get("price") if isinstance(d.get("price"), dict) else {}
    story["vol_5m"] = p.get("volume_5m") or p.get("volume")
    story["vol_1h"] = p.get("volume_1h")
    created = d.get("creation_timestamp") or d.get("open_timestamp")
    if created:
        try:
            age_s = int(time.time()) - int(created)
            story["age"] = f"{age_s // 60}m" if age_s < 3600 else f"{age_s // 3600}h"
            story["age_sec"] = age_s
        except (TypeError, ValueError):
            pass
    dev = d.get("dev") if isinstance(d.get("dev"), dict) else {}
    story["creator"] = dev.get("creator_address") or d.get("creator")
    story["creator_status"] = dev.get("creator_token_status")
    if story["launchpad"]:
        story["why"].append(f"Launchpad: {story['launchpad']}")
    if story.get("age"):
        story["why"].append(f"Token age ~{story['age']}")
    if story["mcap"] is not None:
        story["why"].append(f"Market cap {fmt_usd(story['mcap'])} (RH)")
    if story["creator_status"]:
        story["why"].append(f"Creator: {story['creator_status']}")
    if story["twitter"]:
        tw = story["twitter"]
        if isinstance(tw, str) and tw.startswith("http"):
            story["why"].append(f"Social: {tw}")
        else:
            story["why"].append(f"Twitter: @{str(tw).lstrip('@')}")
    if not story["why"]:
        story["why"].append("Bought by a top-PnL Robinhood Chain wallet in the scan window")
    return story


def classify_buy(item: dict[str, Any]) -> dict[str, Any] | None:
    base = item.get("base") or {}
    quote = item.get("quote") or {}
    base_to = (base.get("type_swap") or "").lower() == "to"
    quote_to = (quote.get("type_swap") or "").lower() == "to"
    bought = None
    if base_to and (base.get("symbol") or "").upper() not in STABLES:
        bought = base
    elif quote_to and (quote.get("symbol") or "").upper() not in STABLES:
        bought = quote
    elif base_to:
        bought = base
    elif quote_to:
        bought = quote
    if not bought:
        return None
    sym = (bought.get("symbol") or "?").upper()
    if sym in STABLES:
        return None
    return {
        "symbol": bought.get("symbol"),
        "address": (bought.get("address") or "").lower() if bought.get("address") else None,
        "ui_amount": bought.get("ui_amount") or bought.get("ui_change_amount"),
        "price": bought.get("price") or bought.get("nearest_price"),
        "volume_usd": item.get("volume_usd"),
        "tx_hash": item.get("tx_hash"),
        "block_unix_time": item.get("block_unix_time"),
        "tx_type": item.get("tx_type"),
        "source": item.get("source"),
    }


def flatten_trenches(payload: Any) -> list[dict]:
    out: list[dict] = []
    if not isinstance(payload, dict):
        return out

    def walk(x: Any) -> None:
        if isinstance(x, list):
            for i in x:
                if isinstance(i, dict) and (i.get("address") or i.get("symbol")):
                    out.append(i)
                else:
                    walk(i)
        elif isinstance(x, dict):
            for v in x.values():
                walk(v)

    walk(payload)
    return out


def render_brief(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("══════════════════════════════════════")
    lines.append("ROBINHOOD CHAIN · HIGH-PnL WALLET BUYS")
    lines.append(
        f"Window: last {payload['window_minutes']:g} min · mcap ≤ {fmt_usd(payload['max_mcap'])}"
    )
    lines.append(f"Time: {payload['generated_at']}")
    lines.append("Chain lock: robinhood ONLY (no SOL / Base / BSC)")
    lines.append("══════════════════════════════════════")
    lines.append("")
    lines.append(
        f"Birdeye top-PnL wallets scanned: {payload.get('wallets_scanned', 0)} · "
        f"raw buys in window: {payload.get('raw_buys', 0)} · "
        f"matched safe: {len(payload.get('cards') or [])} · "
        f"dropped unsafe/honeypot: {payload.get('dropped_unsafe_count', 0)}"
    )
    lines.append("Security: GMGN token security (honeypot/alert/tax). Unsafe tokens DROPPED by default.")
    lines.append("")

    dropped = payload.get("dropped_unsafe") or []
    if dropped:
        lines.append("──────────────────────────────────────")
        lines.append("⛔ DROPPED AS UNSAFE / HONEYPOT (do not buy)")
        for d in dropped[:15]:
            sec = d.get("security") or {}
            lines.append(f"  · ${d.get('symbol')}")
            lines.append(f"    CA (full): {d.get('token')}")
            lines.append(f"    Reasons: {', '.join(sec.get('reasons') or ['unsafe'])}")
            if (d.get("links") or {}).get("token_gmgn"):
                lines.append(f"    {d['links']['token_gmgn']}")
        lines.append("")

    cards = payload.get("cards") or []
    if not cards:
        lines.append("No matching SAFE RH buys in this window.")
        lines.append("Try --minutes 30 or --max-mcap 500000 or --top 20")
        if dropped:
            lines.append("(There were buys, but all failed the security gate — see DROPPED above.)")
    else:
        by_tok: dict[str, list] = {}
        for c in cards:
            by_tok.setdefault(c.get("token") or "?", []).append(c)
        rank = 0
        for token, events in sorted(
            by_tok.items(),
            key=lambda kv: -sum(float(e.get("amount_usd") or 0) for e in kv[1]),
        ):
            rank += 1
            e0 = events[0]
            story = e0.get("token_story") or {}
            lines.append("──────────────────────────────────────")
            lines.append(
                f"#{rank}  ${story.get('symbol') or e0.get('symbol')}  —  {story.get('name') or ''}".rstrip()
            )
            # Full CA only — never abbreviated (so Telegram copy works)
            lines.append("CA (full, copy this):")
            lines.append(str(token))
            lines.append(
                f"Mcap {fmt_usd(story.get('mcap') or e0.get('mcap'))} · "
                f"Liq {fmt_usd(story.get('liquidity'))} · "
                f"Holders {story.get('holders') or 'n/a'} · "
                f"Age {story.get('age') or 'n/a'}"
            )
            if story.get("vol_5m") or story.get("vol_1h"):
                lines.append(
                    f"Volume 5m {fmt_usd(story.get('vol_5m'))} · 1h {fmt_usd(story.get('vol_1h'))}"
                )
            lines.append("")
            lines.append("WHY THIS TOKEN IS ON THE LIST:")
            for w in story.get("why") or []:
                lines.append(f"  • {w}")
            # socials
            if story.get("website"):
                lines.append(f"  • Website: {story['website']}")
            if story.get("telegram"):
                lines.append(f"  • Telegram: {story['telegram']}")
            lines.append("")
            lines.append("WHO BOUGHT (top-PnL wallets on Robinhood Chain):")
            seen = set()
            for e in sorted(events, key=lambda x: -(float(x.get("amount_usd") or 0))):
                key = (e.get("wallet"), e.get("tx"))
                if key in seen:
                    continue
                seen.add(key)
                pnl = e.get("wallet_pnl")
                lines.append(
                    f"  → bought {fmt_usd(e.get('amount_usd'))} ({fmt_age(int(e.get('age_sec') or 0))})"
                )
                lines.append(
                    f"     Why this wallet: Birdeye top profit on RH · "
                    f"wallet PnL {fmt_usd(pnl)} · trades {e.get('wallet_trades')} · vol {fmt_usd(e.get('wallet_volume'))}"
                )
                lines.append("     • Ranked among highest-PnL traders on Robinhood Chain (Birdeye gainers)")
                lines.append("     • Buy happened inside your time window — not a historical bag")
                lines.append("     Wallet (full, copy this):")
                lines.append(f"     {e.get('wallet')}")
                ln = e.get("links") or {}
                if ln.get("trader_gmgn"):
                    lines.append(f"     Trader GMGN: {ln['trader_gmgn']}")
                if ln.get("trader_explorer"):
                    lines.append(f"     Trader explorer: {ln['trader_explorer']}")
                if ln.get("tx"):
                    lines.append(f"     Tx: {ln['tx']}")
            lines.append("")
            ln0 = e0.get("links") or {}
            lines.append("LINKS:")
            if ln0.get("token_gmgn"):
                lines.append(f"  GMGN:     {ln0['token_gmgn']}")
            if ln0.get("token_explorer"):
                lines.append(f"  Explorer: {ln0['token_explorer']}")
            lines.append("")

    watch = payload.get("new_token_watch") or []
    if watch:
        lines.append("──────────────────────────────────────")
        lines.append("NEW / LOW-MCAP ON RH (GMGN trenches · not necessarily bought this window)")
        for t in watch[:12]:
            lines.append(
                f"  · ${t.get('symbol')} · mcap {fmt_usd(t.get('mcap'))} · age {t.get('age') or 'n/a'}"
            )
            lines.append(f"    CA: {t.get('address')}")
            if t.get("gmgn"):
                lines.append(f"    {t['gmgn']}")
        lines.append("")

    lines.append("──────────────────────────────────────")
    lines.append("Sources: Birdeye (RH PnL + buys) · GMGN (RH token/trenches).")
    lines.append("DYOR. Not financial advice. Research only. ROBINHOOD CHAIN ONLY.")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, default=5)
    ap.add_argument("--max-mcap", type=float, default=200_000)
    ap.add_argument("--min-buy-usd", type=float, default=20)
    ap.add_argument("--top", type=int, default=12, help="top PnL wallets from Birdeye")
    ap.add_argument("--max-token-age-min", type=float, default=0, help="0 = no age filter; e.g. 60 = only tokens younger than 60m")
    ap.add_argument(
        "--include-unsafe",
        action="store_true",
        help="Keep honeypots/unsafe tokens in brief (default: DROP them)",
    )
    ap.add_argument("--json-out", default="")
    ap.add_argument("--brief-out", default="")
    args = ap.parse_args()

    now = int(time.time())
    cutoff = now - int(args.minutes * 60)
    api_key = load_api_key(env_file=str(ROOT / ".env"))

    gainers = request(
        "/trader/gainers-losers",
        api_key=api_key,
        chain=CHAIN,
        params={
            "type": "today",
            "sort_by": "PnL",
            "sort_type": "desc",
            "offset": 0,
            "limit": min(args.top, 100),
        },
    )
    if not gainers.get("success"):
        # fallback 1W
        gainers = request(
            "/trader/gainers-losers",
            api_key=api_key,
            chain=CHAIN,
            params={
                "type": "1W",
                "sort_by": "PnL",
                "sort_type": "desc",
                "offset": 0,
                "limit": min(args.top, 100),
            },
        )

    wallets = ((gainers.get("data") or {}).get("items")) or []
    raw_buys = 0
    events: list[dict] = []

    for row in wallets:
        w = row.get("address")
        if not w:
            continue
        txs = request(
            "/trader/txs/seek_by_time",
            api_key=api_key,
            chain=CHAIN,
            params={
                "address": w,
                "offset": 0,
                "limit": 40,
                "after_time": cutoff,
            },
        )
        if not txs.get("success"):
            # retry without after_time
            time.sleep(1.5)
            txs = request(
                "/trader/txs/seek_by_time",
                api_key=api_key,
                chain=CHAIN,
                params={"address": w, "offset": 0, "limit": 40},
            )
        time.sleep(1.3)
        if not txs.get("success"):
            continue
        for it in ((txs.get("data") or {}).get("items")) or []:
            ts = int(it.get("block_unix_time") or 0)
            if ts and ts < cutoff:
                continue
            b = classify_buy(it if isinstance(it, dict) else {})
            if not b or not b.get("address"):
                continue
            try:
                usd = float(b.get("volume_usd") or 0)
            except (TypeError, ValueError):
                usd = 0.0
            if usd < args.min_buy_usd:
                continue
            raw_buys += 1
            events.append(
                {
                    "wallet": w,
                    "wallet_pnl": row.get("pnl"),
                    "wallet_trades": row.get("trade_count"),
                    "wallet_volume": row.get("volume"),
                    "token": b["address"],
                    "symbol": b.get("symbol"),
                    "amount_usd": usd,
                    "tx": b.get("tx_hash"),
                    "timestamp": ts or now,
                    "age_sec": now - (ts or now),
                }
            )

    # GMGN enrich + SECURITY
    info_cache: dict[str, Any] = {}
    sec_cache: dict[str, dict] = {}
    cards: list[dict] = []
    dropped_unsafe: list[dict] = []
    for ev in events:
        tok = ev["token"]
        if tok not in info_cache:
            info_cache[tok] = gmgn_cmd("token", "info", "--chain", CHAIN, "--address", tok)
            time.sleep(0.2)
        if tok not in sec_cache:
            sec_cache[tok] = token_security(tok)
            time.sleep(0.25)
        info = info_cache[tok]
        sec = sec_cache[tok]
        story = token_story(info)
        mc = story.get("mcap")
        if mc is not None and mc > args.max_mcap:
            continue
        if args.max_token_age_min > 0 and story.get("age_sec"):
            if story["age_sec"] > args.max_token_age_min * 60:
                continue
        if not story.get("symbol"):
            story["symbol"] = ev.get("symbol")
        if mc is None:
            story["why"].append("Mcap unknown on GMGN — kept because top-PnL RH wallet bought it")

        # Security gate
        if sec.get("is_honeypot"):
            story["why"].insert(0, "⛔ HONEYPOT")
        for r in sec.get("reasons") or []:
            if r not in story["why"]:
                story["why"].append(f"Security: {r}")

        if sec.get("unsafe") and not args.include_unsafe:
            dropped_unsafe.append(
                {
                    "token": tok,
                    "symbol": story.get("symbol") or ev.get("symbol"),
                    "mcap": mc,
                    "amount_usd": ev.get("amount_usd"),
                    "wallet": ev.get("wallet"),
                    "security": {k: sec.get(k) for k in (
                        "is_honeypot", "is_show_alert", "buy_tax", "sell_tax", "reasons", "unsafe"
                    )},
                    "links": links(tok, ev.get("wallet"), ev.get("tx")),
                }
            )
            continue

        ln = links(tok, ev["wallet"], ev.get("tx"))
        cards.append(
            {
                **ev,
                "mcap": mc,
                "token_story": story,
                "security": {k: sec.get(k) for k in (
                    "is_honeypot", "is_show_alert", "buy_tax", "sell_tax",
                    "is_open_source", "top_10_holder_rate", "reasons", "unsafe", "soft_risk",
                )},
                "links": ln,
            }
        )

    cards.sort(key=lambda x: (-(x.get("amount_usd") or 0), x.get("age_sec") or 0))

    # new token watch from trenches/trending RH
    new_watch: list[dict] = []
    trenches = gmgn_cmd(
        "market",
        "trenches",
        "--chain",
        CHAIN,
        "--type",
        "new_creation",
        "--max-marketcap",
        str(int(args.max_mcap)),
        "--max-created",
        "60m",
        "--limit",
        "30",
    )
    for t in flatten_trenches(trenches if isinstance(trenches, dict) else {}):
        addr = (t.get("address") or "").lower()
        if not addr:
            continue
        # trenches often expose is_honeypot
        if t.get("is_honeypot") in (True, 1, "1", "true"):
            continue
        try:
            mc = float(t.get("usd_market_cap") or t.get("market_cap") or 0)
        except (TypeError, ValueError):
            mc = 0
        if mc and mc > args.max_mcap:
            continue
        age = None
        cts = t.get("created_timestamp")
        if cts:
            try:
                age_s = now - int(cts)
                if age_s < 0:
                    age_s = 0
                age = f"{age_s // 60}m" if age_s < 3600 else f"{age_s // 3600}h"
            except (TypeError, ValueError):
                pass
        new_watch.append(
            {
                "address": addr,
                "symbol": t.get("symbol"),
                "mcap": mc or None,
                "age": age,
                "gmgn": f"https://gmgn.ai/robinhood/token/{addr}",
            }
        )

    # trending RH under mcap cap
    trending = gmgn_cmd(
        "market",
        "trending",
        "--chain",
        CHAIN,
        "--interval",
        "5m",
        "--max-marketcap",
        str(int(args.max_mcap)),
        "--limit",
        "20",
    )
    if isinstance(trending, dict):
        rank = ((trending.get("data") or {}).get("rank")) or trending.get("rank") or []
        if isinstance(rank, list):
            for t in rank:
                if not isinstance(t, dict):
                    continue
                addr = (t.get("address") or "").lower()
                if not addr:
                    continue
                if any(x["address"] == addr for x in new_watch):
                    continue
                try:
                    mc = float(t.get("market_cap") or 0)
                except (TypeError, ValueError):
                    mc = 0
                new_watch.append(
                    {
                        "address": addr,
                        "symbol": t.get("symbol"),
                        "mcap": mc or None,
                        "age": "trending_5m",
                        "gmgn": f"https://gmgn.ai/robinhood/token/{addr}",
                    }
                )

    payload = {
        "ok": True,
        "chain": CHAIN,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window_minutes": args.minutes,
        "max_mcap": args.max_mcap,
        "min_buy_usd": args.min_buy_usd,
        "include_unsafe": args.include_unsafe,
        "wallets_scanned": len(wallets),
        "raw_buys": raw_buys,
        "cards": cards,
        "dropped_unsafe": dropped_unsafe,
        "dropped_unsafe_count": len(dropped_unsafe),
        "new_token_watch": new_watch[:20],
        "gainers_ok": bool(gainers.get("success")),
    }
    brief = render_brief(payload)
    payload["brief"] = brief

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    if args.brief_out:
        Path(args.brief_out).write_text(brief, encoding="utf-8")
    print(brief)


if __name__ == "__main__":
    main()
