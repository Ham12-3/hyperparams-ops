#!/bin/bash
set -euo pipefail

# Minikube setup script for hyperparams-ops
# Starts Minikube, builds images, and deploys the Helm chart.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
HELM_CHART="$PROJECT_DIR/k8s/helm/hyperparams-ops"

echo "=== Hyperparams Ops - Minikube Setup ==="

# Check prerequisites
for cmd in minikube kubectl helm docker; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "ERROR: $cmd is not installed"
        exit 1
    fi
done

# Start Minikube if not running
if ! minikube status | grep -q "Running"; then
    echo "Starting Minikube..."
    minikube start --memory=8192 --cpus=4 --driver=docker
else
    echo "Minikube is already running"
fi

# Point Docker to Minikube's daemon
echo "Configuring Docker to use Minikube..."
eval "$(minikube docker-env)"

# Build images
echo "Building Docker images..."
docker build -t hyperparams-ops-worker:latest "$PROJECT_DIR/worker"
docker build -t hyperparams-ops-backend:latest "$PROJECT_DIR/backend"
docker build -t hyperparams-ops-dashboard:latest "$PROJECT_DIR/dashboard"
docker build -t hyperparams-ops-mlflow:latest "$PROJECT_DIR/mlflow"

# Deploy with Helm
echo "Deploying Helm chart..."
helm upgrade --install hyperparams-ops "$HELM_CHART" \
    --namespace hyperparams-ops \
    --create-namespace \
    --set worker.image=hyperparams-ops-worker:latest \
    --set backend.image=hyperparams-ops-backend:latest \
    --set dashboard.image=hyperparams-ops-dashboard:latest \
    --set mlflow.image=hyperparams-ops-mlflow:latest

# Wait for pods
echo "Waiting for pods to be ready..."
kubectl wait --for=condition=ready pod -l app=postgres -n hyperparams-ops --timeout=120s
kubectl wait --for=condition=ready pod -l app=redis -n hyperparams-ops --timeout=60s
kubectl wait --for=condition=ready pod -l app=mlflow -n hyperparams-ops --timeout=120s
kubectl wait --for=condition=ready pod -l app=backend -n hyperparams-ops --timeout=60s

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Access the services:"
echo "  Dashboard:  $(minikube service dashboard -n hyperparams-ops --url 2>/dev/null || echo 'Run: minikube service dashboard -n hyperparams-ops')"
echo "  MLflow:     kubectl port-forward svc/mlflow 5000:5000 -n hyperparams-ops"
echo "  Backend:    kubectl port-forward svc/backend 8000:8000 -n hyperparams-ops"
echo ""
echo "Check status:  kubectl get pods -n hyperparams-ops"
echo "View logs:     kubectl logs -f job/hpo-worker -n hyperparams-ops"
