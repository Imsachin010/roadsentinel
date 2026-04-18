@echo off
echo ===================================================
echo   RoadSentinel — Cloud-Ready Cockpit Launcher
echo ===================================================
echo.

echo [1/5] Cleaning up stale processes...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5000 " ^| findstr "LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5001 " ^| findstr "LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
)
echo     ✅ Ports 5000 and 5001 cleared.

echo.
echo [2/5] Starting WebSocket Broadcaster (port 5000)...
set PORT=5000
set ENGINE_URL=http://localhost:5001
start "RoadSentinel — Node Broadcaster" cmd /k "cd server && set PORT=5000 && set ENGINE_URL=http://localhost:5001 && node alert-broadcaster.js"
timeout /t 2 /nobreak >nul

echo [3/5] Starting FastAPI Detection Engine (port 5001)...
set PORT=5001
set BROADCASTER_URL=http://localhost:5000
start "RoadSentinel — Detection Engine" cmd /k "call .mahex\Scripts\activate && set PORT=5001 && set BROADCASTER_URL=http://localhost:5000 && python src\detection\main.py"
echo     Waiting 6s for engine to fully boot...
timeout /t 6 /nobreak >nul

echo [4/5] Starting React Dashboard (port 3000)...
:: Vite uses VITE_ prefix for client-side env vars
start "RoadSentinel — Dashboard" cmd /k "cd dashboard && set VITE_BROADCASTER_URL=http://localhost:5000 && npm run dev"
timeout /t 3 /nobreak >nul

echo [5/5] Starting Telemetry Simulator...
set DETECTION_URL=http://localhost:5001
start "RoadSentinel — Simulator" cmd /k "call .mahex\Scripts\activate && set DETECTION_URL=http://localhost:5001 && python scripts\simulate_traces.py"

echo.
echo ===================================================
echo   ✅ ALL SYSTEMS ONLINE (LOCAL MODE)
echo.
echo   Environment: Cloud-Ready (Env-Aware)
echo   Dashboard  →  http://localhost:3000
echo   Engine API →  http://localhost:5001/docs
echo   Node WS    →  http://localhost:5000
echo ===================================================
timeout /t 5 /nobreak >nul
exit
