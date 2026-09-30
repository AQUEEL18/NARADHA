"""
Dashboard models for NARADHA application.
"""
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from apps.complaints.models import Complaint, ComplaintCategory
from apps.users.models import CustomUser, Department, Jurisdiction


class DashboardWidget(models.Model):
    """Configurable dashboard widgets."""
    name = models.CharField(max_length=200)
    widget_type = models.CharField(
        max_length=50,
        choices=[
            ('STATS_CARD', 'Stats Card'),
            ('CHART', 'Chart'),
            ('TABLE', 'Table'),
            ('MAP', 'Map'),
            ('LIST', 'List'),
            ('METRIC', 'Metric'),
        ]
    )
    
    # Widget configuration
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text='Widget configuration (data source, display options, etc.)'
    )
    
    # Position
    position_x = models.PositiveSmallIntegerField(default=0)
    position_y = models.PositiveSmallIntegerField(default=0)
    width = models.PositiveSmallIntegerField(default=1)
    height = models.PositiveSmallIntegerField(default=1)
    
    # Visibility
    is_visible = models.BooleanField(default=True)
    is_public = models.BooleanField(
        default=True,
        help_text='Visible on public dashboard'
    )
    
    # Access control
    allowed_roles = models.JSONField(
        default=list,
        blank=True,
        help_text='List of roles that can see this widget'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Dashboard Widget')
        verbose_name_plural = _('Dashboard Widgets')
        ordering = ['position_y', 'position_x']
    
    def __str__(self):
        return f"{self.name} ({self.widget_type})"


class DashboardView(models.Model):
    """Custom dashboard views for different user types."""
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    
    # View type
    view_type = models.CharField(
        max_length=50,
        choices=[
            ('PUBLIC', 'Public Dashboard'),
            ('CITIZEN', 'Citizen Dashboard'),
            ('OFFICIAL', 'Official Dashboard'),
            ('MINISTER', 'Minister Dashboard'),
            ('ADMIN', 'Admin Dashboard'),
            ('CUSTOM', 'Custom Dashboard'),
        ],
        default='CUSTOM'
    )
    
    # Widgets in this view
    widgets = models.ManyToManyField(
        DashboardWidget,
        related_name='dashboard_views',
        blank=True
    )
    
    # Layout
    layout = models.JSONField(
        default=dict,
        blank=True,
        help_text='Dashboard layout configuration'
    )
    
    # Access control
    is_active = models.BooleanField(default=True)
    allowed_users = models.ManyToManyField(
        CustomUser,
        related_name='dashboard_views',
        blank=True
    )
    allowed_departments = models.ManyToManyField(
        Department,
        related_name='dashboard_views',
        blank=True
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Dashboard View')
        verbose_name_plural = _('Dashboard Views')
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.view_type})"


