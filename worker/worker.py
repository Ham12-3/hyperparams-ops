"""Optuna worker that connects to a shared study via PostgreSQL.

Runs hyperparameter trials, logs to MLflow, and publishes progress to Redis.
"""

import json
import os
import time
import logging
from typing import Any

import mlflow
import optuna
import redis
from optuna.pruners import HyperbandPruner, MedianPruner

from objective import train_and_evaluate

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("hyperparams-worker")

# ---------------------------------------------------------------------------
# Configuration from environment
# ---------------------------------------------------------------------------
POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "optuna")
POSTGRES_USER = os.environ.get("POSTGRES_USER", "optuna")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "optuna")

REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))

MLFLOW_TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI", "http://mlflow:5000")

STUDY_NAME = os.environ.get("STUDY_NAME", "cifar10-hpo")
N_TRIALS = int(os.environ.get("N_TRIALS", "20"))
MAX_EPOCHS = int(os.environ.get("MAX_EPOCHS", "10"))
PRUNER_TYPE = os.environ.get("PRUNER_TYPE", "hyperband")
WORKER_ID = os.environ.get("HOSTNAME", "worker-local")

# Search space bounds (configurable via env)
LR_LOW = float(os.environ.get("LR_LOW", "1e-5"))
LR_HIGH = float(os.environ.get("LR_HIGH", "1e-1"))
BATCH_SIZES = json.loads(os.environ.get("BATCH_SIZES", "[32, 64, 128]"))
NUM_LAYERS_LOW = int(os.environ.get("NUM_LAYERS_LOW", "2"))
NUM_LAYERS_HIGH = int(os.environ.get("NUM_LAYERS_HIGH", "5"))
DROPOUT_LOW = float(os.environ.get("DROPOUT_LOW", "0.1"))
DROPOUT_HIGH = float(os.environ.get("DROPOUT_HIGH", "0.5"))
OPTIMIZERS = json.loads(os.environ.get("OPTIMIZERS", '["adam", "sgd", "adamw", "rmsprop"]'))


def get_storage_url() -> str:
    """Build the PostgreSQL connection URL for Optuna."""
    return (
        f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
        f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )


def get_redis_client() -> redis.Redis:  # type: ignore[type-arg]
    """Create a Redis client for pub/sub."""
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


def get_pruner() -> optuna.pruners.BasePruner:
    """Create the configured pruner."""
    if PRUNER_TYPE == "median":
        return MedianPruner(n_startup_trials=5, n_warmup_steps=3)
    return HyperbandPruner(min_resource=1, max_resource=MAX_EPOCHS, reduction_factor=3)


def publish_trial_update(
    redis_client: redis.Redis,  # type: ignore[type-arg]
    study_name: str,
    trial_number: int,
    status: str,
    params: dict[str, Any],
    value: float | None = None,
    epoch: int | None = None,
    intermediate_value: float | None = None,
) -> None:
    """Publish a trial update to the Redis channel."""
    message = {
        "study_name": study_name,
        "trial_number": trial_number,
        "worker_id": WORKER_ID,
        "status": status,
        "params": params,
        "value": value,
        "epoch": epoch,
        "intermediate_value": intermediate_value,
        "timestamp": time.time(),
    }
    channel = f"study:{study_name}:trials"
    redis_client.publish(channel, json.dumps(message))
    logger.info("Published update for trial %d: %s", trial_number, status)


def objective(trial: optuna.Trial) -> float:
    """Optuna objective function with MLflow logging and Redis updates."""
    redis_client = get_redis_client()

    # Sample hyperparameters
    lr = trial.suggest_float("learning_rate", LR_LOW, LR_HIGH, log=True)
    batch_size = trial.suggest_categorical("batch_size", BATCH_SIZES)
    num_layers = trial.suggest_int("num_layers", NUM_LAYERS_LOW, NUM_LAYERS_HIGH)
    dropout = trial.suggest_float("dropout", DROPOUT_LOW, DROPOUT_HIGH)
    optimizer_name = trial.suggest_categorical("optimizer", OPTIMIZERS)

    params = {
        "learning_rate": lr,
        "batch_size": batch_size,
        "num_layers": num_layers,
        "dropout": dropout,
        "optimizer": optimizer_name,
    }

    # Publish trial started
    publish_trial_update(
        redis_client, STUDY_NAME, trial.number, "running", params
    )

    # MLflow tracking
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(STUDY_NAME)

    with mlflow.start_run(run_name=f"trial-{trial.number}"):
        mlflow.log_params(params)
        mlflow.set_tag("worker_id", WORKER_ID)
        mlflow.set_tag("trial_number", str(trial.number))

        def report_callback(epoch: int, accuracy: float) -> None:
            """Report intermediate values for pruning and publish to Redis."""
            trial.report(accuracy, epoch)
            mlflow.log_metric("val_accuracy", accuracy, step=epoch)

            publish_trial_update(
                redis_client,
                STUDY_NAME,
                trial.number,
                "running",
                params,
                epoch=epoch,
                intermediate_value=accuracy,
            )

            if trial.should_prune():
                publish_trial_update(
                    redis_client, STUDY_NAME, trial.number, "pruned", params,
                    value=accuracy,
                )
                mlflow.set_tag("pruned", "true")
                raise optuna.TrialPruned()

        try:
            accuracy = train_and_evaluate(
                learning_rate=lr,
                batch_size=batch_size,
                num_layers=num_layers,
                dropout=dropout,
                optimizer_name=optimizer_name,
                max_epochs=MAX_EPOCHS,
                report_callback=report_callback,
            )
        except optuna.TrialPruned:
            raise
        except Exception as e:
            publish_trial_update(
                redis_client, STUDY_NAME, trial.number, "failed", params
            )
            mlflow.set_tag("error", str(e))
            raise

        mlflow.log_metric("best_val_accuracy", accuracy)

        publish_trial_update(
            redis_client, STUDY_NAME, trial.number, "complete", params,
            value=accuracy,
        )

    return accuracy


def create_study_with_retry(max_retries: int = 10) -> optuna.Study:
    """Create or load a study with retry logic for race conditions.

    Multiple workers starting simultaneously can race on schema creation.
    This retries with exponential backoff to handle that gracefully.
    """
    storage_url = get_storage_url()
    pruner = get_pruner()

    for attempt in range(max_retries):
        try:
            return optuna.create_study(
                study_name=STUDY_NAME,
                storage=storage_url,
                direction="maximize",
                pruner=pruner,
                load_if_exists=True,
            )
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            wait = min(2 ** attempt, 30)
            logger.warning(
                "Study creation attempt %d failed (%s), retrying in %ds",
                attempt + 1, e, wait,
            )
            time.sleep(wait)

    raise RuntimeError("Unreachable")


def main() -> None:
    """Entry point: create or load study and run trials."""
    logger.info("Worker %s starting", WORKER_ID)
    logger.info("Study: %s | Trials: %d | Pruner: %s", STUDY_NAME, N_TRIALS, PRUNER_TYPE)

    study = create_study_with_retry()

    logger.info("Starting %d trials", N_TRIALS)
    study.optimize(objective, n_trials=N_TRIALS)

    logger.info(
        "Worker %s finished. Best trial: #%d with value %.4f",
        WORKER_ID,
        study.best_trial.number,
        study.best_trial.value,
    )


if __name__ == "__main__":
    main()
