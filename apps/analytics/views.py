"""
Views for Analytics app.
"""
from django.db.models import Q, Count, Avg, Sum, F, FloatField, ExpressionWrapper
from django.db.models.functions import TruncDate, ExtractDay, ExtractMonth, ExtractYear
from rest_framework import generics, permissions, status, views, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import (
    DepartmentPerformance, OfficialPerformance, IssuePattern, HeatmapData
)
from .serializers import (
    DepartmentPerformanceSerializer, OfficialPerformanceSerializer,
    IssuePatternSerializer, HeatmapDataSerializer
)
from apps.complaints.models import Complaint
from apps.users.models import Department, Jurisdiction


class AnalyticsView(views.APIView):
    """Comprehensive analytics endpoint."""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Time range filter
        time_range = request.query_params.get('time_range', 'LAST_30_DAYS')
        group_by = request.query_params.get('group_by', 'day')
        
        # Calculate date range
        from django.utils import timezone
        from datetime import timedelta
        
        end_date = timezone.now()
        if time_range == 'LAST_7_DAYS':
            start_date = end_date - timedelta(days=7)
        elif time_range == 'LAST_90_DAYS':
            start_date = end_date - timedelta(days=90)
        elif time_range == 'LAST_YEAR':
            start_date = end_date - timedelta(days=365)
        else:  # LAST_30_DAYS
            start_date = end_date - timedelta(days=30)
        
        # Filter complaints based on user role
        if user.is_admin or user.is_superuser:
            complaints = Complaint.objects.filter(created_at__range=[start_date, end_date])
        elif user.is_official():
            complaints = Complaint.objects.filter(
                Q(assigned_official=user) | 
                Q(assigned_department=user.department) |
                Q(jurisdiction=user.jurisdiction),
                created_at__range=[start_date, end_date]
            )
        elif user.is_field_worker():
            complaints = Complaint.objects.filter(
                assigned_field_worker=user,
                created_at__range=[start_date, end_date]
            )
        else:
            complaints = Complaint.objects.filter(
                citizen=user,
                created_at__range=[start_date, end_date]
            )
        
        # Get statistics
        total_complaints = complaints.count()
        resolved_complaints = complaints.filter(status='RESOLVED').count()
        pending_complaints = complaints.exclude(status__in=['RESOLVED', 'REJECTED']).count()
        
        resolution_rate = (resolved_complaints / total_complaints * 100) if total_complaints > 0 else 0
        
        # Time series data
        time_series = []
        
        if group_by == 'day':
            for day in range((end_date - start_date).days + 1):
                current_date = start_date + timedelta(days=day)
                count = complaints.filter(
                    created_at__date=current_date.date()
                ).count()
                resolved = complaints.filter(
                    status='RESOLVED',
                    resolution_date__date=current_date.date()
                ).count()
                time_series.append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'count': count,
                    'resolved': resolved
                })
        elif group_by == 'week':
            # Group by week
            current_date = start_date
            while current_date <= end_date:
                next_date = current_date + timedelta(days=7)
                count = complaints.filter(
                    created_at__range=[current_date, next_date]
                ).count()
                resolved = complaints.filter(
                    status='RESOLVED',
                    resolution_date__range=[current_date, next_date]
                ).count()
                time_series.append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'end_date': next_date.strftime('%Y-%m-%d'),
                    'count': count,
                    'resolved': resolved
                })
                current_date = next_date
        elif group_by == 'month':
            # Group by month
            current_date = start_date
            while current_date <= end_date:
                # Get first day of next month
                if current_date.month == 12:
                    next_date = current_date.replace(year=current_date.year + 1, month=1, day=1)
                else:
                    next_date = current_date.replace(month=current_date.month + 1, day=1)
                
                count = complaints.filter(
                    created_at__range=[current_date, next_date]
                ).count()
                resolved = complaints.filter(
                    status='RESOLVED',
                    resolution_date__range=[current_date, next_date]
                ).count()
                time_series.append({
                    'date': current_date.strftime('%Y-%m'),
                    'count': count,
                    'resolved': resolved
                })
                current_date = next_date
        
        # Category distribution
        category_distribution = []
        for category in complaints.values('category__name').annotate(count=Count('id')):
            if category['category__name']:
                category_distribution.append({
                    'category': category['category__name'],
                    'count': category['count']
                })
        
        category_distribution.sort(key=lambda x: x['count'], reverse=True)
        
        # Priority distribution
        priority_distribution = []
        for priority in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
            count = complaints.filter(priority=priority).count()
            priority_distribution.append({
                'priority': priority,
                'count': count
            })
        
        # Status distribution
        status_distribution = []
        for status in complaints.values('status').annotate(count=Count('id')):
            status_distribution.append({
                'status': status['status'],
                'count': status['count']
            })
        
        status_distribution.sort(key=lambda x: x['count'], reverse=True)
        
        # Department performance (if admin or minister)
        dept_performance = []
        if user.is_admin or user.is_superuser or user.role == 'MINISTER':
            departments = Department.objects.filter(is_active=True)
            for dept in departments:
                dept_complaints = complaints.filter(assigned_department=dept)
                dept_resolved = dept_complaints.filter(status='RESOLVED').count()
                dept_total = dept_complaints.count()
                
                if dept_total > 0:
                    dept_resolution_rate = (dept_resolved / dept_total * 100)
                else:
                    dept_resolution_rate = 0
                
                dept_performance.append({
                    'department': dept.name,
                    'total': dept_total,
                    'resolved': dept_resolved,
                    'resolution_rate': round(dept_resolution_rate, 2)
                })
            
            dept_performance.sort(key=lambda x: x['resolution_rate'], reverse=True)
        
        # Geographic distribution
        geographic_distribution = []
        jurisdictions = Jurisdiction.objects.filter(is_active=True)
        for jurisdiction in jurisdictions:
            count = complaints.filter(jurisdiction=jurisdiction).count()
            if count > 0:
                geographic_distribution.append({
                    'jurisdiction': jurisdiction.name,
                    'count': count
                })
        
        geographic_distribution.sort(key=lambda x: x['count'], reverse=True)
        
        # SLA compliance
        sla_compliant = complaints.filter(sla_breached=False, status='RESOLVED').count()
        sla_total = complaints.filter(status='RESOLVED').count()
        sla_compliance_rate = (sla_compliant / sla_total * 100) if sla_total > 0 else 0
        
        # Citizen satisfaction
        ratings = complaints.filter(citizen_ratings__isnull=False).values('citizen_ratings')
        rating_counts = {}
        for r in ratings:
            rating = r['citizen_ratings']
            rating_counts[rating] = rating_counts.get(rating, 0) + 1
        
        avg_rating = sum(r['citizen_ratings'] for r in ratings) / len(ratings) if ratings else 0
        
        return Response({
            'time_range': time_range,
            'group_by': group_by,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'statistics': {
                'total_complaints': total_complaints,
                'resolved_complaints': resolved_complaints,
                'pending_complaints': pending_complaints,
                'resolution_rate': round(resolution_rate, 2),
                'sla_compliance_rate': round(sla_compliance_rate, 2),
                'avg_citizen_rating': round(avg_rating, 2)
            },
            'time_series': time_series,
            'category_distribution': category_distribution,
            'priority_distribution': priority_distribution,
            'status_distribution': status_distribution,
            'department_performance': dept_performance,
            'geographic_distribution': geographic_distribution,
            'rating_distribution': rating_counts
        })


