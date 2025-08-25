# Demo 1 - Resilient AWS Lambda with EventBridge, Retries, and DLQ

This demo shows how to build a resilient AWS Lambda that processes events from Amazon EventBridge, retries on failure, and sends failed events to an Amazon SQS Dead Letter Queue (DLQ).

## 📂 Project Structure
```
module-2/
  demo-3-retry-dlq/
    src/
      lambda_function.py
    README.md
```

---

## 1️⃣ Create the SQS Dead Letter Queue (DLQ)
1. Open **Amazon SQS** in the AWS Console.
2. Click **Create queue** → **Standard Queue**.
3. Name it: `lambda-failures-dlq`
4. Keep defaults for configuration.
5. **Create queue**.

---

## 2️⃣ Update the DLQ Access Policy
1. Go to the DLQ you created → **Permissions** tab → **Access Policy**.
2. Replace the policy with:
```json
{
  "Version": "2012-10-17",
  "Id": "__default_policy_ID",
  "Statement": [
    {
      "Sid": "__owner_statement",
      "Effect": "Allow",
      "Principal": { "AWS": "arn:aws:iam::<YOUR_ACCOUNT_ID>:root" },
      "Action": "SQS:*",
      "Resource": "arn:aws:sqs:us-east-1:<YOUR_ACCOUNT_ID>:lambda-failures-dlq"
    },
    {
      "Sid": "AllowLambdaServiceToSendToDLQ",
      "Effect": "Allow",
      "Principal": { "Service": "lambda.amazonaws.com" },
      "Action": "sqs:SendMessage",
      "Resource": "arn:aws:sqs:us-east-1:<YOUR_ACCOUNT_ID>:lambda-failures-dlq",
      "Condition": {
        "StringEquals": { "aws:SourceAccount": "<YOUR_ACCOUNT_ID>" },
        "ArnLike": { "aws:SourceArn": "arn:aws:lambda:us-east-1:<YOUR_ACCOUNT_ID>:function:demo1-retry-and-dlq*" }
      }
    }
  ]
}
```
> Replace `<YOUR_ACCOUNT_ID>` with your AWS Account ID.

---

## 3️⃣ Create the Lambda Execution Role
1. Go to **IAM** → **Roles** → **Create role**.
2. Select **AWS service** → **Lambda**.
3. Attach policies:
   - **AWSLambdaBasicExecutionRole**
   - **AmazonSQSFullAccess**
4. Name the role: `LambdaRetryDLQRole`
5. **Create role**.

---

## 4️⃣ Create the Lambda Function
1. Go to **AWS Lambda** → **Create function**.
2. Choose **Author from scratch**.
3. Function name: `demo1-retry-and-dlq`
4. Runtime: **Python 3.12** (or latest available).
5. Execution role: **Use existing role** → select `LambdaRetryDLQRole`.
6. Create the function.

---

## 5️⃣ Add Lambda Code
In `src/lambda_function.py`:
```python
import json

def lambda_handler(event, context):
    if isinstance(event, str):
        try:
            event = json.loads(event)
        except json.JSONDecodeError:
            pass

    # Accept either a raw payload OR an EventBridge envelope
    payload = event.get("detail", event) if isinstance(event, dict) else {}
    price = payload.get("price")

    if price is None:
        raise Exception("Missing price")

    order_id = payload.get("order_id")
    print(f"Processed order {order_id} at price {price}")
    return {"ok": True, "order_id": order_id, "price": price}
```

Deploy the code.

---

## 6️⃣ Configure the Lambda's DLQ
1. In the Lambda **Configuration** tab → **Asynchronous invocation**.
2. Enable **DLQ** → select **SQS** → choose `lambda-failures-dlq`.
3. Save changes.

---

## 7️⃣ Create EventBridge Rule
1. Go to **Amazon EventBridge** → **Rules** → **Create rule**.
2. Name: `send-orders-to-lambda`
3. Event pattern (Custom events):
```json
{
  "source": ["demo.orders"]
}
```
4. Target: **Lambda function** → `demo1-retry-and-dlq`.

---

## 8️⃣ Test Failure Path (DLQ)
1. Go to **EventBridge** → **Event buses** → **default** → **Send events**.
2. Event to send:
   - Event source: `demo.orders`
   - Detail type: `trigger`
   - Event detail:          
      ```json
      {
        "order_id": 123
      }
      ```

1. This will fail because `price` is missing.
2. After retry attempts, check **SQS → lambda-failures-dlq → Messages** to see the failed event.

---

## 9️⃣ Test Success Path
1. Send an event with required fields:
   - Event source: `demo.orders`
   - Detail type: `trigger`
   - Event detail:          
      ```json
      {
        "order_id": 123,
        "price": 42
      }
      ```
 
1. Check **CloudWatch Logs** for the Lambda function.
2. You should see:
```
Processed order 123 at price 42
```

---

## 🔍 DLQ Message Tabs Explained
When you view a DLQ message in SQS:
- **Body** → Original event payload
- **Attributes** → Metadata such as SentTimestamp
- **Message attributes** → Custom attributes if any
- **MD5 of body** → Hash for message integrity

---

✅ **You now have a resilient Lambda with retries and a DLQ for failed events.**

---

Cleanup
-------

-   EventBridge → disable/delete `invoke-demo3`
    
-   Lambda → delete `demo3-retry-and-dlq`
    
-   SQS → delete `lambda-failures-dlq`
    
-   IAM → delete `lambda-retry-dlq-role` (if it’s demo‑only)
