# Cron examples — hoodradar (customize for yourself)

These are **examples**, not mandatory.  
Product is **Hermes-first**: prefer Hermes cron so delivery hits **Telegram**.  
You can also use system crontab / systemd timer on a VPS.

**Always:**
- Research only — no autotrade  
- Set `RH_DESK_ROOT` to your clone path  
- Never commit keys  
- Empty scans are OK  

Related templates:
- [`hermes/cron-buy-the-dip.md`](../hermes/cron-buy-the-dip.md)
- [`hermes/cron-smart-buys.md`](../hermes/cron-smart-buys.md)
- [`hermes/cron-dashboard-refresh.md`](../hermes/cron-dashboard-refresh.md)

---

## 1) Recommended Hermes cron set

| Job | When (UTC) | What |
|-----|------------|------|
| **Buy the dip** | `0 7,15 * * *` | 1h + 24h dip scans → short alert to Telegram |
| **Smart buys** | `0 * * * *` or `*/30 * * * *` | high-PnL buys + honeypot drop |
| **Dashboard refresh** (optional) | same as above | writes `cron/cache/*` for local web UI |

### How to add in Hermes
1. Open cron / scheduled jobs for your **hoodradar** profile  
2. Paste the **prompt** from the matching `hermes/cron-*.md` file  
3. Enable **terminal** (+ file) tools  
4. Deliver → your Telegram home / origin  
5. Change schedule to your timezone preference  

Official Hermes messaging (Telegram delivery depends on gateway):  
https://hermes-agent.nousresearch.com/docs/user-guide/messaging/

---

## 2) Example schedules (pick & edit)

### A. Conservative (low noise)
```cron
# UTC
0 7,15 * * *   buy-the-dip (1h + 24h)
0 */2 * * *    smart-buys every 2 hours
```

### B. Active desk
```cron
0 7,12,17 * * *   buy-the-dip 3×/day
*/30 * * * *      smart-buys every 30m
```

### C. Night quiet (example Europe)
```cron
# Run less overnight local time — convert to UTC yourself
0 6,14 * * *   dip
0 8-22/2 * * * smart-buys only 08–22 local → adjust UTC
```

**You must customize** hours for your sleep / market hours. These are not financial recommendations.

---

## 3) Shell one-shots (what cron actually runs)

Set once:
```bash
export RH_DESK_ROOT=/path/to/HOODRADAR
export PATH="$RH_DESK_ROOT/tools/node_modules/.bin:$PATH"
source "$RH_DESK_ROOT/tools/env.sh"
mkdir -p "$RH_DESK_ROOT/cron/cache"
```

### Buy the dip
```bash
python3 "$RH_DESK_ROOT/scripts/buy_the_dip.py" \
  --interval 1h --top 10 --min-drop 20 \
  --json-out "$RH_DESK_ROOT/cron/cache/buy_the_dip.json" \
  --brief-out "$RH_DESK_ROOT/cron/cache/buy_the_dip_brief.txt"

python3 "$RH_DESK_ROOT/scripts/buy_the_dip.py" \
  --interval 24h --top 10 --min-drop 20 \
  --json-out "$RH_DESK_ROOT/cron/cache/buy_the_dip_24h.json" \
  --brief-out "$RH_DESK_ROOT/cron/cache/buy_the_dip_24h_brief.txt"

python3 "$RH_DESK_ROOT/scripts/format_short_alert.py" \
  "$RH_DESK_ROOT/cron/cache/buy_the_dip.json" --max 5
```

### Smart buys
```bash
python3 "$RH_DESK_ROOT/scripts/rh_smart_buys.py" \
  --minutes 180 --max-mcap 1000000 --top 15 \
  --json-out "$RH_DESK_ROOT/cron/cache/rh_smart_buys.json" \
  --brief-out "$RH_DESK_ROOT/cron/cache/rh_smart_buys_brief.txt"
```

Or use the helper:
```bash
bash "$RH_DESK_ROOT/scripts/run_cron_bundle.sh" dip
bash "$RH_DESK_ROOT/scripts/run_cron_bundle.sh" smart
bash "$RH_DESK_ROOT/scripts/run_cron_bundle.sh" all
```

---

## 4) System crontab example (Linux VPS, optional)

```cron
RH_DESK_ROOT=/opt/data/src/HOODRADAR
PATH=/usr/bin:/bin:$RH_DESK_ROOT/tools/node_modules/.bin

0 7,15 * * *  cd $RH_DESK_ROOT && . tools/env.sh && bash scripts/run_cron_bundle.sh dip >> cron/cache/cron_dip.log 2>&1
0 * * * *     cd $RH_DESK_ROOT && . tools/env.sh && bash scripts/run_cron_bundle.sh smart >> cron/cache/cron_smart.log 2>&1
```

System cron does **not** send Telegram unless you pipe into Hermes or another notifier.  
**Preferred:** Hermes cron → Telegram gateway.

---

## 5) Local web desk + cron

Cron writes JSON/briefs into `cron/cache/`.  
Local UI reads that folder:

```bash
python3 scripts/dashboard_server.py
# http://127.0.0.1:8787
```

See [LOCAL_DASHBOARD.md](./LOCAL_DASHBOARD.md).

---

## 6) Customize checklist

- [ ] Change UTC hours to your day  
- [ ] Tighten/loosen `--max-mcap`, `--minutes`, `--min-drop`  
- [ ] Prefer short alert to Telegram; full brief in dashboard  
- [ ] Keep honeypot drop ON (no `--include-unsafe` in production cron)  
- [ ] Log files under `cron/cache/` (gitignored if you add logs)  

---

## 7) What not to cron

- Trading / swaps  
- Dumping API keys into chat  
- SOL KOL trackers as “RH truth”  
- 1-minute hammering (rate limits)

DYOR. Not financial advice.
