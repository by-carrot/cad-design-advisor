import numpy as np
import trimesh


def check_face_alignment(
    body_face: dict,
    cap_face: dict,
    tolerance_mm: float = 2.0,
) -> dict:
    body_centroid = np.array(body_face["centroid"])
    cap_centroid = np.array(cap_face["centroid"])

    body_normal = np.array(body_face["normal"])
    cap_normal = np.array(cap_face["normal"])

    normals_opposing = float(np.dot(body_normal, cap_normal)) < -0.9

    xy_offset = np.sqrt(
        (body_centroid[0] - cap_centroid[0]) ** 2 +
        (body_centroid[1] - cap_centroid[1]) ** 2
    )

    z_gap = float(abs(body_centroid[2] - cap_centroid[2]))

    area_ratio = min(body_face["area_mm2"], cap_face["area_mm2"]) / max(body_face["area_mm2"], cap_face["area_mm2"])

    aligned = (
        normals_opposing and
        xy_offset < tolerance_mm and
        area_ratio > 0.5
    )

    issues = []
    if not normals_opposing:
        issues.append("Mating face normals are not opposing. Parts may be oriented incorrectly.")
    if xy_offset > tolerance_mm:
        issues.append(f"Mating faces are offset by {round(xy_offset, 2)}mm in XY. Alignment gap exceeds {tolerance_mm}mm tolerance.")
    if area_ratio < 0.5:
        issues.append(f"Mating face areas differ significantly (ratio {round(area_ratio, 2)}). Parts may not fully engage.")

    return {
        "aligned": aligned,
        "normals_opposing": normals_opposing,
        "xy_offset_mm": round(xy_offset, 2),
        "z_gap_mm": round(z_gap, 2),
        "area_ratio": round(area_ratio, 2),
        "issues": issues,
    }


def check_interference_fit(
    body_mesh: trimesh.Trimesh,
    cap_mesh: trimesh.Trimesh,
    pattern_id: str,
    material: str = "ABS",
) -> dict:
    INTERFERENCE_RANGES = {
        "cantilever_snap": {"min_mm": 0.0, "max_mm": 0.5},
        "annular_snap": {"min_mm": 0.0, "max_mm": 0.75},
        "press_fit": {"min_mm": 0.05, "max_mm": 0.15},
    }

    body_bounds = body_mesh.bounds
    cap_bounds = cap_mesh.bounds

    body_z_max = float(body_bounds[1][2])
    cap_z_min = float(cap_bounds[0][2])

    gap_mm = cap_z_min - body_z_max
    interference_mm = -gap_mm if gap_mm < 0 else 0.0
    actual_gap_mm = gap_mm if gap_mm > 0 else 0.0

    expected = INTERFERENCE_RANGES.get(pattern_id, {"min_mm": 0.0, "max_mm": 0.5})

    issues = []
    if actual_gap_mm > 1.0:
        issues.append(f"Parts have a {round(actual_gap_mm, 2)}mm gap along assembly axis. They will not engage without modification.")
    if interference_mm > expected["max_mm"]:
        issues.append(f"Interference of {round(interference_mm, 2)}mm exceeds maximum {expected['max_mm']}mm for {pattern_id}. Parts will not assemble without excessive force.")

    return {
        "gap_mm": round(actual_gap_mm, 2),
        "interference_mm": round(interference_mm, 2),
        "within_tolerance": len(issues) == 0,
        "expected_range_mm": expected,
        "issues": issues,
    }


def check_assembly(
    body_mesh: trimesh.Trimesh,
    cap_mesh: trimesh.Trimesh,
    body_parting_face: dict,
    cap_parting_face: dict,
    pattern_id: str,
    material: str = "ABS",
    alignment_tolerance_mm: float = 2.0,
) -> dict:
    face_alignment = check_face_alignment(
        body_face=body_parting_face,
        cap_face=cap_parting_face,
        tolerance_mm=alignment_tolerance_mm,
    )

    interference = check_interference_fit(
        body_mesh=body_mesh,
        cap_mesh=cap_mesh,
        pattern_id=pattern_id,
        material=material,
    )

    all_issues = face_alignment["issues"] + interference["issues"]
    assembly_compatible = face_alignment["aligned"] and interference["within_tolerance"]

    return {
        "assembly_compatible": assembly_compatible,
        "face_alignment": face_alignment,
        "interference_fit": interference,
        "issues": all_issues,
        "issue_count": len(all_issues),
    }