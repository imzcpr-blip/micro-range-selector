@echo off
cd /d "%~dp0"
echo Starting CPRP Micro Selector — http://localhost:8501
python -m streamlit run app.py --server.headless true
pause
