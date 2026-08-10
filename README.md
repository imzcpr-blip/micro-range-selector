# Cooper Precision Reversion Protocol — Session Micro Selector

Personal tool aligned to **Cooper Precision Reversion Protocol (CPRP)**  
**Official Rulebook base v1.3** + **Update v1.5** (final)  
*(Chart Pair Hierarchy & RSI Clarification · Aug 10, 2026 · Raymon Michael Cooper)*

Analyzes **MES**, **MNQ**, and **MYM** and recommends which micro to run for the current trading session — with desktop alerts when the pick changes.

> *Trade the boundaries. Respect the structure. Control the risk.*

## What it does

1. Pulls intraday bars for the three approved micros (Yahoo Finance continuous contracts).
2. Scores each for **range/channel-reversion suitability** using CPRP logic:
   - Structure confirmation (horizontal range **or** channel; ≥2 touches each boundary)
   - Boundary retests and mid-structure occupancy
   - Price location at Support/Resistance extremes
   - Volume + rejection-style price action + RSI as **secondary** confirm (§4 / v1.5)
   - Whether structure width fits the **−$50 to −$100** hard stop (§5)
   - **Static 1-Hour trend context**: more selective when fading against HTF trend
3. Applies operational priority on near-ties: **MES → MNQ → MYM** (§7).
4. Suggests active chart pair from the **two approved pairs only** (**15m+5m** default · **30m+15m** larger/slower) plus **1-Hour static** HTF.
5. Alerts you when the recommended session micro changes (or when it flips to sit-out).

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
| `assets/cprp_logo_video.mp4` | Branding logo video (dashboard header) |
| `assets/cprp_logo_icon.jpg` | Favicon / sidebar monogram |
| `assets/CPRP_Quick_Reference_v1.5.jpg` | Downloadable Quick Reference card |
| `assets/CPRP_Quick_Reference_v1.5.pdf` | Official Quick Reference v1.5 PDF |
| `assets/CPRP_Rulebook_Update_v1.5.pdf` | Official Rulebook Update & Changelog v1.5 |
| `assets/CPRP_Official_Rulebook_v1.3.pdf` | Official Rulebook base (synced from CPRP Trading) |
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

## How to operate the strategy (Official Quick Reference v1.5)

These are the CPRP operating instructions distilled from the **Official Quick Reference v1.5** and **Rulebook Update v1.5**. The selector chooses *which micro* to focus on; **you** still run the Protocol on the charts.

> *Trade the boundaries. Respect the structure. Control the risk.*

### Strategy identity

Range-bound mean-reversion on **MES** (primary), **MNQ**, **MYM**.  
**Sell confirmed resistance · Buy confirmed support.**  
Hard risk: **−$50 to −$100** max per trade.  
Pause **30 minutes** (or until a new clear range forms) after any S/R break.  
Static **1-Hour (or 4H)** chart is context only — never generates entries.

### Chart pair hierarchy (v1.5 — only two pairs)

| Situation | Structure | Execution | Notes |
|-----------|-----------|-----------|-------|
| **Primary / default** | **15-minute** | **5-minute** | Cleaner RSI, better range definition, still responsive |
| Larger / slower ranges or lower volume | **30-minute** | **15-minute** | Highest quality S/R, least noise |

No chart lower than the **5-minute** is used for structure or execution.

### RSI rules (v1.5)

- Prefer **divergence at the actual S/R level** over absolute **70/30** extremes.
- On **15m and 30m**, RSI extremes are useful as **alerts / preparation only**. If price is still mid-range, do not enter — wait for the confirmed boundary + price action + volume.
- RSI is **secondary** confirmation. Full entry stack: **confirmed S/R + price action + volume**.
- Optional: faster RSI (**7 or 9**) on the execution chart for divergence visualization only. Keep standard **14** on the structure chart.

### Confirmation hierarchy

1. Confirmed Support / Resistance of the active range (structure chart)  
2. Price action at the level (rejection, absorption, engulfs)  
3. Volume confirmation  
4. RSI (secondary — prefer divergence at S/R)  

### Hard risk rule (non-negotiable)

- Max loss per trade: **−$50 to −$100**
- Exit **immediately** at the limit
- **No averaging down**
- Stay on micros only

### Key operating rules

- New session lows / highs that **break the prior range** → **pause**. Do not hunt lower-TF bounces.
- 1-Hour (or 4H) window is a **mandatory context filter only**.
- **Fewer, higher-quality trades** preferred over high-frequency noise trades.
- Prefer **MES** unless MNQ/MYM is clearly superior.
- Platform preference: **NinjaTrader Web** (high/low display).

### Recommended session flow with this app

1. Open the dashboard → note recommended micro (or sit out).  
2. Open that micro’s chart pair (**15m+5m** or **30m+15m**) + static 1-Hour on NinjaTrader.  
3. Confirm structure at boundaries.  
4. Apply confirmation hierarchy (S/R → PA → volume → RSI secondary) before ordering.  
5. Manage breaks with flatten + 30-min pause (or new clear range).  
6. Re-check the selector after breaks or major session shifts.  

Full in-app copy: sidebar **How to operate the strategy (official Quick Reference)** and the main expander of the same name.

## Important limits

- **Not a broker** — does not place orders (use Ironbeam / NinjaTrader).
- Market data is **Yahoo delayed**, not CME live — use for session selection, not tick entries.
- Hard stop, structure-break pause, micros-only rules still apply in your platform.
- Futures trading involves substantial risk of loss.

## Rulebook mapping (base v1.3 + update v1.5)

| Section | How the app uses it |
|---------|---------------------|
| §1 Strategy overview | Sit-out when structure unconfirmed; no forced trades |
| §2 Instruments & charts | MES / MNQ / MYM only; **two chart pairs** (15m+5m default, 30m+15m secondary); static 1-Hour context |
| §3 Structure definition | Efficiency + dual-side retests; ranges **and** channels valid |
| §4 Entry rules | Confirmation hierarchy: boundary → PA → volume → RSI secondary (divergence preferred) |
| §5 Risk & exits | Range geometry vs $50–$100 stop; 30-min break pause (or new clear range) |
| §6 Checklist | Interactive pre-trade checklist in dashboard |
| §7 Discipline | MES preferred on ties; **quality over frequency** |
| **v1.5 update** | Final chart-pair hierarchy (two pairs only); RSI secondary-confirm clarification |

## Version note

App aligned to **CPRP Official Rulebook base v1.3** + **Update v1.5** (final, 10 August 2026).

**v1.5 primary changes:**
- Chart pairs: **15m+5m** (primary/default) and **30m+15m** (larger/slower/lower volume) only
- No chart lower than 5-minute for structure or execution
- RSI clarified as secondary confirmation; prefer divergence at S/R; 15m/30m extremes are alerts only
- Quality over frequency reinforced

All other v1.3 sections remain in force unless explicitly superseded by the v1.5 update document.
