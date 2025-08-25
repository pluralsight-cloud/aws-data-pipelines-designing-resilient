# Demo 5 – Deduplicating Raw Orders with AWS Glue and Validating in Athena

In this exercise, we’ll handle **duplicate events in raw order data** using **AWS Glue** and validate the results using **Athena**.

Duplicates can happen in production when:

- Upstream teams replay the same files,
- Retry storms resend the same payload,
- Or systems produce accidental duplicates.

Our goal:  
✅ Crawl raw order data into the Glue Data Catalog  
✅ Create a Glue ETL job to deduplicate by `order_id`  
✅ Store curated output in partitioned Parquet format  
✅ Crawl the curated output  
✅ Validate in Athena that duplicates are removed

---

## Prerequisites

- **Account ID:** `167042070033`
- **S3 Bucket:** `ps-demo-resilient-pipeline-rt`
- **Database:** `ps_resilient_demo_db`
- **IAM Roles:**

  - `PS_GlueDemoCrawlerRole` (for Crawlers)
  - `PS_GlueDemo5JobRole` (for Glue Job, see policy below)

---

## Step 1 – Prepare S3 Folders and Data

Your bucket should have this structure:

```sql
ps-demo-resilient-pipeline-rt/
├── raw/
│   └── orders/
│       ├── order_date=2025-08-20/
│       │   ├── 199.json
│       │   └── 200.json
│       └── order_date=2025-08-21/
│           ├── 201.json
│           ├── 202.json
│           ├── 202-dup.json   <- duplicate
│           └── 203.json
└── curated/
    └── orders/   (empty initially, Glue job will populate)
```

Sample raw order file:

```json
{
  "order_id": 202,
  "price": 30.0,
  "order_date": "2025-08-21"
}
```

---

## Step 2 – IAM Role for Glue Job

Create a new role: **`PS_GlueDemo5JobRole`**

Attach managed policies:

- `AWSGlueServiceRole`
- `AmazonS3FullAccess`

Add **inline policy** (least privilege):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3AccessForGlueJob",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": [
        "arn:aws:s3:::ps-demo-resilient-pipeline-rt/*",
        "arn:aws:s3:::ps-demo-resilient-pipeline-rt"
      ]
    },
    {
      "Sid": "GlueCatalogAccess",
      "Effect": "Allow",
      "Action": [
        "glue:GetDatabase",
        "glue:GetTable",
        "glue:CreateTable",
        "glue:UpdateTable"
      ],
      "Resource": "*"
    }
  ]
}

```

---

## Step 3 – Create Glue Crawlers

### Raw Orders Crawler

- **Name:** `ps-glue-crawler-raw-orders`
- **Role:** `PS_GlueDemoCrawlerRole`
- **S3 path:** `s3://ps-demo-resilient-pipeline-rt/raw/orders/`
- **Database:** `ps_resilient_demo_db`
- **Table prefix:** `raw_`

Run this crawler → creates table **`raw_orders`** with schema:  
`order_id INT, price DOUBLE, order_date STRING (partition)`

### Curated Orders Crawler

- **Name:** `ps-glue-crawler-curated-orders`
- **Role:** `PS_GlueDemoCrawlerRole`
- **S3 path:** `s3://ps-demo-resilient-pipeline-rt/curated/orders/`
- **Database:** `ps_resilient_demo_db`
- **Table prefix:** `curated_`

---

## Step 4 – Validate Raw Orders in Athena

Run crawler for raw orders.  
Query in Athena:

`SELECT  *  FROM "ps_resilient_demo_db"."raw_orders";`

Expected result: **6 rows** (includes duplicate `order_id=202`).

---

## Step 5 – Create Glue Job for Deduplication

In **Glue Studio** → **Script editor** → **Spark, Start fresh**

**Job name:** `curate-orders-job`  
**Role:** `PS_GlueDemo5JobRole`  
**Language:** Python  
**Glue version:** 5.0

Paste this script:

```python
import sys
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from awsglue.dynamicframe import DynamicFrame
from pyspark.sql.functions import col, row_number
from pyspark.sql.window import Window

# Boilerplate
args = getResolvedOptions(sys.argv, ['JOB_NAME'])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# 1. Read raw orders
orders_dyf = glueContext.create_dynamic_frame.from_catalog(
    database="ps_resilient_demo_db",
    table_name="raw_orders"
)
orders_df = orders_dyf.toDF()

# Log raw count
print(f"Raw orders count: {orders_df.count()}")

# 2. Deduplicate by order_id (keep latest by order_date)
window_spec = Window.partitionBy("order_id").orderBy(col("order_date").desc())
dedup_df = orders_df.withColumn("rn", row_number().over(window_spec)) \
                    .filter(col("rn") == 1) \
                    .drop("rn")

print(f"Deduplicated orders count: {dedup_df.count()}")

# 3. Write curated output partitioned by order_date
dedup_dyf = DynamicFrame.fromDF(dedup_df, glueContext, "dedup_dyf")

glueContext.write_dynamic_frame.from_options(
    frame=dedup_dyf,
    connection_type="s3",
    connection_options={"path": "s3://ps-demo-resilient-pipeline-rt/curated/orders/", "partitionKeys": ["order_date"]},
    format="parquet"
)

job.commit()

```
Run the job → Output written to `s3://ps-demo-resilient-pipeline-rt/curated/orders/`

---

## Step 6 – Run Curated Orders Crawler

Run `ps-glue-crawler-curated-orders`.

---

## Step 7 – Validate in Athena

Query curated table:

`SELECT  *  FROM "ps_resilient_demo_db"."curated_orders";`

Expected result: **5 rows (duplicate removed)**

For comparison:

`SELECT  *  FROM "ps_resilient_demo_db"."raw_orders";`

Shows **6 rows (with duplicate)**

---

## Step 8 – Check Glue Job Logs (CloudWatch)

Navigate to CloudWatch Logs group:

`/aws-glue/jobs/output`

Expected log lines:

`Raw orders count:  6  Deduplicated orders count:  5`

---

## Outcome

🎯 We ingested raw orders with duplicates,  
🎯 Used Glue to deduplicate safely,  
🎯 Validated results with Athena,  
🎯 Logged before/after counts in CloudWatch.

This mirrors real-world data engineering patterns where Glue handles batch deduplication, and Athena validates output before downstream analytics.
