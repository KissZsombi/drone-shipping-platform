from __future__ import annotations

import json
import logging
import os
import threading
from copy import deepcopy
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
import paho.mqtt.client as mqtt

load_dotenv()

logger = logging.getLogger("backend.mqtt_bg")

MQTT_HOST = os.getenv("MQTT_HOST", "broker.hivemq.com")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "dron/utvonal")

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


def get_last_message() -> Dict[str, Any]:
    with _state_lock:
        return deepcopy(_last_message)


def get_last_route() -> List[Any]:
    with _state_lock:
        return deepcopy(_last_route)
