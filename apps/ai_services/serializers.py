"""
Serializers for AI Services models.
"""
from rest_framework import serializers
from .models import (
    AIModel, AIServiceLog, ImageAnalysisResult, TextAnalysisResult,
    PriorityScoringResult, RoutingSuggestion, TranslationRequest,
    VoiceRecognitionResult, AITrainingData
)
from apps.complaints.models import Complaint, ComplaintProof
from apps.users.serializers import UserSerializer


class AIModelSerializer(serializers.ModelSerializer):
    """Serializer for AIModel model."""
    
    class Meta:
        model = AIModel
        fields = ['id', 'name', 'description', 'model_type', 'version',
                 'model_file', 'config', 'is_active', 'is_trained',
                 'accuracy', 'precision', 'recall', 'f1_score',
                 'training_data_count', 'last_trained', 'created_at', 'updated_at']
        read_only_fields = ['id', 'is_trained', 'last_trained']


class AIServiceLogSerializer(serializers.ModelSerializer):
    """Serializer for AIServiceLog model."""
    
    triggered_by = UserSerializer(read_only=True)
    
    class Meta:
        model = AIServiceLog
        fields = ['id', 'service_name', 'model', 'request_data', 'response_data',
                 'processing_time', 'confidence_score', 'status', 'error_message',
                 'complaint', 'proof', 'triggered_by', 'created_at']
        read_only_fields = ['id', 'created_at']


class ImageAnalysisResultSerializer(serializers.ModelSerializer):
    """Serializer for ImageAnalysisResult model."""
    
    proof = serializers.PrimaryKeyRelatedField(read_only=True)
    
    class Meta:
        model = ImageAnalysisResult
        fields = ['id', 'proof', 'analysis_complete', 'image_width', 'image_height',
                 'image_format', 'camera_make', 'camera_model', 'capture_timestamp',
                 'gps_latitude', 'gps_longitude', 'gps_accuracy', 'primary_objects',
                 'object_confidences', 'scene_type', 'scene_confidence', 'quality_score',
                 'blur_score', 'brightness_score', 'contrast_score',
                 'manipulation_detected', 'manipulation_confidence', 'manipulation_type',
                 'relevance_score', 'relevance_keywords', 'authenticity_score',
                 'authenticity_notes', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class TextAnalysisResultSerializer(serializers.ModelSerializer):
    """Serializer for TextAnalysisResult model."""
    
    complaint = serializers.PrimaryKeyRelatedField(read_only=True)
    
    class Meta:
        model = TextAnalysisResult
        fields = ['id', 'complaint', 'analysis_complete', 'text_length', 'word_count',
                 'sentence_count', 'detected_language', 'language_confidence',
                 'sentiment_score', 'sentiment_label', 'sentiment_confidence',
                 'emotions', 'keywords', 'keyword_scores', 'primary_topic',
                 'secondary_topics', 'entities', 'urgency_score', 'urgency_keywords',
                 'severity_score', 'severity_indicators', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class PriorityScoringResultSerializer(serializers.ModelSerializer):
    """Serializer for PriorityScoringResult model."""
    
    complaint = serializers.PrimaryKeyRelatedField(read_only=True)
    
    class Meta:
        model = PriorityScoringResult
        fields = ['id', 'complaint', 'base_score', 'urgency_score', 'severity_score',
                 'impact_score', 'recurrence_score', 'evidence_score',
                 'final_score', 'priority_level', 'factors', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class RoutingSuggestionSerializer(serializers.ModelSerializer):
    """Serializer for RoutingSuggestion model."""
    
    complaint = serializers.PrimaryKeyRelatedField(read_only=True)
    suggested_department = serializers.StringRelatedField(read_only=True)
    suggested_jurisdiction = serializers.StringRelatedField(read_only=True)
    suggested_officials = UserSerializer(many=True, read_only=True)
    accepted_by = UserSerializer(read_only=True)
    
    class Meta:
        model = RoutingSuggestion
        fields = ['id', 'complaint', 'suggested_department', 'suggested_jurisdiction',
                 'suggested_officials', 'department_confidence', 'jurisdiction_confidence',
                 'officials_confidence', 'reasoning', 'accepted', 'accepted_by',
                 'accepted_at', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class TranslationRequestSerializer(serializers.ModelSerializer):
    """Serializer for TranslationRequest model."""
    
    complaint = serializers.PrimaryKeyRelatedField(read_only=True)
    triggered_by = UserSerializer(read_only=True)
    
    class Meta:
        model = TranslationRequest
        fields = ['id', 'original_text', 'source_language', 'target_language',
                 'translated_text', 'status', 'error_message', 'complaint',
                 'message', 'triggered_by', 'created_at', 'updated_at']
        read_only_fields = ['id', 'translated_text', 'status', 'error_message',
                           'complaint', 'message', 'triggered_by', 'created_at', 'updated_at']


class VoiceRecognitionResultSerializer(serializers.ModelSerializer):
    """Serializer for VoiceRecognitionResult model."""
    
    class Meta:
        model = VoiceRecognitionResult
        fields = ['id', 'audio_file', 'recognized_text', 'detected_language',
                 'language_confidence', 'created_at', 'updated_at']
        read_only_fields = ['id', 'recognized_text', 'detected_language',
                           'language_confidence', 'created_at', 'updated_at']


class AITrainingDataSerializer(serializers.ModelSerializer):
    """Serializer for AITrainingData model."""
    
    verified_by = UserSerializer(read_only=True)
    
    class Meta:
        model = AITrainingData
        fields = ['id', 'data_type', 'data_file', 'labels', 'source',
                 'quality_score', 'is_verified', 'verified_by', 'created_at', 'updated_at']
        read_only_fields = ['id', 'is_verified', 'verified_by', 'created_at', 'updated_at']
