# API keys — Birdeye + GMGN (you create these yourself)

**Never commit keys. Never paste keys into public GitHub issues.**  
hoodradar only needs **read/query** access. Keep **trading disabled**.

---

## 1. Birdeye (wallet PnL + trades)

### What we use it for
- Top profit / loss wallets on **Robinhood Chain**
- Recent swap history for those wallets  
Scripts: `rh_smart_buys.py`, `smart_wallet_tracker.py`

### How to get a key

1. Open Birdeye docs / dashboard: https://docs.birdeye.so/  
2. Sign up / log in  
3. Create an **API key** (Security / API keys section in the dashboard)  
4. Copy the key **once** into your local `.env` (not into chat, not into git):

```bash
# .env  (gitignored)
BIRDEYE=YOUR_BIRDEYE_KEY_HERE
```

Aliases also work: `BIRDEYE_API_KEY`, `BIRDEYE_KEY`.

### Verify

```bash
source tools/env.sh
python3 - <<'PY'
from pathlib import Path
import sys
sys.path.insert(0, "scripts")
from birdeye_client import load_api_key, request
k = load_api_key(env_file=".env")
r = request(
    "/trader/gainers-losers",
    api_key=k,
    chain="robinhood",
    params={"type": "1W", "sort_by": "PnL", "sort_type": "desc", "offset": 0, "limit": 3},
)
print("ok", r.get("success"), "wallets", len((r.get("data") or {}).get("items") or []))
print("message", (r.get("message") or "")[:120])
PY
```

Expect: `ok True` and `wallets` ≥ 1.

### Limits / tips
- Free tiers may **rate-limit** (HTTP 429). Scripts sleep between wallet calls; raise delay if needed.  
- Always send chain as **`robinhood`** (header `x-chain`).  
- If gainers fail on `today`, try window `1W` (script already falls back in places).

### Security
- Key = full read power on your plan. Rotate if leaked.  
- Do not put Birdeye keys inside Hermes chat history or screenshots.

---

## 2. GMGN (trending + token info + security)

### What we use it for
- RH **trending** top list (buy-the-dip)  
- **Token info** (mcap, socials, age)  
- **Token security** (honeypot / Unsafe banner)  
Scripts: `buy_the_dip.py`, `rh_smart_buys.py`

### Important RH limit
`gmgn-cli track kol` / `track smartmoney` support **sol / bsc / base / eth** — **not robinhood**.  
hoodradar does **not** fake RH KOLs with SOL feeds. On RH we use:
- trending / trenches / token info / security  
- Birdeye for high-PnL wallet tape  

### How to get a key

#### A. Install CLI (done by `./install.sh`)

```bash
source tools/env.sh
gmgn-cli --version   # or: which gmgn-cli
```

#### B. Generate public key + open create link

```bash
gmgn-cli config
```

This prints:
- an **Ed25519 public key** block  
- often a **one-click URL** to https://gmgn.ai/ai  

#### C. Create API key on GMGN

1. Open https://gmgn.ai/ai (or the link from `gmgn-cli config`)  
2. Sign in  
3. **Create API Key** / Generate API  
4. Paste the **public key** from your machine if asked  
5. Prefer **query-only** / **Trading disabled** (research desk)  
6. Copy the API key string (starts like `gmgn_...`)

#### D. Apply key locally

```bash
gmgn-cli config --apply 'gmgn_YOUR_KEY_HERE'
gmgn-cli config --check
```

This writes config under `~/.config/gmgn/` (private key material stays local — **do not commit**).

### Verify

```bash
source tools/env.sh
gmgn-cli config --check
gmgn-cli market trending --chain robinhood --interval 1h --limit 3 --raw | head -c 300
gmgn-cli token security --chain robinhood --address 0x84ae417f04e7feabd92bda7b6654f308633d2d7f --raw
# Example address used in docs for honeypot flag demo — DO NOT BUY
```

### Security
- Keep **trading OFF**.  
- Never commit `~/.config/gmgn/keypair.pem` or `.env`.  
- If key leaks: revoke on gmgn.ai and re-run `gmgn-cli config`.

---

## 3. What goes where

| Secret | Where | In git? |
|--------|--------|---------|
| Birdeye API key | project `.env` → `BIRDEYE=` | **No** |
| GMGN API key | `gmgn-cli config --apply` → `~/.config/gmgn/` | **No** |
| GMGN keypair | `~/.config/gmgn/keypair.pem` | **No** |
| This repo | GitHub public | **Yes** (code only) |

Hermes profile: put Birdeye in **profile `.env`**; run `gmgn-cli config` as the same OS user Hermes uses.

---

## 4. Minimal checklist

- [ ] `BIRDEYE` set in `.env`  
- [ ] Birdeye test returns wallets on `chain=robinhood`  
- [ ] `gmgn-cli config --check` OK  
- [ ] Trending RH returns JSON  
- [ ] Security endpoint returns fields (`is_honeypot`, etc.)  
- [ ] No secrets in `git status`  

Next: [INSTALL.md](./INSTALL.md) · [HERMES_SETUP.md](./HERMES_SETUP.md)
