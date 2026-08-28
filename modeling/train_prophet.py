import os
import sys
import pickle
import pandas as pd
import numpy as np
import warnings

warnings.filterwarnings("ignore")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

def train_prophet_models(data_path: str = None, horizon: int = 14):
    """
    Trains additive time-series baseline models per store/SKU combination.
    Uses Prophet if available; seamlessly falls back to statsmodels ExponentialSmoothing.
    Produces forecasts with 80% confidence intervals.
    """
    if data_path is None:
        data_path = os.path.join(PROJECT_ROOT, "data", "curated", "sales_daily.parquet")

    print(f"Loading curated sales data for baseline training from {data_path}...")
    df = pd.read_parquet(data_path)
    df["ds"] = pd.to_datetime(df["date"])
    df["y"] = df["qty_sold"].astype(float)

    models_dir = os.path.join(PROJECT_ROOT, "data", "models", "prophet")
    forecasts_dir = os.path.join(PROJECT_ROOT, "data", "predictions")
    os.makedirs(models_dir, exist_ok=True)
    os.makedirs(forecasts_dir, exist_ok=True)

    all_forecasts = []
    unique_combos = df[["store_id", "sku"]].drop_duplicates().values
    print(f"Training baseline models for {len(unique_combos)} store-SKU series...")

    # Test if Prophet can be instantiated
    use_prophet = False
    try:
        from prophet import Prophet
        test_p = Prophet()
        use_prophet = True
    except Exception:
        use_prophet = False

    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    for store_id, sku in unique_combos:
        sub_df = df[(df["store_id"] == store_id) & (df["sku"] == sku)].sort_values("ds")
        if len(sub_df) < 14:
            continue

        last_date = sub_df["ds"].max()
        future_dates = [last_date + pd.Timedelta(days=i) for i in range(1, horizon + 1)]
        
        trained = False
        if use_prophet:
            try:
                from prophet import Prophet
                model = Prophet(yearly_seasonality=False, weekly_seasonality=True, daily_seasonality=False, interval_width=0.80)
                model.fit(sub_df[["ds", "y"]], show_progress=False)
                future = model.make_future_dataframe(periods=horizon, freq="D")
                forecast = model.predict(future)
                future_forecast = forecast.tail(horizon).copy()
                future_forecast["store_id"] = store_id
                future_forecast["sku"] = sku
                future_forecast["model_version"] = "prophet_baseline_v1"
                future_forecast["forecast_qty"] = np.maximum(0, future_forecast["yhat"]).round(1)
                future_forecast["lower_ci"] = np.maximum(0, future_forecast["yhat_lower"]).round(1)
                future_forecast["upper_ci"] = np.maximum(0, future_forecast["yhat_upper"]).round(1)
                future_forecast["date"] = future_forecast["ds"].dt.strftime("%Y-%m-%d")
                res_df = future_forecast[["store_id", "sku", "date", "forecast_qty", "lower_ci", "upper_ci", "model_version"]]
                all_forecasts.append(res_df)
                trained = True
            except Exception:
                trained = False

        if not trained:
            # High quality Seasonal Holt-Winters Baseline
            try:
                series = sub_df["y"].values
                hw_model = ExponentialSmoothing(
                    series,
                    seasonal_periods=7,
                    trend="add",
                    seasonal="add",
                    initialization_method="estimated"
                ).fit()
                pred_vals = np.maximum(0, hw_model.forecast(horizon))
                residual_std = float(np.std(series - hw_model.fittedvalues)) if len(series) > 7 else 2.0
            except Exception:
                # Rolling mean fallback
                mean_val = float(sub_df["y"].tail(7).mean())
                pred_vals = np.full(horizon, max(0.0, mean_val))
                residual_std = 2.5

            res_records = []
            for i, f_date in enumerate(future_dates):
                f_qty = round(float(pred_vals[i]), 1)
                res_records.append({
                    "store_id": store_id,
                    "sku": sku,
                    "date": f_date.strftime("%Y-%m-%d"),
                    "forecast_qty": f_qty,
                    "lower_ci": max(0.0, round(f_qty - 1.28 * residual_std, 1)),
                    "upper_ci": max(0.0, round(f_qty + 1.28 * residual_std, 1)),
                    "model_version": "baseline_seasonality_v1"
                })
            all_forecasts.append(pd.DataFrame(res_records))

    df_forecasts = pd.concat(all_forecasts, ignore_index=True)
    output_forecast_path = os.path.join(forecasts_dir, "prophet_forecasts.parquet")
    df_forecasts.to_parquet(output_forecast_path, index=False)
    print(f"Baseline training complete. Generated {len(df_forecasts)} forecast records.")
    print(f"Saved to: {output_forecast_path}")

    # Log to MLflow
    try:
        from modeling.mlflow_utils import log_experiment_run
        log_experiment_run(
            run_name="baseline_exponential_smoothing",
            model_type="additive_seasonality_baseline",
            params={"horizon_days": horizon, "series_count": len(unique_combos), "seasonality": "weekly"},
            metrics={"forecast_mean_qty": float(df_forecasts["forecast_qty"].mean())},
            tags={"role": "baseline", "phase": "phase_8"},
            model_artifact_path=output_forecast_path
        )
    except Exception as e:
        print(f"Notice: MLflow logging skipped ({e})")

    return df_forecasts

if __name__ == "__main__":
    train_prophet_models()
