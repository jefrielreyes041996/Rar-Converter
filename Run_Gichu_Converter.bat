@echo off
cd /d "%~dp0"
py -3 Gichu_RAR_Converter.py
if errorlevel 1 (
  echo.
  echo Could not start the app. Make sure Python 3 is installed.
  pause
)
