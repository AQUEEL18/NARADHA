"""
Serializers for Dashboard models.
"""
from rest_framework import serializers
from .models import (
    DashboardWidget, DashboardView, PublicDashboardSettings,
    AnalyticsData, DepartmentPerformance, OfficialPerformance,
    IssuePattern, HeatmapData, DashboardAlert
)
from apps.complaints.models import ComplaintCategory
from apps.users.serializers import UserSerializer, DepartmentSerializer


class DashboardWidgetSerializer(serializers.ModelSerializer):
    """Serializer for DashboardWidget model."""
    
    class Meta:
        model = DashboardWidget
        fields = ['id', 'name', 'widget_type', 'config', 'position_x', 
                 'position_y', 'width', 'height', 'is_visible', 'is_public',
                 'allowed_roles', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class DashboardViewSerializer(serializers.ModelSerializer):
    """Serializer for DashboardView model."""
    
    widgets = DashboardWidgetSerializer(many=True, read_only=True)
    
    class Meta:
        model = DashboardView
        fields = ['id', 'name', 'description', 'view_type', 'widgets',
                 'layout', 'is_active', 'allowed_users', 'allowed_departments',
                 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class PublicDashboardSettingsSerializer(serializers.ModelSerializer):
    """Serializer for PublicDashboardSettings model."""
    
    class Meta:
        model = PublicDashboardSettings
        fields = ['id', 'show_resolution_times', 'show_department_rankings',
                 'show_issue_patterns', 'show_citizen_satisfaction',
                 'show_sla_compliance', 'show_recent_complaints',
                 'show_top_officials', 'anonymize_citizen_data',
                 'anonymize_location_data', 'anonymization_level',
                 'min_complaints_for_patterns', 'show_only_resolved',
                 'default_time_range', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class AnalyticsDataSerializer(serializers.ModelSerializer):
    """Serializer for AnalyticsData model."""
    
    class Meta:
        model = AnalyticsData
        fields = ['id', 'data_type', 'data', 'start_date', 'end_date',
                 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


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


class DashboardAlertSerializer(serializers.ModelSerializer):
    """Serializer for DashboardAlert model."""
    
    complaint_id = serializers.CharField(source='complaint.complaint_id', read_only=True, allow_null=True)
    department = DepartmentSerializer(read_only=True)
    official = UserSerializer(read_only=True)
    resolved_by = UserSerializer(read_only=True)
    
    class Meta:
        model = DashboardAlert
        fields = ['id', 'alert_type', 'title', 'message', 'complaint',
                 'complaint_id', 'department', 'official', 'severity',
                 'is_active', 'is_acknowledged', 'acknowledged_by', 'acknowledged_at',
                 'action_url', 'action_text', 'created_at', 'updated_at',
                 'resolved_by']
        read_only_fields = ['id', 'is_acknowledged', 'acknowledged_at',
                           'acknowledged_by', 'created_at', 'updated_at']
