import os
import sys
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from typing import Optional, List

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from services.common.schemas import HealthResponse, ForecastResponse, ForecastPoint

app = FastAPI(
    title="RetailPulse Demand Prediction Service",
    description="Operational microservice serving XGBoost and Prophet demand forecasts with confidence bounds.",
    version="1.0.0"
)

PREDICTIONS_PATH = os.path.join(PROJECT_ROOT, "data", "predictions", "forecast.parquet")
CURATED_PATH = os.path.join(PROJECT_ROOT, "data", "curated", "sales_daily.parquet")

@app.get("/health", response_model=HealthResponse)
def health_check():
    return HealthResponse(status="ok", service="prediction_service")

@app.get("/forecast/stores", response_model=List[str])
def get_stores():
    if os.path.exists(CURATED_PATH):
        df = pd.read_parquet(CURATED_PATH)
        return sorted(df["store_id"].unique().tolist())
    return [f"STORE_{i:03d}" for i in range(1, 6)]

@app.get("/forecast/skus", response_model=List[str])
def get_skus():
    if os.path.exists(CURATED_PATH):
        df = pd.read_parquet(CURATED_PATH)
        return sorted(df["sku"].unique().tolist())
    return [f"SKU_{i:03d}" for i in range(1, 11)]

@app.get("/forecast/{store_id}/{sku}", response_model=ForecastResponse)
def get_forecast(
    store_id: str,
    sku: str,
    horizon: int = Query(default=14, ge=1, le=30, description="Forecast horizon in days")
):
    if not os.path.exists(PREDICTIONS_PATH):
        # Fallback to generate or read prophet
        prophet_path = os.path.join(PROJECT_ROOT, "data", "predictions", "prophet_forecasts.parquet")
        if os.path.exists(prophet_path):
            df_pred = pd.read_parquet(prophet_path)
        else:
            raise HTTPException(status_code=404, detail="Prediction models have not been trained yet.")
    else:
        df_pred = pd.read_parquet(PREDICTIONS_PATH)

    matched = df_pred[(df_pred["store_id"] == store_id) & (df_pred["sku"] == sku)].sort_values("date")
    
    if len(matched) == 0:
        raise HTTPException(status_code=404, detail=f"No forecast series found for store '{store_id}' and SKU '{sku}'.")

    matched_subset = matched.head(horizon)
    points = [
        ForecastPoint(
            date=str(row["date"]),
            forecast_qty=float(row["forecast_qty"]),
            lower_ci=float(row["lower_ci"]),
            upper_ci=float(row["upper_ci"]),
            model_version=str(row.get("model_version", "xgboost_v1.0"))
        )
        for _, row in matched_subset.iterrows()
    ]

    return ForecastResponse(
        store_id=store_id,
        sku=sku,
        horizon=len(points),
        forecasts=points
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
