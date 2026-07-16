#!/usr/bin/env python3
"""Smart wallet tracker via Birdeye.

1) Top gainers (profit wallets) — GET /trader/gainers-losers
2) Recent buys per wallet — GET /trader/txs/seek_by_time (tx_type=buy when supported, else filter)

Usage:
  export BIRDEYE_API_KEY=...
  python3 scripts/smart_wallet_tracker.py --chain robinhood --window 1W --top 15 --buys 8
  python3 scripts/smart_wallet_tracker.py --chain solana --window today --top 10

Windows (Birdeye type): yesterday | today | 1W | 30d | 90d
  Note: 30d/90d often Solana-only per Birdeye docs; prefer today/1W for robinhood first.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# allow import from same dir
sys.path.insert(0, str(Path(__file__).resolve().parent))
from birdeye_client import load_api_key, request  # noqa: E402


def classify_buy(item: dict[str, Any]) -> dict[str, Any] | None:
    """Best-effort: treat side where trader receives non-quote meme as buy."""
    base = item.get("base") or {}
    quote = item.get("quote") or {}
    # type_swap: "to" means received that asset
    base_to = (base.get("type_swap") or "").lower() == "to"
    quote_to = (quote.get("type_swap") or "").lower() == "to"
    # Prefer token received that is not stable/gas heuristics
    stables = {
        "usdc",
        "usdt",
        "dai",
        "eth",
        "weth",
        "sol",
        "wsol",
        "bnb",
        "wbnb",
    }
    bought = None
    if base_to and (base.get("symbol") or "").lower() not in stables:
        bought = base
    elif quote_to and (quote.get("symbol") or "").lower() not in stables:
        bought = quote
    elif base_to:
        bought = base
    elif quote_to:
        bought = quote
    if not bought:
        return None
    return {
        "symbol": bought.get("symbol"),
        "address": bought.get("address"),
        "ui_amount": bought.get("ui_amount") or bought.get("ui_change_amount"),
        "price": bought.get("price") or bought.get("nearest_price"),
        "volume_usd": item.get("volume_usd"),
        "tx_hash": item.get("tx_hash"),
        "block_unix_time": item.get("block_unix_time"),
        "tx_type": item.get("tx_type"),
        "source": item.get("source"),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chain", default="robinhood")
    ap.add_argument("--window", default="1W", help="yesterday|today|1W|30d|90d")
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--buys", type=int, default=8, help="max recent buys per wallet")
    ap.add_argument("--sort-by", default="PnL", help="PnL|realized_pnl|unrealized_pnl")
    ap.add_argument("--api-key")
    ap.add_argument("--env-file")
    ap.add_argument("--sleep", type=float, default=1.2, help="pause between wallet trade calls (raise if 429)")
    ap.add_argument("--json-out", default="")
    ap.add_argument("--brief-out", default="")
    ap.add_argument("--skip-buys", action="store_true")
    args = ap.parse_args()

    api_key = load_api_key(args.api_key, args.env_file)
    chain = args.chain.lower()

    gainers = request(
        "/trader/gainers-losers",
        api_key=api_key,
        chain=chain,
        params={
            "type": args.window,
            "sort_by": args.sort_by,
            "sort_type": "desc",
            "offset": 0,
            "limit": min(args.top, 100),
        },
    )

    if not gainers.get("success"):
        out = {
            "ok": False,
            "stage": "gainers-losers",
            "chain": chain,
            "window": args.window,
            "response": gainers,
            "hint": "Check API key, package access for /trader/gainers-losers, and x-chain support.",
        }
        print(json.dumps(out, indent=2))
        sys.exit(2)

    items = ((gainers.get("data") or {}).get("items")) or []
    wallets: list[dict[str, Any]] = []

    after_time = None
    # optional time bound: last 7d if window 1W
    now = int(time.time())
    if args.window in {"today", "yesterday"}:
        after_time = now - 2 * 86400
    elif args.window == "1W":
        after_time = now - 8 * 86400
    elif args.window == "30d":
        after_time = now - 31 * 86400
    elif args.window == "90d":
        after_time = now - 91 * 86400

    for row in items[: args.top]:
        addr = row.get("address")
        entry: dict[str, Any] = {
            "address": addr,
            "network": row.get("network") or chain,
            "pnl": row.get("pnl"),
            "volume": row.get("volume"),
            "trade_count": row.get("trade_count"),
            "recent_buys": [],
            "buys_error": None,
        }
        if args.skip_buys or not addr:
            wallets.append(entry)
            continue

        txs = None
        for attempt in range(3):
            txs = request(
                "/trader/txs/seek_by_time",
                api_key=api_key,
                chain=chain,
                params={
                    "address": addr,
                    "offset": 0,
                    "limit": min(max(args.buys * 4, 20), 100),
                    "tx_type": "swap",
                    "after_time": after_time,
                },
            )
            if txs.get("success"):
                break
            status = txs.get("http_status")
            if status == 429:
                time.sleep(args.sleep * (attempt + 2) + 1.5)
                continue
            # retry without filters once
            txs = request(
                "/trader/txs/seek_by_time",
                api_key=api_key,
                chain=chain,
                params={
                    "address": addr,
                    "offset": 0,
                    "limit": min(max(args.buys * 4, 20), 100),
                },
            )
            if txs.get("success") or txs.get("http_status") != 429:
                break
            time.sleep(args.sleep * (attempt + 2) + 1.5)
        if not txs or not txs.get("success"):
            entry["buys_error"] = txs
        else:
            buys = []
            seen_tx = set()
            for it in ((txs.get("data") or {}).get("items")) or []:
                b = classify_buy(it if isinstance(it, dict) else {})
                if not b:
                    continue
                # skip gas/wrappers for meme desk signal
                sym = (b.get("symbol") or "").upper()
                if sym in {"WETH", "ETH", "USDC", "USDT", "DAI", "SOL", "WSOL"}:
                    continue
                txh = b.get("tx_hash") or ""
                dedupe = f"{txh}:{b.get('address')}"
                if dedupe in seen_tx:
                    continue
                seen_tx.add(dedupe)
                buys.append(b)
                if len(buys) >= args.buys:
                    break
            entry["recent_buys"] = buys
        wallets.append(entry)
        time.sleep(args.sleep)

    # aggregate hot buys
    heat: dict[str, dict[str, Any]] = {}
    for w in wallets:
        for b in w.get("recent_buys") or []:
            key = (b.get("address") or b.get("symbol") or "?").lower()
            h = heat.setdefault(
                key,
                {
                    "symbol": b.get("symbol"),
                    "address": b.get("address"),
                    "buyers": set(),
                    "count": 0,
                    "volume_usd_sum": 0.0,
                },
            )
            h["count"] += 1
            if w.get("address"):
                h["buyers"].add(w["address"])
            try:
                h["volume_usd_sum"] += float(b.get("volume_usd") or 0)
            except (TypeError, ValueError):
                pass

    hot = []
    for _, h in heat.items():
        hot.append(
            {
                "symbol": h["symbol"],
                "address": h["address"],
                "buy_events": h["count"],
                "unique_smart_wallets": len(h["buyers"]),
                "volume_usd_sum": h["volume_usd_sum"],
                "buyer_sample": list(h["buyers"])[:5],
            }
        )
    hot.sort(key=lambda x: (-x["unique_smart_wallets"], -x["buy_events"], -x["volume_usd_sum"]))

    payload = {
        "ok": True,
        "chain": chain,
        "window": args.window,
        "sort_by": args.sort_by,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "top_wallets": wallets,
        "hot_buys": hot[:30],
        "source": "birdeye",
        "endpoints": ["/trader/gainers-losers", "/trader/txs/seek_by_time"],
    }

    # brief
    lines = [
        f"RH SMART WALLETS · {chain} · {args.window} · {payload['generated_at']}",
        f"Top {len(wallets)} by {args.sort_by} (Birdeye gainers-losers)",
        "",
        "## TOP PROFIT WALLETS",
    ]
    for i, w in enumerate(wallets, 1):
        pnl = w.get("pnl")
        try:
            pnl_s = f"${float(pnl):,.0f}" if pnl is not None else "n/a"
        except (TypeError, ValueError):
            pnl_s = str(pnl)
        lines.append(
            f"{i}. `{w.get('address')}` · PnL {pnl_s} · trades {w.get('trade_count')} · vol {w.get('volume')}"
        )
        buys = w.get("recent_buys") or []
        if w.get("buys_error"):
            lines.append("   buys: error (see JSON)")
        elif not buys:
            lines.append("   buys: (none parsed)")
        else:
            lines.append("   Recent BUYS:")
            for b in buys:
                ts = b.get("block_unix_time")
                tss = (
                    datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
                    if isinstance(ts, (int, float))
                    else "?"
                )
                lines.append(
                    f"   - ${b.get('symbol')} `{b.get('address')}` · usd {b.get('volume_usd')} · {tss} · tx {b.get('tx_hash')}"
                )
        lines.append("")

    lines.append("## HOT BUYS (across top wallets)")
    if not hot:
        lines.append("(no aggregated buys)")
    for h in hot[:15]:
        lines.append(
            f"· ${h.get('symbol')} `{h.get('address')}` · wallets {h['unique_smart_wallets']} · events {h['buy_events']} · usd_sum {h['volume_usd_sum']:.0f}"
        )
    lines.append("")
    lines.append("DYOR. Not financial advice. Data: Birdeye. Research only.")

    brief = "\n".join(lines)
    payload["brief"] = brief

    text = json.dumps(payload, indent=2, default=str)
    if args.json_out:
        Path(args.json_out).write_text(text, encoding="utf-8")
    if args.brief_out:
        Path(args.brief_out).write_text(brief, encoding="utf-8")
    # always print brief for humans; full json to stdout if no brief-out only? print both sections
    print(brief)
    print("\n--- JSON_OK ---")
    print(text if not args.json_out else f"wrote {args.json_out}")


if __name__ == "__main__":
    main()
