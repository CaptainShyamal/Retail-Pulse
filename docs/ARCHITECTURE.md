# Architecture — RetailPulse

## 1. High-level data flow

```
                 ┌───────────────────────┐
   Batch CSV --> │                        │
   (sales hist.) │       INGEST           │ --> Raw Zone (S3 / MinIO)
   Kafka stream --> (Kafka / producer sim)│
   (POS + IoT)   └───────────────────────┘
                            │
                            v
                 ┌───────────────────────┐
                 │      TRANSFORM         │
                 │  PySpark: clean, join  │ --> Curated Zone
                 │  structured + text     │     (Delta Lake, ACID)
                 └───────────────────────┘
                            │
                            v
                 ┌───────────────────────┐
                 │       ENRICH           │
                 │  Neo4j knowledge graph │ --> graph features
                 │  (product/store/       │     (substitutes, co-stock)
                 │   supplier relations)  │
                 └───────────────────────┘
                            │
                            v
                 ┌───────────────────────┐
                 │        MODEL           │
                 │ scikit-learn / XGBoost │ --> forecasts
                 │ / Prophet + MLflow     │     anomaly flags
                 └───────────────────────┘
                            │
                 ┌──────────┴───────────┐
                 v                       v
        ┌────────────────┐     ┌─────────────────┐
        │     SERVE       │     │    WAREHOUSE     │
        │ FastAPI micro-  │     │ Postgres/        │
        │ services        │     │ Snowflake        │
        │ (predict, alert,│     │ (curated preds   │
        │  ingest)        │     │  for BI query)   │
        └────────────────┘     └─────────────────┘
                 │                       │
                 └──────────┬────────────┘
                             v
                  ┌────────────────────┐
                  │      VISUALIZE      │
                  │ Streamlit / Power BI│
                  │ narrative dashboard │
                  └────────────────────┘
```

## 2. Components

### 2.1 Ingestion layer
- **Batch**: Python script loads historical sales CSV → raw zone (S3/MinIO), partitioned by date.
- **Streaming**: Kafka producer (`ingestion/stream_producer.py`) simulates POS transactions and IoT shelf-sensor pings on two topics (`pos-events`, `iot-stock-events`). A consumer job lands events into the raw zone in micro-batches.
- **Cloud-agnostic design**: all storage access goes through a thin `storage/` abstraction so the same code targets MinIO locally and S3 in prod by swapping an endpoint/env var.

### 2.2 Transform layer (PySpark)
- Reads raw zone, cleans nulls/dupes, joins structured sales with unstructured product-review text.
- Sentiment score on review text (HuggingFace pipeline) becomes a feature column.
- Writes to Delta Lake curated zone with schema enforcement (ACID, time-travel for reproducibility).

### 2.3 Enrichment layer (Neo4j)
- Graph schema: `(:Product)-[:SOLD_AT]->(:Store)`, `(:Product)-[:SUBSTITUTE_FOR]->(:Product)`, `(:Store)-[:SUPPLIED_BY]->(:Supplier)`.
- Feature extraction job queries the graph for "frequently co-stocked" and "substitute available" flags, joins them back onto the curated Spark table as forecasting features.

### 2.4 Modeling layer
- Baseline: Prophet per SKU/store for seasonality.
- Primary: XGBoost with engineered features (lag sales, graph features, sentiment, calendar features).
- Anomaly detection: statistical control limits (rolling z-score) on sales/stock-sensor series, flags stockout risk and suspicious spikes (fraud/return-abuse pattern).
- MLflow tracks runs/params/metrics; Evidently AI checks prediction drift on a schedule.

### 2.5 Serving layer (FastAPI microservices)
- `ingestion-service`: accepts manual/batch upload triggers, health checks.
- `prediction-service`: `GET /forecast/{sku}/{store}`, returns forecast + confidence interval.
- `anomaly-service`: `GET /anomalies`, `POST /anomalies/ack`.
- Each service is its own container; Docker Compose wires them together with the DBs.

### 2.6 Warehouse layer
- Curated predictions + anomaly flags pushed to Postgres (local) / Snowflake (cloud) for BI querying — decoupled from the operational Delta Lake so BI tools don't hit the lakehouse directly.

### 2.7 Visualization layer
- Streamlit app (MVP) reading from the warehouse + calling the FastAPI services.
- Optional Power BI dashboard connected directly to the warehouse for a "V2" polish pass.
- Pages: Overview (stat cards + trend chart, mirrors `UI_DESIGN.md`), Forecast Explorer (per SKU/store), Anomaly Feed, Knowledge Graph Explorer (V2).

## 3. Deployment topology
- **Local dev**: Docker Compose — MinIO, Kafka (or Redpanda for lighter footprint), Postgres, Neo4j, the 3 FastAPI services, Streamlit.
- **Cloud (stretch)**: same containers pushed to AWS (S3 replaces MinIO, ECS/Fargate or a single EC2 + Docker Compose for services, RDS Postgres or Snowflake for warehouse).

## 4. Data contracts (summary — full schemas in `IMPLEMENTATION.md`)
- `raw.sales_events`: `store_id, sku, ts, qty_sold, price, channel`
- `raw.iot_stock_events`: `store_id, sku, ts, shelf_qty, sensor_id`
- `curated.sales_daily`: `store_id, sku, date, qty_sold, revenue, sentiment_score, graph_features...`
- `predictions.forecast`: `store_id, sku, date, forecast_qty, lower_ci, upper_ci, model_version`
- `predictions.anomaly`: `store_id, sku, ts, anomaly_type, severity, score`

## 5. Design principles
- Every layer is independently runnable and testable (no layer requires the whole stack to be up to unit-test its logic).
- MVP path (batch-only, no Kafka/Neo4j) must work standalone — real-time and graph enrichment are additive, not load-bearing.
- All inter-service communication is over HTTP/REST (FastAPI) or the message bus (Kafka) — no direct DB-to-DB coupling between services.
