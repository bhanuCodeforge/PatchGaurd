import django_filters
from django_filters import BaseInFilter, CharFilter
from .models import Patch

class CharInFilter(BaseInFilter, CharFilter):
    pass

class PatchFilter(django_filters.FilterSet):
    severity = CharInFilter(field_name='severity', lookup_expr='in')
    status = CharInFilter(field_name='status', lookup_expr='in')
    vendor = django_filters.CharFilter(lookup_expr='icontains')
    cve_id = django_filters.CharFilter(method='filter_cve')
    applicable_os = django_filters.CharFilter(method='filter_os')
    requires_reboot = django_filters.BooleanFilter()
    released_after = django_filters.DateTimeFilter(field_name='released_at', lookup_expr='gte')
    released_before = django_filters.DateTimeFilter(field_name='released_at', lookup_expr='lte')
    has_active_exploitation = django_filters.BooleanFilter(method='filter_active_exploitation')

    class Meta:
        model = Patch
        fields = ['severity', 'status', 'vendor', 'requires_reboot']

    def filter_cve(self, queryset, name, value):
        # Tags/Arrays replaced with JSONField due to SQLite limitations
        return queryset.filter(cve_ids__icontains=value)

    def filter_os(self, queryset, name, value):
        return queryset.filter(applicable_os__icontains=value)
        
    def filter_active_exploitation(self, queryset, name, value):
        # Stub for future enrichment logic
        return queryset
