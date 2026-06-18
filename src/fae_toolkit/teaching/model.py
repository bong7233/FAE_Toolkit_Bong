"""Data model for AGV/AMR teaching points and routes."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class PointType(str, Enum):
    WAYPOINT = "WAYPOINT"
    LOAD = "LOAD"
    UNLOAD = "UNLOAD"
    CHARGE = "CHARGE"
    STANDBY = "STANDBY"


@dataclass
class TeachingPoint:
    """A taught position: AGV base pose plus station/metadata."""

    id: int
    name: str
    type: PointType = PointType.WAYPOINT
    x: float = 0.0  # mm
    y: float = 0.0  # mm
    theta: float = 0.0  # heading, degrees
    station: str = ""  # equipment / station id
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "x": self.x,
            "y": self.y,
            "theta": self.theta,
            "station": self.station,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict) -> TeachingPoint:
        return cls(
            id=int(d["id"]),
            name=str(d["name"]),
            type=PointType(d.get("type", "WAYPOINT")),
            x=float(d.get("x", 0.0)),
            y=float(d.get("y", 0.0)),
            theta=float(d.get("theta", 0.0)),
            station=str(d.get("station", "")),
            notes=str(d.get("notes", "")),
        )


@dataclass
class Route:
    """An ordered path through a list of point ids."""

    name: str
    point_ids: list[int] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"name": self.name, "point_ids": list(self.point_ids)}

    @classmethod
    def from_dict(cls, d: dict) -> Route:
        return cls(name=str(d["name"]), point_ids=[int(i) for i in d.get("point_ids", [])])


@dataclass
class TeachingProject:
    """A named collection of teaching points and routes."""

    name: str = "untitled"
    version: int = 1
    points: list[TeachingPoint] = field(default_factory=list)
    routes: list[Route] = field(default_factory=list)

    # --- helpers ---------------------------------------------------------- #
    def next_id(self) -> int:
        return (max((p.id for p in self.points), default=0)) + 1

    def get_point(self, point_id: int) -> TeachingPoint | None:
        return next((p for p in self.points if p.id == point_id), None)

    def add_point(self, point: TeachingPoint) -> None:
        self.points.append(point)

    def remove_point(self, point_id: int) -> None:
        self.points = [p for p in self.points if p.id != point_id]
        for route in self.routes:
            route.point_ids = [i for i in route.point_ids if i != point_id]

    # --- serialization ---------------------------------------------------- #
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "points": [p.to_dict() for p in self.points],
            "routes": [r.to_dict() for r in self.routes],
        }

    @classmethod
    def from_dict(cls, d: dict) -> TeachingProject:
        return cls(
            name=str(d.get("name", "untitled")),
            version=int(d.get("version", 1)),
            points=[TeachingPoint.from_dict(p) for p in d.get("points", [])],
            routes=[Route.from_dict(r) for r in d.get("routes", [])],
        )
