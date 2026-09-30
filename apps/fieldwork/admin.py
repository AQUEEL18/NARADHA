"""
Admin configuration for the fieldwork app.
"""
from django.contrib import admin

from .models import (
    FieldTask, FieldTaskHistory, FieldWorkerLocation,
    FieldWorkerPerformance, FieldTaskChecklist, FieldTaskChecklistTemplate
)


@admin.register(FieldTask)
class FieldTaskAdmin(admin.ModelAdmin):
    list_display = (
        'task_id', 'title', 'complaint', 'assigned_to', 'status',
        'priority', 'deadline', 'created_at'
    )
    list_filter = ('status', 'priority', 'work_type')
    search_fields = ('task_id', 'title', 'complaint__complaint_id')
    date_hierarchy = 'created_at'
    readonly_fields = ('task_id', 'created_at', 'updated_at')


@admin.register(FieldTaskHistory)
class FieldTaskHistoryAdmin(admin.ModelAdmin):
    list_display = ('task', 'previous_status', 'new_status', 'changed_by', 'created_at')
    list_filter = ('new_status',)
    readonly_fields = ('created_at',)


@admin.register(FieldWorkerLocation)
class FieldWorkerLocationAdmin(admin.ModelAdmin):
    list_display = (
        'worker', 'latitude', 'longitude', 'accuracy',
        'current_task', 'created_at'
    )
    readonly_fields = ('created_at',)


@admin.register(FieldWorkerPerformance)
class FieldWorkerPerformanceAdmin(admin.ModelAdmin):
    list_display = (
        'worker', 'total_tasks', 'completed_tasks', 'avg_quality_rating',
        'performance_score', 'last_active'
    )
    readonly_fields = ('created_at', 'updated_at')


@admin.register(FieldTaskChecklist)
class FieldTaskChecklistAdmin(admin.ModelAdmin):
    list_display = (
        'task', 'item_name', 'is_required', 'is_completed', 'order'
    )
    list_filter = ('is_required', 'is_completed')


@admin.register(FieldTaskChecklistTemplate)
class FieldTaskChecklistTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'work_type', 'is_active', 'updated_at')
    list_filter = ('work_type', 'is_active')
