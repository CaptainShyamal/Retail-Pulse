# ⚡ RetailPulse — Retail Demand Forecasting & Anomaly Detection Platform

[![Python](https://img.shields.io/badge/Python-3.11-3776AB.svg?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Delta Lake](https://img.shields.io/badge/Delta_Lake-Parquet-003545.svg?logo=apachespark&logoColor=white)](https://delta.io)
[![Neo4j](https://img.shields.io/badge/Neo4j-5.19-008CC1.svg?logo=neo4j&logoColor=white)](https://neo4j.com)
[![MLflow](https://img.shields.io/badge/MLflow-Tracking-0194E2.svg?logo=mlflow&logoColor=white)](https://mlflow.org)

An end-to-end, portfolio-grade retail demand forecasting and anomaly detection pipeline: batch + simulated streaming ingestion, a Delta Lake lakehouse, a Neo4j knowledge graph, gradient-boosted demand forecasting, statistical anomaly detection, MLOps monitoring, and a Streamlit dashboard — built to demonstrate the full data-to-decision lifecycle, not just an isolated model.

## What this is (and isn't)

This is a **single-node, local, portfolio project** built with a public/synthetic dataset — not a production system serving real stores. Every number below was actually measured on a 28-day holdout backtest; none are estimated or aspirational. See [Known Limitations](#known-limitations) for an honest accounting of what's demo-grade vs. what's solid.

## Architecture

```
Batch CSV + simulated IoT sensor stream
        │
        ▼
   Ingestion (MinIO raw zone)
        │
        ▼
   PySpark clean/join + sentiment features
        │
        ▼
   Delta Lake curated zone (sales_daily)
        │
        ├──► Neo4j knowledge graph (product/store/supplier features) [experimental]
        │
        ▼
   XGBoost / Prophet forecasting + anomaly detection
        │
        ├──► MLflow experiment tracking
        ├──► Evidently AI drift monitoring
        │
        ▼
   PostgreSQL warehouse
        │
        ▼
   FastAPI microservices (prediction / anomaly / ingestion)
        │
        ▼
   Streamlit dashboard
```

## Measured results

| Metric | Baseline (Holt-Winters) | XGBoost (production model) | Graph-enhanced XGBoost (experimental) |
|---|---|---|---|
| Holdout MAPE (28 days) | 73.63% | **61.47%** (12.16pp lower / 16.5% relative reduction) | 62.01% |
| Holdout RMSE | 3.36 | **3.35** | 3.33 |
| MAE | 2.50 | **2.08** | 2.08 |
| Anomaly detection recall | — | 100% (3/3 injected synthetic stockouts detected) | — |
| Drift monitoring | — | PASS (Evidently AI, 0/6 features drifted) | — |

The graph-enhanced model is not used in production — with only 10 SKUs and 4 substitute relationships, the knowledge graph is too sparse to reliably improve forecasts yet. That result is reported honestly in [`reports/backtest.md`](reports/backtest.md) rather than cherry-picked.

## Repository layout

```
retailpulse/
├── docker-compose.yml       # MinIO, Postgres, Redpanda, Neo4j (local infra)
├── Makefile                 # make run-all, make dashboard, etc.
├── .env.example
├── data/raw_sample/         # seed sales + review dataset
├── ingestion/                # batch_loader.py, iot_generator.py, stream_producer/consumer.py
├── transform/spark_jobs/     # clean_join.py, sentiment_feature.py
├── graph/                    # Neo4j schema + point-in-time feature extraction
├── modeling/                 # train_xgboost.py, train_prophet.py, anomaly_detection.py,
│                              # backtest.py, drift_monitor.py, mlflow_utils.py
├── warehouse/load_warehouse.py
├── services/                 # prediction_service, anomaly_service, ingestion_service (FastAPI)
├── dashboard/                # Streamlit app
├── reports/                  # backtest.md, drift_report.html
├── tests/                    # 15 pytest tests
└── docs/                     # PRD, architecture, implementation, API reference
```

## Quick start (local only — no cloud account required)

```bash
cp .env.example .env
docker compose up -d          # MinIO, Postgres, Redpanda, Neo4j
make run-all                  # ingest -> transform -> graph -> model -> backtest -> drift -> warehouse -> tests
make dashboard                # Streamlit UI at http://localhost:8501
```

| Service | URL |
|---|---|
| Streamlit dashboard | http://localhost:8501 |
| Prediction API | http://localhost:8001/health |
| Anomaly API | http://localhost:8002/health |
| Ingestion API | http://localhost:8003/health |
| MinIO console | http://localhost:9001 |
| Neo4j browser | http://localhost:7474 |
| MLflow UI | `make mlflow-ui` → http://localhost:5000 |

## Testing

```bash
pytest tests/ -v   # 15 tests: ingestion contracts, service health, streaming schemas,
                    # graph leakage guard, MLflow logging, drift verdicts, warehouse idempotency
```

## Known limitations

- **Single-node local deployment** — Postgres, MinIO, Neo4j, and Redpanda all run as local Docker containers, not a distributed/multi-AZ setup.
- **Synthetic dataset** — 10 SKUs, 5 stores; sensor data is generated, not from real hardware.
- **Forecast accuracy is moderate, not high** (61.47% MAPE) — expected given the small catalog and limited historical depth; documented rather than inflated.
- **Knowledge graph features are experimental**, not part of the production model, due to catalog sparsity.
- **No live/automatic ingestion trigger from the dashboard** — new data is loaded by running pipeline scripts, not by uploading a file through the UI.

## Docs

- [`docs/PRD.md`](docs/PRD.md) — requirements, goals, success metrics
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — full data flow and design decisions
- [`docs/IMPLEMENTATION.md`](docs/IMPLEMENTATION.md) — data contracts, module notes
- [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md) — endpoints, env vars, external services
- [`docs/UI_DESIGN.md`](docs/UI_DESIGN.md) — dashboard design spec
- [`reports/backtest.md`](reports/backtest.md) — full per-SKU accuracy report

## License

MIT — see [LICENSE](LICENSE).
