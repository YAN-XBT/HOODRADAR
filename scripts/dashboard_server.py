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
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "cron" / "cache"
WEB = ROOT / "web"
CONFIG = ROOT / "config"
PORT = 8787

RPC_URL = "https://rpc.mainnet.chain.robinhood.com"
CHAIN_ID = 4663
FACTORY_V2 = "0x7eD598BcEf8bd9Edd8C97A195C6d13f40801EC7e"
FACTORY_V1 = "0xA5aAb3F0c6EeadF30Ef1D3Eb997108E976351feB"
TOPIC_TOKEN_LAUNCHED = "0x8d4aad4953d0ca700d468f3753aa14432d1b35b43ec6409f051fb6aa43a89607"
SEL_SYMBOL = "0x95d89b41"
SEL_NAME = "0x06fdde03"
RPC_TIMEOUT = 12
LOOKBACK_BLOCKS = 30_000
WINDOW_BLOCKS = 2_000
MAX_PAIRS = 40

ADDR_RE = re.compile(r"0x[a-fA-F0-9]{40}")
PET_RE = re.compile(r"\b(pet|dog|cat|meme|doge|shib|pepe|inu|kitten|puppy)\b", re.I)

_lock = threading.Lock()
_index_lock = threading.Lock()
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
    "scan": {"dip": None, "wallets": None, "error": None},
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
        STATE["scan"]["error"] = None
    persist_cache()


def _set_scan_error(msg: str | None):
    with _lock:
        STATE["scan"]["error"] = msg


def rpc(method: str, params, retries: int = 4):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "HOODRADAR/2 (research)",
    }
    last_err = None
    for attempt in range(retries):
        try:
            req = Request(RPC_URL, data=body, headers=headers, method="POST")
            with urlopen(req, timeout=RPC_TIMEOUT) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if data.get("error"):
                raise RuntimeError(str(data["error"]))
            return data.get("result")
        except HTTPError as e:
            last_err = e
            if e.code in (429, 502, 503, 504):
                time.sleep(0.6 * (attempt + 1))
                continue
            raise
        except (URLError, TimeoutError, OSError) as e:
            last_err = e
            time.sleep(0.4 * (attempt + 1))
    raise RuntimeError(f"rpc {method} failed: {last_err}")


def topic_addr(topic: str) -> str:
    h = (topic or "").replace("0x", "").lower()
    return "0x" + h[-40:]


def decode_abi_string(hexdata: str) -> str:
    if not hexdata or hexdata in ("0x", "0x0"):
        return ""
    raw = bytes.fromhex(hexdata[2:] if hexdata.startswith("0x") else hexdata)
    if len(raw) < 64:
        return ""
    offset = int.from_bytes(raw[0:32], "big")
    if offset + 32 > len(raw):
        offset = 32
    length = int.from_bytes(raw[offset : offset + 32], "big")
    start = offset + 32
    end = start + length
    if end > len(raw):
        end = len(raw)
    return raw[start:end].decode("utf-8", errors="replace").rstrip("\x00").strip()


def eth_call(to: str, data: str) -> str | None:
    try:
        return rpc("eth_call", [{"to": to, "data": data}, "latest"], retries=2)
    except Exception:
        return None


