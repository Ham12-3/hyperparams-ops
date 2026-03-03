"""REST API routes for Optuna study management."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services import k8s_manager, optuna_service

logger = logging.getLogger("studies-router")
router = APIRouter(prefix="/studies", tags=["studies"])


class CreateStudyRequest(BaseModel):
    """Request body for creating a new study."""

    name: str
    direction: str = "maximize"
    pruner_type: str = "hyperband"
    search_space: dict[str, Any] | None = None
    num_workers: int = 2
    n_trials_per_worker: int = 10


class ScaleRequest(BaseModel):
    """Request body for scaling workers."""

    num_workers: int
    n_trials_per_worker: int = 5


class StopStudyRequest(BaseModel):
    """Request body for stopping a study."""

    cleanup: bool = True


@router.get("")
def list_studies() -> list[dict[str, Any]]:
    """List all Optuna studies."""
    try:
        return optuna_service.list_studies()
    except Exception as e:
        logger.error("Failed to list studies: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{name}/trials")
def get_trials(name: str) -> list[dict[str, Any]]:
    """Get all trials for a study."""
    try:
        return optuna_service.get_trials(name)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Study '{name}' not found")
    except Exception as e:
        logger.error("Failed to get trials for %s: %s", name, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{name}/best")
def get_best_trial(name: str) -> dict[str, Any]:
    """Get the best trial for a study."""
    try:
        return optuna_service.get_best_trial(name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to get best trial for %s: %s", name, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{name}/stats")
def get_study_stats(name: str) -> dict[str, Any]:
    """Get study statistics including active pods and trial counts."""
    try:
        trials = optuna_service.get_trials(name)
        pods = k8s_manager.get_worker_pods(name)

        completed = sum(1 for t in trials if t["state"] == "COMPLETE")
        running = sum(1 for t in trials if t["state"] == "RUNNING")
        pruned = sum(1 for t in trials if t["state"] == "PRUNED")
        failed = sum(1 for t in trials if t["state"] == "FAIL")

        active_pods = [p for p in pods if p["phase"] in ("Running", "Pending")]

        return {
            "total_trials": len(trials),
            "completed": completed,
            "running": running,
            "pruned": pruned,
            "failed": failed,
            "active_pods": len(active_pods),
            "pods": pods,
        }
    except Exception as e:
        logger.error("Failed to get stats for %s: %s", name, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
def create_study(req: CreateStudyRequest) -> dict[str, Any]:
    """Create a new study and optionally launch workers."""
    try:
        study_info = optuna_service.create_study(
            name=req.name,
            direction=req.direction,
            pruner_type=req.pruner_type,
            search_space=req.search_space,
        )

        jobs = k8s_manager.launch_workers(
            study_name=req.name,
            count=req.num_workers,
            n_trials_per_worker=req.n_trials_per_worker,
            env_overrides=req.search_space or {},
        )

        return {
            **study_info,
            "workers_launched": len(jobs),
            "job_names": jobs,
        }
    except Exception as e:
        logger.error("Failed to create study: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{name}/stop")
def stop_study(name: str, req: StopStudyRequest) -> dict[str, Any]:
    """Stop a running study by cleaning up worker jobs."""
    try:
        cleaned = 0
        if req.cleanup:
            cleaned = k8s_manager.cleanup_completed_jobs(name)

        return {
            "study": name,
            "jobs_cleaned": cleaned,
            "status": "stopped",
        }
    except Exception as e:
        logger.error("Failed to stop study %s: %s", name, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{name}/scale")
def scale_workers(name: str, req: ScaleRequest) -> dict[str, Any]:
    """Scale workers for a study."""
    try:
        return k8s_manager.scale_workers(
            study_name=name,
            desired_count=req.num_workers,
            n_trials_per_worker=req.n_trials_per_worker,
        )
    except Exception as e:
        logger.error("Failed to scale workers for %s: %s", name, e)
        raise HTTPException(status_code=500, detail=str(e))
