"""
Admin configuration for the AI services app.
"""
from django.contrib import admin

from .models import (
    AIModel, AIServiceLog, ImageAnalysisResult, TextAnalysisResult,
    PriorityScoringResult, RoutingSuggestion, TranslationRequest,
    VoiceRecognitionResult, AITrainingData
)


@admin.register(AIModel)
class AIModelAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'model_type', 'version', 'is_active', 'is_trained',
        'accuracy', 'last_trained'
    )
    list_filter = ('model_type', 'is_active', 'is_trained')
    search_fields = ('name', 'version')


@admin.register(AIServiceLog)
class AIServiceLogAdmin(admin.ModelAdmin):
    list_display = (
        'service_name', 'status', 'processing_time',
        'confidence_score', 'complaint', 'created_at'
    )
    list_filter = ('status', 'service_name')
    search_fields = ('service_name', 'error_message')
    readonly_fields = ('created_at',)


@admin.register(ImageAnalysisResult)
class ImageAnalysisResultAdmin(admin.ModelAdmin):
    list_display = (
        'proof', 'analysis_complete', 'quality_score',
        'manipulation_detected', 'authenticity_score', 'created_at'
    )
    list_filter = ('analysis_complete', 'manipulation_detected')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(TextAnalysisResult)
class TextAnalysisResultAdmin(admin.ModelAdmin):
    list_display = (
        'complaint', 'analysis_complete', 'detected_language',
        'sentiment_label', 'urgency_score', 'severity_score', 'created_at'
    )
    list_filter = ('analysis_complete', 'sentiment_label')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(PriorityScoringResult)
class PriorityScoringResultAdmin(admin.ModelAdmin):
    list_display = (
        'complaint', 'final_score', 'priority_level', 'updated_at'
    )
    ordering = ('-final_score',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(RoutingSuggestion)
class RoutingSuggestionAdmin(admin.ModelAdmin):
    list_display = (
        'complaint', 'suggested_department', 'department_confidence',
        'accepted', 'created_at'
    )
    list_filter = ('accepted',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(TranslationRequest)
class TranslationRequestAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'source_language', 'target_language', 'status', 'created_at'
    )
    list_filter = ('status',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(VoiceRecognitionResult)
class VoiceRecognitionResultAdmin(admin.ModelAdmin):
    list_display = ('id', 'detected_language', 'language_confidence', 'created_at')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(AITrainingData)
class AITrainingDataAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'data_type', 'source', 'quality_score', 'is_verified', 'created_at'
    )
    list_filter = ('data_type', 'is_verified')
