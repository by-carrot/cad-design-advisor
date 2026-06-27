import numpy as np
import trimesh
import open3d as o3d
from pathlib import Path


def load_mesh(file_path: str) -> trimesh.Trimesh:
    mesh = trimesh.load(file_path)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(mesh.dump())
    return mesh


def trimesh_to_open3d(mesh: trimesh.Trimesh) -> o3d.geometry.TriangleMesh:
    o3d_mesh = o3d.geometry.TriangleMesh()
    o3d_mesh.vertices = o3d.utility.Vector3dVector(mesh.vertices)
    o3d_mesh.triangles = o3d.utility.Vector3iVector(mesh.faces)
    o3d_mesh.compute_vertex_normals()
    return o3d_mesh


def detect_flat_planes(mesh: trimesh.Trimesh, min_area_mm2: float = 20.0) -> list[dict]:
    face_normals = mesh.face_normals
    face_areas = mesh.area_faces
    face_centroids = mesh.triangles_center

    canonical_normals = [
        np.array([0, 0, 1]),
        np.array([0, 0, -1]),
        np.array([0, 1, 0]),
        np.array([0, -1, 0]),
        np.array([1, 0, 0]),
        np.array([-1, 0, 0]),
    ]

    planes = []

    for canonical in canonical_normals:
        dot_products = face_normals @ canonical
        aligned_mask = dot_products > 0.95

        if not np.any(aligned_mask):
            continue

        aligned_areas = face_areas[aligned_mask]
        aligned_centroids = face_centroids[aligned_mask]
        aligned_indices = np.where(aligned_mask)[0]

        total_area = float(np.sum(aligned_areas))
        if total_area < min_area_mm2:
            continue

        weighted_centroid = np.average(
            aligned_centroids, weights=aligned_areas, axis=0
        )

        planes.append({
            "normal": canonical.tolist(),
            "area_mm2": round(total_area, 2),
            "centroid": weighted_centroid.tolist(),
            "face_indices": aligned_indices.tolist(),
            "face_count": int(np.sum(aligned_mask)),
        })

    planes.sort(key=lambda p: p["area_mm2"], reverse=True)
    return planes


def identify_mating_surfaces(planes: list[dict]) -> dict:
    if not planes:
        return {}

    horizontal = [p for p in planes if abs(p["normal"][2]) > 0.95]
    vertical = [p for p in planes if abs(p["normal"][2]) < 0.05]

    top_face = None
    bottom_face = None

    if horizontal:
        sorted_h = sorted(horizontal, key=lambda p: p["centroid"][2])
        bottom_face = sorted_h[0]
        top_face = sorted_h[-1]

    largest_vertical = vertical[0] if vertical else None

    return {
        "top_face": top_face,
        "bottom_face": bottom_face,
        "largest_vertical_face": largest_vertical,
        "recommended_snap_face": top_face or largest_vertical,
        "all_planes": planes,
    }


def analyze_mesh(file_path: str) -> dict:
    mesh = load_mesh(file_path)

    bounds = mesh.bounds
    dimensions = {
        "x_mm": round(float(bounds[1][0] - bounds[0][0]), 2),
        "y_mm": round(float(bounds[1][1] - bounds[0][1]), 2),
        "z_mm": round(float(bounds[1][2] - bounds[0][2]), 2),
    }

    planes = detect_flat_planes(mesh)
    mating_surfaces = identify_mating_surfaces(planes)

    return {
        "dimensions": dimensions,
        "volume_mm3": round(float(mesh.volume), 2),
        "face_count": len(mesh.faces),
        "is_watertight": bool(mesh.is_watertight),
        "mating_surfaces": mating_surfaces,
        "plane_count": len(planes),
    }

def split_bodies(file_path: str) -> dict:
    mesh = load_mesh(file_path)
    bodies = trimesh.graph.split(mesh, only_watertight=False)

    if len(bodies) < 2:
        return {
            "error": "Could not detect two separate bodies. Ensure the two parts are not touching in the STL.",
            "body_count": len(bodies),
        }

    bodies_sorted = sorted(bodies, key=lambda b: b.volume, reverse=True)
    main_body = bodies_sorted[0]
    cap = bodies_sorted[1]

    return {
        "body_count": len(bodies),
        "main_body": {
            "volume_mm3": round(float(main_body.volume), 2),
            "face_count": len(main_body.faces),
            "bounds": main_body.bounds.tolist(),
            "mesh": main_body,
        },
        "cap": {
            "volume_mm3": round(float(cap.volume), 2),
            "face_count": len(cap.faces),
            "bounds": cap.bounds.tolist(),
            "mesh": cap,
        },
    }


def detect_parting_line(body_mesh: trimesh.Trimesh, cap_mesh: trimesh.Trimesh) -> dict:
    body_planes = detect_flat_planes(body_mesh, min_area_mm2=10.0)
    cap_planes = detect_flat_planes(cap_mesh, min_area_mm2=10.0)

    if not body_planes or not cap_planes:
        return {"error": "Could not detect flat planes on one or both bodies."}

    best_body_plane = None
    best_cap_plane = None
    best_score = float("inf")

    for bp in body_planes:
        for cp in cap_planes:
            normals_opposing = np.dot(bp["normal"], cp["normal"]) < -0.9
            if not normals_opposing:
                continue
            z_distance = abs(bp["centroid"][2] - cp["centroid"][2])
            xy_distance = np.sqrt(
                (bp["centroid"][0] - cp["centroid"][0]) ** 2 +
                (bp["centroid"][1] - cp["centroid"][1]) ** 2
            )
            score = z_distance + xy_distance * 0.5
            if score < best_score:
                best_score = score
                best_body_plane = bp
                best_cap_plane = cp

    if best_body_plane is None:
        return {"error": "Could not find opposing mating faces between the two bodies."}

    return {
        "body_parting_face": {
            "normal": best_body_plane["normal"],
            "area_mm2": best_body_plane["area_mm2"],
            "centroid": best_body_plane["centroid"],
            "face_count": best_body_plane["face_count"],
        },
        "cap_parting_face": {
            "normal": best_cap_plane["normal"],
            "area_mm2": best_cap_plane["area_mm2"],
            "centroid": best_cap_plane["centroid"],
            "face_count": best_cap_plane["face_count"],
        },
        "separation_distance_mm": round(best_score, 2),
    }