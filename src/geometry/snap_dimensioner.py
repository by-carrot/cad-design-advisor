import numpy as np


MATERIAL_STRAIN = {
    "ABS": {"single": 0.025, "frequent": 0.015},
    "PP": {"single": 0.025, "frequent": 0.015},
    "PC": {"single": 0.040, "frequent": 0.024},
    "PC_ABS": {"single": 0.025, "frequent": 0.015},
    "Nylon_PA6": {"single": 0.030, "frequent": 0.018},
    "TPE": {"single": 0.050, "frequent": 0.030},
    "HDPE": {"single": 0.030, "frequent": 0.018},
}

SEMI_PERMANENT_STRAIN_FACTOR = 0.6
PERMANENT_STRAIN_FACTOR = 1.0
EASY_RELEASE_STRAIN_FACTOR = 0.4


def get_strain(material: str, assembly_type: str = "semi_permanent") -> float:
    strains = MATERIAL_STRAIN.get(material, MATERIAL_STRAIN["ABS"])

    if assembly_type == "single":
        return strains["single"] * PERMANENT_STRAIN_FACTOR
    elif assembly_type == "semi_permanent":
        return strains["frequent"] * SEMI_PERMANENT_STRAIN_FACTOR
    elif assembly_type == "easy_release":
        return strains["frequent"] * EASY_RELEASE_STRAIN_FACTOR
    return strains["frequent"]


def compute_cantilever_dimensions(
    catch_depth_mm: float,
    wall_thickness_mm: float,
    material: str = "ABS",
    assembly_type: str = "semi_permanent",
    arm_width_mm: float = 6.0,
) -> dict:
    strain = get_strain(material, assembly_type)
    root_thickness = min(wall_thickness_mm * 0.6, 2.5)
    root_thickness = max(root_thickness, 0.8)

    arm_length = np.sqrt((catch_depth_mm * 0.9 * root_thickness) / strain)
    arm_length = float(np.clip(arm_length, 5.0, 30.0))

    tip_thickness = root_thickness * 0.5
    root_radius = max(0.38, root_thickness * 0.3)

    deflection_check = (strain * arm_length ** 2) / (0.9 * root_thickness)
    meets_requirement = deflection_check >= catch_depth_mm

    return {
        "arm_length_mm": round(arm_length, 2),
        "root_thickness_mm": round(root_thickness, 2),
        "tip_thickness_mm": round(tip_thickness, 2),
        "root_radius_mm": round(root_radius, 2),
        "arm_width_mm": round(arm_width_mm, 2),
        "catch_depth_mm": round(catch_depth_mm, 2),
        "permissible_strain": round(strain, 4),
        "deflection_capacity_mm": round(deflection_check, 3),
        "meets_catch_requirement": meets_requirement,
        "material": material,
        "assembly_type": assembly_type,
        "source": "Bayer MaterialScience snap-fit design guide (2013), tapered cantilever formula p.11",
    }


def compute_annular_snap_dimensions(
    diameter_mm: float,
    material: str = "ABS",
    assembly_type: str = "semi_permanent",
    wall_thickness_mm: float = 2.0,
) -> dict:
    strain = get_strain(material, assembly_type)
    bead_height = strain * diameter_mm
    bead_height = float(np.clip(bead_height, 0.2, 0.75))
    bead_radius = bead_height * 0.5
    undercut_angle = 45.0
    engagement_length = max(1.0, diameter_mm * 0.05)

    return {
        "bead_height_mm": round(bead_height, 3),
        "bead_radius_mm": round(bead_radius, 3),
        "undercut_angle_deg": undercut_angle,
        "engagement_length_mm": round(engagement_length, 2),
        "wall_thickness_mm": round(wall_thickness_mm, 2),
        "permissible_strain": round(strain, 4),
        "material": material,
        "assembly_type": assembly_type,
        "source": "Bayer MaterialScience snap-fit design guide (2013), annular snap formula y_pm = strain x diameter, p.21",
    }