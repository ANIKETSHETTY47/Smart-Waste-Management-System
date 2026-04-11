# 🗑️ Smart Waste Management System
### Fog & Edge Computing Architecture on AWS

> **MSc Fog & Edge Computing — Academic Project**

---

## 📐 Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        SENSOR LAYER                              │
│   sensor/sensor_simulator.py                                     │
│   Generates readings for bin_1 … bin_5 every 5 seconds           │
│   Fields: bin_id, fill_level, temperature, methane, weight       │
└──────────────────────┬───────────────────────────────────────────┘
                       │ function call
┌──────────────────────▼───────────────────────────────────────────┐
│                        FOG LAYER                                 │
│   fog/fog_node.py                                                │
│   • Validates data                                               │
│   • Applies edge logic → status classification                  │
│   • Sends enriched payload to AWS SQS                            │
└──────────────────────┬───────────────────────────────────────────┘
                       │ boto3 → SQS
┌──────────────────────▼───────────────────────────────────────────┐
│                     AWS CLOUD BACKEND                             │
│                                                                   │
│   SQS (wasteSensorQueue)                                         │
│       │                                                           │
│       ▼                                                           │
│   Lambda (processWasteSensorData)  ──►  DynamoDB (WasteSensorData)│
│                                                                   │
│   API Gateway (GET /data)                                         │
│       │                                                           │
│       ▼                                                           │
│   Lambda (getWasteData)  ──►  reads DynamoDB                      │
│                                                                   │
│   S3 Static Website  ──►  Dashboard (HTML/JS)                     │
└──────────────────────────────────────────────────────────────────┘
```

---

## 📂 Folder Structure

```
Project/
├── config.py                              # Shared constants & thresholds
├── requirements.txt                       # Python dependencies
├── sensor/
│   └── sensor_simulator.py                # Sensor layer — data generator
├── fog/
│   └── fog_node.py                        # Fog layer — edge logic + SQS
├── cloud/
│   └── lambda/
│       ├── process_waste_sensor/
│       │   └── lambda_function.py         # SQS → DynamoDB
│       └── get_waste_data/
│           └── lambda_function.py         # API Gateway → DynamoDB scan
├── frontend/
│   ├── index.html                         # Dashboard page
│   ├── style.css                          # Styling
│   └── app.js                             # Fetch loop (10s refresh)
├── deploy/
│   ├── setup_aws.sh                       # Full AWS deployment script
│   ├── package_lambdas.sh                 # Zip Lambda packages
│   └── cleanup.sh                         # Tear down resources
├── bonus/
│   └── load_simulator.py                  # Stress-test script
└── README.md
```

---

## 🔧 Edge Logic Rules

| Priority | Condition               | Status              |
|----------|-------------------------|----------------------|
| 1        | `fill_level > 80%`      | `NEEDS_COLLECTION`   |
| 2        | `methane_level > 300`   | `GAS_ALERT`          |
| 3        | `temperature > 60°C`    | `FIRE_RISK`          |
| 4        | None of the above       | `NORMAL`             |

---

## 🚀 Deployment Guide

### Prerequisites
- Python 3.9+ installed locally
- AWS CLI v2 configured (`aws configure`)
- AWS Learner Lab credentials active

### Step 1 — Install Python Dependencies
```bash
cd Project
pip install -r requirements.txt
```

### Step 2 — Package Lambda Functions
```bash
bash deploy/package_lambdas.sh
```

### Step 3 — Deploy AWS Infrastructure
```bash
bash deploy/setup_aws.sh
```

This creates: SQS queue → DynamoDB table → IAM role → Lambda functions → API Gateway → S3 website.

**Note the outputs** — you will need the **API endpoint** URL.

### Step 4 — Update Frontend API URL
Open `frontend/app.js` and replace the placeholder:
```javascript
const API_URL = "https://YOUR_API_GATEWAY_ID.execute-api.us-east-1.amazonaws.com/prod/data";
```
with the API endpoint printed by the setup script.

Then re-upload:
```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
aws s3 sync frontend/ s3://waste-dashboard-${ACCOUNT_ID}/
```

### Step 5 — Run the Sensor Simulator
```bash
python sensor/sensor_simulator.py
```
Let it run for 30–60 seconds. You'll see logs showing data → fog → SQS.

### Step 6 — View the Dashboard
Open the S3 website URL from the setup output in a browser:
```
http://waste-dashboard-ACCOUNT_ID.s3-website-us-east-1.amazonaws.com
```

---

## ✅ Testing & Verification

### Check SQS Messages
```bash
aws sqs get-queue-attributes \
    --queue-url $(aws sqs get-queue-url --queue-name wasteSensorQueue --query QueueUrl --output text) \
    --attribute-names ApproximateNumberOfMessages
