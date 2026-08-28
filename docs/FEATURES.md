# Features — RetailPulse

Legend: **[MVP]** required for v1 · **[V2]** stretch, additive · **[V3]** optional polish

## F1. Data ingestion
- **[MVP]** Batch loader for historical sales CSV into raw zone.
  - *Acceptance*: running `make ingest-batch` lands partitioned Parquet/CSV files in MinIO raw zone, idempotent on re-run.
- **[MVP]** Synthetic IoT stock-sensor generator (simulates shelf-level stock pings).
  - *Acceptance*: generator produces N events/sec with configurable stockout scenarios for demo purposes.
- **[V2]** Kafka streaming ingestion (`pos-events`, `iot-stock-events` topics) with a consumer landing job.
  - *Acceptance*: producer publishes events; consumer lands micro-batches into raw zone within a configurable interval.

## F2. Data transformation
- **[MVP]** PySpark job cleans and joins structured sales data.
  - *Acceptance*: nulls handled per documented rule, duplicate transactions removed, schema validated against `IMPLEMENTATION.md` contract.
- **[MVP]** Unstructured review-text sentiment feature.
  - *Acceptance*: sentiment score column present in curated table for every SKU with review data; missing reviews default to neutral, documented.
- **[MVP]** Delta Lake curated zone with ACID writes.
  - *Acceptance*: curated table supports time-travel query (`DESCRIBE HISTORY`) and schema enforcement rejects malformed writes.

## F3. Knowledge graph enrichment
- **[V2]** Neo4j graph of product/store/supplier relationships.
  - *Acceptance*: graph loadable from curated data; Cypher query returns "frequently co-stocked" and "substitute" pairs.
- **[V2]** Graph-derived features joined back into modeling table.
  - *Acceptance*: at least 2 graph-derived columns present and used by the model; feature importance report shows non-zero contribution.

## F4. Forecasting & anomaly detection
- **[MVP]** Baseline seasonality forecast (Prophet) per SKU/store.
- **[MVP]** Primary forecast model (XGBoost) with engineered features, beats baseline on held-out MAPE.
  - *Acceptance*: backtest report (`reports/backtest.md`) shows MAPE/RMSE for both models side by side.
- **[MVP]** Anomaly detection on sales/stock series (rolling z-score / statistical control limits).
  - *Acceptance*: known synthetic anomalies (injected into test data) are flagged with documented precision/recall.
- **[V2]** MLflow experiment tracking for all model runs.
- **[V2]** Evidently AI drift check comparing recent predictions vs training distribution, on a schedule.

## F5. Serving layer
- **[MVP]** `prediction-service` FastAPI: forecast endpoint by SKU/store with confidence interval.
- **[MVP]** `anomaly-service` FastAPI: list + acknowledge anomalies.
- **[MVP]** `ingestion-service` FastAPI: trigger/health endpoints.
  - *Acceptance*: all 3 services pass `docker compose up` and respond to `/health` with 200.
- **[V2]** Services containerized independently, orchestrated via Docker Compose with restart policies.

## F6. Warehouse & BI
- **[V2]** Curated predictions pushed to Postgres (local) / Snowflake (cloud).
  - *Acceptance*: warehouse table refreshed on each model run; query returns latest forecast per SKU/store in <1s locally.
- **[V3]** Power BI dashboard connected to warehouse as an alternate front end.

## F7. Dashboard (Streamlit) — see `UI_DESIGN.md` for visual spec
- **[MVP]** Overview page: stat cards (Total Forecasted Demand, Total Actual Sales, Open Anomalies), trend chart with Daily/Weekly/Monthly toggle.
- **[MVP]** Forecast Explorer: pick SKU/store, see forecast vs actual, confidence band.
- **[MVP]** Anomaly Feed: list of flagged anomalies with severity, type, and "why" explanation.
- **[V2]** Demand breakdown donut (by category) + Top Products/Stores list with mini trend bars (mirrors reference screenshot's "Demographic" + "Top Channels" panels).
- **[V3]** Knowledge Graph Explorer: visualize product substitution graph interactively.

## F8. Ops / quality
- **[MVP]** `.env`-based config, no secrets committed.
- **[MVP]** README with local run instructions (`docker compose up`, seed data, run dashboard).
- **[V2]** Basic CI (lint + unit tests) via GitHub Actions.
- **[V2]** Structured logging across all services.
