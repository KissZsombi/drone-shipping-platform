from __future__ import annotations

import json
import os
import time
from math import atan2, cos, radians, sin, sqrt
from pathlib import Path
from typing import Dict, List, Tuple

import paho.mqtt.client as mqtt

BROKER_HOST = os.getenv("MQTT_HOST", "broker.hivemq.com")
BROKER_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "dron/utvonal")
POINTS_FILE = Path(__file__).resolve().parents[1] / "dronoptimalisut.txt"
HUB_LOCATION = {"name": "GLS Hungary", "lon": 19.160145, "lat": 47.340793}


def haversine_distance_m(coord_a: Tuple[float, float], coord_b: Tuple[float, float]) -> float:
    """Calculate approximate great-circle distance between two coordinates in meters."""
    lon1, lat1 = map(radians, coord_a)
    lon2, lat2 = map(radians, coord_b)
    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    earth_radius_m = 6_371_000
    return earth_radius_m * c


def load_points() -> List[Dict[str, float]]:
    if not POINTS_FILE.exists():
        raise FileNotFoundError(f"Missing points file: {POINTS_FILE}")

    points: List[Dict[str, float]] = []
    with POINTS_FILE.open(encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 3:
                continue
            try:
                lon = float(parts[1])
                lat = float(parts[2])
            except ValueError:
                continue
            points.append({"name": parts[0], "lon": lon, "lat": lat})
    return points


def publish_route(points: List[Dict[str, float]]) -> None:
    client = mqtt.Client()
    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
    print(f"Connected to MQTT broker {BROKER_HOST}:{BROKER_PORT}")

    previous_name = HUB_LOCATION["name"]
    previous_coord = (HUB_LOCATION["lon"], HUB_LOCATION["lat"])

    for point in points:
        coord = (point["lon"], point["lat"])
        distance = round(haversine_distance_m(previous_coord, coord), 2)

        payload = {
            "previous": previous_name,
            "next": point["name"],
            "coordinates": {"x": point["lon"], "y": point["lat"]},
            "distance": distance,
        }

        client.publish(MQTT_TOPIC, json.dumps(payload))
        print(f"Published telemetry: {payload}")
        time.sleep(0.5)

        previous_name = point["name"]
        previous_coord = coord

    route_payload = {"route": [point["name"] for point in points]}
    client.publish(MQTT_TOPIC, json.dumps(route_payload))
    print(f"Published route summary: {route_payload}")

    client.disconnect()
    print("MQTT connection closed.")


def main() -> None:
    points = load_points()
    if not points:
        raise RuntimeError("No delivery points found in dronoptimalisut.txt")
    publish_route(points)


if __name__ == "__main__":
    main()
