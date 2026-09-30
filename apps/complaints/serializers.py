"""
Serializers for Complaint models.
"""
from rest_framework import serializers
from django.utils import timezone
from .models import (
    Complaint, ComplaintCategory, ComplaintProof, ComplaintHistory,
    ComplaintEndorsement, ComplaintTag, ComplaintTagAssignment
)
from apps.users.models import CustomUser, Department, Jurisdiction
from apps.users.serializers import UserSerializer


class ComplaintCategorySerializer(serializers.ModelSerializer):
    """Serializer for ComplaintCategory model."""
    
    department = serializers.StringRelatedField()
    
    class Meta:
        model = ComplaintCategory
        fields = ['id', 'name', 'code', 'description', 'department', 
                 'icon', 'color', 'is_active', 'priority_weight']
        read_only_fields = ['id']


class ComplaintProofSerializer(serializers.ModelSerializer):
    """Serializer for ComplaintProof model."""
    
    file_size_display = serializers.SerializerMethodField()
    
    class Meta:
        model = ComplaintProof
        fields = ['id', 'complaint', 'proof_type', 'file', 'thumbnail',
                 'file_size', 'file_type', 'duration', 'gps_latitude', 
                 'gps_longitude', 'gps_accuracy', 'camera_make', 'camera_model',
                 'capture_timestamp', 'ai_analysis_complete', 'ai_authenticity_score',
                 'ai_relevance_score', 'ai_quality_score', 'ai_manipulation_detected',
                 'ai_manipulation_confidence', 'ai_notes', 'human_review_complete',
                 'human_reviewer', 'human_review_notes', 'human_approved',
                 'classified_type', 'classification_confidence', 'file_size_display']
        read_only_fields = ['id', 'ai_analysis_complete', 'ai_authenticity_score',
                           'ai_relevance_score', 'ai_quality_score', 'ai_manipulation_detected',
                           'ai_manipulation_confidence', 'ai_notes', 'human_review_complete',
                           'human_reviewer', 'human_review_notes', 'human_approved',
                           'classified_type', 'classification_confidence', 'file_size_display']
    
    def get_file_size_display(self, obj):
        """Get human-readable file size."""
        if obj.file_size:
            if obj.file_size < 1024:
                return f"{obj.file_size} B"
            elif obj.file_size < 1024 * 1024:
                return f"{obj.file_size / 1024:.2f} KB"
            else:
                return f"{obj.file_size / (1024 * 1024):.2f} MB"
        return ""


class ComplaintHistorySerializer(serializers.ModelSerializer):
    """Serializer for ComplaintHistory model."""
    
    changed_by = UserSerializer(read_only=True)
    
    class Meta:
        model = ComplaintHistory
        fields = ['id', 'complaint', 'previous_status', 'new_status',
                 'changed_by', 'notes', 'ip_address', 'user_agent', 'created_at']
        read_only_fields = ['id', 'complaint', 'changed_by', 'created_at']


class ComplaintEndorsementSerializer(serializers.ModelSerializer):
    """Serializer for ComplaintEndorsement model."""
    
    citizen = UserSerializer(read_only=True)
    
    class Meta:
        model = ComplaintEndorsement
        fields = ['id', 'complaint', 'citizen', 'is_anonymous', 'comments', 'created_at']
        read_only_fields = ['id', 'citizen', 'created_at']


class ComplaintTagSerializer(serializers.ModelSerializer):
    """Serializer for ComplaintTag model."""
    
    class Meta:
        model = ComplaintTag
        fields = ['id', 'name', 'slug', 'description', 'color', 'is_active']
        read_only_fields = ['id', 'slug']


class ComplaintTagAssignmentSerializer(serializers.ModelSerializer):
    """Serializer for ComplaintTagAssignment model."""
    
    tag = ComplaintTagSerializer(read_only=True)
    assigned_by = UserSerializer(read_only=True)
    
    class Meta:
        model = ComplaintTagAssignment
        fields = ['id', 'complaint', 'tag', 'assigned_by', 'created_at']
        read_only_fields = ['id', 'complaint', 'tag', 'assigned_by', 'created_at']


