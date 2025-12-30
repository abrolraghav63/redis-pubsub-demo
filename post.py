import os
import logging
import threading

from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
import redis


# -------------------------
# Logging
# -------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger("post-service")


# -------------------------
# App
# -------------------------
app = FastAPI()


# -------------------------
# Config
# -------------------------
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

STATUS_KEY = "profile_service_status"
STATUS_CHANNEL = "profile_service_status_updates"


# -------------------------
# Redis client
# -------------------------
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=2
)


# -------------------------
# In-memory cache
# -------------------------
profile_service_status_cache = {
    "value": "down"   # SAFE DEFAULT
}


# -------------------------
# Pub/Sub listener
# -------------------------
def listen_for_status_updates():
    pubsub = redis_client.pubsub()
    pubsub.subscribe(STATUS_CHANNEL)

    logger.info("Subscribed to Redis channel: %s", STATUS_CHANNEL)

    for message in pubsub.listen():
        if message["type"] != "message":
            continue

        new_status = message["data"]
        profile_service_status_cache["value"] = new_status

        logger.info(
            "Received profile service status update via Pub/Sub: %s",
            new_status
        )


# -------------------------
# Startup logic
# -------------------------
@app.on_event("startup")
def startup():
    # 1. Bootstrap from Redis ONCE
    try:
        value = redis_client.get(STATUS_KEY)

        if value:
            profile_service_status_cache["value"] = value
            logger.info(
                "Bootstrapped profile_service_status from Redis: %s",
                value
            )
        else:
            logger.warning(
                "profile_service_status key missing at startup; using default"
            )

    except redis.exceptions.RedisError:
        logger.error(
            "Failed to bootstrap profile_service_status from Redis",
            exc_info=True
        )

    # 2. Start Pub/Sub listener thread
    thread = threading.Thread(
        target=listen_for_status_updates,
        daemon=True
    )
    thread.start()

    logger.info("Started Redis Pub/Sub listener thread")


# -------------------------
# API endpoint
# -------------------------
@app.get("/")
def root():
    if profile_service_status_cache["value"] == "up":
        return {"message": "hello from post service"}

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"message": "not available"}
    )
