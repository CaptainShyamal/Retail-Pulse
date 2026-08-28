import os
import sys
import pandas as pd
import json

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def run_data_quality_checks(parquet_path: str = None):
    if parquet_path is None:
        parquet_path = os.path.join(PROJECT_ROOT, "data", "curated", "sales_daily.parquet")

    print(f"Running Data Quality Gate on: {parquet_path}")
    if not os.path.exists(parquet_path):
        raise FileNotFoundError(f"Curated file {parquet_path} does not exist. Run transform pipeline first.")

    df = pd.read_parquet(parquet_path)
    
    expected_columns = {
        "store_id": "object",
        "sku": "object",
        "date": "object",
        "qty_sold": "int64",
        "revenue": "float64",
        "avg_shelf_qty": "float64",
        "sentiment_score": "float64",
        "graph_co_stock_flag": "bool",
        "graph_substitute_available": "bool"
    }

    results = {
        "total_records": len(df),
        "passed": True,
        "checks": {}
    }

    # Check 1: Record count
    results["checks"]["min_record_threshold"] = {
        "passed": len(df) > 0,
        "count": len(df)
    }
    if len(df) == 0:
        results["passed"] = False

    # Check 2: Column presence
    missing_cols = [col for col in expected_columns if col not in df.columns]
    results["checks"]["schema_completeness"] = {
        "passed": len(missing_cols) == 0,
        "missing_columns": missing_cols
    }
    if missing_cols:
        results["passed"] = False

    # Check 3: Null rates
    null_summary = df.isnull().mean().to_dict()
    unacceptable_nulls = {col: rate for col, rate in null_summary.items() if rate > 0.05}
    results["checks"]["null_rate_tolerance"] = {
        "passed": len(unacceptable_nulls) == 0,
        "null_rates": null_summary,
        "violations": unacceptable_nulls
    }
    if unacceptable_nulls:
        results["passed"] = False

    # Check 4: Value bounds (non-negative quantities and revenues)
    negative_qty = int((df["qty_sold"] < 0).sum()) if "qty_sold" in df.columns else 0
    negative_rev = int((df["revenue"] < 0).sum()) if "revenue" in df.columns else 0
    results["checks"]["non_negative_bounds"] = {
        "passed": (negative_qty == 0 and negative_rev == 0),
        "negative_qty_count": negative_qty,
        "negative_revenue_count": negative_rev
    }
    if negative_qty > 0 or negative_rev > 0:
        results["passed"] = False

    # Save report
    report_path = os.path.join(PROJECT_ROOT, "reports", "data_quality_report.json")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4)

    print("=" * 60)
    print(f"Data Quality Check Results: {'PASSED [OK]' if results['passed'] else 'FAILED [ERROR]'}")
    print(f"Report saved to: {report_path}")
    print("=" * 60)
    return results

if __name__ == "__main__":
    run_data_quality_checks()
