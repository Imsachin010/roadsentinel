import os
import osmnx as ox
import json
import numpy as np

def compute_bearing(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1

    x = np.sin(dlon) * np.cos(lat2)
    y = np.cos(lat1)*np.sin(lat2) - np.sin(lat1)*np.cos(lat2)*np.cos(dlon)

    bearing = np.degrees(np.arctan2(x, y))
    return (bearing + 360) % 360


def load_graph(city_name):
    print(f"Loading road graph for {city_name}...")
    G = ox.graph_from_place(city_name, network_type='drive')

    edges = []

    for u, v, data in G.edges(data=True):
        if 'geometry' in data:
            coords = list(data['geometry'].coords)

            for i in range(len(coords) - 1):
                lon1, lat1 = coords[i]
                lon2, lat2 = coords[i+1]

                bearing = compute_bearing(lat1, lon1, lat2, lon2)

                edges.append({
                    "start": [lat1, lon1],
                    "end": [lat2, lon2],
                    "bearing": bearing,
                    "road_type": data.get("highway", "unknown")
                })

    return edges


if __name__ == "__main__":
    city = "Chennai, India"
    edges = load_graph(city)

    os.makedirs("data", exist_ok=True)

    with open("data/road_graph.json", "w") as f:
        json.dump(edges, f)

    print(f"Saved {len(edges)} road segments.")