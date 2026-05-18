"""Comprehensive test suite for the A/B testing pipeline."""
import pytest
import numpy as np
import pandas as pd

from tests.conftest import make_df
from src.data_validation import run_validation
from src.statistical_tests import z_test_proportions, segment_analysis
from src.decision_framework import generate_recommendation
from src.power_analysis import calculate_required_sample_size, calculate_achieved_power
from src.config import load_config, reset_config


# ═══════════════════════════════════════════════════════════════════════════════
# 1. DATA VALIDATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_validation_passes_valid_data(config):
    df = make_df(0.12, 0.15)
    report = run_validation(df, config)
    assert report["passed"] is True
    assert "columns" in report["details"]


def test_validation_fails_missing_column(config):
    df = make_df(0.12, 0.15).drop(columns=["revenue"])
    report = run_validation(df, config)
    assert report["passed"] is False
    assert any("Missing" in w for w in report["warnings"])


def test_validation_fails_duplicate_users(config):
    df = make_df(0.12, 0.15)
    df_with_dups = pd.concat([df, df.head(10)], ignore_index=True)
    report = run_validation(df_with_dups, config)
    assert report["passed"] is False


# ═══════════════════════════════════════════════════════════════════════════════
# 2. STATISTICAL TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_z_test_detects_positive_lift():
    df = make_df(0.10, 0.15, n=2000)
    res = z_test_proportions(df)
    assert res["significant"] is True
    assert res["lift_percent"] > 0
    assert res["p_value"] < 0.05


def test_z_test_handles_no_difference():
    df = make_df(0.12, 0.12, n=2000)
    res = z_test_proportions(df)
    assert res["significant"] is False
    assert abs(res["lift_percent"]) < 5


def test_z_test_ci_contains_zero_when_not_significant():
    df = make_df(0.12, 0.12, n=2000)
    res = z_test_proportions(df)
    assert res["ci_95"][0] < 0 < res["ci_95"][1]


# ═══════════════════════════════════════════════════════════════════════════════
# 3. DECISION FRAMEWORK TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_decision_scale_variant():
    stats = {"p_value": 0.01, "lift_percent": 8.0, "ci_95": [2.1, 13.9], "ci_width": 11.8}
    res = generate_recommendation(stats, achieved_power=0.85)
    assert "SCALE VARIANT B" in res["recommendation"]


def test_decision_guardrail_overrides_positive_result():
    stats = {"p_value": 0.01, "lift_percent": 8.0, "ci_95": [2.1, 13.9], "ci_width": 11.8}
    res = generate_recommendation(stats, guardrail_breached=True)
    assert "GUARDRAIL BREACH" in res["recommendation"]


def test_decision_underpowered():
    stats = {"p_value": 0.15, "lift_percent": 4.0, "ci_95": [-1.0, 9.0], "ci_width": 10.0}
    res = generate_recommendation(stats, achieved_power=0.45)
    assert "INCREASE SAMPLE SIZE" in res["recommendation"]


def test_decision_negative_impact():
    stats = {"p_value": 0.02, "lift_percent": -5.0, "ci_95": [-9.0, -1.0], "ci_width": 8.0}
    res = generate_recommendation(stats)
    assert "DO NOT SCALE" in res["recommendation"]


# ═══════════════════════════════════════════════════════════════════════════════
# 4. POWER ANALYSIS TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_required_sample_size_reasonable():
    n = calculate_required_sample_size(0.12, 0.15)
    assert n > 1000
    assert isinstance(n, int)


def test_achieved_power_increases_with_sample_size():
    p_small = calculate_achieved_power(0.12, 0.15, n_per_group=500)
    p_large = calculate_achieved_power(0.12, 0.15, n_per_group=3000)
    assert p_large > p_small


def test_achieved_power_zero_for_negative_lift():
    power = calculate_achieved_power(0.12, -0.05, n_per_group=1000)
    assert power == 0.0


def test_required_sample_size_invalid_inputs():
    with pytest.raises(ValueError):
        calculate_required_sample_size(1.5, 0.15)
    with pytest.raises(ValueError):
        calculate_required_sample_size(0.12, -0.10)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. SEGMENT ANALYSIS — HOLM-BONFERRONI CORRECTION
# ═══════════════════════════════════════════════════════════════════════════════

def _build_segmented_df(
    true_effect_segment: str,
    conv_a: float = 0.12,
    conv_b: float = 0.20,
    null_conv: float = 0.12,
    n_per_cell: int = 600,
    seed: int = 0,
) -> pd.DataFrame:
    np.random.seed(seed)
    rows = []
    segments = ["New_SME", "Established_SME", "Enterprise"]

    for seg in segments:
        for variant in ["A", "B"]:
            if seg == true_effect_segment and variant == "B":
                rate = conv_b
            else:
                rate = conv_a if variant == "A" else null_conv

            rows.append(pd.DataFrame({
                "user_id": [f"{seg}_{variant}_{i}" for i in range(n_per_cell)],
                "variant": variant,
                "converted": np.random.binomial(1, rate, n_per_cell),
                "revenue": np.random.exponential(50, n_per_cell),
                "unsubscribed": 0,
                "segment": seg,
                "timestamp": pd.date_range("2026-01-01", periods=n_per_cell, freq="h"),
            }))

    return pd.concat(rows, ignore_index=True)


def test_segment_holm_correction_exists():
    df = _build_segmented_df("New_SME")
    res_df = segment_analysis(df)
    assert "p_value_corrected" in res_df.columns
    assert "significant_corrected" in res_df.columns


def test_segment_holm_corrected_pvalues_are_conservative():
    df = _build_segmented_df("New_SME")
    res_df = segment_analysis(df)
    assert all(res_df["p_value_corrected"] >= res_df["p_value"] - 1e-10)


def test_segment_true_effect_survives_correction():
    df = _build_segmented_df("New_SME", conv_b=0.22, n_per_cell=800)
    res_df = segment_analysis(df)
    true_seg = res_df[res_df["segment"] == "New_SME"]
    assert not true_seg.empty
    assert bool(true_seg["significant_corrected"].iloc[0])


def test_segment_null_segments_not_falsely_flagged():
    df = _build_segmented_df(
        true_effect_segment="Enterprise",
        conv_a=0.12, conv_b=0.12, null_conv=0.12,
        n_per_cell=1000, seed=42
    )
    res_df = segment_analysis(df)
    null_segs = res_df[res_df["segment"] != "Enterprise"]
    assert all(~null_segs["significant_corrected"])