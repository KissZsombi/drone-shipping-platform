from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend import mqtt_bg

load_dotenv()

APP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = APP_ROOT.parent
POINTS_FILE = REPO_ROOT / "dronoptimalisut.txt"

origins_env = os.getenv("ALLOW_ORIGINS", "*")
ALLOW_ORIGINS = [origin.strip() for origin in origins_env.split(",") if origin.strip()] or ["*"]

app = FastAPI(title="Drone Shipping Platform")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if "*" in ALLOW_ORIGINS else ALLOW_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


def read_points() -> List[Dict[str, Any]]:
    points: List[Dict[str, Any]] = []
    if not POINTS_FILE.exists():
        return points

    with POINTS_FILE.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 3:
                continue
            name = parts[0]
            try:
                lon = float(parts[1])
                lat = float(parts[2])
            except ValueError:
                continue
            points.append({"name": name, "lon": lon, "lat": lat})
    return points


@app.on_event("startup")
async def startup_event() -> None:
    mqtt_bg.start()


@app.get("/api/points")
def get_points() -> List[Dict[str, Any]]:
    return read_points()


@app.get("/api/route")
def get_route() -> List[Any]:
    return mqtt_bg.get_last_route()


@app.get("/api/last")
def get_last() -> Dict[str, Any]:
    return mqtt_bg.get_last_message()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    last_payload: Dict[str, Any] = {}

    try:
        while True:
            payload = mqtt_bg.get_last_message()
            if payload and payload != last_payload:
                await websocket.send_json(payload)
                last_payload = payload
            await asyncio.sleep(0.3)
    except WebSocketDisconnect:
        return
