# Hermes setup — hoodradar (PRIMARY GUIDE)

**Product assumption:** users install this **into Hermes Agent**, not as a random Python toy.

Supported hosts:

| Host | Notes |
|------|--------|
| **Nous Portal** (hosted VPS / agent) | [portal.nousresearch.com](https://portal.nousresearch.com) |
| **Hermes Desktop** | Local app; clone into a workspace Hermes can read |
| **Hermes CLI** | `hermes setup`, profiles, gateway on your machine |

Official Hermes docs: https://hermes-agent.nousresearch.com/docs/

---

## A. Install Hermes (if needed)

### Recommended — Nous Portal OAuth

```bash
hermes setup --portal
```

One flow: login → model provider → Tool Gateway (web, image, TTS, browser on paid Portal).

Guide: https://hermes-agent.nousresearch.com/docs/guides/run-hermes-with-nous-portal  
Portal: https://portal.nousresearch.com/manage-subscription  

### Desktop

Install Hermes Desktop from Nous / project docs, complete onboarding, ensure **terminal tools** work in chat.

### CLI only

```bash
# see upstream README
# https://github.com/nousresearch/hermes-agent
hermes setup
hermes model          # pick Nous Portal or other provider
```

---

## B. Telegram gateway (alerts on your phone)

hoodradar does **not** implement Telegram itself. Hermes does.

### Official docs

- https://hermes-agent.nousresearch.com/docs/user-guide/messaging/telegram  
- https://hermes-agent.nousresearch.com/docs/user-guide/messaging/  

### Commands (typical)

```bash
hermes gateway setup     # interactive: Telegram bot token, allowlist, etc.
hermes gateway           # run gateway (foreground)
# production: enable gateway service as in Hermes docs for your host
```

### You need

1. Telegram bot token from **@BotFather**  
2. Your user id allowed to talk to the bot (Hermes pairing / allowlist)  
3. Gateway **running** on the same environment as the hoodradar profile  
4. Cron `deliver` → your Telegram chat / home channel  

**Portal users:** messaging is often configured in Portal / profile UI — still the same idea (bot token + gateway).

---

## C. Install hoodradar into Hermes

### 1) Clone where the agent can execute files

**Portal / Linux agent example:**

```bash
mkdir -p /opt/data/src
cd /opt/data/src
git clone https://github.com/YAN-XBT/HOODRADAR.git
cd HOODRADAR
chmod +x install.sh && ./install.sh
```

**Desktop:** clone under the workspace folder Hermes uses (check Desktop docs / project root).

`install.sh` installs local `gmgn-cli` + creates `.env.example` → `.env`.

### 2) API keys (never commit)

See [API_KEYS.md](./API_KEYS.md).

```bash
# Birdeye → .env in project OR Hermes profile .env
echo 'BIRDEYE=your_key' >> .env

# GMGN
source tools/env.sh
gmgn-cli config
gmgn-cli config --apply 'gmgn_YOUR_KEY'
gmgn-cli config --check
```

Prefer GMGN **trading disabled**.

### 3) Profile SOUL

1. Create profile e.g. `hoodradar` (Portal UI / `hermes profile` / Desktop profiles)  
2. Copy [../hermes/SOUL.md](../hermes/SOUL.md) → that profile’s `SOUL.md`  
3. Edit `RH_DESK_ROOT` to your clone path  

```bash
export RH_DESK_ROOT=/opt/data/src/HOODRADAR
export PATH="$RH_DESK_ROOT/tools/node_modules/.bin:$PATH"
```

Put the same exports in profile env if your host supports profile `.env`.

### 4) Optional skill

Copy [../hermes/skill-SKILL.md](../hermes/skill-SKILL.md) to:

```text
~/.hermes/profiles/<profile>/skills/hoodradar/SKILL.md
# or Portal equivalent skills path
```

### 5) Smoke in Telegram chat

```text
Run buy the dip RH 1h top 10
```

or short commands from SOUL: `dip` · `smart buys` · `short`

Agent should run:

```bash
source "$RH_DESK_ROOT/tools/env.sh"
python3 "$RH_DESK_ROOT/scripts/buy_the_dip.py" --interval 1h --top 10
python3 "$RH_DESK_ROOT/scripts/rh_smart_buys.py" --minutes 15 --top 8
python3 "$RH_DESK_ROOT/scripts/format_short_alert.py" "$RH_DESK_ROOT/cron/cache/buy_the_dip.json"
```

---

## D. Cron inside Hermes

Use Hermes **cron** (not system cron only) so delivery hits Telegram.

| Job | Template | Schedule idea (UTC) |
|-----|----------|---------------------|
| Buy the dip | [../hermes/cron-buy-the-dip.md](../hermes/cron-buy-the-dip.md) | `0 7,15 * * *` |
| Smart buys | [../hermes/cron-smart-buys.md](../hermes/cron-smart-buys.md) | `0 * * * *` or `*/30 * * * *` |

In cron UI / tool:

- Paste the **prompt** from the template  
- Enable **terminal** (+ file) tools  
- Deliver to **origin** or your Telegram home  
- Set `RH_DESK_ROOT` correctly in the prompt  

---

## E. Portal vs Desktop vs CLI checklist

| Step | Portal | Desktop | CLI |
|------|--------|---------|-----|
| Hermes running | Hosted instance | App open | `hermes gateway` / session |
| Clone HOODRADAR | SSH/terminal on instance | Local disk workspace | Local disk |
| `./install.sh` | Yes | Yes (or WSL) | Yes |
| Keys | Profile/project `.env` + gmgn-cli | Same | Same |
| SOUL | Profile editor / file | Profile file | `~/.hermes/profiles/...` |
| Telegram | Gateway / Portal messaging | `hermes gateway setup` | `hermes gateway setup` |
| Cron | Portal/agent cron | Agent cron | Agent cron |

---

## F. Troubleshooting (Hermes-specific)

| Issue | Fix |
|-------|-----|
| Agent can’t find scripts | Wrong `RH_DESK_ROOT`; re-check path in SOUL |
| `gmgn-cli: not found` | `source $RH_DESK_ROOT/tools/env.sh` or re-run `install.sh` |
| Birdeye 401 | `BIRDEYE` missing in **this** profile’s env |
| No Telegram replies | Gateway not running / bot token / user not allowlisted — see Telegram docs |
| Cron silent | Check deliver target; empty dip window is normal |
| Wrong chain data | SOUL chain lock; never install SOL KOL feeds as RH |

---

## G. Security

- Research profile ≠ trading profile  
- No swap private keys in hoodradar  
- Never paste keys into Telegram  
- Don’t commit `.env` or `~/.config/gmgn/keypair.pem`  

---

## H. Done when

- [ ] Hermes chat can run `dip` and return a brief  
- [ ] Honeypots land under DROPPED when present  
- [ ] Full CAs copyable  
- [ ] Telegram receives agent messages (gateway OK)  
- [ ] Optional: cron fired once with a test run  

Next: [MODULES.md](./MODULES.md) · [API_KEYS.md](./API_KEYS.md)
