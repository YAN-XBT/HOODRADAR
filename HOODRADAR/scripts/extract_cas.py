#!/usr/bin/env python3
"""RH Meme Desk — extract CAs and $tickers from text / xurl JSON.

Usage:
  python3 extract_cas.py --text "..."
  python3 extract_cas.py --json-file posts.json
  cat posts.json | python3 extract_cas.py --stdin-json

Outputs JSON: { contracts: {addr: count}, tickers: {TICKER: count}, pairs: [...] }
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from typing import Any

CA_RE = re.compile(r"\b0x[a-fA-F0-9]{40}\b")
TICKER_RE = re.compile(r"\$([A-Za-z][A-Za-z0-9]{1,15})\b")


def normalize_ca(addr: str) -> str:
    return addr.lower()


def extract_from_text(text: str) -> tuple[list[str], list[str]]:
    cas = [normalize_ca(m.group(0)) for m in CA_RE.finditer(text or "")]
    tickers = [m.group(1).upper() for m in TICKER_RE.finditer(text or "")]
    return cas, tickers


def texts_from_xurl_payload(payload: Any) -> list[str]:
    texts: list[str] = []
    if isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and item.get("text"):
                    texts.append(str(item["text"]))
        elif isinstance(data, dict) and data.get("text"):
            texts.append(str(data["text"]))
        if "text" in payload and isinstance(payload["text"], str):
            texts.append(payload["text"])
    elif isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict) and item.get("text"):
                texts.append(str(item["text"]))
            elif isinstance(item, str):
                texts.append(item)
    return texts


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", default="")
    ap.add_argument("--json-file")
    ap.add_argument("--stdin-json", action="store_true")
    args = ap.parse_args()

    texts: list[str] = []
    if args.text:
        texts.append(args.text)
    if args.json_file:
        with open(args.json_file, encoding="utf-8") as f:
            texts.extend(texts_from_xurl_payload(json.load(f)))
    if args.stdin_json:
        texts.extend(texts_from_xurl_payload(json.load(sys.stdin)))

    ca_counts: Counter[str] = Counter()
    ticker_counts: Counter[str] = Counter()
    ticker_to_cas: dict[str, Counter[str]] = defaultdict(Counter)

    for t in texts:
        cas, tickers = extract_from_text(t)
        ca_counts.update(cas)
        ticker_counts.update(tickers)
        # co-occurrence: any CA in same post with any ticker
        for tick in set(tickers):
            for ca in set(cas):
                ticker_to_cas[tick][ca] += 1

    out = {
        "post_count": len(texts),
        "contracts": dict(ca_counts.most_common()),
        "tickers": dict(ticker_counts.most_common()),
        "ticker_to_contracts": {
            k: dict(v.most_common()) for k, v in ticker_to_cas.items()
        },
    }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
