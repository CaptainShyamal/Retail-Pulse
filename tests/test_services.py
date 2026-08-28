import os
import sys
import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from services.prediction_service.main import app as pred_app
from services.anomaly_service.main import app as anom_app
from services.ingestion_service.main import app as ingest_app

def test_prediction_service_health():
    client = TestClient(pred_app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "prediction_service"

def test_anomaly_service_health():
    client = TestClient(anom_app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "anomaly_service"

def test_ingestion_service_health():
    client = TestClient(ingest_app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "ingestion_service"

def test_anomaly_service_list():
    client = TestClient(anom_app)
    response = client.get("/anomalies?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "anomalies" in data
