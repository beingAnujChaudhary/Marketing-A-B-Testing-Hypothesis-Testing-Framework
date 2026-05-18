import sys
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from src.config import get_config
from scripts.generate_ab_data import generate_ab_data
from src.data_validation import run_validation


# Load config
config = get_config()

# Generate synthetic data
df = generate_ab_data(config)

print(f"✅ Generated {len(df)} rows")

print("\n📈 Conversion Rates:")
print(df.groupby("variant")["converted"].mean())

# Run validation
report = run_validation(df, config)

print(f"\n✅ Validation passed: {report['passed']}")

if report["warnings"]:
    print("\n⚠️ Warnings:")
    for warning in report["warnings"]:
        print("-", warning)
else:
    print("\n🎉 No validation warnings!")