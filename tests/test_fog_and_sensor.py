"""
Tests for the fog node edge logic and sensor simulator.
Uses moto to mock AWS services so no real AWS calls are made.
"""

import sys
import os
import json
import pytest
import boto3
from moto import mock_aws
from decimal import Decimal

# allow imports from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import (
    FILL_THRESHOLD,
    METHANE_THRESHOLD,
    TEMP_THRESHOLD,
    SQS_QUEUE_NAME,
    AWS_REGION,
)
from fog.fog_node import classify_status, validate
from sensor.sensor_simulator import generate_sensor_reading


# ── Edge Logic Tests ───────────────────────────────────────────

class TestClassifyStatus:
    """Tests for the fog node classification rules."""

    def test_normal_status(self):
        status = classify_status(50.0, 100.0, 30.0)
        assert status == "NORMAL"

    def test_needs_collection_when_full(self):
        status = classify_status(85.0, 100.0, 30.0)
        assert status == "NEEDS_COLLECTION"

    def test_gas_alert_high_methane(self):
        status = classify_status(50.0, 400.0, 30.0)
        assert status == "GAS_ALERT"

    def test_fire_risk_high_temp(self):
        status = classify_status(50.0, 100.0, 70.0)
        assert status == "FIRE_RISK"

    def test_fill_level_takes_priority_over_gas(self):
        """fill_level > 80 should win even if methane is also high"""
        status = classify_status(90.0, 400.0, 30.0)
        assert status == "NEEDS_COLLECTION"

    def test_fill_level_takes_priority_over_fire(self):
        """fill_level > 80 should win even if temp is also high"""
        status = classify_status(90.0, 100.0, 70.0)
        assert status == "NEEDS_COLLECTION"

    def test_gas_takes_priority_over_fire(self):
        """methane alert should win over fire risk"""
        status = classify_status(50.0, 400.0, 70.0)
        assert status == "GAS_ALERT"

    def test_boundary_fill_level(self):
        """exactly at threshold should be NORMAL (not >)"""
        status = classify_status(FILL_THRESHOLD, 100.0, 30.0)
        assert status == "NORMAL"

    def test_boundary_methane(self):
        status = classify_status(50.0, METHANE_THRESHOLD, 30.0)
        assert status == "NORMAL"

    def test_boundary_temp(self):
        status = classify_status(50.0, 100.0, TEMP_THRESHOLD)
        assert status == "NORMAL"


# ── Validation Tests ───────────────────────────────────────────

class TestValidation:
    """Tests for the fog node data validation."""

    def test_valid_reading_passes(self):
        data = {
            "bin_id": "bin_1",
            "fill_level": 50.0,
            "temperature": 30.0,
            "methane_level": 100.0,
            "weight": 10.0,
            "timestamp": "2026-04-10T12:00:00+00:00",
        }
        assert validate(data) is True

    def test_missing_bin_id_fails(self):
        data = {
            "fill_level": 50.0,
            "temperature": 30.0,
            "methane_level": 100.0,
            "weight": 10.0,
            "timestamp": "2026-04-10T12:00:00+00:00",
        }
        assert validate(data) is False

    def test_missing_timestamp_fails(self):
        data = {
            "bin_id": "bin_1",
            "fill_level": 50.0,
            "temperature": 30.0,
            "methane_level": 100.0,
            "weight": 10.0,
        }
        assert validate(data) is False

    def test_empty_dict_fails(self):
        assert validate({}) is False


# ── Sensor Simulator Tests ─────────────────────────────────────

class TestSensorSimulator:
    """Tests for the sensor data generator."""

    def test_reading_has_all_fields(self):
        reading = generate_sensor_reading("bin_1")
        expected_keys = {"bin_id", "fill_level", "temperature",
                         "methane_level", "weight", "timestamp"}
        assert reading.keys() == expected_keys

    def test_reading_has_correct_bin_id(self):
        reading = generate_sensor_reading("bin_42")
        assert reading["bin_id"] == "bin_42"

    def test_fill_level_in_range(self):
        for _ in range(50):
            reading = generate_sensor_reading("bin_1")
            assert 0 <= reading["fill_level"] <= 100

    def test_temperature_in_range(self):
        for _ in range(50):
            reading = generate_sensor_reading("bin_1")
            assert 20 <= reading["temperature"] <= 80

    def test_methane_in_range(self):
        for _ in range(50):
            reading = generate_sensor_reading("bin_1")
            assert 50 <= reading["methane_level"] <= 500

    def test_weight_in_range(self):
        for _ in range(50):
            reading = generate_sensor_reading("bin_1")
            assert 0.5 <= reading["weight"] <= 50.0


# ── SQS Integration Test (mocked) ─────────────────────────────

class TestSQSIntegration:
    """Tests fog node SQS dispatch using moto mock."""

    @mock_aws
    def test_process_sensor_data_sends_to_sqs(self):
        # create a mock SQS queue
        sqs = boto3.client("sqs", region_name=AWS_REGION)
        sqs.create_queue(QueueName=SQS_QUEUE_NAME)

        # reimport fog_node so it picks up the mock
        import importlib
        import fog.fog_node as fog_module
        fog_module.sqs = boto3.client("sqs", region_name=AWS_REGION)
        if hasattr(fog_module._get_queue_url, "_url"):
            del fog_module._get_queue_url._url

        reading = {
            "bin_id": "bin_1",
            "fill_level": 90.0,
            "temperature": 30.0,
            "methane_level": 100.0,
            "weight": 10.0,
            "timestamp": "2026-04-10T12:00:00+00:00",
        }
        fog_module.process_sensor_data(reading)

        # check message arrived in queue
        queue_url = sqs.get_queue_url(QueueName=SQS_QUEUE_NAME)["QueueUrl"]
        msgs = sqs.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=1)
        assert "Messages" in msgs
        body = json.loads(msgs["Messages"][0]["Body"])
        assert body["bin_id"] == "bin_1"
        assert body["status"] == "NEEDS_COLLECTION"
