import time
import structlog
from django.utils.deprecation import MiddlewareMixin
from .utils import get_client_ip

logger = structlog.get_logger("patchguard")


class RequestTimingMiddleware(MiddlewareMixin):
    """
    Measures the duration of requests and logs warnings for slow requests.
    """
    def process_request(self, request):
        request.start_time = time.time()

    def process_response(self, request, response):
        if hasattr(request, "start_time"):
            duration_s = time.time() - request.start_time
            duration_ms = int(duration_s * 1000)
            
            response["X-Response-Time-Ms"] = str(duration_ms)
            
            if duration_ms > 500:
                logger.warning(
                    "slow_request",
                    path=request.path,
                    method=request.method,
                    duration_ms=duration_ms,
                    status=response.status_code
                )
        return response


class AuditLogMiddleware(MiddlewareMixin):
    """
    Logs mutating actions by authenticated users to an audit log.
    NOTE: In Phase 1, we just write to structlog. In Phase 2, this will save to the Database.
    """
    _audit_queue = []
    
    def process_response(self, request, response):
        # Only audit mutating methods
        if request.method not in ["POST", "PUT", "PATCH", "DELETE"]:
            return response
            
        # Only successful responses
        if response.status_code >= 400:
            return response
            
        # Only authenticated users
        if not hasattr(request, "user") or not request.user.is_authenticated:
            return response

        action = f"{request.method} {request.path}"
        resource_type = request.path.strip("/").split("/")[2] if len(request.path.split("/")) > 2 else "unknown"
        ip_address = get_client_ip(request)
        
        audit_entry = {
            "user_id": request.user.id,
            "action": action,
            "resource_type": resource_type,
            "details": {
                "status_code": response.status_code,
                "query_params": dict(request.GET),
            },
            "ip_address": ip_address,
        }
        
        # Log it for Phase 1. Task 1.5 explicitly states we use bulk_create if multiple queued.
        # This will be fully activated when the AuditLog model is created in Phase 2.
        logger.info("audit_log", **audit_entry)
        
        # Placeholder for DB bulk_create logic
        self._audit_queue.append(audit_entry)
        if len(self._audit_queue) > 10:
            # AuditLog.objects.bulk_create([AuditLog(**data) for data in self._audit_queue])
            self._audit_queue.clear()
            
        return response
