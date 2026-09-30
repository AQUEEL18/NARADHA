"""
Serializers for the routing app.
"""
from rest_framework import serializers

from .models import OfficialWorkload, RoutingLog


class RoutingLogSerializer(serializers.ModelSerializer):
    """Serializer for RoutingLog."""

    complaint_id_str = serializers.CharField(
        source='complaint.complaint_id', read_only=True
    )
    previous_official_name = serializers.CharField(
        source='previous_official.get_short_name', read_only=True, default=None
    )
    new_official_name = serializers.CharField(
        source='new_official.get_short_name', read_only=True, default=None
    )
    new_department_name = serializers.CharField(
        source='new_department.name', read_only=True, default=None
    )

    class Meta:
        model = RoutingLog
        fields = [
            'id', 'complaint', 'complaint_id_str',
            'previous_official', 'previous_official_name',
            'new_official', 'new_official_name',
            'previous_department', 'new_department', 'new_department_name',
            'routing_method', 'routing_reason', 'routing_confidence',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class OfficialWorkloadSerializer(serializers.ModelSerializer):
    """Serializer for OfficialWorkload."""

    official_name = serializers.CharField(
        source='official.get_short_name', read_only=True
    )
    official_email = serializers.CharField(
        source='official.email', read_only=True
    )
    load_ratio = serializers.FloatField(read_only=True)

    class Meta:
        model = OfficialWorkload
        fields = [
            'id', 'official', 'official_name', 'official_email',
            'assigned_complaints', 'resolved_complaints', 'active_complaints',
            'max_daily_capacity', 'load_ratio', 'is_available',
            'unavailable_until', 'last_assigned_at', 'updated_at'
        ]
        read_only_fields = ['id', 'updated_at']
