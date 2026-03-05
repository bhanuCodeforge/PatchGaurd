"""
Celery worker entrypoint with Python 3.14 Windows SIGINT fix.

timezone_field.TimeZoneField eagerly loads ~600 zoneinfo.ZoneInfo objects at
Django model import time. On Python 3.14 Windows, one of those file opens
raises KeyboardInterrupt from a stale SIGINT in the VS Code terminal buffer.
This wrapper suppresses SIGINT during django.setup() and restores it after.

Usage (same args as `python -m celery`):
  python celery_worker.py -A config.celery_app worker --pool=solo ...
  python celery_worker.py -A config.celery_app beat ...
"""
import sys
import signal
import django as _django

_original_setup = _django.setup


def _safe_setup(**kwargs):
    _old = signal.signal(signal.SIGINT, signal.SIG_IGN)
    try:
        _original_setup(**kwargs)
    finally:
        signal.signal(signal.SIGINT, _old)


_django.setup = _safe_setup

# Inject 'celery' as argv[0] so Celery's main() sees the right command name
sys.argv = ["celery"] + sys.argv[1:]

from celery.__main__ import main
main()
