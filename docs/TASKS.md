# Tasks — RetailPulse (phased, for Antigravity)

Each phase should end in a demoable/testable state before moving to the next. Do not start V2 phases until the MVP (Phases 0–5) runs end-to-end.

## Phase 0 — Scaffold
- [x] Initialize repo with the folder structure in `IMPLEMENTATION.md` §1.
- [x] `docker-compose.yml` with MinIO + Postgres only (Kafka/Neo4j added in later phases).
- [x] `.env.example` with all required variables (see `API_REFERENCE.md`).
- [x] Pick and download a public dataset (e.g., Kaggle "Store Item Demand Forecasting Challenge" or "Online Retail II") into `data/raw_sample/`.
- [x] README stub with "how to run locally" placeholder.

## Phase 1 — Ingestion (batch)
- [x] `ingestion/batch_loader.py`: load CSV → raw zone in MinIO, partitioned by date.
- [x] Synthetic IoT stock-sensor generator producing `raw.iot_stock_events` records, including deliberate stockout scenarios.
- [x] Unit test: loader is idempotent on re-run.

## Phase 2 — Transform (PySpark + Delta Lake)
- [x] `transform/spark_jobs/clean_join.py`: null-handling per `IMPLEMENTATION.md` rules, join sales + IoT + review sentiment.
- [x] `transform/spark_jobs/sentiment_feature.py`: HuggingFace sentiment pipeline over review text, cached.
- [x] Write `curated.sales_daily` to Delta Lake; verify with `DESCRIBE HISTORY`.
- [x] Data quality check script (row counts, null rates, schema match against contract).

## Phase 3 — Modeling
- [x] `modeling/train_prophet.py` — baseline per SKU/store.
- [x] `modeling/train_xgboost.py` — primary model with engineered features.
- [x] `modeling/backtest.py` — time-based holdout, produces `reports/backtest.md` (MAPE/RMSE comparison).
- [x] `modeling/anomaly_detection.py` — rolling z-score + shelf-stock cross-check, produces `predictions.anomaly` records.
- [x] Validate anomaly detection against the synthetic scenarios injected in Phase 1; record precision/recall.

## Phase 4 — Serving (FastAPI)
- [x] `services/prediction_service` — `GET /forecast/{store_id}/{sku}`, `GET /health`.
- [x] `services/anomaly_service` — `GET /anomalies`, `POST /anomalies/{id}/ack`, `GET /health`.
- [x] `services/ingestion_service` — `POST /ingest/batch`, `GET /health`.
- [x] Dockerfile per service; wire into `docker-compose.yml`.
- [x] Integration test: `docker compose up` → all 3 `/health` endpoints return 200.

## Phase 5 — Dashboard (MVP, Streamlit)
- [x] Build Overview page per `UI_DESIGN.md` §2 (stat cards, trend chart with Daily/Weekly/Monthly toggle, donut breakdown, top-products-at-risk list).
- [x] Build Forecast Explorer page (SKU/store picker + trend chart scoped to selection).
- [x] Build Anomaly Feed page (list + acknowledge action, calling `anomaly_service`).
- [x] Apply the dark-sidebar / lime-accent styling from `UI_DESIGN.md` §1.
- [x] **MVP checkpoint**: full pipeline runs locally via `docker compose up` + one `make` command chain (ingest → transform → model → serve → dashboard).

---
## Phase 6 — [V2] Streaming
- [x] `ingestion/stream_producer.py` — Kafka/Redpanda producer replaying historical data as live POS/IoT events.
- [x] `ingestion/stream_consumer.py` — lands micro-batches into raw zone.
- [x] Update `docker-compose.yml` with Kafka/Redpanda broker.

## Phase 7 — [V2] Knowledge graph
- [x] `graph/schema.cypher` — Product/Store/Supplier node + relationship schema.
- [x] `graph/load_graph.py` — populate Neo4j from curated data.
- [x] `graph/graph_features.py` — co-stock + substitute-available features joined back into modeling table.
- [x] Re-run backtest with graph features included; compare MAPE to Phase 3 baseline.

## Phase 8 — [V2] Warehouse + monitoring
- [x] `warehouse/load_warehouse.py` — curated + prediction tables → Postgres (local) / Snowflake (cloud-ready).
- [x] MLflow tracking wired into all training scripts; MLflow UI reachable locally.
- [x] Evidently AI drift report on a schedule (cron or manual trigger for demo).

## Phase 9 — [V3] Polish
- [x] Power BI dashboard connected to warehouse as an alternate front end (`docs/POWERBI_SETUP.md`).
- [x] Knowledge Graph Explorer UI page.
- [x] GitHub Actions CI (lint + unit tests in `.github/workflows/ci.yml`).
- [x] Cloud deployment pass (AWS S3 replaces MinIO; documented in `docs/CLOUD_DEPLOYMENT.md`).
- [x] Complete documentation & test suite passing 15/15 unit/integration tests.

## Final
- [x] Fill in real backtest numbers (MAPE/RMSE) into `PRD.md` §5 success metrics — replace placeholders with measured results.
- [x] Write the resume bullet using only metrics that were actually measured.
