# PatchGuard Django config package
# Ensure the Celery app is loaded when Django starts so that
# @shared_task decorators use the correct app instance.
from .celery_app import app as celery_app

__all__ = ("celery_app",)
