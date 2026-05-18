"""Reporting and visualisation utilities for A/B test results."""
import json
import logging
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from typing import Dict, Any, Optional

from src.config import get_config

logger = logging.getLogger(__name__)


def save_results_json(
    stats_result: Dict[str, Any],
    recommendation: Dict[str, str],
    output_path: str = "output/results/summary.json",
) -> None:
    """Save statistical results and recommendation to a JSON file."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    report = {
        "experiment": get_config()["experiment"]["name"],
        "statistics": stats_result,
        "recommendation": recommendation,
        "metadata": {"generated_by": "Marketing A/B Testing Framework v2.0"}
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    logger.info("💾 Results saved to %s", output_path)


def plot_conversion_rates(
    df: pd.DataFrame,
    variant_col: str = "variant",
    target_col: str = "converted",
    output_path: Optional[str] = "output/results/conversion_plot.html",
) -> go.Figure:
    """Create an interactive Plotly bar chart of conversion rates by variant."""
    summary = df.groupby(variant_col)[target_col].agg(
        rate="mean", n="count", std="std"
    ).reset_index()
    summary["se"] = summary["std"] / np.sqrt(summary["n"])

    fig = px.bar(
        summary, x=variant_col, y="rate", error_y="se",
        title="Conversion Rate by Variant (95% CI)",
        labels={"rate": "Conversion Rate", variant_col: "Variant"},
        color=variant_col,
        color_discrete_map={"A": "#1f77b4", "B": "#ff7f0e"},
        height=400
    )

    baseline = get_config()["statistics"]["baseline_conversion"]
    fig.add_hline(
        y=baseline, line_dash="dash", line_color="gray",
        annotation_text=f"Baseline: {baseline:.1%}",
        annotation_position="top right"
    )
    fig.update_layout(yaxis_tickformat=".1%", hovermode="x unified", showlegend=False)

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        fig.write_html(output_path)
        logger.info("📊 Chart saved to %s", output_path)

    return fig


def plot_cumulative_lift(
    df: pd.DataFrame,
    variant_col: str = "variant",
    target_col: str = "converted",
    time_col: str = "timestamp",
    output_path: Optional[str] = "output/results/cumulative_lift.html",
) -> go.Figure:
    """Create a cumulative lift chart to monitor experiment progress."""
    df_sorted = df.sort_values(time_col).copy()
    df_sorted["cumulative"] = df_sorted.groupby(variant_col)[target_col].cumsum()
    df_sorted["cumulative_n"] = df_sorted.groupby(variant_col)[target_col].cumcount() + 1
    df_sorted["cumulative_rate"] = df_sorted["cumulative"] / df_sorted["cumulative_n"]

    pivot = df_sorted.pivot_table(
        index=time_col, columns=variant_col, values="cumulative_rate", aggfunc="last"
    ).ffill()
    pivot["lift"] = (pivot["B"] - pivot["A"]) / pivot["A"] * 100

    fig = px.line(
        pivot.reset_index(), x=time_col, y="lift",
        title="Cumulative Lift Over Time (%)",
        labels={"lift": "Lift vs Control (%)", time_col: "Time"},
        height=400
    )
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    min_lift = get_config()["statistics"]["minimum_business_lift"] * 100
    fig.add_hline(
        y=min_lift, line_dash="dot", line_color="green",
        annotation_text=f"Min Business Lift: {min_lift:.1f}%",
        annotation_position="bottom right"
    )

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        fig.write_html(output_path)
        logger.info("📈 Cumulative lift chart saved to %s", output_path)

    return fig