# Hermes Agent setup — copy hoodradar into your agent

Goal: a user opens **your GitHub**, clones **hoodradar**, and runs the same research desk inside **their** Hermes Agent — with **their** API keys only.

---

## Architecture (recommended)

```text
Hermes profile:  hoodradar   (or rh-meme-desk)
  SOUL.md        ← chain lock + commands (from this repo)
  .env           ← BIRDEYE=... only on their machine
  skills/        ← optional skill text pointing at scripts
  workspace/ or /path/to/hoodradar  ← this git clone

OS user runs:
  gmgn-cli config   → ~/.config/gmgn/  (same user as Hermes)
```

---

## Path A — Fastest (CLI inside Hermes)

### 1. Clone on the Hermes machine

```bash
# example durable path
mkdir -p /opt/data/src
cd /opt/data/src
git clone https://github.com/YAN-XBT/HOODRADAR.git
cd hoodradar
chmod +x install.sh && ./install.sh
```

### 2. Keys (private)

```bash
# Birdeye
cp .env.example .env
nano .env   # BIRDEYE=...

# GMGN
source tools/env.sh
gmgn-cli config
gmgn-cli config --apply 'gmgn_...'
gmgn-cli config --check
```

Details: [API_KEYS.md](./API_KEYS.md)

### 3. Create / use a Hermes profile

```bash
# name is up to you
hermes profile create hoodradar   # if your CLI supports it
# or use Portal / existing profile
```

Copy soul:

```bash
# Adjust paths to your Hermes layout
cp /opt/data/src/hoodradar/hermes/SOUL.md \
   ~/.hermes/profiles/hoodradar/SOUL.md
# On Nous hosted profiles, path is often:
# /opt/data/profiles/hoodradar/SOUL.md
```

Optional: put Birdeye in **profile** env:

```bash
# /opt/data/profiles/hoodradar/.env
BIRDEYE=...
```

And point scripts at the clone:

```bash
# in profile env or shell
export RH_DESK_ROOT=/opt/data/src/hoodradar
export PATH="/opt/data/src/hoodradar/tools/node_modules/.bin:$PATH"
```

### 4. Smoke from Hermes chat

Tell the agent:

> Run buy-the-dip RH 1h top 10 min-drop 20. Use RH_DESK_ROOT=/opt/data/src/hoodradar and source tools/env.sh.

Or:

> Scan Robinhood high-PnL wallet buys last 15 minutes, mcap ≤ 200k, drop honeypots. Full CAs only.

Agent should run:

```bash
source /opt/data/src/hoodradar/tools/env.sh
export RH_DESK_ROOT=/opt/data/src/hoodradar
python3 $RH_DESK_ROOT/scripts/buy_the_dip.py --interval 1h --top 10
python3 $RH_DESK_ROOT/scripts/rh_smart_buys.py --minutes 15 --max-mcap 200000 --top 12
```

---

## Path B — Drop-in profile kit (from this repo)

This repo includes:

```text
hermes/
  SOUL.md           # paste into profile SOUL
  skill-SKILL.md    # optional skill body
  cron-buy-the-dip.md   # cron prompt template
  cron-smart-buys.md
```

### Steps

1. Create profile `hoodradar` in Hermes / Portal  
2. Paste `hermes/SOUL.md` into profile SOUL (or replace file)  
3. Clone repo path into SOUL’s documented `RH_DESK_ROOT`  
4. Add API keys only to profile `.env` + `gmgn-cli config`  
5. Create crons using the markdown templates (copy prompt text into Hermes cron UI / `cronjob` tool)  

### Suggested crons

| Job | Schedule (UTC) | Script |
|-----|----------------|--------|
| Buy the dip | `0 7,15 * * *` (≈ 10:00 & 18:00 Riga) | `buy_the_dip` 1h + 24h |
| Smart buys | every 30–60m | `rh_smart_buys --minutes 30` quiet-ish |

Deliver to Telegram home channel. **Never autotrade.**

---

## Chat command cheat-sheet (put in SOUL)

| User says | Agent does |
|-----------|------------|
| `dip` / `buy the dip` | `buy_the_dip.py --interval 1h` (+ optional 24h) |
| `smart buys` / `pnL scan` | `rh_smart_buys.py --minutes 15` |
| `short` | `format_short_alert.py` on latest JSON |
| `board` | `smart_wallet_tracker.py` |

Always:
- chain **robinhood only**
- full CAs
- DYOR footer
- no key printing

---

## What users copy from GitHub vs what they create

| From GitHub (public) | User creates (private) |
|----------------------|-------------------------|
| All scripts | Birdeye API key |
| SOUL + skill text | GMGN API key + keypair |
| install.sh + docs | Profile `.env` |
| cron **templates** | Live cron jobs on their Hermes |
| defaults (mcap/liq/drop) | Their Telegram delivery targets |

---

## Troubleshooting on Hermes

| Issue | Fix |
|-------|-----|
| `gmgn-cli: not found` | `source $RH_DESK_ROOT/tools/env.sh` or re-run `install.sh` |
| Birdeye 401 | Profile `.env` missing `BIRDEYE` for the **running** profile |
| Wrong chain data | SOUL must forbid sol/base; scripts hardcode `robinhood` |
| Cron empty output | Normal if no ≥20% large dumps; still send “no setups” |
| Permission on `/opt/data` | Clone under profile workspace the agent can read |

---

## Security for Hermes users

1. Separate profile for trading vs research (this one = research)  
2. GMGN trading disabled  
3. Do not put keys in SOUL.md or skills (env only)  
4. Do not `cat` `.env` into Telegram  

---

## Done checklist

- [ ] Repo cloned on Hermes host  
- [ ] `install.sh` OK  
- [ ] Birdeye + GMGN verified  
- [ ] SOUL installed on profile  
- [ ] Manual `dip` + `smart buys` work in chat  
- [ ] Optional cron delivers to Telegram  
- [ ] `git status` clean of secrets  

Next: [MODULES.md](./MODULES.md) · [INSTALL.md](./INSTALL.md)
