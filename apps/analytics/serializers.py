"""
Serializers for Analytics models.
"""
from rest_framework import serializers
from .models import DepartmentPerformance, OfficialPerformance, IssuePattern, HeatmapData
from apps.users.serializers import UserSerializer, DepartmentSerializer


class DepartmentPerformanceSerializer(serializers.ModelSerializer):
    """Serializer for DepartmentPerformance model."""
    
    department = DepartmentSerializer(read_only=True)
    
    class Meta:
        model = DepartmentPerformance
        fields = ['id', 'department', 'total_complaints', 'resolved_complaints',
                 'rejected_complaints', 'pending_complaints', 'avg_resolution_time',
                 'median_resolution_time', 'avg_citizen_rating', 'avg_priority_score',
                 'sla_compliance_rate', 'sla_breach_count', 'performance_score',
                 'rank', 'created_at', 'updated_at']
        read_only_fields = ['id', 'avg_resolution_time', 'median_resolution_time',
                           'performance_score', 'rank', 'created_at', 'updated_at']


class OfficialPerformanceSerializer(serializers.ModelSerializer):
    """Serializer for OfficialPerformance model."""
    
    official = UserSerializer(read_only=True)
    
    class Meta:
        model = OfficialPerformance
        fields = ['id', 'official', 'total_complaints', 'resolved_complaints',
                 'rejected_complaints', 'pending_complaints', 'overdue_complaints',
                 'avg_response_time', 'avg_resolution_time', 'avg_citizen_rating',
                 'avg_priority_score', 'sla_compliance_rate', 'sla_breach_count',
                 'messages_sent', 'messages_received', 'avg_message_response_time',
                 'performance_score', 'rank', 'created_at', 'updated_at']
        read_only_fields = ['id', 'avg_response_time', 'avg_resolution_time',
                           'avg_message_response_time', 'performance_score',
                           'rank', 'created_at', 'updated_at']


class IssuePatternSerializer(serializers.ModelSerializer):
    """Serializer for IssuePattern model."""
    
    category = serializers.StringRelatedField(read_only=True)
    resolved_by = UserSerializer(read_only=True)
    jurisdictions = serializers.StringRelatedField(many=True, read_only=True)
    
    class Meta:
        model = IssuePattern
        fields = ['id', 'name', 'description', 'category', 'keywords',
                 'complaint_count', 'first_seen', 'last_seen', 'jurisdictions',
                 'avg_priority_score', 'max_priority_score', 'is_active',
                 'is_resolved', 'resolution_notes', 'resolved_at', 'resolved_by',
                 'created_at', 'updated_at']
        read_only_fields = ['id', 'complaint_count', 'first_seen', 'last_seen',
                           'created_at', 'updated_at']


class HeatmapDataSerializer(serializers.ModelSerializer):
    """Serializer for HeatmapData model."""
    
    class Meta:
        model = HeatmapData
        fields = ['id', 'location', 'latitude', 'longitude', 'complaint_count',
                 'resolved_count', 'pending_count', 'low_priority', 'medium_priority',
                 'high_priority', 'critical_priority', 'category_data',
                 'start_date', 'end_date', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
