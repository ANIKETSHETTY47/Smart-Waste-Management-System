"""
fog_node.py — Fog / Edge Layer
Receives sensor data, validates it, applies edge logic to classify
bin status, and forwards the enriched payload to AWS SQS.
"""

import sys
import os
import json

import boto3

# Allow imports from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import (
    AWS_REGION,
    SQS_QUEUE_NAME,
    FILL_THRESHOLD,
    METHANE_THRESHOLD,
    TEMP_THRESHOLD,
)

# ─── SQS client (initialised once) ──────────────────────────────────
sqs = boto3.client("sqs", region_name=AWS_REGION)


def _get_queue_url() -> str:
    """Retrieve the SQS queue URL by name (cached after first call)."""
    if not hasattr(_get_queue_url, "_url"):
        resp = sqs.get_queue_url(QueueName=SQS_QUEUE_NAME)
        _get_queue_url._url = resp["QueueUrl"]
    return _get_queue_url._url


# ─── Edge Logic ──────────────────────────────────────────────────────

def classify_status(fill_level: float,
                    methane_level: float,
                    temperature: float) -> str:
    """
    Apply fog-layer edge logic to determine bin status.
    Priority order: fill → gas → fire → normal.
    """
    if fill_level > FILL_THRESHOLD:
        return "NEEDS_COLLECTION"
    elif methane_level > METHANE_THRESHOLD:
        return "GAS_ALERT"
    elif temperature > TEMP_THRESHOLD:
        return "FIRE_RISK"
    else:
        return "NORMAL"


# ─── Validation ──────────────────────────────────────────────────────

REQUIRED_KEYS = {"bin_id", "fill_level", "temperature",
                 "methane_level", "weight", "timestamp"}


def validate(data: dict) -> bool:
    """Return True if all required keys are present."""
    missing = REQUIRED_KEYS - data.keys()
    if missing:
        print(f"[Fog] ✗ Validation failed — missing keys: {missing}")
        return False
    return True


# ─── Main Processing ─────────────────────────────────────────────────

def process_sensor_data(data: dict) -> None:
    """
    1. Validate incoming sensor data.
    2. Apply edge logic to determine status.
    3. Send enriched payload to SQS.
    """
    # Step 1 — Validate
    if not validate(data):
        return

    # Step 2 — Apply edge logic
    status = classify_status(
        data["fill_level"],
        data["methane_level"],
        data["temperature"],
    )
    data["status"] = status
    print(f"[Fog]  {data['bin_id']} → status={status}")

    # Step 3 — Send to SQS
    try:
        queue_url = _get_queue_url()
        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(data),
        )
        print(f"[Fog]  ✓ Sent to SQS")
    except Exception as exc:
        print(f"[Fog]  ✗ SQS send failed: {exc}")
