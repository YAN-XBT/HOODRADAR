# HOODRADAR v2 — local PONS dashboard

Research-only tape for Robinhood Chain / PONS. No trading, no tx buttons.

## Run

```bash
python3 scripts/dashboard_server.py
```

Open http://127.0.0.1:8787/

## Config

- `config/pons.json` — chainId 4663, RPC, v1/v2 factories
- `config/x-watch.json` — X handle allowlist

## API

- `GET /api/state`
- `POST /api/scan` — `{"kind":"dip"}` or `{"kind":"wallets"}`
- `POST /api/agent` — `{"message":"..."}` paste a 0x wallet, 0x token, or `scan all pet coins on pons`.

Header: REFRESH, SCAN WALLETS, RUN DIP, ASK AGENT.
