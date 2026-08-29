<div align="center">

# ⚡ RetailPulse
### Intelligent Retail Demand Forecasting & Anomaly Detection Lakehouse Platform

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io/)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB.svg?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688.svg?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Apache Spark](https://img.shields.io/badge/Apache_Spark-3.5-E25A1C.svg?style=flat&logo=apachespark&logoColor=white)](https://spark.apache.org/)
[![Delta Lake](https://img.shields.io/badge/Delta_Lake-Parquet-003545.svg?style=flat&logo=delta&logoColor=white)](https://delta.io)
[![XGBoost](https://img.shields.io/badge/XGBoost-2.0-EB5424.svg?style=flat&logo=xgboost&logoColor=white)](https://xgboost.readthedocs.io/)
[![Neo4j](https://img.shields.io/badge/Neo4j-5.19-008CC1.svg?style=flat&logo=neo4j&logoColor=white)](https://neo4j.com)
[![MLflow](https://img.shields.io/badge/MLflow-Tracking-0194E2.svg?style=flat&logo=mlflow&logoColor=white)](https://mlflow.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

<p align="center">
  <b>An end-to-end, production-grade retail intelligence platform combining real-time IoT streaming, Delta Lake lakehouse engineering, gradient-boosted demand forecasting, graph relational intelligence, and automated drift monitoring.</b>
</p>

---

[🚀 Live Demo](#-live-demo--deployment) • [📊 Architecture](#-system-architecture) • [✨ Key Features](#-key-features) • [📈 Benchmark Results](#-measured-results) • [🛠️ Tech Stack](#️-tech-stack) • [⚡ Quickstart](#-quickstart-guide)

---

</div>

## 📌 Executive Summary

**RetailPulse** is an enterprise-scale data science and MLOps system built to tackle real-world supply chain challenges: stockout prevention, automated demand forecasting, data drift detection, and inventory anomaly diagnosis. 

Instead of an isolated machine learning notebook, RetailPulse provides the **complete data-to-decision lifecycle**: from raw IoT sensor streams and Delta Lake curation to automated backtesting, FastAPI microservice serving, and an interactive executive command center.

---

## 📊 System Architecture

```
                                  RETAILPULSE DATA PIPELINE
                                  
  [ Batch Sales CSV ]        [ Simulated IoT Sensors ]
           │                            │
           ▼                            ▼
  [ MinIO S3 Raw Storage ]     [ Redpanda / Kafka Stream ]
           │                            │
           └──────────────┬─────────────┘
                          ▼
            [ PySpark Transformation Engine ]
            • Data Cleaning & Standardization
            • Temporal & Rolling Aggregations
            • Sentiment & Customer Feedback Features
                          │
                          ▼
             [ Delta Lake Curated Zone ]
                 (ACID / Time-Travel)
                          │
            ┌─────────────┴─────────────┐
            ▼                           ▼
  [ Neo4j Knowledge Graph ]   [ ML Pipeline (XGBoost / Prophet) ]
  • Store-Product Substitutes • Automated 28-day Holdout Backtest
  • Graph Feature Embeddings  • Statistical Anomaly Detection
            │                           │
            └─────────────┬─────────────┘
                          ▼
               [ MLOps & Observability ]
               • MLflow Experiment Tracking
               • Evidently AI Data Drift Audits
                          │
                          ▼
             [ PostgreSQL Data Warehouse ]
                          │
            ┌─────────────┴─────────────┐
            ▼                           ▼
  [ FastAPI Microservices ]    [ Executive Streamlit Dashboard ]
  • Prediction API (:8001)     • Multi-Store Demand Heatmaps
  • Anomaly API    (:8002)     • Dynamic CSV Upload & Retraining
  • Ingestion API  (:8003)     • Real-time Inventory Alerts
```

---

## ✨ Key Features

- **⚡ Multi-Tier Demand Forecasting:** Production XGBoost model incorporating calendar cycles, rolling lag statistics, price elasticity, and promotional impacts.
- **🛡️ Statistical Anomaly Detection:** Real-time z-score and moving-average anomaly engine with **100% recall** on simulated stockouts and sensor disruptions.
- **🕸️ Graph Relational Features:** Neo4j knowledge graph modeling product substitution networks, supplier dependencies, and regional cross-store demand.
- **📦 Modern Lakehouse Architecture:** Delta Lake storage layer on MinIO S3 providing ACID guarantees and schema enforcement for raw and curated data.
- **📈 Comprehensive MLOps:** Integrated **MLflow** parameter/artifact logging paired with **Evidently AI** continuous feature drift monitoring.
- **🖥️ Executive Command Center:** Polished high-contrast Streamlit interface supporting multi-store telemetry, custom dynamic dataset uploads, and on-the-fly model retraining.

---

## 📈 Measured Results

All metrics are derived from an un-cherrypicked **28-day holdout backtest**:

| Model / Pipeline Stage | Holdout MAPE (28-Day) | RMSE | MAE | Operational Note |
| :--- | :---: | :---: | :---: | :--- |
| **Baseline (Holt-Winters)** | 73.63% | 3.36 | 2.50 | Standard statistical baseline |
| **XGBoost (Production)** | **61.47%** | **3.35** | **2.08** | **16.5% relative error reduction** |
| **Graph-Enhanced XGBoost** | 62.01% | 3.33 | 2.08 | Experimental (evaluates substitute density) |
| **Anomaly Detection Engine**| — | — | — | **100% recall** (3/3 synthetic stockouts detected) |
| **Evidently AI Drift Audit**| — | — | — | **PASS** (0/6 features drifted) |

*Full evaluation reports and per-SKU metrics available in [`reports/backtest.md`](reports/backtest.md).*

---

## 🛠️ Tech Stack

| Category | Technologies |
| :--- | :--- |
| **Core & APIs** | Python 3.11, FastAPI, Uvicorn, Pydantic, Requests |
| **Data Engineering** | Apache Spark (PySpark), Delta Lake, PostgreSQL, MinIO (S3-Compatible) |
| **Streaming & Graph** | Redpanda / Apache Kafka, Neo4j Graph Database, Cypher |
| **Machine Learning** | XGBoost, Facebook Prophet, Scikit-Learn, Statsmodels, Scipy |
| **MLOps & Monitoring** | MLflow, Evidently AI, Pytest |
| **Frontend & UI** | Streamlit, Plotly Express & Graph Objects, Custom CSS Theme |
| **Infrastructure** | Docker, Docker Compose, Make |

---

## 📁 Repository Layout

```text
Retail-Pulse/
├── dashboard/                  # Streamlit Interactive Web Application
│   ├── app.py                  # Main Dashboard Entry Point
│   └── styles.py               # Dark Mode & High-Contrast Design System
├── services/                   # Production FastAPI Microservices
│   ├── prediction_service/     # Inference & Demand Forecasting API
│   ├── anomaly_service/        # Anomaly Detection & Incident API
│   ├── ingestion_service/      # Ingestion Health & Webhook API
│   └── common/                 # Shared Data Schemas & Utilities
├── modeling/                   # Machine Learning & MLOps Pipelines
│   ├── train_xgboost.py        # Gradient Boosted Model Training
│   ├── train_prophet.py        # Bayesian Additive Time-Series Model
│   ├── anomaly_detection.py    # Statistical & Rule-Based Anomaly Engine
│   ├── backtest.py             # 28-day Sliding Window Evaluator
│   └── drift_monitor.py        # Evidently AI Data Drift Audits
├── transform/spark_jobs/       # PySpark ETL & Feature Engineering
│   ├── clean_join.py           # Spark Cleaning, Deduping & Joins
│   └── sentiment_feature.py    # Sentiment Extraction Pipeline
├── graph/                      # Neo4j Graph Intelligence
│   ├── schema.py               # Graph Constraints & Schema Setup
│   └── feature_extractor.py    # Graph Embeddings & Substitute Extraction
├── ingestion/                  # Streaming & Batch Data Ingestion
│   ├── batch_loader.py         # S3 Raw Zone Uploader
│   └── iot_generator.py        # IoT Sensor Telemetry Simulator
├── warehouse/                  # PostgreSQL Warehouse Loaders
├── data/raw_sample/            # Seed Sales, Inventory & Review Datasets
├── tests/                      # Automated Unit & Contract Test Suite
├── docker-compose.yml          # Containerized Multi-Service Infrastructure
├── requirements.txt            # Python Dependencies
└── Makefile                    # Developer Workflow Automation
```

---

## ⚡ Quickstart Guide

### Option 1: Local Development with Docker

1. **Clone the repository:**
   ```bash
   git clone https://github.com/CaptainShyamal/Retail-Pulse.git
   cd Retail-Pulse
   ```

2. **Set up environment:**
   ```bash
   cp .env.example .env
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Start local infrastructure (Docker Compose):**
   ```bash
   docker compose up -d
   ```

4. **Run the full end-to-end pipeline:**
   ```bash
   make run-all
   ```

5. **Launch the Dashboard:**
   ```bash
   make dashboard
   # App will be live at http://localhost:8501
   ```

---

### Option 2: Live Deployment on Streamlit Community Cloud (100% Free)

To deploy this interactive dashboard online for free:

1. **Fork or Push** this repository to your GitHub account.
2. Navigate to **[share.streamlit.io](https://share.streamlit.io)** and log in with GitHub.
3. Click **"New app"** and configure:
   - **Repository:** `Your-Username/Retail-Pulse`
   - **Branch:** `main`
   - **Main file path:** `dashboard/app.py`
4. Click **Deploy**! 🚀

---

## 🧪 Testing & Validation

The codebase includes comprehensive unit, integration, and data contract tests:

```bash
pytest tests/ -v
```

**Test Coverage Includes:**
- Ingestion data contracts and schema validation
- FastAPI microservice health checks and prediction payloads
- Streaming schema parsing and sensor boundary limits
- Knowledge graph temporal leakage prevention
- MLflow parameter logging & Evidently AI drift verdict assertions

---

## 📖 Documentation Index

- 📘 [Product Requirements Document (PRD)](docs/PRD.md)
- 📐 [System Architecture & Data Flows](docs/ARCHITECTURE.md)
- ⚙️ [Implementation & Data Contracts](docs/IMPLEMENTATION.md)
- 🔌 [FastAPI Endpoint Reference](docs/API_REFERENCE.md)
- 🎨 [Dashboard UI Design Specification](docs/UI_DESIGN.md)
- 📊 [Full Model Backtest Report](reports/backtest.md)

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
