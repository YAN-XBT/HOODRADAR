# Cron template — Smart Buys (periodic)

**Schedule example:** every 60 minutes → `0 * * * *`  
Or every 30 minutes → `*/30 * * * *`

**Name:** `hoodradar smart-buys`

**Prompt:**

```text
You are hoodradar (Robinhood Chain research only).

source "$RH_DESK_ROOT/tools/env.sh" 2>/dev/null || true
export PATH="$RH_DESK_ROOT/tools/node_modules/.bin:$PATH"
export RH_DESK_ROOT="${RH_DESK_ROOT:-/opt/data/src/hoodradar}"

python3 "$RH_DESK_ROOT/scripts/rh_smart_buys.py" \
  --minutes 30 --max-mcap 200000 --top 12 --min-buy-usd 20 \
  --json-out "$RH_DESK_ROOT/cron/cache/rh_smart_buys.json" \
  --brief-out "$RH_DESK_ROOT/cron/cache/rh_smart_buys_brief.txt"

python3 "$RH_DESK_ROOT/scripts/format_short_alert.py" \
  "$RH_DESK_ROOT/cron/cache/rh_smart_buys.json" --max 5

If safe hits == 0 and dropped unsafe == 0, you may send a one-line "no RH high-PnL buys this window" OR stay quiet if operator prefers silent empty ticks.

Always: full CAs, separate honeypot DROPPED list, DYOR footer, no keys, no trades.
```

**Deliver:** Telegram  
**Tools:** terminal, file