class DepartmentPerformanceViewSet(viewsets.ModelViewSet):
    """CRUD operations for Department Performance."""
    queryset = DepartmentPerformance.objects.all()
    serializer_class = DepartmentPerformanceSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def recalculate(self, request):
        """Recalculate all department performance metrics."""
        from django.utils import timezone
        from datetime import timedelta
        
        # Get time range from query params
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)
        
        departments = Department.objects.filter(is_active=True)
        
        for dept in departments:
            # Get complaints for this department
            complaints = Complaint.objects.filter(
                assigned_department=dept,
                created_at__gte=start_date
            )
            
            total = complaints.count()
            resolved = complaints.filter(status='RESOLVED').count()
            rejected = complaints.filter(status='REJECTED').count()
            pending = complaints.exclude(status__in=['RESOLVED', 'REJECTED']).count()
            
            # Calculate average resolution time
            avg_resolution_time = None
            resolved_with_dates = complaints.filter(
                status='RESOLVED',
                submitted_at__isnull=False,
                resolution_date__isnull=False
            )
            
            if resolved_with_dates.exists():
                total_days = sum(
                    (c.resolution_date - c.submitted_at).days 
                    for c in resolved_with_dates
                )
                avg_resolution_time = total_days / resolved_with_dates.count()
            
            # Calculate average citizen rating
            avg_rating = complaints.filter(
                citizen_ratings__isnull=False
            ).aggregate(
                avg_rating=Avg('citizen_ratings')
            ).get('avg_rating') or 0
            
            # Calculate average priority score
            avg_priority = complaints.aggregate(
                avg_priority=Avg('priority_score')
            ).get('avg_priority') or 0
            
            # Calculate SLA compliance
            sla_compliant = complaints.filter(sla_breached=False, status='RESOLVED').count()
            sla_total = complaints.filter(status='RESOLVED').count()
            sla_compliance_rate = (sla_compliant / sla_total * 100) if sla_total > 0 else 0
            sla_breach_count = complaints.filter(sla_breached=True).count()
            
            # Calculate performance score
            performance_score = 0
            if total > 0:
                resolution_rate = (resolved / total * 100)
                performance_score = (resolution_rate * 0.5) + (sla_compliance_rate * 0.3) + (avg_rating * 20 * 0.2)
            
            # Update or create department performance
            DepartmentPerformance.objects.update_or_create(
                department=dept,
                defaults={
                    'total_complaints': total,
                    'resolved_complaints': resolved,
                    'rejected_complaints': rejected,
                    'pending_complaints': pending,
                    'avg_resolution_time': avg_resolution_time,
                    'avg_citizen_rating': avg_rating,
                    'avg_priority_score': avg_priority,
                    'sla_compliance_rate': sla_compliance_rate,
                    'sla_breach_count': sla_breach_count,
                    'performance_score': performance_score
                }
            )
        
        # Recalculate ranks
        dept_performances = DepartmentPerformance.objects.all().order_by('-performance_score')
        for rank, performance in enumerate(dept_performances, start=1):
            performance.rank = rank
            performance.save()
        
        return Response({
            'message': 'Department performance metrics recalculated.',
            'count': departments.count()
        })


