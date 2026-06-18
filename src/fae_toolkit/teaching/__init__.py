"""Teaching-point management: model, persistence, and validation.

Captures the AGV/AMR teaching workflow — naming positions, tagging them as
Load/Unload/Charge/etc., ordering them into routes, validating the result, and
importing/exporting in diff-friendly formats.
"""

from fae_toolkit.teaching.model import PointType, Route, TeachingPoint, TeachingProject
from fae_toolkit.teaching.store import (
    export_points_csv,
    load_project,
    sample_project,
    save_project,
    validate,
)

__all__ = [
    "PointType",
    "Route",
    "TeachingPoint",
    "TeachingProject",
    "load_project",
    "save_project",
    "export_points_csv",
    "validate",
    "sample_project",
]
