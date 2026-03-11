"""
PatchGuard BFF (Backend-for-Frontend) / API Gateway

A lightweight FastAPI service that:
  - Gives Angular a single base URL for all API & realtime calls
  - Translates cookie/header auth to downstream JWT
  - Aggregates the /api/v1/dashboard endpoint from multiple upstream calls
  - Proxies /api/v1/devices with Redis caching
  - Proxies WebSocket /ws/* to the realtime service
  - Enforces per-client rate limits on heavy endpoints

Usage:
  uvicorn bff.main:app --host 0.0.0.0 --port 8080 --reload

Environment variables (see .env.bff.example):
  BACKEND_URL          = http://localhost:8000      # Django backend
  REALTIME_URL         = http://localhost:8001      # FastAPI realtime service
  REALTIME_WS_URL      = ws://localhost:8001        # WebSocket base for realtime
  REDIS_URL            = redis://localhost:6379/2   # DB 2 for BFF cache
  BFF_CACHE_TTL        = 30                         # seconds for device list cache
  DASHBOARD_CACHE_TTL  = 10                         # seconds for dashboard aggregate
  RATE_LIMIT_DEVICES   = 60                         # requests/minute per client
  RATE_LIMIT_DASHBOARD = 120                        # requests/minute per client
"""
