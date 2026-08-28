import os
import sys
import json
import argparse
import pandas as pd
import numpy as np
from datetime import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

def run_drift_analysis(
    data_path: str = None,
    html_report_path: str = None,
    json_summary_path: str = None,
    holdout_days: int = 28
):
    """
    Executes automated data and feature drift monitoring using Evidently AI.
    
    Data Slicing Strategy (Real Out-of-Sample Test):
    -----------------------------------------------
    - Reference Dataset: Historical training period prior to holdout window (e.g. 2024-01-01 to 2025-12-03).
    - Current Dataset: Genuine out-of-sample 28-day backtest window (2025-12-04 to 2025-12-31).
    
    Drift Decision Framework & Reconciled Verdict Thresholds:
    ---------------------------------------------------------
    - Statistical Method: Kolmogorov-Smirnov (KS) test for continuous numerical features (alpha = 0.05).
    - Share of Drifted Features Thresholds:
        * PASS (<= 20%): Less than or equal to 20% of monitored features exhibit statistically significant drift.
                         Distribution is considered stable for production forecasting.
        * WARN (20% - 50%): 20% to 50% of features exhibit drift.
                            Moderate covariate shift detected; model monitoring / recalibration recommended.
        * FAIL (> 50%): More than 50% of features exhibit drift.
                        Critical covariate shift detected; automated retraining alert triggered.
                
    Outputs:
    - HTML Report: reports/drift_report.html (Interactive visual exploration)
    - JSON Summary: reports/drift_summary.json (Machine-readable audit trail)
    - CLI Verdict: Clear PASS / WARN / FAIL printed directly to stdout.
    """
    if data_path is None:
        data_path = os.path.join(PROJECT_ROOT, "data", "curated", "sales_daily.parquet")
    if html_report_path is None:
        html_report_path = os.path.join(PROJECT_ROOT, "reports", "drift_report.html")
    if json_summary_path is None:
        json_summary_path = os.path.join(PROJECT_ROOT, "reports", "drift_summary.json")

    os.makedirs(os.path.dirname(html_report_path), exist_ok=True)
    os.makedirs(os.path.dirname(json_summary_path), exist_ok=True)

    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Curated sales data not found at {data_path}")

    print(f"Loading curated data for Evidently drift analysis from {data_path}...")
    df = pd.read_parquet(data_path)
    df["dt"] = pd.to_datetime(df["date"])
    df = df.sort_values("dt").reset_index(drop=True)

    # Time-based holdout slice: Train history vs 28-day holdout
    max_date = df["dt"].max()
    split_date = max_date - pd.Timedelta(days=holdout_days)

    reference_df = df[df["dt"] <= split_date].copy()
    current_df = df[df["dt"] > split_date].copy()

    monitored_cols = ["qty_sold", "revenue", "avg_shelf_qty", "sentiment_score"]
    if "graph_co_stock_freq" in df.columns:
        monitored_cols.append("graph_co_stock_freq")
    if "graph_substitute_available" in df.columns:
        monitored_cols.append("graph_substitute_available")

    ref_subset = reference_df[monitored_cols]
    curr_subset = current_df[monitored_cols]

    ref_period_str = f"{reference_df['dt'].min().strftime('%Y-%m-%d')} to {reference_df['dt'].max().strftime('%Y-%m-%d')}"
    curr_period_str = f"{current_df['dt'].min().strftime('%Y-%m-%d')} to {current_df['dt'].max().strftime('%Y-%m-%d')}"

    print(f"Reference training period: {ref_period_str} ({len(ref_subset)} rows)")
    print(f"Current evaluation window: {curr_period_str} ({len(curr_subset)} rows)")
    print(f"Monitored features: {monitored_cols}")

    from evidently.report import Report
    from evidently.metric_preset import DataDriftPreset

    report = Report(metrics=[DataDriftPreset()])
    report.run(reference_data=ref_subset, current_data=curr_subset)
    report.save_html(html_report_path)

    # Extract summary metrics from Evidently dictionary representation
    report_dict = report.as_dict()
    metrics_list = report_dict.get("metrics", [])
    drift_summary = {}

    for m in metrics_list:
        result = m.get("result", {})
        if "number_of_columns" in result:
            drift_summary = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "comparison": f"Reference Training Period ({ref_period_str}) vs Out-of-Sample {holdout_days}-Day Holdout ({curr_period_str})",
                "total_columns": result.get("number_of_columns", len(monitored_cols)),
                "number_of_drifted_columns": result.get("number_of_drifted_columns", 0),
                "share_of_drifted_columns": float(result.get("share_of_drifted_columns", 0.0)),
                "dataset_drift_detected": bool(result.get("dataset_drift", False)),
                "drift_by_columns": result.get("drift_by_columns", {})
            }
            break

    # Determine Verdict based on reconciled 20% / 50% thresholds
    drift_share = drift_summary.get("share_of_drifted_columns", 0.0)
    drifted_count = drift_summary.get("number_of_drifted_columns", 0)
    total_count = drift_summary.get("total_columns", len(monitored_cols))

    if drift_share > 0.50:
        verdict = "FAIL"
        verdict_desc = f"CRITICAL DRIFT: {drifted_count}/{total_count} ({drift_share*100:.1f}%) features shifted (>50%). Immediate model retraining required."
    elif drift_share > 0.20:
        verdict = "WARN"
        verdict_desc = f"MODERATE DRIFT: {drifted_count}/{total_count} ({drift_share*100:.1f}%) features shifted (20-50%). Model recalibration recommended."
    else:
        verdict = "PASS"
        verdict_desc = f"STABLE DISTRIBUTION: {drifted_count}/{total_count} ({drift_share*100:.1f}%) features shifted (<=20%). Distribution stable."

    drift_summary["verdict"] = verdict
    drift_summary["verdict_description"] = verdict_desc

    # Save JSON summary
    with open(json_summary_path, "w", encoding="utf-8") as f:
        json.dump(drift_summary, f, indent=2, default=str)

    # Print CLI Summary Banner
    print("=" * 60)
    print(f"EVIDENTLY AI DRIFT MONITORING VERDICT: [{verdict}]")
    print(f"  - Comparison:            {drift_summary['comparison']}")
    print(f"  - Status:                {verdict_desc}")
    print(f"  - Drifted Features:      {drifted_count} / {total_count}")
    print(f"  - Drift Share:           {drift_share * 100:.1f}% (Pass Threshold: <=20.0%, Warn: 20-50%, Fail: >50%)")
    print(f"  - Interactive Report:    {html_report_path}")
    print(f"  - JSON Audit Summary:    {json_summary_path}")
    print("=" * 60)

    return drift_summary

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RetailPulse Evidently AI Drift Monitor")
    parser.add_argument("--data-path", type=str, default=None, help="Path to curated dataset")
    parser.add_argument("--holdout-days", type=int, default=28, help="Holdout days for evaluation comparison")
    args = parser.parse_args()

    run_drift_analysis(data_path=args.data_path, holdout_days=args.holdout_days)
