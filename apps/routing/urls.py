"""
URLs for the routing app.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import OfficialWorkloadViewSet, RoutingLogViewSet

router = DefaultRouter()
router.register(r'logs', RoutingLogViewSet, basename='routing-log')
router.register(r'workloads', OfficialWorkloadViewSet, basename='official-workload')

urlpatterns = [
    path('', include(router.urls)),
]
