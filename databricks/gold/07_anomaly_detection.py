# ============================================================
# Notebook: 07_anomaly_detection
# Layer:    Gold (AI Extension)
# Purpose:  For each product+store combination, send its
#           hourly sales time series to Azure Anomaly Detector.
#           Write results to fact_anomaly_scores Delta table.
#
# Output table columns:
#   product_id, store_id, date, hour,
#   total_quantity, expected_value,
#   upper_bound, lower_bound,
#   is_anomaly, anomaly_score, severity
# ============================================================

import requests
import json
from datetime import datetime, timedelta

from pyspark.sql import Row
from pyspark.sql.functions import col, concat_ws, lit
from pyspark.sql.types import (
    StructType, StructField,
    StringType, IntegerType, DoubleType, BooleanType, DateType
)
import config

# ── Minimum points required by the API ──────────────────────
# Azure Anomaly Detector needs at least 12 data points.
MIN_DATA_POINTS = 12


# ============================================================
# HELPER: Build ISO timestamp string the API expects
# ============================================================
def build_timestamp(date_val, hour_val):
    """
    Combine a Python date and an integer hour into an
    ISO-8601 string: '2024-03-15T14:00:00Z'
    """
    dt = datetime(date_val.year, date_val.month, date_val.day, hour_val)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# ============================================================
# HELPER: Call Azure Anomaly Detector — entire series endpoint
# This sends the full time series and gets anomaly status
# for every single point in one API call.
# ============================================================
def call_anomaly_detector(series_points):
    """
    series_points: list of {"timestamp": str, "value": float}
    Returns: full API response dict, or None on failure
    """
    url = (
        f"{config.ANOMALY_DETECTOR_ENDPOINT}"
        f"anomalydetector/{config.ANOMALY_API_VERSION}"
        f"/timeseries/entire/detect"
    )

    headers = {
        "Content-Type": "application/json",
        "Ocp-Apim-Subscription-Key": config.ANOMALY_DETECTOR_API_KEY
    }

    payload = {
        "series": series_points,
        "granularity": config.ANOMALY_GRANULARITY,
        "sensitivity": config.ANOMALY_SENSITIVITY
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"  ⚠️  API call failed: {e}")
        return None


# ============================================================
# HELPER: Map anomaly score to human-readable severity label
# ============================================================
def get_severity(score, is_anomaly):
    if not is_anomaly:
        return "Normal"
    if score >= 0.9:
        return "High"
    if score >= 0.6:
        return "Medium"
    return "Low"


# ============================================================
# MAIN: Process each product+store combination
# ============================================================

# ── 1. Load hourly fact table ────────────────────────────────
hourly_df = spark.read.format("delta").load(config.FACT_SALES_HOURLY_PATH)

# ── 2. Get distinct product+store combinations ───────────────
combos = (
    hourly_df
    .select("product_id", "store_id")
    .distinct()
    .collect()
)

print(f"📦 Processing {len(combos)} product+store combinations...")

# ── 3. Collect results across all combinations ───────────────
all_results = []

for row in combos:
    product_id = row["product_id"]
    store_id   = row["store_id"]

    # Filter time series for this product+store
    ts_rows = (
        hourly_df
        .filter(
            (col("product_id") == product_id) &
            (col("store_id") == store_id)
        )
        .orderBy("date", "hour")
        .select("date", "hour", "total_quantity")
        .collect()
    )

    # Skip if not enough data points
    if len(ts_rows) < MIN_DATA_POINTS:
        print(f"  ⏭  Skipping {product_id}/{store_id} — only {len(ts_rows)} points")
        continue

    # Build series payload for API
    series_points = [
        {
            "timestamp": build_timestamp(r["date"], r["hour"]),
            "value": float(r["total_quantity"])
        }
        for r in ts_rows
    ]

    # Call Azure Anomaly Detector
    api_response = call_anomaly_detector(series_points)

    if api_response is None:
        continue

    # ── Parse API response ───────────────────────────────────
    # The API returns parallel arrays — one value per time point
    is_anomaly_list   = api_response.get("isAnomaly", [])
    expected_vals     = api_response.get("expectedValues", [])
    upper_margins     = api_response.get("upperMargins", [])
    lower_margins     = api_response.get("lowerMargins", [])
    anomaly_scores    = api_response.get("anomalyScores", [False] * len(ts_rows))

    # ── Build one result row per time point ─────────────────
    for i, ts_row in enumerate(ts_rows):
        expected  = expected_vals[i]   if i < len(expected_vals)   else None
        upper_m   = upper_margins[i]   if i < len(upper_margins)   else None
        lower_m   = lower_margins[i]   if i < len(lower_margins)   else None
        is_anom   = is_anomaly_list[i] if i < len(is_anomaly_list) else False
        score     = float(anomaly_scores[i]) if i < len(anomaly_scores) else 0.0

        # API returns margins, not absolute bounds — convert
        upper_bound = (expected + upper_m) if (expected and upper_m) else None
        lower_bound = (expected - lower_m) if (expected and lower_m) else None

        all_results.append(Row(
            product_id      = str(product_id),
            store_id        = str(store_id),
            date            = ts_row["date"],
            hour            = int(ts_row["hour"]),
            total_quantity  = float(ts_row["total_quantity"]),
            expected_value  = float(expected)    if expected     else None,
            upper_bound     = float(upper_bound) if upper_bound  else None,
            lower_bound     = float(lower_bound) if lower_bound  else None,
            is_anomaly      = bool(is_anom),
            anomaly_score   = float(score),
            severity        = get_severity(score, is_anom)
        ))

    print(f"  ✅ {product_id}/{store_id} — {len(ts_rows)} points processed")

print(f"\n📊 Total result rows: {len(all_results)}")

# ── 4. Define output schema ──────────────────────────────────
schema = StructType([
    StructField("product_id",     StringType(),  True),
    StructField("store_id",       StringType(),  True),
    StructField("date",           DateType(),    True),
    StructField("hour",           IntegerType(), True),
    StructField("total_quantity", DoubleType(),  True),
    StructField("expected_value", DoubleType(),  True),
    StructField("upper_bound",    DoubleType(),  True),
    StructField("lower_bound",    DoubleType(),  True),
    StructField("is_anomaly",     BooleanType(), True),
    StructField("anomaly_score",  DoubleType(),  True),
    StructField("severity",       StringType(),  True),
])

# ── 5. Create DataFrame and write to Delta ───────────────────
if all_results:
    anomaly_df = spark.createDataFrame(all_results, schema=schema)

    anomaly_df.write \
        .format("delta") \
        .mode("overwrite") \
        .partitionBy("date") \
        .save(config.FACT_ANOMALY_PATH)

    # Quick summary
    anomaly_count = anomaly_df.filter(col("is_anomaly") == True).count()
    total_count   = anomaly_df.count()

    print(f"\n✅ fact_anomaly_scores written successfully.")
    print(f"   Total rows : {total_count}")
    print(f"   Anomalies  : {anomaly_count}")
    print(f"   Normal     : {total_count - anomaly_count}")
else:
    print("⚠️  No results to write — check API connectivity and data volume.")
