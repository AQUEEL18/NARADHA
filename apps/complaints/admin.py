"""
Admin configuration for the complaints app.
"""
from django.contrib import admin

from .models import (
    Complaint, ComplaintCategory, ComplaintProof, ComplaintHistory,
    ComplaintEndorsement, ComplaintTag, ComplaintTagAssignment
)


@admin.register(ComplaintCategory)
class ComplaintCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'department', 'priority_weight', 'is_active')
    list_filter = ('is_active', 'department')
    search_fields = ('name', 'code', 'description')
    prepopulated_fields = {}


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = (
        'complaint_id', 'title', 'status', 'priority', 'category',
        'citizen', 'assigned_official', 'sla_breached', 'created_at'
    )
    list_filter = (
        'status', 'priority', 'sla_breached', 'ai_verification_status',
        'human_verification_status', 'category', 'source'
    )
    search_fields = ('complaint_id', 'title', 'description', 'location_address')
    date_hierarchy = 'created_at'
    readonly_fields = ('complaint_id', 'created_at', 'updated_at')
    filter_horizontal = ()


@admin.register(ComplaintProof)
class ComplaintProofAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'complaint', 'proof_type', 'file_size',
        'ai_authenticity_score', 'ai_manipulation_detected',
        'human_approved', 'created_at'
    )
    list_filter = ('proof_type', 'ai_manipulation_detected', 'human_approved')
    search_fields = ('complaint__complaint_id',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ComplaintHistory)
class ComplaintHistoryAdmin(admin.ModelAdmin):
    list_display = ('complaint', 'previous_status', 'new_status', 'changed_by', 'created_at')
    list_filter = ('new_status',)
    search_fields = ('complaint__complaint_id', 'notes')
    readonly_fields = ('created_at',)


@admin.register(ComplaintEndorsement)
class ComplaintEndorsementAdmin(admin.ModelAdmin):
    list_display = ('complaint', 'citizen', 'is_anonymous', 'created_at')
    list_filter = ('is_anonymous',)
    search_fields = ('complaint__complaint_id', 'citizen__email')


@admin.register(ComplaintTag)
class ComplaintTagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'color', 'is_active')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(ComplaintTagAssignment)
class ComplaintTagAssignmentAdmin(admin.ModelAdmin):
    list_display = ('complaint', 'tag', 'assigned_by', 'created_at')
    search_fields = ('complaint__complaint_id', 'tag__name')
