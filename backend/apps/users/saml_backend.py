"""
apps.users.saml_backend
────────────────────────
SAML 2.0 integration using the python3-saml library (OneLogin).

Installation:
  pip install python3-saml>=1.16.0
  # On Linux: apt install xmlsec1 libxml2-dev libxmlsec1-dev pkg-config
  # On Windows: pip install xmlsec  (ships pre-built wheels for Python 3.10+)

This module is designed to fail gracefully:
  - All public functions raise ImportError if python3-saml is missing.
  - The views catch ImportError and return HTTP 501.
  - Everything else in the system works without SAML installed.

Public API:
  build_saml_settings(config, base_url) → dict
  generate_metadata(saml_settings)      → (xml_str, errors)
  init_auth(saml_settings, request)     → OneLogin_Saml2_Auth
  process_response(auth)                → (attrs_dict, name_id)
  provision_saml_user(config, attrs, name_id) → User
"""

import logging
from typing import Any

from django.contrib.auth import get_user_model
from django.utils import timezone

logger = logging.getLogger("patchguard.saml")
User   = get_user_model()


# ── python3-saml integration ──────────────────────────────────────────────────

def _import_saml():
    """Lazy import — raises ImportError with a helpful message if missing."""
    try:
        from onelogin.saml2.auth import OneLogin_Saml2_Auth          # noqa
        from onelogin.saml2.settings import OneLogin_Saml2_Settings   # noqa
        from onelogin.saml2.utils import OneLogin_Saml2_Utils         # noqa
        return OneLogin_Saml2_Auth, OneLogin_Saml2_Settings, OneLogin_Saml2_Utils
    except ImportError:
        raise ImportError(
            "python3-saml is not installed. Run: pip install python3-saml>=1.16.0"
        )


# ── Settings builder ──────────────────────────────────────────────────────────

