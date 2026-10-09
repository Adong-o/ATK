@echo off
title XAUUSD Bot - Status Report
color 0B
cd /d "%~dp0"
echo.
python -m src.utils.status_report
pause
