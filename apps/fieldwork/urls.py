"""
URLs for Fieldwork app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    FieldTaskViewSet, FieldTaskHistoryViewSet, FieldWorkerLocationViewSet,
    FieldWorkerPerformanceViewSet, FieldTaskChecklistViewSet,
    FieldTaskChecklistTemplateViewSet, UpdateLocationView
)

router = DefaultRouter()
router.register(r'tasks', FieldTaskViewSet, basename='field-task')
router.register(r'task-history', FieldTaskHistoryViewSet, basename='field-task-history')
router.register(r'locations', FieldWorkerLocationViewSet, basename='field-worker-location')
router.register(r'performance', FieldWorkerPerformanceViewSet, basename='field-worker-performance')
router.register(r'checklists', FieldTaskChecklistViewSet, basename='field-task-checklist')
router.register(r'checklist-templates', FieldTaskChecklistTemplateViewSet, basename='field-task-checklist-template')

urlpatterns = [
    path('', include(router.urls)),
    path('location/update/', UpdateLocationView.as_view(), name='update-location'),
]
