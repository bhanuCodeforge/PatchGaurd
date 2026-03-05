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

from routes import health, agents, events
from ws_manager import manager

logging.basicConfig(level=logging.INFO)
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

async def redis_subscriber():
    """Background task to listen to Redis Pub/Sub channels from Django Celery."""
    redis_conn = await aioredis.from_url(REDIS_URL)
    pubsub = redis_conn.pubsub()
    
    # Subscribe to relevant backend system broadcast channels
    await pubsub.subscribe("deployment:progress", "system:notification", "system:compliance_alert")
    
    # Subscribe to agent command patterns (e.g. agent:command:*)
    await pubsub.psubscribe("agent:command:*")
    
    logger.info("Started Redis Pub/Sub asynchronous loop.")
    try:
        async for message in pubsub.listen():
            if message["type"] in ("message", "pmessage"):
                channel = message["channel"].decode() if isinstance(message["channel"], bytes) else message["channel"]
                data = message["data"].decode() if isinstance(message["data"], bytes) else message["data"]
                
                # Routing Logic
                if channel == "deployment:progress":
                    env = json.loads(data)
                    dep_id = env["payload"].get("deployment_id")
                    if dep_id:
                        await manager.broadcast_to_deployment(dep_id, data)
                
                elif channel.startswith("system:"):
                    # Broadcast generic notifications to all dashboards
                    await manager.broadcast_to_dashboard(data)

                elif channel.startswith("agent:command:"):
                    # Extract agent_id from channel specifically
                    agent_id = channel.split(":")[-1]
                    await manager.send_to_agent(agent_id, data)
                    
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Redis sub loop crashed: {e}")

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

    # Start Redis Pub/Sub background task
    sub_task = asyncio.create_task(redis_subscriber())

    yield

    # Shutdown
    sub_task.cancel()
    if app.state.pool:
        await app.state.pool.close()

app = FastAPI(title="PatchGuard Async Realtime Service", version="1.0", lifespan=lifespan)

# Register routes
app.include_router(health.router)
app.include_router(agents.router)
app.include_router(events.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
