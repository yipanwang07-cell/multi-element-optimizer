@echo off
setlocal
set "APP_ROOT=%~dp0"
cd /d "%APP_ROOT%"
if not exist "%APP_ROOT%runtime\python\pythonw.exe" goto source
set "PYTHONHOME=%APP_ROOT%\runtime\python"
set "PYTHONPATH=%APP_ROOT%\app"
set "PYTHONPYCACHEPREFIX=%APP_ROOT%\runtime\cache\python"
set "PYTHONNOUSERSITE=1"
set "PYTHONUTF8=1"
set "TCL_LIBRARY=%APP_ROOT%\runtime\python\Library\lib\tcl8.6"
set "TK_LIBRARY=%APP_ROOT%\runtime\python\Library\lib\tk8.6"
set "PATH=%APP_ROOT%\runtime\java\bin;%APP_ROOT%\runtime\python\Library\bin;%APP_ROOT%\runtime\python;%APP_ROOT%\runtime\python\DLLs;%PATH%"
start "" "%APP_ROOT%\runtime\python\pythonw.exe" "%APP_ROOT%\app\app.py"

exit /b
:source
set "PYTHONHOME="
set "PYTHONPATH=%APP_ROOT%app"
set "PYTHONUTF8=1"
if exist "%APP_ROOT%.venv\Scripts\pythonw.exe" (
  start "" "%APP_ROOT%.venv\Scripts\pythonw.exe" "%APP_ROOT%app\app.py"
) else (
  python "%APP_ROOT%app\app.py"
  if errorlevel 1 pause
)