class PublicDashboardSettings(models.Model):
    """Settings for the public dashboard."""
    # What to show
    show_resolution_times = models.BooleanField(default=True)
    show_department_rankings = models.BooleanField(default=True)
    show_issue_patterns = models.BooleanField(default=True)
    show_citizen_satisfaction = models.BooleanField(default=True)
    show_sla_compliance = models.BooleanField(default=True)
    show_recent_complaints = models.BooleanField(default=True)
    show_top_officials = models.BooleanField(default=True)
    
    # Anonymization settings
    anonymize_citizen_data = models.BooleanField(default=True)
    anonymize_location_data = models.BooleanField(default=False)
    anonymization_level = models.CharField(
        max_length=20,
        choices=[
            ('FULL', 'Full Anonymization'),
            ('PARTIAL', 'Partial Anonymization'),
            ('MINIMAL', 'Minimal Anonymization'),
        ],
        default='PARTIAL'
    )
    
    # Data filters
    min_complaints_for_patterns = models.PositiveIntegerField(
        default=5,
        help_text='Minimum number of complaints to show as a pattern'
    )
    
    show_only_resolved = models.BooleanField(
        default=False,
        help_text='Show only resolved complaints on public dashboard'
    )
    
    # Time range
    default_time_range = models.CharField(
        max_length=20,
        choices=[
            ('LAST_7_DAYS', 'Last 7 Days'),
            ('LAST_30_DAYS', 'Last 30 Days'),
            ('LAST_90_DAYS', 'Last 90 Days'),
            ('LAST_YEAR', 'Last Year'),
            ('ALL_TIME', 'All Time'),
        ],
        default='LAST_30_DAYS'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Public Dashboard Settings')
        verbose_name_plural = _('Public Dashboard Settings')
    
    def __str__(self):
        return "Public Dashboard Settings"


class AnalyticsData(models.Model):
    """Pre-computed analytics data for faster dashboard loading."""
    data_type = models.CharField(
        max_length=50,
        choices=[
            ('RESOLUTION_TIMES', 'Resolution Times'),
            ('DEPARTMENT_RANKINGS', 'Department Rankings'),
            ('ISSUE_PATTERNS', 'Issue Patterns'),
            ('CITIZEN_SATISFACTION', 'Citizen Satisfaction'),
            ('SLA_COMPLIANCE', 'SLA Compliance'),
            ('OFFICIAL_PERFORMANCE', 'Official Performance'),
            ('GEOGRAPHIC_DISTRIBUTION', 'Geographic Distribution'),
        ]
    )
    
    # Data
    data = models.JSONField(default=dict, blank=True)
    
    # Metadata
    start_date = models.DateField()
    end_date = models.DateField()
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Analytics Data')
        verbose_name_plural = _('Analytics Data')
        ordering = ['-updated_at']
        unique_together = ['data_type', 'start_date', 'end_date']
    
    def __str__(self):
        return f"{self.data_type} ({self.start_date} to {self.end_date})"


class DepartmentPerformance(models.Model):
    """Performance metrics for departments."""
    department = models.OneToOneField(
        Department,
        on_delete=models.CASCADE,
        related_name='performance'
    )
    
    # Complaint statistics
    total_complaints = models.PositiveIntegerField(default=0)
    resolved_complaints = models.PositiveIntegerField(default=0)
    rejected_complaints = models.PositiveIntegerField(default=0)
    pending_complaints = models.PositiveIntegerField(default=0)
    
    # Time metrics
    avg_resolution_time = models.DurationField(blank=True, null=True)
    median_resolution_time = models.DurationField(blank=True, null=True)
    
    # Quality metrics
    avg_citizen_rating = models.FloatField(default=0.0)
    avg_priority_score = models.FloatField(default=0.0)
    
    # SLA metrics
    sla_compliance_rate = models.FloatField(default=0.0)
    sla_breach_count = models.PositiveIntegerField(default=0)
    
    # Performance score (calculated)
    performance_score = models.FloatField(default=0.0, help_text='0-100%')
    
    # Ranking
    rank = models.PositiveSmallIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Department Performance')
        verbose_name_plural = _('Department Performances')
        ordering = ['-performance_score']
    
    def __str__(self):
        return f"{self.department.name} ({self.performance_score}%)"
    
    def calculate_performance_score(self):
        """Calculate overall performance score."""
        if self.total_complaints == 0:
            self.performance_score = 0.0
            return self.performance_score
        
        # Resolution rate (40% weight)
        resolution_rate = (self.resolved_complaints / self.total_complaints) * 100
        
        # SLA compliance (30% weight)
        sla_score = self.sla_compliance_rate
        
        # Quality score (20% weight)
        quality_score = self.avg_citizen_rating * 20  # Convert 1-5 to 0-100
        
        # Time score (10% weight)
        if self.avg_resolution_time:
            # Assume 14 days is ideal
            ideal_days = 14
            avg_days = self.avg_resolution_time.days
            time_score = max(0, 100 - (avg_days - ideal_days) * 5)
            time_score = min(100, time_score)
        else:
            time_score = 50.0
        
        # Calculate weighted score
        self.performance_score = (resolution_rate * 0.4) + (sla_score * 0.3) + (quality_score * 0.2) + (time_score * 0.1)
        return self.performance_score


class OfficialPerformance(models.Model):
    """Performance metrics for officials."""
    official = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='official_performance',
        limit_choices_to={'role__in': ['OFFICIAL', 'MINISTER']}
    )
    
    # Complaint statistics
    total_complaints = models.PositiveIntegerField(default=0)
    resolved_complaints = models.PositiveIntegerField(default=0)
    rejected_complaints = models.PositiveIntegerField(default=0)
    pending_complaints = models.PositiveIntegerField(default=0)
    overdue_complaints = models.PositiveIntegerField(default=0)
    
    # Time metrics
    avg_response_time = models.DurationField(blank=True, null=True)
    avg_resolution_time = models.DurationField(blank=True, null=True)
    
    # Quality metrics
    avg_citizen_rating = models.FloatField(default=0.0)
    avg_priority_score = models.FloatField(default=0.0)
    
    # SLA metrics
    sla_compliance_rate = models.FloatField(default=0.0)
    sla_breach_count = models.PositiveIntegerField(default=0)
    
    # Communication metrics
    messages_sent = models.PositiveIntegerField(default=0)
    messages_received = models.PositiveIntegerField(default=0)
    avg_message_response_time = models.DurationField(blank=True, null=True)
    
    # Performance score (calculated)
    performance_score = models.FloatField(default=0.0, help_text='0-100%')
    
    # Ranking
    rank = models.PositiveSmallIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Official Performance')
        verbose_name_plural = _('Official Performances')
        ordering = ['-performance_score']
    
    def __str__(self):
        return f"{self.official.get_short_name()} ({self.performance_score}%)"
    
    def calculate_performance_score(self):
        """Calculate overall performance score."""
        if self.total_complaints == 0:
            self.performance_score = 0.0
            return self.performance_score
        
        # Resolution rate (30% weight)
        resolution_rate = (self.resolved_complaints / self.total_complaints) * 100
        
        # SLA compliance (25% weight)
        sla_score = self.sla_compliance_rate
        
        # Quality score (20% weight)
        quality_score = self.avg_citizen_rating * 20  # Convert 1-5 to 0-100
        
        # Time score (15% weight)
        if self.avg_resolution_time:
            ideal_days = 14
            avg_days = self.avg_resolution_time.days
            time_score = max(0, 100 - (avg_days - ideal_days) * 5)
            time_score = min(100, time_score)
        else:
            time_score = 50.0
        
        # Response score (10% weight)
        if self.avg_response_time:
            ideal_hours = 2
            avg_hours = self.avg_response_time.total_seconds() / 3600
            response_score = max(0, 100 - (avg_hours - ideal_hours) * 50)
            response_score = min(100, response_score)
        else:
            response_score = 50.0
        
        # Calculate weighted score
        self.performance_score = (resolution_rate * 0.3) + (sla_score * 0.25) + (quality_score * 0.2) + (time_score * 0.15) + (response_score * 0.1)
        return self.performance_score


