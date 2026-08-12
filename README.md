# Cooper Precision Reversion Protocol — Session Micro Selector

Personal tool aligned to **Cooper Precision Reversion Protocol (CPRP)**  
**Official Rulebook v1.6** + **Quick Reference v1.6**  
*(Multi-Timeframe Hierarchy & Order Flow Clarified · Aug 12, 2026 · Raymon Michael Cooper)*

Analyzes **MES**, **MNQ**, and **MYM** and recommends which micro to run for the current trading session — with desktop alerts when the pick changes.

> *Trade the boundaries. Respect the structure. Control the risk.*

## What it does

1. Pulls intraday bars for the three approved micros (Yahoo Finance continuous contracts).
2. Scores each for **range/channel-reversion suitability** using CPRP logic:
   - Structure confirmation (horizontal range **or** channel; ≥2 touches each boundary)
   - Boundary retests and mid-structure occupancy
   - Price location at Support/Resistance extremes
   - Volume + rejection-style price action + RSI as **secondary** confirm (v1.6)
   - Whether structure width fits the **−$50 to −$100** hard stop
   - **Static 60-minute (1H) bias context**: more selective when fading against HTF power
3. Applies operational priority on near-ties: **MES → MNQ → MYM** (§8).
4. Suggests active chart pair from the **two approved pairs only** (**15m+5m** default · **30m+15m** pre-market/slow) plus **60m static** HTF.
5. Alerts you when the recommended session micro changes (or when it flips to sit-out).
6. Surfaces the **v1.6 9-point checklist** (incl. **order flow** — confirm bid/ask on your platform).

## Quick start

```powershell
cd C:\Users\imzcp\micro-range-selector
python -m pip install -r requirements.txt

# Dashboard (recommended)
python -m streamlit run app.py

# One-shot CLI
python run_once.py --alert

# Watch mode (re-score every 60s + alert on change)
python run_once.py --watch 60 --alert
```

Or double-click `Start-Dashboard.bat` / `Start-Watch.bat`.

## Accounts, usernames & Member Chat

Visitors must **sign up or log in** before using the tool.

- **Login** = email + password (min 8 characters; password hashed)  
- **Public username** = chosen after first login (3–20 chars: letters, numbers, `_`)  
- On **sign up**, an email is sent to you with the new subscriber address  
- **Member Chat** = live member panel with messages + **online member count** (green active icon)  
- **Trading Journal** = private session notes (saved per account); also shown **side-by-side** with the Quick Reference on the Session Selector

### Configure email (required for signup alerts)

