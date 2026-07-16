#!/usr/bin/env python3
"""
HOODRADAR local web desk — research only.
Serves a dark UI on localhost and JSON from cron/cache + live optional.

  python3 scripts/dashboard_server.py
  open http://127.0.0.1:8787

No trading. No secrets in responses (does not dump .env).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse, unquote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "cron" / "cache"
WEB = ROOT / "web"
LOGO_DIR = CACHE / "logos"
PORT = int(os.environ.get("HOODRADAR_PORT", "8787"))
HOST = os.environ.get("HOODRADAR_HOST", "127.0.0.1")


def _read_json(name: str):
    p = CACHE / name
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        return {"error": str(e), "path": str(p)}


def _read_text(name: str) -> str:
    p = CACHE / name
    if not p.is_file():
        return ""
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        return ""


def _list_cache():
    if not CACHE.is_dir():
        return []
    out = []
    for p in sorted(CACHE.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if p.is_file():
            out.append(
                {
                    "name": p.name,
                    "bytes": p.stat().st_size,
                    "mtime": datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).isoformat(),
                }
            )
    return out


def _api_state():
    wallets = _read_json("wallets_top20.json")
    return {
        "ok": True,
        "product": "hoodradar",
        "mode": "research_only",
        "root": str(ROOT),
        "time": datetime.now(timezone.utc).isoformat(),
        "cache": _list_cache(),
        "buy_the_dip": _read_json("buy_the_dip.json") or _read_json("buy_the_dip_24h.json"),
        "buy_the_dip_1h": _read_json("buy_the_dip.json"),
        "buy_the_dip_24h": _read_json("buy_the_dip_24h.json"),
        "smart_buys": _read_json("rh_smart_buys.json"),
        "wallets": wallets,
        "hot_search": _read_json("hot_search.json"),
        "briefs": {
            "buy_the_dip": _read_text("buy_the_dip_brief.txt")
            or _read_text("buy_the_dip_24h_brief.txt"),
            "buy_the_dip_1h": _read_text("buy_the_dip_brief.txt"),
            "buy_the_dip_24h": _read_text("buy_the_dip_24h_brief.txt"),
            "smart_buys": _read_text("rh_smart_buys_brief.txt"),
            "wallets": _read_text("wallets_top20_brief.txt")
            or ((wallets or {}).get("brief") if isinstance(wallets, dict) else "")
            or "",
            "hot_search": _read_text("hot_search_brief.txt"),
        },
    }


def _run_scan(kind: str) -> dict:
    """Optional on-demand scan (may take 1–3 min)."""
    env = os.environ.copy()
    tools_bin = ROOT / "tools" / "node_modules" / ".bin"
    env["PATH"] = f"{tools_bin}:{env.get('PATH', '')}"
    env["RH_DESK_ROOT"] = str(ROOT)
    CACHE.mkdir(parents=True, exist_ok=True)

    py = sys.executable
    cmds = []
    if kind in ("dip", "all"):
        cmds.append(
            [
                py,
                str(ROOT / "scripts" / "buy_the_dip.py"),
                "--interval",
                "1h",
                "--top",
                "10",
                "--min-drop",
                "20",
                "--json-out",
                str(CACHE / "buy_the_dip.json"),
                "--brief-out",
                str(CACHE / "buy_the_dip_brief.txt"),
            ]
        )
        cmds.append(
            [
                py,
                str(ROOT / "scripts" / "buy_the_dip.py"),
                "--interval",
                "24h",
                "--top",
                "10",
                "--min-drop",
                "20",
                "--json-out",
                str(CACHE / "buy_the_dip_24h.json"),
                "--brief-out",
                str(CACHE / "buy_the_dip_24h_brief.txt"),
            ]
        )
    if kind in ("smart", "all"):
        cmds.append(
            [
                py,
                str(ROOT / "scripts" / "rh_smart_buys.py"),
                "--minutes",
                "180",
                "--max-mcap",
                "1000000",
                "--top",
                "15",
                "--json-out",
                str(CACHE / "rh_smart_buys.json"),
                "--brief-out",
                str(CACHE / "rh_smart_buys_brief.txt"),
            ]
        )
    if kind in ("wallets", "all"):
        cmds.append(
            [
                py,
                str(ROOT / "scripts" / "smart_wallet_tracker.py"),
                "--chain",
                "robinhood",
                "--window",
                "1W",
                "--top",
                "20",
                "--json-out",
                str(CACHE / "wallets_top20.json"),
                "--brief-out",
                str(CACHE / "wallets_top20_brief.txt"),
            ]
        )
    if kind in ("hot", "hotsearch", "hot_search", "all"):
        cmds.append(
            [
                py,
                str(ROOT / "scripts" / "hot_search.py"),
                "--chain",
                "robinhood",
                "--interval",
                "24h",
                "--limit",
                "30",
                "--json-out",
                str(CACHE / "hot_search.json"),
                "--brief-out",
                str(CACHE / "hot_search_brief.txt"),
            ]
        )
    if not cmds:
        return {"ok": False, "error": "unknown kind (dip|smart|wallets|hot|all)"}

    logs = []
    for cmd in cmds:
        try:
            r = subprocess.run(
                cmd,
                cwd=str(ROOT),
                env=env,
                capture_output=True,
                text=True,
                timeout=300,
            )
            logs.append(
                {
                    "cmd": " ".join(cmd[-8:]),
                    "code": r.returncode,
                    "stdout_tail": (r.stdout or "")[-2000:],
                    "stderr_tail": (r.stderr or "")[-500:],
                }
            )
        except Exception as e:
            logs.append({"cmd": str(cmd), "error": str(e)})
    return {"ok": True, "kind": kind, "logs": logs, "state": _api_state()}


def _fetch_logo(url: str) -> tuple[bytes, str] | tuple[None, str]:
    """Proxy GMGN logos (direct browser load often hits Cloudflare 403)."""
    if not url or not url.startswith("https://"):
        return None, "bad url"
    # only allow known logo hosts
    host = urlparse(url).netloc.lower()
    if not any(
        host.endswith(x)
        for x in (
            "gmgn.ai",
            "gmgn.cc",
            "external-res",
        )
    ) and "gmgn" not in host and "external-res" not in url:
        # still allow gmgn external-res paths
        if "gmgn" not in host:
            return None, "host not allowed"
    LOGO_DIR.mkdir(parents=True, exist_ok=True)
    # cache key
    import hashlib

    key = hashlib.sha1(url.encode("utf-8")).hexdigest()
    ext = ".webp"
    if ".png" in url.lower():
        ext = ".png"
    elif ".jpg" in url.lower() or ".jpeg" in url.lower():
        ext = ".jpg"
    elif ".gif" in url.lower():
        ext = ".gif"
    path = LOGO_DIR / f"{key}{ext}"
    if path.is_file() and path.stat().st_size > 50:
        ctype = {
            ".webp": "image/webp",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".gif": "image/gif",
        }.get(ext, "application/octet-stream")
        return path.read_bytes(), ctype
    try:
        req = Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
                "Referer": "https://gmgn.ai/",
            },
        )
        with urlopen(req, timeout=15) as resp:
            data = resp.read()
            ctype = resp.headers.get_content_type() or "image/webp"
        if not data or len(data) < 50:
            return None, "empty"
        path.write_bytes(data)
        return data, ctype
    except Exception as e:
        return None, str(e)


def _gmgn_cli() -> str:
    tools = ROOT / "tools" / "node_modules" / ".bin"
    for name in ("gmgn-cli", "gmgn-cli.cmd", "gmgn-cli.exe"):
        p = tools / name
        if p.is_file():
            return str(p)
    import shutil

    w = shutil.which("gmgn-cli") or shutil.which("gmgn-cli.cmd")
    if w:
        return w
    # hermes desk common path (this VPS profile)
    alt = Path("/opt/data/profiles/rh-meme-desk/tools/node_modules/.bin/gmgn-cli")
    if alt.is_file():
        return str(alt)
    return "gmgn-cli"


def _spark_closes(address: str, hours: int = 24, resolution: str = "1h") -> dict:
    """GMGN kline closes for mini sparkline. Disk cache ~15m (+ bundled demo sparks ok)."""
    addr = (address or "").strip().lower()
    if not re.fullmatch(r"0x[a-f0-9]{40}", addr):
        return {"ok": False, "error": "bad address"}
    spark_dir = CACHE / "sparks"
    spark_dir.mkdir(parents=True, exist_ok=True)
    cache_path = spark_dir / f"{addr}_{resolution}_{hours}h.json"
    # allow stale bundled demo sparks forever if no gmgn available
    if cache_path.is_file() and cache_path.stat().st_size > 20:
        age = time.time() - cache_path.stat().st_mtime
        if age < 900:  # fresh
            try:
                return json.loads(cache_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        else:
            # stale: try refresh below; if fail, still return stale
            try:
                stale = json.loads(cache_path.read_text(encoding="utf-8"))
            except Exception:
                stale = None
    else:
        stale = None

    to_ts = int(time.time())
    from_ts = to_ts - int(hours) * 3600
    env = os.environ.copy()
    tools_bin = ROOT / "tools" / "node_modules" / ".bin"
    env["PATH"] = f"{tools_bin}{os.pathsep}{env.get('PATH', '')}"
    # also prepend rh-meme tools if present on this machine
    rh = Path("/opt/data/profiles/rh-meme-desk/tools/node_modules/.bin")
    if rh.is_dir():
        env["PATH"] = f"{rh}{os.pathsep}{env['PATH']}"
    cmd = [
        _gmgn_cli(),
        "market",
        "kline",
        "--chain",
        "robinhood",
        "--address",
        addr,
        "--resolution",
        resolution,
        "--from",
        str(from_ts),
        "--to",
        str(to_ts),
        "--raw",
    ]
    try:
        r = subprocess.run(
            cmd, cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=45
        )
        if r.returncode != 0:
            if stale and stale.get("closes"):
                stale = dict(stale)
                stale["stale"] = True
                stale["error"] = (r.stderr or r.stdout or "kline fail")[:160]
                return stale
            return {"ok": False, "error": (r.stderr or r.stdout or "kline fail")[:200]}
        raw = json.loads(r.stdout)
        rows = raw.get("list") if isinstance(raw, dict) else raw
        closes = []
        for row in rows or []:
            try:
                closes.append(float(row.get("close")))
            except Exception:
                continue
        out = {
            "ok": True,
            "address": addr,
            "resolution": resolution,
            "hours": hours,
            "closes": closes[-48:],
            "n": len(closes),
        }
        cache_path.write_text(json.dumps(out), encoding="utf-8")
        return out
    except Exception as e:
        if stale and stale.get("closes"):
            stale = dict(stale)
            stale["stale"] = True
            stale["error"] = str(e)[:160]
            return stale
        return {"ok": False, "error": str(e)}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB), **kwargs)

    def log_message(self, fmt, *args):
        sys.stderr.write("[hoodradar-web] " + (fmt % args) + "\n")

    def _json(self, code: int, obj):
        body = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path in ("/api/state", "/api/health"):
            self._json(200, _api_state() if u.path == "/api/state" else {"ok": True})
            return
        if u.path == "/api/brief":
            q = parse_qs(u.query)
            name = (q.get("name") or ["buy_the_dip"])[0]
            safe = re.sub(r"[^a-zA-Z0-9_.-]", "", name)
            text = _read_text(f"{safe}_brief.txt") or _read_text(f"{safe}.txt")
            self._json(200, {"name": safe, "text": text})
            return
        if u.path == "/api/logo":
            q = parse_qs(u.query)
            raw = (q.get("u") or q.get("url") or [""])[0]
            url = unquote(raw)
            data, ctype = _fetch_logo(url)
            if not data:
                self.send_response(404)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"logo unavailable")
                return
            self.send_response(200)
            self.send_header("Content-Type", ctype if isinstance(ctype, str) and ctype.startswith("image") else "image/webp")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "public, max-age=86400")
            self.end_headers()
            self.wfile.write(data)
            return
        if u.path == "/api/spark":
            q = parse_qs(u.query)
            addr = (q.get("a") or q.get("address") or [""])[0]
            hours = int((q.get("h") or ["24"])[0] or 24)
            res = (q.get("r") or ["1h"])[0] or "1h"
            self._json(200, _spark_closes(addr, hours=hours, resolution=res))
            return
        # default static from web/
        if u.path == "/" or u.path == "":
            self.path = "/index.html"
        return SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        u = urlparse(self.path)
        if u.path == "/api/scan":
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            try:
                body = json.loads(raw.decode("utf-8") or "{}")
            except Exception:
                body = {}
            kind = (body.get("kind") or "dip").lower()
            if kind not in ("dip", "smart", "wallets", "hot", "hotsearch", "hot_search", "all"):
                self._json(400, {"ok": False, "error": "kind must be dip|smart|wallets|hot|all"})
                return
            # run in-thread (blocks this worker only)
            result = _run_scan(kind)
            self._json(200, result)
            return
        self._json(404, {"ok": False, "error": "not found"})


def main():
    WEB.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    if not (WEB / "index.html").is_file():
        print(f"ERROR: missing {WEB / 'index.html'}", file=sys.stderr)
        sys.exit(1)
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"HOODRADAR desk → http://{HOST}:{PORT}")
    print(f"  root={ROOT}")
    print(f"  cache={CACHE}")
    print("  research only · Ctrl+C to stop")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")
        httpd.shutdown()


if __name__ == "__main__":
    main()
