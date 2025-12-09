from __future__ import annotations

"""
End-to-end test that records every project file touched during a simulated
browser-style flow (page load, data fetch, order creation, route planning,
and MQTT-style telemetry publishing).

Run with:
    python backend/tests/test_file_usage_e2e.py
or:
    pytest -s backend/tests/test_file_usage_e2e.py
"""

import importlib
import json
import os
import shutil
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple
from unittest.mock import patch

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
# Ensure the repository root is importable as a package root (so "backend" works when running via python file.py).
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

BACKEND_ROOT = PROJECT_ROOT / "backend"
DB_SEED = BACKEND_ROOT / "drone_delivery.db"
REPORT_PATH = BACKEND_ROOT / "tests" / "file_usage_report.json"
FILE_EVENTS = {"open", "os.open", "sqlite3.connect"}


class DummyMqttClient:
    """Collects MQTT publish calls without hitting the network."""

    def __init__(self) -> None:
        self.messages: List[Dict[str, Any]] = []

    def publish(self, topic: str, payload: str, *_args, **_kwargs) -> Any:
        self.messages.append({"topic": topic, "payload": payload})

        class Result:
            rc = 0

        return Result()


class DummySimulatorClient(DummyMqttClient):
    """Simulator MQTT client stub with connect/disconnect hooks."""

    def connect(self, *_args, **_kwargs) -> int:  # type: ignore[override]
        return 0

    def disconnect(self, *_args, **_kwargs) -> int:  # type: ignore[override]
        return 0


def _install_file_audit(project_root: Path) -> List[Dict[str, str]]:
    """Register a Python audit hook that collects file opens under project_root."""
    recorded: List[Dict[str, str]] = []
    root_str = str(project_root.resolve())

    def _hook(event: str, args: Tuple[Any, ...]) -> None:
        if event not in FILE_EVENTS or not args:
            return

        target = args[0]
        if isinstance(target, (bytes, os.PathLike)):
            target = os.fspath(target)
        if not isinstance(target, str):
            return

        try:
            resolved = str(Path(target).resolve())
        except Exception:
            resolved = str(target)

        if not resolved.startswith(root_str):
            return

        caller = "unknown"
        try:
            frame = traceback.extract_stack(limit=6)
            if len(frame) >= 2:
                caller_frame = frame[-2]
                caller = f"{Path(caller_frame.filename).name}:{caller_frame.lineno}"
        except Exception:
            caller = "unknown"

        recorded.append({"event": event, "path": resolved, "caller": caller})

    sys.addaudithook(_hook)
    return recorded


def _summarize(events: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    summary: Dict[str, Dict[str, Any]] = {}
    for entry in events:
        bucket = summary.setdefault(
            entry["path"],
            {"count": 0, "events": set(), "callers": set()},
        )
        bucket["count"] += 1
        bucket["events"].add(entry["event"])
        bucket["callers"].add(entry["caller"])

    summarized: List[Dict[str, Any]] = []
    for path, data in sorted(summary.items()):
        summarized.append(
            {
                "path": path,
                "count": data["count"],
                "events": sorted(data["events"]),
                "callers": sorted(data["callers"]),
            }
        )
    return summarized


def _simulate_browser_flow(client: TestClient, mqtt_bg_mod: Any) -> Dict[str, Any]:
    """Drive the FastAPI app through the same steps as the browser UI."""
    root_resp = client.get("/")
    assert root_resp.status_code == 200, "index page failed"

    counties_resp = client.get("/api/counties")
    assert counties_resp.status_code == 200 and counties_resp.json(), "counties fetch failed"
    counties = counties_resp.json()
    county_id = counties[0]["id"]

    locations_resp = client.get(f"/api/locations?county_id={county_id}")
    assert locations_resp.status_code == 200, "locations fetch failed"
    locations = locations_resp.json()
    assert len(locations) >= 2, "need at least two locations in seed data"

    order_payload = {
        "origin_location_id": locations[0]["id"],
        "destination_location_id": locations[1]["id"],
        "weight_kg": 1.0,
    }
    order_resp = client.post("/api/orders", json=order_payload)
    assert order_resp.status_code == 201, "order creation failed"

    target_ids = [loc["id"] for loc in locations[:3]]
    weights = [0.5 for _ in target_ids]
    mqtt_bg_mod._handle_targets_payload({"county_id": county_id, "targets": target_ids, "weights": weights})

    route_resp = client.get("/api/route")
    assert route_resp.status_code == 200, "route fetch failed"

    return {
        "county_id": county_id,
        "locations_used": target_ids,
        "order": order_resp.json(),
        "route": route_resp.json(),
    }


def _run_simulator_flow() -> Dict[str, Any]:
    """Load points and publish simulated telemetry without real network calls."""
    dummy_client = DummySimulatorClient()
    with patch("simulator.publisher.mqtt.Client", return_value=dummy_client), patch(
        "simulator.publisher.time.sleep", lambda _sec: None
    ):
        publisher = importlib.import_module("simulator.publisher")
        points = publisher.load_points()
        sample = points[:3]
        publisher.publish_route(sample)

    return {"points_used": sample, "published_messages": dummy_client.messages}


def test_full_browser_flow_file_usage() -> None:
    if not DB_SEED.exists():
        raise FileNotFoundError(f"Seed database missing: {DB_SEED}")

    audit_log = _install_file_audit(PROJECT_ROOT)

    temp_dir = Path(
        tempfile.mkdtemp(prefix="file_usage_db_", dir=BACKEND_ROOT)
    )
    temp_db = temp_dir / "drone_delivery.db"
    shutil.copy(DB_SEED, temp_db)

    env_overrides = {
        "DATABASE_URL": f"sqlite:///{temp_db}",
        "MQTT_HOST": "localhost",
        "MQTT_PORT": "1883",
        "MQTT_TOPIC": "dron/utvonal",
        "MQTT_TARGETS_TOPIC": "dron/celpontok",
    }

    for mod in ["backend.db", "backend.models", "backend.mqtt_bg", "backend.main"]:
        sys.modules.pop(mod, None)

    dummy_backend_mqtt = DummyMqttClient()
    with patch.dict(os.environ, env_overrides, clear=False), patch(
        "backend.mqtt_bg.start", lambda: None
    ), patch("backend.mqtt_bg.get_client", lambda: dummy_backend_mqtt):
        main = importlib.import_module("backend.main")
        mqtt_bg_mod = importlib.import_module("backend.mqtt_bg")
        with TestClient(main.app) as client:
            backend_flow = _simulate_browser_flow(client, mqtt_bg_mod)

    simulator_flow = _run_simulator_flow()

    summary = _summarize(audit_log)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(
            {
                "summary": summary,
                "events": audit_log,
                "backend_flow": backend_flow,
                "backend_mqtt_messages": dummy_backend_mqtt.messages,
                "simulator_flow": simulator_flow,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print("\nFile usage summary (project root only):")
    for item in summary:
        events = ", ".join(item["events"])
        callers = ", ".join(item["callers"])
        print(f"- {item['path']} | count={item['count']} | events={events} | callers={callers}")
    print(f"\nDetailed report written to: {REPORT_PATH}")

    shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    test_full_browser_flow_file_usage()
