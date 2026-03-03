"""WebSocket handler for streaming live trial updates from Redis pub/sub."""

import asyncio
import json
import logging
import os

import redis.asyncio as aioredis
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger("ws-handler")

REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))


async def study_websocket(websocket: WebSocket, study_name: str) -> None:
    """Stream trial updates for a study via WebSocket.

    Subscribes to the Redis pub/sub channel for the study and forwards
    all messages to the connected WebSocket client.
    """
    await websocket.accept()
    logger.info("WebSocket connected for study: %s", study_name)

    redis_client = aioredis.Redis(
        host=REDIS_HOST, port=REDIS_PORT, decode_responses=True
    )
    pubsub = redis_client.pubsub()
    channel = f"study:{study_name}:trials"

    try:
        await pubsub.subscribe(channel)
        logger.info("Subscribed to Redis channel: %s", channel)

        while True:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True, timeout=1.0
            )
            if message and message["type"] == "message":
                data = json.loads(message["data"])
                await websocket.send_json(data)

            # Small yield to prevent busy loop
            await asyncio.sleep(0.05)

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for study: %s", study_name)
    except Exception as e:
        logger.error("WebSocket error for study %s: %s", study_name, e)
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()
        await redis_client.close()
