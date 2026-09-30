"""
Views for AI Services.
"""
from django.http import JsonResponse
from rest_framework import generics, permissions, status, views, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import (
    AIModel, AIServiceLog, ImageAnalysisResult, TextAnalysisResult,
    PriorityScoringResult, RoutingSuggestion, TranslationRequest,
    VoiceRecognitionResult, AITrainingData
)
from .serializers import (
    AIModelSerializer, AIServiceLogSerializer,
    ImageAnalysisResultSerializer, TextAnalysisResultSerializer,
    PriorityScoringResultSerializer, RoutingSuggestionSerializer,
    TranslationRequestSerializer, VoiceRecognitionResultSerializer,
    AITrainingDataSerializer
)
from apps.complaints.models import Complaint, ComplaintProof
from apps.users.permissions import IsAdmin, IsReviewer
from .tasks import (
    verify_complaint_proofs, score_complaint_priority, route_complaint
)


class AIModelViewSet(viewsets.ModelViewSet):
    """CRUD operations for AI Models."""
    queryset = AIModel.objects.all()
    serializer_class = AIModelSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]
        return super().get_permissions()


class AIServiceLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only operations for AI Service Logs."""
    queryset = AIServiceLog.objects.all()
    serializer_class = AIServiceLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_admin or user.is_superuser:
            return self.queryset
        return self.queryset.filter(triggered_by=user)


class ImageAnalysisResultViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only operations for Image Analysis Results."""
    queryset = ImageAnalysisResult.objects.all()
    serializer_class = ImageAnalysisResultSerializer
    permission_classes = [permissions.IsAuthenticated]


class TextAnalysisResultViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only operations for Text Analysis Results."""
    queryset = TextAnalysisResult.objects.all()
    serializer_class = TextAnalysisResultSerializer
    permission_classes = [permissions.IsAuthenticated]


class PriorityScoringResultViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only operations for Priority Scoring Results."""
    queryset = PriorityScoringResult.objects.all()
    serializer_class = PriorityScoringResultSerializer
    permission_classes = [permissions.IsAuthenticated]


class RoutingSuggestionViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only operations for Routing Suggestions."""
    queryset = RoutingSuggestion.objects.all()
    serializer_class = RoutingSuggestionSerializer
    permission_classes = [permissions.IsAuthenticated]


class TranslationRequestViewSet(viewsets.ModelViewSet):
    """CRUD operations for Translation Requests."""
    queryset = TranslationRequest.objects.all()
    serializer_class = TranslationRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        # Set user from request
        serializer.save(triggered_by=self.request.user)


class VoiceRecognitionResultViewSet(viewsets.ModelViewSet):
    """CRUD operations for Voice Recognition Results."""
    queryset = VoiceRecognitionResult.objects.all()
    serializer_class = VoiceRecognitionResultSerializer
    permission_classes = [permissions.IsAuthenticated]


class AITrainingDataViewSet(viewsets.ModelViewSet):
    """CRUD operations for AI Training Data."""
    queryset = AITrainingData.objects.all()
    serializer_class = AITrainingDataSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]
        return super().get_permissions()


class VerifyComplaintView(views.APIView):
    """Trigger AI verification for a complaint."""
    permission_classes = [permissions.IsAuthenticated, IsReviewer]
    
    def post(self, request, pk=None):
        complaint = generics.get_object_or_404(Complaint, pk=pk)
        
        # Trigger verification task
        task = verify_complaint_proofs.delay(complaint.id)
        
        return Response({
            'message': 'Verification task started.',
            'task_id': task.id
        }, status=status.HTTP_202_ACCEPTED)


class ScorePriorityView(views.APIView):
    """Trigger priority scoring for a complaint."""
    permission_classes = [permissions.IsAuthenticated, IsReviewer]
    
    def post(self, request, pk=None):
        complaint = generics.get_object_or_404(Complaint, pk=pk)
        
        # Trigger scoring task
        task = score_complaint_priority.delay(complaint.id)
        
        return Response({
            'message': 'Priority scoring task started.',
            'task_id': task.id
        }, status=status.HTTP_202_ACCEPTED)


class RouteComplaintView(views.APIView):
    """Trigger routing for a complaint."""
    permission_classes = [permissions.IsAuthenticated, IsReviewer]
    
    def post(self, request, pk=None):
        complaint = generics.get_object_or_404(Complaint, pk=pk)
        
        # Trigger routing task
        task = route_complaint.delay(complaint.id)
        
        return Response({
            'message': 'Routing task started.',
            'task_id': task.id
        }, status=status.HTTP_202_ACCEPTED)


class ProcessAllComplaintsView(views.APIView):
    """Process all pending complaints through AI pipeline."""
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    
    def post(self, request):
        # Get all complaints that need processing
        complaints = Complaint.objects.filter(
            status__in=['SUBMITTED', 'PROOF_RECEIVED']
        )
        
        # Trigger tasks for each complaint
        task_ids = []
        for complaint in complaints:
            # Verify proofs
            verify_task = verify_complaint_proofs.delay(complaint.id)
            task_ids.append(verify_task.id)
            
            # Score priority
            score_task = score_complaint_priority.delay(complaint.id)
            task_ids.append(score_task.id)
        
        return Response({
            'message': f'Processing {complaints.count()} complaints.',
            'task_ids': task_ids
        }, status=status.HTTP_202_ACCEPTED)


class AnalyzeImageView(views.APIView):
    """Analyze an image proof."""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, pk=None):
        proof = generics.get_object_or_404(ComplaintProof, pk=pk)
        
        # Trigger image analysis
        from .tasks import analyze_image
        result = analyze_image(proof)
        
        # Save result
        ImageAnalysisResult.objects.update_or_create(
            proof=proof,
            defaults={
                'analysis_complete': True,
                'image_width': result.get('width', 0),
                'image_height': result.get('height', 0),
                'image_format': result.get('format', ''),
                'camera_make': result.get('camera_make', ''),
                'camera_model': result.get('camera_model', ''),
                'capture_timestamp': result.get('capture_timestamp'),
                'gps_latitude': result.get('gps_latitude'),
                'gps_longitude': result.get('gps_longitude'),
                'gps_accuracy': result.get('gps_accuracy'),
                'quality_score': result.get('quality_score', 0),
                'blur_score': result.get('blur_score', 0),
                'brightness_score': result.get('brightness_score', 0),
                'contrast_score': result.get('contrast_score', 0),
                'manipulation_detected': result.get('manipulation_detected', False),
                'manipulation_confidence': result.get('manipulation_confidence', 0),
                'manipulation_type': result.get('manipulation_type', ''),
                'relevance_score': result.get('relevance_score', 0),
                'relevance_keywords': result.get('relevance_keywords', []),
                'authenticity_score': result.get('authenticity_score', 0),
                'authenticity_notes': result.get('notes', ''),
            }
        )
        
        return Response({
            'message': 'Image analysis completed.',
            'result': result
        }, status=status.HTTP_200_OK)


class TranslateTextView(views.APIView):
    """Translate text."""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = TranslationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Perform translation (simplified)
        text = serializer.validated_data['original_text']
        target_language = serializer.validated_data['target_language']
        
        # In production, use a translation API
        # For now, just return the original text
        translated_text = f"[Translated to {target_language}]: {text}"
        
        # Save translation request
        translation_request = serializer.save(
            translated_text=translated_text,
            status='COMPLETED'
        )
        
        return Response({
            'original_text': text,
            'translated_text': translated_text,
            'source_language': serializer.validated_data['source_language'],
            'target_language': target_language
        }, status=status.HTTP_200_OK)


class RecognizeVoiceView(views.APIView):
    """Recognize voice."""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        audio_file = request.FILES.get('audio')
        if not audio_file:
            return Response({'error': 'No audio file provided.'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Save the audio file
        voice_result = VoiceRecognitionResult.objects.create(
            audio_file=audio_file,
            recognized_text='',
            detected_language='en',
            language_confidence=0
        )
        
        # In production, use a speech recognition API
        # For now, just return a placeholder
        recognized_text = f"[Recognized text from {audio_file.name}]"
        voice_result.recognized_text = recognized_text
        voice_result.save()
        
        return Response({
            'recognized_text': recognized_text,
            'language': 'en',
            'confidence': 0.8
        }, status=status.HTTP_200_OK)
