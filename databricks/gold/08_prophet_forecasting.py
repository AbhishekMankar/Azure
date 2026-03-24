# ============================================================
# Notebook: 08_prophet_forecasting
# Layer:    Gold (AI Extension)
# Purpose:  Train a Facebook Prophet model per product+store
#           using fact_sales_hourly as training data.
#           Forecast the next 24 hours of demand.
#           Write results to fact_sales_forecast Delta table.
#
# Input:    fact_sales_hourly  (product_id, store_id, date,
#                               hour, total_quantity)
#
# Output:   fact_sales_forecast columns:
#           product_id, store_id, forecast_timestamp,
#           forecast_date, forecast_hour,
#           forecasted_quantity, lower_bound, upper_bound,
#           model_trained_at, training_rows_used
#
# Run after: 06_fact_sales_hourly.py
# ============================================================

# ── Install Prophet (run once per cluster) ───────────────────
# In Databricks, install via cluster libraries:
#   Libraries → Install New → PyPI → prophet
# Or uncomment the line below to install in-notebook:
# %pip install prophet


from prophet import Prophet
from datetime import datetime, timedelta

import pandas as pd
from pyspark.sql import Row
from pyspark.sql.functions import col, lit, current_timestamp
from pyspark.sql.types import (
    StructType, StructField,
    StringType, IntegerType, DoubleType, TimestampType, DateType
)
import config

print("✅ Libraries loaded successfully.")


# ============================================================
# HELPER: Build a datetime from date + hour
# ============================================================
def build_datetime(date_val, hour_val):
    return datetime(
        date_val.year,
        date_val.month,
        date_val.day,
        int(hour_val)
    )


# ============================================================
# HELPER: Train Prophet and forecast next N hours
# ============================================================
def train_and_forecast(pdf, product_id, store_id):
    """
    pdf          : pandas DataFrame with columns [ds, y]
                   ds = datetime, y = total_quantity
    product_id   : str
    store_id     : str

    Returns      : list of result dicts, or empty list on failure
    """

    # ── Validate minimum data ────────────────────────────────
    if len(pdf) < config.MIN_TRAINING_ROWS:
        print(f"  ⏭  Skipping {product_id}/{store_id} "
              f"— only {len(pdf)} rows (need {config.MIN_TRAINING_ROWS})")
        return []

    try:
        # ── Initialise Prophet ───────────────────────────────
        # daily_seasonality=True  : captures intraday hourly patterns
        # weekly_seasonality=True : captures Mon-Sun differences
        # yearly_seasonality=False: not enough data for yearly patterns
        #                           in most retail scenarios
        model = Prophet(
            daily_seasonality  = True,
            weekly_seasonality = True,
            yearly_seasonality = False,
            interval_width     = config.FORECAST_INTERVAL_WIDTH,
            changepoint_prior_scale = 0.05  # controls trend flexibility
                                            # lower = more stable baseline
        )

        # ── Add retail-specific seasonalities ────────────────
        # Weekend effect — retail behaves very differently Sat/Sun
        model.add_seasonality(
            name   = "weekend",
            period = 7,
            fourier_order = 3
        )

        # ── Fit the model ────────────────────────────────────
        model.fit(pdf)

        # ── Build future dataframe ───────────────────────────
        # Prophet needs a dataframe with future timestamps
        future = model.make_future_dataframe(
            periods = config.FORECAST_HOURS_AHEAD,
            freq    = "H",          # H = hourly frequency
            include_history = False  # only return future predictions
        )

        # ── Generate forecast ────────────────────────────────
        forecast = model.predict(future)

        # ── Parse results ────────────────────────────────────
        training_rows = len(pdf)
        trained_at    = datetime.now()
        results       = []

        for _, row in forecast.iterrows():
            ts            = row["ds"].to_pydatetime()
            predicted_qty = max(0.0, float(row["yhat"]))       # floor at 0
            lower         = max(0.0, float(row["yhat_lower"])) # floor at 0
            upper         = max(0.0, float(row["yhat_upper"])) # floor at 0

            results.append({
                "product_id"          : str(product_id),
                "store_id"            : str(store_id),
                "forecast_timestamp"  : ts,
                "forecast_date"       : ts.date(),
                "forecast_hour"       : int(ts.hour),
                "forecasted_quantity" : predicted_qty,
                "lower_bound"         : lower,
                "upper_bound"         : upper,
                "model_trained_at"    : trained_at,
                "training_rows_used"  : training_rows
            })

        print(f"  ✅ {product_id}/{store_id} — "
              f"trained on {training_rows} rows, "
              f"forecasted {len(results)} hours ahead")
        return results

    except Exception as e:
        print(f"  ❌ Error for {product_id}/{store_id}: {e}")
        return []


# ============================================================
# MAIN
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

print(f"\n📦 Training Prophet models for {len(combos)} "
      f"product+store combinations...\n")

# ── 3. Train model and forecast for each combination ─────────
all_forecasts = []

for row in combos:
    product_id = row["product_id"]
    store_id   = row["store_id"]

    # Pull this combination's time series into pandas
    ts_pdf = (
        hourly_df
        .filter(
            (col("product_id") == product_id) &
            (col("store_id")   == store_id)
        )
        .orderBy("date", "hour")
        .select("date", "hour", "total_quantity")
        .toPandas()
    )

    # Build Prophet-required columns: ds (datetime) and y (value)
    ts_pdf["ds"] = ts_pdf.apply(
        lambda r: build_datetime(r["date"], r["hour"]), axis=1
    )
    ts_pdf["y"] = ts_pdf["total_quantity"].astype(float)
    ts_pdf = ts_pdf[["ds", "y"]].sort_values("ds").reset_index(drop=True)

    # Train and forecast
    results = train_and_forecast(ts_pdf, product_id, store_id)
    all_forecasts.extend(results)

print(f"\n📊 Total forecast rows generated: {len(all_forecasts)}")


# ── 4. Define output schema ──────────────────────────────────
schema = StructType([
    StructField("product_id",           StringType(),    True),
    StructField("store_id",             StringType(),    True),
    StructField("forecast_timestamp",   TimestampType(), True),
    StructField("forecast_date",        DateType(),      True),
    StructField("forecast_hour",        IntegerType(),   True),
    StructField("forecasted_quantity",  DoubleType(),    True),
    StructField("lower_bound",          DoubleType(),    True),
    StructField("upper_bound",          DoubleType(),    True),
    StructField("model_trained_at",     TimestampType(), True),
    StructField("training_rows_used",   IntegerType(),   True),
])


# ── 5. Create Spark DataFrame ────────────────────────────────
if all_forecasts:
    forecast_df = spark.createDataFrame(all_forecasts, schema=schema)

    # ── 6. Write to Gold Delta table ─────────────────────────
    forecast_df.write \
        .format("delta") \
        .mode("overwrite") \
        .partitionBy("forecast_date") \
        .save(config.FACT_FORECAST_PATH)

    print(f"\n✅ fact_sales_forecast written successfully.")
    print(f"   Products forecasted : {len(combos)}")
    print(f"   Total forecast rows : {forecast_df.count()}")
    print(f"   Forecast horizon    : {config.FORECAST_HOURS_AHEAD} hours ahead")

    # ── 7. Preview sample output ─────────────────────────────
    print("\n📋 Sample forecast output:")
    forecast_df.orderBy("product_id", "forecast_timestamp").show(10, truncate=False)

else:
    print("⚠️  No forecasts generated — check data volume in fact_sales_hourly.")
