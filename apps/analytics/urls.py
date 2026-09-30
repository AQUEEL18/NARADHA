"""
URLs for Analytics app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AnalyticsView, DepartmentPerformanceViewSet, OfficialPerformanceViewSet,
    IssuePatternViewSet, HeatmapDataViewSet
)

router = DefaultRouter()
router.register(r'department-performance', DepartmentPerformanceViewSet, basename='analytics-department-performance')
router.register(r'official-performance', OfficialPerformanceViewSet, basename='analytics-official-performance')
router.register(r'issue-patterns', IssuePatternViewSet, basename='analytics-issue-pattern')
router.register(r'heatmap-data', HeatmapDataViewSet, basename='analytics-heatmap-data')

urlpatterns = [
    path('', include(router.urls)),
    path('comprehensive/', AnalyticsView.as_view(), name='analytics-comprehensive'),
]
