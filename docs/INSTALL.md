# INSTALL — bootstrap scripts (used by Hermes hosts)

This file is the **script layer**.  
**Primary user journey:** [HERMES_SETUP.md](./HERMES_SETUP.md) (Portal / Desktop / CLI + Telegram).

Hermes Agent docs: https://hermes-agent.nousresearch.com/docs/

---

## 1. Clone (on the machine Hermes uses)

```bash
git clone https://github.com/YAN-XBT/HOODRADAR.git
cd HOODRADAR
```

---

## 2. Bootstrap tools

```bash
chmod +x install.sh
./install.sh
source tools/env.sh
```

Installs local `gmgn-cli`, creates `.env` from example.

Requires: **Python 3.10+**, **Node/npm 18+**.

---

## 3. Keys

Full guide: [API_KEYS.md](./API_KEYS.md)

```bash
# .env
BIRDEYE=...

source tools/env.sh
gmgn-cli config
gmgn-cli config --apply 'gmgn_...'
gmgn-cli config --check
```

---

## 4. Smoke (CLI)

```bash
python3 scripts/buy_the_dip.py --interval 1h --top 10 --min-drop 20
python3 scripts/rh_smart_buys.py --minutes 15 --max-mcap 200000 --top 8
python3 scripts/format_short_alert.py cron/cache/buy_the_dip.json
```

Then continue Hermes SOUL + Telegram: **[HERMES_SETUP.md](./HERMES_SETUP.md)**.

---

## 5. Telegram (Hermes, not this repo)

```bash
hermes gateway setup
```

Docs:

- https://hermes-agent.nousresearch.com/docs/user-guide/messaging/telegram  
- https://hermes-agent.nousresearch.com/docs/user-guide/messaging/  

---

## 6. Windows / Desktop notes

- Prefer clone path **without** double nesting (`HOODRADAR/HOODRADAR/...`)  
- Root must contain `README.md` and `scripts/`  
- LF/CRLF warnings in Git can be ignored  
- If Desktop has no npm: use WSL or run `install.sh` on a Linux Hermes host  

---

## 7. Success criteria

- [ ] CLI smoke OK  
- [ ] Hermes profile SOUL points at `RH_DESK_ROOT`  
- [ ] Chat command returns a brief  
- [ ] Gateway delivers to Telegram (if you use mobile)
