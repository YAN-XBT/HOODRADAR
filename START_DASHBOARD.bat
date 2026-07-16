@echo off
cd /d "%~dp0"
echo.
echo  HOODRADAR local dashboard
echo  Open http://127.0.0.1:8787  then Ctrl+F5
echo  (needs Python3; gmgn-cli + keys for live Run buttons / sparklines)
echo.
where py >nul 2>&1 && py -3 scripts\dashboard_server.py && goto e
python scripts\dashboard_server.py
:e
pause
