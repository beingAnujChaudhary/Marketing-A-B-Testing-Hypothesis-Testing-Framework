"""Statistical power analysis for A/B test planning and post-hoc evaluation."""
import numpy as np
import logging
from statsmodels.stats.power import zt_ind_solve_power
from statsmodels.stats.proportion import proportion_effectsize

logger = logging.getLogger(__name__)


def calculate_required_sample_size(
    baseline_rate: float,
    min_detectable_lift: float,
    alpha: float = 0.05,
    power: float = 0.80,
) -> int:
    """Calculate the minimum sample size per variant to detect a given lift.

    Args:
        baseline_rate: Control group conversion rate (between 0 and 1).
        min_detectable_lift: Minimum relative lift to detect, e.g. 0.15 = 15%.
        alpha: Significance level. Default 0.05.
        power: Desired statistical power. Default 0.80.

    Returns:
        Required sample size per variant as an integer.
    """
    if not (0 < baseline_rate < 1):
        raise ValueError("baseline_rate must be strictly between 0 and 1")
    if min_detectable_lift <= 0:
        raise ValueError("min_detectable_lift must be positive")

    test_rate = min(baseline_rate * (1 + min_detectable_lift), 0.9999)
    effect_size = proportion_effectsize(baseline_rate, test_rate)

    n_per_group = zt_ind_solve_power(
        effect_size=effect_size,
        alpha=alpha,
        power=power,
        ratio=1.0,
        alternative="two-sided",
    )

    return int(np.ceil(n_per_group))


def calculate_achieved_power(
    baseline_rate: float,
    observed_lift: float,
    n_per_group: int,
    alpha: float = 0.05,
) -> float:
    """Calculate the achieved power given observed results.

    Args:
        baseline_rate: Control group conversion rate.
        observed_lift: Observed relative lift (e.g. 0.12 = 12%).
        n_per_group: Actual sample size per variant.
        alpha: Significance level used for the test.

    Returns:
        Achieved statistical power as a float between 0 and 1.
    """
    if n_per_group <= 0:
        raise ValueError("n_per_group must be positive")

    if observed_lift <= 0:
        return 0.0

    test_rate = min(baseline_rate * (1 + observed_lift), 0.9999)
    effect_size = proportion_effectsize(baseline_rate, test_rate)

    power = zt_ind_solve_power(
        effect_size=effect_size,
        nobs1=n_per_group,
        alpha=alpha,
        ratio=1.0,
        alternative="two-sided",
    )

    return float(power)