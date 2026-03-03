"""FastAPI backend for the hyperparameter optimization platform.

Provides REST endpoints for study management and WebSocket endpoints
for real-time trial updates via Redis pub/sub.
"""

import logging

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from routers.studies import router as studies_router
from ws.handler import study_websocket

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(
    title="Hyperparams Ops",
    description="Distributed Hyperparameter Optimization Platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(studies_router)


@app.websocket("/ws/studies/{study_name}")
async def websocket_endpoint(websocket: WebSocket, study_name: str) -> None:
    """WebSocket endpoint for streaming live trial updates."""
    await study_websocket(websocket, study_name)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}
