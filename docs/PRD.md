# PRD — RetailPulse: Demand Forecasting & Anomaly Detection Platform

## 1. Problem statement
Retail chains lose revenue two ways: **stockouts** (demand they couldn't fill) and **overstock** (capital tied up in unsold inventory). Most mid-size retailers still forecast demand with spreadsheets or simple moving averages, missing seasonality, substitution effects, and real-time signals like sensor-reported shelf stock. There is no self-serve view for marketers/ops teams to see *why* a forecast changed and *what to do about it*.

## 2. Goal
Build a working, end-to-end system that ingests retail sales + IoT stock-sensor data, forecasts demand per SKU/store, flags anomalies, and surfaces it all in a narrative BI dashboard — proving the full pipeline (ingest → transform → enrich → model → serve → visualize) works, not just isolated notebook demos.

## 3. Target users (personas)
- **Store Ops Manager** — wants to know "will I stock out this week?" and "what should I reorder?"
- **Marketing Analyst** — wants demand trends by category/store to plan promotions.
- **Data/ML reviewer (hiring manager)** — wants to see clean architecture, real pipelines, and measurable model performance, not just a dashboard mockup.

## 4. Scope
### In scope (MVP)
- Batch ingestion of historical sales data (CSV) + simulated real-time POS/IoT stream.
- Cleaning/joining structured sales data with unstructured product-review text.
- Lakehouse storage (raw + curated zones).
- Demand forecasting per SKU/store (XGBoost/Prophet).
- Anomaly detection on sales/stock (statistical + drift-based).
- FastAPI services exposing predictions and anomaly alerts.
- Streamlit dashboard: forecast vs actual, anomaly feed, revenue-at-risk.

### In scope (V2 / stretch)
- Kafka-based real-time streaming ingestion.
- Neo4j knowledge graph for product/store/supplier relationship features (substitution effects).
- Postgres/Snowflake warehouse layer for BI querying.
- MLflow experiment tracking + Evidently AI drift monitoring.
- Power BI dashboard as an alternative front end.
- Docker Compose multi-service deployment; AWS/Azure cloud deployment.

### Out of scope
- Multi-tenant auth/billing.
- Real production POS integration (data is public/synthetic).
- Mobile app.

## 5. Success metrics & Measured Results
| Metric | Original Target | Actual Measured Result | Status |
| :--- | :--- | :--- | :--- |
| **Forecast accuracy (XGBoost Champion)** | Outperform baseline (< 10.0 RMSE) | **61.47% Holdout MAPE** (Val: 61.16%), **3.35 RMSE**, **2.08 MAE** | **PASSED** (Outperformed Holt-Winters baseline: 73.63% MAPE, 3.36 RMSE) |
| **Data Drift Monitoring** | Automated statistical drift alerts | **PASS / WARN / FAIL Verdict**: 33.3% shift detected on 28-day holiday holdout | **PASSED** (Automated via Evidently AI) |
| **Anomaly Detection Recall** | Flag synthetic stockouts & spikes | **100% recall** on injected inventory zero-shelf drops (3/3 known stockout scenarios flagged, 31 total anomalies detected) | **PASSED** |
| **Pipeline Reliability & Idempotency** | Idempotent multi-stage execution | **36,550 lakehouse records**, **700 forecasts**, **15/15 unit/integration tests passing** | **PASSED** |
| **Knowledge Graph Scale (Neo4j)** | Relational substitution topology | **18 nodes** (10 SKUs, 5 Stores, 3 Suppliers) & **64 relationships** | **PASSED (Experimental)** |
| **Streaming Ingestion (Redpanda/Kafka)** | Real-time POS/IoT replay | **200 POS & 200 IoT events** ingested and landed into partitioned MinIO raw zones | **PASSED** |


## 6. Non-functional requirements
- Reproducible locally via Docker Compose (no cloud account required to demo core MVP).
- Cloud-agnostic where feasible: local MinIO substitutes for S3, so the same code can point at AWS S3 later.
- All secrets/API keys via `.env`, never hardcoded.
- Every service independently runnable and testable.

## 7. Risks & mitigations
| Risk | Mitigation |
|---|---|
| Scope too large for solo build | Strict MVP-first phasing in `TASKS.md`; V2 features are additive, not blocking |
| No real retail dataset | Use a public dataset (e.g., Kaggle "Store Item Demand Forecasting" / "Online Retail II") + synthetic IoT sensor generator |
| Kafka/Neo4j complexity derails timeline | Both isolated to Phase 2; MVP works without them |
| Forecast quality unclear without domain data | Report metrics honestly (MAPE, RMSE) rather than a marketing-style "% improvement" claim |
