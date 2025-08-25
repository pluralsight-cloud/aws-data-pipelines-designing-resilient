# Designing Resilient AWS Data Pipelines

This repository provides all demo code, datasets, and policies used in the Pluralsight course **Designing Resilient AWS Data Pipelines** by Rupesh Tiwari.

Each demo is organized by module, with its own README file for detailed setup and run instructions.

---

## 📂 Repository Layout

```ruby
SRC/
├── module-1
│   └── demo-glue-crawler-schema-discovery
│       ├── data/                 # Sample raw data
│       ├── README.md             # Steps to run Glue Crawler demo
│
├── module-2
│   ├── demo-3-retry-dlq
│   │   ├── lambda_function.py    # Lambda with retry + DLQ
│   │   ├── README.md
│   │
│   ├── demo-4-idempotent-pipeline
│   │   ├── lambda_function.py    # Lambda with idempotent logic
│   │   ├── policy.json           # IAM policy for Lambda/DynamoDB
│   │   ├── README.md
│   │
│   └── demo-5-glue-dedup
│       ├── data/                 # Sample data with duplicates
│       ├── glue_job.py           # Glue job with deduplication logic
│       ├── policy.json
│       ├── README.md
│
└── README.md                     # This file


```

## 🚀 How to Use This Repo

1. Clone the repository:

    `git clone https://github.com/<your-repo>/aws-data-pipelines-resilience.git cd aws-data-pipelines-resilience`

2. Navigate to the demo you want to run.  
    Example:

    `cd module-2/demo-3-retry-dlq`

3. Follow the `README.md` inside that demo folder for setup and execution steps.

---

## 📘 Learning Path

- **Module 1**

  - [Demo: Glue Crawler for Schema Discovery](./module-1/demo-glue-crawler-schema-discovery/)

- **Module 2**

  - [Demo 3: Lambda Retries and Dead-Letter Queues](./module-2/demo-3-retry-dlq/)
  - [Demo 4: Idempotent Pipeline with Lambda](./module-2/demo-4-idempotent-pipeline/)
  - [Demo 5: Deduplication at Scale with AWS Glue](./module-2/demo-5-glue-dedup/)

---

## ⚠️ Cost and Cleanup

Running these demos in your AWS account will incur charges for:

- Amazon S3 storage
- AWS Glue crawlers and jobs
- AWS Lambda execution
- Athena queries

Be sure to **delete all created resources** (S3 buckets, Glue jobs, Lambda functions, IAM roles) after completing each demo.

---

## 📩 Support

For course-related discussions, please use the Pluralsight platform.  

For personalized coaching or interview prep: [bit.ly/book-rupesh](https://bit.ly/book-rupesh)
