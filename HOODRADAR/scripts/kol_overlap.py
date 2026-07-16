#!/usr/bin/env python3
"""Match hot token CAs against KOL watchlist using Blockscout token holders (RH chain).

Chain: Robinhood Chain mainnet 4663
Explorer API: https://robinhoodchain.blockscout.com/api

Usage:
  python3 kol_overlap.py --wallets ../references/kol_wallets.json \\
      --contracts 0xabc...,0xdef...
  python3 kol_overlap.py --wallets ... --heat-json extract_out.json --top 10

Notes:
- Placeholder/disabled wallets skipped.
- Holder pagination capped for speed.
- If API fails → report error per contract, never invent KOL hits.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://robinhoodchain.blockscout.com/api"
ZERO = "0x0000000000000000000000000000000000000000"


def http_get(url: str, timeout: int = 25) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "rh-meme-desk/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_holders(contract: str, max_pages: int = 3, offset: int = 50) -> list[str]:
    """Return lowercase holder addresses (best-effort)."""
    contract = contract.lower()
    holders: list[str] = []
    page = 1
    while page <= max_pages:
        q = urllib.parse.urlencode(
            {
                "module": "token",
                "action": "getTokenHolders",
                "contractaddress": contract,
                "page": page,
                "offset": offset,
            }
        )
        url = f"{API}?{q}"
        try:
            data = http_get(url)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            return {"error": str(e), "holders": []}  # type: ignore
        if str(data.get("status")) not in {"1", "1.0"} and not data.get("result"):
            # some blockscout variants
            if not data.get("result"):
                return {"error": data.get("message") or "no result", "holders": []}  # type: ignore
        result = data.get("result") or []
        if isinstance(result, dict):
            # unexpected shape
            break
        if not result:
            break
        for row in result:
            addr = (row.get("address") or row.get("addressHash") or "").lower()
            if addr.startswith("0x") and len(addr) == 42:
                holders.append(addr)
        if len(result) < offset:
            break
        page += 1
    return holders  # type: ignore


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wallets", required=True)
    ap.add_argument("--contracts", default="")
    ap.add_argument("--heat-json", help="extract_cas.py output; use top contracts")
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--max-pages", type=int, default=3)
    args = ap.parse_args()

    wdata = json.loads(Path(args.wallets).read_text(encoding="utf-8"))
    watch = []
    for w in wdata.get("wallets") or []:
        if w.get("enabled") is False:
            continue
        addr = (w.get("address") or "").lower()
        if not addr or addr == ZERO or len(addr) != 42:
            continue
        watch.append({"label": w.get("label") or addr[:10], "address": addr, "tier": w.get("tier")})

    contracts: list[str] = []
    if args.contracts:
        contracts = [c.strip().lower() for c in args.contracts.split(",") if c.strip()]
    if args.heat_json:
        heat = json.loads(Path(args.heat_json).read_text(encoding="utf-8"))
        ranked = list((heat.get("contracts") or {}).keys())[: args.top]
        for c in ranked:
            if c not in contracts:
                contracts.append(c)

    if not watch:
        print(
            json.dumps(
                {
                    "warning": "No enabled KOL wallets in watchlist. Edit references/kol_wallets.json",
                    "kol_tape": [],
                    "contracts_checked": contracts,
                },
                indent=2,
            )
        )
        return

    watch_set = {w["address"]: w for w in watch}
    tape = []
    for ca in contracts:
        holders = fetch_holders(ca, max_pages=args.max_pages)
        if isinstance(holders, dict) and "error" in holders:
            tape.append({"contract": ca, "error": holders["error"], "kol_hits": []})
            continue
        hits = []
        for h in holders:
            if h in watch_set:
                hits.append(
                    {
                        "label": watch_set[h]["label"],
                        "address": h,
                        "tier": watch_set[h].get("tier"),
                        "evidence": "token_holder_list_blockscout",
                    }
                )
        tape.append(
            {
                "contract": ca,
                "holders_scanned": len(holders) if isinstance(holders, list) else 0,
                "kol_hits": hits,
            }
        )

    print(json.dumps({"watchlist_size": len(watch), "kol_tape": tape}, indent=2))


if __name__ == "__main__":
    main()
