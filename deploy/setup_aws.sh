#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════
# setup_aws.sh — AWS CLI commands to deploy the Smart Waste Management
# System end-to-end.  Run from the project root directory.
#
# Prerequisites:
#   • AWS CLI v2 configured (aws configure)
#   • Lambda zips already built (run package_lambdas.sh first)
# ═══════════════════════════════════════════════════════════════════════

set -e   # stop on first error

REGION="us-east-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "═══════════════════════════════════════════════════════════"
echo " AWS Account: $ACCOUNT_ID   Region: $REGION"
echo "═══════════════════════════════════════════════════════════"

# ─── 1. SQS Queue ────────────────────────────────────────────────────
echo "[1/8] Creating SQS queue…"
SQS_URL=$(aws sqs create-queue \
    --queue-name wasteSensorQueue \
    --region $REGION \
    --query 'QueueUrl' --output text)
echo "      Queue URL: $SQS_URL"

SQS_ARN=$(aws sqs get-queue-attributes \
    --queue-url $SQS_URL \
    --attribute-names QueueArn \
    --query 'Attributes.QueueArn' --output text)
echo "      Queue ARN: $SQS_ARN"

# ─── 2. DynamoDB Table ───────────────────────────────────────────────
echo "[2/8] Creating DynamoDB table…"
aws dynamodb create-table \
    --table-name WasteSensorData \
    --attribute-definitions \
        AttributeName=bin_id,AttributeType=S \
        AttributeName=timestamp,AttributeType=S \
    --key-schema \
        AttributeName=bin_id,KeyType=HASH \
        AttributeName=timestamp,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST \
    --region $REGION \
    2>/dev/null || echo "      (table may already exist)"

echo "      Waiting for table to become ACTIVE…"
aws dynamodb wait table-exists --table-name WasteSensorData --region $REGION
echo "      ✓ Table ready"

# ─── 3. IAM Role for Lambda ──────────────────────────────────────────
echo "[3/8] Using IAM role…"
# In AWS Learner Lab, use the pre-existing LabRole.
# If deploying outside Learner Lab, create a custom role instead.
ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/LabRole"
echo "      ✓ Role ARN: $ROLE_ARN"

# ─── 4. Lambda — processWasteSensorData ──────────────────────────────
echo "[4/8] Deploying processWasteSensorData Lambda…"
aws lambda create-function \
    --function-name processWasteSensorData \
    --runtime python3.12 \
    --role $ROLE_ARN \
    --handler lambda_function.lambda_handler \
    --zip-file fileb://cloud/lambda/process_waste_sensor/process_waste_sensor.zip \
    --timeout 30 \
    --environment 'Variables={TABLE_NAME=WasteSensorData}' \
    --region $REGION \
    2>/dev/null || echo "      (function may already exist — updating code…)" && \
    aws lambda update-function-code \
        --function-name processWasteSensorData \
        --zip-file fileb://cloud/lambda/process_waste_sensor/process_waste_sensor.zip \
        --region $REGION 2>/dev/null

# Add SQS trigger
echo "      Adding SQS trigger…"
aws lambda create-event-source-mapping \
    --function-name processWasteSensorData \
    --event-source-arn $SQS_ARN \
    --batch-size 10 \
    --region $REGION \
    2>/dev/null || echo "      (trigger may already exist)"

# ─── 5. Lambda — getWasteData ────────────────────────────────────────
echo "[5/8] Deploying getWasteData Lambda…"
aws lambda create-function \
    --function-name getWasteData \
    --runtime python3.12 \
    --role $ROLE_ARN \
    --handler lambda_function.lambda_handler \
    --zip-file fileb://cloud/lambda/get_waste_data/get_waste_data.zip \
    --timeout 30 \
    --environment 'Variables={TABLE_NAME=WasteSensorData}' \
    --region $REGION \
    2>/dev/null || echo "      (function may already exist — updating code…)" && \
    aws lambda update-function-code \
        --function-name getWasteData \
        --zip-file fileb://cloud/lambda/get_waste_data/get_waste_data.zip \
        --region $REGION 2>/dev/null

# ─── 6. API Gateway ──────────────────────────────────────────────────
echo "[6/8] Creating API Gateway…"

API_ID=$(aws apigateway create-rest-api \
    --name WasteManagementAPI \
    --region $REGION \
    --query 'id' --output text)
echo "      API ID: $API_ID"

ROOT_ID=$(aws apigateway get-resources \
    --rest-api-id $API_ID \
    --region $REGION \
    --query 'items[0].id' --output text)

# Create /data resource
RESOURCE_ID=$(aws apigateway create-resource \
    --rest-api-id $API_ID \
    --parent-id $ROOT_ID \
    --path-part data \
    --region $REGION \
    --query 'id' --output text)

# GET method
aws apigateway put-method \
    --rest-api-id $API_ID \
    --resource-id $RESOURCE_ID \
    --http-method GET \
    --authorization-type NONE \
    --region $REGION

