#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════
# cleanup.sh — Tear down all AWS resources created by setup_aws.sh
# Run from the project root directory.
# ═══════════════════════════════════════════════════════════════════════

set -e

REGION="us-east-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET_NAME="waste-dashboard-${ACCOUNT_ID}"

echo "═══════════════════════════════════════════════════════════"
echo " CLEANING UP AWS RESOURCES"
echo "═══════════════════════════════════════════════════════════"

# ─── 1. Delete S3 bucket ─────────────────────────────────────────────
echo "[1/7] Deleting S3 bucket…"
aws s3 rb s3://$BUCKET_NAME --force --region $REGION 2>/dev/null || true

# ─── 2. Delete API Gateway ───────────────────────────────────────────
echo "[2/7] Deleting API Gateway…"
API_ID=$(aws apigateway get-rest-apis --region $REGION \
    --query "items[?name=='WasteManagementAPI'].id" --output text)
if [ -n "$API_ID" ]; then
    aws apigateway delete-rest-api --rest-api-id $API_ID --region $REGION
    echo "      ✓ Deleted API $API_ID"
fi

# ─── 3. Delete Lambda event source mapping ───────────────────────────
echo "[3/7] Removing SQS trigger…"
MAPPING_UUID=$(aws lambda list-event-source-mappings \
    --function-name processWasteSensorData \
    --region $REGION \
    --query 'EventSourceMappings[0].UUID' --output text 2>/dev/null)
if [ -n "$MAPPING_UUID" ] && [ "$MAPPING_UUID" != "None" ]; then
    aws lambda delete-event-source-mapping --uuid $MAPPING_UUID --region $REGION
fi

# ─── 4. Delete Lambda functions ──────────────────────────────────────
echo "[4/7] Deleting Lambda functions…"
aws lambda delete-function --function-name processWasteSensorData --region $REGION 2>/dev/null || true
aws lambda delete-function --function-name getWasteData --region $REGION 2>/dev/null || true

# ─── 5. Delete DynamoDB table ────────────────────────────────────────
echo "[5/7] Deleting DynamoDB table…"
aws dynamodb delete-table --table-name WasteSensorData --region $REGION 2>/dev/null || true

# ─── 6. Delete SQS queue ─────────────────────────────────────────────
echo "[6/7] Deleting SQS queue…"
SQS_URL=$(aws sqs get-queue-url --queue-name wasteSensorQueue --region $REGION \
    --query 'QueueUrl' --output text 2>/dev/null)
if [ -n "$SQS_URL" ]; then
    aws sqs delete-queue --queue-url $SQS_URL --region $REGION
fi

# ─── 7. Delete IAM role ──────────────────────────────────────────────
echo "[7/7] Deleting IAM role…"
aws iam detach-role-policy --role-name WasteLambdaRole \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole 2>/dev/null || true
aws iam detach-role-policy --role-name WasteLambdaRole \
    --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess 2>/dev/null || true
aws iam detach-role-policy --role-name WasteLambdaRole \
    --policy-arn arn:aws:iam::aws:policy/AmazonSQSFullAccess 2>/dev/null || true
aws iam delete-role --role-name WasteLambdaRole 2>/dev/null || true

# ─── CloudWatch logs ─────────────────────────────────────────────────
aws logs delete-log-group --log-group-name /aws/lambda/processWasteSensorData --region $REGION 2>/dev/null || true
aws logs delete-log-group --log-group-name /aws/lambda/getWasteData --region $REGION 2>/dev/null || true

echo ""
echo "═══════════════════════════════════════════════════════════"
echo " CLEANUP COMPLETE"
echo "═══════════════════════════════════════════════════════════"
