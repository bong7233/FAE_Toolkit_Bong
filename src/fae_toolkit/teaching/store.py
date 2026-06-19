"""Persistence, CSV export, and validation for teaching projects."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

from fae_toolkit.teaching.model import (
    PointType,
    Route,
    TeachingPoint,
    TeachingProject,
    TeachingStatus,
)


def load_project(path: str | Path) -> TeachingProject:
    with open(path, encoding="utf-8") as fh:
        return TeachingProject.from_dict(json.load(fh))


def save_project(project: TeachingProject, path: str | Path) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(project.to_dict(), fh, indent=2, ensure_ascii=False)


def export_points_csv(project: TeachingProject, path: str | Path) -> None:
    fields = ["id", "name", "type", "x", "y", "theta", "station", "status", "notes"]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for p in project.points:
            writer.writerow(p.to_dict())


def validate(project: TeachingProject) -> list[str]:
    """Return a list of human-readable issues (``ERROR``/``WARN`` prefixed)."""
    issues: list[str] = []

    ids = [p.id for p in project.points]
    for dup in {i for i in ids if ids.count(i) > 1}:
        issues.append(f"ERROR: duplicate point id {dup}")

    names = [p.name.strip().lower() for p in project.points]
    for p in project.points:
        if not p.name.strip():
            issues.append(f"ERROR: point id {p.id} has an empty name")
    for dup in {n for n in names if n and names.count(n) > 1}:
        issues.append(f"ERROR: duplicate point name '{dup}'")

    id_set = set(ids)
    for route in project.routes:
        if len(route.point_ids) < 2:
            issues.append(f"WARN: route '{route.name}' has fewer than 2 points")
        for pid in route.point_ids:
            if pid not in id_set:
                issues.append(f"ERROR: route '{route.name}' references unknown point id {pid}")

    types = {p.type for p in project.points}
    if PointType.LOAD.value not in types:
        issues.append("WARN: project has no LOAD point")
    if PointType.UNLOAD.value not in types:
        issues.append("WARN: project has no UNLOAD point")

    for p in project.points:
        if p.status == TeachingStatus.ALARM:
            issues.append(f"WARN: point '{p.name}' is in ALARM (teaching faulted)")

    # Points taught at (nearly) the same coordinate are often a mistake.
    for i, a in enumerate(project.points):
        for b in project.points[i + 1 :]:
            if math.hypot(a.x - b.x, a.y - b.y) < 1.0:
                issues.append(f"WARN: '{a.name}' and '{b.name}' are at almost the same position")
    return issues


def sample_project() -> TeachingProject:
    """A small but realistic AGV layout for demos and tests."""
    S = TeachingStatus
    points = [
        TeachingPoint(1, "HOME", "STANDBY", 0, 0, 0, "", S.DONE, "dock / idle"),
        TeachingPoint(2, "CHARGE_1", "CHARGE", 500, 0, 180, "CHG01", S.DONE, "charger"),
        TeachingPoint(3, "WP_AISLE_1", "WAYPOINT", 2000, 0, 0, "", S.DONE),
        TeachingPoint(4, "WP_AISLE_2", "WAYPOINT", 2000, 3000, 90, "", S.IN_PROGRESS),
        TeachingPoint(5, "ST_A_LOAD", "LOAD", 2600, 3000, 90, "STN_A", S.IN_PROGRESS, "input port"),
        TeachingPoint(6, "ST_B_UNLOAD", "UNLOAD", 2000, 6000, 90, "STN_B", S.IN_PROGRESS, "output"),
    ]
    routes = [
        Route("A_to_B", [1, 3, 4, 5, 4, 6]),
        Route("to_charge", [1, 2]),
    ]
    return TeachingProject(name="sample_line", version=2, points=points, routes=routes)
