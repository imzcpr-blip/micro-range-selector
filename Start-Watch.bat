@echo off
cd /d "%~dp0"
echo CPRP watch: MES / MNQ / MYM every 60s — desktop alert when pick changes.
python run_once.py --watch 60 --alert
pause
