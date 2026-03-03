"""Service layer for interacting with Optuna studies via PostgreSQL storage."""

import os
from typing import Any

import optuna
from optuna.pruners import HyperbandPruner, MedianPruner

POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "optuna")
POSTGRES_USER = os.environ.get("POSTGRES_USER", "optuna")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "optuna")


def get_storage_url() -> str:
    """Build the PostgreSQL connection URL."""
    return (
        f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
        f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )


def get_storage() -> optuna.storages.RDBStorage:
    """Create an Optuna RDB storage instance."""
    return optuna.storages.RDBStorage(url=get_storage_url())


def list_studies() -> list[dict[str, Any]]:
    """List all studies with summary info."""
    storage = get_storage()
    summaries = optuna.study.get_all_study_summaries(storage=storage)
    results = []
    for s in summaries:
        best_value = None
        if s.best_trial is not None:
            best_value = s.best_trial.value
        results.append({
            "name": s.study_name,
            "direction": s.direction.name if hasattr(s.direction, "name") else str(s.direction),
            "n_trials": s.n_trials,
            "best_value": best_value,
            "datetime_start": s.datetime_start.isoformat() if s.datetime_start else None,
        })
    return results


def get_study(name: str) -> optuna.Study:
    """Load an existing study by name."""
    return optuna.load_study(study_name=name, storage=get_storage_url())


def get_trials(name: str) -> list[dict[str, Any]]:
    """Get all trials for a study."""
    study = get_study(name)
    trials = []
    for t in study.trials:
        trials.append({
            "number": t.number,
            "state": t.state.name,
            "value": t.value,
            "params": t.params,
            "duration": (
                (t.datetime_complete - t.datetime_start).total_seconds()
                if t.datetime_complete and t.datetime_start
                else None
            ),
            "datetime_start": t.datetime_start.isoformat() if t.datetime_start else None,
            "datetime_complete": (
                t.datetime_complete.isoformat() if t.datetime_complete else None
            ),
            "intermediate_values": dict(t.intermediate_values),
        })
    return trials


def get_best_trial(name: str) -> dict[str, Any]:
    """Get the best trial for a study."""
    study = get_study(name)
    best = study.best_trial
    return {
        "number": best.number,
        "value": best.value,
        "params": best.params,
        "state": best.state.name,
        "datetime_start": best.datetime_start.isoformat() if best.datetime_start else None,
        "datetime_complete": (
            best.datetime_complete.isoformat() if best.datetime_complete else None
        ),
    }


def create_study(
    name: str,
    direction: str = "maximize",
    pruner_type: str = "hyperband",
    search_space: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a new Optuna study.

    Args:
        name: Study name.
        direction: Optimization direction (maximize or minimize).
        pruner_type: Pruner type (median or hyperband).
        search_space: Optional search space configuration (stored as user attr).

    Returns:
        Study summary dict.
    """
    if pruner_type == "median":
        pruner: optuna.pruners.BasePruner = MedianPruner(
            n_startup_trials=5, n_warmup_steps=3
        )
    else:
        pruner = HyperbandPruner(min_resource=1, max_resource=10, reduction_factor=3)

    study = optuna.create_study(
        study_name=name,
        storage=get_storage_url(),
        direction=direction,
        pruner=pruner,
        load_if_exists=True,
    )

    if search_space:
        study.set_user_attr("search_space", search_space)

    return {
        "name": study.study_name,
        "direction": direction,
        "pruner": pruner_type,
    }


def delete_study(name: str) -> None:
    """Delete a study by name."""
    optuna.delete_study(study_name=name, storage=get_storage_url())