class OfficialPerformanceViewSet(viewsets.ModelViewSet):
    """CRUD operations for Official Performance."""
    queryset = OfficialPerformance.objects.all()
    serializer_class = OfficialPerformanceSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def recalculate(self, request):
        """Recalculate all official performance metrics."""
        from django.utils import timezone
        from datetime import timedelta
        
        # Get time range from query params
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)
        
        officials = CustomUser.objects.filter(role__in=['OFFICIAL', 'MINISTER'])
        
        for official in officials:
            # Get complaints assigned to this official
            complaints = Complaint.objects.filter(
                assigned_official=official,
                created_at__gte=start_date
            )
            
            total = complaints.count()
            resolved = complaints.filter(status='RESOLVED').count()
            rejected = complaints.filter(status='REJECTED').count()
            pending = complaints.exclude(status__in=['RESOLVED', 'REJECTED']).count()
            overdue = complaints.filter(sla_breached=True).count()
            
            # Calculate average response time (from assignment to first message)
            # This is a simplified version
            avg_response_time = None
            
            # Calculate average resolution time
            avg_resolution_time = None
            resolved_with_dates = complaints.filter(
                status='RESOLVED',
                submitted_at__isnull=False,
                resolution_date__isnull=False
            )
            
            if resolved_with_dates.exists():
                total_days = sum(
                    (c.resolution_date - c.submitted_at).days 
                    for c in resolved_with_dates
                )
                avg_resolution_time = total_days / resolved_with_dates.count()
            
            # Calculate average citizen rating
            avg_rating = complaints.filter(
                citizen_ratings__isnull=False
            ).aggregate(
                avg_rating=Avg('citizen_ratings')
            ).get('avg_rating') or 0
            
            # Calculate average priority score
            avg_priority = complaints.aggregate(
                avg_priority=Avg('priority_score')
            ).get('avg_priority') or 0
            
            # Calculate SLA compliance
            sla_compliant = complaints.filter(sla_breached=False, status='RESOLVED').count()
            sla_total = complaints.filter(status='RESOLVED').count()
            sla_compliance_rate = (sla_compliant / sla_total * 100) if sla_total > 0 else 0
            sla_breach_count = complaints.filter(sla_breached=True).count()
            
            # Calculate message statistics
            messages_sent = official.sent_messages.count()
            messages_received = official.received_messages.count()
            
            # Calculate performance score
            performance_score = 0
            if total > 0:
                resolution_rate = (resolved / total * 100)
                performance_score = (resolution_rate * 0.3) + (sla_compliance_rate * 0.25) + (avg_rating * 20 * 0.2)
                
                if avg_resolution_time:
                    ideal_days = 14
                    time_score = max(0, 100 - (avg_resolution_time - ideal_days) * 5)
                    time_score = min(100, time_score)
                    performance_score += time_score * 0.15
            
            # Update or create official performance
            OfficialPerformance.objects.update_or_create(
                official=official,
                defaults={
                    'total_complaints': total,
                    'resolved_complaints': resolved,
                    'rejected_complaints': rejected,
                    'pending_complaints': pending,
                    'overdue_complaints': overdue,
                    'avg_resolution_time': avg_resolution_time,
                    'avg_citizen_rating': avg_rating,
                    'avg_priority_score': avg_priority,
                    'sla_compliance_rate': sla_compliance_rate,
                    'sla_breach_count': sla_breach_count,
                    'messages_sent': messages_sent,
                    'messages_received': messages_received,
                    'performance_score': performance_score
                }
            )
        
        # Recalculate ranks
        official_performances = OfficialPerformance.objects.all().order_by('-performance_score')
        for rank, performance in enumerate(official_performances, start=1):
            performance.rank = rank
            performance.save()
        
        return Response({
            'message': 'Official performance metrics recalculated.',
            'count': officials.count()
        })


