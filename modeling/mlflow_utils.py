import os
import sys
import pathlib
import mlflow
from dotenv import load_dotenv

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv()

def setup_mlflow(experiment_name: str = "retailpulse-demand-forecasting"):
    """
    Configures MLflow tracking URI with automatic local SQLite fallback on D: drive,
    ensuring zero external accounts required for full MLOps lifecycle.
    """
    db_path = os.path.join(PROJECT_ROOT, "data", "mlflow.db")
    mlruns_dir = os.path.join(PROJECT_ROOT, "data", "mlruns")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    os.makedirs(mlruns_dir, exist_ok=True)

    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", None)
    use_sqlite = True
    if tracking_uri and tracking_uri.startswith("http"):
        try:
            import urllib.request
            urllib.request.urlopen(tracking_uri, timeout=1)
            use_sqlite = False
        except Exception:
            use_sqlite = True

    if use_sqlite:
        norm_db = db_path.replace("\\", "/")
        tracking_uri = f"sqlite:///{norm_db}"

    mlflow.set_tracking_uri(tracking_uri)

    artifact_uri = pathlib.Path(mlruns_dir).resolve().as_uri()
    experiment = mlflow.get_experiment_by_name(experiment_name)
    if experiment is None:
        try:
            mlflow.create_experiment(
                name=experiment_name,
                artifact_location=artifact_uri
            )
        except Exception:
            pass
    mlflow.set_experiment(experiment_name)
    return tracking_uri

def log_experiment_run(
    run_name: str,
    model_type: str,
    params: dict,
    metrics: dict,
    tags: dict = None,
    model_artifact_path: str = None
):
    """
    Logs parameters, metrics, tags, and model binaries to active MLflow run.
    """
    setup_mlflow()
    with mlflow.start_run(run_name=run_name):
        # 1. Log Tags
        run_tags = {"model_type": model_type}
        if tags:
            run_tags.update(tags)
        mlflow.set_tags(run_tags)

        # 2. Log Hyperparameters
        if params:
            mlflow.log_params(params)

        # 3. Log Evaluation Metrics
        if metrics:
            mlflow.log_metrics(metrics)

        # 4. Log Artifacts
        if model_artifact_path and os.path.exists(model_artifact_path):
            try:
                mlflow.log_artifact(model_artifact_path, artifact_path="model_package")
            except Exception as ae:
                print(f"Notice: Model artifact file logging skipped ({ae})")

        run_id = mlflow.active_run().info.run_id
        print(f"Logged MLflow run '{run_name}' (ID: {run_id}) with metrics: {metrics}")
        return run_id
