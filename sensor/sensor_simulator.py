"""
sensor_simulator.py — Sensor Layer
Simulates 5 waste bins generating random sensor readings every 5 seconds.
Each reading is forwarded to the Fog Node for processing.
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
    DISPATCH_INTERVAL_SECONDS,
    FILL_LEVEL_RANGE,
    TEMPERATURE_RANGE,
    METHANE_RANGE,
    WEIGHT_RANGE,
)
from fog.fog_node import process_sensor_data


def generate_sensor_reading(bin_id: str) -> dict:
    """
    Generate a single random sensor reading for one bin.
    Returns a dictionary with bin_id, fill_level, temperature,
    methane_level, weight, and timestamp.
    """
    return {
        "bin_id": bin_id,
        "fill_level": round(random.uniform(*FILL_LEVEL_RANGE), 1),
        "temperature": round(random.uniform(*TEMPERATURE_RANGE), 1),
        "methane_level": round(random.uniform(*METHANE_RANGE), 1),
        "weight": round(random.uniform(*WEIGHT_RANGE), 2),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def run_simulation():
    """
    Main loop: generates readings for all bins and sends each
    to the fog node. Repeats every DISPATCH_INTERVAL_SECONDS.
    """
    print(f"[Sensor] Starting simulation for {NUM_BINS} bins "
          f"(interval={DISPATCH_INTERVAL_SECONDS}s)")
    print("-" * 60)

    cycle = 0
    try:
        while True:
            cycle += 1
            print(f"\n[Sensor] ── Cycle {cycle} ──")
            for i in range(1, NUM_BINS + 1):
                bin_id = f"{BIN_ID_PREFIX}_{i}"
                reading = generate_sensor_reading(bin_id)
                print(f"[Sensor] Generated → {reading}")

                # Forward to Fog Node (direct function call)
                process_sensor_data(reading)

            print(f"[Sensor] Sleeping {DISPATCH_INTERVAL_SECONDS}s …")
            time.sleep(DISPATCH_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("\n[Sensor] Simulation stopped by user.")


if __name__ == "__main__":
    run_simulation()