class IssuePattern(models.Model):
    """Patterns of recurring issues."""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Pattern details
    category = models.ForeignKey(
        ComplaintCategory,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='issue_patterns'
    )
    
    keywords = models.JSONField(
        default=list,
        blank=True,
        help_text='List of keywords that identify this pattern'
    )
    
    # Statistics
    complaint_count = models.PositiveIntegerField(default=0)
    first_seen = models.DateTimeField(blank=True, null=True)
    last_seen = models.DateTimeField(blank=True, null=True)
    
    # Geographic info
    jurisdictions = models.ManyToManyField(
        Jurisdiction,
        related_name='issue_patterns',
        blank=True
    )
    
    # Severity
    avg_priority_score = models.FloatField(default=0.0)
    max_priority_score = models.PositiveSmallIntegerField(default=0)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_resolved = models.BooleanField(default=False)
    
    # Resolution
    resolution_notes = models.TextField(blank=True)
    resolved_at = models.DateTimeField(blank=True, null=True)
    resolved_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='resolved_patterns'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Issue Pattern')
        verbose_name_plural = _('Issue Patterns')
        ordering = ['-complaint_count', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.complaint_count} complaints)"
    
    def get_trend(self):
        """Get trend (increasing, decreasing, stable)."""
        # This would be calculated based on historical data
        # For now, return based on recent activity
        if self.last_seen and (timezone.now() - self.last_seen).days < 7:
            return 'INCREASING'
        elif self.last_seen and (timezone.now() - self.last_seen).days < 30:
            return 'STABLE'
        else:
            return 'DECREASING'


