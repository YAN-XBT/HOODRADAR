#!/usr/bin/env python3
"""HOODRADAR v2 local dashboard. Research only. Port 8787."""
from __future__ import annotations

import hashlib
import json
import re
import threading
import uuid
import os
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, unquote, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "cron" / "cache"
IMG_CACHE = CACHE / "img"
WEB = ROOT / "web"
CONFIG = ROOT / "config"
PORT = 8787

RPC_URL = "https://rpc.mainnet.chain.robinhood.com"
CHAIN_ID = 4663
FACTORY_V2 = "0x7eD598BcEf8bd9Edd8C97A195C6d13f40801EC7e"
FACTORY_V1 = "0xA5aAb3F0c6EeadF30Ef1D3Eb997108E976351feB"
WETH = "0x0Bd7D308f8E1639FAb988df18A8011f41EAcAD73"
TOPIC_TOKEN_LAUNCHED = "0x8d4aad4953d0ca700d468f3753aa14432d1b35b43ec6409f051fb6aa43a89607"
TOPIC_CURVE_BUY = "0xec36bf571f136799e8dc0b0b8bea4b04d8bd3d43de838aab0d5fc21d4cbfc455"
TOPIC_CURVE_SELL = "0x8113d738abdcb6b38357e9d53a54a7157861a09031b453651f0fe7fe151f59df"
SEL_SYMBOL = "0x95d89b41"
SEL_NAME = "0x06fdde03"
SEL_TOTAL_SUPPLY = "0x18160ddd"
SEL_GET_TOKEN_INFO = "0xabb1dc44"
SEL_TOKEN_LOGO = "0x291526ac"
SEL_GET_RESERVES = "0x0902f1ac"
SEL_REAL_QUOTE = "0x4f1f58fd"
SEL_PAIR_TOKEN = "0x3de35b79"
SEL_PAIR_DECIMALS = "0xc9b58ec7"
SEL_GRADUATED = "0xe7c2b772"
SEL_GRAD_THRESH = "0x8b0bc501"
SEL_GET_LAUNCHED = "0x3cf28b5a"
SEL_PHANTOM = "0xc57eadfc"
RPC_TIMEOUT = 12
LOOKBACK_BLOCKS = 30_000
WINDOW_BLOCKS = 2_000
VOL_LOOKBACK = 8_000
BLOCKS_1H = 1_800
BLOCKS_5M = 150
MAX_PAIRS = 40
MAX_ENRICH = 80
MC_MIN_USD = 5000.0
MC_TAPE_USD = 20_000.0
ABOUT_PROGRESS = 0.70
ABOUT_MIN = 8
DIP_CHG = -20.0
DIP_MC = 50_000.0
IMG_MAX = 512 * 1024

ADDR_RE = re.compile(r"0x[a-fA-F0-9]{40}")
PET_RE = re.compile(r"\b(pet|dog|cat|meme|doge|shib|pepe|inu|kitten|puppy)\b", re.I)

_lock = threading.Lock()
_index_lock = threading.Lock()
_eth_usd = {"price": None, "src": None, "at": 0.0}
STATE = {
    "online": True,
    "updated_at": None,
    "research_only": True,
    "wallet": {"address": "", "balance_usd": 0, "pnl_usd": 0},
    "safe_tape": [],
    "new_pairs": [],
    "pairs_migrated": [],
    "pairs_about": [],
    "dips": [],
    "trending": {"1h": [], "5m": []},
    "wallets": [],
    "x_watch": [],
    "x_feed": [],
    "x_feed_error": None,
    "x_feed_source": None,
    "cache_count": 0,
    "wallet_count": 0,
    "scan": {"dip": None, "wallets": None, "error": None},
    "eth_usd": None,
    "eth_usd_src": None,
}


# --- keccak-256 (Ethereum, not NIST SHA3) ---
_RC = [
    0x0000000000000001, 0x0000000000008082, 0x800000000000808A, 0x8000000080008000,
    0x000000000000808B, 0x0000000080000001, 0x8000000080008081, 0x8000000000008009,
    0x000000000000008A, 0x0000000000000088, 0x0000000080008009, 0x000000008000000A,
    0x000000008000808B, 0x800000000000008B, 0x8000000000008089, 0x8000000000008003,
    0x8000000000008002, 0x8000000000000080, 0x000000000000800A, 0x800000008000000A,
    0x8000000080008081, 0x8000000000008080, 0x0000000080000001, 0x8000000080008008,
]
_ROT = [
    [0, 36, 3, 41, 18], [1, 44, 10, 45, 2], [62, 6, 43, 15, 61],
    [28, 55, 25, 21, 56], [27, 20, 39, 8, 14],
]
_MASK64 = (1 << 64) - 1


def _rotl64(x, n):
    n %= 64
    return ((x << n) | (x >> (64 - n))) & _MASK64


