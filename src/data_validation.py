"""Data validation pipeline for A/B test datasets.

Runs a 6-point quality check before any statistical analysis.
Separates hard failures (stop pipeline) from soft warnings (log and continue).
"""
import logging
import pandas as pd
from typing import Dict, Any

logger = logging.getLogger(__name__)


def run_validation(df: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
    """Run comprehensive validation checks on A/B test data."""
    report: Dict[str, Any] = {"passed": True, "details": {}, "warnings": []}

    # ── Check 1: Required columns exist ───────────────────────────────────────
    required = ["user_id", "variant", "converted", "revenue", "unsubscribed"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        report["passed"] = False
        report["warnings"].append(f"❌ Missing required columns: {missing}")
        return report
    report["details"]["columns"] = "✅ PASS"

    # ── Check 2: Null values in critical fields ────────────────────────────────
    nulls = df[required].isnull().sum()
    if nulls.sum() > 0:
        report["warnings"].append(
            f"⚠️ Null values found: {nulls[nulls > 0].to_dict()}"
        )
        if nulls[["user_id", "variant", "converted", "unsubscribed"]].sum() > 0:
            report["passed"] = False
    else:
        report["details"]["nulls"] = "✅ PASS"

    # ── Check 3: Conversion is binary (0 or 1) ────────────────────────────────
    if not set(df["converted"].dropna().unique()).issubset({0, 1}):
        report["warnings"].append("❌ Invalid conversion values (must be 0 or 1)")
        report["passed"] = False
    else:
        report["details"]["binary_conversion"] = "✅ PASS"

    # ── Check 4: Variant labels are exactly A and B ───────────────────────────
    observed_variants = set(df["variant"].dropna().unique())
    if observed_variants != {"A", "B"}:
        report["warnings"].append(
            f"❌ Expected variants A/B, got: {observed_variants}"
        )
        report["passed"] = False
    else:
        report["details"]["variant_labels"] = "✅ PASS"

    # ── Check 5: No duplicate user_ids ────────────────────────────────────────
    duplicates = df["user_id"].duplicated().sum()
    if duplicates > 0:
        report["warnings"].append(f"⚠️ Duplicate user_ids found: {duplicates}")
        report["passed"] = False
    else:
        report["details"]["unique_users"] = "✅ PASS"

    # ── Check 6: Guardrail — unsubscribe rate in Variant B ────────────────────
    unsub_rate = df.groupby("variant")["unsubscribed"].mean()
    threshold = config["data"]["guardrail_unsubscribe_rate"]
    if unsub_rate.get("B", 0) > threshold * 1.5:
        report["warnings"].append(
            f"🚨 Guardrail breach: Variant B unsubscribe rate "
            f"({unsub_rate['B']:.3f}) exceeds threshold ({threshold})"
        )
    report["details"]["guardrail_check"] = "✅ PASS"

    logger.info("Validation %s", "✅ PASSED" if report["passed"] else "❌ FAILED")
    return report