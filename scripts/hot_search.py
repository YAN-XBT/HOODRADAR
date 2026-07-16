#!/usr/bin/env python3
"""GMGN Hot Search ranking for Robinhood Chain → cache + brief."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def gmgn_bin() -> str:
    local = ROOT / "tools" / "node_modules" / ".bin" / "gmgn-cli"
    if local.is_file():
        return str(local)
    return "gmgn-cli"


def run_hot(chain: str, interval: str, limit: int) -> list:
    cmd = [
        gmgn_bin(),
        "market",
        "hot-searches",
        "--chain",
        chain,
        "--interval",
        interval,
        "--limit",
        str(limit),
        "--raw",
    ]
    env = os.environ.copy()
    tools = ROOT / "tools" / "node_modules" / ".bin"
    env["PATH"] = f"{tools}:{env.get('PATH', '')}"
    r = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=120)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout or "gmgn hot-searches failed")[:800])
    data = json.loads(r.stdout)
    # shape: [{chain, interval, tokens:[...]}]
    if isinstance(data, list) and data:
        tokens = data[0].get("tokens") or []
        return tokens
    if isinstance(data, dict):
        return data.get("tokens") or []
    return []


def brief_text(tokens: list, interval: str, chain: str) -> str:
    lines = [
        f"HOT SEARCH · {chain.upper()} · interval {interval}",
        f"Time: {datetime.now(timezone.utc).isoformat()}",
        f"Source: gmgn-cli market hot-searches (same family as gmgn.ai/trend?tab=hotsearch)",
        f"Count: {len(tokens)}",
        "",
    ]
    for i, t in enumerate(tokens[:50], 1):
        sym = t.get("symbol") or "?"
        name = t.get("name") or ""
        ca = t.get("address") or ""
        rank = t.get("rank") or i
        mcap = t.get("market_cap")
        ch = t.get("price_change_percent")
        vol = t.get("volume")
        visit = t.get("visiting_count")
        hot = t.get("hot_level")
        lines.append(f"#{rank}  ${sym}  —  {name}")
        lines.append(
            f"  mcap {mcap} · chg {ch}% · vol {vol} · visits {visit} · hot_level {hot}"
        )
        lines.append(f"  CA: {ca}")
        lines.append(f"  https://gmgn.ai/robinhood/token/{ca}")
        lines.append("")
    lines.append("DYOR. Not financial advice. Research only. ROBINHOOD CHAIN ONLY.")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="RH GMGN hot-search ranking")
    ap.add_argument("--chain", default="robinhood")
    ap.add_argument("--interval", default="24h", choices=["1m", "5m", "1h", "6h", "24h"])
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--json-out", default=str(ROOT / "cron" / "cache" / "hot_search.json"))
    ap.add_argument(
        "--brief-out", default=str(ROOT / "cron" / "cache" / "hot_search_brief.txt")
    )
    args = ap.parse_args()

    if args.chain != "robinhood":
        print("WARN: product chain lock is robinhood", file=sys.stderr)

    tokens = run_hot(args.chain, args.interval, args.limit)
    brief = brief_text(tokens, args.interval, args.chain)
    out = {
        "ok": True,
        "module": "hot_search",
        "chain": args.chain,
        "interval": args.interval,
        "limit": args.limit,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "gmgn market hot-searches",
        "gmgn_ui": f"https://gmgn.ai/trend?chain={args.chain}&tab=hotsearch",
        "count": len(tokens),
        "tokens": tokens,
        "brief": brief,
    }
    Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.json_out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    Path(args.brief_out).write_text(brief, encoding="utf-8")
    print(brief)
    print(f"\n--- JSON_OK ---\nwrote {args.json_out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
