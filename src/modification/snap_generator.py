import cadquery as cq
import numpy as np
from pathlib import Path
from src.geometry.snap_dimensioner import compute_cantilever_dimensions, compute_annular_snap_dimensions


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
    undercut_angle_deg: float = 45.0,
) -> cq.Workplane:
    outer_radius = diameter_mm / 2
    inner_radius = outer_radius - wall_thickness_mm

    bead_tip_r = outer_radius + bead_height_mm
    bead_base_r = outer_radius

    undercut_rad = np.radians(undercut_angle_deg)
    bead_depth = bead_radius_mm * 2

    profile_pts = [
        (inner_radius, 0),
        (inner_radius, bead_depth),
        (bead_base_r, bead_depth),
        (bead_tip_r, bead_depth / 2),
        (bead_base_r, 0),
    ]

    ring = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(*placement_point))
        .polyline(profile_pts)
        .close()
        .revolve(360, (0, 0, 0), (0, 1, 0))
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
    material: str = "ABS",
    assembly_type: str = "semi_permanent",
    wall_thickness_mm: float = 2.0,
    catch_depth_mm: float = 0.5,
    diameter_mm: float = 30.0,
) -> dict:
    placement_point = surface.get("centroid", [0, 0, 0])
    face_normal = surface.get("normal", [0, 0, 1])

    if pattern_id == "cantilever_snap":
        dims = compute_cantilever_dimensions(
            catch_depth_mm=catch_depth_mm,
            wall_thickness_mm=wall_thickness_mm,
            material=material,
            assembly_type=assembly_type,
        )
        result = generate_cantilever_snap(
            arm_length_mm=dims["arm_length_mm"],
            arm_thickness_root_mm=dims["root_thickness_mm"],
            arm_width_mm=6.0,
            catch_depth_mm=dims["catch_depth_mm"],
            deflection_angle_deg=5.0,
            placement_point=placement_point,
            face_normal=face_normal,
        )
        computed_dims = dims

    elif pattern_id == "annular_snap":
        dims = compute_annular_snap_dimensions(
            diameter_mm=diameter_mm,
            material=material,
            assembly_type=assembly_type,
            wall_thickness_mm=wall_thickness_mm,
        )
        result = generate_annular_snap(
            diameter_mm=diameter_mm,
            bead_height_mm=dims["bead_height_mm"],
            bead_radius_mm=dims["bead_radius_mm"],
            wall_thickness_mm=wall_thickness_mm,
            placement_point=placement_point,
        )
        computed_dims = dims

    else:
        return {"error": f"Snap generation not yet implemented for pattern: {pattern_id}"}

    output_file = export_snap(result, output_path)

    return {
        "pattern_id": pattern_id,
        "output_file": output_file,
        "placement_point": placement_point,
        "face_normal": face_normal,
        "computed_dimensions": computed_dims,
    }

def generate_snaps_for_placements(
    pattern_id: str,
    placements: list[dict],
    geometry_params: dict,
    output_dir: str,
    file_id: str,
    material: str = "ABS",
    assembly_type: str = "semi_permanent",
    catch_depth_mm: float = 0.5,
    face_normal: list[float] = None,
) -> list[dict]:
    results = []
    for i, placement in enumerate(placements):
        surface = {
            "centroid": placement["point"],
            "normal": face_normal or [0, 0, 1],
        }
        output_path = f"{output_dir}/{file_id}_{pattern_id}_snap_{i}.stl"
        result = generate_snap_for_surface(
            pattern_id=pattern_id,
            surface=surface,
            geometry_params=geometry_params,
            output_path=output_path,
            material=material,
            assembly_type=assembly_type,
            wall_thickness_mm=placement.get("wall_thickness_mm", 2.0),
            catch_depth_mm=catch_depth_mm,
        )
        if "error" not in result:
            results.append(result)
    return results