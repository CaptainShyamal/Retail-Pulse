# Cloud Deployment Architecture Guide — RetailPulse

This document defines the production migration path for swapping local Docker services into fully managed **Amazon Web Services (AWS)** enterprise infrastructure.

---

## 1. Local-to-Cloud Service Mapping

| Local Component | Local Technology | Enterprise Cloud Equivalent | Migration Effort |
| :--- | :--- | :--- | :--- |
| **Object Lakehouse** | MinIO (S3-compatible) | **Amazon S3** (`s3://retailpulse-curated`) | **Zero Code Change** (Boto3/S3 API drop-in) |
| **Relational DWH** | PostgreSQL 15 | **Amazon RDS PostgreSQL** / **Snowflake** | **Zero Code Change** (SQLAlchemy connection swap) |
| **Streaming Broker** | Redpanda (Kafka-compatible) | **Amazon MSK** / **Confluent Cloud** | **Zero Code Change** (Bootstrap server swap) |
| **Knowledge Graph** | Neo4j Community (Docker) | **Neo4j AuraDB Enterprise** / **Amazon Neptune** | **Zero Code Change** (Bolt URI swap) |
| **Microservices** | FastAPI (Ports 8001–8003) | **AWS ECS Fargate** + **Application Load Balancer** | Containerized (Dockerfiles provided) |
| **Dashboard** | Streamlit (Port 8501) | **AWS ECS Fargate** / **AWS App Runner** | Containerized |
| **ML Tracking** | Local MLflow (SQLite) | **AWS Managed MLflow** (Amazon SageMaker) | `MLFLOW_TRACKING_URI` swap |

---

## 2. Configuration Swaps (`.env` Delta)

To deploy to AWS, update `.env` with the following production credentials:

```env
# ==========================================
# PRODUCTION AWS CLOUD ENVIRONMENT
# ==========================================

# 1. Object Storage (AWS S3)
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=us-east-1
S3_BUCKET_RAW=retailpulse-production-raw-us-east-1
S3_BUCKET_CURATED=retailpulse-production-curated-us-east-1
MINIO_ENDPOINT=   # Left empty to enable standard AWS S3 endpoint routing

# 2. Relational Warehouse (AWS RDS PostgreSQL)
POSTGRES_HOST=retailpulse-warehouse.c9ak4dummy.us-east-1.rds.amazonaws.com
POSTGRES_PORT=5432
POSTGRES_DB=retailpulse_prod
POSTGRES_USER=retailpulse_admin
POSTGRES_PASSWORD=SecureEnterprisePassword2026!

# 3. Streaming Bus (Amazon MSK / Confluent)
KAFKA_BOOTSTRAP_SERVERS=b-1.retailpulse-msk.dummy.us-east-1.kafka.amazonaws.com:9092,b-2.retailpulse-msk.dummy.us-east-1.kafka.amazonaws.com:9092

# 4. Knowledge Graph (Neo4j AuraDB)
NEO4J_URI=neo4j+s://a1b2c3d4.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=SecureAuraDBPassword2026!

# 5. MLOps Experiment Tracking (Amazon SageMaker / Managed MLflow)
MLFLOW_TRACKING_URI=https://retailpulse-mlflow.sagemaker.us-east-1.amazonaws.com
```

---

## 3. ECS Fargate Container Deployment Architecture

```mermaid
flowchart TD
    subgraph AWS VPC
        ALB[AWS Application Load Balancer]
        
        subgraph Public Subnets
            ECS_DASH[Streamlit Dashboard Service<br/>Port 8501]
        end
        
        subgraph Private Subnets
            ECS_PRED[Prediction Service<br/>Port 8001]
            ECS_ANOM[Anomaly Service<br/>Port 8002]
            ECS_INGEST[Ingestion Service<br/>Port 8003]
        end
        
        subgraph Managed Storage & Data Layers
            S3[(Amazon S3<br/>Raw & Curated Lakehouse)]
            RDS[(Amazon RDS PostgreSQL<br/>Warehouse Tables)]
            MSK[(Amazon MSK<br/>Kafka Streaming Bus)]
            AURA[(Neo4j AuraDB<br/>Knowledge Graph)]
        end
    end
    
    ALB --> ECS_DASH
    ALB --> ECS_PRED
    ALB --> ECS_ANOM
    ALB --> ECS_INGEST
    
    ECS_INGEST --> MSK
    MSK --> S3
    S3 --> RDS
    S3 --> AURA
    ECS_PRED --> RDS
    ECS_ANOM --> RDS
```

---

## 4. Production CI/CD & Deployment Steps

1. **Build Container Images**:
   ```bash
   docker build -t retailpulse/prediction-service:v1.0 -f services/prediction_service/Dockerfile .
   docker build -t retailpulse/anomaly-service:v1.0 -f services/anomaly_service/Dockerfile .
   docker build -t retailpulse/dashboard:v1.0 -f dashboard/Dockerfile .
   ```
2. **Push to Amazon ECR**:
   ```bash
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <aws_account_id>.dkr.ecr.us-east-1.amazonaws.com
   docker push <aws_account_id>.dkr.ecr.us-east-1.amazonaws.com/retailpulse/prediction-service:v1.0
   ```
3. **Execute Database & Lakehouse Migrations**:
   ```bash
   python warehouse/load_warehouse.py
   python graph/load_graph.py
   ```
