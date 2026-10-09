@echo off
title XAUUSD Bot - DRY RUN TEST
color 0E
cd /d "%~dp0"

echo.
echo  ============================================================
echo   DRY RUN TEST  ^|  One cycle, no real orders
echo  ============================================================
echo.

python -m pip install -r requirements.txt -q --no-warn-script-location
python -m playwright install chromium --quiet 2>nul

echo  Running single cycle (dry_run=true in settings)...
echo  Watch MT5 launch automatically if installed.
echo.

python -m src.main --run-once

echo.
echo  Done. Check CHECK_STATUS.bat for results.
pause
