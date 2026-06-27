import numpy as np
import trimesh
import pytest
from src.geometry.snap_validator import (
    detect_protrusions,
    measure_snap_arm,
    validate_cantilever_snap,
    validate_mesh_snaps,
)


def make_flat_base_with_protrusion(base_size=30.0, base_height=2.0, arm_length=10.0, arm_width=6.0, arm_thickness=1.2):
    base = trimesh.creation.box(extents=[base_size, base_size, base_height])
    arm = trimesh.creation.box(extents=[arm_width, arm_thickness, arm_length])
    arm.apply_translation([0, 0, base_height / 2 + arm_length / 2])
    return trimesh.util.concatenate([base, arm])


def test_detect_protrusions_finds_arm():
    mesh = make_flat_base_with_protrusion()
    base_plane = {"normal": [0, 0, 1], "centroid": [0, 0, 1.0]}
    protrusions = detect_protrusions(mesh, base_plane["normal"], base_plane["centroid"], min_protrusion_mm=0.5)
    assert len(protrusions) > 0


def test_detect_protrusions_none_on_flat_surface():
    mesh = trimesh.creation.box(extents=[30, 30, 5])
    base_plane = {"normal": [0, 0, 1], "centroid": [0, 0, 2.5]}
    protrusions = detect_protrusions(mesh, base_plane["normal"], base_plane["centroid"], min_protrusion_mm=0.5)
    assert len(protrusions) == 0


def test_measure_snap_arm_returns_expected_keys():
    protrusion = {"height_mm": 10.0, "width_mm": 6.0, "depth_mm": 1.2, "centroid": [0, 0, 5]}
    result = measure_snap_arm(protrusion)
    assert "arm_length_mm" in result
    assert "root_thickness_mm" in result
    assert "tip_thickness_ratio" in result
    assert result["tip_thickness_ratio"] == 0.5


def test_validate_cantilever_snap_passes_good_design():
    measurements = {
        "arm_length_mm": 12.0,
        "arm_width_mm": 6.0,
        "root_thickness_mm": 1.5,
        "tip_thickness_mm": 0.75,
        "tip_thickness_ratio": 0.5,
    }
    result = validate_cantilever_snap(measurements, material="ABS")
    assert result["passed"] is True
    assert len(result["violations"]) == 0


def test_validate_cantilever_snap_flags_short_arm():
    measurements = {
        "arm_length_mm": 2.0,
        "arm_width_mm": 6.0,
        "root_thickness_mm": 1.5,
        "tip_thickness_mm": 0.75,
        "tip_thickness_ratio": 0.5,
    }
    result = validate_cantilever_snap(measurements, material="ABS")
    assert result["passed"] is False
    assert any("length" in v.lower() for v in result["violations"])


def test_validate_cantilever_snap_flags_thin_root():
    measurements = {
        "arm_length_mm": 12.0,
        "arm_width_mm": 6.0,
        "root_thickness_mm": 0.3,
        "tip_thickness_mm": 0.15,
        "tip_thickness_ratio": 0.5,
    }
    result = validate_cantilever_snap(measurements, material="ABS")
    assert result["passed"] is False
    assert any("thickness" in v.lower() for v in result["violations"])


def test_validate_mesh_snaps_no_features_on_flat():
    mesh = trimesh.creation.box(extents=[30, 30, 5])
    base_plane = {"normal": [0, 0, 1], "centroid": [0, 0, 2.5]}
    result = validate_mesh_snaps(mesh, base_plane, "cantilever_snap", "ABS")
    assert result["snap_features_detected"] == 0


def test_validate_mesh_snaps_detects_protrusion():
    mesh = make_flat_base_with_protrusion(arm_length=12.0, arm_thickness=1.5)
    base_plane = {"normal": [0, 0, 1], "centroid": [0, 0, 1.0]}
    result = validate_mesh_snaps(mesh, base_plane, "cantilever_snap", "ABS")
    assert result["snap_features_detected"] > 0