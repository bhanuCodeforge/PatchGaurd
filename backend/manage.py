#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
import signal


def _patch_django_setup():
    """
    Suppress SIGINT during django.setup() to prevent Python 3.14 Windows bug
    where zoneinfo.ZoneInfo() raises KeyboardInterrupt during the eager load of
    ~600 timezone objects in timezone_field.TimeZoneField.__init__().
    The stale SIGINT comes from VS Code's node-terminal restarting the process.
    """
    import django as _django
    _original = _django.setup

    def _safe_setup(**kwargs):
        _old = signal.signal(signal.SIGINT, signal.SIG_IGN)
        try:
            _original(**kwargs)
        finally:
            signal.signal(signal.SIGINT, _old)

    _django.setup = _safe_setup


_patch_django_setup()


def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
