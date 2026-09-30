"""
URLs for the verification app.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import VerificationResultViewSet

router = DefaultRouter()
router.register(r'', VerificationResultViewSet, basename='verification-result')

urlpatterns = [
    path('', include(router.urls)),
]