class HeatmapData(models.Model):
    """Geographic heatmap data for issue visualization."""
    location = models.CharField(max_length=255)
    latitude = models.DecimalField(max_digits=10, decimal_places=8)
    longitude = models.DecimalField(max_digits=11, decimal_places=8)
    
    # Aggregated data
    complaint_count = models.PositiveIntegerField(default=0)
    resolved_count = models.PositiveIntegerField(default=0)
    pending_count = models.PositiveIntegerField(default=0)
    
    # Priority distribution
    low_priority = models.PositiveIntegerField(default=0)
    medium_priority = models.PositiveIntegerField(default=0)
    high_priority = models.PositiveIntegerField(default=0)
    critical_priority = models.PositiveIntegerField(default=0)
    
    # Category distribution
    category_data = models.JSONField(
        default=dict,
        blank=True,
        help_text='Dictionary of category IDs to counts'
    )
    
    # Time range
    start_date = models.DateField()
    end_date = models.DateField()
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Heatmap Data')
        verbose_name_plural = _('Heatmap Data')
        ordering = ['-complaint_count']
        unique_together = ['latitude', 'longitude', 'start_date', 'end_date']
    
    def __str__(self):
        return f"{self.location} ({self.complaint_count} complaints)"
    
    def get_intensity(self):
        """Get intensity level for heatmap visualization."""
        if self.complaint_count >= 100:
            return 'VERY_HIGH'
        elif self.complaint_count >= 50:
            return 'HIGH'
        elif self.complaint_count >= 20:
            return 'MEDIUM'
        elif self.complaint_count >= 5:
            return 'LOW'
        else:
            return 'VERY_LOW'


class DashboardAlert(models.Model):
    """Alerts for dashboard users."""
    alert_type = models.CharField(
        max_length=50,
        choices=[
            ('SLA_BREACH', 'SLA Breach'),
            ('HIGH_PRIORITY', 'High Priority Complaint'),
            ('RECURRING_ISSUE', 'Recurring Issue Detected'),
            ('PERFORMANCE_DROP', 'Performance Drop'),
            ('NEW_PATTERN', 'New Issue Pattern'),
            ('ESCALATION', 'Escalation'),
            ('SYSTEM_ISSUE', 'System Issue'),
        ]
    )
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Related objects
    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='dashboard_alerts'
    )
    
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='dashboard_alerts'
    )
    
    official = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='dashboard_alerts'
    )
    
    # Severity
    severity = models.CharField(
        max_length=20,
        choices=[
            ('LOW', 'Low'),
            ('MEDIUM', 'Medium'),
            ('HIGH', 'High'),
            ('CRITICAL', 'Critical'),
        ],
        default='MEDIUM'
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    is_acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='acknowledged_alerts'
    )
    acknowledged_at = models.DateTimeField(blank=True, null=True)
    
    # Action
    action_url = models.URLField(blank=True)
    action_text = models.CharField(max_length=100, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Dashboard Alert')
        verbose_name_plural = _('Dashboard Alerts')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.alert_type}: {self.title}"
    
    def get_severity_color(self):
        """Get color for severity badge."""
        colors = {
            'LOW': 'bg-blue-100 text-blue-800',
            'MEDIUM': 'bg-yellow-100 text-yellow-800',
            'HIGH': 'bg-orange-100 text-orange-800',
            'CRITICAL': 'bg-red-100 text-red-800',
        }
        return colors.get(self.severity, 'bg-gray-100 text-gray-800')
