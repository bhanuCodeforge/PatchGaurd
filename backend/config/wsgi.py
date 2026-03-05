# TODO: Implement WSGI configuration in Task 1.4
"""
WSGI config for PatchGuard project.
"""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")
application = get_wsgi_application()
