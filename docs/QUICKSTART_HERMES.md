# QUICKSTART — Hermes Agent only

**Repo:** https://github.com/YAN-XBT/HOODRADAR  

## 1) Hermes
- Portal: https://portal.nousresearch.com → `hermes setup --portal`  
- Docs: https://hermes-agent.nousresearch.com/docs/  
- Telegram: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/telegram  
  ```bash
  hermes gateway setup
  ```

## 2) Clone + tools
```bash
git clone https://github.com/YAN-XBT/HOODRADAR.git && cd HOODRADAR
./install.sh && source tools/env.sh
```

## 3) Keys
- Birdeye → `.env` `BIRDEYE=`  
- GMGN → `gmgn-cli config` → apply key (trading OFF)  
- Details: docs/API_KEYS.md  

## 4) Profile
- Paste `hermes/SOUL.md` into profile SOUL  
- Set `RH_DESK_ROOT` to clone path  

## 5) Chat
```
dip
smart buys
short
```

## 6) Cron (optional)
- Templates in `hermes/cron-*.md`  
- Deliver to Telegram via Hermes cron  

**Research only. DYOR.**
