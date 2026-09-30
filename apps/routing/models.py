"""
Routing models for NARADHA application.

Logs how complaints are assigned and tracks each official's workload
so the AI router can balance assignments.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.complaints.models import Complaint
from apps.users.models import CustomUser, Department


class RoutingLog(models.Model):
    """Immutable log of every complaint assignment/transfer."""
    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name='routing_logs'
    )

    previous_official = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='routings_from',
        help_text='Official before this routing (None for first assignment)'
    )
    new_official = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='routings_to'
    )
    previous_department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='routings_from'
    )
    new_department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='routings_to'
    )

    routing_method = models.CharField(
        max_length=20,
        choices=[
            ('AUTO', 'Automatic (AI)'),
            ('MANUAL', 'Manual'),
            ('ESCALATION', 'Escalation'),
            ('TRANSFER', 'Transfer'),
        ],
        default='AUTO'
    )
    routing_reason = models.TextField(blank=True)

    # Confidence reported by the AI router (when method is AUTO)
    routing_confidence = models.FloatField(
        default=0.0,
        help_text='Confidence score of the AI routing decision (0-100%)'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Routing Log')
        verbose_name_plural = _('Routing Logs')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['complaint']),
        ]

    def __str__(self):
        prev = self.previous_official.get_short_name() if self.previous_official else 'None'
        new = self.new_official.get_short_name() if self.new_official else 'None'
        return f"{self.complaint.complaint_id}: {prev} → {new} ({self.routing_method})"


class OfficialWorkload(models.Model):
    """Rolling workload counters used by the AI router for load balancing."""
    official = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='workload',
        limit_choices_to={'role__in': ['OFFICIAL', 'MINISTER']}
    )

    assigned_complaints = models.PositiveIntegerField(default=0)
    resolved_complaints = models.PositiveIntegerField(default=0)
    active_complaints = models.PositiveIntegerField(default=0)

    # Optional per-day capacity used by the router
    max_daily_capacity = models.PositiveSmallIntegerField(
        default=20,
        help_text='Maximum new complaints this official can receive per day'
    )

    # Availability
    is_available = models.BooleanField(default=True)
    unavailable_until = models.DateTimeField(blank=True, null=True)

    last_assigned_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Official Workload')
        verbose_name_plural = _('Official Workloads')
        ordering = ['active_complaints']

    def __str__(self):
        return f"Workload: {self.official.get_short_name()} ({self.active_complaints} active)"

    @property
    def load_ratio(self):
        """Active complaints as a ratio of monthly capacity (~30 days)."""
        if self.max_daily_capacity == 0:
            return float('inf')
        return self.active_complaints / (self.max_daily_capacity * 30)

    def recalculate(self):
        """Recalculate counters from live complaint data."""
        complaints = self.official.complaints_assigned.exclude(is_deleted=True)
        self.assigned_complaints = complaints.count()
        self.resolved_complaints = complaints.filter(status='RESOLVED').count()
        self.active_complaints = complaints.exclude(
            status__in=['RESOLVED', 'REJECTED']
        ).count()
        self.save()
        return self
