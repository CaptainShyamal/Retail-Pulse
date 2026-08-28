import os
import sys
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from typing import Optional, List, Dict, Any

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from services.common.schemas import (
    HealthResponse,
    AnomalyItem,
    AnomalyAckResponse,
    AnomalyListResponse
)

app = FastAPI(
    title="RetailPulse Anomaly Detection & Triage Service",
    description="Operational microservice for surfacing stockout risks, demand spikes, and sensor faults with triage acknowledgment workflow.",
    version="1.0.0"
)

ANOMALIES_PARQUET = os.path.join(PROJECT_ROOT, "data", "predictions", "anomalies.parquet")
ANOMALIES_JSON = os.path.join(PROJECT_ROOT, "data", "predictions", "anomalies.json")

def load_anomalies_df() -> pd.DataFrame:
    if os.path.exists(ANOMALIES_PARQUET):
        return pd.read_parquet(ANOMALIES_PARQUET)
    elif os.path.exists(ANOMALIES_JSON):
        return pd.read_json(ANOMALIES_JSON)
    else:
        return pd.DataFrame()

def save_anomalies_df(df: pd.DataFrame):
    os.makedirs(os.path.dirname(ANOMALIES_PARQUET), exist_ok=True)
    df.to_parquet(ANOMALIES_PARQUET, index=False)
    df.to_json(ANOMALIES_JSON, orient="records", indent=4)

@app.get("/health", response_model=HealthResponse)
def health_check():
    return HealthResponse(status="ok", service="anomaly_service")

@app.get("/anomalies", response_model=AnomalyListResponse)
def list_anomalies(
    status: Optional[str] = Query(default="all", description="Status filter: 'open', 'acknowledged', or 'all'"),
    severity: Optional[str] = Query(default=None, description="Severity filter: 'high', 'medium', 'low'"),
    anomaly_type: Optional[str] = Query(default=None, description="Type: 'stockout_risk', 'demand_spike', 'sensor_mismatch'"),
    store_id: Optional[str] = Query(default=None),
    sku: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000)
):
    df = load_anomalies_df()
    if df.empty:
        return AnomalyListResponse(total=0, open_count=0, acknowledged_count=0, anomalies=[])

    total_count = len(df)
    open_count = int((df["acknowledged"] == False).sum())
    ack_count = int((df["acknowledged"] == True).sum())

    filtered = df.copy()

    if status == "open":
        filtered = filtered[filtered["acknowledged"] == False]
    elif status == "acknowledged":
        filtered = filtered[filtered["acknowledged"] == True]

    if severity:
        filtered = filtered[filtered["severity"] == severity.lower()]
    if anomaly_type:
        filtered = filtered[filtered["anomaly_type"] == anomaly_type.lower()]
    if store_id:
        filtered = filtered[filtered["store_id"] == store_id]
    if sku:
        filtered = filtered[filtered["sku"] == sku]

    filtered = filtered.head(limit)

    items = [
        AnomalyItem(
            id=str(r["id"]),
            store_id=str(r["store_id"]),
            sku=str(r["sku"]),
            date=str(r["date"]),
            ts=str(r["ts"]),
            anomaly_type=str(r["anomaly_type"]),
            severity=str(r["severity"]),
            score=float(r["score"]),
            shelf_qty=float(r["shelf_qty"]),
            qty_sold=int(r["qty_sold"]),
            description=str(r["description"]),
            acknowledged=bool(r["acknowledged"])
        )
        for _, r in filtered.iterrows()
    ]

    return AnomalyListResponse(
        total=total_count,
        open_count=open_count,
        acknowledged_count=ack_count,
        anomalies=items
    )

@app.post("/anomalies/{anomaly_id}/ack", response_model=AnomalyAckResponse)
def acknowledge_anomaly(anomaly_id: str):
    df = load_anomalies_df()
    if df.empty or "id" not in df.columns:
        raise HTTPException(status_code=404, detail="No anomalies dataset available.")

    match_mask = df["id"] == anomaly_id
    if not match_mask.any():
        raise HTTPException(status_code=404, detail=f"Anomaly with ID '{anomaly_id}' not found.")

    df.loc[match_mask, "acknowledged"] = True
    save_anomalies_df(df)

    return AnomalyAckResponse(
        id=anomaly_id,
        acknowledged=True,
        message=f"Anomaly {anomaly_id} has been acknowledged and marked as reviewed."
    )

@app.get("/anomalies/stats")
def get_anomaly_stats() -> Dict[str, Any]:
    df = load_anomalies_df()
    if df.empty:
        return {"total": 0, "by_type": {}, "by_severity": {}, "open_count": 0}

    return {
        "total": len(df),
        "open_count": int((df["acknowledged"] == False).sum()),
        "acknowledged_count": int((df["acknowledged"] == True).sum()),
        "by_type": df["anomaly_type"].value_counts().to_dict(),
        "by_severity": df["severity"].value_counts().to_dict(),
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
