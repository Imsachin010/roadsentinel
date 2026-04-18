from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import json
import time
import sys
import os
import requests
import math

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.utils.geo import angular_difference, haversine
from src.utils.scoring import compute_score

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# CONFIG
THRESHOLD = 3.5     # raised: reduces false positives on normal traffic
NEARBY_RADIUS = 25  # meters
TEMPORAL_WINDOW = 3

BROADCASTER_URL = os.getenv("BROADCASTER_URL", "http://localhost:5000")
PORT = int(os.getenv("PORT", 5001))

# GLOBAL STATE
history = {}
graph = []
prev_heading = {}
confidence_ramp = {}   # tracks how many times each vehicle has fired an alert
SCENARIO = "normal"   # normal | ghost | false_positive

def load_graph(path):
    with open(path, "r") as f:
        return json.load(f)

# Load graph at startup
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
graph_path = os.path.join(base_dir, "data", "road_graph.json")
try:
    graph = load_graph(graph_path)
    print(f"Loaded road graph with {len(graph)} segments.")
except Exception as e:
    print(f"Could not load graph: {e}")

def get_nearby_segments(lat, lon, road_graph):
    nearby = []
    for seg in road_graph:
        s_lat, s_lon = seg["start"]
        dist = haversine(lat, lon, s_lat, s_lon)
        if dist < NEARBY_RADIUS:
            nearby.append(seg)
    return nearby

def velocity_vector(speed, heading):
    """Returns (vx, vy) in m/s — heading in degrees from North."""
    rad = math.radians(heading)
    return (speed * math.cos(rad), speed * math.sin(rad))

def compute_ttc(intruder, other):
    """True relative-velocity TTC. Gate: Δθ>150°, dist<500m."""
    delta_theta = angular_difference(intruder["heading"], other["heading"])
    if delta_theta <= 150:
        return None  # Not opposing traffic

    dist = haversine(intruder["lat"], intruder["lon"], other["lat"], other["lon"])
    if dist > 500:
        return None  # Too far to matter

    v1 = velocity_vector(intruder["speed"], intruder["heading"])
    v2 = velocity_vector(other["speed"],   other["heading"])

    rel_vx = v1[0] - v2[0]
    rel_vy = v1[1] - v2[1]
    rel_speed = math.sqrt(rel_vx**2 + rel_vy**2)

    if rel_speed < 0.1:
        return None

    return dist / rel_speed   # seconds

def find_collision_risk(intruder_v, frame):
    """Find the closest head-on vehicle and return TTC."""
    best_ttc  = float('inf')
    target_id = None

    for v in frame:
        if v["vehicle_id"] == intruder_v["vehicle_id"]:
            continue
        ttc = compute_ttc(intruder_v, v)
        if ttc is not None and ttc < best_ttc:
            best_ttc  = ttc
            target_id = v["vehicle_id"]

    if target_id is not None and best_ttc < 60:
        return {"target_id": target_id, "time_to_impact": round(best_ttc, 1)}
    return None

def send_alert(vehicle, avg_score, road_type, collision_warning=None):
    vid = vehicle["vehicle_id"]

    # Gradual confidence ramp — grows 0.15/alert, caps at 1.0
    ramp = confidence_ramp.get(vid, 0)
    ramp = min(ramp + 0.15, 1.0)
    confidence_ramp[vid] = ramp

    # Scale raw score into [0,1] then blend with ramp for natural evolution
    raw_conf = min(avg_score / 5.0, 1.0)
    confidence = round(raw_conf * ramp, 2)     # starts low → rises each frame
    severity   = "HIGH" if confidence > 0.7 else "MEDIUM"

    payload = {
        "vehicle_id": vid,
        "lat":  vehicle["lat"],
        "lon":  vehicle["lon"],
        "confidence": confidence,
        "road_type":  road_type,
        "severity":   severity,
        "timestamp":  vehicle.get("timestamp", 0),
        "is_intruder": vehicle.get("is_intruder", False)
    }
    if collision_warning:
        payload["collision_warning"] = collision_warning

    try:
        requests.post(f"{BROADCASTER_URL}/alert", json=payload)
    except Exception as e:
        print("Alert send failed:", e)

@app.get("/scenario")
async def get_scenario():
    return {"scenario": SCENARIO}

@app.post("/scenario")
async def set_scenario(request: Request):
    global SCENARIO, history, prev_heading, confidence_ramp
    body = await request.json()
    SCENARIO = body.get("scenario", "normal")
    history = {}
    prev_heading = {}
    confidence_ramp = {}       # reset ramp so new vehicles start fresh
    print(f"🎬 Scenario switched to: {SCENARIO.upper()}")
    return {"status": "ok", "scenario": SCENARIO}

@app.post("/stream")
async def process_stream(request: Request):
    global history
    frame = await request.json()
    
    for v in frame:
        vid = v["vehicle_id"]
        lat = v["lat"]
        lon = v["lon"]
        heading = v["heading"]
        speed = v["speed"]

        if speed < 2:
            continue

        if vid in prev_heading:
            if angular_difference(prev_heading[vid], heading) > 150 and speed < 5:
                continue
        prev_heading[vid] = heading

        segments = get_nearby_segments(lat, lon, graph)
        score = 0
        best_road_type = "unknown"

        for seg in segments:
            delta = angular_difference(heading, seg["bearing"])
            if delta > 140:   # tighter gate: must be clearly opposing (was 120)
                score += compute_score(delta, speed, seg["road_type"])
                best_road_type = seg.get("road_type", "unknown")

        # TEMPORAL FILTER
        if vid not in history:
            history[vid] = []

        history[vid].append(score)

        if len(history[vid]) > TEMPORAL_WINDOW:
            history[vid].pop(0)

        avg_score = sum(history[vid]) / len(history[vid])

        # ALERT
        if avg_score > THRESHOLD:
            print(f"🚨 WRONG WAY DETECTED: Vehicle {vid} - Score: {avg_score:.2f} | Conf: {min(avg_score/5.0,1.0)*100:.0f}% | Road: {best_road_type}")
            col_risk = find_collision_risk(v, frame)
            send_alert(v, avg_score, best_road_type, collision_warning=col_risk)

    # Forward telemetry to broadcasting server
    try:
        requests.post(f"{BROADCASTER_URL}/telemetry", json=frame)
    except Exception as e:
        pass

    return {"status": "success", "processed_vehicles": len(frame)}

if __name__ == "__main__":
    import uvicorn
    print(f"🚀 Detection Engine starting on port {PORT}...")
    print(f"📡 Forwarding alerts to: {BROADCASTER_URL}")
    uvicorn.run(app, host="0.0.0.0", port=PORT)