# HOODRADAR — full brief for article writing (for Claude / humans)

**Purpose of this file:** source of truth so another writer (e.g. Claude) can produce a long-form article.  
**Do not invent** features, prices, or chains beyond this brief.  
**Date context:** product built/shipped ~July 2026. Re-check live repo if details drift.

---

## 1. One-line product

**HOODRADAR** is an open-source **Robinhood Chain research desk** designed to run **inside Hermes Agent** (Nous Portal, Hermes Desktop, or Hermes CLI): Telegram in → scripts run → research briefs out. Users bring **their own** Birdeye + GMGN API keys. **No autotrade.**

---

## 2. Public links (use exactly)

| What | URL |
|------|-----|
| **GitHub repo** | https://github.com/YAN-XBT/HOODRADAR |
| Clone | `git clone https://github.com/YAN-XBT/HOODRADAR.git` |
| Hermes docs home | https://hermes-agent.nousresearch.com/docs/ |
| Hermes + Nous Portal guide | https://hermes-agent.nousresearch.com/docs/guides/run-hermes-with-nous-portal |
| Hermes Telegram | https://hermes-agent.nousresearch.com/docs/user-guide/messaging/telegram |
| Hermes messaging gateway | https://hermes-agent.nousresearch.com/docs/user-guide/messaging/ |
| Hermes Tool Gateway | https://hermes-agent.nousresearch.com/docs/user-guide/features/tool-gateway |
| Hermes agent source | https://github.com/nousresearch/hermes-agent |
| Nous Portal | https://portal.nousresearch.com |
| Portal subscription | https://portal.nousresearch.com/manage-subscription |
| GMGN RH trend (data UI) | https://gmgn.ai/trend?chain=robinhood |
| GMGN AI / API keys | https://gmgn.ai/ai |
| Birdeye docs | https://docs.birdeye.so/ |

**In-repo docs (after clone):**

| Path | Role |
|------|------|
| `README.md` | Product overview + golden path |
| `docs/QUICKSTART_HERMES.md` | 1-page Hermes install |
| `docs/HERMES_SETUP.md` | **Primary** full Hermes guide |
| `docs/API_KEYS.md` | Birdeye + GMGN key setup |
| `docs/INSTALL.md` | `install.sh` / script bootstrap |
| `docs/MODULES.md` | Module map |
| `DISCLAIMER.md` | Legal / research only |
| `hermes/SOUL.md` | Paste into Hermes profile |
| `hermes/skill-SKILL.md` | Optional skill |
| `hermes/cron-buy-the-dip.md` | Cron template |
| `hermes/cron-smart-buys.md` | Cron template |

---

## 3. Problem the product solves

- Robinhood Chain meme flow is noisy; UIs are heavy.  
- Many “smart money / KOL bot” tutorials assume **Solana** (or other chains).  
- **GMGN `track kol` / `track smartmoney` do not support `robinhood`** (they support sol/bsc/base/eth). Faking RH with SOL feeds is dishonest.  
- Author wanted a **cloneable research workflow inside Hermes Agent**, not a hosted signal service and not autotrade.  
- Need: high-PnL wallet activity on RH + dump detection on large trending names + honeypot filtering + Telegram via Hermes.

---

## 4. What it is / is not

### Is
- Open-source DIY toolkit (MIT)  
- **Hermes-first**: profile SOUL + scripts + optional cron  
- Robinhood Chain **only**  
- Research briefs (human-readable)  
- Uses **user’s** Birdeye + GMGN keys  
- Honeypot / Unsafe filtering via GMGN security  
- Optional Telegram delivery through **Hermes gateway**

### Is not
- Financial advice or “signals product”  
- Autotrade / swap bot  
- Affiliated with Robinhood Markets, Birdeye, GMGN, or Nous Research  
- A multi-chain KOL sniper  
- A SaaS that holds user keys  
- A guarantee of profit or safety  

---

## 5. Architecture (for diagrams)

