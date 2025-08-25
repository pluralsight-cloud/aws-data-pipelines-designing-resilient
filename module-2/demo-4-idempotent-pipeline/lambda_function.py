import json
import os
import boto3
from datetime import datetime, timezone
from botocore.exceptions import ClientError

ddb = boto3.resource("dynamodb")
s3 = boto3.client("s3")

TABLE = ddb.Table("processed-orders")

# --- REQUIRED env vars (set in Lambda console) ---
# BUCKET = ps-demo-resilient-pipeline-rt
# RAW_PREFIX = raw/events/   (note: no leading slash, no bucket name here)
BUCKET = os.environ["BUCKET"]
RAW_PREFIX = os.environ.get("RAW_PREFIX", "raw/events/")  # keep it simple & consistent

def _event_payload(evt: dict) -> dict:
    """Accepts EventBridge envelope or raw dict/string and returns the business payload."""
    if isinstance(evt, str):
        try:
            evt = json.loads(evt)
        except json.JSONDecodeError:
            return {}
    return evt.get("detail", evt) if isinstance(evt, dict) else {}

def lambda_handler(event, context):
    payload = _event_payload(event)

    order_id = str(payload.get("order_id") or "").strip()
    price = payload.get("price")
    # Allow caller to pass event_date (YYYY-MM-DD); otherwise use today's UTC date
    event_date = payload.get("event_date")
    if not event_date:
        event_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if not order_id or price is None:
        raise Exception("Invalid event – missing order_id or price")

    # Idempotency via conditional put: first write wins, duplicates are ignored
    try:
        TABLE.put_item(
            Item={
                "order_id": order_id,
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "price": price,
                "event_date": event_date,
            },
            ConditionExpression="attribute_not_exists(order_id)",
        )
        first_time = True
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
            print(f"Duplicate event ignored: order_id={order_id}")
            return {"ok": True, "duplicate": True, "order_id": order_id}
        raise

    # Partitioned S3 key to match Module 1 style
    key = f"{RAW_PREFIX}event_date={event_date}/order_id={order_id}.json"

    s3.put_object(
        Bucket=BUCKET,
        Key=key,
        Body=json.dumps({"order_id": order_id, "price": price, "event_date": event_date}),
        ContentType="application/json",
    )

    print(f"Processed order {order_id} at price {price} → s3://{BUCKET}/{key}")
    return {"ok": True, "order_id": order_id, "event_date": event_date, "first_time": first_time}
