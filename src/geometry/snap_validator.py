import numpy as np
import trimesh


CANTILEVER_RULES = {
    "root_radius_min_mm": 0.38,
    "tip_thickness_ratio_max": 0.6,
    "tip_thickness_ratio_min": 0.4,
    "arm_length_min_mm": 5.0,
    "arm_length_max_mm": 30.0,
    "arm_thickness_root_min_mm": 0.8,
    "arm_thickness_root_max_mm": 3.5,
    "catch_depth_min_mm": 0.3,
    "catch_depth_max_mm": 1.5,
}


def detect_protrusions(mesh: trimesh.Trimesh, base_plane_normal: list, base_plane_centroid: list, min_protrusion_mm: float = 0.5) -> list[dict]:
    normal = np.array(base_plane_normal)
    centroid = np.array(base_plane_centroid)

    vertices = mesh.vertices
    projections = (vertices - centroid) @ normal
    protrusion_mask = projections > min_protrusion_mm

    if not np.any(protrusion_mask):
        return []

    protrusion_indices = np.where(protrusion_mask)[0]
    protrusion_heights = projections[protrusion_mask]

    face_mask = np.any(np.isin(mesh.faces, protrusion_indices), axis=1)
    protrusion_faces = mesh.faces[face_mask]

    if len(protrusion_faces) == 0:
        return []

    components = []
    visited = set()

    for face_idx in np.where(face_mask)[0]:
        if face_idx in visited:
            continue

        component_faces = [face_idx]
        queue = [face_idx]
        visited.add(face_idx)

        face_adjacency = mesh.face_adjacency
        adj_map = {}
        for pair in face_adjacency:
            adj_map.setdefault(pair[0], []).append(pair[1])
            adj_map.setdefault(pair[1], []).append(pair[0])

        while queue:
            current = queue.pop()
            for neighbor in adj_map.get(current, []):
                if neighbor not in visited and face_mask[neighbor]:
                    visited.add(neighbor)
                    component_faces.append(neighbor)
                    queue.append(neighbor)

        component_verts = mesh.vertices[np.unique(mesh.faces[component_faces])]
        heights = (component_verts - centroid) @ normal
        height = float(np.max(heights))
        width = float(np.max(component_verts[:, 0]) - np.min(component_verts[:, 0]))
        depth = float(np.max(component_verts[:, 1]) - np.min(component_verts[:, 1]))

        components.append({
            "face_count": len(component_faces),
            "height_mm": round(height, 2),
            "width_mm": round(width, 2),
            "depth_mm": round(depth, 2),
            "centroid": np.mean(component_verts, axis=0).tolist(),
        })

    return components


def measure_snap_arm(protrusion: dict) -> dict:
    arm_length = protrusion["height_mm"]
    arm_width = protrusion["width_mm"]
    arm_depth = protrusion["depth_mm"]
    root_thickness = arm_depth
    tip_thickness = root_thickness * 0.5

    return {
        "arm_length_mm": arm_length,
        "arm_width_mm": arm_width,
        "root_thickness_mm": root_thickness,
        "tip_thickness_mm": tip_thickness,
        "tip_thickness_ratio": round(tip_thickness / root_thickness, 2) if root_thickness > 0 else None,
    }


def validate_cantilever_snap(measurements: dict, material: str = "ABS") -> dict:
    violations = []
    warnings = []

    arm_length = measurements["arm_length_mm"]
    root_thickness = measurements["root_thickness_mm"]
    tip_ratio = measurements["tip_thickness_ratio"]

    if arm_length < CANTILEVER_RULES["arm_length_min_mm"]:
        violations.append(f"Arm length {arm_length}mm is below minimum {CANTILEVER_RULES['arm_length_min_mm']}mm. Short arms concentrate stress at the root and reduce deflection capacity.")

    if arm_length > CANTILEVER_RULES["arm_length_max_mm"]:
        warnings.append(f"Arm length {arm_length}mm exceeds typical range of {CANTILEVER_RULES['arm_length_max_mm']}mm. Very long arms may exhibit excessive flex and misalignment.")

    if root_thickness < CANTILEVER_RULES["arm_thickness_root_min_mm"]:
        violations.append(f"Root thickness {root_thickness}mm is below minimum {CANTILEVER_RULES['arm_thickness_root_min_mm']}mm for {material}. Risk of fracture at assembly.")

    if root_thickness > CANTILEVER_RULES["arm_thickness_root_max_mm"]:
        warnings.append(f"Root thickness {root_thickness}mm exceeds typical range. Arm may be too stiff to deflect without fracturing the mating part.")

    if tip_ratio is not None:
        if tip_ratio > CANTILEVER_RULES["tip_thickness_ratio_max"]:
            warnings.append(f"Tip-to-root thickness ratio {tip_ratio} is above optimal 0.5. Stress distribution is uneven. Taper more aggressively toward the tip.")
        if tip_ratio < CANTILEVER_RULES["tip_thickness_ratio_min"]:
            warnings.append(f"Tip-to-root thickness ratio {tip_ratio} is below 0.4. Tip may be too thin and prone to fracture at the catch.")

    return {
        "passed": len(violations) == 0,
        "violations": violations,
        "warnings": warnings,
        "measurements": measurements,
        "rules_applied": "Bayer MaterialScience snap-fit design guide (2013)",
    }


def validate_mesh_snaps(mesh: trimesh.Trimesh, base_plane: dict, pattern_id: str, material: str = "ABS") -> dict:
    protrusions = detect_protrusions(
        mesh=mesh,
        base_plane_normal=base_plane["normal"],
        base_plane_centroid=base_plane["centroid"],
        min_protrusion_mm=0.5,
    )

    if not protrusions:
        return {
            "snap_features_detected": 0,
            "message": "No snap features detected on this surface. The surface appears flat with no protrusions above 0.5mm.",
            "validations": [],
        }

    validations = []
    for p in protrusions:
        if p["height_mm"] < 2.0 or p["face_count"] < 4:
            continue
        aspect_ratio = p["height_mm"] / max(p["depth_mm"], 0.01)
        if aspect_ratio < 2.0:
            continue
        measurements = measure_snap_arm(p)
        if pattern_id == "cantilever_snap":
            result = validate_cantilever_snap(measurements, material)
            validations.append(result)

    return {
        "snap_features_detected": len(protrusions),
        "snap_features_validated": len(validations),
        "validations": validations,
    }