from __future__ import annotations

import json
import logging
from typing import Dict, Iterable, List, Sequence, Tuple

from paho.mqtt.client import Client

from backend import models

logger = logging.getLogger("backend.route_planner")


def haversine_km(coord_a: Tuple[float, float], coord_b: Tuple[float, float]) -> float:
    """Great-circle distance in kilometers between two (lat, lon) coordinates."""
    from math import atan2, cos, radians, sin, sqrt

    lat1, lon1 = map(radians, coord_a)
    lat2, lon2 = map(radians, coord_b)
    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    earth_radius_km = 6371.0
    return earth_radius_km * c


def effective_capacity_km(drone: models.Drone, payload_kg: float) -> float:
    """Compute effective full-charge range based on current payload."""
    if drone.max_payload_kg <= 0:
        return 0.0
    factor = 1 - 0.5 * max(payload_kg, 0.0) / drone.max_payload_kg
    return max(10.0, drone.base_range_km * factor)


def consumption_factor(payload_kg: float, drone: models.Drone) -> float:
    """Multiplier for energy use based on payload."""
    if drone.max_payload_kg <= 0:
        return 1.0
    return 1 + 0.3 * min(1.0, max(payload_kg, 0.0) / drone.max_payload_kg)


def calc_battery_pct(remaining_range_km: float, capacity_km: float) -> float:
    if capacity_km <= 0:
        return 0.0
    return max(0.0, min(100.0, (remaining_range_km / capacity_km) * 100.0))


def plan_route_with_recharges(
    locations: Sequence[models.Location],
    station: models.Station,
    drone: models.Drone,
    weights_by_location_id: Dict[int, float],
    safety_margin_ratio: float = 0.05,
) -> List[Dict[str, object]]:
    """Nearest-neighbour planner with battery and recharge at station."""
    remaining = [(loc, float(weights_by_location_id.get(loc.id, 0.0))) for loc in locations]
    station_coord = (station.lat, station.lon)
    current_coord = station_coord
    current_name = station.name
    total_payload = sum(weight for _, weight in remaining)
    capacity_km = effective_capacity_km(drone, total_payload)
    remaining_range_km = capacity_km
    cumulative_km = 0.0
    steps: List[Dict[str, object]] = []

    def append_step(prev_name: str, next_name: str, next_coord: Tuple[float, float], distance_km: float) -> None:
        nonlocal cumulative_km, remaining_range_km, capacity_km
        cumulative_km += distance_km
        battery_pct = calc_battery_pct(remaining_range_km, capacity_km)
        steps.append(
            {
                "previous": prev_name,
                "next": next_name,
                "coordinates": {"x": next_coord[1], "y": next_coord[0]},
                "distance": round(distance_km * 1000, 2),
                "distance_km": round(distance_km, 3),
                "cumulative_distance_km": round(cumulative_km, 3),
                "battery_pct": round(battery_pct, 1),
                "speed_kmh": drone.speed_kmh,
                "drone_id": drone.id,
                "max_payload_kg": drone.max_payload_kg,
                "base_range_km": drone.base_range_km,
                "payload_kg": round(total_payload, 3),
            }
        )

    while remaining:
        safety_margin_km = capacity_km * safety_margin_ratio
        feasible = []
        for loc, weight in remaining:
            dist_to_next = haversine_km(current_coord, (loc.lat, loc.lon))
            dist_back = haversine_km((loc.lat, loc.lon), station_coord)
            if dist_to_next + dist_back <= remaining_range_km - safety_margin_km:
                feasible.append((loc, weight, dist_to_next))

        if not feasible:
            if current_coord != station_coord:
                # Return to station to recharge.
                back_km = haversine_km(current_coord, station_coord)
                remaining_range_km = max(
                    0.0,
                    remaining_range_km - back_km * consumption_factor(total_payload, drone),
                )
                append_step(current_name, station.name, station_coord, back_km)
                current_coord = station_coord
                current_name = station.name
            # Recharge with current payload.
            capacity_km = effective_capacity_km(drone, total_payload)
            remaining_range_km = capacity_km
            # If still nothing feasible from the hub, abort to avoid infinite loop.
            if current_coord == station_coord and not any(
                haversine_km(station_coord, (loc.lat, loc.lon))
                + haversine_km((loc.lat, loc.lon), station_coord)
                <= remaining_range_km - capacity_km * safety_margin_ratio
                for loc, _w in remaining
            ):
                logger.warning("No feasible targets within range for current payload; aborting planning.")
                break
            continue

        next_loc, weight, dist_to_next = min(feasible, key=lambda item: item[2])
        # Consume battery based on payload.
        remaining_range_km = max(
            0.0,
            remaining_range_km - dist_to_next * consumption_factor(total_payload, drone),
        )
        append_step(current_name, next_loc.name, (next_loc.lat, next_loc.lon), dist_to_next)

        total_payload = max(0.0, total_payload - weight)
        remaining_range_km = min(remaining_range_km, capacity_km)
        current_coord = (next_loc.lat, next_loc.lon)
        current_name = next_loc.name
        remaining = [(loc, w) for loc, w in remaining if loc.id != next_loc.id]

    if current_coord != station_coord:
        back_km = haversine_km(current_coord, station_coord)
        remaining_range_km = max(
            0.0,
            remaining_range_km - back_km * consumption_factor(total_payload, drone),
        )
        append_step(current_name, station.name, station_coord, back_km)

    return steps


def publish_route_mqtt(
    client: Client,
    steps: Sequence[Dict[str, object]],
    topic: str,
) -> None:
    """Publish each step plus a final route summary to the MQTT topic."""
    route_names: List[str] = []
    for step in steps:
        if step.get("next") is not None:
            route_names.append(step["next"])  # type: ignore[arg-type]
        result = client.publish(topic, json.dumps(step))
        if result.rc != 0:
            logger.warning("Failed to publish step to %s: rc=%s", topic, result.rc)

    summary_payload = {"route": route_names}
    client.publish(topic, json.dumps(summary_payload))
