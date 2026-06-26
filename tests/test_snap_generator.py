import pytest
import trimesh
from pathlib import Path
from src.modification.snap_generator import (
    generate_cantilever_snap,
    generate_annular_snap,
    export_snap,
    generate_snap_for_surface,
)


def test_cantilever_snap_generates_without_error():
    result = generate_cantilever_snap(
        arm_length_mm=10.0,
        arm_thickness_root_mm=1.2,
        arm_width_mm=6.0,
        catch_depth_mm=0.5,
        deflection_angle_deg=5.0,
        placement_point=[0, 0, 0],
        face_normal=[0, 0, 1],
    )
    assert result is not None


def test_annular_snap_generates_without_error():
    result = generate_annular_snap(
        diameter_mm=30.0,
        bead_height_mm=0.4,
        bead_radius_mm=0.4,
        wall_thickness_mm=2.0,
        placement_point=[0, 0, 0],
    )
    assert result is not None


def test_export_snap_creates_file(tmp_path):
    snap = generate_cantilever_snap(
        arm_length_mm=10.0,
        arm_thickness_root_mm=1.2,
        arm_width_mm=6.0,
        catch_depth_mm=0.5,
        deflection_angle_deg=5.0,
        placement_point=[0, 0, 0],
        face_normal=[0, 0, 1],
    )
    output = str(tmp_path / "snap.stl")
    result = export_snap(snap, output)
    assert Path(result).exists()
    assert Path(result).stat().st_size > 0


def test_generate_snap_for_surface_cantilever(tmp_path):
    surface = {"centroid": [0, 0, 5], "normal": [0, 0, 1]}
    geometry_params = {
        "arm_length_mm": {"min": 5, "max": 30},
        "arm_thickness_root_mm": {"min": 0.8, "max": 3.5},
        "catch_depth_mm": {"min": 0.3, "max": 1.5},
    }
    output = str(tmp_path / "cantilever.stl")
    result = generate_snap_for_surface(
        pattern_id="cantilever_snap",
        surface=surface,
        geometry_params=geometry_params,
        output_path=output,
    )
    assert "error" not in result
    assert Path(result["output_file"]).exists()


def test_generate_snap_for_surface_annular(tmp_path):
    surface = {"centroid": [0, 0, 0], "normal": [0, 0, 1]}
    geometry_params = {
        "bead_height_mm": {"min": 0.3, "max": 0.75},
    }
    output = str(tmp_path / "annular.stl")
    result = generate_snap_for_surface(
        pattern_id="annular_snap",
        surface=surface,
        geometry_params=geometry_params,
        output_path=output,
    )
    assert "error" not in result
    assert Path(result["output_file"]).exists()


def test_generate_snap_for_unsupported_pattern(tmp_path):
    surface = {"centroid": [0, 0, 0], "normal": [0, 0, 1]}
    result = generate_snap_for_surface(
        pattern_id="bayonet_lock",
        surface=surface,
        geometry_params={},
        output_path=str(tmp_path / "out.stl"),
    )
    assert "error" in result