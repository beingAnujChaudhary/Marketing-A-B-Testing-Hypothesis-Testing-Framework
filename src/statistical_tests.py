"""Core statistical testing functions for A/B analysis.

Design decisions:
- Two-sided z-test: guards against both positive and negative effects.
- [A, B] ordering: positive lift always means B outperforms A.
- Unpooled SE for CIs: standard practice; pooled SE is only used under H0.
- Holm-Bonferroni: more powerful than Bonferroni while controlling FWER.
"""
import logging
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.proportion import proportions_ztest, proportion_effectsize
from statsmodels.stats.multitest import multipletests
from typing import Dict, Any

from src.config import get_config

logger = logging.getLogger(__name__)


def z_test_proportions(
    df: pd.DataFrame,
    variant_col: str = "variant",
    target_col: str = "converted",
) -> Dict[str, Any]:
    """Run a two-sided Z-test for conversion lift."""
    config = get_config()
    alpha = config["statistics"]["alpha"]

    counts = df.groupby(variant_col)[target_col].sum()
    nobs = df.groupby(variant_col)[target_col].count()

    count_arr = [counts["A"], counts["B"]]
    nobs_arr = [nobs["A"], nobs["B"]]

    stat, pval = proportions_ztest(
        count=count_arr,
        nobs=nobs_arr,
        alternative="two-sided",
    )

    rate_a = counts["A"] / nobs["A"]
    rate_b = counts["B"] / nobs["B"]
    lift = (rate_b - rate_a) / rate_a * 100

    se_diff = np.sqrt(
        rate_a * (1 - rate_a) / nobs["A"]
        + rate_b * (1 - rate_b) / nobs["B"]
    )
    z_crit = stats.norm.ppf(1 - alpha / 2)
    margin = z_crit * se_diff

    ci_low = ((rate_b - rate_a) - margin) / rate_a * 100
    ci_high = ((rate_b - rate_a) + margin) / rate_a * 100

    return {
        "z_stat": float(stat),
        "p_value": float(pval),
        "lift_percent": float(lift),
        "ci_95": [round(ci_low, 2), round(ci_high, 2)],
        "ci_width": round(ci_high - ci_low, 2),
        "effect_size_cohens_h": round(float(proportion_effectsize(rate_a, rate_b)), 3),
        "conversion_rates": {
            "A": round(float(rate_a), 4),
            "B": round(float(rate_b), 4),
        },
        "significant": bool(pval < alpha),
    }


def segment_analysis(
    df: pd.DataFrame,
    segment_col: str = "segment",
    target_col: str = "converted",
) -> pd.DataFrame:
    """Run per-segment Z-tests with Holm-Bonferroni multiple testing correction."""
    segments = df[segment_col].dropna().unique()
    results = []

    for seg in segments:
        seg_df = df[df[segment_col] == seg]
        if len(seg_df) < 100:
            logger.warning("Skipping segment '%s': fewer than 100 observations", seg)
            continue
        res = z_test_proportions(seg_df, target_col=target_col)
        results.append({"segment": seg, **res})

    if not results:
        logger.warning("No segments had sufficient data for analysis")
        return pd.DataFrame()

    res_df = pd.DataFrame(results)

    if len(res_df) > 1:
        reject, p_corrected, _, _ = multipletests(res_df["p_value"], method="holm")
        res_df["p_value_corrected"] = p_corrected
        res_df["significant_corrected"] = reject
    else:
        res_df["p_value_corrected"] = res_df["p_value"]
        res_df["significant_corrected"] = res_df["significant"]

    return res_df