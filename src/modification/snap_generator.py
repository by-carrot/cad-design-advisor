import cadquery as cq
import numpy as np
from pathlib import Path


def generate_cantilever_snap(
    arm_length_mm: float,
    arm_thickness_root_mm: float,
    arm_width_mm: float,
    catch_depth_mm: float,
    deflection_angle_deg: float,
    placement_point: list[float],
    face_normal: list[float],
) -> cq.Workplane:
    tip_thickness = arm_thickness_root_mm * 0.5
    catch_height = catch_depth_mm

    arm = (
        cq.Workplane("XZ")
        .polyline([
            (0, 0),
            (0, arm_thickness_root_mm),
            (arm_length_mm, tip_thickness),
            (arm_length_mm, 0),
        ])
        .close()
        .extrude(arm_width_mm)
    )

    catch = (
        cq.Workplane("XZ")
        .polyline([
            (arm_length_mm, 0),
            (arm_length_mm + catch_height, tip_thickness / 2),
            (arm_length_mm, tip_thickness),
        ])
        .close()
        .extrude(arm_width_mm)
    )

    result = arm.union(catch)

    normal = np.array(face_normal, dtype=float)
    normal = normal / np.linalg.norm(normal)
    default_normal = np.array([0, 0, 1], dtype=float)

    rotation_axis = np.cross(default_normal, normal)
    axis_norm = np.linalg.norm(rotation_axis)

    if axis_norm > 1e-6:
        rotation_axis = rotation_axis / axis_norm
        angle_rad = float(np.arccos(np.clip(np.dot(default_normal, normal), -1.0, 1.0)))
        angle_deg = float(np.degrees(angle_rad))
        result = result.rotate(
            (0, 0, 0),
            tuple(rotation_axis.tolist()),
            angle_deg,
        )

    px, py, pz = placement_point
    result = result.translate((px, py, pz))

    return result


def generate_annular_snap(
    diameter_mm: float,
    bead_height_mm: float,
    bead_radius_mm: float,
    wall_thickness_mm: float,
    placement_point: list[float],
) -> cq.Workplane:
    outer_radius = diameter_mm / 2
    inner_radius = outer_radius - wall_thickness_mm

    ring = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(*placement_point))
        .circle(outer_radius + bead_height_mm)
        .circle(inner_radius)
        .extrude(bead_radius_mm * 2)
    )

    return ring


def export_snap(workplane: cq.Workplane, output_path: str) -> str:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    cq.exporters.export(workplane, str(path))
    return str(path)


def generate_snap_for_surface(
    pattern_id: str,
    surface: dict,
    geometry_params: dict,
    output_path: str,
) -> dict:
    placement_point = surface.get("centroid", [0, 0, 0])
    face_normal = surface.get("normal", [0, 0, 1])

    if pattern_id == "cantilever_snap":
        arm_length = geometry_params.get("arm_length_mm", {})
        arm_length_val = arm_length.get("min", 10.0) if isinstance(arm_length, dict) else 10.0

        thickness = geometry_params.get("arm_thickness_root_mm", {})
        thickness_val = thickness.get("min", 1.2) if isinstance(thickness, dict) else 1.2

        catch_depth = geometry_params.get("catch_depth_mm", {})
        catch_val = catch_depth.get("min", 0.5) if isinstance(catch_depth, dict) else 0.5

        result = generate_cantilever_snap(
            arm_length_mm=arm_length_val,
            arm_thickness_root_mm=thickness_val,
            arm_width_mm=6.0,
            catch_depth_mm=catch_val,
            deflection_angle_deg=5.0,
            placement_point=placement_point,
            face_normal=face_normal,
        )

    elif pattern_id == "annular_snap":
        bead_height = geometry_params.get("bead_height_mm", {})
        bead_val = bead_height.get("min", 0.4) if isinstance(bead_height, dict) else 0.4

        result = generate_annular_snap(
            diameter_mm=30.0,
            bead_height_mm=bead_val,
            bead_radius_mm=0.4,
            wall_thickness_mm=2.0,
            placement_point=placement_point,
        )

    else:
        return {"error": f"Snap generation not yet implemented for pattern: {pattern_id}"}

    output_file = export_snap(result, output_path)

    return {
        "pattern_id": pattern_id,
        "output_file": output_file,
        "placement_point": placement_point,
        "face_normal": face_normal,
    }