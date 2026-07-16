---
name: hoodradar
description: Robinhood Chain research desk — buy-the-dip, high-PnL wallet buys, honeypot filter. RH only, research only.
---

# hoodradar skill

Use when the user wants Robinhood Chain research: dumps on trend, high-PnL wallet buys, or Hermes setup of this desk.

## Prerequisites
- `RH_DESK_ROOT` points at the hoodradar clone
- `source $RH_DESK_ROOT/tools/env.sh`
- Birdeye in `.env`; GMGN via `gmgn-cli config --check`

## Run buy-the-dip
```bash
python3 "$RH_DESK_ROOT/scripts/buy_the_dip.py" --interval 1h --top 10 --min-drop 20 --min-mcap 50000 --min-liq 15000
```

## Run smart buys
```bash
python3 "$RH_DESK_ROOT/scripts/rh_smart_buys.py" --minutes 15 --max-mcap 200000 --top 12
```

## Short alert
```bash
python3 "$RH_DESK_ROOT/scripts/format_short_alert.py" "$RH_DESK_ROOT/cron/cache/buy_the_dip.json"
```

## Rules
- RH only; full CAs; no key dumps; DYOR footer; honeypots not recommended