class IssuePatternViewSet(viewsets.ModelViewSet):
    """CRUD operations for Issue Patterns."""
    queryset = IssuePattern.objects.all()
    serializer_class = IssuePatternSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    @action(detail=False, methods=['get'])
    def detect(self, request):
        """Detect new issue patterns."""
        from django.utils import timezone
        from datetime import timedelta
        
        # Get time range from query params
        days = int(request.query_params.get('days', 90))
        min_complaints = int(request.query_params.get('min_complaints', 5))
        start_date = timezone.now() - timedelta(days=days)
        
        # Get all complaints in the time range
        complaints = Complaint.objects.filter(created_at__gte=start_date)
        
        # Group by category and location
        from django.db.models import Count
        
        # Find recurring issues
        patterns = complaints.values('category__name', 'jurisdiction__name').annotate(
            count=Count('id')
        ).filter(count__gte=min_complaints).order_by('-count')
        
        # Create or update issue patterns
        for pattern in patterns:
            name = f"{pattern['category__name']} in {pattern['jurisdiction__name']}"
            
            IssuePattern.objects.update_or_create(
                name=name,
                defaults={
                    'description': f"Recurring issue: {pattern['category__name']} in {pattern['jurisdiction__name']}",
                    'category_id': ComplaintCategory.objects.get(name=pattern['category__name']).id,
                    'keywords': [pattern['category__name'].lower()],
                    'complaint_count': pattern['count'],
                    'is_active': True
                }
            )
        
        return Response({
            'message': 'Issue patterns detected.',
            'patterns_detected': patterns.count()
        })


class HeatmapDataViewSet(viewsets.ModelViewSet):
    """CRUD operations for Heatmap Data."""
    queryset = HeatmapData.objects.all()
    serializer_class = HeatmapDataSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    @action(detail=False, methods=['get'])
    def generate(self, request):
        """Generate heatmap data."""
        from django.utils import timezone
        from datetime import timedelta
        
        # Get time range from query params
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)
        
        # Get all complaints in the time range with location data
        complaints = Complaint.objects.filter(
            created_at__gte=start_date,
            latitude__isnull=False,
            longitude__isnull=False
        )
        
        # Group by location (simplified - in production, use proper geographic clustering)
        # For now, we'll just count complaints per location
        from django.db.models import Count
        
        location_data = complaints.values('latitude', 'longitude', 'location_address').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Create heatmap data
        for data in location_data:
            HeatmapData.objects.update_or_create(
                latitude=data['latitude'],
                longitude=data['longitude'],
                start_date=start_date.date(),
                end_date=timezone.now().date(),
                defaults={
                    'location': data['location_address'] or f"{data['latitude']}, {data['longitude']}",
                    'complaint_count': data['count'],
                    'resolved_count': complaints.filter(
                        latitude=data['latitude'],
                        longitude=data['longitude'],
                        status='RESOLVED'
                    ).count(),
                    'pending_count': complaints.filter(
                        latitude=data['latitude'],
                        longitude=data['longitude']
                    ).exclude(status__in=['RESOLVED', 'REJECTED']).count()
                }
            )
        
        return Response({
            'message': 'Heatmap data generated.',
            'locations': location_data.count()
        })
