@echo off
setlocal
cd /d "%~dp0"

where pyw >nul 2>nul
if %errorlevel%==0 (
  start "" pyw ".\app.py"
  goto :eof
)

where pythonw >nul 2>nul
if %errorlevel%==0 (
  start "" pythonw ".\app.py"
  goto :eof
)

where py >nul 2>nul
if %errorlevel%==0 (
  start "" py ".\app.py"
  goto :eof
)

where python >nul 2>nul
if %errorlevel%==0 (
  start "" python ".\app.py"
  goto :eof
)

echo FleetKey could not find Python.
echo Install Python from https://www.python.org/downloads/windows/
pause
