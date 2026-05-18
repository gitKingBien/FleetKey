@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
  py ".\app.py"
  goto :eof
)

where python >nul 2>nul
if %errorlevel%==0 (
  python ".\app.py"
  goto :eof
)

echo FleetKey could not find Python.
echo Install Python from https://www.python.org/downloads/windows/
pause
