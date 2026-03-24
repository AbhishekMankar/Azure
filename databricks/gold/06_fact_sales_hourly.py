# ============================================================
# Notebook: 06_fact_sales_hourly
# Layer:    Gold
# Purpose:  Aggregate fact_sales to hourly grain per product
#           per store. This table is the direct input for the
#           Anomaly Detector and the Prophet forecasting model.
# ============================================================

from pyspark.sql.functions import (
    col, hour, to_timestamp, sum as _sum, count
)
import config

# ── 1. Load fact_sales ───────────────────────────────────────
fact_sales = spark.read.format("delta").load(config.FACT_SALES_PATH)

# ── 2. Extract hour from transaction date ────────────────────
# Assumes fact_sales.date is a date or timestamp column.
# If it is a plain date (no time), you need transaction_timestamp
# from the silver layer instead — adjust the load path accordingly.
fact_with_hour = fact_sales.withColumn(
    "hour", hour(to_timestamp(col("date")))
)

# ── 3. Aggregate to hourly grain ─────────────────────────────
# Grain: product_id + store_id + date + hour
fact_sales_hourly = (
    fact_with_hour
    .groupBy("product_id", "store_id", "date", "hour")
    .agg(
        _sum("quantity").alias("total_quantity"),
        _sum("line_total").alias("total_revenue"),
        count("transaction_id").alias("transaction_count")
    )
    .orderBy("product_id", "store_id", "date", "hour")
)

# ── 4. Write to Gold layer as Delta ─────────────────────────
fact_sales_hourly.write \
    .format("delta") \
    .mode("overwrite") \
    .partitionBy("date") \
    .save(config.FACT_SALES_HOURLY_PATH)

print("✅ fact_sales_hourly written successfully.")
print(f"   Total rows: {fact_sales_hourly.count()}")
