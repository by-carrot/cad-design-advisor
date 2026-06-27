import numpy as np
import trimesh
import pytest
from src.geometry.assembly_checker import (
    check_face_alignment,
    check_interference_fit,
    check_assembly,
)


def make_body():
    mesh = trimesh.creation.box(extents=[30, 20, 10])
    mesh.apply_translation([0, 0, 5])
    return mesh


def make_cap():
    mesh = trimesh.creation.box(extents=[30, 20, 5])
    mesh.apply_translation([0, 0, 12.5])
    return mesh


def make_misaligned_cap():
    mesh = trimesh.creation.box(extents=[30, 20, 5])
    mesh.apply_translation([10, 10, 12.5])
    return mesh


def test_face_alignment_passes_for_opposing_faces():
    body_face = {"normal": [0, 0, 1], "area_mm2": 600.0, "centroid": [0, 0, 10.0]}
    cap_face = {"normal": [0, 0, -1], "area_mm2": 600.0, "centroid": [0, 0, 12.5]}
    result = check_face_alignment(body_face, cap_face)
    assert result["aligned"] is True
    assert result["normals_opposing"] == True
    assert len(result["issues"]) == 0


def test_face_alignment_fails_for_same_direction_normals():
    body_face = {"normal": [0, 0, 1], "area_mm2": 600.0, "centroid": [0, 0, 10.0]}
    cap_face = {"normal": [0, 0, 1], "area_mm2": 600.0, "centroid": [0, 0, 12.5]}
    result = check_face_alignment(body_face, cap_face)
    assert result["aligned"] is False
    assert result["normals_opposing"] == False


def test_face_alignment_fails_for_large_xy_offset():
    body_face = {"normal": [0, 0, 1], "area_mm2": 600.0, "centroid": [0, 0, 10.0]}
    cap_face = {"normal": [0, 0, -1], "area_mm2": 600.0, "centroid": [20, 20, 12.5]}
    result = check_face_alignment(body_face, cap_face, tolerance_mm=2.0)
    assert result["aligned"] == False
    assert result["xy_offset_mm"] > 2.0


def test_interference_fit_detects_gap():
    body = make_body()
    cap = make_cap()
    cap.apply_translation([0, 0, 5])
    result = check_interference_fit(body, cap, "cantilever_snap", "ABS")
    assert result["gap_mm"] > 0


def test_interference_fit_detects_interference():
    body = make_body()
    cap = trimesh.creation.box(extents=[30, 20, 5])
    cap.apply_translation([0, 0, 9.0])
    result = check_interference_fit(body, cap, "press_fit", "ABS")
    assert result["interference_mm"] > 0


def test_check_assembly_compatible():
    body = make_body()
    cap = make_cap()
    body_face = {"normal": [0, 0, 1], "area_mm2": 600.0, "centroid": [0, 0, 10.0]}
    cap_face = {"normal": [0, 0, -1], "area_mm2": 600.0, "centroid": [0, 0, 12.5]}
    result = check_assembly(body, cap, body_face, cap_face, "cantilever_snap", "ABS")
    assert result["assembly_compatible"] == True
    assert result["issue_count"] == 0


def test_check_assembly_flags_misalignment():
    body = make_body()
    cap = make_misaligned_cap()
    body_face = {"normal": [0, 0, 1], "area_mm2": 600.0, "centroid": [0, 0, 10.0]}
    cap_face = {"normal": [0, 0, -1], "area_mm2": 600.0, "centroid": [10, 10, 12.5]}
    result = check_assembly(body, cap, body_face, cap_face, "cantilever_snap", "ABS")
    assert result["assembly_compatible"] == False
    assert result["issue_count"] > 0