LAMBDA_URI="arn:aws:apigateway:${REGION}:lambda:path/2015-03-31/functions/arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:getWasteData/invocations"

aws apigateway put-integration \
    --rest-api-id $API_ID \
    --resource-id $RESOURCE_ID \
    --http-method GET \
    --type AWS_PROXY \
    --integration-http-method POST \
    --uri $LAMBDA_URI \
    --region $REGION

# Grant API Gateway permission to invoke Lambda
aws lambda add-permission \
    --function-name getWasteData \
    --statement-id apigateway-invoke-${API_ID} \
    --action lambda:InvokeFunction \
    --principal apigateway.amazonaws.com \
    --source-arn "arn:aws:execute-api:${REGION}:${ACCOUNT_ID}:${API_ID}/*" \
    --region $REGION \
    2>/dev/null || echo "      (permission may already exist)"

# Enable CORS — OPTIONS method
aws apigateway put-method \
    --rest-api-id $API_ID \
    --resource-id $RESOURCE_ID \
    --http-method OPTIONS \
    --authorization-type NONE \
    --region $REGION

aws apigateway put-integration \
    --rest-api-id $API_ID \
    --resource-id $RESOURCE_ID \
    --http-method OPTIONS \
    --type MOCK \
    --request-templates '{"application/json": "{\"statusCode\": 200}"}' \
    --region $REGION

aws apigateway put-method-response \
    --rest-api-id $API_ID \
    --resource-id $RESOURCE_ID \
    --http-method OPTIONS \
    --status-code 200 \
    --response-parameters '{
        "method.response.header.Access-Control-Allow-Headers": false,
        "method.response.header.Access-Control-Allow-Methods": false,
        "method.response.header.Access-Control-Allow-Origin": false
    }' \
    --region $REGION

aws apigateway put-integration-response \
    --rest-api-id $API_ID \
    --resource-id $RESOURCE_ID \
    --http-method OPTIONS \
    --status-code 200 \
    --response-parameters '{
        "method.response.header.Access-Control-Allow-Headers": "'\''Content-Type'\''",
        "method.response.header.Access-Control-Allow-Methods": "'\''GET,OPTIONS'\''",
        "method.response.header.Access-Control-Allow-Origin": "'\''*'\''"
    }' \
    --region $REGION

# Deploy API
aws apigateway create-deployment \
    --rest-api-id $API_ID \
    --stage-name prod \
    --region $REGION

API_ENDPOINT="https://${API_ID}.execute-api.${REGION}.amazonaws.com/prod/data"
echo "      ✓ API Endpoint: $API_ENDPOINT"

# ─── 7. S3 Static Website Hosting ────────────────────────────────────
echo "[7/8] Setting up S3 static website…"

BUCKET_NAME="waste-dashboard-${ACCOUNT_ID}"

aws s3 mb s3://$BUCKET_NAME --region $REGION 2>/dev/null || echo "      (bucket may exist)"

# Disable Block Public Access (required for static hosting)
aws s3api put-public-access-block \
    --bucket $BUCKET_NAME \
    --public-access-block-configuration \
        BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false \
    --region $REGION

# Bucket policy for public read
BUCKET_POLICY="{
  \"Version\": \"2012-10-17\",
  \"Statement\": [{
    \"Sid\": \"PublicRead\",
    \"Effect\": \"Allow\",
    \"Principal\": \"*\",
    \"Action\": \"s3:GetObject\",
    \"Resource\": \"arn:aws:s3:::${BUCKET_NAME}/*\"
  }]
}"
aws s3api put-bucket-policy --bucket $BUCKET_NAME --policy "$BUCKET_POLICY"

aws s3 website s3://$BUCKET_NAME \
    --index-document index.html \
    --region $REGION

# Upload frontend files
aws s3 sync frontend/ s3://$BUCKET_NAME/ --region $REGION

WEBSITE_URL="http://${BUCKET_NAME}.s3-website-${REGION}.amazonaws.com"
echo "      ✓ Dashboard URL: $WEBSITE_URL"

# ─── 8. CloudWatch Log Groups ────────────────────────────────────────
echo "[8/8] Creating CloudWatch log groups…"
aws logs create-log-group --log-group-name /aws/lambda/processWasteSensorData --region $REGION 2>/dev/null || true
aws logs create-log-group --log-group-name /aws/lambda/getWasteData --region $REGION 2>/dev/null || true
echo "      ✓ Log groups ready"

# ─── Summary ─────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════"
echo " DEPLOYMENT COMPLETE"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo " SQS Queue URL  : $SQS_URL"
echo " DynamoDB Table : WasteSensorData"
echo " API Endpoint   : $API_ENDPOINT"
echo " Dashboard URL  : $WEBSITE_URL"
echo ""
echo " ⚠️  IMPORTANT: Update frontend/app.js with the API endpoint:"
echo "    const API_URL = \"$API_ENDPOINT\";"
echo "    Then re-upload:  aws s3 sync frontend/ s3://$BUCKET_NAME/"
echo "═══════════════════════════════════════════════════════════"
