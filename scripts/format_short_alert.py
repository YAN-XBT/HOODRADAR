#!/usr/bin/env python3
"""format_short_alert.py — Telegram-sized summaries from JSON artifacts.

Usage:
  python3 scripts/format_short_alert.py cron/cache/buy_the_dip.json
  python3 scripts/format_short_alert.py cron/cache/rh_scan_safe.json
  python3 scripts/format_short_alert.py cron/cache/buy_the_dip.json --max 3
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def fmt_usd(x: Any) -> str:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return "?"
    if abs(v) >= 1_000_000:
        return f"${v/1_000_000:.2f}M"
    if abs(v) >= 1_000:
        return f"${v/1_000:.1f}k"
    return f"${v:.0f}"


def fmt_pct(x: Any) -> str:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return "?"
    return f"{v:+.1f}%"


def short_dip(data: dict, max_n: int) -> str:
    lines = []
    lines.append(f"BUY THE DIP · RH · {data.get('interval', '?')}")
    lines.append(
        f"top{data.get('top_n', 10)} · drop≤-{data.get('min_drop_pct', 20):g}% · "
        f"mcap≥{fmt_usd(data.get('min_mcap'))}"
    )
    hits = data.get("hits") or []
    if not hits:
        lines.append("No large dumps ≥20% in top trend right now.")
        near = data.get("near_misses") or []
        if near:
            t = near[0]
            lines.append(
                f"Closest: ${t.get('symbol')} {fmt_pct(t.get('drop_pct'))} "
                f"mcap {fmt_usd(t.get('market_cap'))}"
            )
        lines.append("DYOR · research only · RH only")
        return "\n".join(lines)

    for i, t in enumerate(hits[:max_n], 1):
        lines.append("")
        lines.append(f"{i}) ${t.get('symbol')} {fmt_pct(t.get('drop_pct'))}")
        lines.append(
            f"mcap {fmt_usd(t.get('market_cap'))} · liq {fmt_usd(t.get('liquidity'))}"
        )
        lines.append(str(t.get("address")))
        lines.append(f"https://gmgn.ai/robinhood/token/{t.get('address')}")
    if data.get("dropped_unsafe_count"):
        lines.append("")
        lines.append(f"Also dropped unsafe: {data['dropped_unsafe_count']}")
    lines.append("")
    lines.append("DYOR · not financial advice · RH only")
    return "\n".join(lines)


def short_smart(data: dict, max_n: int) -> str:
    lines = []
    lines.append(
        f"RH HIGH-PnL BUYS · last {data.get('window_minutes', '?')}m · "
        f"mcap≤{fmt_usd(data.get('max_mcap'))}"
    )
    cards = data.get("cards") or []
    dropped = data.get("dropped_unsafe") or []
    lines.append(
        f"safe hits: {len(cards)} · dropped honeypot/unsafe: {data.get('dropped_unsafe_count', len(dropped))}"
    )

    # group by token
    by: dict[str, list] = {}
    for c in cards:
        by.setdefault(c.get("token") or "?", []).append(c)

    ranked = sorted(
        by.items(),
        key=lambda kv: -sum(float(e.get("amount_usd") or 0) for e in kv[1]),
    )[:max_n]

    if not ranked:
        lines.append("No safe hits this window.")
        if dropped:
            d0 = dropped[0]
            lines.append(
                f"Example dropped: ${d0.get('symbol')} honeypot/unsafe"
            )
            lines.append(str(d0.get("token")))
    else:
        for i, (tok, events) in enumerate(ranked, 1):
            e0 = events[0]
            story = e0.get("token_story") or {}
            sym = story.get("symbol") or e0.get("symbol")
            total = sum(float(e.get("amount_usd") or 0) for e in events)
            lines.append("")
            lines.append(f"{i}) ${sym} · buys ~{fmt_usd(total)}")
            lines.append(
                f"mcap {fmt_usd(story.get('mcap') or e0.get('mcap'))} · "
                f"{len(events)} wallet event(s)"
            )
            lines.append(str(tok))
            lines.append(f"https://gmgn.ai/robinhood/token/{tok}")

    lines.append("")
    lines.append("DYOR · not financial advice · RH only")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("json_path")
    ap.add_argument("--max", type=int, default=3)
    args = ap.parse_args()
    path = Path(args.json_path)
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        return 1
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("module") == "buy_the_dip" or "hits" in data and "min_drop_pct" in data:
        print(short_dip(data, args.max))
    elif "cards" in data:
        print(short_smart(data, args.max))
    else:
        print("Unknown JSON shape. Expected buy_the_dip or rh_smart_buys export.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
