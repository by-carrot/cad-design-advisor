import pytest
from src.filtering.filter import filter_patterns


def test_cantilever_snap_matches_basic_cosmetic_case():
    results = filter_patterns(
        product_type="cosmetic_casing",
        production_method="injection_molding",
        volume=500,
        budget_tier="low",
        material="ABS",
    )
    ids = [r["id"] for r in results]
    assert "cantilever_snap" in ids


def test_living_hinge_excluded_for_resin_casting():
    results = filter_patterns(
        product_type="cosmetic_casing",
        production_method="resin_casting",
        volume=500,
        budget_tier="low",
        material="PP",
    )
    ids = [r["id"] for r in results]
    assert "living_hinge" not in ids


def test_living_hinge_excluded_for_abs():
    results = filter_patterns(
        product_type="cosmetic_casing",
        production_method="injection_molding",
        volume=5000,
        budget_tier="low",
        material="ABS",
    )
    ids = [r["id"] for r in results]
    assert "living_hinge" not in ids


def test_bayonet_excluded_for_low_volume():
    results = filter_patterns(
        product_type="cosmetic_casing",
        production_method="injection_molding",
        volume=100,
        budget_tier="low",
        material="ABS",
    )
    ids = [r["id"] for r in results]
    assert "bayonet_lock" not in ids


def test_annular_snap_requires_circular_geometry_material():
    results = filter_patterns(
        product_type="cosmetic_casing",
        production_method="injection_molding",
        volume=1000,
        budget_tier="low",
        material="PP",
    )
    ids = [r["id"] for r in results]
    assert "annular_snap" in ids


def test_no_results_for_unsupported_material():
    results = filter_patterns(
        product_type="cosmetic_casing",
        production_method="injection_molding",
        volume=1000,
        budget_tier="low",
        material="PEEK",
    )
    assert results == []


def test_press_fit_matches_across_all_budget_tiers():
    for tier in ["low", "medium", "high"]:
        results = filter_patterns(
            product_type="cosmetic_casing",
            production_method="injection_molding",
            volume=1000,
            budget_tier=tier,
            material="ABS",
        )
        ids = [r["id"] for r in results]
        assert "press_fit" in ids


def test_threaded_insert_excluded_above_volume_cap():
    results = filter_patterns(
        product_type="cosmetic_casing",
        production_method="injection_molding",
        volume=200000,
        budget_tier="high",
        material="ABS",
    )
    ids = [r["id"] for r in results]
    assert "threaded_insert" not in ids