```

### Check DynamoDB Records
```bash
aws dynamodb scan --table-name WasteSensorData --max-items 5
```

### Test API Endpoint
```bash
curl https://YOUR_API_GATEWAY_ID.execute-api.us-east-1.amazonaws.com/prod/data
```

### Check Lambda Logs
```bash
aws logs tail /aws/lambda/processWasteSensorData --since 5m
aws logs tail /aws/lambda/getWasteData --since 5m
```

---

## 📊 Example JSON Output

API response from `GET /data`:
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
  },
  {
    "bin_id": "bin_3",
    "fill_level": 45.0,
    "temperature": 35.0,
    "methane_level": 350.0,
    "weight": 15.2,
    "status": "GAS_ALERT",
    "timestamp": "2026-03-01T22:45:00+00:00"
  }
]
```

---

## 🧹 Cleanup

To remove all AWS resources:
```bash
bash deploy/cleanup.sh
```

---

## 🎓 Academic Architecture Justification

### Why Fog & Edge Computing?

Traditional cloud-only IoT architectures suffer from:
1. **High latency** — every sensor reading travels to the cloud for processing.
2. **Bandwidth waste** — raw data floods the network.
3. **Single point of failure** — cloud outage means no processing.

Our fog/edge approach addresses these by introducing a **fog layer** between sensors and the cloud:

| Concern | Cloud-Only | Fog/Edge (Our Approach) |
|---------|-----------|------------------------|
| Latency | High (round-trip to cloud) | Low (local processing) |
| Bandwidth | All raw data uploaded | Only enriched data sent |
| Reliability | Cloud-dependent | Fog can operate offline |
| Privacy | Raw data in cloud | Sensitive data stays local |

### Architecture Mapping

| Layer | Role | Technology |
|-------|------|-----------|
| **Edge/Sensor** | Data generation, physical interface | Python script (simulated IoT) |
| **Fog** | Local validation, classification, filtering | Python service (fog_node.py) |
| **Cloud** | Persistent storage, API, dashboard | AWS SQS, Lambda, DynamoDB, API Gateway, S3 |

### Key Design Decisions
- **Function-call integration** between sensor and fog avoids requiring a local HTTP server, keeping the project simple and focused on the architecture concepts.
- **SQS as a buffer** decouples the fog layer from cloud processing, enabling asynchronous and reliable delivery.
- **Serverless backend** (Lambda + DynamoDB) eliminates server management — ideal for academic environments with limited resources.
- **Static frontend on S3** avoids running a web server and is essentially free within AWS Free Tier.

---

## 🎤 4-Minute Presentation Guide

| Time | Topic | What to Show |
|------|-------|-------------|
| 0:00–0:30 | **Introduction** | Project title, problem statement (inefficient waste collection), your name |
| 0:30–1:00 | **Architecture** | Show the architecture diagram. Explain 3 layers: sensors → fog → cloud |
| 1:00–1:30 | **Edge Logic** | Show `fog_node.py` classify_status function. Explain the 4 status categories & why processing at the edge reduces cloud load |
| 1:30–2:30 | **Live Demo** | 1. Run `python sensor/sensor_simulator.py` — show terminal logs. 2. Open dashboard — show bins updating. 3. Point out status badges (NORMAL vs NEEDS_COLLECTION) |
| 2:30–3:15 | **AWS Components** | Show DynamoDB table in console (or CLI scan). Mention SQS → Lambda → DynamoDB flow. Show API Gateway returning JSON |
| 3:15–3:45 | **Academic Value** | Fog reduces latency & bandwidth. Edge logic enables real-time alerts. Scalable serverless backend |
| 3:45–4:00 | **Conclusion** | Summarise benefits, potential extensions (real sensors, ML-based predictions), thank audience |

### Demo Tips
- Start the simulator **before** your presentation so data is already in DynamoDB.
- Have the dashboard URL open and ready.
- Keep a `curl` command ready to show raw API output.

---

## 📋 Environment Variables (Reference)

| Variable | Used By | Default |
|----------|---------|---------|
| `AWS_REGION` | Fog node, Lambdas | `us-east-1` |
| `TABLE_NAME` | Lambda functions | `WasteSensorData` |
| `AWS_ACCESS_KEY_ID` | boto3 (local) | From `aws configure` |
| `AWS_SECRET_ACCESS_KEY` | boto3 (local) | From `aws configure` |
| `AWS_SESSION_TOKEN` | boto3 (Learner Lab) | From `aws configure` |

---

## ⚠️ Notes for AWS Learner Lab

- Learner Lab sessions expire — **redeploy if your session resets**.
- IAM permissions are restricted — the script uses managed policies that should work in Learner Lab.
- Avoid creating resources in regions other than `us-east-1`.
- If `aws iam create-role` fails, check if the role already exists: `aws iam get-role --role-name WasteLambdaRole`.
