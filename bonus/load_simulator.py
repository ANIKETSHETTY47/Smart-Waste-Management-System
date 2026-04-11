"""
load_simulator.py — Bonus: Load / Stress Test Script
Rapidly sends a burst of sensor readings through the fog node
to stress-test the AWS pipeline (SQS → Lambda → DynamoDB).
"""

import sys
import os
import random
import time
from datetime import datetime, timezone

# Allow imports from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import (
    NUM_BINS,
    BIN_ID_PREFIX,
    FILL_LEVEL_RANGE,
    TEMPERATURE_RANGE,
    METHANE_RANGE,
    WEIGHT_RANGE,
)
from fog.fog_node import process_sensor_data


# ─── Configuration ───────────────────────────────────────────────────
TOTAL_MESSAGES = 50          # total messages to send
DELAY_BETWEEN = 0.1          # seconds between messages (fast)


def generate_random_reading():
    """Generate a random sensor reading for a random bin."""
    bin_id = f"{BIN_ID_PREFIX}_{random.randint(1, NUM_BINS)}"
    return {
        "bin_id": bin_id,
        "fill_level": round(random.uniform(*FILL_LEVEL_RANGE), 1),
        "temperature": round(random.uniform(*TEMPERATURE_RANGE), 1),
        "methane_level": round(random.uniform(*METHANE_RANGE), 1),
        "weight": round(random.uniform(*WEIGHT_RANGE), 2),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def run_load_test():
    """Send TOTAL_MESSAGES rapidly through the fog node."""
    print(f"[LoadTest] Sending {TOTAL_MESSAGES} messages "
          f"(delay={DELAY_BETWEEN}s)")
    print("-" * 50)

    start = time.time()
    success = 0

    for i in range(1, TOTAL_MESSAGES + 1):
        reading = generate_random_reading()
        try:
            process_sensor_data(reading)
            success += 1
            print(f"  [{i}/{TOTAL_MESSAGES}] ✓ {reading['bin_id']}")
        except Exception as exc:
            print(f"  [{i}/{TOTAL_MESSAGES}] ✗ {exc}")
        time.sleep(DELAY_BETWEEN)

    elapsed = time.time() - start
    print("-" * 50)
    print(f"[LoadTest] Done — {success}/{TOTAL_MESSAGES} sent "
          f"in {elapsed:.1f}s ({success/elapsed:.1f} msg/s)")


if __name__ == "__main__":
    run_load_test()
