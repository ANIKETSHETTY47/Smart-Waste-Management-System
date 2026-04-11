"""
config.py — Shared configuration for Smart Waste Management System.
All thresholds, AWS resource names, and simulation parameters live here.
"""

# ─── AWS Configuration ───────────────────────────────────────────────
AWS_REGION = "us-east-1"
SQS_QUEUE_NAME = "wasteSensorQueue"
DYNAMODB_TABLE = "WasteSensorData"

# ─── Edge-Logic Thresholds ───────────────────────────────────────────
FILL_THRESHOLD = 80        # percent  → NEEDS_COLLECTION
METHANE_THRESHOLD = 300    # ppm      → GAS_ALERT
TEMP_THRESHOLD = 60        # °C       → FIRE_RISK

# ─── Sensor Simulation ──────────────────────────────────────────────
NUM_BINS = 5                       # bin_1 … bin_5
DISPATCH_INTERVAL_SECONDS = 5      # how often each round of readings is sent
BIN_ID_PREFIX = "bin"              # produces bin_1, bin_2, …

# ─── Sensor Value Ranges (for random generation) ────────────────────
FILL_LEVEL_RANGE = (0, 100)        # percent
TEMPERATURE_RANGE = (20, 80)       # °C
METHANE_RANGE = (50, 500)          # ppm
WEIGHT_RANGE = (0.5, 50.0)        # kg
