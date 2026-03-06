"""
AgentAPIKeyAuthentication — authenticates agent REST calls via X-Agent-API-Key header.
Used by heartbeat, ingest_scan, and any other agent-initiated endpoints.
"""
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


class AgentPrincipal:
    """Lightweight user-like object representing an authenticated agent (device)."""
    is_authenticated = True
    is_active = True
    role = "agent"

    def __init__(self, device):
        self.device = device
        self.id = device.id
        self.pk = device.id
        self.username = f"agent:{device.hostname}"

    def __str__(self):
        return self.username


class AgentAPIKeyAuthentication(BaseAuthentication):
    """
    Authenticate via 'X-Agent-API-Key' HTTP header.
    Returns (AgentPrincipal, api_key) on success, None to pass to next authenticator.
    """

    def authenticate(self, request):
        api_key = request.META.get("HTTP_X_AGENT_API_KEY")
        if not api_key:
            return None  # fall through to JWT or other auth classes

        try:
            from apps.inventory.models import Device
            device = Device.objects.exclude(
                status=Device.Status.DECOMMISSIONED
            ).get(agent_api_key=api_key)
            return (AgentPrincipal(device), api_key)
        except Device.DoesNotExist:
            raise AuthenticationFailed("Invalid agent API key.")

    def authenticate_header(self, request):
        return "X-Agent-API-Key"
