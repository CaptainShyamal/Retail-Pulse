import os
import sys
import json
import pytest
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modeling.mlflow_utils import setup_mlflow, log_experiment_run
from modeling.drift_monitor import run_drift_analysis
from warehouse.load_warehouse import get_warehouse_engine, sync_lakehouse_to_warehouse

def test_mlflow_experiment_logging():
    uri = setup_mlflow(experiment_name="test-experiment")
    assert uri is not None
    run_id = log_experiment_run(
        run_name="unit_test_run",
        model_type="test_model",
        params={"learning_rate": 0.05, "max_depth": 3},
        metrics={"mae": 1.5, "rmse": 2.1, "mape": 15.2},
        tags={"environment": "test"}
    )
    assert run_id is not None
    assert len(run_id) > 0

def test_evidently_drift_monitoring_contract(tmp_path):
    html_out = str(tmp_path / "drift_test.html")
    json_out = str(tmp_path / "drift_test.json")

    curated_path = os.path.join(PROJECT_ROOT, "data", "curated", "sales_daily.parquet")
    if not os.path.exists(curated_path):
        pytest.skip("Curated parquet not available for drift test")

    summary = run_drift_analysis(
        data_path=curated_path,
        html_report_path=html_out,
        json_summary_path=json_out
    )

    assert os.path.exists(html_out)
    assert os.path.exists(json_out)
    assert summary["verdict"] in ["PASS", "WARN", "FAIL"]
    assert "total_columns" in summary
    assert "share_of_drifted_columns" in summary

def test_warehouse_sync_idempotency():
    engine = get_warehouse_engine()

    # First sync
    sync_lakehouse_to_warehouse()
    df_1 = pd.read_sql("SELECT count(*) AS cnt FROM curated_sales_daily", engine)
    count_1 = int(df_1["cnt"].iloc[0])
    assert count_1 > 0

    # Second sync (must match count exactly)
    sync_lakehouse_to_warehouse()
    df_2 = pd.read_sql("SELECT count(*) AS cnt FROM curated_sales_daily", engine)
    count_2 = int(df_2["cnt"].iloc[0])
    assert count_1 == count_2, f"Warehouse sync is not idempotent: count {count_1} != {count_2}"
