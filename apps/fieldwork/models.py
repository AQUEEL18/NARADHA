"""
Fieldwork models for NARADHA application.
"""
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from apps.complaints.models import Complaint
from apps.users.models import CustomUser, Jurisdiction


class FieldTaskStatus(models.TextChoices):
    """Status choices for field tasks."""
    PENDING = 'PENDING', _('Pending')
    ASSIGNED = 'ASSIGNED', _('Assigned')
    IN_PROGRESS = 'IN_PROGRESS', _('In Progress')
    ON_SITE = 'ON_SITE', _('On Site')
    COMPLETED = 'COMPLETED', _('Completed')
    VERIFIED = 'VERIFIED', _('Verified')
    REJECTED = 'REJECTED', _('Rejected')
    CANCELLED = 'CANCELLED', _('Cancelled')


class FieldTask(models.Model):
    """Field tasks for complaint resolution."""
    task_id = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        help_text='Unique task ID (e.g., FT-987654)'
    )
    
    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name='field_tasks'
    )
    
    # Assignment
    assigned_to = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        related_name='assigned_tasks',
        null=True,
        blank=True,
        limit_choices_to={'role': 'FIELD_WORKER'}
    )
    
    assigned_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='tasks_assigned'
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=FieldTaskStatus.choices,
        default=FieldTaskStatus.PENDING
    )
    
    # Task details
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Location
    location_address = models.TextField(blank=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=8, blank=True, null=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, blank=True, null=True)
    jurisdiction = models.ForeignKey(
        Jurisdiction,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='field_tasks'
    )
    
    # Deadline
    deadline = models.DateTimeField(blank=True, null=True)
    
    # Work details
    work_type = models.CharField(
        max_length=100,
        blank=True,
        choices=[
            ('INSPECTION', 'Inspection'),
            ('REPAIR', 'Repair'),
            ('CLEANING', 'Cleaning'),
            ('INSTALLATION', 'Installation'),
            ('REMOVAL', 'Removal'),
            ('MAINTENANCE', 'Maintenance'),
            ('SURVEY', 'Survey'),
            ('OTHER', 'Other'),
        ]
    )
    
    materials_used = models.TextField(blank=True)
    labor_hours = models.FloatField(blank=True, null=True)
    cost_estimate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )
    
    # Before/After photos
    before_photo = models.ImageField(
        upload_to='fieldwork/before/',
        blank=True,
        null=True
    )
    after_photo = models.ImageField(
        upload_to='fieldwork/after/',
        blank=True,
        null=True
    )
    
    # Completion details
    completion_notes = models.TextField(blank=True)
    completion_date = models.DateTimeField(blank=True, null=True)
    
    # Verification
    verified_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='verified_tasks'
    )
    verification_notes = models.TextField(blank=True)
    verification_date = models.DateTimeField(blank=True, null=True)
    
    # Quality rating
    quality_rating = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    quality_feedback = models.TextField(blank=True)
    
    # GPS tracking
    gps_track = models.JSONField(
        default=list,
        blank=True,
        help_text='List of GPS coordinates with timestamps'
    )
    
    # Metadata
    priority = models.CharField(
        max_length=20,
        choices=[
            ('LOW', 'Low'),
            ('MEDIUM', 'Medium'),
            ('HIGH', 'High'),
            ('CRITICAL', 'Critical'),
        ],
        default='MEDIUM'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        verbose_name = _('Field Task')
        verbose_name_plural = _('Field Tasks')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['assigned_to']),
            models.Index(fields=['complaint']),
        ]
    
    def __str__(self):
        return f"{self.task_id} - {self.title}"
    
    def save(self, *args, **kwargs):
        """Override save to generate task_id if not set."""
        if not self.task_id:
            from django.db.models import Max
            last_task = FieldTask.objects.aggregate(Max('id'))
            last_id = last_task['id__max'] or 0
            self.task_id = f"FT-{100000 + last_id + 1}"
        
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('field_task_detail', args=[str(self.task_id)])
    
    def get_status_badge(self):
        """Get HTML badge for status."""
        status_colors = {
            FieldTaskStatus.PENDING: 'bg-gray-100 text-gray-800',
            FieldTaskStatus.ASSIGNED: 'bg-blue-100 text-blue-800',
            FieldTaskStatus.IN_PROGRESS: 'bg-yellow-100 text-yellow-800',
            FieldTaskStatus.ON_SITE: 'bg-cyan-100 text-cyan-800',
            FieldTaskStatus.COMPLETED: 'bg-green-100 text-green-800',
            FieldTaskStatus.VERIFIED: 'bg-emerald-100 text-emerald-800',
            FieldTaskStatus.REJECTED: 'bg-red-100 text-red-800',
            FieldTaskStatus.CANCELLED: 'bg-rose-100 text-rose-800',
        }
        color = status_colors.get(self.status, 'bg-gray-100 text-gray-800')
        return f'<span class="px-2 py-1 rounded-full text-xs font-semibold {color}">{self.get_status_display()}</span>'
    
    def get_priority_badge(self):
        """Get HTML badge for priority."""
        priority_colors = {
            'LOW': 'bg-blue-100 text-blue-800',
            'MEDIUM': 'bg-yellow-100 text-yellow-800',
            'HIGH': 'bg-orange-100 text-orange-800',
            'CRITICAL': 'bg-red-100 text-red-800',
        }
        color = priority_colors.get(self.priority, 'bg-gray-100 text-gray-800')
        return f'<span class="px-2 py-1 rounded-full text-xs font-semibold {color}">{self.priority}</span>'
    
    def is_overdue(self):
        """Check if task is overdue."""
        if self.deadline:
            return timezone.now() > self.deadline
        return False
    
    def get_completion_percentage(self):
        """Get completion percentage based on status."""
        status_weights = {
            FieldTaskStatus.PENDING: 0,
            FieldTaskStatus.ASSIGNED: 10,
            FieldTaskStatus.IN_PROGRESS: 40,
            FieldTaskStatus.ON_SITE: 60,
            FieldTaskStatus.COMPLETED: 80,
            FieldTaskStatus.VERIFIED: 100,
            FieldTaskStatus.REJECTED: 0,
            FieldTaskStatus.CANCELLED: 0,
        }
        return status_weights.get(self.status, 0)