```text
User (Telegram app)
        ↕
Hermes Messaging Gateway  (hermes gateway setup)
        ↕
Hermes Agent  (profile SOUL = hoodradar)
        → shell: python scripts in RH_DESK_ROOT
        → Birdeye API  (x-chain: robinhood)
        → GMGN via gmgn-cli  (trending, token info, security)
        → brief / short alert back to Telegram
```

**Mental model:** not a separate bot codebase for Telegram — Hermes owns chat; hoodradar owns research scripts + SOUL instructions.

---

## 6. Modules (product inventory)

### 6.1 Buy the Dip — `scripts/buy_the_dip.py` (core)

**Job:** From GMGN Robinhood **trending** (same family as gmgn.ai/trend?chain=robinhood), take **top N** (default 10). Keep tokens that are **large enough** (min market cap + min liquidity). Keep only if price change is a **dump of at least 20%** (hard floor in code: cannot alert below 20%). Drop honeypot / Unsafe. Output human brief + JSON.

**Defaults (typical):**
- `--top 10`
- `--min-drop 20` (mandatory ≥20)
- `--min-mcap 50000` (USD)
- `--min-liq 15000` (USD)
- `--interval 1h` or `24h`

**Why it exists:** Simple, teachable rule: large trending + hard dump.

**Outputs:** terminal brief; `cron/cache/buy_the_dip.json`; `buy_the_dip_brief.txt`

**Example command:**
```bash
python3 scripts/buy_the_dip.py --interval 1h --top 10 --min-drop 20 --min-mcap 50000 --min-liq 15000
```

---

### 6.2 Smart Buys — `scripts/rh_smart_buys.py` (core)

**Job:**
1. Birdeye top PnL wallets on Robinhood (`/trader/gainers-losers`)  
2. Their recent buys (`/trader/txs/seek_by_time`) in last N minutes  
3. Enrich with GMGN token info (mcap, age, socials)  
4. GMGN `token security` → **drop** honeypot / Unsafe / extreme tax  
5. Card-style brief: why token, who bought (wallet PnL), **full CA**, links  

**Defaults (typical):**
- `--minutes 15`
- `--top 12` wallets
- `--max-mcap 200000` (low-cap hunt; user can raise)
- `--min-buy-usd 20`
- Honeypots dropped unless `--include-unsafe` (not for public demos)

**Why it exists:** “Follow printers carefully” without calling them KOLs falsely.

**Honest naming for article:** **high-PnL wallets (Birdeye)**, not “KOL stream,” unless a wallet is actually tagged.

**Lesson learned (true story for article):** A token ($CMX example) can appear on high-PnL buy tape and still be **honeypot / Unsafe** on GMGN. Product response: **DROPPED** section, not a buy idea.

**Example:**
```bash
python3 scripts/rh_smart_buys.py --minutes 15 --max-mcap 200000 --top 12
```

---

### 6.3 Wallet Board — `scripts/smart_wallet_tracker.py`

**Job:** Raw top-PnL wallet table + sample buys (building block / debug / screenshots).

---

### 6.4 Short Alert — `scripts/format_short_alert.py`

**Job:** Compress JSON artifacts into Telegram-sized text.

```bash
python3 scripts/format_short_alert.py cron/cache/buy_the_dip.json --max 3
```

---

### 6.5 Birdeye client — `scripts/birdeye_client.py`

Shared HTTP helper: load `BIRDEYE` / `BIRDEYE_API_KEY` / `BIRDEYE_KEY` from `.env`, send `x-chain: robinhood`.

---

### 6.6 Hermes pack — `hermes/`

| File | Purpose |
|------|---------|
| `SOUL.md` | Profile “brain”: chain lock, commands (`dip`, `smart buys`, `short`), safety |
| `skill-SKILL.md` | Optional Hermes skill stub |
| `cron-buy-the-dip.md` | Cron prompt template (e.g. 07:00 & 15:00 UTC) |
| `cron-smart-buys.md` | Periodic smart-buys cron template |

---

### 6.7 Optional / experimental (do not oversell)

`extract_cas.py`, `lore_match.py`, `kol_overlap.py` — early X/text lore helpers. **Not required** for core desk. Label experimental if mentioned.

---

## 7. Design rules (quote in article)

