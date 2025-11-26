from __future__ import annotations

import json
import logging
import os
import threading
from copy import deepcopy
from typing import Any, Dict, List, Optional

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

from backend import models
from backend.db import SessionLocal
from backend.services import route_planner

load_dotenv()

logger = logging.getLogger("backend.mqtt_bg")

MQTT_HOST = os.getenv("MQTT_HOST", "broker.hivemq.com")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "dron/utvonal")
MQTT_TOPIC_TARGETS = os.getenv("MQTT_TARGETS_TOPIC", "dron/celpontok")

_state_lock = threading.Lock()
_last_message: Dict[str, Any] = {}
_last_route: List[Any] = []

_client_lock = threading.Lock()
_client: Optional[mqtt.Client] = None
_started = False


def _on_connect(client: mqtt.Client, _userdata, _flags, rc: int) -> None:
    if rc == 0:
        logger.info("Connected to MQTT broker %s:%s", MQTT_HOST, MQTT_PORT)
        client.subscribe(MQTT_TOPIC)
        client.subscribe(MQTT_TOPIC_TARGETS)
    else:
        logger.error("MQTT connection failed with code %s", rc)


def _on_message(_client: mqtt.Client, _userdata, msg: mqtt.MQTTMessage) -> None:
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
    except json.JSONDecodeError:
        logger.warning("Invalid JSON payload on %s: %s", msg.topic, msg.payload)
        return

    if not isinstance(payload, dict):
        return

    if "coordinates" in payload:
        with _state_lock:
            _last_message.clear()
            _last_message.update(payload)

    if "route" in payload and isinstance(payload["route"], list):
        with _state_lock:
            _last_route.clear()
            _last_route.extend(payload["route"])

    if msg.topic == MQTT_TOPIC_TARGETS:
        _handle_targets_payload(payload)


def _handle_targets_payload(payload: Dict[str, Any]) -> None:
    """Receive county + targets payload, compute route from DB, and publish to MQTT_TOPIC."""
    targets = payload.get("targets") or []
    weights = payload.get("weights") or payload.get("target_weights") or []
    target_names = payload.get("target_names") or []
    if not targets and not target_names:
        logger.warning("Received targets payload without targets: %s", payload)
        return

    county_id = payload.get("county_id")
    county_name = payload.get("county")

    with SessionLocal() as session:
        county = None
        if county_id is not None:
            county = session.get(models.County, int(county_id))
        elif county_name:
            county = (
                session.query(models.County)
                .filter(models.County.name == str(county_name))
                .first()
            )

        if not county:
            logger.warning("Unknown county in targets payload: %s", payload)
            return

        station = (
            session.query(models.Station)
            .filter(models.Station.county_id == county.id)
            .order_by(models.Station.id)
            .first()
        )
        if not station:
            logger.warning("No station found for county %s", county.name)
            return

        locations: List[models.Location] = []
        weights_by_id: Dict[int, float] = {}
        names = targets or target_names

        def record_weight(loc_id: int, weight_index: int) -> None:
            try:
                weights_by_id[loc_id] = float(weights[weight_index])
            except Exception:
                weights_by_id.setdefault(loc_id, 0.0)

        if all(isinstance(t, (int, float, str)) and str(t).isdigit() for t in names):
            ids = [int(t) for t in names]
            locations = (
                session.query(models.Location)
                .filter(models.Location.id.in_(ids), models.Location.county_id == county.id)
                .all()
            )
            missing = [target_id for target_id in ids if target_id not in {loc.id for loc in locations}]
            if missing:
                logger.warning("Some target IDs not found for county %s: %s", county.name, missing)
            for idx, loc_id in enumerate(ids):
                record_weight(loc_id, idx)
        else:
            for idx, name in enumerate(names):
                loc = (
                    session.query(models.Location)
                    .filter(models.Location.county_id == county.id, models.Location.name == str(name))
                    .first()
                )
                if not loc:
                    logger.warning("Target name not found in county %s: %s", county.name, name)
                    continue
                locations.append(loc)
                record_weight(loc.id, idx)

        if not locations:
            logger.warning("No valid locations resolved from payload: %s", payload)
            return

        drone = (
            session.query(models.Drone)
            .filter(models.Drone.station_id == station.id)
            .order_by(models.Drone.id)
            .first()
        )
        if not drone:
            logger.error("No drone configured for station %s", station.name)
            return

        total_payload = sum(weights_by_id.values())
        if drone.max_payload_kg and total_payload > drone.max_payload_kg:
            logger.warning(
                "Total payload %.2f kg exceeds drone max payload %.2f kg; attempting planning anyway.",
                total_payload,
                drone.max_payload_kg,
            )

        steps = route_planner.plan_route_with_recharges(
            locations,
            station,
            drone,
            weights_by_location_id=weights_by_id,
        )
        client = get_client()
        if not client:
            logger.error("MQTT client not available; cannot publish route.")
            return

        with _state_lock:
            _last_route.clear()
            _last_route.extend([step.get("next") for step in steps if step.get("next")])

        route_planner.publish_route_mqtt(client, steps, MQTT_TOPIC)


def start() -> None:
    """Initialise the background MQTT client if it isn't running yet."""
    global _client, _started

    with _client_lock:
        if _started:
            return

        client = mqtt.Client()
        client.on_connect = _on_connect
        client.on_message = _on_message

        try:
            client.connect(MQTT_HOST, MQTT_PORT, 60)
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Failed to connect to MQTT broker: %s", exc)
            return

        client.loop_start()
        _client = client
        _started = True
        logger.info("MQTT background client started.")


def get_client() -> Optional[mqtt.Client]:
    with _client_lock:
        return _client


def get_last_message() -> Dict[str, Any]:
    with _state_lock:
        return deepcopy(_last_message)


def get_last_route() -> List[Any]:
    with _state_lock:
        return deepcopy(_last_route)
