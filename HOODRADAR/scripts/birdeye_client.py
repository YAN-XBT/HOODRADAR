#!/usr/bin/env python3
"""Minimal Birdeye HTTP client.

Auth: X-API-KEY
Chain: x-chain header (robinhood supported for PnL / many endpoints)

Key resolution order:
  1) --api-key CLI
  2) BIRDEYE_API_KEY env
  3) profile .env BIRDEYE_API_KEY=
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

BASE = "https://public-api.birdeye.so"


_KEY_NAMES = ("BIRDEYE_API_KEY", "BIRDEYE", "BIRDEYE_KEY", "BDS_API_KEY")


def load_api_key(cli_key: str | None = None, env_file: str | None = None) -> str:
    if cli_key:
        return cli_key.strip()
    for name in _KEY_NAMES:
        if os.environ.get(name):
            return os.environ[name].strip()
    paths = []
    if env_file:
        paths.append(Path(env_file))
    paths.extend(
        [
            Path(__file__).resolve().parents[1] / ".env",
            Path.cwd() / ".env",
        ]
    )
    for p in paths:
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() in _KEY_NAMES:
                return v.strip().strip('"').strip("'")
    raise SystemExit(
        "Missing BIRDEYE / BIRDEYE_API_KEY. Get one at https://bds.birdeye.so/ and set:\n"
        "  BIRDEYE=...  or  BIRDEYE_API_KEY=... in rh-meme-desk/.env"
    )


def request(
    path: str,
    *,
    api_key: str,
    chain: str = "robinhood",
    params: dict[str, Any] | None = None,
    timeout: int = 40,
) -> dict[str, Any]:
    q = urllib.parse.urlencode({k: v for k, v in (params or {}).items() if v is not None})
    url = f"{BASE}{path}"
    if q:
        url = f"{url}?{q}"
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "X-API-KEY": api_key,
            "x-chain": chain,
            "User-Agent": "rh-smart-wallet-tracker/0.1",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(err_body)
        except json.JSONDecodeError:
            parsed = {"raw": err_body[:500]}
        return {"success": False, "http_status": e.code, "error": parsed, "path": path}
    except urllib.error.URLError as e:
        return {"success": False, "error": str(e), "path": path}
