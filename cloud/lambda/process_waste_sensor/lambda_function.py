"""
processWasteSensorData — AWS Lambda (Python 3.12)
Triggered by SQS. Parses each message and writes the sensor
reading into the DynamoDB table 'WasteSensorData'.
"""

import json
import os
import boto3
from decimal import Decimal

# ─── DynamoDB resource ───────────────────────────────────────────────
dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
table = dynamodb.Table(os.environ.get("TABLE_NAME", "WasteSensorData"))


def lambda_handler(event, context):
    """
    Entry point for SQS-triggered Lambda.
    Each SQS record body is a JSON string representing one sensor reading.
    """
    records_processed = 0

    for record in event.get("Records", []):
        try:
            # Parse the SQS message body
            body = json.loads(record["body"], parse_float=Decimal)
            print(f"[Lambda] Processing: {body}")

            # Write to DynamoDB
            table.put_item(Item={
                "bin_id":        str(body["bin_id"]),
                "timestamp":     str(body["timestamp"]),
                "fill_level":    Decimal(str(body["fill_level"])),
                "temperature":   Decimal(str(body["temperature"])),
                "methane_level": Decimal(str(body["methane_level"])),
                "weight":        Decimal(str(body["weight"])),
                "status":        str(body["status"]),
            })
            records_processed += 1
            print(f"[Lambda] ✓ Saved {body['bin_id']} @ {body['timestamp']}")

        except Exception as exc:
            print(f"[Lambda] ✗ Error processing record: {exc}")

    return {
        "statusCode": 200,
        "body": json.dumps({"records_processed": records_processed}),
    }
