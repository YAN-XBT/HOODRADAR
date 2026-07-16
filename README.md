<p align="center">
  <img src="assets/hoodradar-banner.jpg" alt="HOODRADAR" width="720"/>
</p>

<p align="center"><strong>Robinhood Chain research desk</strong> · clone into Hermes Agent or plain CLI</p>

# hoodradar

**Robinhood Chain research desk you can clone into Hermes Agent (or plain CLI).**

> High-PnL wallets · honeypot filter · buy-the-dip on GMGN RH trend  
> **Research only. No autotrade. Your keys stay on your machine.**

[![Chain](https://img.shields.io/badge/chain-Robinhood%20only-0A66C2)](#)
[![Mode](https://img.shields.io/badge/mode-research%20only-2ea44f)](#)
[![Trade](https://img.shields.io/badge/trading-off-d73a49)](#)
[![Hermes](https://img.shields.io/badge/Hermes%20Agent-ready-7c3aed)](#)

**Not affiliated with Robinhood Markets, Birdeye, GMGN, or Nous Research.**  
Read [DISCLAIMER.md](./DISCLAIMER.md) first.

---

## What is this?

**hoodradar** is a small open toolkit to research **Robinhood Chain** memes without cosplaying Solana KOL bots:

| You get | You do not get |
|---------|----------------|
| Scripts + Hermes SOUL/cron recipes | Our API keys |
| Module map + full install | Autotrade / “signals service” |
| Honeypot drop + full CAs | Guaranteed profit |

### Three core jobs

1. **Who is printing?** → Birdeye top-PnL wallets + their buys  
2. **Is it a trap?** → GMGN security (honeypot / Unsafe)  
3. **Did a large trend dump?** → GMGN top-10 RH trend, drop **≥ 20%**

```text
 Birdeye (RH PnL + txs) ──┐
                          ├──► rh_smart_buys ──► brief / Telegram
 GMGN security + info ────┘

 GMGN trending (RH top 10) ──► buy_the_dip (≥20% dump, large mcap/liq)
```

---

## Quick start (CLI)

```bash
git clone https://github.com/YAN-XBT/HOODRADAR.git
cd hoodradar
chmod +x install.sh && ./install.sh

# 1) Birdeye → .env
# 2) GMGN → gmgn-cli config (see docs/API_KEYS.md)

source tools/env.sh
python3 scripts/buy_the_dip.py --interval 1h --top 10
python3 scripts/rh_smart_buys.py --minutes 15 --top 8
```

Full path: **[docs/INSTALL.md](./docs/INSTALL.md)**  
API keys: **[docs/API_KEYS.md](./docs/API_KEYS.md)**  
Hermes Agent: **[docs/HERMES_SETUP.md](./docs/HERMES_SETUP.md)**  
Modules: **[docs/MODULES.md](./docs/MODULES.md)**

---

## Modules (product map)

| Module | Script | Purpose |
|--------|--------|---------|
| **Buy the Dip** | `buy_the_dip.py` | Top 10 [GMGN RH trend](https://gmgn.ai/trend?chain=robinhood); large names; dump ≥20% |
| **Smart Buys** | `rh_smart_buys.py` | High-PnL RH wallets (Birdeye) + buys + honeypot filter |
| **Wallet Board** | `smart_wallet_tracker.py` | Raw top-PnL table + recent buys |
| **Short Alert** | `format_short_alert.py` | Telegram-sized summary from JSON |
| **Birdeye client** | `birdeye_client.py` | Shared RH API helper |
| **Optional lore** | `extract_cas` / `lore_match` / `kol_overlap` | X/text heat helpers (bonus chapter) |

Deep dive: [docs/MODULES.md](./docs/MODULES.md)

---

## Hermes Agent (copy settings, not keys)

1. Clone this repo onto the machine where Hermes runs (or copy the folder into a profile workspace).  
2. Follow [docs/HERMES_SETUP.md](./docs/HERMES_SETUP.md):  
   - drop `SOUL.md` into a profile (e.g. `hoodradar`)  
   - put keys only in **that profile’s `.env`** (never in git)  
   - install `gmgn-cli` via `./install.sh`  
   - optional cron: buy-the-dip 2×/day + smart buys on a timer  
3. Chat commands: *“run buy the dip”* / *“scan high-PnL RH buys last 15m”*

---

## Requirements

- Python 3.10+  
- Node 18+ / npm (`gmgn-cli`)  
- [Birdeye](https://docs.birdeye.so/) API key  
- [GMGN](https://gmgn.ai/ai) query API key (trading **OFF**)  
- Optional: [Hermes Agent](https://hermes-agent.nousresearch.com/docs) for Telegram + cron  

---

## Design rules (please keep these if you fork)

1. **Robinhood Chain only** — no SOL KOL feed as a fake RH substitute  
2. **Research only** — no trading private keys in this project  
3. **Full contract addresses** always  
4. **Honeypots dropped**, not hyped  
5. **High-PnL ≠ KOL** unless the wallet is actually tagged  
6. **Empty windows are OK**  

---

## Disclaimer

Educational / research toolkit. Not financial advice.  
See [DISCLAIMER.md](./DISCLAIMER.md).

## License

MIT — [LICENSE](./LICENSE)
