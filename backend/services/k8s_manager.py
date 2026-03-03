"""Kubernetes resource manager for worker pods.

Uses the kubernetes Python client to launch, monitor, scale, and clean up
worker Job pods for Optuna hyperparameter optimization.
"""

import logging
import os
import time
from typing import Any

logger = logging.getLogger("k8s-manager")

K8S_NAMESPACE = os.environ.get("K8S_NAMESPACE", "hyperparams-ops")
WORKER_IMAGE = os.environ.get("WORKER_IMAGE", "hyperparams-ops-worker:latest")
MAX_PARALLEL_TRIALS = int(os.environ.get("MAX_PARALLEL_TRIALS", "4"))
MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "3"))
ENABLE_K8S = os.environ.get("ENABLE_K8S", "false").lower() == "true"


def _get_clients() -> tuple[Any, Any]:
    """Get Kubernetes API clients, loading config appropriately."""
    from kubernetes import client, config

    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()

    return client.CoreV1Api(), client.BatchV1Api()


def _build_worker_job(
    study_name: str,
    job_index: int,
    n_trials: int = 5,
    env_overrides: dict[str, str] | None = None,
) -> Any:
    """Build a Kubernetes Job spec for a worker pod."""
    from kubernetes import client

    job_name = f"hpo-worker-{study_name}-{job_index}-{int(time.time())}"

    env_vars = [
        client.V1EnvVar(name="STUDY_NAME", value=study_name),
        client.V1EnvVar(name="N_TRIALS", value=str(n_trials)),
    ]

    # Add env from ConfigMap
    env_from = [
        client.V1EnvFromSource(
            config_map_ref=client.V1ConfigMapEnvSource(name="hyperparams-config")
        )
    ]

    if env_overrides:
        for k, v in env_overrides.items():
            env_vars.append(client.V1EnvVar(name=k, value=v))

    container = client.V1Container(
        name="worker",
        image=WORKER_IMAGE,
        env=env_vars,
        env_from=env_from,
        resources=client.V1ResourceRequirements(
            requests={"cpu": "500m", "memory": "1Gi"},
            limits={"cpu": "2", "memory": "4Gi"},
        ),
    )

    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(
            labels={
                "app": "hpo-worker",
                "study": study_name,
            }
        ),
        spec=client.V1PodSpec(
            containers=[container],
            restart_policy="Never",
        ),
    )

    job = client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=client.V1ObjectMeta(
            name=job_name,
            namespace=K8S_NAMESPACE,
            labels={
                "app": "hpo-worker",
                "study": study_name,
            },
        ),
        spec=client.V1JobSpec(
            template=template,
            backoff_limit=MAX_RETRIES,
            ttl_seconds_after_finished=300,
        ),
    )
    return job


def launch_workers(
    study_name: str,
    count: int | None = None,
    n_trials_per_worker: int = 5,
    env_overrides: dict[str, str] | None = None,
) -> list[str]:
    """Launch worker pods for a study.

    Args:
        study_name: Name of the Optuna study.
        count: Number of workers to launch (defaults to MAX_PARALLEL_TRIALS).
        n_trials_per_worker: Number of trials each worker should run.
        env_overrides: Additional environment variables.

    Returns:
        List of created job names.
    """
    if not ENABLE_K8S:
        logger.warning("K8s not enabled; skipping worker launch")
        return []

    _, batch_api = _get_clients()
    num_workers = count or MAX_PARALLEL_TRIALS
    created_jobs: list[str] = []

    for i in range(num_workers):
        job = _build_worker_job(study_name, i, n_trials_per_worker, env_overrides)
        batch_api.create_namespaced_job(namespace=K8S_NAMESPACE, body=job)
        created_jobs.append(job.metadata.name)
        logger.info("Created job %s", job.metadata.name)

    return created_jobs


def get_worker_pods(study_name: str) -> list[dict[str, Any]]:
    """Get status of all worker pods for a study."""
    if not ENABLE_K8S:
        return []

    core_api, _ = _get_clients()
    pods = core_api.list_namespaced_pod(
        namespace=K8S_NAMESPACE,
        label_selector=f"app=hpo-worker,study={study_name}",
    )

    result = []
    for pod in pods.items:
        status = pod.status
        container_statuses = status.container_statuses or []
        resource_info: dict[str, Any] = {}

        if container_statuses:
            cs = container_statuses[0]
            resource_info = {
                "restart_count": cs.restart_count,
                "ready": cs.ready,
            }
            if cs.state.terminated:
                resource_info["exit_code"] = cs.state.terminated.exit_code
                resource_info["reason"] = cs.state.terminated.reason

        result.append({
            "name": pod.metadata.name,
            "phase": status.phase,
            "start_time": (
                status.start_time.isoformat() if status.start_time else None
            ),
            "node": pod.spec.node_name,
            **resource_info,
        })
    return result


def cleanup_completed_jobs(study_name: str) -> int:
    """Delete completed/failed jobs for a study.

    Returns:
        Number of jobs cleaned up.
    """
    if not ENABLE_K8S:
        return 0

    _, batch_api = _get_clients()
    jobs = batch_api.list_namespaced_job(
        namespace=K8S_NAMESPACE,
        label_selector=f"app=hpo-worker,study={study_name}",
    )

    cleaned = 0
    for job in jobs.items:
        conditions = job.status.conditions or []
        is_done = any(
            c.type in ("Complete", "Failed") and c.status == "True"
            for c in conditions
        )
        if is_done:
            batch_api.delete_namespaced_job(
                name=job.metadata.name,
                namespace=K8S_NAMESPACE,
                propagation_policy="Background",
            )
            cleaned += 1
            logger.info("Cleaned up job %s", job.metadata.name)

    return cleaned


def scale_workers(
    study_name: str,
    desired_count: int,
    n_trials_per_worker: int = 5,
) -> dict[str, Any]:
    """Scale workers to the desired count.

    Launches new workers or notes excess. K8s Jobs are immutable once created,
    so scaling down means we stop launching new ones; existing ones finish naturally.
    """
    if not ENABLE_K8S:
        return {"status": "k8s_disabled"}

    active_pods = [
        p for p in get_worker_pods(study_name) if p["phase"] in ("Running", "Pending")
    ]
    current_count = len(active_pods)

    if current_count < desired_count:
        new_jobs = launch_workers(
            study_name,
            count=desired_count - current_count,
            n_trials_per_worker=n_trials_per_worker,
        )
        return {
            "action": "scaled_up",
            "previous": current_count,
            "current": desired_count,
            "new_jobs": new_jobs,
        }

    return {
        "action": "no_change" if current_count == desired_count else "excess_running",
        "current": current_count,
        "desired": desired_count,
        "note": (
            "Excess workers will complete their current trials naturally"
            if current_count > desired_count
            else None
        ),
    }
