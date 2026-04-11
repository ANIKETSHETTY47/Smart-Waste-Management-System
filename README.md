# Smart Waste Management System

Fog & Edge Computing Architecture on AWS

MSc Fog & Edge Computing — NCI, Semester 2 2026

---

## Architecture

The system has three layers: sensors generate data, a fog node processes it locally, and an AWS backend stores and serves it to a web dashboard.

```
SENSOR LAYER (sensor/sensor_simulator.py)
  Generates readings for bin_1 .. bin_5 every 5 seconds
  Fields: bin_id, fill_level, temperature, methane, weight
        |
        | function call
        v
FOG LAYER (fog/fog_node.py)
  Validates incoming data
  Classifies bin status (edge logic)
  Sends enriched payload to SQS
        |
        | boto3 -> SQS
        v
AWS CLOUD BACKEND
  SQS (wasteSensorQueue)
    -> Lambda (processWasteSensorData) -> DynamoDB (WasteSensorData)

  API Gateway (GET /data)
    -> Lambda (getWasteData) -> reads DynamoDB

  S3 Static Website -> Dashboard (HTML/JS)
```

---

## Folder Structure

```
Project/
├── config.py                              # shared constants & thresholds
├── requirements.txt                       # python dependencies
├── sensor/
│   └── sensor_simulator.py                # sensor layer, data generator
├── fog/
│   └── fog_node.py                        # fog layer, edge logic + SQS dispatch
├── cloud/
│   └── lambda/
│       ├── process_waste_sensor/
│       │   └── lambda_function.py         # SQS trigger -> writes to DynamoDB
│       └── get_waste_data/
│           └── lambda_function.py         # API Gateway -> scans DynamoDB
├── frontend/
│   ├── index.html                         # dashboard page
│   ├── style.css                          # styling
│   └── app.js                             # polling loop, charts, table
├── deploy/
│   ├── setup_aws.sh                       # provisions all AWS resources
│   ├── package_lambdas.sh                 # zips lambda code for deployment
│   └── cleanup.sh                         # tears down AWS resources
├── bonus/
│   └── load_simulator.py                  # stress test script
└── README.md
```

---

## Edge Logic

The fog node classifies each bin reading based on these thresholds (checked in priority order):

| Priority | Condition               | Status              |
|----------|-------------------------|----------------------|
| 1        | `fill_level > 80%`      | `NEEDS_COLLECTION`   |
| 2        | `methane_level > 300`   | `GAS_ALERT`          |
| 3        | `temperature > 60°C`    | `FIRE_RISK`          |
| 4        | none of the above       | `NORMAL`             |

So if a bin is both full and overheating, it gets `NEEDS_COLLECTION` since that's checked first.

---

## How to Deploy

### What you need
- Python 3.9+
- AWS CLI v2, configured with `aws configure`
- Active AWS Learner Lab session (or a personal AWS account)

### 1. Install dependencies
```bash
cd Project
pip install -r requirements.txt
```

### 2. Package the Lambda functions
```bash
bash deploy/package_lambdas.sh
```

### 3. Deploy to AWS
```bash
bash deploy/setup_aws.sh
```

This creates everything: SQS queue, DynamoDB table, both Lambda functions, API Gateway, and the S3-hosted dashboard. The script prints out the API endpoint and dashboard URL at the end — copy those.

### 4. Set the API URL in the frontend
Open `frontend/app.js` and put your API endpoint on line 7:
```javascript
var API_URL = "https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/prod/data";
```

Then re-upload the frontend:
```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
aws s3 sync frontend/ s3://waste-dashboard-${ACCOUNT_ID}/
```

### 5. Start the sensor simulator
```bash
python sensor/sensor_simulator.py
```
Let it run for about 30-60 seconds so data builds up in DynamoDB.

### 6. Open the dashboard
Go to the S3 website URL that the setup script printed:
```
http://waste-dashboard-ACCOUNT_ID.s3-website-us-east-1.amazonaws.com
```
You should see the table and charts updating every 3 seconds.

---

## Verifying it Works

