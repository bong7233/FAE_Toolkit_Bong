"""Tests for the teaching-point model, persistence, and validation."""

import csv

from fae_toolkit.teaching import (
    BackgroundImage,
    EquipmentStyle,
    PointType,
    Route,
    TeachingPoint,
    TeachingProject,
    TeachingStatus,
    export_points_csv,
    load_project,
    sample_project,
    save_project,
    validate,
)


def test_sample_project_is_valid():
    assert validate(sample_project()) == []


def test_project_dict_round_trip():
    project = sample_project()
    restored = TeachingProject.from_dict(project.to_dict())
    assert restored.to_dict() == project.to_dict()


def test_save_and_load(tmp_path):
    project = sample_project()
    path = tmp_path / "proj.json"
    save_project(project, path)
    loaded = load_project(path)
    assert loaded.name == project.name
    assert len(loaded.points) == len(project.points)
    assert loaded.to_dict() == project.to_dict()


def test_export_csv(tmp_path):
    project = sample_project()
    path = tmp_path / "points.csv"
    export_points_csv(project, path)
    with open(path, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == len(project.points)
    assert rows[0]["name"] == "HOME"
    assert rows[0]["status"] == "DONE"


def test_point_type_accepts_enum_or_str():
    a = TeachingPoint(1, "a", PointType.LOAD)
    b = TeachingPoint(2, "b", "CONVEYOR")  # custom equipment type
    assert a.type == "LOAD" and isinstance(a.type, str)
    assert b.type == "CONVEYOR"


def test_status_default_and_coercion():
    assert TeachingPoint(1, "a").status == TeachingStatus.IN_PROGRESS
    assert TeachingPoint(2, "b", status="DONE").status == TeachingStatus.DONE


def test_status_and_style_round_trip():
    project = TeachingProject(
        name="styled",
        points=[TeachingPoint(1, "C1", "CONVEYOR", 0, 0, status=TeachingStatus.ALARM)],
        styles=[EquipmentStyle("CONVEYOR", "#123456", "star")],
        background=BackgroundImage("plan.png", x=10, y=20, scale=2.0, opacity=0.4),
    )
    restored = TeachingProject.from_dict(project.to_dict())
    assert restored.to_dict() == project.to_dict()
    assert restored.points[0].status == TeachingStatus.ALARM
    assert restored.style_for("CONVEYOR").shape == "star"
    assert restored.background.scale == 2.0


def test_style_for_falls_back():
    project = TeachingProject()
    assert project.style_for("UNKNOWN").type == "UNKNOWN"  # neutral fallback


def test_has_style_is_exact_membership():
    # style_for() fabricates a fallback for any name, so existence checks must
    # use has_style() (regression: the "Add type" button relied on this).
    project = TeachingProject()  # seeded with default styles
    assert project.has_style("WAYPOINT") is True
    assert project.has_style("DOCK") is False
    assert project.style_for("DOCK").type == "DOCK"  # fallback still works for rendering


def test_validation_flags_alarm():
    project = sample_project()
    project.points[0].status = TeachingStatus.ALARM
    issues = "\n".join(validate(project))
    assert "ALARM" in issues


def test_legacy_json_without_new_fields_loads():
    legacy = {
        "name": "old",
        "version": 1,
        "points": [{"id": 1, "name": "P1", "type": "WAYPOINT", "x": 0, "y": 0}],
        "routes": [],
    }
    project = TeachingProject.from_dict(legacy)
    assert project.points[0].status == TeachingStatus.IN_PROGRESS
    assert project.styles  # defaults applied
    assert project.background is None


def test_remove_point_also_cleans_routes():
    project = sample_project()
    project.remove_point(5)  # ST_A_LOAD, used by route A_to_B
    assert project.get_point(5) is None
    assert all(5 not in r.point_ids for r in project.routes)


def test_next_id():
    project = TeachingProject()
    assert project.next_id() == 1
    project.add_point(TeachingPoint(7, "p7"))
    assert project.next_id() == 8


def test_validation_flags_problems():
    project = TeachingProject(
        name="broken",
        points=[
            TeachingPoint(1, "DUP", PointType.WAYPOINT, 0, 0),
            TeachingPoint(2, "DUP", PointType.WAYPOINT, 0, 0),  # dup name + same pos
            TeachingPoint(3, "", PointType.WAYPOINT, 500, 500),  # empty name
        ],
        routes=[Route("bad", [1, 99])],  # references unknown id 99
    )
    issues = "\n".join(validate(project))
    assert "duplicate point name" in issues
    assert "empty name" in issues
    assert "unknown point id 99" in issues
    assert "no LOAD point" in issues
    assert "no UNLOAD point" in issues
    assert "almost the same position" in issues
