.PHONY: ingest transform model anomaly backtest warehouse test run-all dashboard stream-produce stream-consume graph-load graph-features drift-report mlflow-ui

ingest:
	python ingestion/batch_loader.py
	python ingestion/iot_generator.py

stream-produce:
	python ingestion/stream_producer.py --max-events 200

stream-consume:
	python ingestion/stream_consumer.py --max-records 400

graph-load:
	python graph/load_graph.py

graph-features:
	python graph/graph_features.py

drift-report:
	python modeling/drift_monitor.py

mlflow-ui:
	mlflow ui --backend-store-uri sqlite:///data/mlflow.db --port 5000

transform:
	python transform/spark_jobs/sentiment_feature.py
	python transform/spark_jobs/clean_join.py
	python transform/data_quality.py

model:
	python modeling/train_prophet.py
	python modeling/train_xgboost.py
	python modeling/anomaly_detection.py

backtest:
	python modeling/backtest.py

warehouse:
	python warehouse/load_warehouse.py

test:
	pytest tests/ -v

run-all:
	@echo "=== Step 1: Ingestion ==="
	python ingestion/batch_loader.py
	python ingestion/iot_generator.py
	@echo "=== Step 2: Lakehouse Transformation ==="
	python transform/spark_jobs/clean_join.py
	python transform/data_quality.py
	@echo "=== Step 3: Knowledge Graph Sync & Feature Engineering ==="
	python graph/load_graph.py
	python graph/graph_features.py
	@echo "=== Step 4: ML Modeling & MLflow Experiment Tracking ==="
	python modeling/train_prophet.py
	python modeling/train_xgboost.py
	python modeling/anomaly_detection.py
	@echo "=== Step 5: Backtesting ==="
	python modeling/backtest.py
	@echo "=== Step 6: Distribution Drift Monitoring (Evidently AI) ==="
	python modeling/drift_monitor.py
	@echo "=== Step 7: Warehouse Sync ==="
	python warehouse/load_warehouse.py
	@echo "=== Step 8: Tests ==="
	pytest tests/ -v
	@echo "=== Full Pipeline Successfully Completed! ==="

dashboard:
	streamlit run dashboard/app.py

