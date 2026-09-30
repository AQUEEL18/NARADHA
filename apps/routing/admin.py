"""
Admin configuration for the routing app.
"""
from django.contrib import admin

from .models import OfficialWorkload, RoutingLog


@admin.register(RoutingLog)
class RoutingLogAdmin(admin.ModelAdmin):
    list_display = (
        'complaint', 'previous_official', 'new_official',
        'new_department', 'routing_method', 'routing_confidence', 'created_at'
    )
    list_filter = ('routing_method',)
    search_fields = ('complaint__complaint_id',)
    readonly_fields = ('created_at',)


@admin.register(OfficialWorkload)
class OfficialWorkloadAdmin(admin.ModelAdmin):
    list_display = (
        'official', 'assigned_complaints', 'resolved_complaints',
        'active_complaints', 'max_daily_capacity', 'is_available', 'updated_at'
    )
    list_filter = ('is_available',)
    readonly_fields = ('assigned_complaints', 'resolved_complaints', 'active_complaints')
