"""
URLs for Complaint app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ComplaintViewSet, ComplaintCategoryViewSet, ComplaintProofViewSet,
    ComplaintSearchView
)

router = DefaultRouter()
router.register(r'complaints', ComplaintViewSet, basename='complaint')
router.register(r'categories', ComplaintCategoryViewSet, basename='category')
router.register(r'proofs', ComplaintProofViewSet, basename='proof')

urlpatterns = [
    path('', include(router.urls)),
    path('search/', ComplaintSearchView.as_view(), name='complaint-search'),
]
