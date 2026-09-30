"""
Views for Dashboard app.
"""
from django.db.models import Q, Count, Avg, Sum, F, FloatField, ExpressionWrapper
from django.db.models.functions import TruncDate, ExtractDay, ExtractMonth, ExtractYear
from rest_framework import generics, permissions, status, views, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import (
    DashboardWidget, DashboardView, PublicDashboardSettings,
    AnalyticsData, DepartmentPerformance, OfficialPerformance,
    IssuePattern, HeatmapData, DashboardAlert
)
from .serializers import (
    DashboardWidgetSerializer, DashboardViewSerializer,
    PublicDashboardSettingsSerializer, AnalyticsDataSerializer,
    DepartmentPerformanceSerializer, OfficialPerformanceSerializer,
    IssuePatternSerializer, HeatmapDataSerializer, DashboardAlertSerializer
)
from apps.complaints.models import Complaint, ComplaintCategory
from apps.users.models import CustomUser, Department, Jurisdiction
from apps.complaints.serializers import ComplaintMinimalSerializer


class DashboardWidgetViewSet(viewsets.ModelViewSet):
    """CRUD operations for Dashboard Widgets."""
    queryset = DashboardWidget.objects.all()
    serializer_class = DashboardWidgetSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]
        return super().get_permissions()


class DashboardViewViewSet(viewsets.ModelViewSet):
    """CRUD operations for Dashboard Views."""
    queryset = DashboardView.objects.all()
    serializer_class = DashboardViewSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]
        return super().get_permissions()


class PublicDashboardSettingsViewSet(viewsets.ModelViewSet):
    """CRUD operations for Public Dashboard Settings."""
    queryset = PublicDashboardSettings.objects.all()
    serializer_class = PublicDashboardSettingsSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]
        return super().get_permissions()
    
    def get_object(self):
        # There should only be one public dashboard settings object
        obj, created = PublicDashboardSettings.objects.get_or_create(pk=1)
        return obj


class AnalyticsDataViewSet(viewsets.ModelViewSet):
    """CRUD operations for Analytics Data."""
    queryset = AnalyticsData.objects.all()
    serializer_class = AnalyticsDataSerializer
    permission_classes = [permissions.IsAuthenticated]


class DepartmentPerformanceViewSet(viewsets.ModelViewSet):
    """CRUD operations for Department Performance."""
    queryset = DepartmentPerformance.objects.all()
    serializer_class = DepartmentPerformanceSerializer
    permission_classes = [permissions.IsAuthenticated]


class OfficialPerformanceViewSet(viewsets.ModelViewSet):
    """CRUD operations for Official Performance."""
    queryset = OfficialPerformance.objects.all()
    serializer_class = OfficialPerformanceSerializer
    permission_classes = [permissions.IsAuthenticated]


class IssuePatternViewSet(viewsets.ModelViewSet):
    """CRUD operations for Issue Patterns."""
    queryset = IssuePattern.objects.all()
    serializer_class = IssuePatternSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class HeatmapDataViewSet(viewsets.ModelViewSet):
    """CRUD operations for Heatmap Data."""
    queryset = HeatmapData.objects.all()
    serializer_class = HeatmapDataSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class DashboardAlertViewSet(viewsets.ModelViewSet):
    """CRUD operations for Dashboard Alerts."""
    queryset = DashboardAlert.objects.all()
    serializer_class = DashboardAlertSerializer
    permission_classes = [permissions.IsAuthenticated]


