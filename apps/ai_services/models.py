"""
AI Services models for NARADHA application.
"""
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from apps.complaints.models import Complaint, ComplaintProof
from apps.users.models import CustomUser


class AIModel(models.Model):
    """AI models used in the system."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    
    model_type = models.CharField(
        max_length=50,
        choices=[
            ('IMAGE_ANALYSIS', 'Image Analysis'),
            ('TEXT_ANALYSIS', 'Text Analysis'),
            ('VIDEO_ANALYSIS', 'Video Analysis'),
            ('AUDIO_ANALYSIS', 'Audio Analysis'),
            ('SENTIMENT_ANALYSIS', 'Sentiment Analysis'),
            ('PRIORITY_SCORING', 'Priority Scoring'),
            ('ROUTING', 'Routing'),
            ('TRANSLATION', 'Translation'),
            ('VOICE_RECOGNITION', 'Voice Recognition'),
        ]
    )
    
    version = models.CharField(max_length=50)
    
    # Model file
    model_file = models.FileField(upload_to='ai_models/', blank=True, null=True)
    
    # Configuration
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text='Model configuration parameters'
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    is_trained = models.BooleanField(default=False)
    
    # Performance metrics
    accuracy = models.FloatField(default=0.0, help_text='Accuracy (0-100%)')
    precision = models.FloatField(default=0.0, help_text='Precision (0-100%)')
    recall = models.FloatField(default=0.0, help_text='Recall (0-100%)')
    f1_score = models.FloatField(default=0.0, help_text='F1 Score (0-100%)')
    
    # Training data
    training_data_count = models.PositiveIntegerField(default=0)
    last_trained = models.DateTimeField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('AI Model')
        verbose_name_plural = _('AI Models')
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} v{self.version}"


class AIServiceLog(models.Model):
    """Log of AI service calls."""
    service_name = models.CharField(max_length=100)
    model = models.ForeignKey(
        AIModel,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='service_logs'
    )
    
    # Request data
    request_data = models.JSONField(default=dict, blank=True)
    
    # Response data
    response_data = models.JSONField(default=dict, blank=True)
    
    # Processing
    processing_time = models.FloatField(default=0.0, help_text='Processing time in seconds')
    confidence_score = models.FloatField(default=0.0, help_text='Confidence score (0-100%)')
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('SUCCESS', 'Success'),
            ('FAILURE', 'Failure'),
            ('ERROR', 'Error'),
            ('TIMEOUT', 'Timeout'),
        ],
        default='SUCCESS'
    )
    
    error_message = models.TextField(blank=True)
    
    # Related objects
    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='ai_service_logs'
    )
    
    proof = models.ForeignKey(
        ComplaintProof,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='ai_service_logs'
    )
    
    # User who triggered the service
    triggered_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='triggered_ai_services'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('AI Service Log')
        verbose_name_plural = _('AI Service Logs')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['service_name']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.service_name} - {self.status}"


class ImageAnalysisResult(models.Model):
    """Results of image analysis."""
    proof = models.OneToOneField(
        ComplaintProof,
        on_delete=models.CASCADE,
        related_name='image_analysis_result'
    )
    
    # Analysis results
    analysis_complete = models.BooleanField(default=False)
    
    # Basic analysis
    image_width = models.PositiveIntegerField(blank=True, null=True)
    image_height = models.PositiveIntegerField(blank=True, null=True)
    image_format = models.CharField(max_length=20, blank=True)
    
    # Metadata
    camera_make = models.CharField(max_length=100, blank=True)
    camera_model = models.CharField(max_length=100, blank=True)
    capture_timestamp = models.DateTimeField(blank=True, null=True)
    
    # GPS data
    gps_latitude = models.DecimalField(max_digits=10, decimal_places=8, blank=True, null=True)
    gps_longitude = models.DecimalField(max_digits=11, decimal_places=8, blank=True, null=True)
    gps_accuracy = models.FloatField(blank=True, null=True)
    
    # Content analysis
    primary_objects = models.JSONField(
        default=list,
        blank=True,
        help_text='List of primary objects detected'
    )
    object_confidences = models.JSONField(
        default=dict,
        blank=True,
        help_text='Dictionary of object names to confidence scores'
    )
    
    scene_type = models.CharField(max_length=100, blank=True)
    scene_confidence = models.FloatField(default=0.0)
    
    # Quality analysis
    quality_score = models.FloatField(default=0.0, help_text='0-100%')
    blur_score = models.FloatField(default=0.0, help_text='0-100% (higher = more blur)')
    brightness_score = models.FloatField(default=0.0, help_text='0-100%')
    contrast_score = models.FloatField(default=0.0, help_text='0-100%')
    
    # Manipulation detection
    manipulation_detected = models.BooleanField(default=False)
    manipulation_confidence = models.FloatField(default=0.0, help_text='0-100%')
    manipulation_type = models.CharField(max_length=100, blank=True)
    
    # Relevance analysis
    relevance_score = models.FloatField(default=0.0, help_text='0-100%')
    relevance_keywords = models.JSONField(
        default=list,
        blank=True,
        help_text='List of keywords that match the complaint'
    )
    
    # Authenticity
    authenticity_score = models.FloatField(default=0.0, help_text='0-100%')
    authenticity_notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Image Analysis Result')
        verbose_name_plural = _('Image Analysis Results')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Image Analysis: {self.proof.id}"


class TextAnalysisResult(models.Model):
    """Results of text analysis."""
    complaint = models.OneToOneField(
        Complaint,
        on_delete=models.CASCADE,
        related_name='text_analysis_result'
    )
    
    # Analysis results
    analysis_complete = models.BooleanField(default=False)
    
    # Basic analysis
    text_length = models.PositiveIntegerField(default=0)
    word_count = models.PositiveIntegerField(default=0)
    sentence_count = models.PositiveIntegerField(default=0)
    
    # Language detection
    detected_language = models.CharField(max_length=10, blank=True)
    language_confidence = models.FloatField(default=0.0)
    
    # Sentiment analysis
    sentiment_score = models.FloatField(default=0.0, help_text='-1 (negative) to +1 (positive)')
    sentiment_label = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ('POSITIVE', 'Positive'),
            ('NEGATIVE', 'Negative'),
            ('NEUTRAL', 'Neutral'),
            ('MIXED', 'Mixed'),
        ]
    )
    sentiment_confidence = models.FloatField(default=0.0)
    
    # Emotion analysis
    emotions = models.JSONField(
        default=dict,
        blank=True,
        help_text='Dictionary of emotions to scores (0-1)'
    )
    
    # Keyword extraction
    keywords = models.JSONField(
        default=list,
        blank=True,
        help_text='List of extracted keywords'
    )
    keyword_scores = models.JSONField(
        default=dict,
        blank=True,
        help_text='Dictionary of keywords to importance scores'
    )
    
    # Topic modeling
    primary_topic = models.CharField(max_length=100, blank=True)
    secondary_topics = models.JSONField(
        default=list,
        blank=True,
        help_text='List of secondary topics'
    )
    
    # Named entity recognition
    entities = models.JSONField(
        default=dict,
        blank=True,
        help_text='Dictionary of entity types to lists of entities'
    )
    
    # Urgency analysis
    urgency_score = models.FloatField(default=0.0, help_text='0-100%')
    urgency_keywords = models.JSONField(
        default=list,
        blank=True,
        help_text='List of urgency-related keywords found'
    )
    
    # Severity analysis
    severity_score = models.FloatField(default=0.0, help_text='0-100%')
    severity_indicators = models.JSONField(
        default=list,
        blank=True,
        help_text='List of severity indicators found'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Text Analysis Result')
        verbose_name_plural = _('Text Analysis Results')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Text Analysis: {self.complaint.complaint_id}"


class PriorityScoringResult(models.Model):
    """Results of priority scoring."""
    complaint = models.OneToOneField(
        Complaint,
        on_delete=models.CASCADE,
        related_name='priority_scoring_result'
    )
    
    # Score breakdown
    base_score = models.FloatField(default=0.0)
    urgency_score = models.FloatField(default=0.0)
    severity_score = models.FloatField(default=0.0)
    impact_score = models.FloatField(default=0.0)
    recurrence_score = models.FloatField(default=0.0)
    evidence_score = models.FloatField(default=0.0)
    
    # Final score
    final_score = models.FloatField(default=0.0)
    priority_level = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ('LOW', 'Low'),
            ('MEDIUM', 'Medium'),
            ('HIGH', 'High'),
            ('CRITICAL', 'Critical'),
        ]
    )
    
    # Factors
    factors = models.JSONField(
        default=dict,
        blank=True,
        help_text='Dictionary of factors and their contributions to the score'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Priority Scoring Result')
        verbose_name_plural = _('Priority Scoring Results')
        ordering = ['-final_score']
    
    def __str__(self):
        return f"Priority Score: {self.complaint.complaint_id} ({self.final_score})"


class RoutingSuggestion(models.Model):
    """AI routing suggestions."""
    complaint = models.OneToOneField(
        Complaint,
        on_delete=models.CASCADE,
        related_name='routing_suggestion'
    )
    
    # Suggested targets
    suggested_department = models.ForeignKey(
        'users.Department',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='routing_suggestions'
    )
    
    suggested_jurisdiction = models.ForeignKey(
        'users.Jurisdiction',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='routing_suggestions'
    )
    
    suggested_officials = models.ManyToManyField(
        CustomUser,
        related_name='routing_suggestions',
        blank=True,
        limit_choices_to={'role__in': ['OFFICIAL', 'MINISTER']}
    )
    
    # Confidence scores
    department_confidence = models.FloatField(default=0.0, help_text='0-100%')
    jurisdiction_confidence = models.FloatField(default=0.0, help_text='0-100%')
    officials_confidence = models.JSONField(
        default=dict,
        blank=True,
        help_text='Dictionary of official IDs to confidence scores'
    )
    
    # Reasoning
    reasoning = models.TextField(blank=True)
    
    # Status
    accepted = models.BooleanField(default=False)
    accepted_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='accepted_routing_suggestions'
    )
    accepted_at = models.DateTimeField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Routing Suggestion')
        verbose_name_plural = _('Routing Suggestions')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Routing Suggestion: {self.complaint.complaint_id}"


class TranslationRequest(models.Model):
    """Translation requests for multilingual support."""
    original_text = models.TextField()
    source_language = models.CharField(max_length=10, default='auto')
    target_language = models.CharField(max_length=10)
    
    translated_text = models.TextField(blank=True)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', 'Pending'),
            ('COMPLETED', 'Completed'),
            ('FAILED', 'Failed'),
        ],
        default='PENDING'
    )
    
    error_message = models.TextField(blank=True)
    
    # Related objects
    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='translation_requests'
    )
    
    message = models.ForeignKey(
        'messaging.Message',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='translation_requests'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Translation Request')
        verbose_name_plural = _('Translation Requests')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Translate {self.source_language} → {self.target_language}"


class VoiceRecognitionResult(models.Model):
    """Results of voice recognition."""
    audio_file = models.FileField(upload_to='voice_recordings/')
    
    # Recognition results
    recognized_text = models.TextField(blank=True)
    
    # Language
    detected_language = models.CharField(max_length=10, blank=True)
    language_confidence = models.FloatField(default=0.0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Voice Recognition Result')
        verbose_name_plural = _('Voice Recognition Results')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Voice Recognition: {self.audio_file.name}"


class AITrainingData(models.Model):
    """Training data for AI models."""
    data_type = models.CharField(
        max_length=50,
        choices=[
            ('IMAGE', 'Image'),
            ('TEXT', 'Text'),
            ('VIDEO', 'Video'),
            ('AUDIO', 'Audio'),
        ]
    )
    
    # Data file
    data_file = models.FileField(upload_to='ai_training_data/')
    
    # Labels
    labels = models.JSONField(
        default=dict,
        blank=True,
        help_text='Dictionary of labels for the data'
    )
    
    # Metadata
    source = models.CharField(max_length=100, blank=True)
    quality_score = models.FloatField(default=0.0, help_text='0-100%')
    
    # Status
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='verified_training_data'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('AI Training Data')
        verbose_name_plural = _('AI Training Data')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Training Data: {self.data_file.name}"
