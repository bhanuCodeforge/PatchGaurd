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
        # Detect resource type and ID from path more robustly
        path_parts = request.path.strip("/").split("/")
        
        if "api" in path_parts and "v1" in path_parts:
            # Pattern: /api/v1/resource/id/
            v1_idx = path_parts.index("v1")
            resource_type = path_parts[v1_idx + 1] if len(path_parts) > v1_idx + 1 else "unknown"
            potential_id = path_parts[v1_idx + 2] if len(path_parts) > v1_idx + 2 else None
        else:
            # Non-API path (e.g., /admin/login/)
            resource_type = path_parts[0] if path_parts else "unknown"
            potential_id = path_parts[1] if len(path_parts) > 1 else None

        # Validate UUID if present
        resource_id = None
        if potential_id:
            import uuid
            try:
                resource_id = uuid.UUID(potential_id)
            except ValueError:
                resource_id = None

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
        
        from apps.accounts.models import AuditLog, User
        
        # Only assign user if it's a real User instance (not AgentPrincipal)
        audit_user = request.user if isinstance(request.user, User) else None
        
        # If it's an agent, add that info to details
        if not audit_user:
            audit_entry["details"]["agent_principal"] = str(request.user)

        # Log it for Phase 1.
        logger.info("audit_log", **audit_entry)
        
        # Activated DB persistence for Phase 2 implementation.
        AuditLog.objects.create(
            user=audit_user,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            details=audit_entry["details"]
        )
            
        return response
