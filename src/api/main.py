from fastapi import FastAPI
from pydantic import BaseModel
from src.filtering.filter import filter_patterns
from src.api.interpreter import interpret

app = FastAPI()


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


@app.get("/health")
def health():
    return {"status": "ok"}

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