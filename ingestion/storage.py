import os
import boto3
from botocore.client import Config
from dotenv import load_dotenv

# Load env variables from .env
load_dotenv()

def get_s3_client():
    minio_endpoint = os.getenv("MINIO_ENDPOINT")
    minio_user = os.getenv("MINIO_ROOT_USER")
    minio_password = os.getenv("MINIO_ROOT_PASSWORD")
    
    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_region = os.getenv("AWS_REGION", "us-east-1")
    
    # Use MinIO if endpoint is defined and we are running locally, otherwise fall back to AWS S3
    if minio_endpoint and ("localhost" in minio_endpoint or "minio" in minio_endpoint or "127.0.0.1" in minio_endpoint or "9000" in minio_endpoint):
        return boto3.client(
            "s3",
            endpoint_url=minio_endpoint,
            aws_access_key_id=minio_user,
            aws_secret_access_key=minio_password,
            region_name="us-east-1",
            config=Config(signature_version="s3v4")
        )
    elif aws_access_key and aws_secret_key:
        return boto3.client(
            "s3",
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=aws_region
        )
    else:
        # Default to local MinIO fallback parameters
        return boto3.client(
            "s3",
            endpoint_url="http://localhost:9000",
            aws_access_key_id="retailpulse",
            aws_secret_access_key="changeme123",
            region_name="us-east-1",
            config=Config(signature_version="s3v4")
        )

def ensure_bucket_exists(bucket_name):
    client = get_s3_client()
    try:
        client.head_bucket(Bucket=bucket_name)
        print(f"Bucket '{bucket_name}' already exists.")
    except Exception:
        print(f"Bucket '{bucket_name}' does not exist. Creating it...")
        try:
            client.create_bucket(Bucket=bucket_name)
            print(f"Bucket '{bucket_name}' created successfully.")
        except Exception as e:
            print(f"Error creating bucket '{bucket_name}': {e}")
            raise e

if __name__ == "__main__":
    # Test bucket creation
    raw_bucket = os.getenv("S3_BUCKET_RAW", "retailpulse-raw")
    curated_bucket = os.getenv("S3_BUCKET_CURATED", "retailpulse-curated")
    ensure_bucket_exists(raw_bucket)
    ensure_bucket_exists(curated_bucket)
