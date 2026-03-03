#!/bin/bash
set -euo pipefail

# Kind setup script for hyperparams-ops
# Creates a Kind cluster, loads images, and deploys the Helm chart.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
HELM_CHART="$PROJECT_DIR/k8s/helm/hyperparams-ops"
CLUSTER_NAME="hyperparams-ops"

echo "=== Hyperparams Ops - Kind Setup ==="

# Check prerequisites
for cmd in kind kubectl helm docker; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "ERROR: $cmd is not installed"
        exit 1
    fi
done

# Create Kind cluster if it doesn't exist
if ! kind get clusters 2>/dev/null | grep -q "$CLUSTER_NAME"; then
    echo "Creating Kind cluster..."
    cat <<EOF | kind create cluster --name "$CLUSTER_NAME" --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
    extraPortMappings:
      - containerPort: 30080
        hostPort: 3000
        protocol: TCP
EOF
else
    echo "Kind cluster '$CLUSTER_NAME' already exists"
fi

kubectl cluster-info --context "kind-$CLUSTER_NAME"

# Build images
echo "Building Docker images..."
docker build -t hyperparams-ops-worker:latest "$PROJECT_DIR/worker"
docker build -t hyperparams-ops-backend:latest "$PROJECT_DIR/backend"
docker build -t hyperparams-ops-dashboard:latest "$PROJECT_DIR/dashboard"
docker build -t hyperparams-ops-mlflow:latest "$PROJECT_DIR/mlflow"

# Load images into Kind
echo "Loading images into Kind cluster..."
kind load docker-image hyperparams-ops-worker:latest --name "$CLUSTER_NAME"
kind load docker-image hyperparams-ops-backend:latest --name "$CLUSTER_NAME"
kind load docker-image hyperparams-ops-dashboard:latest --name "$CLUSTER_NAME"
kind load docker-image hyperparams-ops-mlflow:latest --name "$CLUSTER_NAME"

# Deploy with Helm
echo "Deploying Helm chart..."
helm upgrade --install hyperparams-ops "$HELM_CHART" \
    --namespace hyperparams-ops \
    --create-namespace

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
echo "  Dashboard:  http://localhost:3000 (via NodePort)"
echo "  MLflow:     kubectl port-forward svc/mlflow 5000:5000 -n hyperparams-ops"
echo "  Backend:    kubectl port-forward svc/backend 8000:8000 -n hyperparams-ops"
echo ""
echo "Check status:  kubectl get pods -n hyperparams-ops"
echo "View logs:     kubectl logs -f job/hpo-worker -n hyperparams-ops"
echo ""
echo "Teardown:      kind delete cluster --name $CLUSTER_NAME"
