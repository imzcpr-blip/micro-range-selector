---
name: run-cprp
description: >
  Launch the Cooper Precision Reversion Protocol (CPRP) Session Micro Selector
  dashboard (Streamlit) or CLI. Use when the user says RunCPRP, /run-cprp,
  /RunCPRP, "run CPRP", "start CPRP dashboard", "open micro range selector",
  "launch the selector", or wants to start the MES/MNQ/MYM session picker.
---

# RunCPRP

Start the **CPRP Session Micro Selector** from this project.

## Project root

Resolve the app root in this order:

1. Workspace path that contains `app.py` + `analyzer.py` + `config.py` (this repo)
2. `C:\Users\imzcp\micro-range-selector`
3. `C:\Users\imzcp\OneDrive\Desktop\micro-range-selector`

If none exist, stop and tell the user the CPRP selector project was not found.

## Default action (dashboard)

When the user invokes **RunCPRP** without extra flags:

1. `cd` to the project root.
2. Ensure deps: `python -m pip install -r requirements.txt` (quiet; only if import of `streamlit` fails).
3. Start the dashboard **in the background** (do not block the chat):

```powershell
python -m streamlit run app.py --server.headless true
```

4. Tell the user:
   - Dashboard URL: **http://localhost:8501**
   - How to stop: Ctrl+C in that terminal, or end the background process
   - Branding logo video + Quick Reference download are on the page

5. If port 8501 is already in use, report that the dashboard may already be running and give the URL.

## Optional modes

| User intent | Command |
|-------------|---------|
| Dashboard (default) | `python -m streamlit run app.py` |
| One-shot CLI pick | `python run_once.py --alert` |
| Watch + alerts | `python run_once.py --watch 60 --alert` |
| Custom hard stop | add `--stop 75` (or 50–100) to `run_once.py` |

Use `Start-Dashboard.bat` / `Start-Watch.bat` only if the user prefers double-click launch outside the agent.

## Windows shell command

The user can also type **`RUNCPRP`** in PowerShell or Command Prompt (installed at `%USERPROFILE%\.grok\bin\RUNCPRP.cmd`, on PATH). Prefer launching via that when they ask for a shell command, or start Streamlit yourself as above when they invoke this skill in chat.

```text
RUNCPRP              → dashboard
RUNCPRP once         → CLI one-shot
RUNCPRP watch        → watch + alerts
RUNCPRP help
```

## Rules

- Do **not** modify trading rules or place orders — this only launches the personal session-selector tool.
- Prefer the primary project path (`C:\Users\imzcp\micro-range-selector`) when both copies exist.
- After starting Streamlit in the background, confirm the process is up; if it exits with an error, surface stderr and fix missing deps once, then retry.
- Keep responses short: URL + mode started + stop instructions.
