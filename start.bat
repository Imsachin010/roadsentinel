@echo off
echo ===================================================
echo 🚀 Starting RoadSentinel Live Cockpit Data Stack...
echo ===================================================

echo Starting WebSocket Broadcaster...
start "WebSocket Broadcaster" cmd /k "cd server && node alert-broadcaster.js"

echo Starting React Dashboard...
start "React Dashboard" cmd /k "cd dashboard && npm run dev"

echo Starting Python FastAPI Detection Engine...
start "Detection Engine" cmd /k "call .mahex\Scripts\activate && python src\detection\main.py"

echo Waiting 4 seconds for Detection Engine to properly boot up...
timeout /t 4 /nobreak >nul

echo Starting Telemetry Simulator...
start "Telemetry Simulator" cmd /k "call .mahex\Scripts\activate && python scripts\simulate_traces.py"

echo.
echo ✅ All systems launched!
echo ✅ Dashboard should be running at http://localhost:3000
echo.
echo You can safely close this orchestrator window. The 4 dedicated terminal windows will remain open so you can easily trace their logs during the presentation!
exit