class FieldTaskHistory(models.Model):
    """History log for field task status changes."""
    task = models.ForeignKey(
        FieldTask,
        on_delete=models.CASCADE,
        related_name='history'
    )
    
    previous_status = models.CharField(
        max_length=20,
        choices=FieldTaskStatus.choices,
        blank=True,
        null=True
    )
    
    new_status = models.CharField(
        max_length=20,
        choices=FieldTaskStatus.choices
    )
    
    changed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='task_status_changes'
    )
    
    notes = models.TextField(blank=True)
    
    # GPS location at time of change
    latitude = models.DecimalField(max_digits=10, decimal_places=8, blank=True, null=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, blank=True, null=True)
    
    # Metadata
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('Field Task History')
        verbose_name_plural = _('Field Task Histories')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.task.task_id}: {self.previous_status or 'None'} → {self.new_status}"


class FieldWorkerLocation(models.Model):
    """Track real-time location of field workers."""
    worker = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='location_updates',
        limit_choices_to={'role': 'FIELD_WORKER'}
    )
    
    latitude = models.DecimalField(max_digits=10, decimal_places=8)
    longitude = models.DecimalField(max_digits=11, decimal_places=8)
    
    accuracy = models.FloatField(help_text='Accuracy in meters')
    
    # Device info
    device_id = models.CharField(max_length=255, blank=True)
    battery_level = models.FloatField(blank=True, null=True)
    
    # Task context
    current_task = models.ForeignKey(
        FieldTask,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='location_updates'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('Field Worker Location')
        verbose_name_plural = _('Field Worker Locations')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['worker']),
        ]
    
    def __str__(self):
        return f"{self.worker.get_short_name()} at ({self.latitude}, {self.longitude})"


