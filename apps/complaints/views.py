"""
Views for Complaint management.
"""
from django.utils import timezone
from django.db.models import Q, Count, Avg, Sum, F, FloatField, ExpressionWrapper
from django.db.models.functions import ExtractDay, ExtractMonth, ExtractYear
from rest_framework import generics, permissions, status, views, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from .models import (
    Complaint, ComplaintCategory, ComplaintProof, ComplaintHistory,
    ComplaintEndorsement, ComplaintTag, ComplaintTagAssignment
)
from .serializers import (
    ComplaintMinimalSerializer, ComplaintDetailSerializer,
    ComplaintCreateSerializer, ComplaintUpdateSerializer,
    ComplaintStatusUpdateSerializer, ComplaintVerificationSerializer,
    ComplaintEndorsementSerializer, ComplaintEndorsementCreateSerializer,
    ComplaintCategorySerializer, ComplaintSearchSerializer,
    ComplaintAnalyticsSerializer, ComplaintProofSerializer
)
from apps.users.models import CustomUser
from apps.users.permissions import IsCitizen, IsOfficial, IsReviewer, IsFieldWorker
from apps.routing.models import RoutingLog
from apps.verification.models import VerificationResult
from apps.ai_services.tasks import verify_complaint_proofs, score_complaint_priority


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class ComplaintCategoryViewSet(viewsets.ModelViewSet):
    """CRUD operations for Complaint Categories."""
    queryset = ComplaintCategory.objects.filter(is_active=True)
    serializer_class = ComplaintCategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]
        return super().get_permissions()


class ComplaintProofViewSet(viewsets.ModelViewSet):
    """CRUD operations for Complaint Proofs."""
    queryset = ComplaintProof.objects.all()
    serializer_class = ComplaintProofSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_admin or user.is_superuser:
            return self.queryset
        elif user.is_official():
            return self.queryset.filter(complaint__assigned_official=user)
        elif user.is_field_worker():
            return self.queryset.filter(complaint__assigned_field_worker=user)
        else:
            return self.queryset.filter(complaint__citizen=user)
    
    def perform_create(self, serializer):
        complaint = serializer.validated_data.get('complaint')
        if not complaint:
            # Get complaint from URL or context
            complaint_id = self.kwargs.get('complaint_pk')
            if complaint_id:
                complaint = Complaint.objects.get(pk=complaint_id)
        
        # Verify proof is owned by user
        if complaint.citizen != self.request.user:
            raise permissions.PermissionDenied("You can only add proofs to your own complaints.")
        
        serializer.save()


