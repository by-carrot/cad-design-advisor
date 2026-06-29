import numpy as np
import trimesh
from src.geometry.snap_dimensioner import compute_cantilever_dimensions


def compute_wall_thickness_at_point(
    mesh: trimesh.Trimesh,
    point: np.ndarray,
    face_normal: np.ndarray,
    num_samples: int = 8,
) -> float:
    ray_origin = point + face_normal * 0.1
    ray_direction = -face_normal

    locations, _, _ = mesh.ray.intersects_location(
        ray_origins=[ray_origin],
        ray_directions=[ray_direction],
    )

    if len(locations) == 0:
        return 2.0

    distances = np.linalg.norm(locations - point, axis=1)
    distances = distances[distances > 0.05]

    if len(distances) == 0:
        return 2.0

    return float(np.min(distances))


def sample_perimeter_points(
    face_vertices: np.ndarray,
    n_points: int = 12,
) -> np.ndarray:
    centroid = np.mean(face_vertices, axis=0)
    angles = np.linspace(0, 2 * np.pi, n_points, endpoint=False)

    x_range = np.max(face_vertices[:, 0]) - np.min(face_vertices[:, 0])
    y_range = np.max(face_vertices[:, 1]) - np.min(face_vertices[:, 1])
    radius_x = x_range * 0.35
    radius_y = y_range * 0.35

    points = []
    for angle in angles:
        p = centroid.copy()
        p[0] += radius_x * np.cos(angle)
        p[1] += radius_y * np.sin(angle)
        points.append(p)

    return np.array(points)


def score_placement_point(
    point: np.ndarray,
    wall_thickness: float,
    face_normal: np.ndarray,
    face_centroid: np.ndarray,
    material: str,
    assembly_type: str,
    catch_depth_mm: float,
) -> dict:
    dims = compute_cantilever_dimensions(
        catch_depth_mm=catch_depth_mm,
        wall_thickness_mm=wall_thickness,
        material=material,
        assembly_type=assembly_type,
    )

    wall_score = 1.0 if wall_thickness >= dims["root_thickness_mm"] * 1.5 else wall_thickness / (dims["root_thickness_mm"] * 1.5)
    meets_requirement = dims["meets_catch_requirement"]

    distance_from_centroid = float(np.linalg.norm(point - face_centroid))
    distribution_score = min(1.0, distance_from_centroid / 10.0)

    total_score = (wall_score * 0.6) + (distribution_score * 0.4)
    if not meets_requirement:
        total_score *= 0.5

    return {
        "point": point.tolist(),
        "wall_thickness_mm": round(wall_thickness, 2),
        "score": round(total_score, 3),
        "computed_dimensions": dims,
        "meets_catch_requirement": meets_requirement,
    }


def optimize_snap_placement(
    mesh: trimesh.Trimesh,
    parting_face: dict,
    material: str = "ABS",
    assembly_type: str = "semi_permanent",
    catch_depth_mm: float = 0.5,
    n_snaps: int = 4,
    n_candidates: int = 12,
) -> dict:
    face_normal = np.array(parting_face["normal"], dtype=float)
    face_centroid = np.array(parting_face["centroid"], dtype=float)

    face_indices = parting_face.get("face_indices", [])
    if face_indices:
        face_verts = mesh.vertices[np.unique(mesh.faces[face_indices])]
    else:
        face_verts = np.array([
            face_centroid + np.array([10, 10, 0]),
            face_centroid + np.array([-10, 10, 0]),
            face_centroid + np.array([-10, -10, 0]),
            face_centroid + np.array([10, -10, 0]),
        ])

    candidate_points = sample_perimeter_points(face_verts, n_candidates)

    scored = []
    for pt in candidate_points:
        wall_thickness = compute_wall_thickness_at_point(mesh, pt, face_normal)
        score_result = score_placement_point(
            point=pt,
            wall_thickness=wall_thickness,
            face_normal=face_normal,
            face_centroid=face_centroid,
            material=material,
            assembly_type=assembly_type,
            catch_depth_mm=catch_depth_mm,
        )
        scored.append(score_result)

    scored.sort(key=lambda x: x["score"], reverse=True)

    selected = []
    min_spacing = 15.0
    for candidate in scored:
        pt = np.array(candidate["point"])
        too_close = False
        for existing in selected:
            if np.linalg.norm(pt - np.array(existing["point"])) < min_spacing:
                too_close = True
                break
        if not too_close:
            selected.append(candidate)
        if len(selected) >= n_snaps:
            break

    return {
        "recommended_placements": selected,
        "placement_count": len(selected),
        "n_snaps_requested": n_snaps,
        "material": material,
        "assembly_type": assembly_type,
        "catch_depth_mm": catch_depth_mm,
    }