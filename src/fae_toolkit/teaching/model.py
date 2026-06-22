"""Data model for AGV/AMR teaching points and routes.

A teaching *point* carries its pose plus two orthogonal display dimensions:

* **type** — the kind of equipment/station (free-form text). Its colour and
  marker shape are looked up from the project's :class:`EquipmentStyle` table,
  so users can add their own equipment types and style them freely.
* **status** — the teaching state (in-progress / done / alarm), which drives the
  marker fill colour so the map doubles as a progress dashboard.

A project may also reference a **background image** (an exported CAD drawing or
floor plan) that the points are placed on top of.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class PointType(str, Enum):
    """Built-in equipment types (users may also add their own as plain text)."""

    WAYPOINT = "WAYPOINT"
    LOAD = "LOAD"
    UNLOAD = "UNLOAD"
    CHARGE = "CHARGE"
    STANDBY = "STANDBY"


class TeachingStatus(str, Enum):
    """Per-point teaching state, shown as the marker fill colour."""

    IN_PROGRESS = "IN_PROGRESS"  # not finished / being taught
    DONE = "DONE"  # taught and verified
    ALARM = "ALARM"  # taught but faulted / needs rework


# Friendly marker shapes (mapped to pyqtgraph symbols in the view layer).
SHAPES = ("circle", "square", "triangle", "diamond", "star", "plus", "cross")


@dataclass
class EquipmentStyle:
    """Colour + marker shape for one equipment type."""

    type: str
    color: str = "#3498db"
    shape: str = "circle"

    def to_dict(self) -> dict:
        return {"type": self.type, "color": self.color, "shape": self.shape}

    @classmethod
    def from_dict(cls, d: dict) -> EquipmentStyle:
        shape = str(d.get("shape", "circle"))
        return cls(
            type=str(d["type"]),
            color=str(d.get("color", "#3498db")),
            shape=shape if shape in SHAPES else "circle",
        )


def default_styles() -> list[EquipmentStyle]:
    return [
        EquipmentStyle("WAYPOINT", "#3498db", "circle"),
        EquipmentStyle("LOAD", "#27ae60", "square"),
        EquipmentStyle("UNLOAD", "#e67e22", "triangle"),
        EquipmentStyle("CHARGE", "#9b59b6", "diamond"),
        EquipmentStyle("STANDBY", "#95a5a6", "circle"),
    ]


@dataclass
class BackgroundImage:
    """A CAD/floor-plan raster placed under the points.

    ``x``/``y`` is the world position (mm) of the image's bottom-left corner;
    ``scale`` is millimetres per pixel; ``opacity`` is 0..1.
    """

    path: str
    x: float = 0.0
    y: float = 0.0
    scale: float = 1.0
    opacity: float = 0.5

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "x": self.x,
            "y": self.y,
            "scale": self.scale,
            "opacity": self.opacity,
        }

    @classmethod
    def from_dict(cls, d: dict) -> BackgroundImage:
        return cls(
            path=str(d["path"]),
            x=float(d.get("x", 0.0)),
            y=float(d.get("y", 0.0)),
            scale=float(d.get("scale", 1.0)),
            opacity=float(d.get("opacity", 0.5)),
        )


@dataclass
class TeachingPoint:
    """A taught position: AGV base pose plus station/metadata."""

    id: int
    name: str
    type: str = PointType.WAYPOINT.value
    x: float = 0.0  # mm
    y: float = 0.0  # mm
    theta: float = 0.0  # heading, degrees
    station: str = ""  # equipment / station id
    status: TeachingStatus = TeachingStatus.IN_PROGRESS
    notes: str = ""

    def __post_init__(self) -> None:
        # Accept PointType enums or plain strings for ``type``; normalise to text.
        if isinstance(self.type, PointType):
            self.type = self.type.value
        else:
            self.type = str(self.type)
        if not isinstance(self.status, TeachingStatus):
            self.status = TeachingStatus(str(self.status))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "x": self.x,
            "y": self.y,
            "theta": self.theta,
            "station": self.station,
            "status": self.status.value,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict) -> TeachingPoint:
        return cls(
            id=int(d["id"]),
            name=str(d["name"]),
            type=str(d.get("type", "WAYPOINT")),
            x=float(d.get("x", 0.0)),
            y=float(d.get("y", 0.0)),
            theta=float(d.get("theta", 0.0)),
            station=str(d.get("station", "")),
            status=TeachingStatus(d.get("status", "IN_PROGRESS")),
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
    """A named collection of teaching points, routes, styles and a backdrop."""

    name: str = "untitled"
    version: int = 2
    points: list[TeachingPoint] = field(default_factory=list)
    routes: list[Route] = field(default_factory=list)
    styles: list[EquipmentStyle] = field(default_factory=default_styles)
    background: BackgroundImage | None = None

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

    def style_for(self, type_name: str) -> EquipmentStyle:
        """Style for *type_name*, falling back to a neutral default."""
        return next(
            (s for s in self.styles if s.type == type_name),
            EquipmentStyle(type_name, "#7f8c8d", "circle"),
        )

    def has_style(self, type_name: str) -> bool:
        """True if an :class:`EquipmentStyle` is explicitly defined for *type_name*.

        Unlike :meth:`style_for` (which fabricates a neutral fallback for unknown
        types so the map can always render), this is an exact membership test —
        use it before adding a new type so existing ones are not duplicated.
        """
        return any(s.type == type_name for s in self.styles)

    def types(self) -> list[str]:
        """All known equipment-type names (styles + any used by points)."""
        names = [s.type for s in self.styles]
        for p in self.points:
            if p.type not in names:
                names.append(p.type)
        return names

    # --- serialization ---------------------------------------------------- #
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "points": [p.to_dict() for p in self.points],
            "routes": [r.to_dict() for r in self.routes],
            "styles": [s.to_dict() for s in self.styles],
            "background": self.background.to_dict() if self.background else None,
        }

    @classmethod
    def from_dict(cls, d: dict) -> TeachingProject:
        styles = [EquipmentStyle.from_dict(s) for s in d.get("styles", [])] or default_styles()
        bg = d.get("background")
        return cls(
            name=str(d.get("name", "untitled")),
            version=int(d.get("version", 2)),
            points=[TeachingPoint.from_dict(p) for p in d.get("points", [])],
            routes=[Route.from_dict(r) for r in d.get("routes", [])],
            styles=styles,
            background=BackgroundImage.from_dict(bg) if bg else None,
        )
