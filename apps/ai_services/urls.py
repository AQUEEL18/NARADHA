"""
URLs for AI Services app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AIModelViewSet, AIServiceLogViewSet, ImageAnalysisResultViewSet,
    TextAnalysisResultViewSet, PriorityScoringResultViewSet,
    RoutingSuggestionViewSet, TranslationRequestViewSet,
    VoiceRecognitionResultViewSet, AITrainingDataViewSet,
    VerifyComplaintView, ScorePriorityView, RouteComplaintView,
    ProcessAllComplaintsView, AnalyzeImageView, TranslateTextView,
    RecognizeVoiceView
)

router = DefaultRouter()
router.register(r'models', AIModelViewSet, basename='ai-model')
router.register(r'logs', AIServiceLogViewSet, basename='ai-log')
router.register(r'image-analyses', ImageAnalysisResultViewSet, basename='image-analysis')
router.register(r'text-analyses', TextAnalysisResultViewSet, basename='text-analysis')
router.register(r'priority-scores', PriorityScoringResultViewSet, basename='priority-score')
router.register(r'routing-suggestions', RoutingSuggestionViewSet, basename='routing-suggestion')
router.register(r'translations', TranslationRequestViewSet, basename='translation')
router.register(r'voice-recognitions', VoiceRecognitionResultViewSet, basename='voice-recognition')
router.register(r'training-data', AITrainingDataViewSet, basename='training-data')

urlpatterns = [
    path('', include(router.urls)),
    
    # AI Processing endpoints
    path('complaints/<int:pk>/verify/', VerifyComplaintView.as_view(), name='ai-verify-complaint'),
    path('complaints/<int:pk>/score/', ScorePriorityView.as_view(), name='ai-score-priority'),
    path('complaints/<int:pk>/route/', RouteComplaintView.as_view(), name='ai-route-complaint'),
    path('complaints/process-all/', ProcessAllComplaintsView.as_view(), name='ai-process-all'),
    
    # Direct AI service endpoints
    path('proofs/<int:pk>/analyze/', AnalyzeImageView.as_view(), name='ai-analyze-image'),
    path('translate/', TranslateTextView.as_view(), name='ai-translate'),
    path('recognize-voice/', RecognizeVoiceView.as_view(), name='ai-recognize-voice'),
]
