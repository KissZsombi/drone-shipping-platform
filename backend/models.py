from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db import Base


class County(Base):
    __tablename__ = "counties"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    stations: Mapped[List["Station"]] = relationship("Station", back_populates="county", cascade="all, delete-orphan")
    locations: Mapped[List["Location"]] = relationship("Location", back_populates="county", cascade="all, delete-orphan")
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="county")


class Station(Base):
    __tablename__ = "stations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    county_id: Mapped[int] = mapped_column(ForeignKey("counties.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)

    county: Mapped[County] = relationship("County", back_populates="stations")
    drones: Mapped[List["Drone"]] = relationship("Drone", back_populates="station", cascade="all, delete-orphan")


class Drone(Base):
    __tablename__ = "drones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    station_id: Mapped[int] = mapped_column(ForeignKey("stations.id"), nullable=False)
    base_range_km: Mapped[float] = mapped_column(Float, nullable=False)
    max_payload_kg: Mapped[float] = mapped_column(Float, nullable=False)
    speed_kmh: Mapped[float] = mapped_column(Float, nullable=False, default=60.0)

    station: Mapped[Station] = relationship("Station", back_populates="drones")
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="drone")


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    county_id: Mapped[int] = mapped_column(ForeignKey("counties.id"), nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)

    county: Mapped[County] = relationship("County", back_populates="locations")
    origin_orders: Mapped[List["Order"]] = relationship(
        "Order",
        back_populates="origin_location",
        foreign_keys="Order.origin_location_id",
    )
    destination_orders: Mapped[List["Order"]] = relationship(
        "Order",
        back_populates="destination_location",
        foreign_keys="Order.destination_location_id",
    )


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    origin_location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), nullable=False)
    destination_location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), nullable=False)
    weight_kg: Mapped[float] = mapped_column(Float, nullable=False)
    county_id: Mapped[int] = mapped_column(ForeignKey("counties.id"), nullable=False)
    drone_id: Mapped[Optional[int]] = mapped_column(ForeignKey("drones.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    county: Mapped[County] = relationship("County", back_populates="orders")
    drone: Mapped[Optional[Drone]] = relationship("Drone", back_populates="orders")
    origin_location: Mapped[Location] = relationship(
        "Location",
        back_populates="origin_orders",
        foreign_keys=[origin_location_id],
    )
    destination_location: Mapped[Location] = relationship(
        "Location",
        back_populates="destination_orders",
        foreign_keys=[destination_location_id],
    )
