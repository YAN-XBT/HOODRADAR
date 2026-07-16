# Cron template — Buy the Dip (2×/day)

**Schedule (UTC):** `0 7,15 * * *`  
(~10:00 and 18:00 Europe/Riga in summer)

**Name:** `hoodradar buy-the-dip`

**Prompt (paste into Hermes cron):**

```text
You are hoodradar (Robinhood Chain research only).

1) Ensure PATH includes $RH_DESK_ROOT/tools/node_modules/.bin
   Default RH_DESK_ROOT=/opt/data/src/hoodradar (or the path in profile SOUL).

2) Run:
source "$RH_DESK_ROOT/tools/env.sh" 2>/dev/null || true
export PATH="$RH_DESK_ROOT/tools/node_modules/.bin:$PATH"
python3 "$RH_DESK_ROOT/scripts/buy_the_dip.py" --interval 1h --top 10 --min-drop 20 --min-mcap 50000 --min-liq 15000 --json-out "$RH_DESK_ROOT/cron/cache/buy_the_dip.json" --brief-out "$RH_DESK_ROOT/cron/cache/buy_the_dip_brief.txt"
python3 "$RH_DESK_ROOT/scripts/buy_the_dip.py" --interval 24h --top 10 --min-drop 20 --min-mcap 50000 --min-liq 15000 --json-out "$RH_DESK_ROOT/cron/cache/buy_the_dip_24h.json" --brief-out "$RH_DESK_ROOT/cron/cache/buy_the_dip_24h_brief.txt"
python3 "$RH_DESK_ROOT/scripts/format_short_alert.py" "$RH_DESK_ROOT/cron/cache/buy_the_dip.json" --max 5

3) Deliver to Telegram: short alert first, then note 24h brief path or include 24h hits.
Full CAs only. DYOR. Not financial advice. No trading. Never print API keys.
```

**Deliver:** origin / Telegram home  
**Tools:** terminal, file
