"""
Views for the routing app.
"""
from rest_framework import permissions, viewsets

from .models import OfficialWorkload, RoutingLog
from .serializers import OfficialWorkloadSerializer, RoutingLogSerializer


class RoutingLogViewSet(viewsets.ReadOnlyModelViewSet):
    """List / retrieve routing logs."""
    queryset = RoutingLog.objects.select_related(
        'complaint', 'previous_official', 'new_official',
        'previous_department', 'new_department'
    )
    serializer_class = RoutingLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['routing_method', 'complaint']
    ordering_fields = ['created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_staff or user.role in ('ADMIN', 'OFFICIAL', 'MINISTER', 'REVIEWER'):
            return queryset
        return queryset.filter(complaint__citizen=user)


class OfficialWorkloadViewSet(viewsets.ReadOnlyModelViewSet):
    """List / retrieve official workload counters."""
    queryset = OfficialWorkload.objects.select_related('official')
    serializer_class = OfficialWorkloadSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['is_available']

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_staff or user.role in ('ADMIN', 'MINISTER'):
            return queryset
        return queryset.filter(official=user)
