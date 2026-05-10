@echo off
:: ─────────────────────────────────────────────
::  Fosk — start server (Windows)
::  Usage: start.cmd [port]
:: ─────────────────────────────────────────────

setlocal

set PORT=%~1
if "%PORT%"=="" set PORT=8000

:: Move to script directory
cd /d "%~dp0"

:: Create venv if not present
if not exist ".venv\" (
    echo [*] Creating virtual environment...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt -q
) else (
    call .venv\Scripts\activate.bat
)

:: Retrieve local IP address
for /f "tokens=2 delims=:" %%i in ('ipconfig ^| findstr /i "IPv4" ^| findstr /v "169.254"') do (
    set LAN_IP=%%i
    goto :got_ip
)
:got_ip
set LAN_IP=%LAN_IP: =%

echo.
echo  +==========================================+
echo  ^|    Fosk Music Server  v1.0              ^|
echo  +==========================================+
echo  ^|  LAN:   http://%LAN_IP%:%PORT%
echo  ^|  Local: http://127.0.0.1:%PORT%
echo  +==========================================+
echo.

:: Start server in background, then open browser at LAN address
start "Fosk Server" /b uvicorn main:app --host 0.0.0.0 --port %PORT%

:: Wait 2 seconds for the server to be ready, then open browser
timeout /t 2 /nobreak >nul
start "" http://%LAN_IP%:%PORT%

:: Re-attach: keep window open until CTRL+C
:keepalive
timeout /t 5 /nobreak >nul
goto :keepalive

endlocal
