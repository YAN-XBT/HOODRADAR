# How YOU publish hoodradar to GitHub

This machine prepared the repo locally. **You** push it under your GitHub account (auth lives with you).

---

## Recommended public name

| Field | Value |
|-------|--------|
| **Repo name** | `hoodradar` |
| **Display title** | **hoodradar** — Robinhood Chain research desk |
| **Tagline** | DIY high-PnL wallet tape + honeypot filter + buy-the-dip for RH |
| **Topics** | `robinhood-chain`, `crypto-research`, `gmgn`, `birdeye`, `hermes-agent`, `memecoins` |

Alternative names if taken: `rh-hoodradar`, `hoodradar-rh`, `rh-research-desk`.

---

## Option A — GitHub CLI (easiest)

On **your laptop** (with `gh auth login` done):

```bash
# 1) Copy the folder from the server OR use the tarball
# scp -r user@host:/opt/data/profiles/rh-meme-desk/diy-export/rh-chain-research-desk ./hoodradar
# OR: scp user@host:/opt/data/profiles/rh-meme-desk/diy-export/rh-chain-research-desk.tar.gz .
#     tar xzf rh-chain-research-desk.tar.gz && mv rh-chain-research-desk hoodradar

cd hoodradar

# 2) Optional: rename remote-facing folder already named in docs as hoodradar
# (content is ready; only GitHub repo name matters)

# 3) Ensure clean of secrets
grep -R "BIRDEYE=\|gmgn_" .env 2>/dev/null && echo "STOP: secrets in tree" || echo "no .env secrets tracked"
git status

# 4) Create public repo + push
gh repo create hoodradar --public --source=. --remote=origin --push \
  --description "hoodradar — DIY Robinhood Chain research desk for Hermes/CLI (high-PnL wallets, honeypot filter, buy-the-dip)"
```

Set About on GitHub:
- Description: same as above  
- Website: your X article URL later  
- Topics: as above  

---

## Option B — Manual (website + git)

1. GitHub → **New repository**  
   - Name: `hoodradar`  
   - Public  
   - **No** README/license (we already have them)  

2. Locally:

```bash
cd hoodradar
git remote add origin git@github.com:YAN-XBT/HOODRADAR.git
# if this folder was already git init'd:
git branch -M main
git push -u origin main
```

---

## Option C — From this VPS (if you add a token)

```bash
cd /opt/data/profiles/rh-meme-desk/diy-export/rh-chain-research-desk
# optional rename for clarity
# (repo content already branded hoodradar in README)

git remote add origin https://github.com/YAN-XBT/HOODRADAR.git
# use PAT or SSH key you install
git push -u origin main
```

**Do not** paste a PAT into Telegram chat with the agent if avoidable — use SSH keys on the machine.

---

## After push — README polish

Edit one line on GitHub README:

```bash
git clone https://github.com/YAN-XBT/HOODRADAR.git
```

Replace `YAN-XBT` with your real username (search-replace in README + INSTALL + HERMES_SETUP).

```bash
# local fix then push
find . -name '*.md' -exec sed -i 's|YAN-XBT|YourRealGithub|g' {} \;
git commit -am "docs: real GitHub user"
git push
```

---

## What followers do (your article CTA)

```text
1. Open github.com/YOU/hoodradar
2. git clone …
3. ./install.sh
4. Add Birdeye + GMGN keys (docs/API_KEYS.md)
5. Optional: paste hermes/SOUL.md into a Hermes profile
6. Run buy_the_dip + rh_smart_buys
```

---

## Security checklist before public

- [ ] No `.env` in repo  
- [ ] No `keypair.pem`  
- [ ] No real `gmgn_` keys in docs  
- [ ] DISCLAIMER.md present  
- [ ] Trading described as OFF  

---

## Local path on this server (for you)

```text
/opt/data/profiles/rh-meme-desk/diy-export/rh-chain-research-desk/
/opt/data/profiles/rh-meme-desk/diy-export/rh-chain-research-desk.tar.gz
```
