"""
getWasteData — AWS Lambda (Python 3.12)
Invoked via API Gateway (GET /data).
Scans DynamoDB for all sensor readings, returns the latest
reading per bin as a JSON array.
"""

import json
import os
from decimal import Decimal
from collections import defaultdict

import boto3


# ─── DynamoDB resource ───────────────────────────────────────────────
dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
table = dynamodb.Table(os.environ.get("TABLE_NAME", "WasteSensorData"))


class DecimalEncoder(json.JSONEncoder):
    """Convert Decimal values to float for JSON serialisation."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def lambda_handler(event, context):
    """
    Scan the table, group by bin_id, and return only the latest
    reading (by timestamp) for each bin.
    """
    try:
        # Full scan (acceptable for small academic dataset)
        response = table.scan()
        items = response.get("Items", [])

        # Handle pagination if needed
        while "LastEvaluatedKey" in response:
            response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            items.extend(response.get("Items", []))

        # Group by bin_id, keep the latest timestamp
        latest = {}
        for item in items:
            bid = item["bin_id"]
            if bid not in latest or item["timestamp"] > latest[bid]["timestamp"]:
                latest[bid] = item

        result = sorted(latest.values(), key=lambda x: x["bin_id"])

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET,OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            },
            "body": json.dumps(result, cls=DecimalEncoder),
        }

    except Exception as exc:
        print(f"[Lambda] ✗ Error: {exc}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"error": str(exc)}),
        }
