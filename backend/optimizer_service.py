from __future__ import annotations

from math import atan2, cos, radians, sin, sqrt
from typing import Dict, List, Tuple

from sqlalchemy.orm import Session, joinedload

from backend import models


def haversine_km(coord_a: Tuple[float, float], coord_b: Tuple[float, float]) -> float:
    """Calculate great-circle distance between two (lat, lon) coordinates in kilometers."""
    lat1, lon1 = map(radians, coord_a)
    lat2, lon2 = map(radians, coord_b)
    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    earth_radius_km = 6371.0
    return earth_radius_km * c


def effective_range_km(base_range_km: float, weight_kg: float, max_payload_kg: float) -> float:
    """Simple range model that reduces range linearly with payload."""
    if max_payload_kg <= 0:
        return 0.0
    factor = 1 - 0.5 * (weight_kg / max_payload_kg)
    return max(0.0, base_range_km * factor)


def plan_orders_for_county(county_id: int, session: Session) -> Dict[str, object]:
    """
    Load pending/planned orders for a county, check range constraints, and compute a visit order.

    Returns:
        {
            "station": {"id": ..., "name": ..., "lat": ..., "lon": ...} | None,
            "planned_orders": [ ... ordered list ... ],
            "too_far": [order_id, ...],
        }
    """
    station = (
        session.query(models.Station)
        .filter(models.Station.county_id == county_id)
        .order_by(models.Station.id)
        .first()
    )

    if not station:
        return {"station": None, "planned_orders": [], "too_far": []}

    orders = (
        session.query(models.Order)
        .options(
            joinedload(models.Order.origin_location),
            joinedload(models.Order.destination_location),
            joinedload(models.Order.drone).joinedload(models.Drone.station),
        )
        .filter(models.Order.county_id == county_id, models.Order.status.in_(["pending", "planned"]))
        .all()
    )

    if not orders:
        return {
            "station": {"id": station.id, "name": station.name, "lat": station.lat, "lon": station.lon},
            "planned_orders": [],
            "too_far": [],
        }

    remaining: List[models.Order] = orders.copy()
    planned_output: List[Dict[str, object]] = []
    too_far: List[int] = []
    station_coord = (station.lat, station.lon)
    current_coord = station_coord

    while remaining:
        next_order = min(
            remaining,
            key=lambda order: haversine_km(
                current_coord,
                (order.origin_location.lat, order.origin_location.lon),
            ),
        )
        remaining.remove(next_order)

        drone = next_order.drone
        if not drone:
            drone = (
                session.query(models.Drone)
                .filter(models.Drone.station_id == station.id)
                .order_by(models.Drone.id)
                .first()
            )

        total_distance = (
            haversine_km(station_coord, (next_order.origin_location.lat, next_order.origin_location.lon))
            + haversine_km(
                (next_order.origin_location.lat, next_order.origin_location.lon),
                (next_order.destination_location.lat, next_order.destination_location.lon),
            )
            + haversine_km((next_order.destination_location.lat, next_order.destination_location.lon), station_coord)
        )

        if drone:
            max_range = effective_range_km(drone.base_range_km, next_order.weight_kg, drone.max_payload_kg)
        else:
            max_range = 0.0

        if max_range <= 0 or total_distance > max_range:
            next_order.status = "too_far"
            too_far.append(next_order.id)
        else:
            next_order.status = "planned"
            planned_output.append(
                {
                    "order_id": next_order.id,
                    "drone_id": drone.id if drone else None,
                    "origin": {
                        "id": next_order.origin_location.id,
                        "name": next_order.origin_location.name,
                        "lat": next_order.origin_location.lat,
                        "lon": next_order.origin_location.lon,
                    },
                    "destination": {
                        "id": next_order.destination_location.id,
                        "name": next_order.destination_location.name,
                        "lat": next_order.destination_location.lat,
                        "lon": next_order.destination_location.lon,
                    },
                    "total_distance_km": round(total_distance, 2),
                    "max_range_km": round(max_range, 2),
                }
            )

        session.add(next_order)
        current_coord = station_coord  # Return to base before the next delivery in this simple model.

    session.commit()

    return {
        "station": {"id": station.id, "name": station.name, "lat": station.lat, "lon": station.lon},
        "planned_orders": planned_output,
        "too_far": too_far,
    }
