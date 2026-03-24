# Retail Lakehouse - Azure End-to-End Data Engineering Project

## Overview

This project demonstrates a **production-grade, end-to-end retail analytics platform** built on Microsoft Azure.

It goes beyond a standard data pipeline, the system helps retail managers make smart decisions **during the same trading day**. It ingests POS transaction data incrementally, processes it through a Medallion architecture, models it into a star schema, and extends it with an **AI intelligence layer** for anomaly detection and demand forecasting.

The architecture was deliberately designed with **FinOps awareness** - pipelines run during business hours only, job clusters auto-terminate after use, and micro-batch processing was chosen over streaming to deliver near real-time insight at a fraction of the cost.

---

## Architecture

### Services Used

| Service | Purpose |
|---|---|
| Azure SQL Database | Source OLTP / POS system |
| Azure Data Factory | Incremental watermark-based ingestion |
| Azure Data Lake Storage Gen2 | Bronze, Silver, Gold storage |
| Azure Databricks | Auto Loader, Delta Lake transformations, AI models |
| Azure Anomaly Detector | AI : real-time anomaly detection |
| Prophet | AI : 24-hour demand forecasting |
| Power BI | DirectQuery dashboards, Live Anomaly Monitor + Demand Forecast |
| Azure Key Vault + Databricks Secrets | Secure credential management |
| GitHub | Version control |

---

### Data Flow

```
Azure SQL Database (POS)
        ↓
  Azure Data Factory
  (Incremental watermark — every 15 min)
        ↓
  Bronze Layer (ADLS Gen2 — Parquet)
        ↓
  Silver Layer (Databricks — Auto Loader + Delta MERGE)
        ↓
  Gold Layer (Databricks — Star Schema — Delta)
        ↓                         ↓
Azure Anomaly Detector      Prophet Forecasting
(fact_anomaly_scores)       (fact_sales_forecast)
        ↓                         ↓
          Power BI — DirectQuery
    Page 1: Live Anomaly Monitor
    Page 2: Product Deep Dive
    Page 3: Demand Forecast
```

---

## Repository Structure

```text
retail-lakehouse-project/
│
├── README.md
│
├── sql/
│   ├── 01_create_tables.sql           # Source table definitions
│   ├── 02_watermark_table.sql         # Watermark control table
│
├── adf/
│   ├── pipeline_design.md             # ADF pipeline step-by-step design
│   ├── header_incremental_query.sql   # Incremental query for transactions_header
│   ├── items_incremental_query.sql    # Incremental query for transaction_items
│
├── databricks/
│   ├── silver/
│   │   ├── config.py                          # Path and checkpoint config
│   │   ├── 01_silver_transactions_header.py   # Auto Loader + dedup + MERGE
│   │   ├── 02_silver_transaction_items.py     # Auto Loader + dedup + MERGE
│   │   ├── 03_silver_curated_join.py          # Join + data quality rules
│   │
│   ├── gold/
│   │   ├── config.py                          # Gold + AI layer paths and config
│   │   ├── 01_dim_date.py                     # Date dimension
│   │   ├── 02_dim_store.py                    # Store dimension
│   │   ├── 03_dim_product.py                  # Product dimension
│   │   ├── 04_dim_customer.py                 # Customer dimension
│   │   ├── 05_fact_sales.py                   # Central fact table
│   │   ├── 06_fact_sales_hourly.py            # Hourly aggregation (AI input)
│   │   ├── 07_anomaly_detection.py            # Azure Anomaly Detector integration
│   │   ├── 08_prophet_forecasting.py          # Prophet demand forecasting
│
├── powerbi/
│   ├── powerbi_anomaly_setup.txt      # DAX measures + anomaly dashboard guide
│   ├── powerbi_forecast_setup.txt     # DAX measures + forecast dashboard guide
│
└── architecture/
    └── architecture_overview.md       # Full architecture narrative
```

---

## Data Ingestion : Azure Data Factory

- **Watermark-based incremental extraction** : only records where `updated_at > last_watermark` are extracted on each run
- Watermark stored in ADLS as a control file : **zero write access required on the source database**
- ADF pipeline steps: Lookup → Copy Header → Copy Items → Update Watermark
- Sink format: **Parquet**, partitioned by `ingestion_date`
- Scheduled trigger: every **15 minutes during business hours only**
- Pre-check logic: if record count = 0, Copy Activity is skipped, no empty files generated

---

## Data Processing -> Azure Databricks

### Silver Layer
- **Auto Loader** (`cloudFiles`) monitors Bronze folders : detects new files instantly without ADF triggering Databricks
- **Checkpointing** ensures fault-tolerant, exactly-once processing
- **Deduplication** using `row_number()` window functions partitioned by `transaction_id` / `item_id`
- **Delta MERGE INTO** for idempotent upserts, safe to rerun, no duplicates
- Curated join of header + items with data quality filters (`quantity > 0`, `line_total >= 0`)

