#!/usr/bin/env python3
"""BUY THE DIP — Robinhood Chain only.

Source: GMGN trending (same list as https://gmgn.ai/trend?chain=robinhood)
Logic:
  1) Take top N trending tokens (default 10)
  2) Keep only LARGE ones (min market cap + min liquidity)
  3) Keep only if price drop is <= -min_drop_pct (default -20%, mandatory floor 20)
  4) Drop honeypots / GMGN Unsafe alerts
  5) Emit human Telegram brief + JSON

Usage:
  export PATH=.../rh-meme-desk/tools/node_modules/.bin:$PATH
  python3 scripts/buy_the_dip.py
  python3 scripts/buy_the_dip.py --interval 1h --min-drop 20 --min-mcap 50000 --min-liq 15000
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
CHAIN = "robinhood"
MIN_DROP_FLOOR = 20.0  # hard product rule: never alert below 20% dump


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
    if not out:
        return {"error": (r.stderr or "empty")[:400], "code": r.returncode}
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return {"error": "not_json", "raw": out[:400]}


def fmt_usd(x: Any) -> str:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return "n/a"
    if abs(v) >= 1_000_000:
        return f"${v/1_000_000:.2f}M"
    if abs(v) >= 1_000:
        return f"${v/1_000:.1f}k"
    return f"${v:.0f}"


def fmt_pct(x: Any) -> str:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return "n/a"
    sign = "+" if v > 0 else ""
    return f"{sign}{v:.1f}%"


def parse_rank(payload: Any) -> list[dict]:
    if not isinstance(payload, dict) or payload.get("error"):
        return []
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    rank = data.get("rank") if isinstance(data, dict) else None
    if isinstance(rank, list):
        return [x for x in rank if isinstance(x, dict)]
    return []


def drop_field_for_interval(t: dict, interval: str) -> float | None:
    """Return signed price change % for the selected interval (negative = dump)."""
    mapping = {
        "1m": "price_change_percent1m",
        "5m": "price_change_percent5m",
        "1h": "price_change_percent1h",
        "6h": "price_change_percent",  # often window field
        "24h": "price_change_percent",
    }
    # Prefer interval-specific, then generic
    keys = [mapping.get(interval, "price_change_percent"), "price_change_percent"]
    if interval == "1h":
        keys = ["price_change_percent1h", "price_change_percent"]
    elif interval == "5m":
        keys = ["price_change_percent5m", "price_change_percent"]
    elif interval == "1m":
        keys = ["price_change_percent1m", "price_change_percent"]
    elif interval == "24h":
        keys = ["price_change_percent", "price_change_percent1h"]
    for k in keys:
        if t.get(k) is not None:
            try:
                return float(t[k])
            except (TypeError, ValueError):
                continue
    return None


def is_hard_unsafe(t: dict) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if t.get("is_honeypot") in (True, 1, "1", "true"):
        reasons.append("HONEYPOT")
    if t.get("is_show_alert") is True:
        reasons.append("GMGN Unsafe alert")
    try:
        if float(t.get("sell_tax") or 0) >= 50:
            reasons.append(f"sell_tax={t.get('sell_tax')}")
    except (TypeError, ValueError):
        pass
    return (bool(reasons), reasons)


def security_extra(addr: str) -> dict[str, Any]:
    raw = gmgn_cmd("token", "security", "--chain", CHAIN, "--address", addr)
    if not isinstance(raw, dict) or raw.get("error"):
        return {"ok": False, "unsafe": False, "reasons": ["security n/a"]}
    d = raw.get("data") if isinstance(raw.get("data"), dict) else raw
    reasons: list[str] = []
    if d.get("is_honeypot") is True or d.get("honeypot") in (1, "1", True):
        reasons.append("HONEYPOT (security API)")
    if d.get("is_show_alert") is True:
        reasons.append("Unsafe alert (security API)")
    return {
        "ok": True,
        "unsafe": bool(reasons),
        "reasons": reasons,
        "is_honeypot": d.get("is_honeypot"),
        "is_show_alert": d.get("is_show_alert"),
    }


def render_brief(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("══════════════════════════════════════")
    lines.append("BUY THE DIP · ROBINHOOD CHAIN")
    lines.append(f"GMGN trending top {payload['top_n']} · interval {payload['interval']}")
    lines.append(
        f"Rules: drop ≤ -{payload['min_drop_pct']:g}% (mandatory ≥20) · "
        f"mcap ≥ {fmt_usd(payload['min_mcap'])} · liq ≥ {fmt_usd(payload['min_liq'])}"
    )
    lines.append(f"Time: {payload['generated_at']}")
    lines.append("══════════════════════════════════════")
    lines.append("")
    lines.append(
        f"Top {payload['top_n']} scanned: {payload['scanned']} · "
        f"large enough: {payload['large_count']} · "
        f"dip hits: {len(payload.get('hits') or [])} · "
        f"dropped unsafe: {payload.get('dropped_unsafe_count', 0)}"
    )
    lines.append("")

    hits = payload.get("hits") or []
    if not hits:
        lines.append("No BUY-THE-DIP setups right now.")
        lines.append(
            "None of the top trending LARGE tokens dumped ≥"
            f"{payload['min_drop_pct']:g}% on {payload['interval']}."
        )
        # show near-misses for transparency
        near = payload.get("near_misses") or []
        if near:
            lines.append("")
            lines.append("Near misses (top large tokens, drop not deep enough or still green):")
            for t in near[:5]:
                lines.append(
                    f"  · ${t.get('symbol')}  {fmt_pct(t.get('drop_pct'))}  "
                    f"mcap {fmt_usd(t.get('market_cap'))} liq {fmt_usd(t.get('liquidity'))}"
                )
                lines.append(f"    CA: {t.get('address')}")
    else:
        for i, t in enumerate(hits, 1):
            lines.append("──────────────────────────────────────")
            lines.append(f"#{i}  ${t.get('symbol')}  —  {t.get('name') or ''}".rstrip())
            lines.append(f"DUMP: {fmt_pct(t.get('drop_pct'))} over {payload['interval']}")
            lines.append(
                f"Mcap {fmt_usd(t.get('market_cap'))} · Liq {fmt_usd(t.get('liquidity'))} · "
                f"Holders {t.get('holder_count')} · Vol {fmt_usd(t.get('volume'))}"
            )
            lines.append(
                f"ATH mcap {fmt_usd(t.get('history_highest_market_cap'))} · "
                f"rank #{t.get('rank')} on RH trending"
            )
            lines.append("")
            lines.append("WHY IT QUALIFIES:")
            lines.append(f"  • In GMGN RH top {payload['top_n']} trending")
            lines.append(
                f"  • Large: mcap ≥ {fmt_usd(payload['min_mcap'])}, "
                f"liq ≥ {fmt_usd(payload['min_liq'])}"
            )
            lines.append(
                f"  • Price drop {fmt_pct(t.get('drop_pct'))} "
                f"(rule: ≤ -{payload['min_drop_pct']:g}%)"
            )
            if t.get("renowned_count"):
                lines.append(f"  • Renowned/KOL wallets: {t.get('renowned_count')}")
            if t.get("smart_degen_count"):
                lines.append(f"  • Smart money holders: {t.get('smart_degen_count')}")
            lines.append("")
            lines.append("CA (full, copy this):")
            lines.append(str(t.get("address")))
            lines.append("")
            lines.append("LINKS:")
            lines.append(f"  Trend:  https://gmgn.ai/trend?chain=robinhood")
            lines.append(f"  Token:  https://gmgn.ai/robinhood/token/{t.get('address')}")
            lines.append(
                f"  Explorer: https://robinhoodchain.blockscout.com/token/{t.get('address')}"
            )
            if t.get("twitter_username"):
                tw = t["twitter_username"]
                if not str(tw).startswith("http"):
                    tw = f"https://x.com/{str(tw).lstrip('@')}"
                lines.append(f"  Twitter: {tw}")
            if t.get("website"):
                lines.append(f"  Web: {t['website']}")
            lines.append("")

    dropped = payload.get("dropped_unsafe") or []
    if dropped:
        lines.append("──────────────────────────────────────")
        lines.append("⛔ Skipped unsafe (would have matched size/drop):")
        for d in dropped[:8]:
            lines.append(f"  · ${d.get('symbol')}  {', '.join(d.get('reasons') or [])}")
            lines.append(f"    CA: {d.get('address')}")
        lines.append("")

    lines.append("──────────────────────────────────────")
    lines.append("DYOR. Not financial advice. Research only. ROBINHOOD CHAIN ONLY.")
    lines.append("Source: GMGN trending · security flags applied.")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="BUY THE DIP · Robinhood only")
    ap.add_argument("--top", type=int, default=10, help="first N trending tokens")
    ap.add_argument(
        "--interval",
        default="1h",
        choices=["1m", "5m", "1h", "6h", "24h"],
        help="GMGN trending interval + drop window",
    )
    ap.add_argument(
        "--min-drop",
        type=float,
        default=20.0,
        help="minimum dump magnitude in %% (must be >= 20)",
    )
    ap.add_argument("--min-mcap", type=float, default=50_000, help="min market cap USD (large token)")
    ap.add_argument("--min-liq", type=float, default=15_000, help="min liquidity USD")
    ap.add_argument("--min-holders", type=int, default=0)
    ap.add_argument("--skip-security-api", action="store_true", help="only use fields on trending row")
    ap.add_argument("--json-out", default="")
    ap.add_argument("--brief-out", default="")
    ap.add_argument(
        "--quiet-if-empty",
        action="store_true",
        help="print nothing if no hits (for silent cron ticks)",
    )
    args = ap.parse_args()

    min_drop = max(float(args.min_drop), MIN_DROP_FLOOR)
    if args.min_drop < MIN_DROP_FLOOR:
        # still enforce floor
        pass

    payload_raw = gmgn_cmd(
        "market",
        "trending",
        "--chain",
        CHAIN,
        "--interval",
        args.interval,
        "--limit",
        str(max(args.top, 10)),
    )
    rank = parse_rank(payload_raw)[: args.top]

    hits: list[dict] = []
    near: list[dict] = []
    dropped_unsafe: list[dict] = []
    large_count = 0

    for t in rank:
        addr = (t.get("address") or "").lower()
        if not addr:
            continue
        try:
            mcap = float(t.get("market_cap") or 0)
            liq = float(t.get("liquidity") or 0)
        except (TypeError, ValueError):
            mcap, liq = 0.0, 0.0
        holders = int(t.get("holder_count") or 0)
        drop = drop_field_for_interval(t, args.interval)

        row = {
            "address": addr,
            "symbol": t.get("symbol"),
            "name": t.get("name"),
            "market_cap": mcap,
            "liquidity": liq,
            "volume": t.get("volume"),
            "holder_count": holders,
            "history_highest_market_cap": t.get("history_highest_market_cap"),
            "rank": t.get("rank"),
            "drop_pct": drop,
            "price": t.get("price"),
            "renowned_count": t.get("renowned_count"),
            "smart_degen_count": t.get("smart_degen_count"),
            "twitter_username": t.get("twitter_username"),
            "website": t.get("website"),
            "telegram": t.get("telegram"),
            "is_honeypot": t.get("is_honeypot"),
            "is_show_alert": t.get("is_show_alert"),
        }

        large = (
            mcap >= args.min_mcap
            and liq >= args.min_liq
            and (args.min_holders <= 0 or holders >= args.min_holders)
        )
        if large:
            large_count += 1

        # hard dump rule: change <= -min_drop
        is_dip = drop is not None and drop <= -min_drop

        if not large:
            continue
        if not is_dip:
            near.append(row)
            continue

        unsafe, reasons = is_hard_unsafe(t)
        if not args.skip_security_api:
            extra = security_extra(addr)
            time.sleep(0.2)
            if extra.get("unsafe"):
                unsafe = True
                reasons = list(dict.fromkeys(reasons + list(extra.get("reasons") or [])))

        if unsafe:
            dropped_unsafe.append({**row, "reasons": reasons})
            continue

        hits.append(row)

    # sort deepest dumps first
    hits.sort(key=lambda x: (x.get("drop_pct") if x.get("drop_pct") is not None else 0))
    near.sort(key=lambda x: (x.get("drop_pct") if x.get("drop_pct") is not None else 999))

    payload = {
        "ok": True,
        "module": "buy_the_dip",
        "chain": CHAIN,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "https://gmgn.ai/trend?chain=robinhood",
        "interval": args.interval,
        "top_n": args.top,
        "min_drop_pct": min_drop,
        "min_mcap": args.min_mcap,
        "min_liq": args.min_liq,
        "scanned": len(rank),
        "large_count": large_count,
        "hits": hits,
        "near_misses": near,
        "dropped_unsafe": dropped_unsafe,
        "dropped_unsafe_count": len(dropped_unsafe),
        "trending_error": payload_raw.get("error") if isinstance(payload_raw, dict) else None,
    }
    brief = render_brief(payload)
    payload["brief"] = brief

    cache = ROOT / "cron" / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    json_out = args.json_out or str(cache / "buy_the_dip.json")
    brief_out = args.brief_out or str(cache / "buy_the_dip_brief.txt")
    Path(json_out).write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    Path(brief_out).write_text(brief, encoding="utf-8")

    if args.quiet_if_empty and not hits:
        return 0
    print(brief)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
