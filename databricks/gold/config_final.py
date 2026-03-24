# ── Existing paths ──────────────────────────────────────────────
SILVER_PATH           = "/mnt/retail/silver/silver_transactions/"
GOLD_BASE_PATH        = "/mnt/retail/gold/"

DIM_DATE_PATH         = GOLD_BASE_PATH + "dim_date/"
DIM_STORE_PATH        = GOLD_BASE_PATH + "dim_store/"
DIM_PRODUCT_PATH      = GOLD_BASE_PATH + "dim_product/"
DIM_CUSTOMER_PATH     = GOLD_BASE_PATH + "dim_customer/"
FACT_SALES_PATH       = GOLD_BASE_PATH + "fact_sales/"

# ── Anomaly Detector paths ───────────────────────────────────────
FACT_SALES_HOURLY_PATH  = GOLD_BASE_PATH + "fact_sales_hourly/"
FACT_ANOMALY_PATH       = GOLD_BASE_PATH + "fact_anomaly_scores/"

# ── Azure Anomaly Detector config ────────────────────────────────
ANOMALY_DETECTOR_ENDPOINT = "https://<your-resource-name>.cognitiveservices.azure.com/"
ANOMALY_DETECTOR_API_KEY  = dbutils.secrets.get(scope="retail-secrets", key="anomaly-detector-key")
ANOMALY_API_VERSION       = "v1.0"
ANOMALY_GRANULARITY       = "hourly"
ANOMALY_SENSITIVITY       = 95

# ── Prophet Forecasting paths ────────────────────────────────────
FACT_FORECAST_PATH      = GOLD_BASE_PATH + "fact_sales_forecast/"
MODEL_STORE_PATH        = "/mnt/retail/models/prophet/"

# ── Prophet config ───────────────────────────────────────────────
FORECAST_HOURS_AHEAD    = 24      # how many hours into future to forecast
MIN_TRAINING_ROWS       = 48      # minimum data points needed to train
FORECAST_INTERVAL_WIDTH = 0.95    # confidence interval width (95%)
