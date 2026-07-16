# X / long-form draft — HOODRADAR

**Repo:** https://github.com/YAN-XBT/HOODRADAR  
**Tone:** teacher-operator · DIY · research only · Hermes-first  
**Not financial advice. Not affiliated with Robinhood Inc., Birdeye, GMGN, Nous.**

---

## Title options

1. I open-sourced a Robinhood Chain research desk that runs inside Hermes Agent  
2. Clone HOODRADAR: high-PnL wallets, honeypot filter, buy-the-dip — on Hermes (Portal / Desktop / CLI)  
3. Stop cosplaying SOL KOL bots on Robinhood Chain. Here’s a cloneable Hermes setup.

---

## Body (post / article)

### Hook

Robinhood Chain is noisy.

Most “smart money” tutorials are still Solana cosplay.  
GMGN’s KOL track doesn’t even support RH the way people pretend.

I wanted something I could run **inside Hermes Agent**:

- Telegram in  
- research brief out  
- **my** keys  
- **no** autotrade  

So I shipped it open source:

**https://github.com/YAN-XBT/HOODRADAR**

---

### What HOODRADAR is

Not a SaaS. Not a signal group.

It’s a **folder + SOUL + scripts** your Hermes profile runs:

1. **Buy the Dip** — GMGN RH top 10 trending · large mcap/liq · dump **≥ 20%**  
2. **Smart Buys** — Birdeye high-PnL RH wallets + recent buys + **honeypot / Unsafe drop**  
3. **Short alerts** — Telegram-sized text  
4. **Hermes pack** — SOUL, skill stub, cron templates  

Stack:

```text
You (Telegram)
   ↕ Hermes Gateway
Hermes Agent (hoodradar SOUL)
   → scripts
   → Birdeye + GMGN (your keys)
   → brief back to you
```

---

### Who it’s for

You run Hermes via:

- **Nous Portal** — https://portal.nousresearch.com  
- **Hermes Desktop**  
- **Hermes CLI** — https://github.com/nousresearch/hermes-agent  

Docs: https://hermes-agent.nousresearch.com/docs/

If you don’t have Hermes yet:

```bash
hermes setup --portal
```

---

### Install (Hermes-first)

Full guide in the repo: `docs/HERMES_SETUP.md`  
One-pager: `docs/QUICKSTART_HERMES.md`

**1) Telegram (Hermes gateway — not a custom bot in the repo)**

```bash
hermes gateway setup
```

Official:  
https://hermes-agent.nousresearch.com/docs/user-guide/messaging/telegram

**2) Clone on the machine Hermes can read**

```bash
git clone https://github.com/YAN-XBT/HOODRADAR.git
cd HOODRADAR
./install.sh
source tools/env.sh
```

**3) Your keys only**

| Key | Use |
|-----|-----|
| Birdeye | high-PnL wallets + trades on RH |
| GMGN | trending + token security (trading OFF) |

Steps: `docs/API_KEYS.md`

**4) Profile**

- Paste `hermes/SOUL.md` into a Hermes profile  
- Set `RH_DESK_ROOT` to the clone path  

**5) Chat**

```text
dip
smart buys
short
```

**6) Optional cron**

Templates in `hermes/cron-*.md`  
Deliver to Telegram via Hermes cron.

---

### Modules (why each exists)

**Buy the Dip**  
Simple rule humans understand:  
among top 10 RH trend names that are *large enough*, which dumped ≥20%?

**Smart Buys**  
Follow wallets that are green on Birdeye PnL.  
Then filter garbage with GMGN security.  
I learned the hard way: high-PnL wallets still buy honeypots.  
The desk **drops** those — it doesn’t hype them.

**Short alert**  
Long research for deep work. Short text for the phone.

**Wallet board**  
Raw leaderboard when you want the under-the-hood view.

---

### Design rules I refuse to break

1. Robinhood Chain only  
2. Research only — no trading keys in this project  
3. Full contract addresses (no `0x12…ab` as the only CA)  
4. Honeypots never presented as “hits”  
5. High-PnL ≠ KOL unless actually tagged  
6. Empty windows are OK — “no setups” is a feature  

---

### Limits (honesty)

- GMGN `track kol` is not RH — we don’t fake it with SOL  
- Security is best-effort, not a guarantee  
- APIs rate-limit; raise sleeps / lower `--top` if you hit 429  
- Not affiliated with Robinhood Markets, Birdeye, GMGN, or Nous  

---

### CTA

Clone it. Break it. Make it yours.

**https://github.com/YAN-XBT/HOODRADAR**

Start: `docs/QUICKSTART_HERMES.md`  
Deep: `docs/HERMES_SETUP.md`

DYOR. Not financial advice. Research only.

---

## Screenshot checklist (attach to the post)

1. Repo README with banner  
2. Hermes / Telegram (gateway) if you show mobile  
3. `dip` output with full CA  
4. Smart buys **DROPPED honeypot** block  
5. Short alert format  

---

## Thread option (if not long-form article)

1/ Hook + repo link  
2/ Architecture (Telegram → Hermes → scripts)  
3/ Buy the dip rule  
4/ Smart buys + honeypot lesson  
5/ Install 6 steps  
6/ Limits + CTA  

---

## Do not say

- guaranteed bounce  
- free alpha forever  
- KOL always right  
- this is financial advice  
