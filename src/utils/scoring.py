def road_weight(road_type):
    if isinstance(road_type, list):
        road_type = road_type[0]

    weights = {
        "motorway": 3.0,
        "trunk": 2.5,
        "primary": 2.0,
        "secondary": 1.5,
        "residential": 1.0
    }

    return weights.get(road_type, 1.0)


def compute_score(delta, speed, road_type):
    if speed < 2:  # ignore slow vehicles
        return 0

    base = (delta / 180)

    return base * road_weight(road_type) * (speed / 10)