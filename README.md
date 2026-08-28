# ⚡ RetailPulse — End-to-End Demand Forecasting & Anomaly Lakehouse

[![RetailPulse CI](https://github.com/CaptainShyamal/Retail-Pulse/actions/workflows/ci.yml/badge.svg)](https://github.com/CaptainShyamal/Retail-Pulse/actions)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB.svg?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Delta Lake](https://img.shields.io/badge/Delta_Lake-Parquet-003545.svg?logo=apachespark&logoColor=white)](https://delta.io)
[![Neo4j](https://img.shields.io/badge/Neo4j-5.19-008CC1.svg?logo=neo4j&logoColor=white)](https://neo4j.com)
[![MLflow](https://img.shields.io/badge/MLflow-Tracking-0194E2.svg?logo=mlflow&logoColor=white)](https://mlflow.org)
[![Evidently AI](https://img.shields.io/badge/Evidently_AI-Monitoring-FF5722.svg)](https://evidentlyai.com)

**RetailPulse** is an enterprise-grade retail demand forecasting and inventory intelligence platform. It ingests batch sales transactions, real-time POS streams, and IoT shelf-stock telemetry; enriches and aggregates records into a curated Delta Lake lakehouse; constructs a Neo4j Knowledge Graph for product substitutions; trains gradient-boosted demand forecasting models (XGBoost & Prophet); detects inventory anomalies and stockouts; and exposes operational intelligence via independent FastAPI microservices, an interactive animated Streamlit dashboard, and Power BI.

---

## 🏛️ System Architecture & Dual Execution Modes

```mermaid
flowchart TD
    subgraph Pipeline A: Production / Batch ML Pipeline
        A1[Historical Sales CSVs] --> B1[ingestion/batch_loader.py]
        A2[IoT Shelf Sensor Generator] --> B1
        A3[Live POS & IoT Simulator] --> B2[ingestion/stream_producer.py]
        B2 -->|Kafka Topics: pos-events, iot-stock-events| B3[Redpanda / Kafka Broker]
        B3 --> B4[ingestion/stream_consumer.py]
        B1 -->|Raw Partitioned CSVs| C1[(MinIO S3 Raw Zone)]
        B4 -->|Micro-Batches| C1
        C1 --> D1[transform/spark_jobs/clean_join.py]
        C1 --> D2[transform/spark_jobs/sentiment_feature.py]
        D1 & D2 --> C2[(Delta Lake Curated Zone: sales_daily.parquet)]
        C2 --> D3[transform/data_quality.py]
        C2 --> E1[graph/load_graph.py]
        E1 --> E2[(Neo4j Knowledge Graph)]
        E2 -->|SOLD_AT, SUBSTITUTE_FOR, SUPPLIED_BY| E3[graph/graph_features.py]
        E3 -->|Point-in-Time Lag Guard| C2
        C2 --> F1[modeling/train_xgboost.py]
        C2 --> F2[modeling/train_prophet.py]
        C2 --> F3[modeling/anomaly_detection.py]
        F1 & F2 --> F4[modeling/backtest.py]
        F1 & F2 --> F5[(MLflow Experiment Tracking)]
        C2 --> F6[modeling/drift_monitor.py]
        F6 -->|Statistical Tests| F7[reports/drift_report.html]
        F1 & F3 --> G1[(PostgreSQL Warehouse)]
        G1 --> H1[FastAPI Prediction Service :8001]
        G1 --> H2[FastAPI Anomaly Service :8002]
        G1 --> H3[FastAPI Ingestion Service :8003]
        G1 --> I2[Power BI DirectQuery]
    end

    subgraph Pipeline B: Interactive Streamlit Dashboard (In-Memory)
        U1[User CSV / Excel Upload] --> U2[dashboard/app.py:process_uploaded_file]
        U2 --> U3[In-Memory Pandas Data Engine]
        U3 --> U4[Dynamic Seasonal 14-Day Forecast Generator]
        U3 --> U5[Dynamic Stockout & Anomaly Triage Engine]
        U4 & U5 --> U6[Animated Streamlit Executive Dashboard :8501]
    end
```

---

## 📊 Measured Benchmark Performance

| Evaluation Metric | Baseline (Seasonal Holt-Winters) | Production Champion (XGBoost) | Experimental (Graph XGBoost) |
| :--- | :--- | :--- | :--- |
| **Holdout MAPE (28 Days)** | 73.63% | **61.47%** (12.16 pp lower) | 62.01% |
| **Validation MAPE** | 71.20% | **61.16%** | 61.16% |
| **Holdout RMSE** | 3.36 units | **3.35 units** | **3.33 units** |
| **Mean Absolute Error (MAE)** | 2.50 units | **2.08 units** | **2.08 units** |
| **Drift Monitoring Verdict** | — | **PASS / Evaluated** | Evaluated on Out-of-Sample |

---

## ✨ Key Features

1. **Dual Execution Pipelines:**
   - **Production Batch Pipeline:** S3/MinIO ingestion, Delta Lake persistence, MLflow experiment tracking, and FastAPI microservices.
   - **Interactive BI Dashboard:** Drag-and-drop Excel/CSV parsing, instant schema normalization, INR (₹) turnover calculation, and in-memory time-series projection.
2. **Moving Graph Animations & Interactive Rollouts:**
   - Interactive Plotly controls (`▶ Play Forecast Rollout`) dynamically draw forward 14-day forecasts day-by-day with animated confidence bounds (`80% Prediction Band`).
   - Smooth Plotly transitions on filter changes without destroying the chart canvas.
   - Pulsing telemetry radar badges indicating active stream inference.
3. **Rigorous Anomaly Triage:**
   - Strict separation between `stockout` (depleted inventory) and `demand_spike` (surge anomalies).
   - Current active stockout alerts strictly evaluate the latest chronological record per `(store_id, sku)` pair.
4. **Machine Learning & MLOps:**
   - Autoregressive 28-day lag features, rolling statistics, calendar seasonality, shelf-stock signals, and customer sentiment NLP.
   - Out-of-sample holdout backtesting and Evidently AI distribution drift monitoring.
5. **Knowledge Graph Features:**
   - Neo4j graph modeling store-product hierarchies, supplier dependencies, and substitute availability.

---

## 📁 Repository Layout

```
Retail-Pulse/
├── docker-compose.yml         # Local MinIO, Postgres, Redpanda, Neo4j infrastructure
├── Makefile                   # Unified command runner for all pipeline stages
├── requirements.txt           # Python dependency manifests
├── .env.example               # Template environment configuration
│
├── data/
│   ├── raw_sample/            # Seed sales and review text datasets
│   ├── curated/               # Delta Lake curated Parquet files
│   ├── predictions/           # Model forecasts and anomaly parquet files
│   └── mlruns/                # Local MLflow experiment store
│
├── ingestion/                 # Batch and streaming ingestion pipelines
│   ├── batch_loader.py        # Date-partitioned MinIO raw zone loader
│   ├── iot_generator.py       # IoT shelf-stock simulator with stockout injection
│   ├── stream_producer.py     # Kafka/Redpanda live event replay producer
│   └── stream_consumer.py     # Streaming micro-batch consumer
│
├── transform/                 # Lakehouse transformation
│   ├── spark_jobs/clean_join.py
│   ├── spark_jobs/sentiment_feature.py
│   └── data_quality.py        # Automated schema and null data quality gate
│
├── graph/                     # Neo4j Knowledge Graph enrichment
│   ├── schema.cypher          # Product, Store, Supplier constraints & relationships
│   ├── load_graph.py          # Idempotent Cypher MERGE graph loader
│   └── graph_features.py      # Point-in-time co-stock & substitute availability features
│
├── modeling/                  # ML demand forecasting & MLOps
│   ├── train_prophet.py       # Additive seasonal baseline with MLflow logging
│   ├── train_xgboost.py       # Primary GBDT model with lag/shelf/sentiment features
│   ├── anomaly_detection.py   # Rolling z-score & shelf-stock cross check
│   ├── backtest.py            # 28-day holdout backtesting engine
│   ├── drift_monitor.py       # Evidently AI distribution drift monitor
│   └── mlflow_utils.py        # Standardized local MLflow tracking helpers
│
├── warehouse/                 # Relational PostgreSQL warehouse layer
│   └── load_warehouse.py      # Idempotent Lakehouse-to-Warehouse synchronization
│
├── services/                  # FastAPI microservices
│   ├── prediction_service/    # Forecast endpoints (Port 8001)
│   ├── anomaly_service/       # Anomaly alerts & ACK endpoints (Port 8002)
│   └── ingestion_service/     # Ingestion trigger endpoints (Port 8003)
│
├── dashboard/                 # Streamlit operational dashboard (Port 8501)
│   ├── app.py                 # Multi-page executive UI + Animated Forecast Explorer
│   └── styles.py              # Modern dark-mode styling tokens & micro-animations
│
├── reports/                   # Generated evaluation reports
│   ├── backtest.md            # Detailed per-SKU backtest accuracy report
│   ├── drift_report.html      # Interactive Evidently AI drift visualization
│   └── drift_summary.json     # Machine-readable drift audit trail
│
├── tests/                     # Comprehensive pytest test suite (15 tests)
│   ├── test_ingestion.py
│   ├── test_services.py
│   ├── test_streaming.py
│   ├── test_graph.py
│   └── test_monitoring.py
│
└── docs/                      # Technical documentation
    ├── PRD.md                 # Product requirements & success metrics
    ├── IMPLEMENTATION.md      # Data contracts & architectural details
    ├── API_REFERENCE.md       # Environment variables & endpoint references
    ├── POWERBI_SETUP.md       # Power BI Desktop connection & DAX guide
    └── CLOUD_DEPLOYMENT.md    # AWS Cloud deployment & S3/RDS migration guide
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.11+ installed
- Docker & Docker Compose running

### 2. Configure Environment & Launch Docker Services
```bash
cp .env.example .env
docker compose up -d
```
Active local infrastructure:
- **MinIO S3 Console**: [http://localhost:9001](http://localhost:9001) (`retailpulse` / `changeme123`)
- **PostgreSQL Warehouse**: `localhost:5432` (`retailpulse` / `changeme123`)
- **Redpanda Streaming Bus**: `localhost:9092`
- **Neo4j Graph Browser**: [http://localhost:7474](http://localhost:7474) (`neo4j` / `changeme123`)

### 3. Run Entire End-to-End Pipeline
Execute all 8 stages with a single command:
```bash
make run-all
```
This automatically executes:
1. **Ingestion**: Raw batch sales + IoT synthetic telemetry generation.
2. **Lakehouse Transform**: Data cleaning, sentiment features, and data quality gate.
3. **Knowledge Graph**: Neo4j node/edge load and point-in-time feature extraction.
4. **ML Modeling**: Prophet baseline and XGBoost training with MLflow tracking.
5. **Backtesting**: 28-day out-of-sample holdout accuracy evaluation.
6. **Drift Monitoring**: Evidently AI statistical drift evaluation against holdout.
7. **Warehouse Sync**: PostgreSQL table upsert with schema comments.
8. **Automated Tests**: Unit and integration test suite.

### 4. Launch Dashboard & UIs
```bash
# Launch Streamlit Executive Dashboard (Port 8501)
make dashboard

# Launch MLflow Experiment Tracking UI (Port 5000)
make mlflow-ui
```

---

## 🛠️ Makefile Command Reference

| Target | Description |
| :--- | :--- |
| `make ingest` | Runs batch loader and synthetic IoT sensor generator |
| `make stream-produce` | Replays live POS and IoT telemetry events to Kafka/Redpanda |
| `make stream-consume` | Consumes streaming micro-batches and lands them to MinIO |
| `make transform` | Executes data cleaning, joins, and data quality gate |
| `make graph-load` | Idempotently populates Neo4j Knowledge Graph |
| `make graph-features` | Computes point-in-time co-stock and substitute availability features |
| `make model` | Trains Prophet, XGBoost, and anomaly detection models |
| `make backtest` | Evaluates holdout performance and generates `reports/backtest.md` |
| `make drift-report` | Runs Evidently AI drift monitoring and outputs `reports/drift_report.html` |
| `make warehouse` | Syncs curated lakehouse tables to PostgreSQL warehouse |
| `make mlflow-ui` | Launches local MLflow tracking UI on port 5000 |
| `make test` | Executes full pytest test suite |
| `make dashboard` | Launches Streamlit operational intelligence dashboard |
| `make run-all` | Executes the complete end-to-end data, ML, and MLOps pipeline |

---

## 🧪 Automated Testing

Run the full test suite with verbose reporting:
```bash
pytest tests/ -v
```
**Test Coverage Includes:**
- `test_raw_sales_data_contract` & `test_raw_reviews_data_contract`: Raw zone contracts
- `test_synthetic_anomalies_logged`: Ground-truth anomaly generation verification
- `test_prediction_service_health`, `test_anomaly_service_health`, `test_ingestion_service_health`: FastAPI endpoints
- `test_pos_event_schema_contract` & `test_iot_event_schema_contract`: Streaming schemas
- `test_schema_cypher_syntax_and_constraints`: Cypher schema integrity
- `test_point_in_time_graph_features_data_leakage_guard`: Zero target leakage verification
- `test_neo4j_live_connection_and_node_counts`: Live Neo4j database verification
- `test_mlflow_experiment_logging`: MLflow run and artifact logging
- `test_evidently_drift_monitoring_contract`: Drift monitoring execution and verdicts
- `test_warehouse_sync_idempotency`: Invariant table row counts across re-runs

---

## 📄 License
This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
