@echo off
echo ===================================================
echo   RoadSentinel — Cockpit System Launcher
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
start "RoadSentinel — Node Broadcaster" cmd /k "cd server && node alert-broadcaster.js"
timeout /t 2 /nobreak >nul

echo [3/5] Starting FastAPI Detection Engine (port 5001)...
start "RoadSentinel — Detection Engine" cmd /k "call .mahex\Scripts\activate && python src\detection\main.py"
echo     Waiting 6s for engine to fully boot with road graph...
timeout /t 6 /nobreak >nul

echo [4/5] Starting React Dashboard (port 3000)...
start "RoadSentinel — Dashboard" cmd /k "cd dashboard && npm run dev"
timeout /t 3 /nobreak >nul

echo [5/5] Starting Telemetry Simulator...
start "RoadSentinel — Simulator" cmd /k "call .mahex\Scripts\activate && python scripts\simulate_traces.py"

echo.
echo ===================================================
echo   ✅ ALL SYSTEMS ONLINE
echo.
echo   Dashboard  →  http://localhost:3000
echo   Engine API →  http://localhost:5001/docs
echo   Node WS    →  http://localhost:5000
echo.
echo   Scenario buttons should now work immediately.
echo ===================================================
timeout /t 5 /nobreak >nul
exit
