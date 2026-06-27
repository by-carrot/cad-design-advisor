from fastapi import FastAPI
from pydantic import BaseModel
from src.filtering.filter import filter_patterns
from src.api.interpreter import interpret
import shutil
import uuid
from fastapi import UploadFile, File, Form
from src.geometry.mesh_analyzer import analyze_mesh
from src.modification.snap_generator import generate_snap_for_surface
from pathlib import Path

app = FastAPI()

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

    mesh_analysis = analyze_mesh(str(input_path))

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
    if recommended_surface:
        output_path = str(output_dir / f"{file_id}_{top_pattern['id']}.stl")
        generated_geometry = generate_snap_for_surface(
            pattern_id=top_pattern["id"],
            surface=recommended_surface,
            geometry_params=top_pattern["geometry_params"],
            output_path=output_path,
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
        "mesh_analysis": clean_mesh_analysis(mesh_analysis),
        "patterns": patterns,
        "interpretation": interpretation,
        "generated_geometry": generated_geometry,
    }