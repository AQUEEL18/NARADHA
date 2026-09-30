"""
Admin configuration for the verification app.
"""
from django.contrib import admin

from .models import VerificationResult, VerificationAuditLog


@admin.register(VerificationResult)
class VerificationResultAdmin(admin.ModelAdmin):
    list_display = (
        'complaint', 'ai_verification_passed', 'ai_confidence_score',
        'human_verification_passed', 'human_reviewer',
        'is_fully_verified', 'is_rejected', 'updated_at'
    )
    list_filter = (
        'ai_verification_passed', 'human_verification_passed',
        'is_fully_verified', 'is_rejected'
    )
    search_fields = ('complaint__complaint_id',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(VerificationAuditLog)
class VerificationAuditLogAdmin(admin.ModelAdmin):
    list_display = ('verification', 'action', 'performed_by', 'is_ai_action', 'created_at')
    list_filter = ('action', 'is_ai_action')
    readonly_fields = ('created_at',)
