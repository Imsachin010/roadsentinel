from fastapi import FastAPI, Request
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

THRESHOLD = 2.5
NEARBY_RADIUS = 25  # meters
TEMPORAL_WINDOW = 3

# GLOBAL STATE
history = {}
graph = []

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

def send_alert(vehicle, collision_warning=None):
    payload = {
        "vehicle_id": vehicle["vehicle_id"],
        "lat": vehicle["lat"],
        "lon": vehicle["lon"],
        "confidence": 1.0,
        "timestamp": vehicle["timestamp"],
        "is_intruder": vehicle.get("is_intruder", False)
    }
    if collision_warning:
        payload["collision_warning"] = collision_warning

    try:
        requests.post("http://localhost:5000/alert", json=payload)
    except Exception as e:
        print("Alert send failed:", e)

def find_collision_risk(intruder_v, frame):
    min_t = float('inf')
    target_id = None

    for v in frame:
        if v["vehicle_id"] == intruder_v["vehicle_id"]:
            continue
            
        delta_theta = angular_difference(intruder_v["heading"], v["heading"])
        if delta_theta > 150: # Opposing direction
            dist = haversine(intruder_v["lat"], intruder_v["lon"], v["lat"], v["lon"])
            if dist < 500: # Within 500 meters
                # Calculate relative velocity
                vx1 = intruder_v["speed"] * math.cos(math.radians(intruder_v["heading"]))
                vy1 = intruder_v["speed"] * math.sin(math.radians(intruder_v["heading"]))
                vx2 = v["speed"] * math.cos(math.radians(v["heading"]))
                vy2 = v["speed"] * math.sin(math.radians(v["heading"]))
                
                v_rel = math.sqrt((vx1 - vx2)**2 + (vy1 - vy2)**2)
                if v_rel > 0:
                    t = dist / v_rel
                    if t < min_t:
                        min_t = t
                        target_id = v["vehicle_id"]
                        
    if target_id is not None and min_t < 60: # Limit to 60s
        return { "target_id": target_id, "time_to_impact": min_t }
    return None

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

        segments = get_nearby_segments(lat, lon, graph)
        score = 0

        for seg in segments:
            delta = angular_difference(heading, seg["bearing"])
            if delta > 120:
                score += compute_score(delta, speed, seg["road_type"])

        # TEMPORAL FILTER
        if vid not in history:
            history[vid] = []

        history[vid].append(score)

        if len(history[vid]) > TEMPORAL_WINDOW:
            history[vid].pop(0)

        avg_score = sum(history[vid]) / len(history[vid])

        # ALERT
        if avg_score > THRESHOLD:
            print(f"🚨 WRONG WAY DETECTED: Vehicle {vid} - Score: {avg_score:.2f}")
            col_risk = find_collision_risk(v, frame)
            send_alert(v, collision_warning=col_risk)

    # Forward telemetry to broadcasting server
    try:
        requests.post("http://localhost:5000/telemetry", json=frame)
    except Exception as e:
        pass

    return {"status": "success", "processed_vehicles": len(frame)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)