import sys
import os
import json
import logging
import asyncio
import asyncpg
import redis.asyncio as aioredis
from pathlib import Path
from fastapi import FastAPI
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load .env from repo root (one level above realtime/)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from routes import health, agents, events, ssh
from ws_manager import manager
from logging_utils import trace
from streams_consumer import StreamsConsumer

logging.basicConfig(
    level=getattr(logging, os.getenv("REALTIME_LOG_LEVEL", "INFO").upper()),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URL", "redis://localhost:6379/0"))

# Build DB_DSN from DATABASE_URL or individual POSTGRES_* vars
_database_url = os.getenv("DATABASE_URL")
if _database_url:
    DB_DSN = _database_url
else:
    _pg_host = os.getenv("POSTGRES_HOST", "localhost")
    _pg_port = os.getenv("POSTGRES_PORT", "5432")
    _pg_db   = os.getenv("POSTGRES_DB", "vector_db")
    _pg_user = os.getenv("POSTGRES_USER", "postgres")
    _pg_pass = os.getenv("POSTGRES_PASSWORD", "password")
    DB_DSN = f"postgresql://{_pg_user}:{_pg_pass}@{_pg_host}:{_pg_port}/{_pg_db}"

# SQLite override mapping
if DB_DSN.startswith("sqlite"):
    DB_DSN = None

@trace
async def redis_subscriber():
    """Background task to listen to Redis Pub/Sub channels from Django Celery.
    Gracefully retries with backoff if Redis is unavailable — never crashes the worker.
    """
    backoff = 2
    while True:
        redis_conn = None
        try:
            redis_conn = await aioredis.from_url(
                REDIS_URL,
                decode_responses=False,
                health_check_interval=30,   # keep-alive ping every 30s
            )
            pubsub = redis_conn.pubsub()

            await pubsub.subscribe(
                "deployment:progress", "system:notification", "system:compliance_alert"
            )
            await pubsub.psubscribe("agent:command:*")

            logger.info("Redis Pub/Sub connected — listening for events.")
            backoff = 2  # reset after successful connect

            async for message in pubsub.listen():
                if message["type"] not in ("message", "pmessage"):
                    continue
                try:
                    channel = (
                        message["channel"].decode()
                        if isinstance(message["channel"], bytes)
                        else message["channel"]
                    )
                    data = (
                        message["data"].decode()
                        if isinstance(message["data"], bytes)
                        else message["data"]
                    )

                    if channel == "deployment:progress":
                        env = json.loads(data)
                        dep_id = env.get("payload", {}).get("deployment_id")
                        if dep_id:
                            await manager.broadcast_to_deployment(dep_id, data)

                    elif channel.startswith("system:"):
                        await manager.broadcast_to_dashboard(data)

                    elif channel.startswith("agent:command:"):
                        agent_id = channel.split(":")[-1]
                        logger.info(f"Command received for Agent {agent_id} via Redis.")
                        delivered = await manager.send_to_agent(agent_id, data)
                        if delivered:
                            logger.info(f"Command successfully delivered to Agent {agent_id}.")
                        else:
                            logger.warning(f"Failed to deliver command: Agent {agent_id} is not connected via WebSocket.")

                except Exception as msg_err:
                    logger.error(f"Redis message handling error: {msg_err}")

        except asyncio.CancelledError:
            logger.info("Redis subscriber task cancelled.")
            return
        except Exception as e:
            logger.warning(
                f"Redis unavailable ({e.__class__.__name__}: {e}). "
                f"Retrying in {backoff}s... (WebSocket server continues normally)"
            )
        finally:
            if redis_conn:
                try:
                    await redis_conn.aclose()
                except Exception:
                    pass

        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, 60)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup async postgres connection pool for Auth checks, skip if SQLite config
    app.state.pool = None
    if DB_DSN:
        try:
            pool = await asyncpg.create_pool(dsn=DB_DSN, min_size=1, max_size=10, ssl=False)
            app.state.pool = pool
            logger.info("Database connection pool established.")
        except Exception as e:
            logger.warning(f"Could not connect to database (will retry on demand): {e}")

    # Phase 1 (migration): Run BOTH Pub/Sub subscriber (legacy) AND Streams consumer (new).
    # Once all deployments use Streams, disable ENABLE_PUBSUB_SUBSCRIBER.
    enable_pubsub = os.getenv("ENABLE_PUBSUB_SUBSCRIBER", "true").lower() == "true"
    enable_streams = os.getenv("ENABLE_STREAMS_CONSUMER", "true").lower() == "true"

    tasks = []

    if enable_pubsub:
        sub_task = asyncio.create_task(redis_subscriber())
        tasks.append(sub_task)
        logger.info("Redis Pub/Sub subscriber started (legacy path).")

    if enable_streams:
        streams_consumer = StreamsConsumer(redis_url=REDIS_URL, manager=manager)
        streams_task = asyncio.create_task(streams_consumer.run())
        tasks.append(streams_task)
        logger.info("Redis Streams consumer started (new path).")

    yield

    # Shutdown all background tasks
    for task in tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    if app.state.pool:
        await app.state.pool.close()

app = FastAPI(title="PatchGuard Async Realtime Service", version="1.0", lifespan=lifespan)

# Register routes
app.include_router(health.router)
app.include_router(agents.router)
app.include_router(events.router)
app.include_router(ssh.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
