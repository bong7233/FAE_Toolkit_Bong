"""Tests for the teaching-point model, persistence, and validation."""

import csv

from fae_toolkit.teaching import (
    PointType,
    Route,
    TeachingPoint,
    TeachingProject,
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
