# API & External Service Reference — RetailPulse

This is the list Antigravity needs to know what accounts, URLs, or API keys are required, and which parts of the build need **zero** external accounts (fully local via Docker).

## 1. Things that need NO external account (local-only, MVP path)
| Service | Local endpoint | Notes |
|---|---|---|
| MinIO (S3-compatible storage) | `http://localhost:9000` (API), `http://localhost:9001` (console) | Runs via Docker Compose; default creds set in `.env` (e.g. `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD`) |
| Postgres | `postgresql://localhost:5432/retailpulse` | Runs via Docker Compose |
| Neo4j *(V2)* | `bolt://localhost:7687`, browser UI `http://localhost:7474` | Runs via Docker Compose, Community Edition |
| Kafka/Redpanda *(V2)* | `localhost:9092` | Runs via Docker Compose |
| MLflow tracking server *(V2)* | `http://localhost:5000` | Local server, SQLite backend, run via `mlflow ui` or its own container |
| FastAPI services | `http://localhost:8001` (ingestion), `:8002` (prediction), `:8003` (anomaly) | Ports configurable in `docker-compose.yml` |
| Streamlit dashboard | `http://localhost:8501` | Default Streamlit port |

**Nothing above requires signing up for a cloud account to build/demo the MVP.**

## 2. External accounts / API keys needed (only if going beyond pure-local MVP)

| Purpose | Service | What's needed | Where used |
|---|---|---|---|
| Sentiment model | HuggingFace | No API key needed if running a local `transformers` pipeline (downloads model weights once). Only needed if using the **Inference API** instead: `HUGGINGFACE_API_TOKEN` from https://huggingface.co/settings/tokens | `transform/spark_jobs/sentiment_feature.py` |
| Public dataset | Kaggle | `KAGGLE_USERNAME` + `KAGGLE_KEY` from https://www.kaggle.com/settings (Account → API → Create New Token) — only if downloading the dataset programmatically via `kaggle` CLI/API. Manual download needs no key. | `data/raw_sample/` setup script |
| Cloud object storage *(stretch)* | AWS S3 | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, bucket name — from AWS IAM console | `storage/` abstraction, swaps MinIO → S3 |
| Cloud compute *(stretch)* | AWS Lambda / ECS / Fargate | AWS account + IAM role with relevant permissions | Deployment phase only |
| Cloud warehouse *(stretch)* | Snowflake | Account URL, `SNOWFLAKE_USER`, `SNOWFLAKE_PASSWORD` (or key-pair auth), `SNOWFLAKE_ACCOUNT`, warehouse/db/schema names — from Snowflake trial account | `warehouse/load_warehouse.py` (Postgres is the default; Snowflake is a drop-in alternative) |
| BI polish *(stretch)* | Power BI | Power BI Desktop (free) + a data source connection string to Postgres/Snowflake — no API key for local Desktop use | Phase 9 |
| Drift monitoring *(V2)* | Evidently AI | Open-source Python package, no account/API key needed for local reports | `modeling/anomaly_detection.py`, scheduled job |

## 3. `.env.example` (fill in only what the current phase needs)
```env
# --- Local infra (Docker Compose) ---
MINIO_ROOT_USER=retailpulse
MINIO_ROOT_PASSWORD=changeme123
MINIO_ENDPOINT=http://minio:9000
S3_BUCKET_RAW=retailpulse-raw
S3_BUCKET_CURATED=retailpulse-curated

POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=retailpulse
POSTGRES_USER=retailpulse
POSTGRES_PASSWORD=changeme123

# --- V2: Neo4j ---
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=changeme123

# --- V2: Kafka ---
KAFKA_BOOTSTRAP_SERVERS=kafka:9092

# --- V2: MLflow ---
MLFLOW_TRACKING_URI=http://mlflow:5000

# --- Optional external accounts ---
HUGGINGFACE_API_TOKEN=
KAGGLE_USERNAME=
KAGGLE_KEY=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=
SNOWFLAKE_ACCOUNT=
SNOWFLAKE_USER=
SNOWFLAKE_PASSWORD=
```

## 4. Recommendation for Antigravity
Start with **section 1 only** (everything local, Docker Compose, no signups). Only ask the user for keys in section 2 when a task explicitly reaches a V2/stretch phase that needs them (e.g., don't request AWS credentials until the cloud-deployment task in Phase 9).
