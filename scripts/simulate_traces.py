import json
import random
import time
import math
import os
import requests

# ---------------------------
# CONFIG
# ---------------------------
DATA_PATH = "data/road_graph.json"
DETECTION_URL = os.getenv("DETECTION_URL", "http://localhost:5001")
NUM_VEHICLES = 20
STEP_TIME = 1   # seconds

# ---------------------------
# HELPERS
# ---------------------------
def move_point(lat, lon, bearing, distance_m):
    R = 6378.1
    bearing_rad = math.radians(bearing)
    lat1, lon1 = math.radians(lat), math.radians(lon)
    lat2 = math.asin(
        math.sin(lat1)*math.cos(distance_m/1000/R) +
        math.cos(lat1)*math.sin(distance_m/1000/R)*math.cos(bearing_rad)
    )
    lon2 = lon1 + math.atan2(
        math.sin(bearing_rad)*math.sin(distance_m/1000/R)*math.cos(lat1),
        math.cos(distance_m/1000/R)-math.sin(lat1)*math.sin(lat2)
    )
    return math.degrees(lat2), math.degrees(lon2)

def add_noise(val, noise=0.00005):
    return val + random.uniform(-noise, noise)

def load_graph():
    with open(DATA_PATH, "r") as f:
        return json.load(f)

def get_scenario():
    try:
        r = requests.get(f"{DETECTION_URL}/scenario", timeout=1)
        return r.json().get("scenario", "normal")
    except:
        return "normal"

# ---------------------------
# INIT VEHICLES
# ---------------------------
def init_vehicles(graph, scenario="normal"):
    vehicles = []

    if scenario == "ghost":
        num_intruders = 1    # ONE ghost driver — clear, dramatic, memorable
    else:
        num_intruders = 0    # normal + false_positive both start clean

    intruder_ids = set(random.sample(range(NUM_VEHICLES), num_intruders)) if num_intruders > 0 else set()

    for vid in range(NUM_VEHICLES):
        seg = random.choice(graph)
        lat, lon = seg["start"]
        bearing = seg["bearing"]

        if vid in intruder_ids:
            bearing = (bearing + 180) % 360  # WRONG WAY

        vehicles.append({
            "vehicle_id": vid,
            "lat": lat,
            "lon": lon,
            "bearing": bearing,
            "orig_bearing": bearing,
            "speed": random.uniform(8, 20),
            "is_intruder": vid in intruder_ids
        })

    return vehicles

# ---------------------------
# SIMULATION LOOP
# ---------------------------
def simulate(graph):
    # Start with current scenario
    current_scenario = get_scenario()
    vehicles = init_vehicles(graph, current_scenario)
    print(f"[Simulator] Starting with scenario: {current_scenario.upper()}")

    t = 0
    while True:
        new_scenario = get_scenario()

        # Re-init vehicles when scenario changes
        if new_scenario != current_scenario:
            print(f"\n[Simulator] Scenario changed: {current_scenario.upper()} → {new_scenario.upper()}")
            current_scenario = new_scenario
            vehicles = init_vehicles(graph, current_scenario)
            t = 0

        timestamp = int(time.time())
        frame = []

        for v in vehicles:
            # FALSE POSITIVE TEST: at t==20, do a slow U-turn on vehicle 0
            if current_scenario == "false_positive" and t == 20 and v["vehicle_id"] == 0:
                print("[Simulator] 🟡 Injecting U-turn (False Positive Test)...")
                v["bearing"] = (v["bearing"] + 180) % 360
                v["speed"] = 3  # slow — should be filtered by U-turn guard

            # Move vehicle
            new_lat, new_lon = move_point(v["lat"], v["lon"], v["bearing"], v["speed"])
            v["lat"], v["lon"] = new_lat, new_lon

            frame.append({
                "vehicle_id": v["vehicle_id"],
                "lat": add_noise(new_lat),
                "lon": add_noise(new_lon),
                "heading": v["bearing"],
                "speed": v["speed"],
                "timestamp": timestamp,
                "is_intruder": v["is_intruder"]
            })

        try:
            resp = requests.post(f"{DETECTION_URL}/stream", json=frame)
            print(f"[{current_scenario.upper()}] t={t:03d} | {len(frame)} vehicles | HTTP {resp.status_code}")
        except Exception as e:
            print(f"[Simulator] Send failed: {e}")

        t += 1
        time.sleep(STEP_TIME)

# ---------------------------
# MAIN
# ---------------------------
if __name__ == "__main__":
    graph = load_graph()
    print("🚗 RoadSentinel Simulator starting (scenario-aware)...")
    simulate(graph)