#!/usr/bin/env python3
"""HOODRADAR v2 local dashboard. Research only. Port 8787."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from threading import Lock

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "cron" / "cache"
WEB = ROOT / "web"
CONFIG = ROOT / "config"
PORT = 8787
ADDR_RE = re.compile(r"0x[a-fA-F0-9]{40}")
PET_RE = re.compile(r"\b(pet|dog|cat|meme|doge|shib|pepe|inu|kitten|puppy)\b", re.I)
_lock = Lock()
STATE = {
    "online": True,
    "updated_at": None,
    "research_only": True,
    "wallet": {"address": "", "balance_usd": 0, "pnl_usd": 0},
    "safe_tape": [],
    "new_pairs": [],
    "dips": [],
    "wallets": [],
    "x_watch": [],
    "cache_count": 0,
    "wallet_count": 0,
    "scan": {"dip": None, "wallets": None},
}

def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def fmt_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S UTC")

def persist_cache():
    CACHE.mkdir(parents=True, exist_ok=True)
    with _lock:
        STATE["updated_at"] = fmt_now()
        STATE["cache_count"] = len(list(CACHE.glob("*")))
        blob = json.dumps(STATE, indent=2)
    (CACHE / "state.json").write_text(blob, encoding="utf-8")

def seed():
    pons = load_json(CONFIG / "pons.json", {})
    xw = load_json(CONFIG / "x-watch.json", {"allowlist": []})
    with _lock:
        STATE["pons"] = pons
        STATE["x_watch"] = [{"handle": h, "status": "allow"} for h in xw.get("allowlist", [])]
        STATE["wallet_count"] = len(STATE["wallets"])
        STATE["updated_at"] = fmt_now()
    persist_cache()

def run_scan(kind):
    kind = (kind or "").lower().strip()
    if kind not in ("dip", "wallets"):
        return {"ok": False, "error": "kind must be dip or wallets"}
    now = fmt_now()
    with _lock:
        STATE["scan"][kind] = now
        if kind == "dip":
            STATE["dips"] = []
        STATE["updated_at"] = now
        STATE["wallet_count"] = len(STATE["wallets"])
    persist_cache()
    return {"ok": True, "kind": kind, "at": now}

def agent_reply(message):
    msg = (message or "").strip()
    if not msg:
        return {"reply": "Paste a 0x wallet, a 0x token, or ask: scan all pet coins on pons. Research only.", "results": []}
    addrs = ADDR_RE.findall(msg)
    pet = bool(PET_RE.search(msg)) or ("scan all pet" in msg.lower())
    results, parts = [], []
    if pet:
        keys = ("cat", "dog", "pet", "meme")
        pets = []
        for t in STATE.get("safe_tape", []) + STATE.get("new_pairs", []):
            blob = f"{t.get('sym','')} {t.get('name','')}".lower()
            if any(k in blob for k in keys):
                row = dict(t)
                row["kind"] = "token"
                row["note"] = "pet/meme tape (research only)"
                pets.append(row)
        results.extend(pets)
        cid = STATE.get("pons", {}).get("chainId", 4663)
        parts.append(f"Pet/meme scan on PONS (chain {cid}): {len(pets)} tape hits. Research only.")
    low = msg.lower()
    for addr in addrs:
        kind = "wallet" if ("wallet" in low or "eoa" in low) else "token"
        if kind == "wallet":
            results.append({"kind": "wallet", "address": addr, "note": "wallet lookup (research only)"})
            parts.append(f"Wallet {addr[:6]}…{addr[-4:]} — research snapshot, no tx.")
        else:
            results.append({"kind": "token", "sym": "?", "addr": addr, "note": "token lookup (research only)"})
            parts.append(f"Token {addr[:6]}…{addr[-4:]} on PONS tape. Research only.")
    if not parts:
        parts.append("No 0x address and no pet/meme keywords. Try a 40-hex address or 'scan all pet coins on pons'.")
    parts.append("HOODRADAR does not execute trades.")
    return {"reply": " ".join(parts), "results": results}

MIME = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8", ".js": "application/javascript; charset=utf-8", ".json": "application/json; charset=utf-8", ".svg": "image/svg+xml"}

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"[{fmt_now()}] {fmt % args}")
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
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception:
            return {}
    def _file(self, path):
        if not path.is_file():
            self.send_error(404)
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", MIME.get(path.suffix.lower(), "application/octet-stream"))
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/state":
            with _lock:
                snap = json.loads(json.dumps(STATE))
            snap["updated_at"] = snap.get("updated_at") or fmt_now()
            return self._json(200, snap)
        if path in ("/", "/index.html"):
            return self._file(WEB / "index.html")
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
    def do_POST(self):
        path = urlparse(self.path).path
        payload = self._read_json()
        if path == "/api/scan":
            return self._json(200, run_scan(str(payload.get("kind") or "")))
        if path == "/api/agent":
            return self._json(200, agent_reply(str(payload.get("message") or "")))
        self.send_error(404)

def main():
    seed()
    print(f"HOODRADAR v2 http://127.0.0.1:{PORT}/  ROOT={ROOT}")
    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.shutdown()

if __name__ == "__main__":
    main()
