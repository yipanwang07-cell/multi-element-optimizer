@echo off
setlocal
for %%I in ("%~dp0..") do set "APP_ROOT=%%~fI"
cd /d "%APP_ROOT%"
set "JAVA_EXE=javaw"
if exist "%APP_ROOT%\runtime\java\bin\javaw.exe" set "JAVA_EXE=%APP_ROOT%\runtime\java\bin\javaw.exe"
start "" "%JAVA_EXE%" -cp "%APP_ROOT%\runtime\vendor\javafoil-compatible-v2.jar;%APP_ROOT%\runtime\vendor\*" MH.JavaFoil.JavaFoil
