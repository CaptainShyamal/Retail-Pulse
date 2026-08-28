from pydantic import BaseModel, Field
from typing import List, Optional

class HealthResponse(BaseModel):
    status: str = "ok"
    service: str
    version: str = "1.0.0"

class ForecastPoint(BaseModel):
    date: str
    forecast_qty: float
    lower_ci: float
    upper_ci: float
    model_version: str = "xgboost_v1.0"

class ForecastResponse(BaseModel):
    store_id: str
    sku: str
    horizon: int
    forecasts: List[ForecastPoint]

class AnomalyItem(BaseModel):
    id: str
    store_id: str
    sku: str
    date: str
    ts: str
    anomaly_type: str
    severity: str
    score: float
    shelf_qty: float
    qty_sold: int
    description: str
    acknowledged: bool = False

class AnomalyAckResponse(BaseModel):
    id: str
    acknowledged: bool
    message: str

class AnomalyListResponse(BaseModel):
    total: int
    open_count: int
    acknowledged_count: int
    anomalies: List[AnomalyItem]

class IngestBatchRequest(BaseModel):
    source_sales_file: Optional[str] = None
    source_reviews_file: Optional[str] = None
    trigger_transform: bool = True

class IngestBatchResponse(BaseModel):
    status: str
    message: str
    sales_records_ingested: int
    iot_records_ingested: int
    timestamp: str
