import os
import sys
import pandas as pd
import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

def test_raw_sales_data_contract():
    sales_path = os.path.join(PROJECT_ROOT, "data", "raw_sample", "sales_raw.csv")
    assert os.path.exists(sales_path), "Raw sales CSV must exist"
    
    df = pd.read_csv(sales_path)
    required_cols = {"store_id", "sku", "ts", "qty_sold", "price", "channel"}
    assert required_cols.issubset(df.columns), f"Missing columns in sales CSV: {required_cols - set(df.columns)}"
    assert len(df) > 0, "Sales CSV must not be empty"

def test_raw_reviews_data_contract():
    reviews_path = os.path.join(PROJECT_ROOT, "data", "raw_sample", "reviews_raw.csv")
    assert os.path.exists(reviews_path), "Raw reviews CSV must exist"
    
    df = pd.read_csv(reviews_path)
    required_cols = {"sku", "review_text"}
    assert required_cols.issubset(df.columns), f"Missing columns in reviews CSV: {required_cols - set(df.columns)}"
    assert len(df) > 0, "Reviews CSV must not be empty"

def test_synthetic_anomalies_logged():
    anomalies_file = os.path.join(PROJECT_ROOT, "data", "raw_sample", "synthetic_anomalies.json")
    assert os.path.exists(anomalies_file), "Synthetic anomaly log must be present"