class FieldWorkerPerformance(models.Model):
    """Performance metrics for field workers."""
    worker = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='field_performance',
        limit_choices_to={'role': 'FIELD_WORKER'}
    )
    
    # Task counts
    total_tasks = models.PositiveIntegerField(default=0)
    completed_tasks = models.PositiveIntegerField(default=0)
    rejected_tasks = models.PositiveIntegerField(default=0)
    
    # Time metrics
    avg_completion_time = models.DurationField(blank=True, null=True)
    total_working_hours = models.FloatField(default=0.0)
    
    # Quality metrics
    avg_quality_rating = models.FloatField(default=0.0)
    quality_rating_count = models.PositiveIntegerField(default=0)
    
    # Distance metrics
    total_distance_traveled = models.FloatField(
        default=0.0,
        help_text='Distance in kilometers'
    )
    
    # Last activity
    last_active = models.DateTimeField(blank=True, null=True)
    
    # Performance score (calculated)
    performance_score = models.FloatField(default=0.0, help_text='0-100%')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Field Worker Performance')
        verbose_name_plural = _('Field Worker Performances')
        ordering = ['-performance_score']
    
    def __str__(self):
        return f"Performance: {self.worker.get_short_name()} ({self.performance_score}%)"
    
    def calculate_performance_score(self):
        """Calculate overall performance score."""
        if self.total_tasks == 0:
            self.performance_score = 0.0
            return self.performance_score
        
        # Completion rate (50% weight)
        completion_rate = (self.completed_tasks / self.total_tasks) * 100
        
        # Quality score (30% weight)
        if self.quality_rating_count == 0:
            quality_score = 0.0
        else:
            quality_score = self.avg_quality_rating * 20  # Convert 1-5 to 0-100
        
        # Efficiency score (20% weight)
        if self.avg_completion_time:
            # Assume 4 hours is ideal for most tasks
            ideal_hours = 4
            avg_hours = self.avg_completion_time.total_seconds() / 3600
            efficiency_score = max(0, 100 - (avg_hours - ideal_hours) * 25)
            efficiency_score = min(100, efficiency_score)
        else:
            efficiency_score = 50.0
        
        # Calculate weighted score
        self.performance_score = (completion_rate * 0.5) + (quality_score * 0.3) + (efficiency_score * 0.2)
        return self.performance_score


class FieldTaskChecklist(models.Model):
    """Checklist items for field tasks."""
    task = models.ForeignKey(
        FieldTask,
        on_delete=models.CASCADE,
        related_name='checklist_items'
    )
    
    item_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    is_required = models.BooleanField(default=True)
    
    is_completed = models.BooleanField(default=False)
    completed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='completed_checklist_items'
    )
    completed_at = models.DateTimeField(blank=True, null=True)
    
    notes = models.TextField(blank=True)
    
    order = models.PositiveSmallIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Field Task Checklist')
        verbose_name_plural = _('Field Task Checklists')
        ordering = ['order']
    
    def __str__(self):
        return f"{self.item_name} for {self.task.task_id}"


class FieldTaskChecklistTemplate(models.Model):
    """Template for field task checklists."""
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    
    work_type = models.CharField(
        max_length=100,
        blank=True,
        choices=[
            ('INSPECTION', 'Inspection'),
            ('REPAIR', 'Repair'),
            ('CLEANING', 'Cleaning'),
            ('INSTALLATION', 'Installation'),
            ('REMOVAL', 'Removal'),
            ('MAINTENANCE', 'Maintenance'),
            ('SURVEY', 'Survey'),
            ('OTHER', 'Other'),
        ]
    )
    
    items = models.JSONField(
        default=list,
        blank=True,
        help_text='List of checklist items with name, description, and is_required'
    )
    
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Field Task Checklist Template')
        verbose_name_plural = _('Field Task Checklist Templates')
        ordering = ['name']
    
    def __str__(self):
        return self.name
