import os
import sys
import pickle
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Constructs rich time-series features (lags, rolling statistics, calendar, and sensor/sentiment signals).
    """
    df = df.copy()
    df["dt"] = pd.to_datetime(df["date"])
    df = df.sort_values(by=["store_id", "sku", "dt"]).reset_index(drop=True)

    # Calendar features
    df["dayofweek"] = df["dt"].dt.dayofweek
    df["is_weekend"] = df["dayofweek"].isin([5, 6]).astype(int)
    df["month"] = df["dt"].dt.month
    df["day"] = df["dt"].dt.day

    # Grouped lag features
    for lag in [1, 2, 7, 14, 21, 28]:
        df[f"qty_lag_{lag}"] = df.groupby(["store_id", "sku"])["qty_sold"].shift(lag)

    # Rolling window features
    for window in [7, 14, 28]:
        df[f"rolling_mean_{window}"] = df.groupby(["store_id", "sku"])["qty_sold"].transform(
            lambda s: s.shift(1).rolling(window=window, min_periods=1).mean()
        )
        df[f"rolling_std_{window}"] = df.groupby(["store_id", "sku"])["qty_sold"].transform(
            lambda s: s.shift(1).rolling(window=window, min_periods=1).std()
        ).fillna(0)

    # Categorical encoding
    store_cats = {s: i for i, s in enumerate(sorted(df["store_id"].unique()))}
    sku_cats = {s: i for i, s in enumerate(sorted(df["sku"].unique()))}
    df["store_encoded"] = df["store_id"].map(store_cats)
    df["sku_encoded"] = df["sku"].map(sku_cats)

    return df

def train_xgboost_model(data_path: str = None, horizon: int = 14):
    """
    Trains XGBoost regressor using time-based split.
    """
    if data_path is None:
        data_path = os.path.join(PROJECT_ROOT, "data", "curated", "sales_daily.parquet")

    print(f"Loading curated sales data for XGBoost training from {data_path}...")
    raw_df = pd.read_parquet(data_path)
    df_feat = build_features(raw_df)

    feature_cols = [
        "store_encoded", "sku_encoded", "dayofweek", "is_weekend", "month", "day",
        "avg_shelf_qty", "sentiment_score",
        "qty_lag_1", "qty_lag_2", "qty_lag_7", "qty_lag_14", "qty_lag_21", "qty_lag_28",
        "rolling_mean_7", "rolling_std_7", "rolling_mean_14", "rolling_std_14",
        "rolling_mean_28", "rolling_std_28"
    ]

    # Dynamically append Knowledge Graph features if available
    if "graph_co_stock_freq" in df_feat.columns:
        feature_cols.append("graph_co_stock_freq")
    if "graph_substitute_available" in df_feat.columns:
        feature_cols.append("graph_substitute_available")

    # Clean rows with NaN lags
    train_valid_df = df_feat.dropna(subset=feature_cols).copy()

    # Time-based train / validation split (hold out last 28 days for validation)
    max_date = train_valid_df["dt"].max()
    split_date = max_date - pd.Timedelta(days=28)

    train_data = train_valid_df[train_valid_df["dt"] <= split_date]
    val_data = train_valid_df[train_valid_df["dt"] > split_date]

    X_train, y_train = train_data[feature_cols], train_data["qty_sold"]
    X_val, y_val = val_data[feature_cols], val_data["qty_sold"]

    print(f"Training set: {len(X_train)} samples, Validation set: {len(X_val)} samples.")

    model = xgb.XGBRegressor(
        n_estimators=250,
        learning_rate=0.04,
        max_depth=5,
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=42,
        tree_method="hist"
    )

    model.fit(
        X_train, y_train,
        eval_set=[(X_train, y_train), (X_val, y_val)],
        verbose=False
    )

    val_preds = model.predict(X_val)
    val_preds = np.maximum(0, val_preds)

    mae = mean_absolute_error(y_val, val_preds)
    rmse = np.sqrt(mean_squared_error(y_val, val_preds))
    
    # Calculate non-zero MAPE
    mask = y_val > 0
    mape = np.mean(np.abs((y_val[mask] - val_preds[mask]) / y_val[mask])) * 100

    print("=" * 60)
    print(f"XGBoost Validation Metrics:")
    print(f"  - MAE:  {mae:.2f}")
    print(f"  - RMSE: {rmse:.2f}")
    print(f"  - MAPE: {mape:.2f}%")
    print("=" * 60)

    # Save model artifact
    models_dir = os.path.join(PROJECT_ROOT, "data", "models", "xgboost")
    os.makedirs(models_dir, exist_ok=True)
    model_path = os.path.join(models_dir, "xgboost_demand.pkl")
    with open(model_path, "wb") as f:
        pickle.dump({
            "model": model,
            "feature_cols": feature_cols,
            "metrics": {"mae": mae, "rmse": rmse, "mape": mape}
        }, f)
    print(f"Model artifact saved to: {model_path}")

    # Generate forward predictions for next `horizon` days
    latest_date = df_feat["dt"].max()
    future_records = []
    
    for (st, sk), group in df_feat.groupby(["store_id", "sku"]):
        last_row = group.iloc[-1].copy()
        current_lags = list(group["qty_sold"].values[-28:])
        last_shelf = last_row["avg_shelf_qty"]
        sentiment = last_row["sentiment_score"]

        for step in range(1, horizon + 1):
            future_dt = latest_date + pd.Timedelta(days=step)
            dow = future_dt.dayofweek
            is_wknd = 1 if dow in [5, 6] else 0

            # approximate feature vector
            row_dict = {
                "store_encoded": last_row["store_encoded"],
                "sku_encoded": last_row["sku_encoded"],
                "dayofweek": dow,
                "is_weekend": is_wknd,
                "month": future_dt.month,
                "day": future_dt.day,
                "avg_shelf_qty": last_shelf,
                "sentiment_score": sentiment,
                "qty_lag_1": current_lags[-1] if len(current_lags) >= 1 else 10,
                "qty_lag_2": current_lags[-2] if len(current_lags) >= 2 else 10,
                "qty_lag_7": current_lags[-7] if len(current_lags) >= 7 else 10,
                "qty_lag_14": current_lags[-14] if len(current_lags) >= 14 else 10,
                "qty_lag_21": current_lags[-21] if len(current_lags) >= 21 else 10,
                "qty_lag_28": current_lags[-28] if len(current_lags) >= 28 else 10,
                "rolling_mean_7": np.mean(current_lags[-7:]),
                "rolling_std_7": np.std(current_lags[-7:]),
                "rolling_mean_14": np.mean(current_lags[-14:]),
                "rolling_std_14": np.std(current_lags[-14:]),
                "rolling_mean_28": np.mean(current_lags[-28:]),
                "rolling_std_28": np.std(current_lags[-28:]),
                "graph_co_stock_freq": last_row.get("graph_co_stock_freq", 0.5),
                "graph_substitute_available": last_row.get("graph_substitute_available", 1.0)
            }
            feat_df = pd.DataFrame([row_dict])[feature_cols]
            pred_val = float(model.predict(feat_df)[0])
            pred_val = max(0.0, round(pred_val, 1))

            # Confidence bounds estimated via residual standard deviation
            sigma = rmse
            lower_ci = max(0.0, round(pred_val - 1.28 * sigma, 1))
            upper_ci = max(0.0, round(pred_val + 1.28 * sigma, 1))

            future_records.append({
                "store_id": st,
                "sku": sk,
                "date": future_dt.strftime("%Y-%m-%d"),
                "forecast_qty": pred_val,
                "lower_ci": lower_ci,
                "upper_ci": upper_ci,
                "model_version": "xgboost_v1.0"
            })
            current_lags.append(pred_val)

    df_future = pd.DataFrame(future_records)
    out_preds_path = os.path.join(PROJECT_ROOT, "data", "predictions", "forecast.parquet")
    os.makedirs(os.path.dirname(out_preds_path), exist_ok=True)
    df_future.to_parquet(out_preds_path, index=False)
    print(f"Saved {len(df_future)} XGBoost forecasts to: {out_preds_path}")

    # Log to MLflow
    try:
        from modeling.mlflow_utils import log_experiment_run
        has_graph = "graph_co_stock_freq" in feature_cols or "graph_substitute_available" in feature_cols
        log_experiment_run(
            run_name="xgboost_graph_enhanced" if has_graph else "xgboost_champion_primary",
            model_type="xgboost_regressor",
            params={
                "n_estimators": 250,
                "learning_rate": 0.04,
                "max_depth": 5,
                "subsample": 0.85,
                "features_count": len(feature_cols),
                "has_graph_features": has_graph
            },
            metrics={"mae": float(mae), "rmse": float(rmse), "mape": float(mape)},
            tags={
                "role": "experimental" if has_graph else "production_champion",
                "phase": "phase_8"
            },
            model_artifact_path=model_path
        )
    except Exception as e:
        print(f"Notice: MLflow logging skipped ({e})")

    return model, df_future

if __name__ == "__main__":
    train_xgboost_model()
