@echo off
setlocal
rem --- Jarvis one-click launcher (Windows, repo root) ---
rem Starts: visualizer server + visualizer window + the voice line (brain).
set PORT=8777
set URL=http://127.0.0.1:%PORT%
set REPO=%~dp0
set VIZ=%REPO%voice-visualizer
set LOG=%TEMP%\jarvis-visualizer.log
set KPROFILE=%TEMP%\jarvis-kiosk-profile

rem Prefer the repo venv (the voice line needs its packages); fall back to system python.
set VENV_PY=%REPO%.venv\Scripts\python.exe
if exist "%VENV_PY%" ( set "PY=%VENV_PY%" ) else ( set "PY=python" )

rem --- 1) visualizer server (only if the port isn't already answering) ---
powershell -NoProfile -Command "try{(New-Object Net.Sockets.TcpClient).Connect('127.0.0.1',%PORT%);exit 0}catch{exit 1}" >nul 2>&1
if errorlevel 1 (
  echo [launch] starting visualizer server on %PORT% ...
  start "" /b cmd /c ""%PY%" "%VIZ%\server.py" > "%LOG%" 2>&1"
  powershell -NoProfile -Command "Start-Sleep -Milliseconds 900" >nul 2>&1
) else (
  echo [launch] visualizer server already running on %PORT%
)

rem --- 2) visualizer window (movable / minimizable; F11 for fullscreen) ---
set CHROME=
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" set CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe
if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" set CHROME=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe
if exist "%LocalAppData%\Google\Chrome\Application\chrome.exe" set CHROME=%LocalAppData%\Google\Chrome\Application\chrome.exe
if defined CHROME (
  echo [launch] opening Jarvis window ...
  start "" "%CHROME%" --app="%URL%" --new-window --user-data-dir="%KPROFILE%" --window-size=1280,800 --window-position=120,80 --no-first-run --no-default-browser-check --disable-extensions --autoplay-policy=no-user-gesture-required
) else (
  echo [launch] Chrome not found - opening default browser. Press F11 to go fullscreen.
  start "" "%URL%"
)

rem --- 3) the voice line / brain (own window shows its logs; watch init on screen) ---
if not exist "%VENV_PY%" echo [launch] WARNING: .venv not found - the voice line may miss its dependencies.
echo [launch] starting Jarvis voice line ...
rem Add --ptt below if you prefer press-Enter-to-talk instead of "Hey Jarvis".
start "Jarvis Voice Line" cmd /k ""%PY%" "%REPO%voice-line\voice_line.py""

echo [launch] up. The visualizer shows initialization; Jarvis greets you when ready.
endlocal
