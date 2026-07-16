# INSTALL — hoodradar from GitHub to working desk

**Audience:** anyone who can open a terminal (or Hermes with terminal tools).  
**Time:** ~20–40 minutes including API signups.

---

## 1. Clone

```bash
git clone https://github.com/YAN-XBT/HOODRADAR.git
cd hoodradar
```

Replace `YAN-XBT` with the GitHub username that published the repo.

---

## 2. Bootstrap

```bash
chmod +x install.sh
./install.sh
```

Installs local `gmgn-cli` under `./tools`, creates `.env`, writes `tools/env.sh`.

---

## 3. API keys

Follow **[API_KEYS.md](./API_KEYS.md)** in full:

1. Birdeye → `.env` → `BIRDEYE=...`  
2. GMGN → `gmgn-cli config` → create key on https://gmgn.ai/ai → `config --apply`  

Both verified with the test commands in that doc.

---

## 4. First runs (CLI)

```bash
source tools/env.sh

# A) Buy the dip — top 10 RH trend, large, dump ≥20%
python3 scripts/buy_the_dip.py \
  --interval 1h --top 10 --min-drop 20 \
  --min-mcap 50000 --min-liq 15000

# B) High-PnL wallet buys + honeypot filter
python3 scripts/rh_smart_buys.py \
  --minutes 15 --max-mcap 200000 --top 12

# C) Short text for Telegram
python3 scripts/format_short_alert.py cron/cache/buy_the_dip.json
```

---

## 5. Hermes Agent (optional but recommended)

See **[HERMES_SETUP.md](./HERMES_SETUP.md)**.

Short version:
- clone path on Hermes host  
- profile SOUL from `hermes/SOUL.md`  
- keys only in profile `.env` + gmgn-cli  
- cron templates in `hermes/`

---

## 6. Schedule (optional)

```cron
# UTC — twice daily buy-the-dip
0 7,15 * * * cd /path/to/hoodradar && . tools/env.sh && python3 scripts/buy_the_dip.py --interval 1h --top 10 && python3 scripts/buy_the_dip.py --interval 24h --top 10 >> cron/cache/cron.log 2>&1
```

---

## 7. Success criteria

- [ ] Trending RH JSON returns  
- [ ] Birdeye gainers on `robinhood` work  
- [ ] Honeypot sample shows up under **DROPPED** when hit  
- [ ] Full CAs copy-paste without `…`  
- [ ] No secrets in git  

---

## 8. Update later

```bash
cd hoodradar
git pull
# re-run install.sh only if gmgn-cli missing
```