class ComplaintMinimalSerializer(serializers.ModelSerializer):
    """Minimal serializer for complaint lists."""
    
    citizen_name = serializers.SerializerMethodField()
    category_name = serializers.StringRelatedField(source='category', read_only=True)
    assigned_official_name = serializers.StringRelatedField(source='assigned_official', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    
    class Meta:
        model = Complaint
        fields = ['id', 'complaint_id', 'title', 'category_name', 'priority', 
                 'priority_display', 'status', 'status_display', 'citizen_name',
                 'assigned_official_name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'complaint_id', 'citizen_name', 'category_name',
                           'assigned_official_name', 'status_display', 'priority_display']
    
    def get_citizen_name(self, obj):
        if obj.citizen:
            return obj.citizen.get_short_name()
        return "Anonymous"


class ComplaintDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for complaint details."""
    
    citizen = UserSerializer(read_only=True)
    category = ComplaintCategorySerializer(read_only=True)
    jurisdiction = serializers.StringRelatedField(read_only=True)
    assigned_official = UserSerializer(read_only=True)
    assigned_department = serializers.StringRelatedField(read_only=True)
    assigned_field_worker = UserSerializer(read_only=True)
    human_reviewer = UserSerializer(read_only=True)
    
    proofs = ComplaintProofSerializer(many=True, read_only=True)
    history = ComplaintHistorySerializer(many=True, read_only=True)
    endorsements = ComplaintEndorsementSerializer(many=True, read_only=True)
    tags = ComplaintTagAssignmentSerializer(many=True, read_only=True)
    
    # Computed fields
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    citizen_anonymous_id = serializers.CharField(source='get_citizen_anonymous_id', read_only=True)
    resolution_time = serializers.SerializerMethodField()
    workflow_step = serializers.SerializerMethodField()
    workflow_progress = serializers.SerializerMethodField()
    is_overdue = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Complaint
        fields = [
            'id', 'complaint_id', 'citizen', 'category', 'title', 'description',
            'location_address', 'latitude', 'longitude', 'jurisdiction',
            'status', 'status_display', 'priority', 'priority_display', 'priority_score',
            'ai_confidence_score', 'ai_verification_status', 'ai_verification_notes',
            'human_reviewer', 'human_verification_status', 'human_verification_notes',
            'assigned_official', 'assigned_department', 'assigned_field_worker',
            'commitment_date', 'commitment_visible',
            'resolution_description', 'resolution_date',
            'citizen_verified', 'citizen_verification_date', 'citizen_ratings', 'citizen_comments',
            'sla_deadline', 'sla_breached', 'days_overdue',
            'escalation_level', 'escalated_to', 'escalation_date', 'escalation_reason',
            'allow_public_communication', 'source', 'ip_address', 'user_agent', 'device_info',
            'created_at', 'updated_at', 'submitted_at',
            'proofs', 'history', 'endorsements', 'tags',
            'citizen_anonymous_id', 'resolution_time', 'workflow_step', 'workflow_progress', 'is_overdue'
        ]
        read_only_fields = [
            'id', 'complaint_id', 'citizen', 'ai_confidence_score', 'ai_verification_status',
            'ai_verification_notes', 'human_verification_status', 'human_verification_notes',
            'assigned_official', 'assigned_department', 'assigned_field_worker',
            'commitment_date', 'resolution_date', 'citizen_verified', 'citizen_verification_date',
            'sla_deadline', 'sla_breached', 'days_overdue', 'escalation_level',
            'escalated_to', 'escalation_date', 'escalation_reason',
            'proofs', 'history', 'endorsements', 'tags',
            'citizen_anonymous_id', 'resolution_time', 'workflow_step', 'workflow_progress', 'is_overdue'
        ]
    
    def get_resolution_time(self, obj):
        return obj.get_resolution_time()
    
    def get_workflow_step(self, obj):
        return obj.get_workflow_step()
    
    def get_workflow_progress(self, obj):
        return obj.get_workflow_progress()


class ComplaintCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating complaints."""
    
    proofs = ComplaintProofSerializer(many=True, required=False)
    
    class Meta:
        model = Complaint
        fields = [
            'title', 'description', 'location_address', 'latitude', 'longitude',
            'category', 'jurisdiction', 'proofs', 'source', 'device_info'
        ]
        extra_kwargs = {
            'latitude': {'required': False},
            'longitude': {'required': False},
            'jurisdiction': {'required': False},
        }
    
    def create(self, validated_data):
        proofs_data = validated_data.pop('proofs', [])
        
        # Create complaint
        complaint = Complaint.objects.create(
            citizen=self.context['request'].user,
            status='SUBMITTED',
            submitted_at=timezone.now(),
            **validated_data
        )
        
        # Create proofs
        for proof_data in proofs_data:
            ComplaintProof.objects.create(complaint=complaint, **proof_data)
        
        return complaint


class ComplaintUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating complaints."""
    
    class Meta:
        model = Complaint
        fields = [
            'title', 'description', 'location_address', 'latitude', 'longitude',
            'category', 'jurisdiction', 'priority', 'priority_score',
            'commitment_date', 'commitment_visible',
            'resolution_description', 'allow_public_communication'
        ]
    
    def validate(self, attrs):
        user = self.context['request'].user
        complaint = self.instance
        
        # Check permissions
        if not user.is_staff and complaint.citizen != user:
            raise serializers.ValidationError("You don't have permission to update this complaint.")
        
        return attrs


class ComplaintStatusUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating complaint status."""
    
    class Meta:
        model = Complaint
        fields = ['status', 'assigned_official', 'assigned_department', 
                 'assigned_field_worker', 'commitment_date', 'commitment_visible',
                 'resolution_description', 'escalation_level', 'escalation_reason']
    
    def validate(self, attrs):
        user = self.context['request'].user
        complaint = self.instance
        
        # Check permissions based on role
        if user.is_citizen() and complaint.citizen != user:
            raise serializers.ValidationError("You can only update your own complaints.")
        
        if user.is_official():
            # Officials can update assigned complaints
            if complaint.assigned_official != user:
                raise serializers.ValidationError("You can only update complaints assigned to you.")
        
        return attrs


class ComplaintVerificationSerializer(serializers.ModelSerializer):
    """Serializer for complaint verification."""
    
    class Meta:
        model = Complaint
        fields = ['ai_verification_status', 'ai_confidence_score', 'ai_verification_notes',
                 'human_verification_status', 'human_verification_notes']
    
    def validate(self, attrs):
        user = self.context['request'].user
        
        # Only reviewers can verify
        if user.role != 'REVIEWER':
            raise serializers.ValidationError("Only reviewers can verify complaints.")
        
        return attrs


class ComplaintEndorsementCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating complaint endorsements."""
    
    class Meta:
        model = ComplaintEndorsement
        fields = ['complaint', 'is_anonymous', 'comments']
    
    def validate(self, attrs):
        user = self.context['request'].user
        complaint = attrs['complaint']
        
        # Check if user already endorsed this complaint
        if ComplaintEndorsement.objects.filter(citizen=user, complaint=complaint).exists():
            raise serializers.ValidationError("You have already endorsed this complaint.")
        
        return attrs
    
    def create(self, validated_data):
        endorsement = ComplaintEndorsement.objects.create(
            citizen=self.context['request'].user,
            **validated_data
        )
        return endorsement


class ComplaintSearchSerializer(serializers.Serializer):
    """Serializer for complaint search."""
    
    query = serializers.CharField(required=False)
    category = serializers.CharField(required=False)
    status = serializers.CharField(required=False)
    priority = serializers.CharField(required=False)
    jurisdiction = serializers.CharField(required=False)
    department = serializers.CharField(required=False)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    assigned_official = serializers.CharField(required=False)
    citizen = serializers.CharField(required=False)
    latitude = serializers.FloatField(required=False)
    longitude = serializers.FloatField(required=False)
    radius = serializers.FloatField(required=False, min_value=0.1, max_value=100)
    
    # Pagination
    page = serializers.IntegerField(required=False, default=1)
    page_size = serializers.IntegerField(required=False, default=20)
    
    # Sorting
    ordering = serializers.CharField(required=False, default='-created_at')


class ComplaintAnalyticsSerializer(serializers.Serializer):
    """Serializer for complaint analytics."""
    
    time_range = serializers.CharField(required=False, default='LAST_30_DAYS')
    group_by = serializers.CharField(required=False, default='day')
    filters = serializers.JSONField(required=False, default=dict)
