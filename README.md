# Drone Shipping Platform

Development quick-start for the demo FastAPI backend, simulator, and WordPress plugin.

## Backend
- Install deps: `pip install -r backend/requirements.txt`
- Initialize database (creates `backend/drone_delivery.db` with sample data): `python backend/init_db.py`
- Run API (CORS open for dev): `uvicorn backend.main:app --reload --port 8000`
- Open the web UI: http://localhost:8000/ (serves `backend/templates/index.html` with county/location selectors backed by SQLite)

## Simulator
- Publishes test telemetry to MQTT (matches the backend listener): `python simulator/publisher.py`

## WordPress plugin
- Copy `wp-plugin/drone-map` into your WordPress `wp-content/plugins` folder and activate it.
- In Settings → Drone Map, set:
  - REST Base URL: e.g. `http://localhost:8000`
  - WebSocket URL: e.g. `ws://localhost:8000/ws`
- Use the shortcodes on a page:
  - `[drone_order_form]` to submit orders against the backend.
  - `[drone_map]` to display the Leaflet live map and telemetry stats.

## MQTT topics
- Targets from UI to backend: `dron/celpontok` (payload includes `county_id` + location ids/names from the DB).
- Route updates from backend to UI: `dron/utvonal` (step-by-step coordinates and final route list).

## County + location selection in the UI
- First pick a county (megye); the hub marker moves to the county’s Station.
- Type into the location field; suggestions come from `/api/locations?county_id=...`.
- Only database-backed locations can be added; the payload sent to MQTT contains validated ids.
