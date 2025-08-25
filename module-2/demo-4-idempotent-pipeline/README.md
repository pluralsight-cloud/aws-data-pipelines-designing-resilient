# Demo 4 – Idempotent Lambda (DynamoDB + S3)

Make your pipeline **retry‑safe** by processing each order **exactly once**. We’ll use DynamoDB for idempotency and write first‑time events to S3 under a clean folder structure. This demo continues from Demo 3 but stands alone if you’re starting fresh.

---

## What you’ll build

* **Lambda** that accepts EventBridge‑style events and implements **idempotency** with DynamoDB conditional writes.
* **S3 write** only on the **first** time an `order_id` arrives.
* **Replay** the same event to prove duplicates are ignored.

**Account:** `081448897918`
**Region:** `us-east-1` (assumed throughout)
**Bucket:** `ps-demo-resilient-pipeline`
**DynamoDB table:** `processed-orders` (PK: `order_id` string)
**Lambda name:** `demo4-idempotent-processor`

---

## Architecture (at a glance)

Event (from EventBridge or direct invoke) → **Lambda** → **DynamoDB conditional PutItem** (reject duplicates) → first time only → **PutObject to S3** at `s3://ps-demo-resilient-pipeline/raw/events/<order_id>.json`

---

## 0) Prereqs

* You have an AWS account and permissions to create S3, DynamoDB, IAM, and Lambda resources in **us‑east‑1**.

---

## 1) Create the S3 bucket and folder layout

1. Open **S3 → Buckets → Create bucket**.
2. Name: **ps-demo-resilient-pipeline**, Region: **us-east-1** → Create bucket.
3. (Optional) Inside the bucket, create the **folders**: `raw/` then inside it `events/`.

> **Important**: Our Lambda will write to the **key prefix** `raw/events/`. Do **not** include the bucket name in this prefix (common mistake that causes duplicated folder names in S3).

---

## 2) Create the DynamoDB table for idempotency

1. Open **DynamoDB → Tables → Create table**.
2. Table name: **processed-orders**.
   Partition key: **order\_id** (String).
   Other settings: default → **Create table**.

---

## 3) Prepare/Update the Lambda execution role

If you already have a Lambda role from Demo 3, reuse it. Otherwise, create one now.

1. Open **IAM → Roles → Create role**.

   * Trusted entity: **AWS service** → **Lambda**.
   * Add permission **AWSLambdaBasicExecutionRole** (for CloudWatch Logs).
   * Role name: **demo-lambda-role** → Create role.
2. With the role open, **Add permissions → Create inline policy**. Paste the JSON below and **Create policy** with name **S3WriteAndDDBIdempotency-Policy**.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "WriteRawEventsToS3",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:AbortMultipartUpload",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::ps-demo-resilient-pipeline",
        "arn:aws:s3:::ps-demo-resilient-pipeline/*"
      ]
    },
    {
      "Sid": "IdempotencyDynamoDB",
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:DeleteItem"
      ],
      "Resource": "arn:aws:dynamodb:us-east-1:081448897918:table/processed-orders"
    }
  ]
}
```

---

## 4) Create the Lambda function

1. Open **Lambda → Create function**.

   * **Author from scratch**.
   * Function name: **demo4-idempotent-processor**.
   * Runtime: **Python 3.13**.
   * Architecture: **x86\_64** (default).
   * Execution role: **Use existing role** → pick **demo-lambda-role**.
   * Create function.
2. In **Code**, replace the default with the code below. Click **Deploy**.

```python
import json, os, boto3, datetime
from botocore.exceptions import ClientError

ddb = boto3.resource("dynamodb")
s3 = boto3.client("s3")

TABLE = ddb.Table("processed-orders")
BUCKET = os.environ["BUCKET"]  # ps-demo-resilient-pipeline
RAW_PREFIX = os.environ.get("RAW_PREFIX", "raw/events/")  # <-- no bucket name here!

