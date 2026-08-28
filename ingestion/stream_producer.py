import os
import sys
import json
import time
import argparse
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv()

# Shared streaming buffer for local/standalone fallback
BUFFER_DIR = os.path.join(PROJECT_ROOT, "data", "stream_buffer")
os.makedirs(BUFFER_DIR, exist_ok=True)

def stream_historical_events(
    pos_topic: str = "pos-events",
    iot_topic: str = "iot-stock-events",
    max_events: int = 100,
    interval_sec: float = 0.01,
    bootstrap_servers: str = None
):
    """
    Replays historical sales transactions and IoT telemetry pings to Kafka/Redpanda
    with fallback to streaming event buffer.
    """
    if bootstrap_servers is None:
        bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

    producer = None
    use_kafka = False
    try:
        from kafka import KafkaProducer
        producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
            retries=2,
            request_timeout_ms=3000
        )
        use_kafka = True
        print(f"Connected to Kafka/Redpanda broker at {bootstrap_servers}")
    except Exception as e:
        print(f"Notice: Kafka broker not directly reachable ({e}). Streaming to local micro-batch buffer.")

    sales_path = os.path.join(PROJECT_ROOT, "data", "raw_sample", "sales_raw.csv")
    if not os.path.exists(sales_path):
        raise FileNotFoundError(f"Raw sales file not found at {sales_path}")

    df_sales = pd.read_csv(sales_path)
    df_sales["qty_sold"] = df_sales["qty_sold"].fillna(0).astype(int)
    df_sales["price"] = df_sales["price"].fillna(0.0).astype(float)
    df_sales["channel"] = df_sales["channel"].fillna("in-store").astype(str)
    events_to_stream = df_sales.head(max_events) if max_events > 0 else df_sales

    print(f"Streaming {len(events_to_stream)} POS and IoT events...")
    pos_sent = 0
    iot_sent = 0
    buffer_pos = []
    buffer_iot = []

    for idx, row in events_to_stream.iterrows():
        # 1. POS event
        pos_payload = {
            "store_id": str(row["store_id"]),
            "sku": str(row["sku"]),
            "ts": str(row["ts"]),
            "qty_sold": int(row["qty_sold"]),
            "price": float(row["price"]),
            "channel": str(row["channel"])
        }
        if use_kafka and producer:
            producer.send(pos_topic, key=pos_payload["store_id"], value=pos_payload)
        else:
            buffer_pos.append(pos_payload)
        pos_sent += 1

        # 2. IoT event
        iot_payload = {
            "store_id": str(row["store_id"]),
            "sku": str(row["sku"]),
            "ts": str(row["ts"]),
            "shelf_qty": max(0, 25 - int(row["qty_sold"])),
            "sensor_id": f"SNSR_{row['store_id']}_{row['sku']}"
        }
        if use_kafka and producer:
            producer.send(iot_topic, key=iot_payload["store_id"], value=iot_payload)
        else:
            buffer_iot.append(iot_payload)
        iot_sent += 1

        if interval_sec > 0 and idx % 50 == 0:
            time.sleep(interval_sec)

    if use_kafka and producer:
        producer.flush()
    else:
        # Write to buffer files
        pos_buf_file = os.path.join(BUFFER_DIR, f"pos_stream_{int(time.time()*1000)}.json")
        iot_buf_file = os.path.join(BUFFER_DIR, f"iot_stream_{int(time.time()*1000)}.json")
        with open(pos_buf_file, "w", encoding="utf-8") as f:
            json.dump(buffer_pos, f)
        with open(iot_buf_file, "w", encoding="utf-8") as f:
            json.dump(buffer_iot, f)

    print("=" * 60)
    print(f"Streaming Replay Complete!")
    print(f"  - '{pos_topic}' messages published: {pos_sent}")
    print(f"  - '{iot_topic}' messages published: {iot_sent}")
    print("=" * 60)
    return {"pos_sent": pos_sent, "iot_sent": iot_sent}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RetailPulse POS & IoT Stream Producer")
    parser.add_argument("--max-events", type=int, default=200, help="Maximum events to stream")
    parser.add_argument("--interval", type=float, default=0.005, help="Interval in seconds")
    args = parser.parse_args()

    stream_historical_events(max_events=args.max_events, interval_sec=args.interval)
