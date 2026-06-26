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