1. **Robinhood Chain only**  
2. **Research only** — no trading private keys in this project  
3. **Full contract addresses** always (never only abbreviated CA as the copy target)  
4. **Honeypots dropped**, never hyped as hits  
5. **High-PnL ≠ KOL** unless tagged  
6. **Empty windows are OK** — “no setups” is valid  

---

## 8. Installation (Hermes-first) — article should teach THIS path

### 8.0 Prerequisites

- Hermes Agent via **Nous Portal** and/or **Desktop** and/or **CLI**  
- Python 3.10+, Node/npm 18+ (for `gmgn-cli` via `install.sh`)  
- Telegram bot token if using mobile alerts (via Hermes gateway)  
- Birdeye API key + GMGN API key (user-created)

### 8.1 Install Hermes (if needed)

```bash
hermes setup --portal   # recommended official path
```

Docs: https://hermes-agent.nousresearch.com/docs/guides/run-hermes-with-nous-portal

### 8.2 Telegram via Hermes (not HOODRADAR code)

```bash
hermes gateway setup
hermes gateway          # or host-specific service
```

Docs: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/telegram  

User needs: @BotFather token, allowlisted Telegram user, gateway running on same host as the profile.

### 8.3 Clone + bootstrap scripts

```bash
# example durable path on Linux/Portal agent
mkdir -p /opt/data/src && cd /opt/data/src
git clone https://github.com/YAN-XBT/HOODRADAR.git
cd HOODRADAR
chmod +x install.sh && ./install.sh
source tools/env.sh
```

`install.sh`: installs local `gmgn-cli` under `./tools`, creates `.env` from `.env.example`, writes `tools/env.sh`.

Desktop: clone into a folder Hermes can read/execute.

### 8.4 API keys (user-owned only)

