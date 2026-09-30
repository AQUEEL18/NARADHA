"""
Admin configuration for the dashboard app.
"""
from django.contrib import admin

from .models import (
    DashboardWidget, DashboardView, PublicDashboardSettings,
    AnalyticsData, DashboardAlert
)


@admin.register(DashboardWidget)
class DashboardWidgetAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'widget_type', 'position_x', 'position_y',
        'is_visible', 'is_public', 'updated_at'
    )
    list_filter = ('widget_type', 'is_visible', 'is_public')


@admin.register(DashboardView)
class DashboardViewAdmin(admin.ModelAdmin):
    list_display = ('name', 'view_type', 'is_active', 'created_at')
    list_filter = ('view_type', 'is_active')
    filter_horizontal = ('widgets', 'allowed_users', 'allowed_departments')


@admin.register(PublicDashboardSettings)
class PublicDashboardSettingsAdmin(admin.ModelAdmin):
    list_display = (
        'anonymization_level', 'default_time_range',
        'show_resolution_times', 'show_department_rankings', 'updated_at'
    )


@admin.register(AnalyticsData)
class AnalyticsDataAdmin(admin.ModelAdmin):
    list_display = ('data_type', 'start_date', 'end_date', 'updated_at')
    list_filter = ('data_type',)


@admin.register(DashboardAlert)
class DashboardAlertAdmin(admin.ModelAdmin):
    list_display = (
        'alert_type', 'title', 'severity', 'complaint', 'department',
        'is_active', 'is_acknowledged', 'created_at'
    )
    list_filter = ('alert_type', 'severity', 'is_active', 'is_acknowledged')
    search_fields = ('title', 'message')
