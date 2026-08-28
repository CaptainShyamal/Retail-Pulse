# Implementation Notes — RetailPulse

## 1. Repository layout
```
retailpulse/
├── docker-compose.yml
├── .env.example
├── data/
│   ├── raw_sample/            # small sample CSVs for local dev
│   └── seed/
├── ingestion/
│   ├── batch_loader.py
│   ├── stream_producer.py     # Kafka POS/IoT simulator [V2]
│   └── stream_consumer.py     # [V2]
├── transform/
│   ├── spark_jobs/
│   │   ├── clean_join.py
│   │   └── sentiment_feature.py
│   └── delta/                 # Delta table configs
├── graph/
│   ├── schema.cypher          # [V2]
│   ├── load_graph.py          # [V2]
│   └── graph_features.py      # [V2]
├── modeling/
│   ├── train_prophet.py
│   ├── train_xgboost.py
│   ├── anomaly_detection.py
│   ├── backtest.py
│   └── mlflow_utils.py
├── services/
│   ├── ingestion_service/     # FastAPI
│   ├── prediction_service/    # FastAPI
│   └── anomaly_service/       # FastAPI
├── warehouse/
│   └── load_warehouse.py      # curated -> Postgres/Snowflake
├── dashboard/
│   └── streamlit_app.py
├── tests/
└── docs/                      # this doc set lives here
```

## 2. Data contracts

### `raw.sales_events` (batch + streaming land here)
| column | type | notes |
|---|---|---|
| store_id | string | |
| sku | string | |
| ts | timestamp | transaction time |
| qty_sold | int | |
| price | float | |
| channel | string | online / in-store |

### `raw.iot_stock_events`
| column | type | notes |
|---|---|---|
| store_id | string | |
| sku | string | |
| ts | timestamp | sensor ping time |
| shelf_qty | int | current shelf stock reading |
| sensor_id | string | |

### `curated.sales_daily` (Delta Lake, output of transform layer)
| column | type | notes |
|---|---|---|
| store_id | string | |
| sku | string | |
| date | date | |
| qty_sold | int | daily aggregate |
| revenue | float | |
| avg_shelf_qty | float | from IoT events |
| sentiment_score | float | from review text, defaults to 0.0 (neutral) if missing |
| graph_co_stock_flag | bool | [V2] from Neo4j |
| graph_substitute_available | bool | [V2] from Neo4j |

### `predictions.forecast`
| column | type | notes |
|---|---|---|
| store_id, sku, date | | forecast target date |
| forecast_qty | float | |
| lower_ci, upper_ci | float | 80–95% interval |
| model_version | string | MLflow run id or semantic tag |

### `predictions.anomaly`
| column | type | notes |
|---|---|---|
| store_id, sku, ts | | |
| anomaly_type | string | `stockout_risk`, `demand_spike`, `sensor_mismatch` |
| severity | string | low / medium / high |
| score | float | z-score or model-based score |
| acknowledged | bool | for the dashboard "ack" action |

## 3. Module notes

### 3.1 Ingestion
- `batch_loader.py`: reads a CSV (public dataset), writes partitioned files to `raw/sales_events/date=YYYY-MM-DD/`.
- `stream_producer.py` [V2]: reads the same historical data and replays it at accelerated speed onto Kafka topics, plus injects synthetic stockout/anomaly scenarios for demo purposes — document exactly which rows are synthetic so the anomaly-detection accuracy report is honest.

### 3.2 Transform (PySpark)
- Use `pyspark.sql` window functions for daily aggregation, not Python loops.
- Null-handling rule: qty_sold nulls → drop row (can't infer sale); price nulls → forward-fill within SKU.
- Sentiment: batch reviews through a HuggingFace pipeline, cache results (don't re-run per Spark job).
- Write with `mode="overwrite"` + `partitionBy("date")` to Delta for the curated table; use `MERGE` for incremental updates once streaming lands.

### 3.3 Graph enrichment [V2]
- Load `(:Product)`, `(:Store)`, `(:Supplier)` nodes from curated data.
- Relationship `SUBSTITUTE_FOR` can start as a simple heuristic (same category, similar price band) before anything ML-based.
- Cypher query for co-stock: products frequently appearing in the same store's top-selling list in the same week.

### 3.4 Modeling
- Train/test split: time-based (last N weeks held out), never random shuffle — this is a time series.
- Log every run (params, metrics, model artifact) to MLflow.
- `backtest.py` produces `reports/backtest.md` with MAPE/RMSE table comparing Prophet vs XGBoost per SKU category.
- Anomaly detection: compute rolling mean/std per SKU/store, flag points beyond a configurable z-score threshold; cross-check against `avg_shelf_qty` dropping toward zero for `stockout_risk`.

### 3.5 Services (FastAPI)
- Each service has its own `main.py`, `Dockerfile`, and `requirements.txt` — no shared runtime dependency beyond a common `libs/` package for data contracts (Pydantic models mirroring the tables above).
- `prediction-service`: `GET /forecast/{store_id}/{sku}?horizon=7`
- `anomaly-service`: `GET /anomalies?status=open`, `POST /anomalies/{id}/ack`
- `ingestion-service`: `POST /ingest/batch` (trigger), `GET /health`

### 3.6 Warehouse
- `load_warehouse.py` reads latest curated + prediction Delta tables, upserts into Postgres tables mirroring the same schema — this is what the dashboard/BI tool queries, never the lakehouse directly.

### 3.7 Dashboard
- Streamlit app calls the FastAPI services for live data and/or queries the warehouse directly for historical aggregates.
- See `UI_DESIGN.md` for the exact layout spec.

## 4. Build order (maps to `TASKS.md` phases)
1. Repo scaffold + Docker Compose skeleton (MinIO, Postgres only).
2. Batch ingestion + PySpark clean/join + Delta curated table (MVP core data path).
3. Modeling: Prophet baseline → XGBoost → backtest report.
4. Anomaly detection module + validation against injected synthetic anomalies.
5. FastAPI services wrapping model + anomaly outputs.
6. Streamlit dashboard (MVP).
7. **[V2]** Kafka streaming path.
8. **[V2]** Neo4j graph enrichment.
9. **[V2]** Warehouse layer + MLflow/Evidently.
10. **[V3]** Power BI, Knowledge Graph Explorer UI, cloud deployment.
