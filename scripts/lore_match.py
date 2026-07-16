#!/usr/bin/env python3
"""Match lore seeds against post texts; frequency board.

Usage:
  python3 lore_match.py --seeds ../references/lore_seeds.json --json-file posts.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path


def load_texts(path: str | None, stdin_json: bool) -> list[str]:
    texts: list[str] = []
    payload = None
    if path:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    elif stdin_json:
        payload = json.load(sys.stdin)
    else:
        return texts
    data = payload.get("data") if isinstance(payload, dict) else payload
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and item.get("text"):
                texts.append(str(item["text"]))
    return texts


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", required=True)
    ap.add_argument("--json-file")
    ap.add_argument("--stdin-json", action="store_true")
    args = ap.parse_args()

    seeds = json.loads(Path(args.seeds).read_text(encoding="utf-8"))["seeds"]
    texts = load_texts(args.json_file, args.stdin_json)

    hits = []
    for seed in seeds:
        aliases = seed.get("aliases") or []
        patterns = [re.compile(re.escape(a), re.I) for a in aliases]
        matched_posts = 0
        samples: list[str] = []
        for t in texts:
            if any(p.search(t) for p in patterns):
                matched_posts += 1
                if len(samples) < 3:
                    samples.append(t[:240].replace("\n", " "))
        if matched_posts:
            hits.append(
                {
                    "id": seed.get("id"),
                    "claim": seed.get("claim"),
                    "priority": seed.get("priority", 0),
                    "mentions": matched_posts,
                    "score": matched_posts * 2 + int(seed.get("priority", 0)),
                    "samples": samples,
                    "label": "community_claim",
                }
            )

    hits.sort(key=lambda x: (-x["score"], -x["mentions"]))
    print(json.dumps({"post_count": len(texts), "lore_board": hits}, indent=2))


if __name__ == "__main__":
    main()
