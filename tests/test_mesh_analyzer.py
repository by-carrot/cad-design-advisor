import numpy as np
import trimesh
import pytest
from src.geometry.mesh_analyzer import (
    load_mesh,
    detect_flat_planes,
    identify_mating_surfaces,
    analyze_mesh,
)


def make_box_mesh(x=30.0, y=20.0, z=10.0) -> trimesh.Trimesh:
    return trimesh.creation.box(extents=[x, y, z])


def test_load_mesh_returns_trimesh(tmp_path):
    mesh = make_box_mesh()
    path = tmp_path / "test.stl"
    mesh.export(str(path))
    loaded = load_mesh(str(path))
    assert isinstance(loaded, trimesh.Trimesh)
    assert len(loaded.faces) > 0


def test_detect_flat_planes_finds_six_faces_on_box():
    mesh = make_box_mesh()
    planes = detect_flat_planes(mesh, min_area_mm2=1.0)
    assert len(planes) == 6


def test_detect_flat_planes_filters_small_faces():
    mesh = make_box_mesh(x=30.0, y=20.0, z=10.0)
    planes = detect_flat_planes(mesh, min_area_mm2=1500.0)
    assert len(planes) == 0


def test_detect_flat_planes_sorted_by_area():
    mesh = make_box_mesh(x=30.0, y=20.0, z=10.0)
    planes = detect_flat_planes(mesh, min_area_mm2=1.0)
    areas = [p["area_mm2"] for p in planes]
    assert areas == sorted(areas, reverse=True)


def test_identify_mating_surfaces_finds_top_and_bottom():
    mesh = make_box_mesh()
    planes = detect_flat_planes(mesh, min_area_mm2=1.0)
    surfaces = identify_mating_surfaces(planes)
    assert surfaces["top_face"] is not None
    assert surfaces["bottom_face"] is not None


def test_identify_mating_surfaces_top_higher_than_bottom():
    mesh = make_box_mesh()
    planes = detect_flat_planes(mesh, min_area_mm2=1.0)
    surfaces = identify_mating_surfaces(planes)
    assert surfaces["top_face"]["centroid"][2] > surfaces["bottom_face"]["centroid"][2]


def test_analyze_mesh_returns_dimensions(tmp_path):
    mesh = make_box_mesh(x=30.0, y=20.0, z=10.0)
    path = tmp_path / "box.stl"
    mesh.export(str(path))
    result = analyze_mesh(str(path))
    assert abs(result["dimensions"]["x_mm"] - 30.0) < 0.1
    assert abs(result["dimensions"]["y_mm"] - 20.0) < 0.1
    assert abs(result["dimensions"]["z_mm"] - 10.0) < 0.1


def test_analyze_mesh_detects_planes(tmp_path):
    mesh = make_box_mesh()
    path = tmp_path / "box.stl"
    mesh.export(str(path))
    result = analyze_mesh(str(path))
    assert result["plane_count"] == 6


def test_split_bodies_finds_two_components(tmp_path):
    box1 = trimesh.creation.box(extents=[20, 20, 10])
    box1.apply_translation([0, 0, 0])
    box2 = trimesh.creation.box(extents=[20, 20, 5])
    box2.apply_translation([0, 0, 20])
    combined = trimesh.util.concatenate([box1, box2])
    path = tmp_path / "combined.stl"
    combined.export(str(path))
    from src.geometry.mesh_analyzer import split_bodies
    result = split_bodies(str(path))
    assert "error" not in result
    assert result["body_count"] == 2
    assert result["main_body"]["volume_mm3"] > result["cap"]["volume_mm3"]


def test_split_bodies_identifies_larger_as_main(tmp_path):
    box1 = trimesh.creation.box(extents=[30, 30, 15])
    box2 = trimesh.creation.box(extents=[10, 10, 5])
    box2.apply_translation([0, 0, 40])
    combined = trimesh.util.concatenate([box1, box2])
    path = tmp_path / "combined.stl"
    combined.export(str(path))
    from src.geometry.mesh_analyzer import split_bodies
    result = split_bodies(str(path))
    assert result["main_body"]["volume_mm3"] > result["cap"]["volume_mm3"]


def test_detect_parting_line_finds_opposing_faces():
    body = trimesh.creation.box(extents=[30, 20, 10])
    cap = trimesh.creation.box(extents=[30, 20, 5])
    cap.apply_translation([0, 0, 15])
    from src.geometry.mesh_analyzer import detect_parting_line
    result = detect_parting_line(body, cap)
    assert "error" not in result
    assert result["body_parting_face"] is not None
    assert result["cap_parting_face"] is not None