def fetch_logs(address: str, from_block: int, to_block: int) -> list:
    window = WINDOW_BLOCKS
    cur = from_block
    logs: list = []
    while cur <= to_block:
        end = min(to_block, cur + window - 1)
        try:
            chunk = rpc(
                "eth_getLogs",
                [
                    {
                        "fromBlock": hex(cur),
                        "toBlock": hex(end),
                        "address": address,
                        "topics": [TOPIC_TOKEN_LAUNCHED],
                    }
                ],
            ) or []
            logs.extend(chunk)
            cur = end + 1
        except Exception as e:
            msg = str(e)
            if window > 200:
                window = max(200, window // 2)
                continue
            _set_scan_error(msg)
            print(f"[indexer] getLogs error {hex(cur)}-{hex(end)}: {e}")
            cur = end + 1
            time.sleep(0.5)
    return logs


def logs_to_pairs(logs: list) -> list:
    by_token = {}
    for lg in logs:
        topics = lg.get("topics") or []
        if len(topics) < 2:
            continue
        token = topic_addr(topics[1])
        block_hex = lg.get("blockNumber") or "0x0"
        try:
            bn = int(block_hex, 16)
        except Exception:
            bn = 0
        prev = by_token.get(token.lower())
        if prev is None or bn >= prev["bn"]:
            by_token[token.lower()] = {
                "addr": token,
                "bn": bn,
                "blockNumber": block_hex,
            }
    rows = sorted(by_token.values(), key=lambda x: x["bn"], reverse=True)[:MAX_PAIRS]
    out = []
    for row in rows:
        addr = row["addr"]
        sym = "?"
        name = ""
        try:
            sraw = eth_call(addr, SEL_SYMBOL)
            nraw = eth_call(addr, SEL_NAME)
            if sraw:
                s = decode_abi_string(sraw)
                if s:
                    sym = s
            if nraw:
                n = decode_abi_string(nraw)
                if n:
                    name = n
        except Exception:
            continue
        out.append(
            {
                "sym": sym,
                "name": name or sym,
                "addr": addr,
                "mc": None,
                "vol": None,
                "chg": None,
                "age": f"block {row['bn']}",
            }
        )
        time.sleep(0.05)
    return out


def index_launches() -> dict:
    """Research-only: read TokenLaunched logs. No buy/tx."""
    with _index_lock:
        try:
            bn_hex = rpc("eth_blockNumber", [])
            latest = int(bn_hex, 16)
            start = max(0, latest - LOOKBACK_BLOCKS)
            logs = fetch_logs(FACTORY_V2, start, latest)
            try:
                v1_start = max(0, latest - WINDOW_BLOCKS)
                v1 = fetch_logs(FACTORY_V1, v1_start, latest)
                if v1:
                    logs.extend(v1)
            except Exception:
                pass
            pairs = logs_to_pairs(logs)
            with _lock:
                STATE["new_pairs"] = pairs
                STATE["updated_at"] = fmt_now()
                STATE["scan"]["error"] = None if pairs or logs else STATE["scan"].get("error")
            persist_cache()
            n = len(pairs)
            print(f"[indexer] {len(logs)} TokenLaunched logs -> {n} unique rows (latest={latest})")
            return {"ok": True, "logs": len(logs), "indexed": n, "latest": latest}
        except Exception as e:
            _set_scan_error(str(e))
            print(f"[indexer] failed: {e}")
            return {"ok": False, "error": str(e), "indexed": 0, "logs": 0}


def run_scan(kind: str) -> dict:
    kind = (kind or "").lower().strip()
    if kind not in ("dip", "wallets"):
        return {"ok": False, "error": "kind must be dip or wallets"}
    now = fmt_now()
    result = index_launches()
    n = int(result.get("indexed") or 0)
    with _lock:
        if kind == "wallets":
            STATE["scan"]["wallets"] = now
            STATE["wallet_count"] = len(STATE["wallets"])
        elif kind == "dip":
            STATE["scan"]["dip"] = now
            STATE["dips"] = []
        STATE["updated_at"] = now
        if not result.get("ok"):
            STATE["scan"]["error"] = result.get("error")
    persist_cache()
    msg = f"indexed {n} launches"
    if not result.get("ok") and result.get("error"):
        msg = f"indexed {n} launches ({result['error']})"
    return {
        "ok": bool(result.get("ok")),
        "kind": kind,
        "at": now,
        "queued": False,
        "indexed": n,
        "logs": result.get("logs"),
        "message": msg,
    }


def classify_addr(message: str, addr: str) -> str:
    low = message.lower()
    if "wallet" in low or "eoa" in low:
        return "wallet"
    if any(k in low for k in ("token", "pair", "contract", "ca", "coin")):
        return "token"
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
    t = threading.Thread(target=index_launches, name="pons-index", daemon=True)
    t.start()
    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"  http://127.0.0.1:{PORT}/")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.shutdown()


if __name__ == "__main__":
    main()
