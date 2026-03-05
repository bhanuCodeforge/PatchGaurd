import structlog
from datetime import datetime, timezone
from rest_framework.views import exception_handler
from rest_framework.exceptions import APIException
from rest_framework import status

logger = structlog.get_logger(__name__)


def custom_exception_handler(exc, context):
    """
    Extends DRF's default exception handler to add consistent format,
    timestamps, error_codes, and log 500 errors.
    """
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    # If the exception is a 500 equivalent, or unhandled
    if response is None:
        logger.error(
            "unhandled_server_error",
            error=str(exc),
            path=context['request'].path if 'request' in context else "unknown",
            exc_info=True
        )
        return None  # Let Django handle 500s normally, or return a custom 500 Response

    # Enhance the structure with common fields
    error_code = getattr(exc, "default_code", "error")
    if hasattr(exc, "error_code"):
        error_code = exc.error_code

    # Flatten DRF detail objects or lists if needed, but keeping it simple for now
    detail = response.data.get("detail", response.data)

    custom_data = {
        "error_code": error_code,
        "detail": detail,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # Replace response data with customized structure
    response.data = custom_data

    return response


class DeploymentInProgressError(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "A deployment is already in progress for this schedule/device."
    default_code = "deployment_in_progress"
    error_code = "deployment_in_progress"


class DeviceOfflineError(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "The device is currently offline or unreachable."
    default_code = "device_offline"
    error_code = "device_offline"


class PatchNotApprovedError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "The patch has not been approved for deployment."
    default_code = "patch_not_approved"
    error_code = "patch_not_approved"


class QuotaExceededError(APIException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = "You have exceeded your resource quota."
    default_code = "quota_exceeded"
    error_code = "quota_exceeded"