class PublicDashboardView(views.APIView):
    """Public dashboard with aggregated data."""
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        # Get settings
        settings = PublicDashboardSettings.objects.first()
        
        # Time range filter
        time_range = request.query_params.get('time_range', 'LAST_30_DAYS')
        
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
        
        # Filter complaints
        complaints = Complaint.objects.filter(
            created_at__range=[start_date, end_date],
            commitment_visible=True
        )
        
        # Get statistics
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
        
        avg_resolution_times = []
        for complaint in resolved_with_dates:
            delta = complaint.resolution_date - complaint.submitted_at
            avg_resolution_times.append(delta.days)
        
        avg_resolution_time = sum(avg_resolution_times) / len(avg_resolution_times) if avg_resolution_times else 0
        
        # Department rankings
        dept_performance = []
        departments = Department.objects.filter(is_active=True)
        for dept in departments:
            dept_complaints = complaints.filter(assigned_department=dept)
            dept_resolved = dept_complaints.filter(status='RESOLVED').count()
            dept_total = dept_complaints.count()
            
            if dept_total > 0:
                dept_resolution_rate = (dept_resolved / dept_total * 100)
                dept_avg_time = sum(
                    (c.resolution_date - c.submitted_at).days 
                    for c in dept_complaints.filter(status='RESOLVED')
                    if c.resolution_date and c.submitted_at
                ) / dept_resolved if dept_resolved > 0 else 0
            else:
                dept_resolution_rate = 0
                dept_avg_time = 0
            
            dept_performance.append({
                'department': {
                    'id': dept.id,
                    'name': dept.name,
                    'code': dept.code
                },
                'total_complaints': dept_total,
                'resolved_complaints': dept_resolved,
                'resolution_rate': round(dept_resolution_rate, 2),
                'avg_resolution_time': round(dept_avg_time, 2)
            })
        
        # Sort by resolution rate
        dept_performance.sort(key=lambda x: x['resolution_rate'], reverse=True)
        
        # Issue patterns (categories)
        category_distribution = []
        categories = ComplaintCategory.objects.filter(is_active=True)
        for category in categories:
            count = complaints.filter(category=category).count()
            if count > 0:
                category_distribution.append({
                    'category': {
                        'id': category.id,
                        'name': category.name,
                        'code': category.code,
                        'color': category.color
                    },
                    'count': count
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
        
        # Citizen satisfaction
        ratings = complaints.filter(citizen_ratings__isnull=False).values('citizen_ratings')
        rating_counts = {}
        for r in ratings:
            rating = r['citizen_ratings']
            rating_counts[rating] = rating_counts.get(rating, 0) + 1
        
        avg_rating = sum(r['citizen_ratings'] for r in ratings) / len(ratings) if ratings else 0
        
        # SLA compliance
        sla_compliant = complaints.filter(sla_breached=False, status='RESOLVED').count()
        sla_total = complaints.filter(status='RESOLVED').count()
        sla_compliance_rate = (sla_compliant / sla_total * 100) if sla_total > 0 else 0
        
        # Time series data
        time_series = []
        for day in range((end_date - start_date).days + 1):
            current_date = start_date + timedelta(days=day)
            count = complaints.filter(
                created_at__date=current_date.date()
            ).count()
            time_series.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'count': count
            })
        
        # Recent complaints
        recent_complaints = complaints.order_by('-created_at')[:10]
        recent_serializer = ComplaintMinimalSerializer(recent_complaints, many=True)
        
        return Response({
            'time_range': time_range,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'statistics': {
                'total_complaints': total_complaints,
                'resolved_complaints': resolved_complaints,
                'pending_complaints': pending_complaints,
                'rejected_complaints': rejected_complaints,
                'resolution_rate': round(resolution_rate, 2),
                'avg_resolution_time': round(avg_resolution_time, 2)
            },
            'department_performance': dept_performance,
            'category_distribution': category_distribution,
            'priority_distribution': priority_distribution,
            'citizen_satisfaction': {
                'avg_rating': round(avg_rating, 2),
                'rating_counts': rating_counts,
                'total_ratings': len(ratings)
            },
            'sla_compliance': {
                'compliance_rate': round(sla_compliance_rate, 2),
                'compliant': sla_compliant,
                'total': sla_total
            },
            'time_series': time_series,
            'recent_complaints': recent_serializer.data
        })