1. Copy `.streamlit/secrets.toml.example` → `.streamlit/secrets.toml` (local).
2. Fill in your SMTP settings (Gmail: use an [App Password](https://myaccount.google.com/apppasswords)).
3. On **Streamlit Cloud**: App → **Settings** → **Secrets** → paste the same TOML.

```toml
[auth]
notify_email = "your-email@example.com"
pepper = "long-random-string"

[smtp]
host = "smtp.gmail.com"
port = 587
username = "your-email@example.com"
password = "your-app-password"
from_email = "your-email@example.com"
```

Local copies of accounts live in `data/users.db` (gitignored).  
**Note:** Streamlit Community Cloud’s disk is temporary — after a full redeploy, the user database may reset. Your **email inbox** remains the durable subscriber list. For permanent cloud storage later, we can move users to a free database (e.g. Supabase).

## Deploy (public link — Streamlit Community Cloud)

GitHub repository (public): **https://github.com/imzcpr-blip/micro-range-selector**

1. Open **[https://share.streamlit.io](https://share.streamlit.io)** (or [streamlit.io/cloud](https://streamlit.io/cloud)).
2. Sign in with **GitHub** and authorize Streamlit.
3. Click **Create app** / **New app**.
4. Choose:
   - **Repository:** `imzcpr-blip/micro-range-selector`
   - **Branch:** `main`
   - **Main file path:** `app.py`
5. Click **Deploy**.

Your shareable URL will look like: `https://<app-name>.streamlit.app`

### If the in-app **Deploy** button says “not connected to a remote”

That button only works when you launch Streamlit from the Git-connected folder **and** `git` is on PATH.

1. Use: `C:\Users\imzcp\micro-range-selector` (not the Desktop copy — that folder has no Git remote).
2. Confirm:

```powershell
cd C:\Users\imzcp\micro-range-selector
git remote -v
# origin https://github.com/imzcpr-blip/micro-range-selector.git
```

3. Stop Streamlit completely, open a **new** terminal, then:

```powershell
cd C:\Users\imzcp\micro-range-selector
python -m streamlit run app.py
```

**Recommended:** deploy from **share.streamlit.io** (steps above). That path does not depend on the local Deploy button.

### Grok skill: RunCPRP

This project includes a Grok skill at `.grok/skills/run-cprp/`.

- Slash: `/run-cprp` or say **RunCPRP**
- Starts the Streamlit dashboard (or CLI/watch if you ask)
- Helper script: `.grok/skills/run-cprp/scripts/start-dashboard.ps1`

### Windows PowerShell: `RUNCPRP`

From **any** PowerShell or Command Prompt window:

```powershell
RUNCPRP              # start dashboard → http://localhost:8501
RUNCPRP once         # one-shot CLI pick + alert
RUNCPRP watch        # re-score every 60s + alerts
RUNCPRP sync         # pull latest docs/branding from CPRP Trading folder
RUNCPRP push         # commit + push to GitHub → public Streamlit app redeploys
RUNCPRP push "msg"   # same, with commit message
RUNCPRP push --sync  # sync assets, then push
RUNCPRP help
```

### Keep the public app in sync with local edits

Streamlit Cloud does **not** watch your PC. It rebuilds from **GitHub `main`**.

| You do locally | Public app |
|----------------|------------|
| Edit files under `C:\Users\imzcp\micro-range-selector` | Unchanged until push |
| `RUNCPRP push` | Auto-redeploys in ~1–3 minutes |

```powershell
# After you change the app locally:
RUNCPRP push
# or:
RUNCPRP push "Update strategy help text"
```

Helper script: `scripts\publish-to-cloud.ps1`

Installed as:
- `C:\Users\imzcp\.grok\bin\RUNCPRP.cmd` (on your user PATH)
- PowerShell profile function `RUNCPRP` / alias `runcprp`

Open a **new** terminal if an old session was already open before install.

## Files

| File | Purpose |
|------|---------|
| `app.py` | Streamlit app: Session Selector · Company Branding · About the Founder |
| `analyzer.py` | Scoring engine (CPRP rulebook-mapped) |
| `alerts.py` | Windows desktop notifications |
| `config.py` | Protocol metadata, instruments, hard stop, founder bio |
| `sync_cprp_assets.py` | Scans CPRP Trading / related folders; syncs docs + branding into `assets/` |
| `run_once.py` | CLI / watch mode |
| `assets/cprp_logo_video.gif` | Looping logo GIF (dashboard header) |
| `assets/cprp_logo_video_alt.gif` | Looping logo GIF (sidebar) |
| `assets/cprp_member_chat_hero.gif` | Member Chat hero GIF |
| `assets/cprp_logo_icon.jpg` | Favicon / sidebar monogram fallback |
| `scripts/convert_videos_to_gifs.py` | Rebuild looping GIFs from MP4 sources |
| `assets/CPRP_Quick_Reference_v1.6.jpg` | Downloadable Quick Reference card |
| `assets/CPRP_Quick_Reference_v1.6.pdf` | Official Quick Reference v1.6 PDF |
| `assets/CPRP_Official_Rulebook_v1.6.pdf` | Official Rulebook v1.6 (synced from CPRP Trading) |
| `assets/branding/` | Company logo suite + video media |

## App pages

| Page | Purpose |
|------|---------|
| **Session Selector** | Micro ranking, strategy instructions, checklist, doc downloads |
| **Company Branding** | Logo gallery, logo video, download branding assets |
| **About the Founder** | Personal story of Raymon Michael Cooper / CPRP origin |

## Document sync

On each app session start (and via **Sync docs from CPRP Trading**), the app scans:

- `C:\Users\imzcp\OneDrive\Desktop\CPRP Trading`
- Desktop, Downloads, and the app folder

It pulls the **latest** Quick Reference / Rulebook Update / Official Rulebook PDFs and branding files into `assets/` (and `assets/branding/`).

Manual sync:

```powershell
cd C:\Users\imzcp\micro-range-selector
python sync_cprp_assets.py
```

## How to operate the strategy (Official Quick Reference v1.6)

These are the CPRP operating instructions distilled from the **Official Quick Reference v1.6** and **Official Rulebook v1.6**. The selector chooses *which micro* to focus on; **you** still run the Protocol on the charts.

> *Trade the boundaries. Respect the structure. Control the risk.*

### Strategy identity

**Intraday range / channel reversion** on **MES** (primary), **MNQ**, **MYM** — **not scalping**.  
**Sell confirmed resistance · Buy confirmed support.**  
Hard risk: **−$50 to −$100** max per trade.  
Pause **30 minutes** (or until a new clear structure forms) after any S/R break.  
Static **60-minute (or 4H)** chart is overall bias only — never generates entries.

### Multi-timeframe hierarchy (v1.6)

| Chart | Role | Use for |
|-------|------|---------|
| **60-minute (static)** | Overall bias / sentiment | Trend context only — never entries |
| **15m or 30m** | Structure & levels | Confirmed S/R + swing structure (“map”) |
| **5m or 15m** | Timing & pressure | Entry timing, rejection, order flow (“trigger”) |

### Working pairs (select by conditions)

| Pair | When | Roles |
|------|------|-------|
| **15m + 5m (default)** | Normal volume, clean ranges, active session | 15m = structure · 5m = timing + pressure |
| **30m + 15m** | Pre-market, low volume, lunch, wide/choppy | 30m = structure · 15m = timing · 5m fine-tune only |

No chart lower than the **5-minute**. Former **5m+1m** pair is fully retired.

### Order flow (v1.6)

- **Bid = buying power** · **Ask = selling power**  
- Shift in dominance at a key level is strong confirmation  
- Confirm on your platform (not available from Yahoo delayed bars)

### RSI rules (v1.6)

- Prefer **divergence at the actual S/R level** over absolute **70/30** extremes.
- **Elevated RSI that stays high** often = **strong buying power** — do **not** fade solely because overbought.
- Exhaustion needs structure break + order-flow shift + RSI failure to reclaim.
- On structure TF: extremes are **alerts only**. Mid-range → wait.
- Optional RSI **7 or 9** on execution chart for divergence only; keep **14** on structure.

### Pre-trade checklist (all 9 required)

1. Confirmed S/R on higher TF of working pair  
2. Price at/near boundary  
3. Price-action rejection on lower TF  
4. Volume supports rejection / absorption  
5. **Order flow confirms**  
6. RSI favorable (divergence preferred)  
7. Hard stop −$50 to −$100  
8. No recent structure break (or pause done)  
9. 60m bias not strongly opposing (or highly selective)

### Hard risk rule (non-negotiable)

- Max loss per trade: **−$50 to −$100**
- Exit **immediately** at the limit
- **No averaging down**
- Stay on micros only

### Key operating rules

- **New session highs:** trade **current developing structure** — do not fade “new high” alone.
- 60m (or 4H) is a **mandatory bias filter only**.
- Early pre-market → default **30m+15m**.
- **Fewer, higher-quality trades** — do not force scalping in slow markets.
- Prefer **MES** unless MNQ/MYM is clearly superior.

### Recommended session flow with this app

1. Open the dashboard → note recommended micro (or sit out).  
2. Open that micro’s chart pair (**15m+5m** or **30m+15m**) + static 60m on NinjaTrader.  
3. Confirm structure at boundaries + order flow.  
4. Apply the full 9-point checklist before ordering.  
5. Manage breaks with flatten + 30-min pause (or new clear structure).  
6. Re-check the selector after breaks or major session shifts.  

Full in-app copy: sidebar **How to operate the strategy** and the main expander of the same name.

## Important limits

- **Not a broker** — does not place orders (use Ironbeam / NinjaTrader).
- Market data is **Yahoo delayed**, not CME live — use for session selection, not tick entries.
- **Order flow** is confirmed on your platform (DOM / footprint) — not scored from Yahoo.
- Hard stop, structure-break pause, micros-only rules still apply in your platform.
- Futures trading involves substantial risk of loss.

## Rulebook mapping (Official Rulebook v1.6)

| Section | How the app uses it |
|---------|---------------------|
| §1 Strategy overview | Sit-out when structure unconfirmed; not scalping |
| §2 Instruments & multi-TF | MES / MNQ / MYM only; two pairs; static 60m bias |
| §3 Structure | Efficiency + dual-side retests; ranges **and** channels; developing structure |
| §4 Order flow | Documented in checklist/UI — confirm Bid/Ask on platform |
| §5 Entry rules | Boundary → PA → volume → OF → RSI (elevated may = strength) |
| §6 Risk & exits | Range geometry vs $50–$100 stop; 30-min break pause |
| §7 Checklist | Interactive **9-item** pre-trade checklist |
| §8 Discipline | MES preferred on ties; quality over frequency |
| **v1.6** | Multi-TF hierarchy formalized; order flow; RSI strength clarification |

## Version note

App aligned to **CPRP Official Rulebook v1.6** and **Quick Reference v1.6** (12 August 2026).

**v1.6 primary points:**
- Multi-timeframe hierarchy: **60m bias → structure → timing**
- Working pairs: **15m+5m** (default) and **30m+15m** (pre-market / slow / choppy)
- **Order flow** (Bid/Ask power) as confirmation layer
- RSI: elevated that stays high often = strength — not auto-fade
- New session highs / developing structure guidance
- Explicit **not scalping** classification
- Documents sync from `CPRP Trading` folder (latest Official Rulebook + Quick Reference)
