@echo off
cd /d "%~dp0"
echo Starting CPRP Session Micro Selector dashboard (Rulebook v1.5)...
python -m streamlit run app.py
pause
