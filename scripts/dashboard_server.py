#!/usr/bin/env python3
"""HOODRADAR v2 local dashboard. Research only. Port 8787."""
from __future__ import annotations

import json
import re
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "cron" / "cache"
WEB = ROOT / "web"
CONFIG = ROOT / "config"
PORT = 8787

ADDR_RE = re.compile(r"0x[a-fA-F0-9]{40}")
PET_RE = re.compile(r"\b(pet|dog|cat|meme|doge|shib|pepe|inu|kitten|puppy)\b", re.I)

_lock = threading.Lock()
STATE = {
    "online": True,
    "updated_at": None,
    "research_only": True,
    "wallet": {
        "address": "",
        "balance_usd": 0,
        "pnl_usd": 0,
    },
    "safe_tape": [],
    "new_pairs": [],
    "dips": [],
    "wallets": [],
    "x_watch": [],
    "cache_count": 0,
    "wallet_count": 0,
    "scan": {"dip": None, "wallets": None},
}


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def fmt_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S UTC")


def persist_cache():
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / "state.json"
    with _lock:
        STATE["updated_at"] = fmt_now()
        STATE["cache_count"] = len(list(CACHE.glob("*")))
        blob = json.dumps(STATE, indent=2)
    path.write_text(blob, encoding="utf-8")
    with _lock:
        STATE["cache_count"] = len(list(CACHE.glob("*")))


def seed():
    pons = load_json(CONFIG / "pons.json", {})
    xw = load_json(CONFIG / "x-watch.json", {"allowlist": []})
    with _lock:
        STATE["pons"] = pons
        STATE["x_watch"] = [{"handle": h, "status": "allow"} for h in xw.get("allowlist", [])]
        STATE["wallet_count"] = len(STATE["wallets"])
        STATE["updated_at"] = fmt_now()
    persist_cache()


def run_scan(kind: str) -> dict:
    kind = (kind or "").lower().strip()
    if kind not in ("dip", "wallets"):
        return {"ok": False, "error": "kind must be dip or wallets"}
    now = fmt_now()
    with _lock:
        if kind == "wallets":
            STATE["scan"]["wallets"] = now
            STATE["wallet_count"] = len(STATE["wallets"])
        elif kind == "dip":
            STATE["scan"]["dip"] = now
            # empty dip tape is the intended empty-state
            STATE["dips"] = []
        STATE["updated_at"] = now
    persist_cache()
    return {
        "ok": True,
        "kind": kind,
        "at": now,
        "queued": True,
        "message": "scan queued (indexer not live yet)",
    }


def classify_addr(message: str, addr: str) -> str:
    low = message.lower()
    if "wallet" in low or "eoa" in low:
        return "wallet"
    if any(k in low for k in ("token", "pair", "contract", "ca", "coin")):
        return "token"
    # heuristic: factory-ish / known tape tokens vs primary wallet
    tape = {t["addr"].lower() for t in STATE.get("safe_tape", [])}
    if addr.lower() in tape:
        return "token"
    if addr.lower() == STATE.get("wallet", {}).get("address", "").lower():
        return "wallet"
    return "token"


def pet_tokens():
    keys = ("cat", "dog", "pet", "meme", "cashcat", "r0b")
    out = []
    for t in STATE.get("safe_tape", []) + STATE.get("new_pairs", []):
        blob = f"{t.get('sym','')} {t.get('name','')}".lower()
        if any(k in blob for k in keys) or t.get("sym", "").upper() in ("CASHCAT", "R0B"):
            item = dict(t)
            item["kind"] = "token"
            item["note"] = "pet/meme tape (research only)"
            out.append(item)
    # dedupe by addr
    seen = set()
    uniq = []
    for x in out:
        a = x.get("addr", "").lower()
        if a in seen:
            continue
        seen.add(a)
        uniq.append(x)
    return uniq


def agent_reply(message: str) -> dict:
    msg = (message or "").strip()
    if not msg:
        return {
            "reply": "Paste a 0x wallet, a 0x token, or ask: scan all pet coins on pons. Research only.",
            "results": [],
        }
    addrs = ADDR_RE.findall(msg)
    pet = bool(PET_RE.search(msg)) or ("scan all pet" in msg.lower())
    results = []
    parts = []

    if pet:
        pets = pet_tokens()
        results.extend(pets)
        parts.append(
            f"Pet/meme scan on PONS (chain {STATE.get('pons', {}).get('chainId', 4663)}): "
            f"{len(pets)} tape hits. Research only — no trades."
        )

    for addr in addrs:
        kind = classify_addr(msg, addr)
        hit = None
        for t in STATE.get("safe_tape", []) + STATE.get("new_pairs", []):
            if t.get("addr", "").lower() == addr.lower():
                hit = dict(t)
                break
        if kind == "wallet":
            w = None
            for ww in STATE.get("wallets", []):
                if ww.get("address", "").lower() == addr.lower():
                    w = dict(ww)
                    break
            row = w or {"address": addr, "label": "unknown", "usd": None, "pnl": None}
            row["kind"] = "wallet"
            row["note"] = "wallet lookup (research only)"
            results.append(row)
            parts.append(f"Wallet {addr[:6]}…{addr[-4:]} — research snapshot, no tx.")
        else:
            row = hit or {"sym": "?", "name": "unknown token", "addr": addr, "mc": None, "vol": None, "chg": None}
            row["kind"] = "token"
            row["note"] = "token lookup (research only)"
            results.append(row)
            parts.append(f"Token {addr[:6]}…{addr[-4:]} on PONS tape. Research only.")

    if not parts:
        parts.append(
            "No 0x address and no pet/meme keywords. Try a 40-hex address or 'scan all pet coins on pons'."
        )

    parts.append("HOODRADAR does not execute trades.")
    return {"reply": " ".join(parts), "results": results}


MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
    ".woff2": "font/woff2",
}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"[{fmt_now()}] {self.address_string()} {fmt % args}")

    def _json(self, code, obj):
        raw = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _read_json(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0:
            return {}
        body = self.rfile.read(n)
        try:
            return json.loads(body.decode("utf-8"))
        except Exception:
            return {}

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/state":
            with _lock:
                snap = json.loads(json.dumps(STATE))
            snap["updated_at"] = snap.get("updated_at") or fmt_now()
            return self._json(200, snap)
        if path in ("/", "/index.html"):
            return self._file(WEB / "index.html")
        # static under web/
        rel = path.lstrip("/")
        if ".." in rel:
            self.send_error(403)
            return
        target = (WEB / rel).resolve()
        try:
            target.relative_to(WEB.resolve())
        except ValueError:
            self.send_error(403)
            return
        if target.is_file():
            return self._file(target)
        self.send_error(404)

    def _file(self, path: Path):
        if not path.is_file():
            self.send_error(404)
            return
        data = path.read_bytes()
        ctype = MIME.get(path.suffix.lower(), "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        payload = self._read_json()
        if path == "/api/scan":
            kind = payload.get("kind") or payload.get("kinds") or ""
            return self._json(200, run_scan(str(kind)))
        if path == "/api/agent":
            msg = payload.get("message") or payload.get("q") or ""
            out = agent_reply(str(msg))
            return self._json(200, out)
        self.send_error(404)


def main():
    seed()
    spark = WEB / "spark.svg"
    logo = WEB / "logo.svg"
    print(f"HOODRADAR v2  ROOT={ROOT}")
    print(f"  WEB={WEB}  CACHE={CACHE}")
    print(f"  logo={logo.is_file()} spark={spark.is_file()}")
    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"  http://127.0.0.1:{PORT}/")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.shutdown()


if __name__ == "__main__":
    main()
