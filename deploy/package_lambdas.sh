#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════
# package_lambdas.sh — Creates deployment ZIP packages for Lambda functions.
# Run from the project root directory.
# ═══════════════════════════════════════════════════════════════════════

set -e

echo "Packaging Lambda functions…"

# ─── processWasteSensorData ──────────────────────────────────────────
echo "[1/2] Packaging processWasteSensorData…"
cd cloud/lambda/process_waste_sensor
zip -j process_waste_sensor.zip lambda_function.py
echo "      ✓ process_waste_sensor.zip created"
cd ../../..

# ─── getWasteData ────────────────────────────────────────────────────
echo "[2/2] Packaging getWasteData…"
cd cloud/lambda/get_waste_data
zip -j get_waste_data.zip lambda_function.py
echo "      ✓ get_waste_data.zip created"
cd ../../..

echo ""
echo "All Lambda packages ready!"
echo "  cloud/lambda/process_waste_sensor/process_waste_sensor.zip"
echo "  cloud/lambda/get_waste_data/get_waste_data.zip"
