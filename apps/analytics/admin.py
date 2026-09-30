"""
Admin configuration for the analytics app.
"""
from django.contrib import admin

from .models import (
    DepartmentPerformance, OfficialPerformance, IssuePattern,
    HeatmapData, AnalyticsSnapshot
)


@admin.register(DepartmentPerformance)
class DepartmentPerformanceAdmin(admin.ModelAdmin):
    list_display = (
        'department', 'total_complaints', 'resolved_complaints',
        'sla_compliance_rate', 'performance_score', 'rank', 'updated_at'
    )
    search_fields = ('department__name',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(OfficialPerformance)
class OfficialPerformanceAdmin(admin.ModelAdmin):
    list_display = (
        'official', 'total_complaints', 'resolved_complaints',
        'avg_citizen_rating', 'performance_score', 'rank', 'updated_at'
    )
    search_fields = ('official__email', 'official__first_name', 'official__last_name')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(IssuePattern)
class IssuePatternAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'category', 'complaint_count', 'avg_priority_score',
        'is_active', 'is_resolved', 'last_seen'
    )
    list_filter = ('is_active', 'is_resolved', 'category')
    search_fields = ('name', 'description')
    filter_horizontal = ('jurisdictions',)


@admin.register(HeatmapData)
class HeatmapDataAdmin(admin.ModelAdmin):
    list_display = (
        'location', 'latitude', 'longitude', 'complaint_count',
        'resolved_count', 'start_date', 'end_date'
    )
    search_fields = ('location',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(AnalyticsSnapshot)
class AnalyticsSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        'snapshot_date', 'total_complaints', 'new_complaints',
        'resolved_complaints', 'sla_compliance_rate'
    )
    readonly_fields = ('created_at', 'updated_at')