**Birdeye**
- Get key from Birdeye dashboard (see https://docs.birdeye.so/)  
- Put in `.env`: `BIRDEYE=...`  
- Used for wallet PnL + trades on chain `robinhood`

**GMGN**
- `gmgn-cli config` → public key / browser link  
- Create key on https://gmgn.ai/ai  
- Prefer **query-only / trading disabled**  
- `gmgn-cli config --apply 'gmgn_...'`  
- `gmgn-cli config --check`  
- Used for trending, token info, security  

Never commit `.env` or GMGN keypairs. Never paste keys into public chats.

Full: `docs/API_KEYS.md`

### 8.5 Wire Hermes profile

1. Create profile e.g. `hoodradar`  
2. Paste `hermes/SOUL.md` into profile SOUL  
3. Set:

```bash
export RH_DESK_ROOT=/opt/data/src/HOODRADAR   # real path
export PATH="$RH_DESK_ROOT/tools/node_modules/.bin:$PATH"
```

4. Optional: install skill from `hermes/skill-SKILL.md`  
5. Chat commands: `dip` · `smart buys` · `short` · `board`

### 8.6 Smoke commands (CLI or agent terminal)

```bash
source tools/env.sh
python3 scripts/buy_the_dip.py --interval 1h --top 10
python3 scripts/rh_smart_buys.py --minutes 15 --top 8
python3 scripts/format_short_alert.py cron/cache/buy_the_dip.json
```

### 8.7 Optional Hermes cron

- Buy the dip 2×/day: template `hermes/cron-buy-the-dip.md` (e.g. `0 7,15 * * *` UTC)  
- Smart buys hourly/half-hourly: `hermes/cron-smart-buys.md`  
- Deliver to Telegram via Hermes cron delivery settings  

### 8.8 Success criteria for readers

- [ ] Hermes can run `dip` / `smart buys` and return a brief  
- [ ] Full CAs are copy-pasteable  
- [ ] Honeypots appear under DROPPED when flagged  
- [ ] Telegram receives agent messages if gateway configured  
- [ ] No secrets in git  

---

## 9. Data sources & technical notes (accuracy)

| Source | Role | Chain |
|--------|------|--------|
| Birdeye REST | gainers-losers, trader txs | header/param `robinhood` |
| GMGN CLI | market trending, token info, token security | `--chain robinhood` |
| GMGN track kol/smartmoney | **Not used for RH** | unsupported on robinhood |

**Security flags used (GMGN):** e.g. `is_honeypot`, `is_show_alert` (Unsafe banner), high sell tax; LP unlock may appear as soft risk notes.

**Rate limits:** Birdeye may return 429; scripts sleep between wallet calls; users can lower `--top` / increase sleep.

**Empty results:** Normal when no large top-10 dump ≥20% or no safe wallet buys in window.

---

## 10. Example live behaviors (for storytelling — not guarantees)

- **Buy the dip:** Can surface large RH names down ≥20% on 1h or 24h intervals (examples during build included names like IMFX on 1h dumps; PONS/JUGGERNAUT-type large names on longer windows — **do not present as current signals**; re-run live for screenshots).  
- **Smart buys:** Top PnL wallets can buy low-mcap tokens; security gate may drop honeypots (e.g. CMX-style Unsafe/honeypot).  
- **Output quality:** Full CA lines labeled “copy this”; GMGN + explorer links; wallet PnL context.

---

## 11. Suggested article structure (for Claude)

1. Hook: RH noise + SOL cosplay problem  
2. What HOODRADAR is / isn’t  
3. Hermes-first architecture diagram  
4. Modules table + why each exists  
5. Honeypot lesson (trust)  
6. Install path (Portal/Desktop/CLI + gateway + clone + keys + SOUL)  
7. Day-1 chat commands  
8. Optional cron  
9. Limits & disclaimer  
10. CTA: repo + QUICKSTART_HERMES.md  

**Tone guidance:** teacher-operator, DIY, anti-hype, research-only.  
**Avoid:** “guaranteed bounce”, “free alpha”, “KOL always right”, “financial advice”.

---

## 12. Screenshot list for the author

1. GitHub README with banner  
2. Hermes / Telegram (optional)  
3. `buy_the_dip` brief with full CA  
4. Smart buys DROPPED honeypot block  
5. Short alert output  
6. (Optional) `gmgn-cli config --check` / install success  

---

## 13. Attribution & legal lines (must include)

- Not affiliated with **Robinhood Markets, Inc.**, **Birdeye**, **GMGN**, or **Nous Research**.  
- **Research only. DYOR. Not financial advice.**  
- MIT license on code; third-party APIs subject to their ToS.  
- Users responsible for their keys and any trading decisions.

---

## 14. FAQ (for article Q&A)

**Q: Does it trade for me?**  
A: No. Research briefs only.

**Q: Does it work without Hermes?**  
A: CLI smoke works for debug; **product story is Hermes Agent**.

**Q: Why not GMGN KOL track on RH?**  
A: CLI doesn’t support robinhood for those tracks; product uses Birdeye PnL + GMGN trend/security instead.

**Q: Are high-PnL wallets always good?**  
A: No. They can buy honeypots; security filter drops many traps but not all risk.

**Q: What keys do I need?**  
A: Birdeye + GMGN (query). Hermes/Portal for the agent; Telegram bot token for gateway.

**Q: Windows?**  
A: Hermes Desktop / clone path Hermes can read; `install.sh` needs bash/npm/python (WSL or Linux agent often easier).

---

## 15. Repo identity

- **Owner:** YAN-XBT  
- **Name:** HOODRADAR  
- **Positioning name:** hoodradar  
- **Tagline:** Robinhood Chain research desk for Hermes Agent  

---

## 16. One paragraph “press blurb”

HOODRADAR is an open-source Robinhood Chain research desk built to run inside Hermes Agent on Nous Portal, Hermes Desktop, or CLI. It combines Birdeye high-PnL wallet buys with GMGN trending and security filters to surface large-token dumps of at least 20% and filter honeypots—delivering research briefs over Telegram via the Hermes gateway. Users clone the repo, add their own API keys, paste the included SOUL into a Hermes profile, and run commands like “dip” and “smart buys.” It does not autotrade and is not affiliated with Robinhood, Birdeye, GMGN, or Nous.

---

END OF BRIEF — article writer should prefer this file + live GitHub over memory.
