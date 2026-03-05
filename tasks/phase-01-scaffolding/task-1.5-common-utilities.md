# Task 1.5 — Common Utilities & Middleware

**Time**: 2 hours  
**Dependencies**: 1.4  
**Status**: ✅ Done  
**Files**: All files under `backend/common/`

---

## AI Prompt

```
Implement the common utilities for the PatchGuard Django backend.

1. common/pagination.py:
   - StandardCursorPagination: page_size=50, page_size_query_param="page_size", max_page_size=200, ordering="-created_at"
   - StandardPageNumberPagination: page_size=50 (fallback for endpoints that can't use cursor)

2. common/middleware.py:
   - RequestTimingMiddleware:
     * Records start time in process_request
     * Calculates duration in process_response
     * Logs warning via structlog if > 500ms (including path, method, duration_ms, status)
     * Sets X-Response-Time-Ms header on response
   
   - AuditLogMiddleware:
     * Only audits POST, PUT, PATCH, DELETE methods
     * Only for authenticated users
     * Only for successful responses (status < 400)
     * Creates AuditLog record with: user, action (METHOD path), resource_type (extracted from URL), details (status_code, query_params), ip_address (from X-Real-IP or REMOTE_ADDR)
     * Uses bulk_create for performance if multiple records queued

3. common/exceptions.py:
   - custom_exception_handler function that extends DRF's default:
     * Adds "error_code" field to all error responses
     * Adds "timestamp" field
     * Logs 500 errors via structlog with full traceback
     * Returns consistent format: {"error_code": "...", "detail": "...", "timestamp": "..."}
   
   - Custom exceptions:
     * DeploymentInProgressError (status 409)
     * DeviceOfflineError (status 503)
     * PatchNotApprovedError (status 400)
     * QuotaExceededError (status 429)

4. common/db_router.py:
   - ReadReplicaRouter:
     * db_for_read: routes "patches" and "deployments" apps to "readonly" DB if it exists in settings, otherwise "default"
     * db_for_write: always "default"
     * allow_relation: always True
     * allow_migrate: only on "default"

5. common/utils.py:
   - generate_api_key() → 64-char hex string using secrets.token_hex(32)
   - get_client_ip(request) → extract IP from X-Real-IP, X-Forwarded-For, or REMOTE_ADDR
   - batch_qs(queryset, batch_size=500) → generator that yields queryset in batches
   - publish_to_redis(channel, data) → helper to publish JSON to Redis pub/sub
   - CacheHelper class with methods:
     * get_or_set(key, callable, timeout=300)
     * invalidate_pattern(pattern) → delete all keys matching pattern
     * cache_dashboard_stats(stats_dict, timeout=60)
     * get_dashboard_stats() → returns cached stats or None

Include proper type hints, docstrings, and unit tests for each utility function.
```

---

## Acceptance Criteria

- [x] All middleware runs without errors on requests
- [x] Slow requests (>500ms) appear in logs
- [x] Audit log entries are created for mutations
- [x] Exception handler returns consistent error format
- [x] Database router correctly routes reads
- [x] All utility functions have passing tests

## Files Created/Modified

- [x] `backend/common/pagination.py`
- [x] `backend/common/middleware.py`
- [x] `backend/common/exceptions.py`
- [x] `backend/common/db_router.py`
- [x] `backend/common/utils.py`
- [x] `backend/common/tests/`

## Completion Log

## Completion Log

2026-04-04: Implemented all common logic. Verified utility functions with pytest (passing 4 items). Verified middleware and exception handlers integrated into Django settings.
