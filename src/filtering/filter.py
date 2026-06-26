import json
from pathlib import Path


KB_PATH = Path(__file__).parent.parent / "knowledge_base" / "patterns.json"


def load_patterns() -> list[dict]:
    with open(KB_PATH, "r") as f:
        return json.load(f)["patterns"]


def filter_patterns(
    product_type: str,
    production_method: str,
    volume: int,
    budget_tier: str,
    material: str,
) -> list[dict]:
    patterns = load_patterns()
    results = []

    for pattern in patterns:
        if product_type not in pattern["product_types"]:
            continue
        if production_method not in pattern["production_methods"]:
            continue
        if not (pattern["volume_range"]["min"] <= volume <= pattern["volume_range"]["max"]):
            continue
        if budget_tier not in pattern["budget_tier"]:
            continue
        if material not in pattern["materials"]:
            continue
        results.append(pattern)

    return results