## Local web dashboard

**File:** `scripts/dashboard_server.py` + `web/`  

Optional localhost board (3-col Home: traders · Hot Search · Dip · tabs for full reports).  
Plain HTML/CSS/JS — **reshape with Hermes** (no black-box SaaS).  

```bash
python3 scripts/dashboard_server.py
# http://127.0.0.1:8787
```

See [LOCAL_DASHBOARD.md](./LOCAL_DASHBOARD.md).

---

## Hot Search (GMGN)

**Script:** `scripts/hot_search.py`

```bash
gmgn-cli market hot-searches --chain robinhood --interval 24h --limit 30 --raw
# or
python3 scripts/hot_search.py --limit 30
```

UI twin of https://gmgn.ai/trend?chain=robinhood&tab=hotsearch

Research only — search popularity ≠ quality.

# MODULES — full product map (hoodradar)

Each module is a **small script with one job**.  
Chain lock: **Robinhood only**. Mode: **research only**.

---

## 1. Buy the Dip  
**File:** `scripts/buy_the_dip.py`  
**Status:** Core · cron-friendly  

### Why it exists
You want a dead-simple rule:  
*“Among the top 10 trending RH tokens, which **large** names just **dumped ≥ 20%**?”*

### Data source
- GMGN `market trending --chain robinhood`  
- Same family as https://gmgn.ai/trend?chain=robinhood  

### Rules (defaults)
| Rule | Default |
|------|---------|
| Top N | 10 |
| Min dump | **20%** (hard floor in code) |
| Min market cap | $50,000 |
| Min liquidity | $15,000 |
| Interval | `1h` or `24h` |
| Honeypot / Unsafe | dropped |

### Outputs
- Terminal brief  
- `cron/cache/buy_the_dip.json`  
- `cron/cache/buy_the_dip_brief.txt`  

### Example

```bash
python3 scripts/buy_the_dip.py --interval 1h --top 10 --min-drop 20
```

### For Hermes
User: `dip` / `buy the dip`  
Cron: 2×/day (see `hermes/cron-buy-the-dip.md`)

---

## 2. Smart Buys (high-PnL wallet tape)  
**File:** `scripts/rh_smart_buys.py`  
**Status:** Core  

### Why it exists
Follow **wallets that are green on PnL** (Birdeye), see what they bought recently, filter garbage with GMGN security, explain *why* in a card format.

### Data source
- Birdeye `/trader/gainers-losers` + `/trader/txs/seek_by_time` (`x-chain: robinhood`)  
- GMGN `token info` + `token security`  

### Rules (defaults)
| Rule | Default |
|------|---------|
| Window | last 15 minutes |
| Top wallets | 12 |
| Max mcap | $200,000 (low-cap hunt; raise if you want) |
| Min buy USD | $20 |
| Honeypot / Unsafe | **dropped** (unless `--include-unsafe`) |

### Honest naming
These are **high-PnL wallets**, not automatically “KOLs”.  
GMGN `track kol` **does not support robinhood**.

### Outputs
- Card brief: token story, who bought, wallet PnL, full CA, links  
- `DROPPED AS UNSAFE / HONEYPOT` section  

### Example

```bash
python3 scripts/rh_smart_buys.py --minutes 15 --max-mcap 200000 --top 12
```

---

## 3. Wallet Board  
**File:** `scripts/smart_wallet_tracker.py`  
**Status:** Core building block  

### Why it exists
Raw **leaderboard** of PnL wallets + sample buys — for debugging and article screenshots before filters.

### Use when
- Teaching how Birdeye gainers look  
- Building a watchlist of addresses  

### Example

```bash
python3 scripts/smart_wallet_tracker.py --chain robinhood --window 1W --top 10
```

---

## 4. Short Alert formatter  
**File:** `scripts/format_short_alert.py`  
**Status:** Core UX  

### Why it exists
Long research briefs are great for analysis; Telegram needs **short** copy.

### Example

```bash
python3 scripts/format_short_alert.py cron/cache/buy_the_dip.json --max 3
python3 scripts/format_short_alert.py cron/cache/rh_scan_safe.json --max 3
```

---

## 5. Birdeye client  
**File:** `scripts/birdeye_client.py`  
**Status:** Library  

### Why it exists
One place for:
- loading `BIRDEYE` from `.env`  
- setting `x-chain: robinhood`  
- basic GET helper  

Not run alone in production demos.

---

## 6. Optional: X / lore helpers  
**Files:** `extract_cas.py`, `lore_match.py`, `kol_overlap.py`  
**Status:** Bonus / experimental  

### Why they exist
Article chapter two: “wire social heat later.”  
**Not required** for Buy the Dip or Smart Buys.

Label them **prototype** if you show them publicly.

---

## 7. Hermes packaging  
**Folder:** `hermes/`  

| File | Purpose |
|------|---------|
| `SOUL.md` | Profile brain: RH lock, commands, safety |
| `skill-SKILL.md` | Optional skill body for Hermes skills |
| `cron-buy-the-dip.md` | Cron prompt template |
| `cron-smart-buys.md` | Cron prompt template |

---

## What is intentionally missing

| Missing | Reason |
|---------|--------|
| Autotrade / swap key | Liability + product scope |
| SOL KOL track as RH | Dishonest |
| Hosted multi-tenant SaaS | This is DIY |
| “Signal” branding | Research briefs only |

---

## Suggested demo order (for your article)

1. Buy the Dip (1h)  
2. Buy the Dip (24h)  
3. Smart Buys + show honeypot **DROPPED**  
4. Short alert  
5. Hermes cron screenshot  

---

## Config cheat-sheet

| Goal | Flags |
|------|--------|
| Stricter “large” dips | `--min-mcap 200000 --min-liq 50000` |
| Faster tape | `--minutes 5 --top 8` |
| Blue-chip dumps only | raise min-mcap/liq on buy_the_dip |
| Debug traps | `rh_smart_buys.py --include-unsafe` (never for public “hits”) |
