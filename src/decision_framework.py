"""Business decision logic: translates statistical results into recommendations.

Decision hierarchy (guardrails take priority over statistics):
    1. Guardrail breach     → STOP
    2. Significant + lift   → SCALE VARIANT B
    3. Significant, low lift → ITERATE
    4. Significant negative → DO NOT SCALE
    5. Underpowered         → INCREASE SAMPLE SIZE
    6. Wide CI              → COLLECT MORE DATA
    7. Narrow CI, no effect → NO CONCLUSION
"""
import logging
from typing import Dict, Any

from src.config import get_config

logger = logging.getLogger(__name__)


def generate_recommendation(
    stats_result: Dict[str, Any],
    guardrail_breached: bool = False,
    achieved_power: float = 0.0,
) -> Dict[str, str]:
    """Generate a business recommendation from statistical results."""
    config = get_config()
    min_lift_pct = config["statistics"]["minimum_business_lift"] * 100
    alpha = config["statistics"]["alpha"]
    power_target = config["statistics"]["power_target"]

    p_val = stats_result["p_value"]
    lift = stats_result["lift_percent"]
    ci_low = stats_result["ci_95"][0]
    ci_width = stats_result.get("ci_width", 100)

    if guardrail_breached:
        return {
            "recommendation": "🛑 STOP (GUARDRAIL BREACH)",
            "confidence": "HIGH",
            "reasoning": (
                "Unsubscribe/complaint rate exceeded the safety threshold. "
                "Do not scale, even if the primary metric looks positive."
            ),
        }

    if p_val < alpha and lift > min_lift_pct and ci_low > 0:
        return {
            "recommendation": "✅ SCALE VARIANT B",
            "confidence": "HIGH",
            "reasoning": (
                "Statistically significant lift exceeding the business threshold "
                "with the entire CI above zero."
            ),
        }

    if p_val < alpha and lift > 0:
        return {
            "recommendation": "⚠️ ITERATE & RETEST",
            "confidence": "MEDIUM",
            "reasoning": (
                "Statistically significant but the lift is below the minimum "
                "business threshold. Consider improving the treatment."
            ),
        }

    if p_val < alpha and lift <= 0:
        return {
            "recommendation": "❌ DO NOT SCALE",
            "confidence": "HIGH",
            "reasoning": "Statistically significant negative impact detected.",
        }

    if p_val >= alpha and achieved_power < power_target:
        return {
            "recommendation": "📈 INCREASE SAMPLE SIZE",
            "confidence": "MEDIUM",
            "reasoning": (
                f"Underpowered (achieved {achieved_power:.0%}). "
                "There is a material risk of a false negative. "
                "Run the experiment longer before concluding."
            ),
        }

    if ci_width > 50:
        return {
            "recommendation": "🔍 COLLECT MORE DATA",
            "confidence": "LOW",
            "reasoning": (
                "Not significant and the confidence interval is too wide "
                "for a reliable business decision."
            ),
        }

    return {
        "recommendation": "❌ NO CONCLUSION",
        "confidence": "LOW",
        "reasoning": (
            "No statistical significance and the CI is narrow, "
            "suggesting the true effect is likely negligible."
        ),
    }
    