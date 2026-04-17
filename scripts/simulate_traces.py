import json
import random
import time
import math
import os
import requests

# ---------------------------
# CONFIG
# ---------------------------
NUM_VEHICLES = 20
NUM_INTRUDERS = 3
DURATION = 120  # seconds
STEP_TIME = 1   # seconds


# ---------------------------
# HELPERS
# ---------------------------
def move_point(lat, lon, bearing, distance_m):
    R = 6378.1  # km
    bearing = math.radians(bearing)

    lat1 = math.radians(lat)
    lon1 = math.radians(lon)

    lat2 = math.asin(
        math.sin(lat1)*math.cos(distance_m/1000/R) +
        math.cos(lat1)*math.sin(distance_m/1000/R)*math.cos(bearing)
    )

    lon2 = lon1 + math.atan2(
        math.sin(bearing)*math.sin(distance_m/1000/R)*math.cos(lat1),
        math.cos(distance_m/1000/R)-math.sin(lat1)*math.sin(lat2)
    )

    return math.degrees(lat2), math.degrees(lon2)


def add_noise(val, noise=0.00005):
    return val + random.uniform(-noise, noise)


# ---------------------------
# LOAD ROAD GRAPH
# ---------------------------
def load_graph():
    with open("data/road_graph.json", "r") as f:
        return json.load(f)


# ---------------------------
# INIT VEHICLES
# ---------------------------
def init_vehicles(graph):
    vehicles = []

    intruder_ids = set(random.sample(range(NUM_VEHICLES), NUM_INTRUDERS))

    for vid in range(NUM_VEHICLES):
        seg = random.choice(graph)

        lat, lon = seg["start"]
        bearing = seg["bearing"]

        if vid in intruder_ids:
            # flip direction (WRONG WAY)
            bearing = (bearing + 180) % 360

        vehicles.append({
            "vehicle_id": vid,
            "lat": lat,
            "lon": lon,
            "bearing": bearing,
            "speed": random.uniform(8, 20),  # m/s (~30–70 km/h)
            "is_intruder": vid in intruder_ids
        })

    return vehicles


# ---------------------------
# SIMULATION LOOP
# ---------------------------
def simulate(graph):
    vehicles = init_vehicles(graph)
    traces = []

    for t in range(DURATION):
        timestamp = int(time.time()) + t

        frame = []

        for v in vehicles:
            # move vehicle
            new_lat, new_lon = move_point(
                v["lat"], v["lon"], v["bearing"], v["speed"]
            )

            v["lat"], v["lon"] = new_lat, new_lon

            # add GPS noise
            noisy_lat = add_noise(new_lat)
            noisy_lon = add_noise(new_lon)

            frame.append({
                "vehicle_id": v["vehicle_id"],
                "lat": noisy_lat,
                "lon": noisy_lon,
                "heading": v["bearing"],
                "speed": v["speed"],
                "timestamp": timestamp,
                "is_intruder": v["is_intruder"]  # for debugging
            })

        try:
            requests.post("http://localhost:5001/stream", json=frame)
            print(f"Sent time {t} frame with {len(frame)} vehicles.")
        except Exception as e:
            print(f"Failed to send frame: {e}")
        
        time.sleep(STEP_TIME)

# ---------------------------
# MAIN
# ---------------------------
if __name__ == "__main__":
    graph = load_graph()

    print("Simulating live vehicle traces...")
    simulate(graph)
    print("Simulation complete.")