### Gold Layer —> Star Schema
- **fact_sales** : transaction grain (transaction_id, date, store_id, product_id, customer_id, quantity, unit_price, line_total)
- **dim_date** : year, quarter, month, weekday, week_of_year
- **dim_store** : store_id, store_name, store_city, store_state
- **dim_product** : product_id, product_name, category, subcategory, brand
- **dim_customer** : customer_id, customer_name, customer_type, loyalty_tier
- **fact_sales_hourly** : hourly aggregation per product+store (input for AI layer)

---

## AI Intelligence Layer

### 🤖 Azure Anomaly Detector (`07_anomaly_detection.py`)
- Sends `fact_sales_hourly` time series per product+store to **Azure Anomaly Detector API**
- Returns `expected_value`, `upper_bound`, `lower_bound`, `is_anomaly`, `anomaly_score` for every hour
- Severity labels mapped: High / Medium / Low / Normal
- Output: `fact_anomaly_scores` Delta table
- Advantage over simple trend formula: accounts for **seasonality, weekly cycles, and gradual trends automatically** - no false positives for products that naturally spike every Friday

### 📈 Prophet Demand Forecasting (`08_prophet_forecasting.py`)
- Trains a **Facebook Prophet model per product per store** on historical hourly sales
- Daily + weekly seasonality enabled, custom weekend seasonality added
- Forecasts next **24 hours** of demand with 95% confidence intervals
- All predictions floored at zero - no negative quantity forecasts
- Output: `fact_sales_forecast` Delta table
- Enables managers to **pre-position stock before a demand spike**, not after

---

## Reporting —> Power BI

- Connected to Gold layer via **DirectQuery** through Databricks SQL Warehouse
- Live data - no scheduled refresh needed
- **Three dashboard pages:**
  - **Live Anomaly Monitor** : ranked table of anomalies by severity with Red/Amber/Green conditional formatting
  - **Product Deep Dive** : Actual vs Expected line chart with upper/lower bounds per product
  - **Demand Forecast** : hourly forecast line chart + demand heatmap by department + Top 10 products by forecasted demand tomorrow

---

## FinOps & Cost Optimisation

| Decision | Impact |
|---|---|
| Pipeline runs business hours only | No overnight compute waste |
| Job clusters with auto-termination | No idle cluster cost |
| Micro-batch over streaming | ~3x cheaper than Event Hub streaming |
| Watermark incremental load | No full table scans |
| Skip-if-empty logic in ADF | No empty file generation |
| Parquet + Delta format | Compressed storage, fast reads |
| Auto-optimize + auto-compact | Manages small file problem automatically |

---

## Security & Governance

- API keys stored in **Azure Key Vault**, accessed via **Databricks Secret Scopes** - no hardcoded credentials anywhere
- **RBAC** applied across ADLS, Databricks, and Key Vault
- Delta Lake provides **ACID transactions** and full **audit trail via time travel**
- Watermark stored in ADLS — source database is read-only, never modified

---

## Three Architectural Approaches Documented

This project documents three approaches for different retail business contexts:

| Approach | Latency | Cost | Best For |
|---|---|---|---|
| Batch (ADF orchestrates Databricks) | Hours | 3/10 | Small local stores, daily reporting |
| Micro-Batch — **This project** | 15 minutes | 6/10 | Growing retail chains, near real-time |
| Real-Time Streaming (Event Hub) | Seconds | 9/10 | Large enterprise, flash sales, fraud detection |

---

## Key Skills Demonstrated

- Azure Data Engineering: ADF, ADLS Gen2, Databricks, Delta Lake
- Medallion Architecture: Bronze, Silver, Gold layered design
- Incremental ingestion with watermark strategy
- Structured Streaming with Auto Loader and checkpointing
- Star schema modelling for analytical workloads
- AI integration: Azure Anomaly Detector + Prophet forecasting
- FinOps: cost-aware pipeline scheduling and cluster management
- Power BI DirectQuery with DAX measures
- Production-level security: Key Vault + Databricks Secrets

---

## Notebook Execution Order

```
Silver:  01 → 02 → 03
Gold:    01 → 02 → 03 → 04 → 05 → 06 → 07 → 08
```

Notebooks 06, 07, and 08 run after 05 - the AI layer depends on `fact_sales` and `fact_sales_hourly` being ready.

---

## Author

**Abhishek Mankar**
GitHub: [https://github.com/AbhishekMankar](https://github.com/AbhishekMankar)
