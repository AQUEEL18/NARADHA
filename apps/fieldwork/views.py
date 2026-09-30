"""
Views for Fieldwork app.
"""
from django.db.models import Q, Count, Avg
from rest_framework import generics, permissions, status, views, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import (
    FieldTask, FieldTaskHistory, FieldWorkerLocation, FieldWorkerPerformance,
    FieldTaskChecklist, FieldTaskChecklistTemplate
)
from .serializers import (
    FieldTaskSerializer, FieldTaskHistorySerializer,
    FieldWorkerLocationSerializer, FieldWorkerPerformanceSerializer,
    FieldTaskChecklistSerializer, FieldTaskChecklistTemplateSerializer
)
from apps.complaints.models import Complaint
from apps.users.models import CustomUser
from apps.users.permissions import IsFieldWorker, IsOfficial


class FieldTaskViewSet(viewsets.ModelViewSet):
    """CRUD operations for Field Tasks."""
    queryset = FieldTask.objects.all()
    serializer_class = FieldTaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        if user.is_admin or user.is_superuser:
            return self.queryset
        elif user.is_official():
            # Officials can see tasks for their complaints
            complaints = Complaint.objects.filter(assigned_official=user)
            return self.queryset.filter(complaint__in=complaints)
        elif user.is_field_worker():
            return self.queryset.filter(assigned_to=user)
        else:
            return self.queryset.none()
    
    def perform_create(self, serializer):
        user = self.request.user
        
        # Check permissions
        if not (user.is_admin or user.is_superuser or user.is_official()):
            raise permissions.PermissionDenied("Only admins and officials can create tasks.")
        
        # Set assigned_by
        serializer.save(assigned_by=user)
    
    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """Assign task to field worker."""
        task = self.get_object()
        user = request.user
        
        # Check permissions
        if not (user.is_admin or user.is_superuser or user.is_official()):
            return Response({'error': 'Only admins and officials can assign tasks.'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        worker_id = request.data.get('worker_id')
        if not worker_id:
            return Response({'error': 'worker_id is required.'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        try:
            worker = CustomUser.objects.get(id=worker_id, role='FIELD_WORKER')
        except CustomUser.DoesNotExist:
            return Response({'error': 'Field worker not found.'}, 
                          status=status.HTTP_404_NOT_FOUND)
        
        # Update task
        task.assigned_to = worker
        task.status = 'ASSIGNED'
        task.save()
        
        # Create history record
        FieldTaskHistory.objects.create(
            task=task,
            previous_status='PENDING',
            new_status='ASSIGNED',
            changed_by=user,
            notes=f'Assigned to {worker.get_short_name()}'
        )
        
        return Response({
            'message': 'Task assigned successfully.',
            'task': FieldTaskSerializer(task).data
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start working on task."""
        task = self.get_object()
        user = request.user
        
        # Check permissions
        if task.assigned_to != user:
            return Response({'error': 'You can only start tasks assigned to you.'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        # Update task
        task.status = 'IN_PROGRESS'
        task.started_at = timezone.now()
        task.save()
        
        # Create history record
        FieldTaskHistory.objects.create(
            task=task,
            previous_status='ASSIGNED',
            new_status='IN_PROGRESS',
            changed_by=user,
            notes='Task started'
        )
        
        return Response({
            'message': 'Task started successfully.',
            'task': FieldTaskSerializer(task).data
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def on_site(self, request, pk=None):
        """Mark task as on site."""
        task = self.get_object()
        user = request.user
        
        # Check permissions
        if task.assigned_to != user:
            return Response({'error': 'You can only update tasks assigned to you.'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        # Get GPS coordinates
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        
        if not latitude or not longitude:
            return Response({'error': 'latitude and longitude are required.'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Update task
        task.status = 'ON_SITE'
        task.latitude = latitude
        task.longitude = longitude
        task.save()
        
        # Record location
        FieldWorkerLocation.objects.create(
            worker=user,
            latitude=latitude,
            longitude=longitude,
            accuracy=request.data.get('accuracy', 0),
            current_task=task,
            device_id=request.data.get('device_id', '')
        )
        
        # Create history record
        FieldTaskHistory.objects.create(
            task=task,
            previous_status='IN_PROGRESS',
            new_status='ON_SITE',
            changed_by=user,
            latitude=latitude,
            longitude=longitude,
            notes='Worker arrived on site'
        )
        
        return Response({
            'message': 'On site status updated.',
            'task': FieldTaskSerializer(task).data
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark task as completed."""
        task = self.get_object()
        user = request.user
        
        # Check permissions
        if task.assigned_to != user:
            return Response({'error': 'You can only complete tasks assigned to you.'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        # Get completion details
        completion_notes = request.data.get('completion_notes', '')
        after_photo = request.FILES.get('after_photo')
        
        # Update task
        task.status = 'COMPLETED'
        task.completion_notes = completion_notes
        task.completion_date = timezone.now()
        
        if after_photo:
            task.after_photo = after_photo
        
        task.save()
        
        # Update complaint status
        complaint = task.complaint
        complaint.status = 'FIELD_WORK_COMPLETED'
        complaint.save()
        
        # Create history record
        FieldTaskHistory.objects.create(
            task=task,
            previous_status='ON_SITE',
            new_status='COMPLETED',
            changed_by=user,
            notes=f'Task completed: {completion_notes}'
        )
        
        return Response({
            'message': 'Task completed successfully.',
            'task': FieldTaskSerializer(task).data
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def upload_before_photo(self, request, pk=None):
        """Upload before photo."""
        task = self.get_object()
        user = request.user
        
        # Check permissions
        if task.assigned_to != user:
            return Response({'error': 'You can only upload photos for tasks assigned to you.'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        before_photo = request.FILES.get('before_photo')
        if not before_photo:
            return Response({'error': 'before_photo is required.'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        task.before_photo = before_photo
        task.save()
        
        return Response({
            'message': 'Before photo uploaded.',
            'task': FieldTaskSerializer(task).data
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def upload_after_photo(self, request, pk=None):
        """Upload after photo."""
        task = self.get_object()
        user = request.user
        
        # Check permissions
        if task.assigned_to != user:
            return Response({'error': 'You can only upload photos for tasks assigned to you.'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        after_photo = request.FILES.get('after_photo')
        if not after_photo:
            return Response({'error': 'after_photo is required.'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        task.after_photo = after_photo
        task.save()
        
        return Response({
            'message': 'After photo uploaded.',
            'task': FieldTaskSerializer(task).data
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def my_tasks(self, request):
        """Get tasks assigned to current user."""
        user = request.user
        
        if not user.is_field_worker():
            return Response({'error': 'Only field workers can access this.'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        tasks = FieldTask.objects.filter(assigned_to=user).order_by('-created_at')
        
        serializer = self.get_serializer(tasks, many=True)
        return Response(serializer.data)


class FieldTaskHistoryViewSet(viewsets.ModelViewSet):
    """CRUD operations for Field Task History."""
    queryset = FieldTaskHistory.objects.all()
    serializer_class = FieldTaskHistorySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        if user.is_admin or user.is_superuser:
            return self.queryset
        elif user.is_official():
            # Officials can see history for their complaints' tasks
            complaints = Complaint.objects.filter(assigned_official=user)
            tasks = FieldTask.objects.filter(complaint__in=complaints)
            return self.queryset.filter(task__in=tasks)
        elif user.is_field_worker():
            tasks = FieldTask.objects.filter(assigned_to=user)
            return self.queryset.filter(task__in=tasks)
        else:
            return self.queryset.none()


class FieldWorkerLocationViewSet(viewsets.ModelViewSet):
    """CRUD operations for Field Worker Locations."""
    queryset = FieldWorkerLocation.objects.all()
    serializer_class = FieldWorkerLocationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        if user.is_admin or user.is_superuser:
            return self.queryset
        elif user.is_field_worker():
            return self.queryset.filter(worker=user)
        else:
            return self.queryset.none()
    
    def perform_create(self, serializer):
        serializer.save(worker=self.request.user)


class FieldWorkerPerformanceViewSet(viewsets.ModelViewSet):
    """CRUD operations for Field Worker Performance."""
    queryset = FieldWorkerPerformance.objects.all()
    serializer_class = FieldWorkerPerformanceSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        if user.is_admin or user.is_superuser:
            return self.queryset
        elif user.is_field_worker():
            return self.queryset.filter(worker=user)
        else:
            return self.queryset.none()
    
    @action(detail=False, methods=['get'])
    def recalculate(self, request):
        """Recalculate all field worker performance metrics."""
        workers = CustomUser.objects.filter(role='FIELD_WORKER')
        
        for worker in workers:
            # Get tasks for this worker
            tasks = FieldTask.objects.filter(assigned_to=worker)
            
            total_tasks = tasks.count()
            completed_tasks = tasks.filter(status='COMPLETED').count()
            rejected_tasks = tasks.filter(status='REJECTED').count()
            
            # Calculate average completion time
            avg_completion_time = None
            completed_with_dates = tasks.filter(
                status='COMPLETED',
                started_at__isnull=False,
                completion_date__isnull=False
            )
            
            if completed_with_dates.exists():
                total_seconds = sum(
                    (t.completion_date - t.started_at).total_seconds() 
                    for t in completed_with_dates
                )
                avg_completion_time = total_seconds / completed_with_dates.count()
            
            # Calculate total working hours
            total_working_hours = sum(
                t.labor_hours or 0 
                for t in tasks.filter(labor_hours__isnull=False)
            )
            
            # Calculate quality metrics
            quality_ratings = tasks.filter(
                quality_rating__isnull=False
            ).values('quality_rating')
            
            if quality_ratings.exists():
                avg_quality_rating = sum(
                    r['quality_rating'] for r in quality_ratings
                ) / len(quality_ratings)
                quality_rating_count = len(quality_ratings)
            else:
                avg_quality_rating = 0
                quality_rating_count = 0
            
            # Calculate total distance traveled (simplified)
            locations = FieldWorkerLocation.objects.filter(worker=worker)
            total_distance = 0
            prev_location = None
            
            for location in locations.order_by('created_at'):
                if prev_location:
                    # Calculate distance between locations (simplified)
                    # In production, use proper distance calculation
                    distance = ((location.latitude - prev_location.latitude) ** 2 + 
                              (location.longitude - prev_location.longitude) ** 2) ** 0.5
                    total_distance += distance * 111  # Approximate km
                prev_location = location
            
            # Calculate performance score
            performance_score = 0
            if total_tasks > 0:
                completion_rate = (completed_tasks / total_tasks) * 100
                performance_score = (completion_rate * 0.5) + (avg_quality_rating * 20 * 0.3) + 50
            
            # Update or create performance
            FieldWorkerPerformance.objects.update_or_create(
                worker=worker,
                defaults={
                    'total_tasks': total_tasks,
                    'completed_tasks': completed_tasks,
                    'rejected_tasks': rejected_tasks,
                    'avg_completion_time': avg_completion_time,
                    'total_working_hours': total_working_hours,
                    'avg_quality_rating': avg_quality_rating,
                    'quality_rating_count': quality_rating_count,
                    'total_distance_traveled': total_distance,
                    'last_active': timezone.now(),
                    'performance_score': performance_score
                }
            )
        
        return Response({
            'message': 'Field worker performance metrics recalculated.',
            'count': workers.count()
        })


class FieldTaskChecklistViewSet(viewsets.ModelViewSet):
    """CRUD operations for Field Task Checklists."""
    queryset = FieldTaskChecklist.objects.all()
    serializer_class = FieldTaskChecklistSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        if user.is_admin or user.is_superuser:
            return self.queryset
        elif user.is_field_worker():
            tasks = FieldTask.objects.filter(assigned_to=user)
            return self.queryset.filter(task__in=tasks)
        else:
            return self.queryset.none()


class FieldTaskChecklistTemplateViewSet(viewsets.ModelViewSet):
    """CRUD operations for Field Task Checklist Templates."""
    queryset = FieldTaskChecklistTemplate.objects.all()
    serializer_class = FieldTaskChecklistTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]
        return super().get_permissions()


class UpdateLocationView(views.APIView):
    """Update field worker location."""
    permission_classes = [permissions.IsAuthenticated, IsFieldWorker]
    
    def post(self, request):
        user = request.user
        
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        accuracy = request.data.get('accuracy')
        task_id = request.data.get('task_id')
        device_id = request.data.get('device_id', '')
        battery_level = request.data.get('battery_level')
        
        if not latitude or not longitude:
            return Response({'error': 'latitude and longitude are required.'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Get current task
        current_task = None
        if task_id:
            try:
                current_task = FieldTask.objects.get(id=task_id)
            except FieldTask.DoesNotExist:
                pass
        
        # Create location record
        location = FieldWorkerLocation.objects.create(
            worker=user,
            latitude=latitude,
            longitude=longitude,
            accuracy=accuracy,
            current_task=current_task,
            device_id=device_id,
            battery_level=battery_level
        )
        
        # Update user's current location
        user.current_latitude = latitude
        user.current_longitude = longitude
        user.save()
        
        return Response({
            'message': 'Location updated successfully.',
            'location': FieldWorkerLocationSerializer(location).data
        }, status=status.HTTP_201_CREATED)
