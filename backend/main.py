from __future__ import annotations

import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend import mqtt_bg, models
from backend.db import get_session

load_dotenv()

APP_ROOT = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(APP_ROOT / "templates"))

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

class LocationResponse(BaseModel):
    id: int
    name: str
    county_id: int
    lat: float
    lon: float

    class Config:
        orm_mode = True


class CountyResponse(BaseModel):
    id: int
    name: str
    hub_lat: Optional[float] = None
    hub_lon: Optional[float] = None
    drone_id: Optional[int] = None
    max_payload_kg: Optional[float] = None
    speed_kmh: Optional[float] = None
    base_range_km: Optional[float] = None

    class Config:
        orm_mode = True


class OrderCreate(BaseModel):
    origin_location_id: int = Field(..., gt=0)
    destination_location_id: int = Field(..., gt=0)
    weight_kg: float = Field(..., gt=0)


class OrderResponse(BaseModel):
    id: int
    origin_location_id: int
    destination_location_id: int
    weight_kg: float
    county_id: int
    drone_id: Optional[int]
    status: str
    created_at: datetime

    class Config:
        orm_mode = True


@app.on_event("startup")
async def startup_event() -> None:
    mqtt_bg.start()


@app.get("/", response_class=HTMLResponse)
def serve_index(request: Request) -> HTMLResponse:
    """Serve the main UI."""
    rest_base_url = os.getenv("FRONTEND_REST_BASE_URL", "").rstrip("/")
    ws_url = os.getenv("FRONTEND_WS_URL", "").rstrip("/")
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "rest_base_url": rest_base_url,
            "ws_url": ws_url,
        },
    )


@app.get("/api/counties", response_model=List[CountyResponse])
def get_counties(session: Session = Depends(get_session)) -> List[CountyResponse]:
    counties = session.query(models.County).order_by(models.County.name).all()
    response: List[CountyResponse] = []
    for county in counties:
        station = (
            session.query(models.Station)
            .filter(models.Station.county_id == county.id)
            .order_by(models.Station.id)
            .first()
        )
        drone = (
            session.query(models.Drone)
            .filter(models.Drone.station_id == station.id)  # type: ignore[arg-type]
            .order_by(models.Drone.id)
            .first()
            if station
            else None
        )
        response.append(
            CountyResponse(
                id=county.id,
                name=county.name,
                hub_lat=station.lat if station else None,
                hub_lon=station.lon if station else None,
                drone_id=drone.id if drone else None,
                max_payload_kg=drone.max_payload_kg if drone else None,
                speed_kmh=drone.speed_kmh if drone else None,
                base_range_km=drone.base_range_km if drone else None,
            )
        )
    return response


@app.get("/api/locations", response_model=List[LocationResponse])
def get_locations(
    county_id: Optional[int] = None, session: Session = Depends(get_session)
) -> List[models.Location]:
    if county_id is not None:
        county = session.get(models.County, county_id)
        if not county:
            raise HTTPException(status_code=404, detail="County not found")
        return (
            session.query(models.Location)
            .filter(models.Location.county_id == county_id)
            .order_by(models.Location.name)
            .all()
        )
    return session.query(models.Location).order_by(models.Location.name).all()


@app.post("/api/orders", response_model=OrderResponse, status_code=201)
def create_order(payload: OrderCreate, session: Session = Depends(get_session)) -> models.Order:
    origin = session.get(models.Location, payload.origin_location_id)
    destination = session.get(models.Location, payload.destination_location_id)

    if not origin:
        raise HTTPException(status_code=404, detail="Origin location not found")
    if not destination:
        raise HTTPException(status_code=404, detail="Destination location not found")

    county_id = origin.county_id
    drone = (
        session.query(models.Drone)
        .join(models.Station)
        .filter(models.Station.county_id == county_id)
        .order_by(models.Drone.id)
        .first()
    )

    if drone is None:
        raise HTTPException(status_code=400, detail="No drone available in this county")

    order = models.Order(
        origin_location_id=origin.id,
        destination_location_id=destination.id,
        weight_kg=payload.weight_kg,
        county_id=county_id,
        drone_id=drone.id,
        status="pending",
    )
    session.add(order)
    session.commit()
    session.refresh(order)
    return order


@app.get("/api/points")
def get_points(session: Session = Depends(get_session)) -> List[Dict[str, Any]]:
    locations = session.query(models.Location).order_by(models.Location.name).all()
    return [{"name": loc.name, "lon": loc.lon, "lat": loc.lat} for loc in locations]


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
