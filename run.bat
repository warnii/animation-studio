@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" app.py
) else (
  python app.py
)
if errorlevel 1 (
  echo.
  echo The studio did not start. Run setup.bat first and review the error above.
  pause
)
