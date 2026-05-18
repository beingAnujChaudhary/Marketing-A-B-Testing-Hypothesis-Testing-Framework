#!/usr/bin/env python3
"""Generate realistic synthetic A/B test data for the SME cashback experiment."""
import sys
import logging
import numpy as np
import pandas as pd
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import get_config

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def generate_ab_data(config: dict) -> pd.DataFrame:
    """Generate synthetic A/B test data with realistic imperfections."""
    np.random.seed(config["data"]["seed"])

    n_total = config["data"]["n_samples"]
    split = config["experiment"]["variant_split"]
    n_a = int(n_total * split[0])
    n_b = n_total - n_a

    baseline = config["statistics"]["baseline_conversion"]
    min_lift = config["statistics"]["minimum_detectable_lift"]

    conv_a = baseline
    conv_b = baseline * (1 + min_lift * 0.8)

    def generate_variant(variant: str, n: int, conv_rate: float) -> pd.DataFrame:
        segments = config["data"]["segments"]
        segment_weights = [0.5, 0.35, 0.15]

        return pd.DataFrame({
            "user_id": [f"{variant}_{i}" for i in range(n)],
            "variant": variant,
            "converted": np.random.binomial(1, conv_rate, n),
            "revenue": np.where(
                np.random.binomial(1, 1 - config["data"]["missing_revenue_rate"], n),
                np.random.lognormal(
                    config["data"]["revenue_lognormal_mean"],
                    config["data"]["revenue_lognormal_sigma"],
                    n,
                ),
                np.nan,
            ),
            "unsubscribed": np.random.binomial(
                1,
                config["data"]["guardrail_unsubscribe_rate"]
                * (1.2 if variant == "B" else 1.0),
                n,
            ),
            "segment": np.random.choice(segments, n, p=segment_weights),
            "timestamp": pd.date_range(start="2026-01-01", periods=n, freq="h")
            + pd.to_timedelta(np.random.randint(0, 24 * 7, n), unit="h"),
        })

    df_a = generate_variant("A", n_a, conv_a)
    df_b = generate_variant("B", n_b, conv_b)
    df = (
        pd.concat([df_a, df_b], ignore_index=True)
        .sample(frac=1, random_state=42)
        .reset_index(drop=True)
    )

    logger.info("✅ Generated %d rows: %d control (A), %d treatment (B)", len(df), n_a, n_b)
    return df


def main() -> None:
    config = get_config()
    df = generate_ab_data(config)

    Path("data/raw").mkdir(parents=True, exist_ok=True)
    Path("data/processed").mkdir(parents=True, exist_ok=True)

    if config["output"]["save_raw"]:
        df.to_csv("data/raw/synthetic_ab_data.csv", index=False)
        logger.info("💾 Saved raw data to data/raw/synthetic_ab_data.csv")

    if config["output"]["save_processed"]:
        df_clean = df.dropna(subset=["user_id", "variant", "converted"])
        df_clean.to_csv("data/processed/clean_ab_data.csv", index=False)
        logger.info("💾 Saved processed data to data/processed/clean_ab_data.csv")

    print(f"\n📊 Data Preview:\n{df.head()}")
    print(f"\n📈 Conversion Rates:\n{df.groupby('variant')['converted'].mean()}")


if __name__ == "__main__":
    main()