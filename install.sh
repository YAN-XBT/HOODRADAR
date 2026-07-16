#!/usr/bin/env bash
# install.sh — bootstrap gmgn-cli + .env for hoodradar
# Primary product path: Hermes Agent (Portal / Desktop / CLI). See docs/HERMES_SETUP.md
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "== RH Chain Research Desk · install =="
echo "Root: $ROOT"
echo

# --- Python ---
if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 required"
  exit 1
fi
echo "[ok] python3: $(python3 --version 2>&1)"

# --- Node (for gmgn-cli) ---
if ! command -v npm >/dev/null 2>&1; then
  echo "ERROR: npm/node required to install gmgn-cli"
  echo "Install Node 20+ then re-run."
  exit 1
fi
echo "[ok] npm: $(npm --version 2>&1) · node: $(node --version 2>&1)"

# --- local gmgn-cli ---
mkdir -p tools
if [[ ! -x tools/node_modules/.bin/gmgn-cli ]]; then
  echo "[..] installing gmgn-cli locally into ./tools"
  (
    cd tools
    if [[ ! -f package.json ]]; then
      npm init -y >/dev/null 2>&1 || true
    fi
    npm install gmgn-cli
  )
else
  echo "[ok] gmgn-cli already present"
fi

# PATH helper
cat > tools/env.sh <<'EOF'
#!/usr/bin/env bash
# source tools/env.sh
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PATH="$ROOT/tools/node_modules/.bin:$PATH"
export RH_DESK_ROOT="$ROOT"
EOF
chmod +x tools/env.sh

# --- .env ---
if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "[ok] created .env from .env.example — fill BIRDEYE key"
else
  echo "[ok] .env already exists"
fi

mkdir -p cron/cache secrets

echo
echo "== Next steps =="
echo "1) Edit .env and set BIRDEYE=your_birdeye_key"
echo "2) Create GMGN API key (query only, trading OFF):"
echo "     source tools/env.sh"
echo "     gmgn-cli config          # prints public key + browser link"
echo "     # create key on gmgn.ai/ai , then:"
echo "     gmgn-cli config --apply 'YOUR_GMGN_API_KEY'"
echo "     gmgn-cli config --check"
echo "3) Smoke tests:"
echo "     source tools/env.sh"
echo "     python3 scripts/buy_the_dip.py --interval 1h --top 10"
echo "     python3 scripts/rh_smart_buys.py --minutes 15 --top 8"
echo
echo "Read docs/HERMES_SETUP.md (Hermes + Telegram) and docs/API_KEYS.md before going further."
echo "Hermes docs: https://hermes-agent.nousresearch.com/docs/"
echo "Done."
