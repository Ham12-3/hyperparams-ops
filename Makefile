.PHONY: help build up down logs worker-logs backend-logs dashboard-logs \
       k8s-minikube k8s-kind k8s-teardown k8s-status k8s-logs \
       clean restart

COMPOSE = docker compose
HELM_CHART = k8s/helm/hyperparams-ops
K8S_NS = hyperparams-ops

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------------------
# Docker Compose (local dev)
# ---------------------------------------------------------------------------

build: ## Build all Docker images
	$(COMPOSE) build

up: ## Start all services with docker-compose
	$(COMPOSE) up -d

up-build: ## Build and start all services
	$(COMPOSE) up -d --build

down: ## Stop all services
	$(COMPOSE) down

restart: ## Restart all services
	$(COMPOSE) restart

logs: ## Tail all service logs
	$(COMPOSE) logs -f

worker-logs: ## Tail worker logs
	$(COMPOSE) logs -f worker

backend-logs: ## Tail backend logs
	$(COMPOSE) logs -f backend

dashboard-logs: ## Tail dashboard logs
	$(COMPOSE) logs -f dashboard

scale-workers: ## Scale workers (usage: make scale-workers N=4)
	$(COMPOSE) up -d --scale worker=$(N)

ps: ## Show running containers
	$(COMPOSE) ps

# ---------------------------------------------------------------------------
# Kubernetes (Minikube / Kind)
# ---------------------------------------------------------------------------

k8s-minikube: ## Deploy to Minikube
	bash scripts/setup-minikube.sh

k8s-kind: ## Deploy to Kind
	bash scripts/setup-kind.sh

k8s-status: ## Show K8s pod status
	kubectl get pods -n $(K8S_NS)
	@echo ""
	kubectl get jobs -n $(K8S_NS)

k8s-logs: ## Tail worker logs in K8s
	kubectl logs -f -l app=hpo-worker -n $(K8S_NS) --max-log-requests=10

k8s-backend-logs: ## Tail backend logs in K8s
	kubectl logs -f -l app=backend -n $(K8S_NS)

k8s-port-forward: ## Port-forward backend and mlflow
	@echo "Backend:  http://localhost:8000"
	@echo "MLflow:   http://localhost:5000"
	@echo "Press Ctrl+C to stop"
	kubectl port-forward svc/backend 8000:8000 -n $(K8S_NS) &
	kubectl port-forward svc/mlflow 5000:5000 -n $(K8S_NS)

k8s-teardown: ## Tear down K8s deployment
	helm uninstall hyperparams-ops -n $(K8S_NS) || true
	kubectl delete namespace $(K8S_NS) || true

k8s-teardown-kind: ## Delete the Kind cluster entirely
	kind delete cluster --name hyperparams-ops

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

clean: ## Remove volumes and built images
	$(COMPOSE) down -v --rmi local
