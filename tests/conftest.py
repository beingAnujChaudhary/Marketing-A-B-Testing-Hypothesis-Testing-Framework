"""Shared pytest fixtures and configuration.

conftest.py is automatically loaded by pytest before any tests run.
Fixtures defined here are available in every test file without importing them.
"""
import logging
import pytest
import numpy as np
import pandas as pd

from src.config import load_config, reset_config


@pytest.fixture(autouse=True)
def suppress_info_logs():
    """Suppress INFO-level log output during tests."""
    logging.basicConfig(level=logging.WARNING)


@pytest.fixture
def config():
    """Provide a freshly loaded config for each test."""
    reset_config()
    return load_config("configs/experiment_config.yaml")


def make_df(
    conv_a: float,
    conv_b: float,
    n: int = 1000,
    seed: int = 42
) -> pd.DataFrame:
    """Create a synthetic A/B DataFrame for use in tests."""
    np.random.seed(seed)

    def make_variant(variant: str, conv_rate: float) -> pd.DataFrame:
        return pd.DataFrame({
            "user_id": [f"{variant}_{i}" for i in range(n)],
            "variant": variant,
            "converted": np.random.binomial(1, conv_rate, n),
            "revenue": np.random.exponential(50, n),
            "unsubscribed": np.random.binomial(1, 0.02, n),
            "segment": "SME",
            "timestamp": pd.date_range(
                "2026-01-01",
                periods=n,
                freq="h"   # changed H → h
            ),
        })

    return pd.concat(
        [make_variant("A", conv_a), make_variant("B", conv_b)],
        ignore_index=True,
    )