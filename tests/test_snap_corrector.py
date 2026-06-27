import pytest
from pathlib import Path
from src.modification.snap_corrector import (
    compute_corrected_dimensions,
    generate_corrected_cantilever,
    correct_snap_violations,
)


def test_compute_corrected_dimensions_fixes_short_arm():
    measurements = {
        "arm_length_mm": 2.0,
        "root_thickness_mm": 1.5,
        "tip_thickness_mm": 0.75,
        "tip_thickness_ratio": 0.5,
        "arm_width_mm": 6.0,
    }
    result = compute_corrected_dimensions(measurements)
    assert result["arm_length_mm"] >= 5.0


def test_compute_corrected_dimensions_fixes_thin_root():
    measurements = {
        "arm_length_mm": 10.0,
        "root_thickness_mm": 0.3,
        "tip_thickness_mm": 0.15,
        "tip_thickness_ratio": 0.5,
        "arm_width_mm": 6.0,
    }
    result = compute_corrected_dimensions(measurements)
    assert result["root_thickness_mm"] >= 0.8


def test_compute_corrected_dimensions_sets_tip_ratio():
    measurements = {
        "arm_length_mm": 10.0,
        "root_thickness_mm": 1.5,
        "tip_thickness_mm": 1.4,
        "tip_thickness_ratio": 0.93,
        "arm_width_mm": 6.0,
    }
    result = compute_corrected_dimensions(measurements)
    assert result["tip_thickness_ratio"] == 0.5


def test_generate_corrected_cantilever_creates_file(tmp_path):
    corrected = {
        "arm_length_mm": 10.0,
        "root_thickness_mm": 1.5,
        "tip_thickness_mm": 0.75,
        "tip_thickness_ratio": 0.5,
        "root_radius_mm": 0.45,
        "arm_width_mm": 6.0,
        "catch_depth_mm": 0.5,
    }
    result = generate_corrected_cantilever(
        corrected_dims=corrected,
        placement_point=[0, 0, 0],
        output_path=str(tmp_path / "corrected.stl"),
    )
    assert Path(result["output_file"]).exists()
    assert Path(result["output_file"]).stat().st_size > 0


def test_correct_snap_violations_no_correction_when_passed():
    validation = {
        "passed": True,
        "violations": [],
        "warnings": [],
        "measurements": {
            "arm_length_mm": 10.0,
            "root_thickness_mm": 1.5,
            "tip_thickness_mm": 0.75,
            "tip_thickness_ratio": 0.5,
            "arm_width_mm": 6.0,
        },
    }
    result = correct_snap_violations(validation, [0, 0, 0], "ABS", "dummy.stl")
    assert result["correction_needed"] is False


def test_correct_snap_violations_generates_file_when_violations(tmp_path):
    validation = {
        "passed": False,
        "violations": ["Arm length 2.0mm is below minimum 5.0mm."],
        "warnings": [],
        "measurements": {
            "arm_length_mm": 2.0,
            "root_thickness_mm": 1.5,
            "tip_thickness_mm": 0.75,
            "tip_thickness_ratio": 0.5,
            "arm_width_mm": 6.0,
        },
    }
    result = correct_snap_violations(
        validation,
        [0, 0, 0],
        "ABS",
        str(tmp_path / "corrected.stl"),
    )
    assert result["correction_needed"] is True
    assert Path(result["output_file"]).exists()