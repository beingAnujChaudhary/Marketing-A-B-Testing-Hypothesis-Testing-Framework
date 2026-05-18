import sys
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from src.config import get_config
from scripts.generate_ab_data import generate_ab_data
from src.statistical_tests import z_test_proportions, segment_analysis
from src.decision_framework import generate_recommendation


# Load config
config = get_config()

# Generate synthetic data
df = generate_ab_data(config)

# Run statistical test
result = z_test_proportions(df)

print("📊 Statistical Results:")
print(f"📈 Lift: {result['lift_percent']:.2f}%")
print(f"🔍 P-value: {result['p_value']:.4f}")
print(f"🎯 95% CI: [{result['ci_95'][0]}, {result['ci_95'][1]}]%")
print(f"📏 Effect Size: {result['effect_size_cohens_h']}")
print(f"✅ Significant: {result['significant']}")

# Business recommendation
recommendation = generate_recommendation(
    result,
    achieved_power=0.85
)

print(f"\n💡 Recommendation: {recommendation['recommendation']}")
print(f"🔐 Confidence: {recommendation['confidence']}")
print(f"📝 Reasoning: {recommendation['reasoning']}")