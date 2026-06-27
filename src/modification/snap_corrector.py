import cadquery as cq
from pathlib import Path
from src.modification.snap_generator import export_snap
from src.geometry.snap_validator import CANTILEVER_RULES


def compute_corrected_dimensions(measurements: dict, material: str = "ABS") -> dict:
    arm_length = measurements["arm_length_mm"]
    root_thickness = measurements["root_thickness_mm"]

    corrected_arm_length = arm_length
    if arm_length < CANTILEVER_RULES["arm_length_min_mm"]:
        corrected_arm_length = CANTILEVER_RULES["arm_length_min_mm"] + 2.0

    corrected_root_thickness = root_thickness
    if root_thickness < CANTILEVER_RULES["arm_thickness_root_min_mm"]:
        corrected_root_thickness = CANTILEVER_RULES["arm_thickness_root_min_mm"] + 0.2
    if root_thickness > CANTILEVER_RULES["arm_thickness_root_max_mm"]:
        corrected_root_thickness = CANTILEVER_RULES["arm_thickness_root_max_mm"] - 0.2

    corrected_tip_thickness = corrected_root_thickness * 0.5
    corrected_root_radius = max(0.38, corrected_root_thickness * 0.3)
    arm_width = measurements.get("arm_width_mm", 6.0)

    return {
        "arm_length_mm": round(corrected_arm_length, 2),
        "root_thickness_mm": round(corrected_root_thickness, 2),
        "tip_thickness_mm": round(corrected_tip_thickness, 2),
        "tip_thickness_ratio": 0.5,
        "root_radius_mm": round(corrected_root_radius, 2),
        "arm_width_mm": round(arm_width, 2),
        "catch_depth_mm": 0.5,
    }


def generate_corrected_cantilever(
    corrected_dims: dict,
    placement_point: list[float],
    output_path: str,
) -> dict:
    arm_length = corrected_dims["arm_length_mm"]
    root_thickness = corrected_dims["root_thickness_mm"]
    tip_thickness = corrected_dims["tip_thickness_mm"]
    arm_width = corrected_dims["arm_width_mm"]
    catch_depth = corrected_dims["catch_depth_mm"]
    root_radius = corrected_dims["root_radius_mm"]

    arm = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(*placement_point))
        .polyline([
            (0, 0),
            (0, root_thickness),
            (arm_length, tip_thickness),
            (arm_length, 0),
        ])
        .close()
        .extrude(arm_width)
    )

    catch = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(*placement_point))
        .polyline([
            (arm_length, 0),
            (arm_length + catch_depth, tip_thickness / 2),
            (arm_length, tip_thickness),
        ])
        .close()
        .extrude(arm_width)
    )

    result = arm.union(catch)
    output_file = export_snap(result, output_path)

    return {
        "output_file": output_file,
        "corrected_dimensions": corrected_dims,
    }


def correct_snap_violations(
    validation_result: dict,
    placement_point: list[float],
    material: str,
    output_path: str,
) -> dict:
    if validation_result.get("passed"):
        return {
            "correction_needed": False,
            "message": "No corrections needed. Snap design meets all parameters.",
        }

    if not validation_result.get("measurements"):
        return {
            "correction_needed": True,
            "message": "Cannot generate correction: no measurements available.",
        }

    corrected = compute_corrected_dimensions(
        validation_result["measurements"],
        material=material,
    )

    geometry = generate_corrected_cantilever(
        corrected_dims=corrected,
        placement_point=placement_point,
        output_path=output_path,
    )

    return {
        "correction_needed": True,
        "violations_addressed": validation_result["violations"],
        "original_measurements": validation_result["measurements"],
        "corrected_dimensions": corrected,
        "output_file": geometry["output_file"],
    }