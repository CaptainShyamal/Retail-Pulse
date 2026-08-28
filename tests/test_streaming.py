import os
import sys
import json
import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

def test_pos_event_schema_contract():
    event = {
        "store_id": "STORE_001",
        "sku": "SKU_001",
        "ts": "2025-06-01 12:30:00",
        "qty_sold": 2,
        "price": 14.99,
        "channel": "in-store"
    }
    required_keys = {"store_id", "sku", "ts", "qty_sold", "price", "channel"}
    assert required_keys.issubset(event.keys())
    assert isinstance(event["qty_sold"], int)
    assert isinstance(event["price"], float)

def test_iot_event_schema_contract():
    event = {
        "store_id": "STORE_001",
        "sku": "SKU_001",
        "ts": "2025-06-01 12:30:00",
        "shelf_qty": 20,
        "sensor_id": "SNSR_STORE_001_SKU_001"
    }
    required_keys = {"store_id", "sku", "ts", "shelf_qty", "sensor_id"}
    assert required_keys.issubset(event.keys())
    assert isinstance(event["shelf_qty"], int)
