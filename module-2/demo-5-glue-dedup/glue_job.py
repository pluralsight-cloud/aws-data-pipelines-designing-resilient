import sys
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from awsglue.dynamicframe import DynamicFrame
from pyspark.sql.functions import col, row_number
from pyspark.sql.window import Window

# Boilerplate
args = getResolvedOptions(sys.argv, ["JOB_NAME"])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args["JOB_NAME"], args)

# 1. Read raw orders
orders_dyf = glueContext.create_dynamic_frame.from_catalog(
    database="ps_resilient_demo_db", table_name="raw_orders"
)
orders_df = orders_dyf.toDF()

# Log raw count
print(f"Raw orders count: {orders_df.count()}")

# 2. Deduplicate by order_id (keep latest by order_date)
window_spec = Window.partitionBy("order_id").orderBy(col("order_date").desc())
dedup_df = (
    orders_df.withColumn("rn", row_number().over(window_spec))
    .filter(col("rn") == 1)
    .drop("rn")
)

print(f"Deduplicated orders count: {dedup_df.count()}")

# 3. Write curated output partitioned by order_date
dedup_dyf = DynamicFrame.fromDF(dedup_df, glueContext, "dedup_dyf")

glueContext.write_dynamic_frame.from_options(
    frame=dedup_dyf,
    connection_type="s3",
    connection_options={
        "path": "s3://ps-demo-resilient-pipeline-rt/curated/orders/",
        "partitionKeys": ["order_date"],
    },
    format="parquet",
)

job.commit()
