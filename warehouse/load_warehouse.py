import os
import sys
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def get_warehouse_engine():
    pg_user = os.getenv("POSTGRES_USER", "retailpulse")
    pg_pass = os.getenv("POSTGRES_PASSWORD", "changeme123")
    pg_host = os.getenv("POSTGRES_HOST", "localhost")
    pg_port = os.getenv("POSTGRES_PORT", "5432")
    pg_db = os.getenv("POSTGRES_DB", "retailpulse")

    conn_str = f"postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}"
    try:
        engine = create_engine(conn_str, connect_args={"connect_timeout": 3})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print(f"Connected to Postgres warehouse at {pg_host}:{pg_port}/{pg_db}")
        return engine
    except Exception as e:
        print(f"Postgres connection not available ({e}). Using local SQLite warehouse fallback.")
        sqlite_path = os.path.join(PROJECT_ROOT, "data", "warehouse.db")
        os.makedirs(os.path.dirname(sqlite_path), exist_ok=True)
        return create_engine(f"sqlite:///{sqlite_path}")

def sync_lakehouse_to_warehouse():
    """
    Syncs curated Delta Lake tables and prediction outputs into the relational warehouse layer.
    Ensures idempotency and tags experimental Knowledge Graph features with schema comments.
    """
    print("=" * 60)
    print("Starting Warehouse Sync Layer (Lakehouse -> Relational DWH)")
    print("=" * 60)

    engine = get_warehouse_engine()
    is_postgres = "postgresql" in str(engine.url)

    # 1. Sync Curated Daily Sales
    curated_path = os.path.join(PROJECT_ROOT, "data", "curated", "sales_daily.parquet")
    if os.path.exists(curated_path):
        df_curated = pd.read_parquet(curated_path)
        df_curated.to_sql("curated_sales_daily", engine, if_exists="replace", index=False)
        print(f"Synced {len(df_curated)} rows into table 'curated_sales_daily'")

        # Tag experimental graph feature columns in PostgreSQL schema
        if is_postgres:
            try:
                with engine.connect() as conn:
                    if "graph_co_stock_freq" in df_curated.columns:
                        conn.execute(text("COMMENT ON COLUMN curated_sales_daily.graph_co_stock_freq IS '[EXPERIMENTAL / V2 GRAPH FEATURE] Co-occurrence frequency of substitute peers across store history';"))
                    if "graph_substitute_available" in df_curated.columns:
                        conn.execute(text("COMMENT ON COLUMN curated_sales_daily.graph_substitute_available IS '[EXPERIMENTAL / V2 GRAPH FEATURE] Binary flag indicating substitute product availability on t-1';"))
                    conn.commit()
                print("Tagged graph feature columns with [EXPERIMENTAL / V2 GRAPH FEATURE] metadata in PostgreSQL schema.")
            except Exception as e:
                print(f"Notice: Column comment tagging skipped ({e})")

    # 2. Sync Demand Forecasts
    forecast_path = os.path.join(PROJECT_ROOT, "data", "predictions", "forecast.parquet")
    if os.path.exists(forecast_path):
        df_forecast = pd.read_parquet(forecast_path)
        df_forecast.to_sql("predictions_forecast", engine, if_exists="replace", index=False)
        print(f"Synced {len(df_forecast)} rows into table 'predictions_forecast'")

    # 3. Sync Anomalies
    anomaly_path = os.path.join(PROJECT_ROOT, "data", "predictions", "anomalies.parquet")
    if os.path.exists(anomaly_path):
        df_anom = pd.read_parquet(anomaly_path)
        df_anom.to_sql("predictions_anomaly", engine, if_exists="replace", index=False)
        print(f"Synced {len(df_anom)} rows into table 'predictions_anomaly'")

    print("=" * 60)
    print("Warehouse Sync Complete and Idempotent!")
    print("=" * 60)

if __name__ == "__main__":
    sync_lakehouse_to_warehouse()
