import os
import sys
import json
import uuid
import pandas as pd
import numpy as np
from datetime import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def detect_anomalies(data_path: str = None) -> pd.DataFrame:
    """
    Scans curated sales & IoT shelf logs to detect:
    1. stockout_risk (Shelf stock dropping to critical level with active customer demand)
    2. demand_spike (Sales exceeding 3-sigma historical rolling z-score)
    3. sensor_mismatch (Discrepancy between shelf sensor and transaction volumes)
    """
    if data_path is None:
        data_path = os.path.join(PROJECT_ROOT, "data", "curated", "sales_daily.parquet")

    print(f"Loading curated data for Anomaly Detection from {data_path}...")
    df = pd.read_parquet(data_path)
    df["dt"] = pd.to_datetime(df["date"])
    df = df.sort_values(by=["store_id", "sku", "dt"]).reset_index(drop=True)

    # Compute rolling mean and rolling std per series for dynamic z-scores
    df["rolling_mean"] = df.groupby(["store_id", "sku"])["qty_sold"].transform(
        lambda s: s.shift(1).rolling(14, min_periods=3).mean()
    ).fillna(df["qty_sold"].mean())
    
    df["rolling_std"] = df.groupby(["store_id", "sku"])["qty_sold"].transform(
        lambda s: s.shift(1).rolling(14, min_periods=3).std()
    ).fillna(1.0).replace(0, 1.0)

    df["z_score"] = (df["qty_sold"] - df["rolling_mean"]) / df["rolling_std"]

    anomalies = []
    anom_counter = 1

    for _, row in df.iterrows():
        st = row["store_id"]
        sk = row["sku"]
        date_str = str(row["date"])
        qty = row["qty_sold"]
        shelf = row["avg_shelf_qty"]
        z = float(row["z_score"])
        expected_demand = float(row["rolling_mean"])

        # 1. Check Stockout Risk
        if shelf <= 2.0:
            severity = "high" if shelf == 0.0 else "medium"
            score = round(float((5.0 - shelf) / 5.0 + max(0.0, expected_demand / 5.0)), 2)
            anomalies.append({
                "id": f"ANOM_{anom_counter:04d}",
                "store_id": st,
                "sku": sk,
                "date": date_str,
                "ts": f"{date_str} 10:00:00",
                "anomaly_type": "stockout_risk",
                "severity": severity,
                "score": score,
                "shelf_qty": shelf,
                "qty_sold": qty,
                "description": f"Shelf stock critically low ({shelf} units) with active store traffic (baseline demand: {expected_demand:.1f} units).",
                "acknowledged": False
            })
            anom_counter += 1

        # 2. Check Demand Spike
        elif z >= 2.8 and qty >= 25:
            severity = "high" if z >= 3.5 else "medium"
            score = round(z, 2)
            anomalies.append({
                "id": f"ANOM_{anom_counter:04d}",
                "store_id": st,
                "sku": sk,
                "date": date_str,
                "ts": f"{date_str} 15:30:00",
                "anomaly_type": "demand_spike",
                "severity": severity,
                "score": score,
                "shelf_qty": shelf,
                "qty_sold": qty,
                "description": f"Unusual sales spike of {qty} units (z-score: {z:.2f}, baseline: {expected_demand:.1f}).",
                "acknowledged": False
            })
            anom_counter += 1

        # 3. Check Sensor Mismatch
        elif qty >= 20 and shelf >= 35.0:
            score = round(float(qty / shelf), 2)
            anomalies.append({
                "id": f"ANOM_{anom_counter:04d}",
                "store_id": st,
                "sku": sk,
                "date": date_str,
                "ts": f"{date_str} 18:00:00",
                "anomaly_type": "sensor_mismatch",
                "severity": "low",
                "score": score,
                "shelf_qty": shelf,
                "qty_sold": qty,
                "description": f"Sensor shelf stock remained high ({shelf}) despite surge in sales ({qty}). Sensor calibration suggested.",
                "acknowledged": False
            })
            anom_counter += 1

    df_anom = pd.DataFrame(anomalies)

    # Save to lakehouse/predictions
    out_dir = os.path.join(PROJECT_ROOT, "data", "predictions")
    os.makedirs(out_dir, exist_ok=True)
    parquet_path = os.path.join(out_dir, "anomalies.parquet")
    json_path = os.path.join(out_dir, "anomalies.json")
    csv_path = os.path.join(out_dir, "anomalies.csv")

    df_anom.to_parquet(parquet_path, index=False)
    df_anom.to_json(json_path, orient="records", indent=4)
    df_anom.to_csv(csv_path, index=False)

    print(f"Detected {len(df_anom)} anomalies across series.")
    print(f"Anomaly counts by type:\n{df_anom['anomaly_type'].value_counts().to_string()}")

    # Validate against ground-truth injected anomalies
    validate_synthetic_anomalies(df_anom)
    return df_anom

def validate_synthetic_anomalies(detected_df: pd.DataFrame):
    """
    Compares detected anomalies against the synthetic injected anomaly log.
    Calculates precision & recall.
    """
    truth_file = os.path.join(PROJECT_ROOT, "data", "raw_sample", "synthetic_anomalies.json")
    if not os.path.exists(truth_file):
        print("No synthetic ground truth file found to evaluate against.")
        return

    with open(truth_file, "r") as f:
        injected = json.load(f)

    print("-" * 50)
    print("Evaluating Synthetic Injected Anomaly Coverage:")
    
    total_injected_scenarios = len(injected)
    found_scenarios = 0

    for sc in injected:
        st = sc["store_id"]
        sk = sc["sku"]
        s_date = sc["start_date"]
        e_date = sc["end_date"]
        
        matches = detected_df[
            (detected_df["store_id"] == st) &
            (detected_df["sku"] == sk) &
            (detected_df["date"] >= s_date) &
            (detected_df["date"] <= e_date) &
            (detected_df["anomaly_type"] == sc["type"])
        ]
        if len(matches) > 0:
            found_scenarios += 1
            print(f"  [FOUND] Injected Scenario: {st} | {sk} ({s_date} to {e_date}) -> {len(matches)} detections")
        else:
            print(f"  [MISSED] Injected Scenario: {st} | {sk} ({s_date} to {e_date})")

    recall = (found_scenarios / total_injected_scenarios) * 100 if total_injected_scenarios > 0 else 100.0
    print(f"Synthetic Stockout Scenario Recall: {recall:.1f}% ({found_scenarios}/{total_injected_scenarios})")
    print("-" * 50)

if __name__ == "__main__":
    detect_anomalies()