class OfficialDashboardView(views.APIView):
    """Dashboard for officials."""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Check if user is official
        if not user.is_official():
            return Response({'error': 'Only officials can access this dashboard.'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        # Time range filter
        time_range = request.query_params.get('time_range', 'LAST_30_DAYS')
        
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
        
        # Filter complaints assigned to this official
        complaints = Complaint.objects.filter(
            assigned_official=user,
            created_at__range=[start_date, end_date]
        )
        
        # Get statistics
        total_complaints = complaints.count()
        resolved_complaints = complaints.filter(status='RESOLVED').count()
        pending_complaints = complaints.exclude(status__in=['RESOLVED', 'REJECTED']).count()
        overdue_complaints = complaints.filter(sla_breached=True).count()
        
        # Resolution rate
        resolution_rate = (resolved_complaints / total_complaints * 100) if total_complaints > 0 else 0
        
        # Average resolution time
        avg_resolution_time = 0
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
        
        # Priority distribution
        priority_distribution = []
        for priority in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
            count = complaints.filter(priority=priority).count()
            priority_distribution.append({
                'priority': priority,
                'count': count
            })
        
        # Category distribution
        category_distribution = []
        categories = ComplaintCategory.objects.filter(is_active=True)
        for category in categories:
            count = complaints.filter(category=category).count()
            if count > 0:
                category_distribution.append({
                    'category': {
                        'id': category.id,
                        'name': category.name,
                        'code': category.code,
                        'color': category.color
                    },
                    'count': count
                })
        
        category_distribution.sort(key=lambda x: x['count'], reverse=True)
        
        # Recent complaints
        recent_complaints = complaints.order_by('-created_at')[:10]
        recent_serializer = ComplaintMinimalSerializer(recent_complaints, many=True)
        
        # Performance metrics
        performance_data = {
            'response_rate': user.response_rate,
            'avg_response_time': str(user.avg_response_time) if user.avg_response_time else None,
            'total_complaints_handled': user.total_complaints_handled
        }
        
        return Response({
            'time_range': time_range,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'statistics': {
                'total_complaints': total_complaints,
                'resolved_complaints': resolved_complaints,
                'pending_complaints': pending_complaints,
                'overdue_complaints': overdue_complaints,
                'resolution_rate': round(resolution_rate, 2),
                'avg_resolution_time': round(avg_resolution_time, 2)
            },
            'priority_distribution': priority_distribution,
            'category_distribution': category_distribution,
            'recent_complaints': recent_serializer.data,
            'performance': performance_data
        })


class MinisterDashboardView(views.APIView):
    """Dashboard for ministers."""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Check if user is minister
        if not (user.role == 'MINISTER' or user.is_admin or user.is_superuser):
            return Response({'error': 'Only ministers can access this dashboard.'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        # Time range filter
        time_range = request.query_params.get('time_range', 'LAST_30_DAYS')
        
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
        
        # Filter complaints by department
        if user.department:
            complaints = Complaint.objects.filter(
                assigned_department=user.department,
                created_at__range=[start_date, end_date]
            )
        else:
            complaints = Complaint.objects.filter(created_at__range=[start_date, end_date])
        
        # Get statistics
        total_complaints = complaints.count()
        resolved_complaints = complaints.filter(status='RESOLVED').count()
        pending_complaints = complaints.exclude(status__in=['RESOLVED', 'REJECTED']).count()
        
        # Resolution rate
        resolution_rate = (resolved_complaints / total_complaints * 100) if total_complaints > 0 else 0
        
        # Department officials performance
        officials = CustomUser.objects.filter(
            role='OFFICIAL',
            department=user.department if user.department else None
        )
        
        officials_performance = []
        for official in officials:
            official_complaints = complaints.filter(assigned_official=official)
            official_resolved = official_complaints.filter(status='RESOLVED').count()
            official_total = official_complaints.count()
            
            if official_total > 0:
                official_resolution_rate = (official_resolved / official_total * 100)
            else:
                official_resolution_rate = 0
            
            officials_performance.append({
                'official': {
                    'id': official.id,
                    'name': official.get_short_name(),
                    'designation': official.designation
                },
                'total_complaints': official_total,
                'resolved_complaints': official_resolved,
                'resolution_rate': round(official_resolution_rate, 2),
                'performance_score': round(official.get_performance_score(), 2)
            })
        
        officials_performance.sort(key=lambda x: x['resolution_rate'], reverse=True)
        
        # Category distribution
        category_distribution = []
        categories = ComplaintCategory.objects.filter(is_active=True)
        for category in categories:
            count = complaints.filter(category=category).count()
            if count > 0:
                category_distribution.append({
                    'category': {
                        'id': category.id,
                        'name': category.name,
                        'code': category.code,
                        'color': category.color
                    },
                    'count': count
                })
        
        category_distribution.sort(key=lambda x: x['count'], reverse=True)
        
        # SLA compliance
        sla_compliant = complaints.filter(sla_breached=False, status='RESOLVED').count()
        sla_total = complaints.filter(status='RESOLVED').count()
        sla_compliance_rate = (sla_compliant / sla_total * 100) if sla_total > 0 else 0
        
        # Escalations
        escalated_complaints = complaints.filter(escalation_level__gte=1).count()
        
        return Response({
            'time_range': time_range,
            'statistics': {
                'total_complaints': total_complaints,
                'resolved_complaints': resolved_complaints,
                'pending_complaints': pending_complaints,
                'resolution_rate': round(resolution_rate, 2),
                'sla_compliance_rate': round(sla_compliance_rate, 2),
                'escalated_complaints': escalated_complaints
            },
            'officials_performance': officials_performance,
            'category_distribution': category_distribution
        })


class CitizenDashboardView(views.APIView):
    """Dashboard for citizens."""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Check if user is citizen
        if not user.is_citizen():
            return Response({'error': 'Only citizens can access this dashboard.'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        # Time range filter
        time_range = request.query_params.get('time_range', 'ALL_TIME')
        
        # Calculate date range
        from django.utils import timezone
        from datetime import timedelta
        
        end_date = timezone.now()
        if time_range == 'LAST_7_DAYS':
            start_date = end_date - timedelta(days=7)
        elif time_range == 'LAST_30_DAYS':
            start_date = end_date - timedelta(days=30)
        elif time_range == 'LAST_90_DAYS':
            start_date = end_date - timedelta(days=90)
        elif time_range == 'LAST_YEAR':
            start_date = end_date - timedelta(days=365)
        else:  # ALL_TIME
            start_date = None
        
        # Filter complaints filed by this citizen
        if start_date:
            complaints = Complaint.objects.filter(
                citizen=user,
                created_at__range=[start_date, end_date]
            )
        else:
            complaints = Complaint.objects.filter(citizen=user)
        
        # Get statistics
        total_complaints = complaints.count()
        resolved_complaints = complaints.filter(status='RESOLVED').count()
        pending_complaints = complaints.exclude(status__in=['RESOLVED', 'REJECTED']).count()
        rejected_complaints = complaints.filter(status='REJECTED').count()
        
        # Resolution rate
        resolution_rate = (resolved_complaints / total_complaints * 100) if total_complaints > 0 else 0
        
        # Average resolution time
        avg_resolution_time = 0
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
        
        # Category distribution
        category_distribution = []
        categories = ComplaintCategory.objects.filter(is_active=True)
        for category in categories:
            count = complaints.filter(category=category).count()
            if count > 0:
                category_distribution.append({
                    'category': {
                        'id': category.id,
                        'name': category.name,
                        'code': category.code,
                        'color': category.color
                    },
                    'count': count
                })
        
        category_distribution.sort(key=lambda x: x['count'], reverse=True)
        
        # Recent complaints
        recent_complaints = complaints.order_by('-created_at')[:10]
        recent_serializer = ComplaintMinimalSerializer(recent_complaints, many=True)
        
        # Citizen satisfaction (for user's complaints)
        ratings = complaints.filter(citizen_ratings__isnull=False).values('citizen_ratings')
        rating_counts = {}
        for r in ratings:
            rating = r['citizen_ratings']
            rating_counts[rating] = rating_counts.get(rating, 0) + 1
        
        avg_rating = sum(r['citizen_ratings'] for r in ratings) / len(ratings) if ratings else 0
        
        return Response({
            'time_range': time_range,
            'statistics': {
                'total_complaints': total_complaints,
                'resolved_complaints': resolved_complaints,
                'pending_complaints': pending_complaints,
                'rejected_complaints': rejected_complaints,
                'resolution_rate': round(resolution_rate, 2),
                'avg_resolution_time': round(avg_resolution_time, 2)
            },
            'category_distribution': category_distribution,
            'recent_complaints': recent_serializer.data,
            'citizen_satisfaction': {
                'avg_rating': round(avg_rating, 2),
                'rating_counts': rating_counts,
                'total_ratings': len(ratings)
            }
        })


class AdminDashboardView(views.APIView):
    """Dashboard for administrators."""
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    
    def get(self, request):
        # Time range filter
        time_range = request.query_params.get('time_range', 'LAST_30_DAYS')
        
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
        
        # Filter complaints
        complaints = Complaint.objects.filter(created_at__range=[start_date, end_date])
        
        # Overall statistics
        total_complaints = complaints.count()
        resolved_complaints = complaints.filter(status='RESOLVED').count()
        pending_complaints = complaints.exclude(status__in=['RESOLVED', 'REJECTED']).count()
        
        resolution_rate = (resolved_complaints / total_complaints * 100) if total_complaints > 0 else 0
        
        # Department statistics
        departments = Department.objects.filter(is_active=True)
        dept_stats = []
        for dept in departments:
            dept_complaints = complaints.filter(assigned_department=dept)
            dept_resolved = dept_complaints.filter(status='RESOLVED').count()
            dept_total = dept_complaints.count()
            
            dept_resolution_rate = (dept_resolved / dept_total * 100) if dept_total > 0 else 0
            
            dept_stats.append({
                'department': {
                    'id': dept.id,
                    'name': dept.name,
                    'code': dept.code
                },
                'total_complaints': dept_total,
                'resolved_complaints': dept_resolved,
                'resolution_rate': round(dept_resolution_rate, 2)
            })
        
        dept_stats.sort(key=lambda x: x['resolution_rate'], reverse=True)
        
        # Official statistics
        officials = CustomUser.objects.filter(role='OFFICIAL')
        official_stats = []
        for official in officials:
            official_complaints = complaints.filter(assigned_official=official)
            official_resolved = official_complaints.filter(status='RESOLVED').count()
            official_total = official_complaints.count()
            
            official_resolution_rate = (official_resolved / official_total * 100) if official_total > 0 else 0
            
            official_stats.append({
                'official': {
                    'id': official.id,
                    'name': official.get_short_name(),
                    'department': official.department.name if official.department else ''
                },
                'total_complaints': official_total,
                'resolved_complaints': official_resolved,
                'resolution_rate': round(official_resolution_rate, 2)
            })
        
        official_stats.sort(key=lambda x: x['resolution_rate'], reverse=True)
        
        # Category distribution
        category_distribution = []
        categories = ComplaintCategory.objects.filter(is_active=True)
        for category in categories:
            count = complaints.filter(category=category).count()
            if count > 0:
                category_distribution.append({
                    'category': {
                        'id': category.id,
                        'name': category.name,
                        'code': category.code,
                        'color': category.color
                    },
                    'count': count
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
        
        # SLA compliance
        sla_compliant = complaints.filter(sla_breached=False, status='RESOLVED').count()
        sla_total = complaints.filter(status='RESOLVED').count()
        sla_compliance_rate = (sla_compliant / sla_total * 100) if sla_total > 0 else 0
        
        # Escalations
        escalated_complaints = complaints.filter(escalation_level__gte=1).count()
        
        # Citizen satisfaction
        ratings = complaints.filter(citizen_ratings__isnull=False).values('citizen_ratings')
        avg_rating = sum(r['citizen_ratings'] for r in ratings) / len(ratings) if ratings else 0
        
        return Response({
            'time_range': time_range,
            'overall_statistics': {
                'total_complaints': total_complaints,
                'resolved_complaints': resolved_complaints,
                'pending_complaints': pending_complaints,
                'resolution_rate': round(resolution_rate, 2),
                'sla_compliance_rate': round(sla_compliance_rate, 2),
                'escalated_complaints': escalated_complaints,
                'avg_citizen_rating': round(avg_rating, 2)
            },
            'department_statistics': dept_stats,
            'official_statistics': official_stats,
            'category_distribution': category_distribution,
            'priority_distribution': priority_distribution
        })
