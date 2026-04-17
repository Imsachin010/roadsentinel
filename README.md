# 🚗 RoadSentinel

**RoadSentinel** is a high-performance, real-time spatial awareness system designed to detect wrong-way drivers and calculate trajectory collision paths asynchronously, fundamentally improving road safety through geometry without relying on heavy Machine Learning computer vision models.

This dynamic repository represents a product-ready **Connected Cockpit** simulation that operates directly on geospatial physics, capable of calculating precise threat radii and impending crashes.

---

## ⚡ Core Features

* **Real-Time Telemetry Streaming**: Autonomous trace generation broadcasting dynamic GPS coordinates and orientations for fleet analytics.
* **Geospatial Detection Engine (FastAPI)**: Utilizing vector physics, Haversine spatial distances, and rotational thresholds to accurately filter and identify topological traffic violations.
* **Collision Prediction Engine**: Mathematical modeling computes Relative Velocity collision vectors in real-time ($T = d / v_{rel}$), emitting warnings strictly upon head-on intersect alignments ($\Delta\theta > 150^\circ$).
* **WebSocket Broadcaster**: Ultra-low latency NodeJS bridge synchronizing Python analytics directly pushing event-driven data to frontend clients.
* **Connected Cockpit UI**: A stunning React Leaflet interactive map rendering live traffic flows using CSS transformed directional matrices `➤` and red/yellow warning tethers upon active threat evaluations.
* **Offline Metric Validation**: A built-in batch testing script that mathematically tracks `True Positives`, `Precision`, and `Recall`.

---

## 🏗️ System Architecture

1. **Simulator (`scripts/simulate_traces.py`)** -> Sends live frames.
2. **Detection AI Brain (`src/detection/main.py`)** -> Assesses constraints, calculates crash vectors.
3. **Broadcaster (`server/alert-broadcaster.js`)** -> Maps REST hooks to WS channels.
4. **Dashboard (`dashboard/src/App.jsx`)** -> Consumes streams and visually maps the data.

---

## 🚀 Quick Start Guide

We have bundled the entire 4-microservice infrastructure into a single orchestrator script. 

### Prerequisites:
* **Node.js** (v18+)
* **Python 3.9+** (Activated `.mahex` environment).

### One-Click Launch (Windows)

Simply double-click the included orchestrator or run it from the root terminal:
```bash
.\start.bat
```
*This will organically spin up the Node runtime, Vite Dashboard, Python Engine, and Simulation Loop synchronously.*

### Manual Startup

If you prefer to start the servers independently across 4 terminals:

1. **Start the WebSockets**
```bash
cd server
node alert-broadcaster.js
```
2. **Start the Dashboard**
```bash
cd dashboard
npm run dev
```
3. **Start the AI Detection Engine**
```bash
call .mahex\Scripts\activate
python src/detection/main.py
```
4. **Start the Simulator** (Traffic Data)
```bash
call .mahex\Scripts\activate
python scripts/simulate_traces.py
```

---

## 📊 Offline Evaluation Validation

To evaluate the mathematical rigor of the anomaly detection threshold under stress:
```bash
call .mahex\Scripts\activate
python scripts\evaluate.py
```
This isolates the physics formulas and prints out statistical benchmarks outlining precision against large simulated datasets.

---

## 🛠️ Built With

* **Backend**: Python 3.10, FastAPI, Requests.
* **Frontend**: React 18, Vite, React-Leaflet, Leaflet.js.
* **Middleware**: Node.js, Express, Socket.io.
* **Math Components**: Haversine metrics, angular difference isolation logic.

---
*Developed as a top-tier hackathon demonstration for live traffic interception & intervention systems.*
