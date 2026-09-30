"""
Serializers for the verification app.
"""
from rest_framework import serializers

from .models import VerificationResult, VerificationAuditLog


class VerificationResultSerializer(serializers.ModelSerializer):
    """Serializer for VerificationResult."""

    complaint_id_str = serializers.CharField(
        source='complaint.complaint_id', read_only=True
    )
    reviewer_name = serializers.CharField(
        source='human_reviewer.get_short_name', read_only=True, default=None
    )

    class Meta:
        model = VerificationResult
        fields = [
            'id', 'complaint', 'complaint_id_str',
            'ai_verification_passed', 'ai_confidence_score', 'ai_verified_at',
            'ai_notes', 'human_verification_passed', 'human_reviewer',
            'reviewer_name', 'human_verification_notes', 'human_verified_at',
            'is_fully_verified', 'is_rejected', 'rejection_reason',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'is_fully_verified', 'created_at', 'updated_at'
        ]


class VerificationAuditLogSerializer(serializers.ModelSerializer):
    """Serializer for VerificationAuditLog."""

    performed_by_name = serializers.CharField(
        source='performed_by.get_short_name', read_only=True, default=None
    )

    class Meta:
        model = VerificationAuditLog
        fields = [
            'id', 'verification', 'action', 'performed_by', 'performed_by_name',
            'is_ai_action', 'details', 'notes', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
