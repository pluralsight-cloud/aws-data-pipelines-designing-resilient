# Demo: Using AWS Glue Crawler to Partition and Discover Schema  
📅 Last Updated: 2025-07-31  

This guide walks you through building a resilient, schema-aware data lake table using Amazon S3, AWS Glue Crawler, and Athena.  
By the end, you'll be able to run partitioned queries over S3 data that evolves over time.

---

## 🎯 What You'll Learn

- How to structure S3 data for partitioned querying
- How to infer schema and partition keys using Glue Crawler
- How to query the resulting table in Athena
- How to troubleshoot schema errors (like malformed JSON)

---

## 🧱 Prerequisites

- An AWS account with permissions for:
  - S3
  - Glue
  - IAM
  - Athena

- Region: This guide uses `us-east-1` but works in any region
- Tools: Any text editor or IDE (e.g., VS Code), and access to AWS Console

---

## ✅ Step 1: Create an S3 Bucket with Partitioned Data

### 1.1 Create a new S3 bucket

```
Bucket name: ps-demo-resilient-pipeline
```

### 1.2 Create folder structure inside the bucket

```
s3://ps-demo-resilient-pipeline/raw/events/event_date=2024-01-01/
s3://ps-demo-resilient-pipeline/raw/events/event_date=2024-01-02/
```

### 1.3 Prepare sample data

Create a local file named `events.json` with the following content:

```
{"user_id":"u123","event_type":"click","timestamp":"2024-01-01T12:00:00Z"}
{"user_id":"u456","event_type":"purchase","timestamp":"2024-01-01T12:01:00Z"}
```

⚠️ Each line is a valid JSON object — newline-delimited JSON is required for Athena and Glue.

### 1.4 Upload `events.json` to both folders

Upload the same file to:

```
s3://ps-demo-resilient-pipeline/raw/events/event_date=2024-01-01/events.json
s3://ps-demo-resilient-pipeline/raw/events/event_date=2024-01-02/events.json
```

---

## ✅ Step 2: Create an IAM Role for Glue Crawler

### 2.1 Go to IAM → Create role

- Trusted entity: AWS service
- Use case: Glue
- Name: PS_GlueDemoCrawlerRole

### 2.2 Attach policies

Attach these managed policies:

- `AWSGlueServiceRole`
- `AmazonS3ReadOnlyAccess`

🔐 Optional (Advanced): Replace S3 read-only with a scoped inline policy to just your bucket

---

## ✅ Step 3: Create a Glue Crawler

### 3.1 Go to Glue → Crawlers → Create crawler

Use the following settings:

| Setting         | Value                                                |
|-----------------|------------------------------------------------------|
| Name            | ps-glue-crawler-events                               |
| Data source     | S3                                                   |
| S3 path         | s3://ps-demo-resilient-pipeline/raw/events/         |
| Crawl mode      | Crawl all subfolders                                 |
| IAM role        | PS_GlueDemoCrawlerRole                               |
| Output database | Create: ps_resilient_demo_db                         |
| Table prefix    | raw_events_                                          |
| Schedule        | On demand                                            |

### 3.2 Run the crawler

After creation, click **Run crawler** and wait for it to complete.

---

## ✅ Step 4: Verify Table Schema and Partitions

### 4.1 Go to Glue → Tables → `raw_events_events`

Check that:

- Columns detected: `user_id`, `event_type`, `timestamp`
- Partition key: `event_date`
- Format: JSON
- Location: `s3://ps-demo-resilient-pipeline/raw/events/`

---

## ✅ Step 5: Query the Table in Athena

### 5.1 Set result output location

In Athena:

- Go to **Settings** (top right)
- Set **Query result location** to:

```
s3://ps-demo-resilient-pipeline/athena-results/
```

### 5.2 Select the database

On the left:

- Data source: `AwsDataCatalog`
- Database: `ps_resilient_demo_db`
- Table: `raw_events_events`

### 5.3 Run the query

```sql
SELECT *
FROM ps_resilient_demo_db.raw_events_events
WHERE event_date = '2024-01-01'
LIMIT 10;
```

✅ You should see:

- 2 rows of data
- Clean column headers
- event_date filter working (partition pruning)

---

## 🧠 Troubleshooting Common Issues

| Issue                   | Fix                                                                 |
|------------------------|----------------------------------------------------------------------|
| `HIVE_CURSOR_ERROR`     | Your JSON file may be an array (`[]`) instead of newline-delimited |
| No columns detected     | Crawler was pointed at the wrong S3 path or empty folder            |
| No results in Athena    | Data not uploaded to the correct partition folder                   |
| Extra empty row         | Expected UI artifact — not a bug                                    |

---

## ✅ What You Now Have

- A clean, partitioned data lake table
- Auto-discovered schema
- Athena queries running over versioned S3 paths
- Production-quality setup for scaling to more events and schema versions

---

## 📌 Next Step

→ Move on to:  
**Demo – Pipeline Compatibility with Schema Changes**  
(You’ll simulate a schema evolution and observe how Glue + Athena handle it without breaking)
