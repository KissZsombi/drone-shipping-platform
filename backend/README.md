# Drone Shipping Backend

Minimal FastAPI service that bridges HiveMQ MQTT telemetry to REST and WebSocket consumers.

## Prerequisites

- Python 3.11+
- Access to the repository root (the API reads `dronoptimalisut.txt` from there)

## Setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate  # PowerShell
pip install -r requirements.txt
cp .env.example .env
```

Adjust the `.env` values if you need a different broker or CORS origin.

## Run

```bash
uvicorn backend.main:app --reload --log-level info
```

The API exposes:

- `GET /api/points` – static delivery points from `dronoptimalisut.txt`
- `GET /api/route` – cached route array received via MQTT
- `GET /api/last` – latest telemetry payload from the drone simulator
- `GET /ws` – WebSocket stream that pushes new telemetry payloads as they arrive
