from fastapi import FastAPI
from pydantic import BaseModel
import trimesh
from src.filtering.filter import filter_patterns
from src.api.interpreter import interpret
import shutil
import uuid
from fastapi import UploadFile, File, Form
from src.geometry.mesh_analyzer import analyze_mesh
from src.modification.snap_generator import generate_snap_for_surface
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from src.geometry.mesh_analyzer import split_bodies, detect_parting_line

from src.geometry.snap_validator import validate_mesh_snaps
from src.modification.snap_corrector import correct_snap_violations



app = FastAPI()
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def index():
    with open("templates/index.html") as f:
        return f.read()

VALID_PRODUCT_TYPES = {"cosmetic_casing", "electronics_enclosure", "consumer_product", "bottle_cap", "circular_enclosure", "flip_top_cap", "compact_case", "pump_assembly", "insert_assembly"}
VALID_PRODUCTION_METHODS = {"injection_molding", "resin_casting", "fdm_printing", "cnc"}
VALID_BUDGET_TIERS = {"low", "medium", "high"}
VALID_MATERIALS = {"ABS", "PP", "PC", "Nylon_PA6", "TPE", "HDPE", "Brass", "Steel", "PLA"}

class DesignRequest(BaseModel):
    product_type: str
    production_method: str
    volume: int
    budget_tier: str
    material: str


@app.post("/recommend")
def recommend(request: DesignRequest):
    patterns = filter_patterns(
        product_type=request.product_type,
        production_method=request.production_method,
        volume=request.volume,
        budget_tier=request.budget_tier,
        material=request.material,
    )
    return {"patterns": patterns}

@app.post("/interpret")
def interpret_patterns(request: DesignRequest):
    patterns = filter_patterns(
        product_type=request.product_type,
        production_method=request.production_method,
        volume=request.volume,
        budget_tier=request.budget_tier,
        material=request.material,
    )
    if not patterns:
        return {"error": "No compatible patterns found for these constraints."}
    result = interpret(request.model_dump(), patterns)
    return result

@app.get("/health")
def health():
    return {"status": "ok"}


def clean_surface(surface: dict) -> dict:
    if surface is None:
        return None
    return {
        "normal": surface["normal"],
        "area_mm2": surface["area_mm2"],
        "centroid": surface["centroid"],
        "face_count": surface["face_count"],
    }


def clean_mesh_analysis(analysis: dict) -> dict:
    surfaces = analysis["mating_surfaces"]
    return {
        "dimensions": analysis["dimensions"],
        "volume_mm3": analysis["volume_mm3"],
        "face_count": analysis["face_count"],
        "is_watertight": analysis["is_watertight"],
        "plane_count": analysis["plane_count"],
        "mating_surfaces": {
            "top_face": clean_surface(surfaces.get("top_face")),
            "bottom_face": clean_surface(surfaces.get("bottom_face")),
            "largest_vertical_face": clean_surface(surfaces.get("largest_vertical_face")),
            "recommended_snap_face": clean_surface(surfaces.get("recommended_snap_face")),
        },
    }

@app.post("/analyze")
async def analyze(
    file: UploadFile = File(...),
    product_type: str = Form(...),
    production_method: str = Form(...),
    volume: int = Form(...),
    budget_tier: str = Form(...),
    material: str = Form(...),
):
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)
    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)

    material = material.upper()
    if product_type not in VALID_PRODUCT_TYPES:
        return {"error": f"Invalid product_type. Valid options: {sorted(VALID_PRODUCT_TYPES)}"}
    if production_method not in VALID_PRODUCTION_METHODS:
        return {"error": f"Invalid production_method. Valid options: {sorted(VALID_PRODUCTION_METHODS)}"}
    if budget_tier not in VALID_BUDGET_TIERS:
        return {"error": f"Invalid budget_tier. Valid options: {sorted(VALID_BUDGET_TIERS)}"}
    if material not in VALID_MATERIALS:
        return {"error": f"Invalid material. Valid options: {sorted(VALID_MATERIALS)}"}

    file_id = str(uuid.uuid4())
    input_path = upload_dir / f"{file_id}_{file.filename}"

    with open(input_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    split_result = split_bodies(str(input_path))

    if "error" in split_result:
        mesh_analysis = analyze_mesh(str(input_path))
        split_mode = False
    else:
        split_mode = True
        body_mesh = split_result["main_body"]["mesh"]
        cap_mesh = split_result["cap"]["mesh"]
        parting_line = detect_parting_line(body_mesh, cap_mesh)
        mesh_analysis = {
            "dimensions": analyze_mesh(str(input_path))["dimensions"],
            "volume_mm3": analyze_mesh(str(input_path))["volume_mm3"],
            "face_count": analyze_mesh(str(input_path))["face_count"],
            "is_watertight": analyze_mesh(str(input_path))["is_watertight"],
            "plane_count": analyze_mesh(str(input_path))["plane_count"],
            "body_count": split_result["body_count"],
            "main_body": {
                "volume_mm3": split_result["main_body"]["volume_mm3"],
                "face_count": split_result["main_body"]["face_count"],
            },
            "cap": {
                "volume_mm3": split_result["cap"]["volume_mm3"],
                "face_count": split_result["cap"]["face_count"],
            },
            "parting_line": parting_line,
            "mating_surfaces": {
                "recommended_snap_face": parting_line.get("body_parting_face"),
                "top_face": parting_line.get("body_parting_face"),
                "bottom_face": parting_line.get("cap_parting_face"),
                "largest_vertical_face": None,
            },
        }

    patterns = filter_patterns(
        product_type=product_type,
        production_method=production_method,
        volume=volume,
        budget_tier=budget_tier,
        material=material,
    )

    if not patterns:
        return {"error": "No compatible patterns found for these constraints."}

    top_pattern = patterns[0]
    recommended_surface = mesh_analysis["mating_surfaces"].get("recommended_snap_face")

    generated_geometry = None
    validation_result = None
    correction_result = None

    if recommended_surface:
        output_path = str(output_dir / f"{file_id}_{top_pattern['id']}.stl")
        generated_geometry = generate_snap_for_surface(
            pattern_id=top_pattern["id"],
            surface=recommended_surface,
            geometry_params=top_pattern["geometry_params"],
            output_path=output_path,
        )

        if split_mode:
            body_mesh = split_result["main_body"]["mesh"]
        else:
            body_mesh = trimesh.load(str(input_path))
            if isinstance(body_mesh, trimesh.Scene):
                body_mesh = trimesh.util.concatenate(body_mesh.dump())

        validation_result = validate_mesh_snaps(
            mesh=body_mesh,
            base_plane=recommended_surface,
            pattern_id=top_pattern["id"],
            material=material,
        )

        if validation_result.get("validations"):
            first_validation = validation_result["validations"][0]
            if not first_validation["passed"]:
                correction_path = str(output_dir / f"{file_id}_corrected.stl")
                correction_result = correct_snap_violations(
                    validation_result=first_validation,
                    placement_point=recommended_surface["centroid"],
                    material=material,
                    output_path=correction_path,
                )

    request_dict = {
        "product_type": product_type,
        "production_method": production_method,
        "volume": volume,
        "budget_tier": budget_tier,
        "material": material,
    }

    interpretation = interpret(request_dict, patterns)

    return {
        "file_id": file_id,
        "split_mode": split_mode,
        "mesh_analysis": clean_mesh_analysis(mesh_analysis),
        "patterns": patterns,
        "interpretation": interpretation,
        "generated_geometry": generated_geometry,
        "validation": validation_result,
        "correction": correction_result,
    }