def lambda_handler(event, context):
    # Accept EventBridge envelope or raw
    if isinstance(event, str):
        event = json.loads(event)
    payload = event.get("detail", event) if isinstance(event, dict) else {}

    order_id = str(payload.get("order_id"))
    price = payload.get("price")
    if not order_id or price is None:
        raise Exception("Invalid event – missing order_id or price")

    # Idempotency: only first time succeeds
    try:
        TABLE.put_item(
            Item={
                "order_id": order_id,
                "processed_at": datetime.datetime.utcnow().isoformat() + "Z",
                "price": price
            },
            ConditionExpression="attribute_not_exists(order_id)"
        )
        first_time = True
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            print(f"Duplicate event ignored: {order_id}")
            return {"ok": True, "duplicate": True, "order_id": order_id}
        raise

    key = f"{RAW_PREFIX}{order_id}.json"
    s3.put_object(
        Bucket=BUCKET,
        Key=key,
        Body=json.dumps({"order_id": order_id, "price": price}),
        ContentType="application/json"
    )
    print(f"Processed order {order_id} at price {price} (wrote s3://{BUCKET}/{key})")
    return {"ok": True, "order_id": order_id, "first_time": first_time}
```

3. Set **Environment variables** (Configuration → Environment variables → **Edit**):

   * `BUCKET` = `ps-demo-resilient-pipeline`
   * `RAW_PREFIX` = `raw/events/`
     Save.

---

## 5) Invoke with a first‑time event

We’ll use the Lambda console (keeps the demo focused). The function accepts both raw and EventBridge‑style envelopes.

1. In the **Test** tab, create a **new test event** named `first-run` with this JSON:

```json
{
  "version": "0",
  "detail-type": "order.created",
  "source": "demo.orders",
  "detail": { "order_id": 123, "price": 42 }
}
```

2. Click **Test**.

**Expected results**

* **CloudWatch Logs** show: `Processed order 123 at price 42 ...`.
* **S3** has a new object: `s3://ps-demo-resilient-pipeline/raw/events/123.json`.
* **DynamoDB → processed-orders → Explore table items** shows an item with `order_id = "123"`.

---

## 6) Prove idempotency (replay)

1. Click **Test** again with the **same** payload.
2. Check **CloudWatch Logs** – you should see `Duplicate event ignored: 123`.
3. **S3** object count does not increase; the existing file remains.
4. **DynamoDB** still has a single item for `order_id = "123"`.

> Want to re‑run the happy path? Either change `order_id` to a new value (e.g., 124) **or** delete the item `order_id=123` from **DynamoDB → Explore table items → select row → Delete** and test again.

---

## 7) (Optional) Trigger via EventBridge rule

If you prefer a bus → rule → target flow:

1. **EventBridge → Rules → Create rule**

   * Name: `demo4-orders-to-idempotent-lambda`
   * Event pattern (JSON):

```json
{
  "source": ["demo.orders"],
  "detail-type": ["order.created"]
}
```

* **Target**: Lambda → `demo4-idempotent-processor` → Create rule.

2. **EventBridge → Event buses → default → Send events** with the same JSON from step 5. The rule routes it to Lambda.

---

## 8) Troubleshooting

* **Duplicate folder name in S3** (e.g., `ps-demo-resilient-pipeline/ps-demo-resilient-pipeline/...`): fix `RAW_PREFIX` to `raw/events/` (no bucket name). Redeploy and retest.
* **AccessDenied to S3 or DynamoDB**: recheck inline policy **S3WriteAndDDBIdempotency-Policy** on the role.
* **No logs**: verify the function executed (Last modified and Monitoring tab), and that the role includes **AWSLambdaBasicExecutionRole**.
* **ConditionalCheckFailedException** is expected on replays—that’s proof of idempotency.

---

## 9) Clean up

* Delete the S3 objects under `raw/events/` if you don’t need them.
* Delete the **processed-orders** table.
* Disable or delete the EventBridge rule (if you created one).
* Keep or remove the Lambda function and role as desired.

---

## What you learned

* How to implement **idempotency** in a Lambda using a DynamoDB **conditional write**.
* How to persist **first‑time** events to S3 while safely **ignoring duplicates**.
* How to **verify** both failure (duplicate) and success paths in **CloudWatch Logs**, **S3**, and **DynamoDB**.