class ComplaintViewSet(viewsets.ModelViewSet):
    """CRUD operations for Complaints."""
    queryset = Complaint.objects.filter(is_deleted=False)
    pagination_class = StandardResultsSetPagination
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ComplaintCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ComplaintUpdateSerializer
        elif self.action == 'verify':
            return ComplaintVerificationSerializer
        elif self.action in ['list', 'retrieve']:
            if self.request.query_params.get('minimal') == 'true':
                return ComplaintMinimalSerializer
            return ComplaintDetailSerializer
        return ComplaintDetailSerializer
    
    def get_permissions(self):
        if self.action == 'create':
            return [permissions.IsAuthenticated(), IsCitizen()]
        elif self.action == 'verify':
            return [permissions.IsAuthenticated(), IsReviewer()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticatedOrReadOnly()]
    
    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset
        
        # Filter by user role
        if user.is_authenticated:
            if user.is_citizen():
                # Citizens can see their own complaints and public complaints
                queryset = queryset.filter(
                    Q(citizen=user) | Q(commitment_visible=True)
                ).distinct()
            elif user.is_official():
                # Officials can see complaints assigned to them or in their department
                queryset = queryset.filter(
                    Q(assigned_official=user) | 
                    Q(assigned_department=user.department) |
                    Q(jurisdiction=user.jurisdiction)
                ).distinct()
            elif user.is_field_worker():
                # Field workers can see assigned tasks
                queryset = queryset.filter(assigned_field_worker=user)
            elif user.is_reviewer():
                # Reviewers can see complaints awaiting verification
                queryset = queryset.filter(status__in=['SUBMITTED', 'PROOF_RECEIVED', 'AWAITING_HUMAN_REVIEW'])
        else:
            # Public users can only see public complaints
            queryset = queryset.filter(commitment_visible=True)
        
        # Apply filters from query params
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        priority = self.request.query_params.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)
        
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__code=category)
        
        jurisdiction = self.request.query_params.get('jurisdiction')
        if jurisdiction:
            queryset = queryset.filter(jurisdiction__code=jurisdiction)
        
        department = self.request.query_params.get('department')
        if department:
            queryset = queryset.filter(assigned_department__code=department)
        
        assigned_official = self.request.query_params.get('assigned_official')
        if assigned_official:
            queryset = queryset.filter(assigned_official__phone_number=assigned_official)
        
        # Search
        query = self.request.query_params.get('query')
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) | 
                Q(description__icontains=query) |
                Q(complaint_id__icontains=query) |
                Q(location_address__icontains=query)
            )
        
        # Date range
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)
        
        # Ordering
        ordering = self.request.query_params.get('ordering', '-created_at')
        queryset = queryset.order_by(ordering)
        
        return queryset
    
    def perform_create(self, serializer):
        complaint = serializer.save()
        
        # Trigger AI verification
        if complaint.proofs.exists():
            verify_complaint_proofs.delay(complaint.id)
        
        # Score priority
        score_complaint_priority.delay(complaint.id)
        
        # Create history record
        ComplaintHistory.objects.create(
            complaint=complaint,
            previous_status=None,
            new_status=complaint.status,
            changed_by=self.request.user,
            notes='Complaint created'
        )
    
    def perform_update(self, serializer):
        complaint = self.get_object()
        old_status = complaint.status
        
        super().perform_update(serializer)
        
        # Update history if status changed
        new_status = serializer.validated_data.get('status', old_status)
        if old_status != new_status:
            ComplaintHistory.objects.create(
                complaint=complaint,
                previous_status=old_status,
                new_status=new_status,
                changed_by=self.request.user,
                notes=f'Status updated via API'
            )
    
    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Verify a complaint (for reviewers)."""
        complaint = self.get_object()
        serializer = self.get_serializer(complaint, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        # Update verification result
        VerificationResult.objects.update_or_create(
            complaint=complaint,
            defaults={
                'ai_verification_passed': serializer.validated_data.get('ai_verification_status', False),
                'ai_confidence_score': serializer.validated_data.get('ai_confidence_score', 0),
                'human_verification_passed': serializer.validated_data.get('human_verification_status', False),
                'human_reviewer': request.user,
                'human_verification_notes': serializer.validated_data.get('human_verification_notes', ''),
                'human_verified_at': timezone.now()
            }
        )
        
        # Update complaint status based on verification
        if serializer.validated_data.get('human_verification_status'):
            complaint.status = 'VERIFIED'
            complaint.save()
            
            # Create history record
            ComplaintHistory.objects.create(
                complaint=complaint,
                previous_status='AWAITING_HUMAN_REVIEW',
                new_status='VERIFIED',
                changed_by=request.user,
                notes='Complaint verified by human reviewer'
            )
        
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """Assign complaint to official."""
        complaint = self.get_object()
        user = request.user
        
        # Check permissions
        if not (user.is_admin or user.is_superuser or user.is_official()):
            return Response({'error': 'You do not have permission to assign complaints.'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        official_id = request.data.get('official_id')
        department_id = request.data.get('department_id')
        
        if not official_id:
            return Response({'error': 'official_id is required.'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        try:
            official = CustomUser.objects.get(id=official_id, role='OFFICIAL')
        except CustomUser.DoesNotExist:
            return Response({'error': 'Official not found.'}, 
                          status=status.HTTP_404_NOT_FOUND)
        
        # Update complaint
        complaint.assigned_official = official
        if department_id:
            try:
                department = Department.objects.get(id=department_id)
                complaint.assigned_department = department
            except Department.DoesNotExist:
                pass
        
        complaint.status = 'NOTIFIED_TO_OFFICIAL'
        complaint.save()
        
        # Create history record
        ComplaintHistory.objects.create(
            complaint=complaint,
            previous_status='VERIFIED',
            new_status='NOTIFIED_TO_OFFICIAL',
            changed_by=request.user,
            notes=f'Assigned to {official.get_short_name()}'
        )
        
        # Log routing
        RoutingLog.objects.create(
            complaint=complaint,
            previous_official=None,
            new_official=official,
            new_department=complaint.assigned_department,
            routing_method='MANUAL',
            routing_reason=f'Manually assigned by {user.get_short_name()}'
        )
        
        return Response({
            'message': 'Complaint assigned successfully.',
            'complaint': ComplaintDetailSerializer(complaint).data
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def commit(self, request, pk=None):
        """Official commits to resolve complaint."""
        complaint = self.get_object()
        user = request.user
        
        # Check permissions
        if complaint.assigned_official != user:
            return Response({'error': 'You can only commit to complaints assigned to you.'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        commitment_date = request.data.get('commitment_date')
        if not commitment_date:
            return Response({'error': 'commitment_date is required.'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        try:
            commitment_date = timezone.datetime.fromisoformat(commitment_date)
        except ValueError:
            return Response({'error': 'Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SS).'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Update complaint
        complaint.commitment_date = commitment_date
        complaint.commitment_visible = True
        complaint.status = 'COMMITMENT_PUBLISHED'
        complaint.sla_deadline = commitment_date
        complaint.save()
        
        # Create history record
        ComplaintHistory.objects.create(
            complaint=complaint,
            previous_status='NOTIFIED_TO_OFFICIAL',
            new_status='COMMITMENT_PUBLISHED',
            changed_by=user,
            notes=f'Official committed to resolve by {commitment_date}'
        )
        
        return Response({
            'message': 'Commitment published successfully.',
            'complaint': ComplaintDetailSerializer(complaint).data
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def endorse(self, request, pk=None):
        """Endorse a complaint."""
        complaint = self.get_object()
        user = request.user
        
        # Check if user is citizen
        if not user.is_citizen():
            return Response({'error': 'Only citizens can endorse complaints.'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        # Check if already endorsed
        if ComplaintEndorsement.objects.filter(citizen=user, complaint=complaint).exists():
            return Response({'error': 'You have already endorsed this complaint.'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        serializer = ComplaintEndorsementCreateSerializer(
            data={'complaint': complaint.id, **request.data},
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        endorsement = serializer.save()
        
        # Update complaint priority based on endorsements
        endorsement_count = ComplaintEndorsement.objects.filter(complaint=complaint).count()
        if endorsement_count >= 5:
            # Increase priority if many endorsements
            complaint.priority_score = min(10, complaint.priority_score + 1)
            complaint.save()
        
        return Response({
            'message': 'Complaint endorsed successfully.',
            'endorsement': ComplaintEndorsementSerializer(endorsement).data
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def rate(self, request, pk=None):
        """Rate the resolution of a complaint."""
        complaint = self.get_object()
        user = request.user
        
        # Check if user is the citizen who filed the complaint
        if complaint.citizen != user:
            return Response({'error': 'You can only rate complaints you filed.'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        # Check if complaint is resolved
        if complaint.status != 'AWAITING_CITIZEN_VERIFICATION':
            return Response({'error': 'This complaint is not ready for rating.'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        rating = request.data.get('rating')
        comments = request.data.get('comments', '')
        
        if not rating or int(rating) < 1 or int(rating) > 5:
            return Response({'error': 'Rating must be between 1 and 5.'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Update complaint
        complaint.citizen_ratings = int(rating)
        complaint.citizen_comments = comments
        complaint.citizen_verified = True
        complaint.citizen_verification_date = timezone.now()
        complaint.status = 'RESOLVED'
        complaint.resolution_date = timezone.now()
        complaint.save()
        
        # Create history record
        ComplaintHistory.objects.create(
            complaint=complaint,
            previous_status='AWAITING_CITIZEN_VERIFICATION',
            new_status='RESOLVED',
            changed_by=user,
            notes=f'Citizen rated {rating}/5: {comments}'
        )
        
        return Response({
            'message': 'Complaint rated successfully.',
            'complaint': ComplaintDetailSerializer(complaint).data
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def reopen(self, request, pk=None):
        """Reopen a resolved complaint."""
        complaint = self.get_object()
        user = request.user
        
        # Check if user is the citizen who filed the complaint
        if complaint.citizen != user:
            return Response({'error': 'You can only reopen complaints you filed.'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        # Check if complaint is resolved
        if complaint.status != 'RESOLVED':
            return Response({'error': 'This complaint is not resolved.'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Reopen complaint
        complaint.status = 'REOPENED'
        complaint.citizen_verified = False
        complaint.citizen_ratings = None
        complaint.citizen_comments = ''
        complaint.resolution_date = None
        complaint.save()
        
        # Create history record
        ComplaintHistory.objects.create(
            complaint=complaint,
            previous_status='RESOLVED',
            new_status='REOPENED',
            changed_by=user,
            notes='Complaint reopened by citizen'
        )
        
        return Response({
            'message': 'Complaint reopened successfully.',
            'complaint': ComplaintDetailSerializer(complaint).data
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def my_complaints(self, request):
        """Get complaints filed by current user."""
        user = request.user
        if not user.is_authenticated:
            return Response({'error': 'Authentication required.'}, 
                          status=status.HTTP_401_UNAUTHORIZED)
        
        complaints = Complaint.objects.filter(citizen=user).order_by('-created_at')
        
        page = self.paginate_queryset(complaints)
        if page is not None:
            serializer = ComplaintDetailSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = ComplaintDetailSerializer(complaints, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def assigned_to_me(self, request):
        """Get complaints assigned to current user."""
        user = request.user
        if not user.is_authenticated:
            return Response({'error': 'Authentication required.'}, 
                          status=status.HTTP_401_UNAUTHORIZED)
        
        complaints = Complaint.objects.filter(assigned_official=user).order_by('-created_at')
        
        page = self.paginate_queryset(complaints)
        if page is not None:
            serializer = ComplaintDetailSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = ComplaintDetailSerializer(complaints, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def for_verification(self, request):
        """Get complaints awaiting verification."""
        user = request.user
        if not user.is_authenticated or user.role != 'REVIEWER':
            return Response({'error': 'Only reviewers can access this.'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        complaints = Complaint.objects.filter(
            status__in=['SUBMITTED', 'PROOF_RECEIVED', 'AWAITING_HUMAN_REVIEW']
        ).order_by('-created_at')
        
        page = self.paginate_queryset(complaints)
        if page is not None:
            serializer = ComplaintDetailSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = ComplaintDetailSerializer(complaints, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def nearby(self, request):
        """Get complaints nearby current user."""
        user = request.user
        if not user.is_authenticated:
            return Response({'error': 'Authentication required.'}, 
                          status=status.HTTP_401_UNAUTHORIZED)
        
        latitude = request.query_params.get('latitude')
        longitude = request.query_params.get('longitude')
        radius = request.query_params.get('radius', 5)  # Default 5km
        
        if not latitude or not longitude:
            return Response({'error': 'latitude and longitude parameters are required.'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        try:
            lat = float(latitude)
            lon = float(longitude)
            radius = float(radius)
        except ValueError:
            return Response({'error': 'Invalid latitude, longitude, or radius values.'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # This is a simplified version - in production, use proper geographic queries
        # For now, we'll use a simple distance calculation
        from django.db.models.functions import Power, Sqrt, Radians
        from django.db.models import F, FloatField, ExpressionWrapper
        
        # Haversine formula would be better, but for simplicity:
        # Approximate distance calculation (not accurate for large distances)
        complaints = Complaint.objects.annotate(
            lat_diff=ExpressionWrapper(
                F('latitude') - lat,
                output_field=FloatField()
            ),
            lon_diff=ExpressionWrapper(
                F('longitude') - lon,
                output_field=FloatField()
            ),
            distance=ExpressionWrapper(
                Sqrt(Power('lat_diff', 2) + Power('lon_diff', 2)) * 111,
                output_field=FloatField()  # Approximate km
            )
        ).filter(
            distance__lte=radius,
            commitment_visible=True
        ).order_by('distance')
        
        page = self.paginate_queryset(complaints)
        if page is not None:
            serializer = ComplaintDetailSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = ComplaintDetailSerializer(complaints, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def analytics(self, request):
        """Get complaint analytics."""
        user = request.user
        
        # Filter complaints based on user role
        if user.is_authenticated:
            if user.is_admin or user.is_superuser:
                complaints = Complaint.objects.filter(is_deleted=False)
            elif user.is_official():
                complaints = Complaint.objects.filter(
                    Q(assigned_official=user) | 
                    Q(assigned_department=user.department) |
                    Q(jurisdiction=user.jurisdiction)
                )
            else:
                complaints = Complaint.objects.filter(citizen=user)
        else:
            complaints = Complaint.objects.filter(commitment_visible=True)
        
        # Calculate analytics
        total_complaints = complaints.count()
        resolved_complaints = complaints.filter(status='RESOLVED').count()
        pending_complaints = complaints.exclude(status__in=['RESOLVED', 'REJECTED']).count()
        rejected_complaints = complaints.filter(status='REJECTED').count()
        
        # Resolution rate
        resolution_rate = (resolved_complaints / total_complaints * 100) if total_complaints > 0 else 0
        
        # Average resolution time
        resolved_with_dates = complaints.filter(
            status='RESOLVED',
            submitted_at__isnull=False,
            resolution_date__isnull=False
        )
        avg_resolution_time = resolved_with_dates.aggregate(
            avg_time=Avg('resolution_date') - Avg('submitted_at')
        ).get('avg_time')
        
        # Priority distribution
        priority_distribution = complaints.values('priority').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Category distribution
        category_distribution = complaints.values('category__name').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Status distribution
        status_distribution = complaints.values('status').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Time series data (last 30 days)
        from django.db.models.functions import TruncDate
        time_series = complaints.annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')
        
        # Citizen satisfaction
        avg_rating = complaints.filter(
            citizen_ratings__isnull=False
        ).aggregate(
            avg_rating=Avg('citizen_ratings')
        ).get('avg_rating') or 0
        
        # SLA compliance
        sla_compliant = complaints.filter(
            sla_breached=False,
            status='RESOLVED'
        ).count()
        sla_total = complaints.filter(status='RESOLVED').count()
        sla_compliance_rate = (sla_compliant / sla_total * 100) if sla_total > 0 else 0
        
        return Response({
            'total_complaints': total_complaints,
            'resolved_complaints': resolved_complaints,
            'pending_complaints': pending_complaints,
            'rejected_complaints': rejected_complaints,
            'resolution_rate': round(resolution_rate, 2),
            'avg_resolution_time': str(avg_resolution_time) if avg_resolution_time else None,
            'priority_distribution': list(priority_distribution),
            'category_distribution': list(category_distribution),
            'status_distribution': list(status_distribution),
            'time_series': list(time_series),
            'avg_citizen_rating': round(avg_rating, 2),
            'sla_compliance_rate': round(sla_compliance_rate, 2),
        })


class ComplaintSearchView(views.APIView):
    """Search complaints."""
    
    def get(self, request):
        serializer = ComplaintSearchSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        queryset = Complaint.objects.filter(is_deleted=False, commitment_visible=True)
        
        # Apply filters
        if data.get('query'):
            queryset = queryset.filter(
                Q(title__icontains=data['query']) | 
                Q(description__icontains=data['query']) |
                Q(complaint_id__icontains=data['query']) |
                Q(location_address__icontains=data['query'])
            )
        
        if data.get('category'):
            queryset = queryset.filter(category__code=data['category'])
        
        if data.get('status'):
            queryset = queryset.filter(status=data['status'])
        
        if data.get('priority'):
            queryset = queryset.filter(priority=data['priority'])
        
        if data.get('jurisdiction'):
            queryset = queryset.filter(jurisdiction__code=data['jurisdiction'])
        
        if data.get('department'):
            queryset = queryset.filter(assigned_department__code=data['department'])
        
        if data.get('assigned_official'):
            queryset = queryset.filter(assigned_official__phone_number=data['assigned_official'])
        
        if data.get('citizen'):
            queryset = queryset.filter(citizen__phone_number=data['citizen'])
        
        # Date range
        if data.get('date_from'):
            queryset = queryset.filter(created_at__gte=data['date_from'])
        if data.get('date_to'):
            queryset = queryset.filter(created_at__lte=data['date_to'])
        
        # Location-based search
        if data.get('latitude') and data.get('longitude') and data.get('radius'):
            lat = data['latitude']
            lon = data['longitude']
            radius = data['radius']
            
            # Simple distance approximation
            from django.db.models.functions import Power, Sqrt
            from django.db.models import F, FloatField, ExpressionWrapper
            
            queryset = queryset.annotate(
                lat_diff=ExpressionWrapper(F('latitude') - lat, output_field=FloatField()),
                lon_diff=ExpressionWrapper(F('longitude') - lon, output_field=FloatField()),
                distance=ExpressionWrapper(
                    Sqrt(Power('lat_diff', 2) + Power('lon_diff', 2)) * 111,
                    output_field=FloatField()
                )
            ).filter(distance__lte=radius)
        
        # Ordering
        ordering = data.get('ordering', '-created_at')
        queryset = queryset.order_by(ordering)
        
        # Pagination
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(queryset, request)
        
        serializer = ComplaintDetailSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)
