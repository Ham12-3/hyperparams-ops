# Hyperparams Ops

Distributed hyperparameter optimization platform built with Optuna, Kubernetes, MLflow, and a real-time React dashboard.

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   React      │◄───│  FastAPI     │◄───│  Redis       │
│   Dashboard  │ WS │  Backend     │ Sub│  (pub/sub)   │
└─────────────┘     └──────┬──────┘     └──────▲──────┘
                           │                    │ Pub
                    ┌──────▼──────┐     ┌──────┴──────┐
                    │  PostgreSQL  │◄───│  Optuna      │
                    │  (Optuna DB) │    │  Workers     │
                    └─────────────┘     └──────┬──────┘
                                               │ Log
                                        ┌──────▼──────┐
                                        │   MLflow     │
                                        │   Server     │
                                        └─────────────┘
```

**Components:**
- **Optuna Workers** - Run HPO trials with PyTorch/CIFAR-10, log to MLflow, publish progress to Redis
- **PostgreSQL** - Shared storage backend for Optuna (distributed study coordination)
- **Redis** - Pub/sub for real-time trial updates from workers to dashboard
- **MLflow** - Experiment tracking (parameters, metrics, artifacts)
- **FastAPI Backend** - REST API + WebSocket for study management and live updates
- **React Dashboard** - Real-time monitoring with optimization charts and controls
- **K8s Resource Manager** - Launches/monitors/scales worker pods via kubernetes Python client

## Prerequisites

- Docker and Docker Compose
- For K8s deployment: `kubectl`, `helm`, and either `minikube` or `kind`
- Node.js 20+ (only if developing the dashboard outside Docker)

## Quick Start (Docker Compose)

This is the fastest way to get everything running locally.

```bash
# Copy environment config
cp .env.example .env

# Build and start all services
make up-build

# Or step by step:
make build
make up
```

**Access:**
| Service   | URL                        |
|-----------|----------------------------|
| Dashboard | http://localhost:3000       |
| Backend   | http://localhost:8000       |
| MLflow    | http://localhost:5000       |
| API Docs  | http://localhost:8000/docs  |

**Useful commands:**
```bash
make logs              # Tail all logs
make worker-logs       # Tail worker logs only
make scale-workers N=4 # Scale to 4 workers
make down              # Stop everything
make clean             # Stop and remove volumes
```

## Kubernetes Deployment (Local)

### Option A: Minikube

```bash
make k8s-minikube
```

### Option B: Kind

```bash
make k8s-kind
```

Both scripts will:
1. Create the cluster (if needed)
2. Build Docker images
3. Load images into the cluster
4. Deploy the Helm chart
5. Wait for all pods to be ready

**After deployment:**
```bash
make k8s-status         # Check pod status
make k8s-port-forward   # Access backend (8000) and MLflow (5000)
make k8s-logs           # Tail worker logs
make k8s-teardown       # Remove the Helm release
```

## Configuration

All configuration is via environment variables. In Docker Compose mode, edit `.env`. In K8s mode, edit `k8s/helm/hyperparams-ops/values.yaml`.

### Study Configuration

| Variable       | Default       | Description                        |
|----------------|---------------|------------------------------------|
| `STUDY_NAME`   | cifar10-hpo   | Optuna study name                  |
| `N_TRIALS`     | 20            | Trials per worker                  |
| `MAX_EPOCHS`   | 10            | Max training epochs per trial      |
| `PRUNER_TYPE`  | hyperband     | Pruner type (hyperband or median)  |

### Search Space

| Variable         | Default                          | Description            |
|------------------|----------------------------------|------------------------|
| `LR_LOW`         | 1e-5                             | Learning rate lower    |
| `LR_HIGH`        | 1e-1                             | Learning rate upper    |
| `BATCH_SIZES`    | [32, 64, 128]                    | Batch size choices     |
| `NUM_LAYERS_LOW` | 2                                | Min conv layers        |
| `NUM_LAYERS_HIGH`| 5                                | Max conv layers        |
| `DROPOUT_LOW`    | 0.1                              | Min dropout            |
| `DROPOUT_HIGH`   | 0.5                              | Max dropout            |
| `OPTIMIZERS`     | ["adam","sgd","adamw","rmsprop"]  | Optimizer choices      |

## API Reference

| Method | Endpoint                  | Description                    |
|--------|---------------------------|--------------------------------|
| GET    | `/studies`                | List all studies               |
| POST   | `/studies`                | Create a new study             |
| GET    | `/studies/{name}/trials`  | Get all trials for a study     |
| GET    | `/studies/{name}/best`    | Get the best trial             |
| GET    | `/studies/{name}/stats`   | Resource usage and pod status  |
| POST   | `/studies/{name}/stop`    | Stop a running study           |
| POST   | `/studies/{name}/scale`   | Scale workers up/down          |
| WS     | `/ws/studies/{name}`      | Live trial update stream       |

Interactive docs available at `http://localhost:8000/docs` when the backend is running.

## Project Structure

```
hyperparams-ops/
├── worker/                 # Optuna worker (PyTorch CIFAR-10)
│   ├── Dockerfile
│   ├── worker.py           # Trial runner with Redis pub/sub + MLflow
│   ├── objective.py        # CNN model and training loop
│   └── requirements.txt
├── backend/                # FastAPI backend
│   ├── Dockerfile
│   ├── main.py             # App entry point
│   ├── routers/
│   │   └── studies.py      # REST endpoints
│   ├── services/
│   │   ├── optuna_service.py  # Optuna study operations
│   │   └── k8s_manager.py     # K8s pod lifecycle management
│   ├── ws/
│   │   └── handler.py      # WebSocket handler (Redis → client)
│   └── requirements.txt
├── dashboard/              # React dashboard
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   └── src/
│       ├── App.js
│       ├── pages/
│       │   ├── StudyList.js
│       │   └── StudyDetail.js
│       ├── components/
│       │   ├── BestTrialCard.js
│       │   ├── OptimizationChart.js
│       │   ├── ParallelCoordinatePlot.js
│       │   ├── TrialsTable.js
│       │   ├── WorkerPods.js
│       │   └── StudyControls.js
│       └── hooks/
│           └── useWebSocket.js
├── mlflow/                 # MLflow server
│   ├── Dockerfile
│   └── entrypoint.sh
├── k8s/helm/hyperparams-ops/  # Helm chart
│   ├── Chart.yaml
│   ├── values.yaml
│   └── templates/
│       ├── namespace.yaml
│       ├── configmap.yaml
│       ├── postgres-statefulset.yaml
│       ├── redis-deployment.yaml
│       ├── mlflow-deployment.yaml
│       ├── backend-deployment.yaml
│       ├── dashboard-deployment.yaml
│       └── worker-job.yaml
├── scripts/
│   ├── setup-minikube.sh
│   └── setup-kind.sh
├── docker-compose.yaml
├── Makefile
├── .env.example
└── .gitignore
```

## How It Works

1. **Create a study** via the dashboard or API (`POST /studies`)
2. **Workers connect** to the shared Optuna study via PostgreSQL
3. Each worker **samples hyperparameters**, trains a CNN on CIFAR-10, and reports intermediate results
4. **Pruners** (Hyperband/Median) kill underperforming trials early
5. Workers **publish progress** to Redis pub/sub channels
6. The backend **streams updates** via WebSocket to the dashboard
7. All trials are **logged to MLflow** with full parameter/metric tracking
8. In K8s mode, the **resource manager** handles pod lifecycle, scaling, and cleanup
