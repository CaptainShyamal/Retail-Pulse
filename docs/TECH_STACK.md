# Tech Stack — RetailPulse

## Full stack table

| Layer | Technology | Why | Local dev substitute |
|---|---|---|---|
| Object storage (raw zone) | AWS S3 (prod) | Cloud-native storage | MinIO (S3-compatible, runs in Docker) |
| Compute — batch transform | PySpark | Distributed processing of structured retail data | Local Spark session (single node) |
| Lakehouse | Delta Lake | ACID transactions, schema enforcement, time travel on top of object storage | Delta Lake OSS on MinIO |
| Streaming | Apache Kafka | Real-time POS/IoT event backbone | Redpanda or single-broker Kafka via Docker |
| NLP (unstructured data) | HuggingFace `transformers` (sentiment pipeline) | Turns review text into a usable feature | Same locally, small model (e.g., DistilBERT SST-2) |
| Knowledge graph | Neo4j | Models product/store/supplier relationships for substitution/co-stock features | Neo4j Community Docker image |
| ML — forecasting | Prophet, XGBoost, scikit-learn | Seasonality baseline + gradient-boosted primary model | same |
| Stats | `scipy.stats` | Seasonality/driver significance tests, anomaly control limits | same |
| Experiment tracking | MLflow | Track runs, params, metrics, model registry | MLflow local tracking server (SQLite backend) |
| Drift monitoring | Evidently AI | Detect prediction/feature drift post-deployment | same |
| API layer | FastAPI | Lightweight microservices for ingestion, prediction, anomaly alerts | same, run via `uvicorn` |
| Containerization | Docker + Docker Compose | Each service independently deployable, mirrors microservices architecture | same |
| Warehouse | Postgres (local) / Snowflake (cloud) | Query layer decoupled from lakehouse, feeds BI | Postgres via Docker |
| BI / dashboard | Streamlit (MVP), Power BI (V2) | Self-serve, narrative dashboard for non-technical users | Streamlit runs anywhere |
| Visualization | Plotly | Interactive charts inside Streamlit | same |
| Language / glue | Python 3.11 | Orchestration, modeling, service code | same |
| Cloud (stretch) | AWS (S3, Lambda, ECS/Fargate) or Azure equivalents | Cloud-native deployment target | — |

## JD-phrase → tech mapping (for resume/portfolio framing)
| JD phrase | Tech used |
|---|---|
| Cloud native + cloud agnostic stacks | AWS S3/Lambda or Azure Blob/Functions + MinIO abstraction |
| Open-source stack like Python, PySpark | Python, PySpark |
| Structured and unstructured data | Sales tables (structured) + review text via HuggingFace (unstructured) |
| Real-time and batch-oriented systems | Kafka + nightly PySpark batch job |
| Digital and IoT data | Simulated shelf-sensor stream |
| Services oriented / microservices architecture | FastAPI services + Docker Compose |
| Build Lakehouses and Warehouses | Delta Lake (lakehouse) + Postgres/Snowflake (warehouse) |
| Next-gen warehouse solutions using Knowledge Graphs | Neo4j |
| Statistical and ML research | scikit-learn, Prophet, XGBoost, scipy.stats |
| Monitor outcomes | MLflow + Evidently AI |
| Dashboards for marketers, self-serve | Streamlit / Power BI |
| Predictive analytics and visual storytelling | Plotly narrative dashboard |

## Minimum versions (pin these in `requirements.txt` / `pyproject.toml`)
- Python 3.11+
- PySpark 3.5.x (Delta Lake 3.x compatible)
- delta-spark 3.x
- fastapi + uvicorn (latest stable)
- xgboost, scikit-learn, prophet, scipy
- neo4j Python driver 5.x
- kafka-python or confluent-kafka
- streamlit, plotly
- mlflow
- evidently

> Antigravity should verify exact compatible version pins at setup time (Delta Lake / PySpark / Python version compatibility is version-sensitive) rather than trusting hardcoded versions here.
