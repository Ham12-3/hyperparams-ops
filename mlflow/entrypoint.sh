#!/bin/bash
set -e

BACKEND_URI="postgresql://${POSTGRES_USER:-optuna}:${POSTGRES_PASSWORD:-optuna}@${POSTGRES_HOST:-postgres}:${POSTGRES_PORT:-5432}/${POSTGRES_DB:-optuna}"

exec mlflow server \
  --host 0.0.0.0 \
  --port 5000 \
  --backend-store-uri "$BACKEND_URI" \
  --default-artifact-root /mlflow/artifacts