Check that messages are landing in SQS:
```bash
aws sqs get-queue-attributes \
    --queue-url $(aws sqs get-queue-url --queue-name wasteSensorQueue --query QueueUrl --output text) \
    --attribute-names ApproximateNumberOfMessages
```

Check DynamoDB has records:
```bash
aws dynamodb scan --table-name WasteSensorData --max-items 5
```

Hit the API directly:
```bash
curl https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/prod/data
```

Check Lambda logs if something isn't working:
```bash
aws logs tail /aws/lambda/processWasteSensorData --since 5m
aws logs tail /aws/lambda/getWasteData --since 5m
```

---

## Example API Response

`GET /data` returns the latest reading for each bin:
```json
[
  {
    "bin_id": "bin_1",
    "fill_level": 85.3,
    "temperature": 42.1,
    "methane_level": 180.5,
    "weight": 23.4,
    "status": "NEEDS_COLLECTION",
    "timestamp": "2026-03-01T22:45:00+00:00"
  },
  {
    "bin_id": "bin_2",
    "fill_level": 30.0,
    "temperature": 65.2,
    "methane_level": 120.0,
    "weight": 8.7,
    "status": "FIRE_RISK",
    "timestamp": "2026-03-01T22:45:00+00:00"
  }
]
```

---

## Tearing Down

To delete all the AWS resources when you're done:
```bash
bash deploy/cleanup.sh
```

---

## Why Fog/Edge Instead of Cloud-Only?

A cloud-only setup would send every raw sensor reading straight to AWS for processing. That works, but it has problems at scale: high latency for time-sensitive alerts (like a fire), wasted bandwidth uploading data that turns out to be normal, and total dependence on the cloud being available.

By adding a fog layer between the sensors and the cloud, we can:
- Classify bin status locally in under a millisecond instead of waiting for a cloud round trip
- Only send enriched/tagged data to the cloud, cutting down on bandwidth
- Keep the fog node running even if the cloud connection drops temporarily

| Concern     | Cloud-Only                 | With Fog Layer              |
|-------------|----------------------------|-----------------------------|
| Latency     | high (cloud round trip)    | low (local classification)  |
| Bandwidth   | all raw data uploaded      | only enriched data sent     |
| Reliability | cloud-dependent            | fog can buffer offline      |
| Privacy     | raw data in cloud          | sensitive data stays local  |

### Layer Breakdown

| Layer         | What it does                              | Tech used                                    |
|---------------|-------------------------------------------|----------------------------------------------|
| Sensor/Edge   | generates bin readings                    | Python simulator                             |
| Fog           | validates, classifies, dispatches         | Python (fog_node.py), boto3                  |
| Cloud         | stores data, serves API, hosts dashboard  | SQS, Lambda, DynamoDB, API Gateway, S3       |

### Design Decisions
- **Direct function call** between sensor and fog (rather than HTTP/MQTT) keeps things simple and focuses on the architecture rather than networking setup. There is an MQTT proof-of-concept in the project files separately.
- **SQS as a buffer** between fog and Lambda means messages won't be lost during Lambda cold starts or throttling.
- **Serverless backend** with Lambda + DynamoDB on-demand means no servers to manage and it scales automatically.
- **Static site on S3** for the dashboard — no web server needed, basically free.

---

## Environment Variables

| Variable              | Used by              | Default            |
|-----------------------|----------------------|--------------------|
| `AWS_REGION`          | fog node, lambdas    | `us-east-1`        |
| `TABLE_NAME`          | lambda functions     | `WasteSensorData`  |
| `AWS_ACCESS_KEY_ID`   | boto3 (local runs)   | from aws configure |
| `AWS_SECRET_ACCESS_KEY`| boto3 (local runs)  | from aws configure |
| `AWS_SESSION_TOKEN`   | boto3 (Learner Lab)  | from aws configure |

---

## Learner Lab Notes

- Sessions expire. If your credentials stop working, start a new session and run `aws configure` again. You may need to redeploy.
- Stick to `us-east-1` — other regions may not have the right permissions.
- If `aws iam create-role` fails, the role probably already exists. Check with `aws iam get-role --role-name WasteLambdaRole`.
- The setup script uses `LabRole` by default, which is the pre-existing role in Learner Lab environments.
