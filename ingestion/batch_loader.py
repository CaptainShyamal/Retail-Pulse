import io
import os
import sys
import pandas as pd
from dotenv import load_dotenv

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ingestion.storage import get_s3_client, ensure_bucket_exists

load_dotenv()

def ingest_batch():
    raw_bucket = os.getenv("S3_BUCKET_RAW", "retailpulse-raw")
    curated_bucket = os.getenv("S3_BUCKET_CURATED", "retailpulse-curated")
    
    # Ensure both raw and curated buckets exist in storage
    ensure_bucket_exists(raw_bucket)
    ensure_bucket_exists(curated_bucket)
    
    s3_client = get_s3_client()
    
    # 1. Ingest Product Reviews (unstructured source text)
    reviews_path = os.path.join("data", "raw_sample", "reviews_raw.csv")
    if os.path.exists(reviews_path):
        print(f"Reading reviews from {reviews_path}...")
        df_reviews = pd.read_csv(reviews_path)
        
        required_review_cols = {"sku", "review_text"}
        if not required_review_cols.issubset(df_reviews.columns):
            raise ValueError(f"Reviews CSV must contain columns: {required_review_cols}")
            
        csv_buffer = io.StringIO()
        df_reviews.to_csv(csv_buffer, index=False)
        
        s3_key = "raw/reviews/reviews.csv"
        s3_client.put_object(
            Bucket=raw_bucket,
            Key=s3_key,
            Body=csv_buffer.getvalue()
        )
        print(f"Successfully uploaded reviews to S3 bucket '{raw_bucket}' at key '{s3_key}'")
    else:
        print(f"WARNING: Reviews file {reviews_path} not found.")

    # 2. Ingest Sales Transactions (partitioned by date)
    sales_path = os.path.join("data", "raw_sample", "sales_raw.csv")
    if os.path.exists(sales_path):
        print(f"Reading sales events from {sales_path}...")
        df_sales = pd.read_csv(sales_path)
        
        required_sales_cols = {"store_id", "sku", "ts", "qty_sold", "price", "channel"}
        if not required_sales_cols.issubset(df_sales.columns):
            raise ValueError(f"Sales CSV must contain columns: {required_sales_cols}")
            
        # Parse partition date from ts column
        df_sales['date_partition'] = pd.to_datetime(df_sales['ts']).dt.strftime('%Y-%m-%d')
        
        # Group sales events by date and upload partitions
        groups = df_sales.groupby('date_partition')
        total_partitions = len(groups)
        print(f"Uploading {total_partitions} partitions to S3 bucket '{raw_bucket}'...")
        
        for date_val, group in groups:
            # Exclude the temporary grouping column from the uploaded CSV
            write_df = group.drop(columns=['date_partition'])
            csv_buffer = io.StringIO()
            write_df.to_csv(csv_buffer, index=False)
            
            s3_key = f"raw/sales_events/date={date_val}/sales.csv"
            s3_client.put_object(
                Bucket=raw_bucket,
                Key=s3_key,
                Body=csv_buffer.getvalue()
            )
            
        print("Successfully uploaded all sales partitions.")
    else:
        print(f"ERROR: Sales file {sales_path} not found.")

if __name__ == "__main__":
    ingest_batch()
