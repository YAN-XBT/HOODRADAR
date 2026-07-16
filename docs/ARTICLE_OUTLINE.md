# ARTICLE OUTLINE — “Build a Robinhood Chain research desk yourself”

Tone: **teacher-operator**, not signal seller.  
Promise: **working clone in one evening**, not “my secret alpha”.

---

## Title angles (pick one)

1. I built a Robinhood Chain research desk with free APIs (you can clone it)  
2. RH memes without the SOL cosplay: high-PnL wallets, honeypot filters, buy-the-dip  
3. DIY: top-10 GMGN trend dumps ≥20% + smart wallet buys on Robinhood Chain  

---

## Structure

### 1. Hook (problem)
- RH is noisy; UIs are heavy  
- People copy SOL “KOL bots” that **don’t map** to RH  
- You want **research**, not a black-box caller  

### 2. What we are building (scope box)
**In:**
- Robinhood Chain only  
- High-PnL wallet buys (Birdeye)  
- Honeypot / Unsafe filter (GMGN)  
- Buy-the-dip on GMGN top-10 trending (drop ≥20%, large mcap/liq)  

**Out:**
- Autotrade  
- Guaranteed profit  
- Fake “KOL stream” on RH  

### 3. Architecture diagram
Paste README diagram. One sentence per arrow.

### 4. Stack + cost
| Piece | Role | Cost |
|-------|------|------|
| This repo | scripts | free |
| Birdeye | PnL + txs | free tier / paid |
| GMGN API | trend + security | free query key |
| Hermes (optional) | cron + Telegram | optional |

### 5. Install (light)
Link to repo → `./install.sh` → keys → two smoke commands.  
**Screenshot:** terminal success of `buy_the_dip` and `config --check`.

### 6. Module deep-dives (one subsection each)

#### 6.1 Buy the dip
- Source: gmgn.ai/trend?chain=robinhood  
- Rules: top 10, large, ≤ −20%  
- Live example with **full CA**  
- Why empty result is healthy  

#### 6.2 High-PnL buys + security
- Birdeye gainers  
- Show a **DROPPED honeypot** (trust moment — CMX-style)  
- Explain: profitable wallets still buy trash  

#### 6.3 Short alerts
- `format_short_alert.py` for Telegram  

### 7. Automation
- Cron twice daily  
- Optional Hermes delivery  
- No trading key  

### 8. Limits (honesty section — do not skip)
- GMGN has no RH `track kol`  
- Security is best-effort  
- Rate limits  
- Not affiliated with Robinhood Inc.  

### 9. Clone checklist
Copy from INSTALL “You’re done when…”

### 10. Close
- Link repo  
- “Fork it, break it, make it yours”  
- DYOR footer  

---

## Screenshot checklist

- [ ] GMGN RH trend page  
- [ ] `gmgn-cli config --check`  
- [ ] Buy-the-dip hit with full CA  
- [ ] Smart buys DROPPED honeypot block  
- [ ] Telegram short alert (optional)  
- [ ] Repo README on GitHub  

---

## Phrases to avoid

- “guaranteed bounce”  
- “smart money always right”  
- “this is financial advice”  
- “KOL buys” (unless wallet is actually tagged KOL **and** you show the tag)  

## Phrases to use

- “high-PnL wallets on RH (Birdeye)”  
- “research brief”  
- “honeypot filtered by GMGN flags”  
- “clone the setup”  
