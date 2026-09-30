"""
Analytics models for NARADHA application.

Pre-computed performance and pattern data used by the analytics API
and the public dashboard.
"""
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.complaints.models import Complaint, ComplaintCategory
from apps.users.models import CustomUser, Department, Jurisdiction


class DepartmentPerformance(models.Model):
    """Performance metrics for departments."""
    department = models.OneToOneField(
        Department,
        on_delete=models.CASCADE,
        related_name='analytics_performance'
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
            ideal_days = 14
            avg_days = self.avg_resolution_time.days
            time_score = max(0, 100 - (avg_days - ideal_days) * 5)
            time_score = min(100, time_score)
        else:
            time_score = 50.0

        # Calculate weighted score
        self.performance_score = (
            (resolution_rate * 0.4) + (sla_score * 0.3)
            + (quality_score * 0.2) + (time_score * 0.1)
        )
        return self.performance_score


class OfficialPerformance(models.Model):
    """Performance metrics for officials."""
    official = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='analytics_performance',
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
        quality_score = self.avg_citizen_rating * 20

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

        self.performance_score = (
            (resolution_rate * 0.3) + (sla_score * 0.25)
            + (quality_score * 0.2) + (time_score * 0.15)
            + (response_score * 0.1)
        )
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
        related_name='analytics_issue_patterns'
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
        related_name='analytics_issue_patterns',
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
        related_name='resolved_analytics_patterns'
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
        if self.last_seen and (timezone.now() - self.last_seen).days < 7:
            return 'INCREASING'
        elif self.last_seen and (timezone.now() - self.last_seen).days < 30:
            return 'STABLE'
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
        return 'VERY_LOW'


class AnalyticsSnapshot(models.Model):
    """Periodic snapshot of aggregate metrics for trend analysis."""
    snapshot_date = models.DateField(unique=True)

    total_complaints = models.PositiveIntegerField(default=0)
    new_complaints = models.PositiveIntegerField(default=0)
    resolved_complaints = models.PositiveIntegerField(default=0)
    escalated_complaints = models.PositiveIntegerField(default=0)

    avg_resolution_days = models.FloatField(default=0.0)
    avg_citizen_rating = models.FloatField(default=0.0)
    sla_compliance_rate = models.FloatField(default=0.0)

    metrics = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Analytics Snapshot')
        verbose_name_plural = _('Analytics Snapshots')
        ordering = ['-snapshot_date']

    def __str__(self):
        return f"Snapshot {self.snapshot_date}"
