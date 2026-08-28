import io
import os
import sys
import json
import glob
import argparse
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv()

from ingestion.storage import get_s3_client, ensure_bucket_exists

BUFFER_DIR = os.path.join(PROJECT_ROOT, "data", "stream_buffer")

def consume_and_land_microbatches(
    topics=("pos-events", "iot-stock-events"),
    max_records: int = 500,
    group_id: str = "retailpulse-stream-group",
    bootstrap_servers: str = None
):
    """
    Consumes live streaming POS and IoT telemetry micro-batches from Kafka/Redpanda (or stream buffer)
    and lands partitioned CSV files directly into MinIO raw zones.
    """
    if bootstrap_servers is None:
        bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

    raw_bucket = os.getenv("S3_BUCKET_RAW", "retailpulse-raw")
    ensure_bucket_exists(raw_bucket)
    s3_client = get_s3_client()

    pos_records_by_date = {}
    iot_records_by_date = {}
    total_consumed = 0

    # Attempt Kafka Consumer
    use_kafka = False
    try:
        from kafka import KafkaConsumer
        consumer = KafkaConsumer(
            *topics,
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            consumer_timeout_ms=3000
        )
        for msg in consumer:
            payload = msg.value
            topic = msg.topic
            ts_str = payload.get("ts", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            date_str = ts_str.split(" ")[0] if " " in ts_str else ts_str[:10]

            if topic == "pos-events":
                pos_records_by_date.setdefault(date_str, []).append(payload)
            elif topic == "iot-stock-events":
                iot_records_by_date.setdefault(date_str, []).append(payload)

            total_consumed += 1
            if max_records > 0 and total_consumed >= max_records:
                break
        use_kafka = True
    except Exception as e:
        print(f"Notice: Kafka consumer not directly reachable ({e}). Ingesting from local streaming buffer.")

    # Ingest from local stream buffer if Kafka did not provide messages
    if total_consumed == 0 and os.path.exists(BUFFER_DIR):
        pos_files = glob.glob(os.path.join(BUFFER_DIR, "pos_stream_*.json"))
        for pf in pos_files:
            try:
                with open(pf, "r", encoding="utf-8") as f:
                    records = json.load(f)
                    for r in records:
                        date_str = str(r.get("ts", ""))[:10]
                        pos_records_by_date.setdefault(date_str, []).append(r)
                        total_consumed += 1
                os.remove(pf)
            except Exception:
                pass

        iot_files = glob.glob(os.path.join(BUFFER_DIR, "iot_stream_*.json"))
        for iof in iot_files:
            try:
                with open(iof, "r", encoding="utf-8") as f:
                    records = json.load(f)
                    for r in records:
                        date_str = str(r.get("ts", ""))[:10]
                        iot_records_by_date.setdefault(date_str, []).append(r)
                        total_consumed += 1
                os.remove(iof)
            except Exception:
                pass

    # 1. Land POS Micro-Batches to MinIO
    pos_landed_count = 0
    for date_val, rows in pos_records_by_date.items():
        if not date_val:
            continue
        s3_key = f"raw/sales_events/date={date_val}/sales.csv"
        existing_df = None
        try:
            resp = s3_client.get_object(Bucket=raw_bucket, Key=s3_key)
            existing_df = pd.read_csv(io.BytesIO(resp["Body"].read()))
        except Exception:
            pass

        new_df = pd.DataFrame(rows)
        if existing_df is not None:
            combined_df = pd.concat([existing_df, new_df], ignore_index=True).drop_duplicates()
        else:
            combined_df = new_df

        csv_buf = io.StringIO()
        combined_df.to_csv(csv_buf, index=False)
        s3_client.put_object(Bucket=raw_bucket, Key=s3_key, Body=csv_buf.getvalue())
        pos_landed_count += len(rows)

    # 2. Land IoT Micro-Batches to MinIO
    iot_landed_count = 0
    for date_val, rows in iot_records_by_date.items():
        if not date_val:
            continue
        s3_key = f"raw/iot_stock_events/date={date_val}/iot.csv"
        existing_df = None
        try:
            resp = s3_client.get_object(Bucket=raw_bucket, Key=s3_key)
            existing_df = pd.read_csv(io.BytesIO(resp["Body"].read()))
        except Exception:
            pass

        new_df = pd.DataFrame(rows)
        if existing_df is not None:
            combined_df = pd.concat([existing_df, new_df], ignore_index=True).drop_duplicates()
        else:
            combined_df = new_df

        csv_buf = io.StringIO()
        combined_df.to_csv(csv_buf, index=False)
        s3_client.put_object(Bucket=raw_bucket, Key=s3_key, Body=csv_buf.getvalue())
        iot_landed_count += len(rows)

    print("=" * 60)
    print(f"Streaming consumer micro-batch landed to MinIO bucket '{raw_bucket}'!")
    print(f"  - Total streaming records processed: {total_consumed}")
    print(f"  - POS events landed: {pos_landed_count} across {len(pos_records_by_date)} partitions")
    print(f"  - IoT events landed: {iot_landed_count} across {len(iot_records_by_date)} partitions")
    print("=" * 60)
    return {"consumed": total_consumed, "pos_landed": pos_landed_count, "iot_landed": iot_landed_count}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RetailPulse Kafka Stream Consumer")
    parser.add_argument("--max-records", type=int, default=500, help="Maximum messages to consume")
    args = parser.parse_args()

    consume_and_land_microbatches(max_records=args.max_records)
