import csv
import io
import json
import os
import sys
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ingestion.storage import get_s3_client, ensure_bucket_exists

load_dotenv()

def generate_iot_events():
    print("Generating synthetic IoT stock-sensor data...")
    raw_bucket = os.getenv("S3_BUCKET_RAW", "retailpulse-raw")
    ensure_bucket_exists(raw_bucket)
    s3_client = get_s3_client()

    # Configuration
    stores = [f"STORE_{i:03d}" for i in range(1, 6)]
    skus = [f"SKU_{i:03d}" for i in range(1, 11)]
    
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2025, 12, 31)
    delta_days = (end_date - start_date).days + 1

    # Defined anomalies to inject
    # format: (store_id, sku, start_date_str, end_date_str, anomaly_type)
    anomalies_to_inject = [
        {"store_id": "STORE_001", "sku": "SKU_001", "start_date": "2025-06-01", "end_date": "2025-06-05", "type": "stockout_risk"},
        {"store_id": "STORE_002", "sku": "SKU_005", "start_date": "2025-11-10", "end_date": "2025-11-14", "type": "stockout_risk"},
        {"store_id": "STORE_003", "sku": "SKU_010", "start_date": "2025-03-15", "end_date": "2025-03-15", "type": "stockout_risk"}
    ]

    # Save anomalies log to file for later verification validation
    anomalies_log_file = os.path.join("data", "raw_sample", "synthetic_anomalies.json")
    os.makedirs(os.path.dirname(anomalies_log_file), exist_ok=True)
    with open(anomalies_log_file, "w", encoding="utf-8") as f:
        json.dump(anomalies_to_inject, f, indent=4)
    print(f"Logged synthetic anomalies to {anomalies_log_file}")

    # Convert anomaly dates to date objects for fast check
    for a in anomalies_to_inject:
        a["start_dt"] = datetime.strptime(a["start_date"], "%Y-%m-%d").date()
        a["end_dt"] = datetime.strptime(a["end_date"], "%Y-%m-%d").date()

    total_records = 0

    # Generate daily pings for each store/SKU combination
    for day_offset in range(delta_days):
        current_date = start_date + timedelta(days=day_offset)
        date_str = current_date.strftime("%Y-%m-%d")
        current_date_obj = current_date.date()

        day_events = []
        for store in stores:
            for sku in skus:
                sensor_id = f"SNSR_{store}_{sku}"
                
                # Check if this store/sku/date combination matches an anomaly
                is_anomaly = False
                for a in anomalies_to_inject:
                    if a["store_id"] == store and a["sku"] == sku and a["start_dt"] <= current_date_obj <= a["end_dt"]:
                        is_anomaly = True
                        break

                if is_anomaly:
                    # Injected Stockout Scenario: stock levels drop near zero
                    shelf_qty = random.choice([0, 1])
                else:
                    # Normal shelf quantities: weekly cycles & random variation
                    base_qty = 25 + (int(sku.split("_")[1]) % 5) * 5
                    # Slightly lower stock mid-week before restocking
                    weekday_factor = -5 if current_date.weekday() in [2, 3] else 0
                    shelf_qty = int(base_qty + weekday_factor + random.randint(-4, 4))
                    shelf_qty = max(2, shelf_qty)

                # Sensor ping timestamp (randomly distributed between 6:00 AM and 11:00 PM)
                hour = random.randint(6, 22)
                minute = random.randint(0, 59)
                second = random.randint(0, 59)
                ts_str = f"{date_str} {hour:02d}:{minute:02d}:{second:02d}"

                day_events.append([store, sku, ts_str, shelf_qty, sensor_id])

        # Save partition file directly to MinIO/S3
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        writer.writerow(["store_id", "sku", "ts", "shelf_qty", "sensor_id"])
        writer.writerows(day_events)

        s3_key = f"raw/iot_stock_events/date={date_str}/iot.csv"
        s3_client.put_object(
            Bucket=raw_bucket,
            Key=s3_key,
            Body=csv_buffer.getvalue()
        )
        total_records += len(day_events)

    print(f"Generated and uploaded {total_records} IoT sensor events to raw zone.")

if __name__ == "__main__":
    generate_iot_events()
