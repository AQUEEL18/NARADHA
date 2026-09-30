"""
Serializers for Fieldwork models.
"""
from rest_framework import serializers
from .models import (
    FieldTask, FieldTaskHistory, FieldWorkerLocation, FieldWorkerPerformance,
    FieldTaskChecklist, FieldTaskChecklistTemplate
)
from apps.complaints.models import Complaint
from apps.complaints.serializers import ComplaintMinimalSerializer
from apps.users.serializers import UserSerializer


class FieldTaskSerializer(serializers.ModelSerializer):
    """Serializer for FieldTask model."""
    
    complaint = ComplaintMinimalSerializer(read_only=True)
    assigned_to = UserSerializer(read_only=True)
    assigned_by = UserSerializer(read_only=True)
    jurisdiction = serializers.StringRelatedField(read_only=True)
    verified_by = UserSerializer(read_only=True)
    
    before_photo_url = serializers.SerializerMethodField()
    after_photo_url = serializers.SerializerMethodField()
    
    class Meta:
        model = FieldTask
        fields = ['id', 'task_id', 'complaint', 'assigned_to', 'assigned_by',
                 'status', 'title', 'description', 'location_address', 'latitude',
                 'longitude', 'jurisdiction', 'deadline', 'work_type',
                 'materials_used', 'labor_hours', 'cost_estimate', 'before_photo',
                 'after_photo', 'before_photo_url', 'after_photo_url',
                 'completion_notes', 'completion_date', 'verified_by',
                 'verification_notes', 'verification_date', 'quality_rating',
                 'quality_feedback', 'gps_track', 'priority', 'created_at',
                 'updated_at', 'started_at']
        read_only_fields = ['id', 'task_id', 'complaint', 'assigned_to', 'assigned_by',
                           'jurisdiction', 'verified_by', 'verification_notes',
                           'verification_date', 'quality_rating', 'quality_feedback',
                           'created_at', 'updated_at', 'started_at', 'completion_date',
                           'before_photo_url', 'after_photo_url']
    
    def get_before_photo_url(self, obj):
        if obj.before_photo:
            return obj.before_photo.url
        return None
    
    def get_after_photo_url(self, obj):
        if obj.after_photo:
            return obj.after_photo.url
        return None


class FieldTaskHistorySerializer(serializers.ModelSerializer):
    """Serializer for FieldTaskHistory model."""
    
    task = FieldTaskSerializer(read_only=True)
    changed_by = UserSerializer(read_only=True)
    
    class Meta:
        model = FieldTaskHistory
        fields = ['id', 'task', 'previous_status', 'new_status', 'changed_by',
                 'notes', 'latitude', 'longitude', 'ip_address', 'user_agent',
                 'created_at']
        read_only_fields = ['id', 'task', 'changed_by', 'created_at']


class FieldWorkerLocationSerializer(serializers.ModelSerializer):
    """Serializer for FieldWorkerLocation model."""
    
    worker = UserSerializer(read_only=True)
    current_task = FieldTaskSerializer(read_only=True)
    
    class Meta:
        model = FieldWorkerLocation
        fields = ['id', 'worker', 'latitude', 'longitude', 'accuracy',
                 'device_id', 'battery_level', 'current_task', 'created_at']
        read_only_fields = ['id', 'worker', 'current_task', 'created_at']


class FieldWorkerPerformanceSerializer(serializers.ModelSerializer):
    """Serializer for FieldWorkerPerformance model."""
    
    worker = UserSerializer(read_only=True)
    
    class Meta:
        model = FieldWorkerPerformance
        fields = ['id', 'worker', 'total_tasks', 'completed_tasks', 'rejected_tasks',
                 'avg_completion_time', 'total_working_hours', 'avg_quality_rating',
                 'quality_rating_count', 'total_distance_traveled', 'last_active',
                 'performance_score', 'created_at', 'updated_at']
        read_only_fields = ['id', 'avg_completion_time', 'performance_score',
                           'created_at', 'updated_at']


class FieldTaskChecklistSerializer(serializers.ModelSerializer):
    """Serializer for FieldTaskChecklist model."""
    
    task = FieldTaskSerializer(read_only=True)
    completed_by = UserSerializer(read_only=True)
    
    class Meta:
        model = FieldTaskChecklist
        fields = ['id', 'task', 'item_name', 'description', 'is_required',
                 'is_completed', 'completed_by', 'completed_at', 'notes',
                 'order', 'created_at', 'updated_at']
        read_only_fields = ['id', 'task', 'completed_by', 'completed_at',
                           'created_at', 'updated_at']


class FieldTaskChecklistTemplateSerializer(serializers.ModelSerializer):
    """Serializer for FieldTaskChecklistTemplate model."""
    
    class Meta:
        model = FieldTaskChecklistTemplate
        fields = ['id', 'name', 'description', 'work_type', 'items',
                 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
