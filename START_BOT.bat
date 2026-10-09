@echo off
title XAUUSD Scalping Bot - LIVE
color 0A
cd /d "%~dp0"

echo.
echo  ============================================================
echo   XAUUSD MT5 SCALPING BOT  ^|  Starting continuous mode...
echo  ============================================================
echo.

:: Install / verify dependencies
echo  [1/3] Checking Python packages...
python -m pip install -r requirements.txt -q --no-warn-script-location
python -m playwright install chromium --quiet 2>nul
echo        OK

:: Check .env
echo  [2/3] Checking credentials (.env)...
if not exist ".env" (
    echo.
    echo  ERROR: .env file missing!
    echo  Copy .env.example to .env and fill in your credentials.
    echo.
    pause
    exit /b 1
)
echo        OK

:: Delete any leftover stop file
if exist "STOP_BOT.txt" del /f "STOP_BOT.txt"

echo  [3/3] Launching bot (continuous mode)...
echo.
echo  Dashboard : http://127.0.0.1:8765/
echo  To STOP   : press Ctrl+C  OR  create STOP_BOT.txt in this folder
echo  Status    : double-click CHECK_STATUS.bat
echo.
echo  ============================================================
echo.

python -m src.main

echo.
echo  Bot stopped. Press any key to close.
pause
