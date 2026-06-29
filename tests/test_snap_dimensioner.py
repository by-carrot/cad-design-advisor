import pytest
from src.geometry.snap_dimensioner import (
    get_strain,
    compute_cantilever_dimensions,
    compute_annular_snap_dimensions,
    MATERIAL_STRAIN,
)


def test_get_strain_semi_permanent_is_reduced():
    strain_single = get_strain("ABS", "single")
    strain_semi = get_strain("ABS", "semi_permanent")
    assert strain_semi < strain_single


def test_get_strain_easy_release_is_lowest():
    strain_semi = get_strain("ABS", "semi_permanent")
    strain_easy = get_strain("ABS", "easy_release")
    assert strain_easy < strain_semi


def test_get_strain_unknown_material_falls_back_to_abs():
    strain = get_strain("UNKNOWN", "single")
    assert strain == get_strain("ABS", "single")


def test_compute_cantilever_dimensions_returns_all_keys():
    result = compute_cantilever_dimensions(
        catch_depth_mm=0.5,
        wall_thickness_mm=2.0,
        material="ABS",
        assembly_type="semi_permanent",
    )
    required_keys = [
        "arm_length_mm", "root_thickness_mm", "tip_thickness_mm",
        "root_radius_mm", "catch_depth_mm", "permissible_strain",
        "deflection_capacity_mm", "meets_catch_requirement",
    ]
    for key in required_keys:
        assert key in result


def test_compute_cantilever_dimensions_arm_within_bounds():
    result = compute_cantilever_dimensions(
        catch_depth_mm=0.5,
        wall_thickness_mm=2.0,
        material="ABS",
        assembly_type="semi_permanent",
    )
    assert 5.0 <= result["arm_length_mm"] <= 30.0


def test_compute_cantilever_dimensions_tip_ratio_is_half():
    result = compute_cantilever_dimensions(
        catch_depth_mm=0.5,
        wall_thickness_mm=2.0,
        material="ABS",
        assembly_type="semi_permanent",
    )
    assert abs(result["tip_thickness_mm"] / result["root_thickness_mm"] - 0.5) < 0.01


def test_compute_cantilever_dimensions_root_radius_above_minimum():
    result = compute_cantilever_dimensions(
        catch_depth_mm=0.5,
        wall_thickness_mm=2.0,
        material="ABS",
        assembly_type="semi_permanent",
    )
    assert result["root_radius_mm"] >= 0.38


def test_compute_cantilever_pc_allows_longer_arm_than_abs():
    abs_result = compute_cantilever_dimensions(
        catch_depth_mm=1.2,
        wall_thickness_mm=2.0,
        material="ABS",
        assembly_type="single",
    )
    pc_result = compute_cantilever_dimensions(
        catch_depth_mm=1.2,
        wall_thickness_mm=2.0,
        material="PC",
        assembly_type="single",
    )
    assert pc_result["arm_length_mm"] < abs_result["arm_length_mm"]


def test_compute_annular_snap_bead_height_within_bounds():
    result = compute_annular_snap_dimensions(
        diameter_mm=30.0,
        material="ABS",
        assembly_type="semi_permanent",
    )
    assert 0.2 <= result["bead_height_mm"] <= 0.75


def test_compute_annular_snap_larger_diameter_gives_larger_bead():
    small = compute_annular_snap_dimensions(diameter_mm=20.0, material="PP")
    large = compute_annular_snap_dimensions(diameter_mm=50.0, material="PP")
    assert large["bead_height_mm"] >= small["bead_height_mm"]