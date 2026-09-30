"""
Frontend URLs for Complaint app (Django templates).
"""
from django.urls import path
from .views_frontend import (
    HomeView, ComplaintCreateView, ComplaintDetailView,
    ComplaintListView, ComplaintTrackingView, ComplaintVerifyView,
    complaint_action_view,
)

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('file-complaint/', ComplaintCreateView.as_view(), name='file_complaint'),
    path('complaints/', ComplaintListView.as_view(), name='complaint_list'),
    path('complaints/<str:complaint_id>/', ComplaintDetailView.as_view(), name='complaint_detail'),
    path('complaints/<str:complaint_id>/track/', ComplaintTrackingView.as_view(), name='complaint_track'),
    path('complaints/<str:complaint_id>/verify/', ComplaintVerifyView.as_view(), name='complaint_verify'),
    path('complaints/<str:complaint_id>/action/', complaint_action_view, name='complaint_action'),
]
