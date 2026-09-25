@echo off
rem ------------------------------------------------------------------
rem  Launchpad Pro TAB Edition - Start unter Windows
rem  Beim ersten Start wird automatisch eine Python-Umgebung (.venv)
rem  angelegt und alle Abhaengigkeiten werden installiert.
rem ------------------------------------------------------------------
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\pythonw.exe" goto run

echo Erster Start: Python-Umgebung wird eingerichtet ...
where py >nul 2>nul
if errorlevel 1 goto nolauncher
py -3 -m venv .venv
goto venvdone
:nolauncher
python -m venv .venv
:venvdone
if not exist ".venv\Scripts\python.exe" goto nopython
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto piperror

:run
rem pythonw = ohne Konsolenfenster
start "" ".venv\Scripts\pythonw.exe" -m launchpad_pro_tab %*
exit /b 0

:nopython
echo.
echo FEHLER: Python 3.10 oder neuer wurde nicht gefunden.
echo Bitte von https://www.python.org/downloads/ installieren
echo (Haken bei "Add python.exe to PATH" setzen) und erneut starten.
pause
exit /b 1

:piperror
echo.
echo FEHLER bei der Installation der Abhaengigkeiten (Internetverbindung?).
rmdir /s /q .venv
pause
exit /b 1
