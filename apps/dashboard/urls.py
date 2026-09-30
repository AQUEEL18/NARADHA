"""
URLs for Dashboard app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DashboardWidgetViewSet, DashboardViewViewSet, PublicDashboardSettingsViewSet,
    AnalyticsDataViewSet, DepartmentPerformanceViewSet, OfficialPerformanceViewSet,
    IssuePatternViewSet, HeatmapDataViewSet, DashboardAlertViewSet,
    PublicDashboardView, OfficialDashboardView, MinisterDashboardView,
    CitizenDashboardView, AdminDashboardView
)

router = DefaultRouter()
router.register(r'widgets', DashboardWidgetViewSet, basename='dashboard-widget')
router.register(r'views', DashboardViewViewSet, basename='dashboard-view')
router.register(r'settings', PublicDashboardSettingsViewSet, basename='dashboard-settings')
router.register(r'analytics-data', AnalyticsDataViewSet, basename='analytics-data')
router.register(r'department-performance', DepartmentPerformanceViewSet, basename='department-performance')
router.register(r'official-performance', OfficialPerformanceViewSet, basename='official-performance')
router.register(r'issue-patterns', IssuePatternViewSet, basename='issue-pattern')
router.register(r'heatmap-data', HeatmapDataViewSet, basename='heatmap-data')
router.register(r'alerts', DashboardAlertViewSet, basename='dashboard-alert')

urlpatterns = [
    path('', include(router.urls)),
    
    # Dashboard views
    path('public/', PublicDashboardView.as_view(), name='public-dashboard'),
    path('official/', OfficialDashboardView.as_view(), name='official-dashboard'),
    path('minister/', MinisterDashboardView.as_view(), name='minister-dashboard'),
    path('citizen/', CitizenDashboardView.as_view(), name='citizen-dashboard'),
    path('admin/', AdminDashboardView.as_view(), name='admin-dashboard'),
]
