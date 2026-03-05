import django_filters
from django_filters import BaseInFilter, CharFilter
from .models import Deployment

class CharInFilter(BaseInFilter, CharFilter):
    pass

class DeploymentFilter(django_filters.FilterSet):
    status = CharInFilter(field_name='status', lookup_expr='in')
    strategy = CharInFilter(field_name='strategy', lookup_expr='in')
    created_by = django_filters.UUIDFilter(field_name='created_by__id')

    class Meta:
        model = Deployment
        fields = ['status', 'strategy', 'created_by']
