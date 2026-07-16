# Local web dashboard (localhost UI)

Optional **full** research board on your machine — Telegram stays short.

## Why it exists

Hermes + Telegram is great for alerts.  
The web desk is for the **operator view**: 3-column Home, full CAs, Hot Search, dips, smart buys, wallets.

**You can reshape it with Hermes** — plain `web/` HTML/CSS/JS, no black box.

```text
Ask Hermes:
  denser columns / swap Hot Search with Dip
  hide sparklines on Home
  add mcap filters
```

## Run

```bash
cd /path/to/HOODRADAR
source tools/env.sh   # after install + keys
python3 scripts/dashboard_server.py
```

Open: **http://127.0.0.1:8787**

```bash
HOODRADAR_PORT=8787
HOODRADAR_HOST=127.0.0.1   # keep localhost
```

Windows: `START_DASHBOARD.bat` if you use the dash pack, or:

```powershell
py -3 scripts\dashboard_server.py
```

## Home board

| Column | Source |
|--------|--------|
| **Top traders** | Birdeye RH PnL top 20 |
| **Hot Search** | GMGN `market hot-searches --chain robinhood` |
| **Buy the Dip** | GMGN trending dips ≥20% |

**Tabs:** Hot Search · Buy the Dip · Smart Buys · Wallets (full reports + briefs)

Also:

- Full CAs · GMGN / social / explorer  
- DROPPED honeypots on Smart Buys  
- Optional mini sparklines via `/api/spark` (GMGN kline · cache under `cron/cache/sparks/`)  
- Buttons: Run hot / dip / smart / wallets / all  

## Fill data

1. UI **Run all**, or  
2. Cron / Hermes templates in [CRON_EXAMPLES.md](./CRON_EXAMPLES.md), or  

```bash
bash scripts/run_cron_bundle.sh all
python3 scripts/hot_search.py --limit 30
```

## Architecture

```text
scripts / buttons  →  cron/cache/*.json (+ sparks)
                              ↓
              dashboard_server.py  →  web/ (browser)
```

Hermes Telegram = short path.  
This UI = local operator desk.

## Customize with Hermes

Files:

| Path | Role |
|------|------|
| `scripts/dashboard_server.py` | stdlib server · `/api/state` · `/api/scan` · `/api/spark` |
| `web/index.html` | layout · tabs |
| `web/styles.css` | theme · 3-col Home |
| `web/app.js` | cards · sparklines · buttons |

Point Hermes at this repo path and describe the UI change in plain language.

## Security

- Bind **127.0.0.1** only unless you know what you’re doing  
- Don’t expose port to the internet without auth  
- Research only — no trading from this UI · API keys never dumped to browser  

## Notes on sparklines

Mini charts are **direction hints**, not full TradingView.  
Data = GMGN kline closes (when `gmgn-cli` + key work). Offline cache may ship for demos.
