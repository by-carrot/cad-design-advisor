import numpy as np
import trimesh
import pytest
from src.geometry.placement_optimizer import (
    sample_perimeter_points,
    score_placement_point,
    optimize_snap_placement,
    compute_wall_thickness_at_point,
)


def make_box_mesh(x=60.0, y=40.0, z=10.0):
    return trimesh.creation.box(extents=[x, y, z])


def test_sample_perimeter_points_returns_correct_count():
    verts = np.array([
        [30, 20, 5], [-30, 20, 5], [-30, -20, 5], [30, -20, 5]
    ], dtype=float)
    points = sample_perimeter_points(verts, n_points=8)
    assert len(points) == 8


def test_sample_perimeter_points_distributed_around_centroid():
    verts = np.array([
        [30, 20, 5], [-30, 20, 5], [-30, -20, 5], [30, -20, 5]
    ], dtype=float)
    points = sample_perimeter_points(verts, n_points=8)
    centroid = np.mean(verts, axis=0)
    distances = np.linalg.norm(points - centroid, axis=1)
    assert np.all(distances > 0)


def test_score_placement_point_returns_expected_keys():
    result = score_placement_point(
        point=np.array([10, 10, 5]),
        wall_thickness=2.0,
        face_normal=np.array([0, 0, 1]),
        face_centroid=np.array([0, 0, 5]),
        material="ABS",
        assembly_type="semi_permanent",
        catch_depth_mm=0.5,
    )
    assert "score" in result
    assert "wall_thickness_mm" in result
    assert "computed_dimensions" in result
    assert "meets_catch_requirement" in result


def test_score_placement_higher_for_adequate_wall():
    thin_wall = score_placement_point(
        point=np.array([10, 10, 5]),
        wall_thickness=0.5,
        face_normal=np.array([0, 0, 1]),
        face_centroid=np.array([0, 0, 5]),
        material="ABS",
        assembly_type="semi_permanent",
        catch_depth_mm=0.5,
    )
    thick_wall = score_placement_point(
        point=np.array([10, 10, 5]),
        wall_thickness=3.0,
        face_normal=np.array([0, 0, 1]),
        face_centroid=np.array([0, 0, 5]),
        material="ABS",
        assembly_type="semi_permanent",
        catch_depth_mm=0.5,
    )
    assert thick_wall["score"] > thin_wall["score"]


def test_optimize_snap_placement_returns_placements():
    mesh = make_box_mesh()
    parting_face = {
        "normal": [0, 0, 1],
        "centroid": [0, 0, 5],
        "area_mm2": 2400.0,
        "face_indices": [],
    }
    result = optimize_snap_placement(
        mesh=mesh,
        parting_face=parting_face,
        material="ABS",
        assembly_type="semi_permanent",
        n_snaps=4,
        n_candidates=12,
    )
    assert "recommended_placements" in result
    assert result["placement_count"] > 0


def test_optimize_snap_placement_respects_spacing():
    mesh = make_box_mesh()
    parting_face = {
        "normal": [0, 0, 1],
        "centroid": [0, 0, 5],
        "area_mm2": 2400.0,
        "face_indices": [],
    }
    result = optimize_snap_placement(
        mesh=mesh,
        parting_face=parting_face,
        material="ABS",
        assembly_type="semi_permanent",
        n_snaps=4,
        n_candidates=12,
    )
    placements = result["recommended_placements"]
    for i in range(len(placements)):
        for j in range(i + 1, len(placements)):
            p1 = np.array(placements[i]["point"])
            p2 = np.array(placements[j]["point"])
            assert np.linalg.norm(p1 - p2) >= 15.0