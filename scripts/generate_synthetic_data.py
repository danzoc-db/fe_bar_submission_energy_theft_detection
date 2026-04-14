"""Generate synthetic smart meter data for the energy theft detection demo.

Produces:
- 100,000 account records
- 200,000 meters (~2 per account)
- 90 days of half-hourly reads per meter
- Pre-computed anomaly scores
- Investigation cases
- Property reference data
- Model performance log

Distribution:
- 95% normal accounts (seasonal + noise)
- 3% tampered accounts (step-down signature)
- 2% edge cases (legitimate drops near boundary)

Usage:
    python scripts/generate_synthetic_data.py

Requires: databricks-sdk, pyspark (run on Databricks cluster or via
databricks-connect).
"""

import random
import math
from datetime import datetime, timedelta
from typing import Any

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

NUM_ACCOUNTS = 100_000
METERS_PER_ACCOUNT = 2
DAYS_OF_READS = 90
READS_PER_DAY = 48  # half-hourly

TAMPERED_PCT = 0.03
EDGE_CASE_PCT = 0.02
NORMAL_PCT = 1.0 - TAMPERED_PCT - EDGE_CASE_PCT

CATALOG = "dz_demos"
SCHEMA = "energy_theft_protection"

UK_REGIONS = [
    "London", "South East", "South West", "East of England",
    "West Midlands", "East Midlands", "North West", "North East",
    "Yorkshire and the Humber", "Wales", "Scotland",
]

PROPERTY_TYPES = ["terraced", "semi-detached", "detached", "flat", "bungalow"]
COUNCIL_TAX_BANDS = ["A", "B", "C", "D", "E", "F", "G", "H"]
EPC_RATINGS = ["A", "B", "C", "D", "E", "F", "G"]
FUEL_TYPES = ["electricity", "gas"]

# Postcode sector prefixes by region
POSTCODE_PREFIXES = {
    "London": ["E1", "EC1", "N1", "NW1", "SE1", "SW1", "W1", "WC1"],
    "South East": ["BN1", "GU1", "ME1", "OX1", "RG1", "SL1", "TN1"],
    "South West": ["BA1", "BS1", "EX1", "GL1", "PL1", "TA1"],
    "East of England": ["CB1", "CM1", "CO1", "IP1", "NR1", "SG1"],
    "West Midlands": ["B1", "CV1", "DY1", "WS1", "WV1"],
    "East Midlands": ["DE1", "LE1", "LN1", "NG1", "NN1"],
    "North West": ["L1", "M1", "OL1", "PR1", "WA1", "WN1"],
    "North East": ["DH1", "DL1", "NE1", "SR1", "TS1"],
    "Yorkshire and the Humber": ["BD1", "DN1", "HD1", "HU1", "LS1", "S1", "YO1"],
    "Wales": ["CF1", "LD1", "LL1", "NP1", "SA1", "SY1"],
    "Scotland": ["AB1", "DD1", "EH1", "FK1", "G1", "KY1", "PA1"],
}


def generate_postcode(region: str) -> str:
    prefix = random.choice(POSTCODE_PREFIXES.get(region, ["XX1"]))
    sector = random.randint(1, 9)
    return f"{prefix} {sector}"


def generate_normal_consumption(hour: int, day_of_year: int, base_kwh: float) -> float:
    """Generate realistic half-hourly consumption with seasonal and daily patterns."""
    seasonal = 1.0 + 0.3 * math.cos(2 * math.pi * (day_of_year - 15) / 365)
    if 7 <= hour <= 9 or 17 <= hour <= 21:
        daily = 1.4
    elif 0 <= hour <= 5:
        daily = 0.4
    else:
        daily = 0.8
    noise = random.gauss(0, 0.1 * base_kwh)
    return max(0.01, base_kwh * seasonal * daily + noise)


def main():
    print(f"Generating synthetic data for {CATALOG}.{SCHEMA}")
    print(f"Accounts: {NUM_ACCOUNTS:,}")
    print(f"Meters: {NUM_ACCOUNTS * METERS_PER_ACCOUNT:,}")
    print(f"Reads: ~{NUM_ACCOUNTS * METERS_PER_ACCOUNT * DAYS_OF_READS * READS_PER_DAY:,}")
    print()
    print("This script is a template. Run on a Databricks cluster or via")
    print("databricks-connect for PySpark execution.")
    print()
    print("Distribution:")
    print(f"  Normal:   {NORMAL_PCT*100:.0f}% ({int(NUM_ACCOUNTS * NORMAL_PCT):,} accounts)")
    print(f"  Tampered: {TAMPERED_PCT*100:.0f}% ({int(NUM_ACCOUNTS * TAMPERED_PCT):,} accounts)")
    print(f"  Edge:     {EDGE_CASE_PCT*100:.0f}% ({int(NUM_ACCOUNTS * EDGE_CASE_PCT):,} accounts)")


if __name__ == "__main__":
    main()
