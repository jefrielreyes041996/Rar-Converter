@echo off
setlocal
cd /d "%~dp0"

echo ==========================================
echo   Gichu RAR Converter - EXE Builder
echo ==========================================
echo.
echo This creates a standalone Windows EXE.
echo Python is needed ONLY on this build computer.
echo Your team will NOT need Python to run the finished EXE.
echo.

where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher was not found.
  echo Install Python 3 from https://www.python.org/downloads/windows/
  echo During installation, enable "Add Python to PATH".
  pause
  exit /b 1
)

py -3 -m pip install --upgrade pyinstaller
if errorlevel 1 (
  echo Failed to install PyInstaller.
  pause
  exit /b 1
)

py -3 -m PyInstaller --noconfirm --clean --onefile --windowed --name "Rar-Converter" Gichu_RAR_Converter.py
if errorlevel 1 (
  echo.
  echo EXE build failed. Please review the error above.
  pause
  exit /b 1
)

echo.
echo BUILD COMPLETE!
echo Your EXE is here:
echo %CD%\dist\Rar-Converter.exe
echo.
echo Copy that EXE to your team's computers.
echo Each computer still needs WinRAR installed.
pause
