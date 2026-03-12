"""
apps.users.filters
──────────────────
django-filter FilterSet for the User model.

Supported query parameters:
  role        – exact match  (admin|operator|viewer|agent)
  source      – exact match  (local|ldap|saml)
  department  – case-insensitive contains
  status      – "active" | "locked"
  search      – searches username, email, full_name, department
  is_active   – boolean
"""

import django_filters
from django.db.models import Q
from django.utils import timezone

from django.contrib.auth import get_user_model

User = get_user_model()


class UserFilter(django_filters.FilterSet):
    # Simple exact-match fields
    role       = django_filters.CharFilter(field_name="role")
    source     = django_filters.CharFilter(field_name="source")
    is_active  = django_filters.BooleanFilter(field_name="is_active")

    # Case-insensitive substring
    department = django_filters.CharFilter(
        field_name="department", lookup_expr="icontains"
    )

    # Derived status filter: "active" | "locked"
    status = django_filters.CharFilter(method="filter_by_status")

    # Free-text search across multiple fields
    search = django_filters.CharFilter(method="filter_search")

    # Date range on last_login
    last_login_after  = django_filters.DateTimeFilter(
        field_name="last_login", lookup_expr="gte"
    )
    last_login_before = django_filters.DateTimeFilter(
        field_name="last_login", lookup_expr="lte"
    )

    class Meta:
        model  = User
        fields = ["role", "source", "department", "is_active", "status", "search"]

    # ── Custom filter methods ─────────────────────────────────────────────────

    def filter_by_status(self, queryset, name, value):
        now = timezone.now()
        if value == "active":
            return queryset.filter(
                Q(locked_until__isnull=True) | Q(locked_until__lte=now)
            )
        if value == "locked":
            return queryset.filter(locked_until__gt=now)
        return queryset

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(username__icontains=value)
            | Q(email__icontains=value)
            | Q(full_name__icontains=value)
            | Q(department__icontains=value)
        )