def build_saml_settings(config, base_url: str) -> dict:
    """
    Convert a SAMLConfiguration model instance into the python3-saml settings
    dictionary format.

    Args:
        config:   apps.users.models.SAMLConfiguration instance
        base_url: Absolute server root, e.g. "https://patchguard.corp.com"
    """
    config_id  = str(config.id)
    sp_base    = f"{base_url}/api/v1/saml/{config_id}"
    sp_entity  = config.get_sp_entity_id(base_url)

    return {
        "strict": True,  # always enforce strict mode in production
        "debug":  False,

        "sp": {
            "entityId":    sp_entity,
            "assertionConsumerService": {
                "url":     f"{sp_base}/acs/",
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
            },
            "singleLogoutService": {
                "url":     f"{sp_base}/sls/",
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "NameIDFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
            # SP signing key — set via SAML_SP_PRIVATE_KEY + SAML_SP_CERT in settings
            "x509cert":    _get_sp_cert(),
            "privateKey":  _get_sp_key(),
        },

        "idp": {
            "entityId": config.idp_entity_id,
            "singleSignOnService": {
                "url":     config.idp_sso_url,
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "singleLogoutService": {
                "url":     config.idp_slo_url or config.idp_sso_url,
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "x509cert": config.idp_x509_cert,
        },

        "security": {
            "nameIdEncrypted":       False,
            "authnRequestsSigned":   bool(_get_sp_key()),
            "logoutRequestSigned":   bool(_get_sp_key()),
            "logoutResponseSigned":  bool(_get_sp_key()),
            "signMetadata":          bool(_get_sp_cert()),
            "wantMessagesSigned":    False,
            "wantAssertionsSigned":  True,   # require IdP to sign assertions
            "wantNameId":            True,
            "wantAssertionsEncrypted": False,
            "wantNameIdEncrypted":   False,
            "requestedAuthnContext": True,
            "signatureAlgorithm":    "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
            "digestAlgorithm":       "http://www.w3.org/2001/04/xmlenc#sha256",
        },
    }


def _get_sp_cert() -> str:
    from django.conf import settings
    return getattr(settings, "SAML_SP_CERT", "")


def _get_sp_key() -> str:
    from django.conf import settings
    return getattr(settings, "SAML_SP_PRIVATE_KEY", "")


# ── Metadata ──────────────────────────────────────────────────────────────────

def generate_metadata(saml_settings: dict) -> tuple[str, list]:
    """
    Returns (xml_string, errors_list).
    Call after build_saml_settings().
    """
    _, OneLogin_Saml2_Settings, _ = _import_saml()
    settings_obj = OneLogin_Saml2_Settings(settings=saml_settings, sp_validation_only=True)
    metadata     = settings_obj.get_sp_metadata()
    errors       = settings_obj.validate_metadata(metadata)
    return metadata, errors


# ── Request preparation ───────────────────────────────────────────────────────

def _prepare_request(request) -> dict:
    """
    Convert a Django HttpRequest into the dict format python3-saml expects.
    Handles both DRF Request wrappers and raw HttpRequest objects.
    """
    # DRF Request wraps Django's HttpRequest in request._request
    django_request = getattr(request, "_request", request)

    return {
        "https":        "on" if django_request.is_secure() else "off",
        "http_host":    django_request.META.get("HTTP_HOST", ""),
        "script_name":  django_request.META.get("PATH_INFO", ""),
        "server_port":  django_request.META.get("SERVER_PORT", ""),
        "get_data":     django_request.GET.dict(),
        "post_data":    django_request.POST.dict(),
        "query_string": django_request.META.get("QUERY_STRING", ""),
    }


def init_auth(saml_settings: dict, request) -> Any:
    """Create and return a OneLogin_Saml2_Auth instance."""
    OneLogin_Saml2_Auth, _, _ = _import_saml()
    return OneLogin_Saml2_Auth(_prepare_request(request), custom_base_path=None,
                               old_settings=saml_settings)


# ── Response processing ───────────────────────────────────────────────────────

def process_response(auth) -> tuple[dict, str]:
    """
    Process the SAML response already loaded into `auth`.
    Returns (attributes_dict, name_id_string).
    Raises ValueError on validation failure.
    """
    auth.process_response()
    errors = auth.get_errors()
    if errors:
        reason = auth.get_last_error_reason() or ", ".join(errors)
        raise ValueError(f"SAML response invalid: {reason}")

    if not auth.is_authenticated():
        raise ValueError("SAML response did not authenticate the user.")

    attrs   = auth.get_attributes()       # {attr_name: [value, ...]}
    name_id = auth.get_nameid() or ""

    # Flatten single-value attributes for convenience
    flat_attrs = {k: (v[0] if isinstance(v, list) and v else v) for k, v in attrs.items()}
    return flat_attrs, name_id


# ── User provisioning ─────────────────────────────────────────────────────────

def provision_saml_user(config, attrs: dict, name_id: str) -> User:
    """
    Find or create the Django User corresponding to a SAML assertion.

    Lookup order:
      1. Match by email from SAML attributes
      2. Fall back to name_id (NameID is typically an email)
    """
    mapping = config.attribute_mapping or {}

    # Extract email
    email_attr = mapping.get("email", "email")
    email = (
        attrs.get(email_attr)
        or attrs.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress")
        or (name_id if "@" in name_id else None)
    )
    if not email:
        raise ValueError("SAML assertion did not contain a usable email address.")
    email = email.lower().strip()

    # Extract full name
    name_attr = mapping.get("full_name") or mapping.get("givenName", "cn")
    full_name = attrs.get(name_attr, "")

    # Extract role (optional)
    role_attr    = mapping.get("role", "")
    saml_role    = attrs.get(role_attr, "") if role_attr else ""
    valid_roles  = [r[0] for r in User.Role.choices]
    resolved_role = saml_role if saml_role in valid_roles else config.default_role

    # Look up existing user by email
    try:
        user = User.objects.get(email__iexact=email)
        if config.auto_update_attrs:
            changed = []
            if full_name and user.full_name != full_name:
                user.full_name = full_name
                changed.append("full_name")
            if user.source != User.UserSource.SAML:
                user.source = User.UserSource.SAML
                changed.append("source")
            if changed:
                user.save(update_fields=changed)
        logger.debug("SAML login matched existing user: %s", user.username)
        return user

    except User.DoesNotExist:
        pass

    if not config.auto_create_users:
        raise ValueError(
            f"No account found for {email} and auto-provisioning is disabled."
        )

    # Derive username from the email local part
    base_username = email.split("@")[0].replace(".", "_").lower()
    username      = _unique_username(base_username)

    user = User.objects.create(
        username  = username,
        email     = email,
        full_name = full_name,
        role      = resolved_role,
        source    = User.UserSource.SAML,
        must_change_password=False,
        is_active = True,
    )
    user.set_unusable_password()
    user.save()

    logger.info("SAML auto-provisioned user: %s (%s)", username, email)
    return user


def _unique_username(base: str) -> str:
    """Append a counter suffix until the username is available."""
    candidate = base
    counter   = 1
    while User.objects.filter(username=candidate).exists():
        candidate = f"{base}_{counter}"
        counter  += 1
    return candidate