def keccak256(data: bytes) -> bytes:
    rate = 136
    st = [[0] * 5 for _ in range(5)]
    pad = data + b"\x01"
    pad += b"\x00" * ((rate - (len(pad) % rate)) % rate)
    pad = pad[:-1] + bytes([pad[-1] | 0x80])
    for i in range(0, len(pad), rate):
        block = pad[i : i + rate]
        for j in range(rate // 8):
            x, y = j % 5, j // 5
            st[x][y] ^= int.from_bytes(block[j * 8 : (j + 1) * 8], "little")
        for rnd in range(24):
            C = [st[x][0] ^ st[x][1] ^ st[x][2] ^ st[x][3] ^ st[x][4] for x in range(5)]
            D = [C[(x - 1) % 5] ^ _rotl64(C[(x + 1) % 5], 1) for x in range(5)]
            for x in range(5):
                for y in range(5):
                    st[x][y] ^= D[x]
            B = [[0] * 5 for _ in range(5)]
            for x in range(5):
                for y in range(5):
                    B[y][(2 * x + 3 * y) % 5] = _rotl64(st[x][y], _ROT[x][y])
            for x in range(5):
                for y in range(5):
                    st[x][y] = (B[x][y] ^ ((~B[(x + 1) % 5][y]) & B[(x + 2) % 5][y])) & _MASK64
            st[0][0] ^= _RC[rnd]
    out = b""
    for j in range(rate // 8):
        x, y = j % 5, j // 5
        out += st[x][y].to_bytes(8, "little")
        if len(out) >= 32:
            break
    return out[:32]


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
        if not STATE.get("x_feed"):
            STATE["x_feed"] = []
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


def rpc_batch(calls: list, retries: int = 3) -> list:
    """calls: list of (method, params). Returns list of results (None on item error)."""
    if not calls:
        return []
    payload = [{"jsonrpc": "2.0", "id": i, "method": m, "params": p} for i, (m, p) in enumerate(calls)]
    body = json.dumps(payload).encode()
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "HOODRADAR/2 (research)",
    }
    last_err = None
    for attempt in range(retries):
        try:
            req = Request(RPC_URL, data=body, headers=headers, method="POST")
            with urlopen(req, timeout=RPC_TIMEOUT + 8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if isinstance(data, dict):
                data = [data]
            by_id = {}
            for item in data:
                by_id[item.get("id")] = item.get("result") if not item.get("error") else None
            return [by_id.get(i) for i in range(len(calls))]
        except HTTPError as e:
            last_err = e
            if e.code in (429, 502, 503, 504):
                time.sleep(0.6 * (attempt + 1))
                continue
            raise
        except (URLError, TimeoutError, OSError) as e:
            last_err = e
            time.sleep(0.4 * (attempt + 1))
    print(f"[indexer] batch failed: {last_err}; falling back to single calls")
    out = []
    for method, params in calls:
        try:
            out.append(rpc(method, params, retries=4))
            time.sleep(0.12)
        except Exception as e:
            print(f"[indexer] single {method} failed: {e}")
            out.append(None)
            time.sleep(0.4)
    return out


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
    end = min(len(raw), start + length)
    return raw[start:end].decode("utf-8", errors="replace").rstrip("\x00").strip()


def _str_at(raw: bytes, offset: int) -> str:
    if offset < 0 or offset + 32 > len(raw):
        return ""
    length = int.from_bytes(raw[offset : offset + 32], "big")
    if length > 10_000:
        return ""
    start = offset + 32
    end = min(len(raw), start + length)
    return raw[start:end].decode("utf-8", errors="replace").rstrip("\x00").strip()


def decode_token_info(hexdata: str) -> dict:
    out = {"deployer": "", "logo": "", "description": "", "socials": {}}
    if not hexdata or hexdata in ("0x", "0x0"):
        return out
    raw = bytes.fromhex(hexdata[2:] if hexdata.startswith("0x") else hexdata)
    if len(raw) < 128:
        return out
    out["deployer"] = "0x" + raw[12:32].hex()
    off_logo = int.from_bytes(raw[32:64], "big")
    off_desc = int.from_bytes(raw[64:96], "big")
    off_soc = int.from_bytes(raw[96:128], "big")
    out["logo"] = _str_at(raw, off_logo)
    out["description"] = _str_at(raw, off_desc)
    names = ("twitter", "telegram", "discord", "website", "farcaster")
    socials = {}
    if 0 <= off_soc < len(raw):
        base = off_soc
        for i, n in enumerate(names):
            sl = base + i * 32
            if sl + 32 > len(raw):
                break
            rel = int.from_bytes(raw[sl : sl + 32], "big")
            socials[n] = _str_at(raw, base + rel)
    out["socials"] = {k: v for k, v in socials.items() if v}
    return out


def u256(hexdata: str | None) -> int:
    if not hexdata or hexdata in ("0x", "0x0"):
        return 0
    try:
        return int(hexdata, 16)
    except Exception:
        return 0


def word_addr(hexdata: str | None) -> str:
    if not hexdata:
        return "0x" + "0" * 40
    h = hexdata[2:] if hexdata.startswith("0x") else hexdata
    h = h.rjust(64, "0")
    return "0x" + h[-40:]


def http_json(url: str, timeout: int = 8):
    req = Request(url, headers={"Accept": "application/json", "User-Agent": "HOODRADAR/2 (research)"})
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_eth_usd() -> tuple[float | None, str | None]:
    now = time.time()
    if _eth_usd["price"] is not None and now - _eth_usd["at"] < 180:
        return _eth_usd["price"], _eth_usd["src"]
    sources = [
        ("coingecko", "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"),
        ("binance", "https://api.binance.com/api/v3/ticker/price?symbol=ETHUSDT"),
    ]
    for name, url in sources:
        try:
            data = http_json(url, timeout=8)
            px = None
            if name == "coingecko":
                px = float((data.get("ethereum") or {}).get("usd") or 0)
            elif name == "binance":
                px = float(data.get("price") or 0)
            if px and px > 0:
                _eth_usd.update({"price": px, "src": name, "at": now})
                return px, name
        except Exception as e:
            print(f"[indexer] eth usd {name} failed: {e}")
    return _eth_usd["price"], _eth_usd["src"]


def eth_call(to: str, data: str) -> str | None:
    try:
        return rpc("eth_call", [{"to": to, "data": data}, "latest"], retries=2)
    except Exception:
        return None


def fetch_logs(address: str, from_block: int, to_block: int, topics: list | None = None) -> list:
    window = WINDOW_BLOCKS
    cur = from_block
    logs: list = []
    tps = topics if topics is not None else [TOPIC_TOKEN_LAUNCHED]
    while cur <= to_block:
        end = min(to_block, cur + window - 1)
        try:
            filt = {
                "fromBlock": hex(cur),
                "toBlock": hex(end),
                "address": address,
                "topics": tps,
            }
            chunk = rpc("eth_getLogs", [filt]) or []
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


def fetch_curve_trade_logs(curves: list[str], from_block: int, to_block: int) -> list:
    if not curves:
        return []
    window = WINDOW_BLOCKS
    cur = from_block
    logs: list = []
    addrs = list(dict.fromkeys(c for c in curves if c))
    while cur <= to_block:
        end = min(to_block, cur + window - 1)
        try:
            chunk = rpc(
                "eth_getLogs",
                [
                    {
                        "fromBlock": hex(cur),
                        "toBlock": hex(end),
                        "address": addrs,
                        "topics": [[TOPIC_CURVE_BUY, TOPIC_CURVE_SELL]],
                    }
                ],
            ) or []
            logs.extend(chunk)
            cur = end + 1
        except Exception as e:
            if window > 200:
                window = max(200, window // 2)
                continue
            print(f"[indexer] trade logs {hex(cur)}-{hex(end)}: {e}")
            cur = end + 1
            time.sleep(0.4)
    return logs


def age_label(bn: int, latest: int) -> str:
    dt = max(0, latest - bn)
    sec = dt * 2
    if sec < 90:
        return f"{sec}s"
    if sec < 3600:
        return f"{sec // 60}m"
    if sec < 86400:
        return f"{sec // 3600}h"
    return f"{sec // 86400}d"


def clean_socials(s: dict) -> dict:
    out = {}
    for k, v in (s or {}).items():
        v = (v or "").strip()
        if not v:
            continue
        out[k] = v
    return out


def social_href(kind: str, val: str) -> str:
    v = val.strip()
    if v.startswith("http://") or v.startswith("https://"):
        return v
    if kind == "twitter":
        h = v.lstrip("@")
        return "https://x.com/" + h
    if kind == "telegram":
        h = v.lstrip("@").replace("https://t.me/", "")
        return "https://t.me/" + h
    if kind == "discord":
        if "discord" in v:
            return v if v.startswith("http") else "https://" + v
        return "https://discord.gg/" + v
    if kind == "website":
        return v if "://" in v else "https://" + v
    if kind == "farcaster":
        h = v.lstrip("@")
        if h.startswith("http"):
            return h
        return "https://warpcast.com/" + h
    return v


def parse_launches(logs: list) -> list:
    by_token = {}
    for lg in logs:
        topics = lg.get("topics") or []
        if len(topics) < 2:
            continue
        token = topic_addr(topics[1])
        curve = topic_addr(topics[2]) if len(topics) > 2 else ""
        deployer = topic_addr(topics[3]) if len(topics) > 3 else ""
        data = lg.get("data") or "0x"
        pair = "0x" + "0" * 40
        if data and data != "0x":
            raw = data[2:] if data.startswith("0x") else data
            if len(raw) >= 64:
                pair = "0x" + raw[24:64]
        block_hex = lg.get("blockNumber") or "0x0"
        try:
            bn = int(block_hex, 16)
        except Exception:
            bn = 0
        prev = by_token.get(token.lower())
        factory = (lg.get("address") or FACTORY_V2).lower()
        if prev is None or bn >= prev["bn"]:
            by_token[token.lower()] = {
                "addr": token,
                "curve": curve,
                "deployer": deployer,
                "pair_token": pair,
                "bn": bn,
                "factory": factory,
            }
    return sorted(by_token.values(), key=lambda x: x["bn"], reverse=True)


def enrich_launches(launches: list, latest: int, eth_usd: float | None) -> list:
    work = launches[:MAX_ENRICH]
    calls = []
    meta = []  # (row_idx, kind)

    def add_call(to, sel, kind, i):
        calls.append(("eth_call", [{"to": to, "data": sel}, "latest"]))
        meta.append((i, kind))

    for i, row in enumerate(work):
        tok, curve = row["addr"], row["curve"]
        add_call(tok, SEL_SYMBOL, "sym", i)
        add_call(tok, SEL_NAME, "name", i)
        add_call(tok, SEL_TOTAL_SUPPLY, "supply", i)
        add_call(tok, SEL_GET_TOKEN_INFO, "info", i)
        add_call(tok, SEL_TOKEN_LOGO, "logo", i)
        if curve:
            add_call(curve, SEL_GET_RESERVES, "reserves", i)
            add_call(curve, SEL_REAL_QUOTE, "realq", i)
            add_call(curve, SEL_PAIR_TOKEN, "pair", i)
            add_call(curve, SEL_PAIR_DECIMALS, "pdec", i)
            add_call(curve, SEL_GRADUATED, "grad", i)
            add_call(curve, SEL_GRAD_THRESH, "gth", i)
        fac = row.get("factory") or FACTORY_V2
        tok_arg = "0x" + tok[2:].lower().rjust(64, "0")
        add_call(fac, SEL_GET_LAUNCHED + tok_arg[2:], "launch", i)

    results = {}
    BATCH = 8
    for off in range(0, len(calls), BATCH):
        chunk = calls[off : off + BATCH]
        got = rpc_batch(chunk)
        for j, res in enumerate(got):
            results[off + j] = res
        time.sleep(0.05)

    buckets = [{} for _ in work]
    for idx, (i, kind) in enumerate(meta):
        buckets[i][kind] = results.get(idx)

    curves = [r["curve"] for r in work if r.get("curve")]
    vol_from = max(0, latest - VOL_LOOKBACK)
    trades = []
    try:
        trades = fetch_curve_trade_logs(curves, vol_from, latest)
    except Exception as e:
        print(f"[indexer] volume logs failed: {e}")

    vol_quote = {c.lower(): 0 for c in curves}
    vol_1h_q = {c.lower(): 0 for c in curves}
    vol_5m_q = {c.lower(): 0 for c in curves}
    txs_1h = {c.lower(): 0 for c in curves}
    txs_5m = {c.lower(): 0 for c in curves}
    first_px = {}
    last_px = {}
    first_bn = {}
    last_bn = {}
    cut_1h = max(0, latest - BLOCKS_1H)
    cut_5m = max(0, latest - BLOCKS_5M)
    for lg in trades:
        addr = (lg.get("address") or "").lower()
        topics = lg.get("topics") or []
        t0 = (topics[0] if topics else "").lower()
        data = lg.get("data") or "0x"
        raw = bytes.fromhex(data[2:] if data.startswith("0x") else data)
        if len(raw) < 64:
            continue
        a = int.from_bytes(raw[0:32], "big")
        b = int.from_bytes(raw[32:64], "big")
        try:
            bn = int(lg.get("blockNumber") or "0x0", 16)
        except Exception:
            bn = 0
        quote = 0
        px = None
        if t0 == TOPIC_CURVE_BUY.lower():
            quote = a
            if b:
                px = a / b
        elif t0 == TOPIC_CURVE_SELL.lower():
            quote = b
            if a:
                px = b / a
        vol_quote[addr] = vol_quote.get(addr, 0) + quote
        if bn >= cut_1h:
            vol_1h_q[addr] = vol_1h_q.get(addr, 0) + quote
            txs_1h[addr] = txs_1h.get(addr, 0) + 1
        if bn >= cut_5m:
            vol_5m_q[addr] = vol_5m_q.get(addr, 0) + quote
            txs_5m[addr] = txs_5m.get(addr, 0) + 1
        if px and px > 0:
            if addr not in first_bn or bn < first_bn[addr]:
                first_bn[addr] = bn
                first_px[addr] = px
            if addr not in last_bn or bn >= last_bn[addr]:
                last_bn[addr] = bn
                last_px[addr] = px

    rows = []
    for i, src in enumerate(work):
        bkt = buckets[i]
        sym = decode_abi_string(bkt.get("sym") or "") or "?"
        name = decode_abi_string(bkt.get("name") or "") or sym
        info = decode_token_info(bkt.get("info") or "")
        logo = info.get("logo") or decode_abi_string(bkt.get("logo") or "")
        socials = clean_socials(info.get("socials") or {})
        supply = u256(bkt.get("supply"))
        res_hex = bkt.get("reserves") or "0x"
        qres = tres = 0
        if res_hex and res_hex not in ("0x", "0x0"):
            rh = res_hex[2:] if res_hex.startswith("0x") else res_hex
            rh = rh.rjust(128, "0")
            qres = int(rh[0:64], 16)
            tres = int(rh[64:128], 16)
        pdec = u256(bkt.get("pdec")) or 18
        if pdec > 36:
            pdec = 18
        pair = word_addr(bkt.get("pair")) if bkt.get("pair") else src.get("pair_token")
        graduated = bool(u256(bkt.get("grad")))
        realq = u256(bkt.get("realq"))
        gth = u256(bkt.get("gth"))
        phase = None
        launch_hex = bkt.get("launch") or "0x"
        if launch_hex and launch_hex not in ("0x", "0x0"):
            lh = launch_hex[2:] if launch_hex.startswith("0x") else launch_hex
            # ABI struct words: 0-4 addrs, 5 threshold, 6 poolFee, 7 tick, 8 tax, 9 buyback, 10 phase
            if len(lh) >= 11 * 64:
                try:
                    phase = int(lh[10 * 64 : 11 * 64], 16)
                except Exception:
                    phase = None
                if not gth:
                    try:
                        gth = int(lh[5 * 64 : 6 * 64], 16)
                    except Exception:
                        pass
        progress = None
        if gth:
            progress = min(1.0, (realq or 0) / gth)
        phase_name = {0: "NotGraduated", 1: "Swept", 2: "PoolCreated", 3: "Rescued"}.get(phase)
        migrated = bool(graduated) or phase in (1, 2) or (phase_name in ("Swept", "PoolCreated"))
        mc_eth = None
        mc_usd = None
        if qres and tres and supply:
            mc_eth = (qres * supply) / tres / (10 ** pdec)
            if eth_usd:
                mc_usd = mc_eth * eth_usd
        curve = src.get("curve") or ""
        vq = vol_quote.get(curve.lower(), 0)
        vol_eth = vq / (10 ** pdec) if vq else 0
        if eth_usd and vq:
            vol_usd = vol_eth * eth_usd
        elif not vq:
            vol_usd = 0.0
        else:
            vol_usd = None
        liq_eth = (realq or qres) / (10 ** pdec) if (realq or qres) else None
        liq_usd = (liq_eth * eth_usd) if (liq_eth is not None and eth_usd) else None
        # GMGN-style curve liq estimate: 2 * real quote (not invented ATH/holders)
        liq2_eth = (2 * realq / (10 ** pdec)) if realq else None
        liq2_usd = (liq2_eth * eth_usd) if (liq2_eth is not None and eth_usd) else None
        def _usd_from_q(q):
            if not q:
                return 0.0 if q == 0 else None
            ethv = q / (10 ** pdec)
            return round(ethv * eth_usd, 2) if eth_usd else None
        v1h = _usd_from_q(vol_1h_q.get(curve.lower(), 0) if curve else 0)
        v5m = _usd_from_q(vol_5m_q.get(curve.lower(), 0) if curve else 0)
        chg = None
        ck = curve.lower()
        if ck in first_px and ck in last_px and first_px[ck]:
            if first_bn.get(ck) != last_bn.get(ck) or first_px[ck] != last_px[ck]:
                chg = (last_px[ck] - first_px[ck]) / first_px[ck] * 100.0
        rows.append(
            {
                "sym": sym,
                "name": name,
                "addr": src["addr"],
                "curve": curve,
                "deployer": src.get("deployer") or info.get("deployer") or "",
                "pair_token": pair,
                "mc": round(mc_usd, 2) if mc_usd is not None else None,
                "mc_eth": round(mc_eth, 6) if mc_eth is not None else None,
                "vol": round(vol_usd, 2) if vol_usd is not None else None,
                "vol_1h": v1h,
                "vol_5m": v5m,
                "txs_1h": txs_1h.get(curve.lower(), 0) if curve else 0,
                "txs_5m": txs_5m.get(curve.lower(), 0) if curve else 0,
                "liq": round(liq_usd, 2) if liq_usd is not None else None,
                "liq2": round(liq2_usd, 2) if liq2_usd is not None else None,
                "chg": round(chg, 2) if chg is not None else None,
                "age": age_label(src["bn"], latest),
                "bn": src["bn"],
                "logo": logo,
                "socials": socials,
                "graduated": graduated,
                "migrated": migrated,
                "phase": phase_name or phase,
                "progress": round(progress, 4) if progress is not None else None,
                "threshold_eth": round(gth / (10 ** pdec), 6) if gth else None,
                "raised_eth": round(liq_eth, 6) if liq_eth is not None else None,
            }
        )
    return rows



def pick_trending(rows: list, window: str = "1h") -> list:
    """Rank by recent curve buy+sell volume then tx count. mc >= $5k. No invented ATH/holders."""
    vol_k = "vol_1h" if window != "5m" else "vol_5m"
    tx_k = "txs_1h" if window != "5m" else "txs_5m"
    pool = []
    for r in rows:
        mc = r.get("mc")
        if mc is None or mc < MC_MIN_USD:
            continue
        item = dict(r)
        item["trend_vol"] = r.get(vol_k) if r.get(vol_k) is not None else 0
        item["trend_txs"] = r.get(tx_k) or 0
        item["trend_window"] = window
        item["liq_show"] = r.get("liq2") if r.get("liq2") is not None else r.get("liq")
        pool.append(item)
    pool.sort(key=lambda r: (r.get("trend_vol") or 0, r.get("trend_txs") or 0), reverse=True)
    return pool[:MAX_PAIRS]


def pick_dips(rows: list) -> list:
    """chg from curve trade window (not invented). Prefer mc>=50k and liq>=15k."""
    dumped = [r for r in rows if r.get("chg") is not None and r["chg"] <= DIP_CHG]
    dumped.sort(key=lambda r: (r.get("chg") or 0, -(r.get("mc") or 0)))
    strict = [
        r
        for r in dumped
        if (r.get("mc") or 0) >= DIP_MC and (r.get("liq") is None or r["liq"] >= 15_000)
    ]
    chosen = strict if strict else dumped
    return chosen[:20]


def wallets_from_launches(launches: list, rows: list) -> list:
    """Tracked EOAs = TokenLaunched deployers. Research labels only."""
    raised = {}
    for r in rows:
        d = (r.get("deployer") or "").lower()
        if not d or d == "0x" + "0" * 40:
            continue
        raised[d] = raised.get(d, 0.0) + float(r.get("raised_eth") or 0)
    counts = {}
    last = {}
    for ln in launches:
        d = (ln.get("deployer") or "").lower()
        if not d or d == "0x" + "0" * 40:
            continue
        counts[d] = counts.get(d, 0) + 1
        if d not in last or ln.get("bn", 0) >= last[d].get("bn", 0):
            last[d] = ln
    ranked = sorted(counts.items(), key=lambda kv: (kv[1], raised.get(kv[0], 0.0)), reverse=True)
    out = []
    for addr, n in ranked[:15]:
        usd = None
        if _eth_usd.get("price") and raised.get(addr):
            usd = round(raised[addr] * _eth_usd["price"], 2)
        out.append(
            {
                "address": last[addr].get("deployer") or addr,
                "label": f"PONS deployer · {n} launch{'es' if n != 1 else ''} (research)",
                "usd": usd,
                "pnl": None,
                "launches": n,
            }
        )
    return out


def split_tapes(rows: list) -> tuple[list, list]:
    """Migrated vs about-to-migrate. Both require live mc_usd >= $20k. No fake mcap."""
    priced = [r for r in rows if r.get("mc") is not None and r["mc"] >= MC_TAPE_USD]
    migrated = [r for r in priced if r.get("migrated") or r.get("graduated")]
    unfinished = [r for r in priced if not (r.get("migrated") or r.get("graduated"))]
    about = [r for r in unfinished if (r.get("progress") or 0) >= ABOUT_PROGRESS]
    if len(about) < ABOUT_MIN:
        have = {(r.get("addr") or "").lower() for r in about}
        extra = [r for r in unfinished if (r.get("addr") or "").lower() not in have]
        extra.sort(key=lambda r: (r.get("progress") is not None, r.get("progress") or 0), reverse=True)
        about = about + extra[: max(0, ABOUT_MIN - len(about))]
    migrated.sort(key=lambda r: (r.get("bn") or 0), reverse=True)
    about.sort(key=lambda r: (r.get("progress") or 0, r.get("bn") or 0), reverse=True)
    return migrated[:MAX_PAIRS], about[:MAX_PAIRS]


def apply_mc_filter(rows: list, eth_usd: float | None) -> tuple[list, str | None]:
    priced = [r for r in rows if r.get("mc") is not None]
    unpriced = [r for r in rows if r.get("mc") is None]
    passing = [r for r in priced if r["mc"] >= MC_MIN_USD]
    err = None
    if not passing:
        if unpriced and (not priced or len(unpriced) >= max(1, int(0.6 * len(rows)))):
            err = (
                "mc filter skipped: live ETH/USD or curve reserves missing; "
                "showing launches with mc=null rather than wiping the table"
            )
            if eth_usd is None:
                err = "mc filter skipped: no live ETH/USD price (CoinGecko/Binance); showing mc=null"
            return unpriced[:MAX_PAIRS] + passing, err
        return passing[:MAX_PAIRS], err
    return passing[:MAX_PAIRS], err


def index_launches() -> dict:
    """Research-only: TokenLaunched + curve stats. No buy/tx."""
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
            launches = parse_launches(logs)
            indexed_n = len(launches)
            eth_usd, eth_src = fetch_eth_usd()
            rows = enrich_launches(launches, latest, eth_usd)
            filtered, ferr = apply_mc_filter(rows, eth_usd)
            migrated, about = split_tapes(rows)
            dips = pick_dips(rows)
            trending_1h = pick_trending(rows, "1h")
            trending_5m = pick_trending(rows, "5m")
            wallets = wallets_from_launches(launches, rows)
            shown_rows = migrated + about
            with _lock:
                STATE["new_pairs"] = shown_rows
                STATE["pairs_migrated"] = migrated
                STATE["pairs_about"] = about
                STATE["dips"] = dips
                STATE["trending"] = {"1h": trending_1h, "5m": trending_5m}
                STATE["wallets"] = wallets
                STATE["wallet_count"] = len(wallets)
                STATE["updated_at"] = fmt_now()
                STATE["eth_usd"] = eth_usd
                STATE["eth_usd_src"] = eth_src
                if ferr:
                    STATE["scan"]["error"] = ferr
                else:
                    STATE["scan"]["error"] = None if (shown_rows or logs) else STATE["scan"].get("error")
            persist_cache()
            print(
                f"[indexer] {len(logs)} TokenLaunched logs -> {indexed_n} launches "
                f"-> migrated={len(migrated)} about={len(about)} (>=${int(MC_TAPE_USD)}) "
                f"dips={len(dips)} trend1h={len(trending_1h)} wallets={len(wallets)} "
                f"(eth_usd={eth_usd} src={eth_src} latest={latest})"
            )
            return {
                "ok": True,
                "logs": len(logs),
                "indexed": indexed_n,
                "shown": len(shown_rows),
                "migrated": len(migrated),
                "about": len(about),
                "dips": len(dips),
                "trending": len(trending_1h),
                "wallets": len(wallets),
                "latest": latest,
                "eth_usd": eth_usd,
                "eth_usd_src": eth_src,
            }
        except Exception as e:
            _set_scan_error(str(e))
            print(f"[indexer] failed: {e}")
            return {"ok": False, "error": str(e), "indexed": 0, "logs": 0, "shown": 0}


def run_scan(kind: str) -> dict:
    kind = (kind or "").lower().strip()
    if kind not in ("dip", "wallets"):
        return {"ok": False, "error": "kind must be dip or wallets"}
    now = fmt_now()
    result = index_launches()
    n = int(result.get("shown") or result.get("indexed") or 0)
    with _lock:
        if kind == "wallets":
            STATE["scan"]["wallets"] = now
            STATE["wallet_count"] = len(STATE["wallets"])
        elif kind == "dip":
            STATE["scan"]["dip"] = now
        STATE["updated_at"] = now
        if not result.get("ok"):
            STATE["scan"]["error"] = result.get("error")
    persist_cache()
    shown = result.get("shown")
    indexed = result.get("indexed")
    msg = (
        f"indexed {indexed} launches, {result.get('migrated') or 0} migrated / "
        f"{result.get('about') or 0} about-to (>=${int(MC_TAPE_USD)}), "
        f"{result.get('dips') or 0} dips, {result.get('wallets') or 0} deployer wallets"
    )
    if kind == "wallets":
        msg = f"wallets: {result.get('wallets') or 0} tracked deployers (research only); " + msg
    if kind == "dip":
        msg = f"dips: {result.get('dips') or 0} (chg<=-20%); " + msg
    if not result.get("ok") and result.get("error"):
        msg = f"indexed {n} launches ({result['error']})"
    return {
        "ok": bool(result.get("ok")),
        "kind": kind,
        "at": now,
        "queued": False,
        "indexed": indexed,
        "shown": shown,
        "dips": result.get("dips"),
        "wallets": result.get("wallets"),
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
    for t in STATE.get("safe_tape", []) + STATE.get("new_pairs", []) + STATE.get("pairs_migrated", []) + STATE.get("pairs_about", []):
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
        for t in STATE.get("safe_tape", []) + STATE.get("new_pairs", []) + STATE.get("pairs_migrated", []) + STATE.get("pairs_about", []):
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
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".ico": "image/x-icon",
    ".woff2": "font/woff2",
}

IPFS_GATEWAYS = (
    "https://ipfs.io/ipfs/",
    "https://cloudflare-ipfs.com/ipfs/",
    "https://gateway.pinata.cloud/ipfs/",
)


def _ipfs_to_http(u: str) -> str:
    if u.startswith("ipfs://"):
        rest = u[7:]
        if rest.startswith("ipfs/"):
            rest = rest[5:]
        return "https://ipfs.io/ipfs/" + rest
    return u


def img_url_ok(u: str) -> bool:
    try:
        p = urlparse(u)
    except Exception:
        return False
    if p.scheme not in ("http", "https"):
        return False
    host = (p.hostname or "").lower()
    if not host:
        return False
    if host in ("localhost", "127.0.0.1") or host.endswith(".local"):
        return False
    return True


def proxy_image(u: str) -> tuple[bytes, str] | tuple[None, str]:
    u = (u or "").strip()
    if not u:
        return None, "empty"
    u = _ipfs_to_http(unquote(u))
    if u.startswith("ipfs://"):
        u = _ipfs_to_http(u)
    if not img_url_ok(u):
        return None, "url not allowlisted"
    key = hashlib.sha256(u.encode("utf-8")).hexdigest()
    IMG_CACHE.mkdir(parents=True, exist_ok=True)
    meta_p = IMG_CACHE / (key + ".json")
    bin_p = IMG_CACHE / (key + ".bin")
    if bin_p.is_file() and meta_p.is_file():
        try:
            meta = json.loads(meta_p.read_text(encoding="utf-8"))
            return bin_p.read_bytes(), meta.get("ctype") or "image/png"
        except Exception:
            pass
    req = Request(u, headers={"User-Agent": "HOODRADAR/2 (research)", "Accept": "image/*,*/*"})
    try:
        with urlopen(req, timeout=8) as resp:
            ctype = resp.headers.get("Content-Type") or "application/octet-stream"
            data = resp.read(IMG_MAX + 1)
    except Exception as e:
        return None, str(e)
    if len(data) > IMG_MAX:
        return None, "too large"
    if not data:
        return None, "empty body"
    try:
        bin_p.write_bytes(data)
        meta_p.write_text(json.dumps({"ctype": ctype, "u": u}), encoding="utf-8")
    except Exception:
        pass
    return data, ctype



_xfeed_cache = {"at": 0.0, "posts": [], "error": None, "source": None, "handles": []}
XFEED_TTL = 60
NITTER_HOSTS = (
    "https://nitter.net",
    "https://nitter.poast.org",
    "https://nitter.privacydev.net",
    "https://xcancel.com",
)
XFEED_UA = "Mozilla/5.0 (compatible; HOODRADAR/2; +https://github.com/YAN-XBT/HOODRADAR)"


def http_bytes(url: str, timeout: int = 12) -> bytes:
    req = Request(url, headers={"User-Agent": XFEED_UA, "Accept": "application/rss+xml, application/xml, text/xml, */*"})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _strip_html(s: str) -> str:
    s = unescape(s or "")
    s = re.sub(r"(?is)<br\s*/?>", "\n", s)
    s = re.sub(r"(?is)<img[^>]*>", "", s)
    s = re.sub(r"(?is)</p>", "\n", s)
    s = re.sub(r"(?is)<[^>]+>", "", s)
    return re.sub(r"\n{3,}", "\n\n", s).strip()


def _rss_ns(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def parse_rss_items(xml_bytes: bytes, handle: str) -> list:
    root = ET.fromstring(xml_bytes)
    items = []
    channel_title = ""
    for el in root.iter():
        if _rss_ns(el.tag) == "title" and not channel_title:
            channel_title = (el.text or "").strip()
            break
    display = channel_title.split("/")[0].strip() if channel_title else handle
    for item in root.iter():
        if _rss_ns(item.tag) != "item":
            continue
        title = desc = link = guid = pub = media = ""
        for child in list(item):
            n = _rss_ns(child.tag)
            if n == "title" and child.text:
                title = child.text
            elif n in ("description", "content") and (child.text or list(child)):
                raw = child.text or ""
                if not raw and list(child):
                    raw = "".join(ET.tostring(c, encoding="unicode") for c in list(child))
                desc = raw
            elif n == "link" and (child.text or child.get("href")):
                link = (child.text or child.get("href") or "").strip()
            elif n == "guid" and child.text:
                guid = child.text.strip()
            elif n in ("pubDate", "published", "date") and child.text:
                pub = child.text.strip()
            elif n in ("content", "thumbnail") and child.get("url"):
                media = child.get("url")
            elif n == "enclosure" and (child.get("url") or "") and "image" in (child.get("type") or "image"):
                media = child.get("url")
        # media from html
        blob = desc or title or ""
        if not media:
            m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', blob, re.I)
            if m:
                media = m.group(1)
        text = _strip_html(desc or title)
        if title and title.strip() and title.strip() not in text:
            # nitter often puts tweet in description; skip duplicate titles like "handle: ..."
            pass
        ts = 0.0
        iso = None
        if pub:
            try:
                dt = parsedate_to_datetime(pub)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                ts = dt.timestamp()
                iso = dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            except Exception:
                try:
                    dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
                    ts = dt.timestamp()
                    iso = dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                except Exception:
                    ts = 0.0
        status_id = None
        for cand in (link, guid):
            m = re.search(r"/status(?:es)?/(\d+)", cand or "")
            if m:
                status_id = m.group(1)
                break
        href = f"https://x.com/{handle}/status/{status_id}" if status_id else f"https://x.com/{handle}"
        if not text:
            continue
        items.append({
            "handle": handle,
            "name": display or handle,
            "text": text,
            "ts": ts,
            "iso": iso,
            "id": status_id,
            "url": href,
            "media": media or None,
        })
    return items


def _fetch_handle_rss(handle: str) -> tuple[list, str | None]:
    urls = [f"{h}/{handle}/rss" for h in NITTER_HOSTS]
    urls.append(f"https://rsshub.app/twitter/user/{handle}")
    urls.append(f"https://rsshub.app/twitter/user/{handle}/")
    last_err = None
    for url in urls:
        try:
            raw = http_bytes(url, timeout=10)
            if not raw or len(raw) < 80:
                last_err = f"empty {url}"
                continue
            low = raw[:200].lower()
            if b"<rss" not in low and b"<feed" not in low and b"xml" not in low:
                last_err = f"not rss {url}"
                continue
            items = parse_rss_items(raw, handle)
            if items:
                return items, url
            last_err = f"no items {url}"
        except Exception as e:
            last_err = f"{url}: {e}"
            continue
    return [], last_err


def get_x_feed(force: bool = False) -> dict:
    now = time.time()
    with _lock:
        cached_ok = (now - _xfeed_cache["at"]) < XFEED_TTL and _xfeed_cache["at"] > 0
        if cached_ok and not force:
            return {
                "posts": list(_xfeed_cache["posts"]),
                "error": _xfeed_cache["error"],
                "source": _xfeed_cache["source"],
                "handles": list(_xfeed_cache["handles"]),
                "cached": True,
            }
        xw = load_json(CONFIG / "x-watch.json", {"allowlist": []})
        handles = [h.strip().lstrip("@") for h in xw.get("allowlist", []) if h and str(h).strip()]
    merged = []
    sources = []
    errors = []
    for h in handles:
        items, src = _fetch_handle_rss(h)
        if items:
            merged.extend(items)
            sources.append(src)
        elif src:
            errors.append(f"{h}: {src}")
    merged.sort(key=lambda p: p.get("ts") or 0, reverse=True)
    posts = merged[:40]
    err = None
    source = None
    if posts:
        # unique hosts that worked
        hosts = []
        for s in sources:
            try:
                hosts.append(urlparse(s).netloc + urlparse(s).path.split("/twitter")[0][:24])
            except Exception:
                hosts.append(s)
        source = ", ".join(dict.fromkeys(hosts))
    else:
        err = "X feed unreachable (no API key)"
    with _lock:
        _xfeed_cache.update({"at": now, "posts": posts, "error": err, "source": source, "handles": handles})
        STATE["x_feed"] = posts
        STATE["x_feed_error"] = err
        STATE["x_feed_source"] = source
        STATE["x_watch"] = [{"handle": h, "status": "allow"} for h in handles]
    return {"posts": posts, "error": err, "source": source, "handles": handles, "cached": False}



GMGN_HOST = "https://openapi.gmgn.ai"
GMGN_WIN_CFG = Path(r"C:\Users\DEPUTAT\Desktop\HOODRADAR\config\gmgn.json")
_gmgn_cache = {}  # interval -> {at, rows, error}


def load_gmgn_key() -> str | None:
    k = (os.environ.get("GMGN_API_KEY") or "").strip()
    if k:
        return k
    for path in (CONFIG / "gmgn.json", GMGN_WIN_CFG):
        try:
            blob = json.loads(Path(path).read_text(encoding="utf-8"))
            k = (blob.get("apiKey") or blob.get("api_key") or blob.get("key") or "").strip()
            if k:
                return k
        except Exception:
            continue
    return None


def _gmgn_num(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except Exception:
        return None


def map_gmgn_rank(item: dict) -> dict:
    tw = item.get("twitter") or item.get("twitter_username") or item.get("twitter_name") or ""
    if isinstance(tw, dict):
        tw = tw.get("username") or tw.get("url") or ""
    logo = item.get("logo") or item.get("logo_url") or item.get("image") or ""
    chg = item.get("price_change_percent")
    if chg is None:
        chg = item.get("price_change") or item.get("price_change_percent1h")
    chg = _gmgn_num(chg)
    # some payloads use 0-1 fraction
    if chg is not None and abs(chg) <= 1.5 and item.get("price_change_percent") is None:
        pass
    created = item.get("creation_timestamp") or item.get("created_timestamp") or item.get("open_timestamp")
    age = None
    if created:
        try:
            ts = int(created)
            if ts > 10_000_000_000:
                ts //= 1000
            sec = max(0, int(time.time()) - ts)
            if sec < 90:
                age = f"{sec}s"
            elif sec < 3600:
                age = f"{sec // 60}m"
            elif sec < 86400:
                age = f"{sec // 3600}h"
            else:
                age = f"{sec // 86400}d"
        except Exception:
            age = None
    socials = {}
    if tw:
        socials["twitter"] = str(tw)
    return {
        "sym": item.get("symbol") or item.get("token_symbol") or "?",
        "name": item.get("name") or item.get("token_name") or "",
        "addr": item.get("address") or item.get("token_address") or "",
        "logo": logo,
        "mc": _gmgn_num(item.get("market_cap") if item.get("market_cap") is not None else item.get("usd_market_cap")),
        "ath_mc": _gmgn_num(item.get("history_highest_market_cap") or item.get("ath_market_cap")),
        "liq": _gmgn_num(item.get("liquidity")),
        "vol": _gmgn_num(item.get("volume") if item.get("volume") is not None else item.get("volume_usd")),
        "swaps": int(_gmgn_num(item.get("swaps")) or 0),
        "buys": int(_gmgn_num(item.get("buys")) or 0) if item.get("buys") is not None else None,
        "sells": int(_gmgn_num(item.get("sells")) or 0) if item.get("sells") is not None else None,
        "holders": int(_gmgn_num(item.get("holder_count") if item.get("holder_count") is not None else item.get("holder")) or 0) if (item.get("holder_count") is not None or item.get("holder") is not None) else None,
        "chg": chg,
        "age": age,
        "socials": socials,
        "twitter": str(tw) if tw else None,
        "source": "gmgn",
    }


def fetch_gmgn_rank(interval: str = "1m") -> dict:
    interval = (interval or "1m").lower().strip()
    if interval not in ("1m", "5m", "1h", "6h", "24h"):
        interval = "1m"
    now = time.time()
    cached = _gmgn_cache.get(interval)
    if cached and now - cached["at"] < 12:
        return cached
    key = load_gmgn_key()
    if not key:
        out = {"at": now, "rows": [], "error": "set GMGN_API_KEY", "interval": interval, "source": None}
        _gmgn_cache[interval] = out
        return out
    last_err = None
    rows = []
    for order_by in ("swaps", "volume"):
        ts = int(time.time())
        cid = str(uuid.uuid4())
        q = (
            f"chain=robinhood&interval={quote(interval)}&limit=50"
            f"&order_by={order_by}&direction=desc&timestamp={ts}&client_id={quote(cid)}"
        )
        url = f"{GMGN_HOST}/v1/market/rank?{q}"
        req = Request(
            url,
            headers={
                "X-APIKEY": key,
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "HOODRADAR/2 (research)",
            },
        )
        try:
            with urlopen(req, timeout=12) as resp:
                raw = resp.read().decode("utf-8")
            envelope = json.loads(raw)
        except Exception as e:
            last_err = str(e)
            continue
        if not isinstance(envelope, dict):
            last_err = "unexpected payload"
            continue
        if envelope.get("code") not in (0, "0", None) and envelope.get("data") is None:
            last_err = envelope.get("error") or envelope.get("message") or f"gmgn code {envelope.get('code')}"
            continue
        data = envelope.get("data") if "data" in envelope else envelope
        rank = []
        if isinstance(data, dict):
            rank = data.get("rank") or data.get("ranks") or data.get("list") or []
        elif isinstance(data, list):
            rank = data
        if not rank:
            last_err = last_err or f"empty rank order_by={order_by}"
            continue
        rows = [map_gmgn_rank(it) for it in rank if isinstance(it, dict)]
        out = {"at": now, "rows": rows, "error": None, "interval": interval, "source": f"gmgn {order_by}"}
        _gmgn_cache[interval] = out
        return out
    out = {"at": now, "rows": [], "error": last_err or "GMGN rank empty", "interval": interval, "source": None}
    _gmgn_cache[interval] = out
    return out


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
        if path == "/api/xfeed":
            feed = get_x_feed(force=False)
            return self._json(200, feed)
        if path == "/api/trending":
            qs = parse_qs(parsed.query)
            interval = (qs.get("interval") or ["1m"])[0]
            data = fetch_gmgn_rank(str(interval))
            return self._json(200, {
                "interval": data.get("interval"),
                "rows": data.get("rows") or [],
                "error": data.get("error"),
                "source": data.get("source"),
                "updated_at": fmt_now(),
            })
        if path == "/api/img":
            qs = parse_qs(parsed.query)
            u = (qs.get("u") or [""])[0]
            data, ctype = proxy_image(u)
            if data is None:
                self.send_error(404, ctype)
                return
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "public, max-age=3600")
            self.end_headers()
            self.wfile.write(data)
            return
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
    threading.Thread(target=lambda: get_x_feed(force=True), name="x-feed", daemon=True).start()
    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"  http://127.0.0.1:{PORT}/")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.shutdown()


if __name__ == "__main__":
    main()
