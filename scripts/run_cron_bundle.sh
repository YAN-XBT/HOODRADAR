#!/usr/bin/env bash
# run_cron_bundle.sh — dip | smart | all
# Writes cron/cache JSON + briefs for Telegram/Hermes and local dashboard.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
KIND="${1:-all}"

export RH_DESK_ROOT="${RH_DESK_ROOT:-$ROOT}"
export PATH="$ROOT/tools/node_modules/.bin:$PATH"
# shellcheck disable=SC1091
source "$ROOT/tools/env.sh" 2>/dev/null || true
mkdir -p "$ROOT/cron/cache"

echo "[hoodradar] bundle=$KIND root=$ROOT"

run_dip() {
  python3 scripts/buy_the_dip.py --interval 1h --top 10 --min-drop 20 \
    --json-out cron/cache/buy_the_dip.json \
    --brief-out cron/cache/buy_the_dip_brief.txt
  python3 scripts/buy_the_dip.py --interval 24h --top 10 --min-drop 20 \
    --json-out cron/cache/buy_the_dip_24h.json \
    --brief-out cron/cache/buy_the_dip_24h_brief.txt
  python3 scripts/format_short_alert.py cron/cache/buy_the_dip.json --max 5 \
    | tee cron/cache/short_alert_dip.txt || true
}

run_smart() {
  python3 scripts/rh_smart_buys.py --minutes 180 --max-mcap 1000000 --top 15 \
    --json-out cron/cache/rh_smart_buys.json \
    --brief-out cron/cache/rh_smart_buys_brief.txt
}

case "$KIND" in
  dip) run_dip ;;
  smart) run_smart ;;
  all) run_dip; run_smart ;;
  *) echo "usage: $0 dip|smart|all"; exit 1 ;;
esac

echo "[hoodradar] done · cache → $ROOT/cron/cache"
