"""
Complaint models for NARADHA application.
"""
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.users.models import CustomUser, Department, Jurisdiction


class ComplaintCategory(models.Model):
    """Categories for complaints."""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)
    description = models.TextField(blank=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='categories'
    )
    icon = models.CharField(max_length=50, blank=True, help_text='Font Awesome icon class')
    color = models.CharField(max_length=20, default='#3B82F6', help_text='Hex color code')
    is_active = models.BooleanField(default=True)
    priority_weight = models.PositiveSmallIntegerField(
        default=1,
        help_text='Weight for priority calculation (1-5)'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Complaint Category')
        verbose_name_plural = _('Complaint Categories')
        ordering = ['name']
    
    def __str__(self):
        return self.name


class ComplaintStatus(models.TextChoices):
    """Status choices for complaints."""
    DRAFT = 'DRAFT', _('Draft')
    SUBMITTED = 'SUBMITTED', _('Submitted')
    PROOF_RECEIVED = 'PROOF_RECEIVED', _('Proof Received')
    AWAITING_HUMAN_REVIEW = 'AWAITING_HUMAN_REVIEW', _('Awaiting Human Review')
    VERIFIED = 'VERIFIED', _('Verified')
    REJECTED = 'REJECTED', _('Rejected')
    REQUEST_MORE_INFO = 'REQUEST_MORE_INFO', _('Request More Info')
    NOTIFIED_TO_OFFICIAL = 'NOTIFIED_TO_OFFICIAL', _('Notified to Official')
    COMMITMENT_PUBLISHED = 'COMMITMENT_PUBLISHED', _('Commitment Published')
    IN_PROGRESS = 'IN_PROGRESS', _('In Progress')
    AWAITING_FIELD_WORK = 'AWAITING_FIELD_WORK', _('Awaiting Field Work')
    FIELD_WORK_COMPLETED = 'FIELD_WORK_COMPLETED', _('Field Work Completed')
    AWAITING_CITIZEN_VERIFICATION = 'AWAITING_CITIZEN_VERIFICATION', _('Awaiting Citizen Verification')
    RESOLVED = 'RESOLVED', _('Resolved')
    REOPENED = 'REOPENED', _('Reopened')
    ESCALATED = 'ESCALATED', _('Escalated')


class ComplaintPriority(models.TextChoices):
    """Priority levels for complaints."""
    LOW = 'LOW', _('Low')
    MEDIUM = 'MEDIUM', _('Medium')
    HIGH = 'HIGH', _('High')
    CRITICAL = 'CRITICAL', _('Critical')


class Complaint(models.Model):
    """Main complaint model."""
    # Unique identifier
    complaint_id = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        help_text='Unique complaint ID (e.g., CR-987654)'
    )
    
    # Citizen who filed the complaint
    citizen = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        related_name='complaints_filed',
        null=True,
        blank=True,
        limit_choices_to={'role': 'CITIZEN'}
    )
    
    # Category
    category = models.ForeignKey(
        ComplaintCategory,
        on_delete=models.SET_NULL,
        related_name='complaints',
        null=True,
        blank=True
    )
    
    # Title and description
    title = models.CharField(max_length=200, blank=True)
    description = models.TextField()
    
    # Location
    location_address = models.TextField()
    latitude = models.DecimalField(max_digits=10, decimal_places=8, blank=True, null=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, blank=True, null=True)
    jurisdiction = models.ForeignKey(
        Jurisdiction,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='complaints'
    )
    
    # Status and workflow
    status = models.CharField(
        max_length=50,
        choices=ComplaintStatus.choices,
        default=ComplaintStatus.DRAFT
    )
    
    priority = models.CharField(
        max_length=20,
        choices=ComplaintPriority.choices,
        default=ComplaintPriority.MEDIUM
    )
    
    priority_score = models.PositiveSmallIntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text='Priority score from 1-10'
    )
    
    # AI Verification
    ai_confidence_score = models.FloatField(
        default=0.0,
        help_text='AI confidence score (0-100%)'
    )
    ai_verification_status = models.BooleanField(default=False)
    ai_verification_notes = models.TextField(blank=True)
    
    # Human Verification
    human_reviewer = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='complaints_reviewed',
        limit_choices_to={'role': 'REVIEWER'}
    )
    human_verification_status = models.BooleanField(default=False)
    human_verification_notes = models.TextField(blank=True)
    
    # Assignment
    assigned_official = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='complaints_assigned',
        limit_choices_to={'role__in': ['OFFICIAL', 'MINISTER']}
    )
    assigned_department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='complaints_assigned'
    )
    
    # Commitment
    commitment_date = models.DateTimeField(blank=True, null=True)
    commitment_visible = models.BooleanField(default=False)
    
    # Field Work
    assigned_field_worker = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='field_tasks',
        limit_choices_to={'role': 'FIELD_WORKER'}
    )
    
    # Resolution
    resolution_description = models.TextField(blank=True)
    resolution_date = models.DateTimeField(blank=True, null=True)
    
    # Citizen Verification
    citizen_verified = models.BooleanField(default=False)
    citizen_verification_date = models.DateTimeField(blank=True, null=True)
    citizen_ratings = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    citizen_comments = models.TextField(blank=True)
    
    # SLA Tracking
    sla_deadline = models.DateTimeField(blank=True, null=True)
    sla_breached = models.BooleanField(default=False)
    days_overdue = models.PositiveIntegerField(default=0)
    
    # Escalation
    escalation_level = models.PositiveSmallIntegerField(
        default=0,
        help_text='0=No escalation, 1=Supervisor, 2=Department Head, 3=Minister, 4=State Level'
    )
    escalated_to = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='escalated_complaints'
    )
    escalation_date = models.DateTimeField(blank=True, null=True)
    escalation_reason = models.TextField(blank=True)
    
    # Communication
    allow_public_communication = models.BooleanField(default=True)
    
    # Metadata
    source = models.CharField(
        max_length=20,
        choices=[
            ('WEB', 'Web'),
            ('MOBILE', 'Mobile'),
            ('VOICE', 'Voice'),
            ('EMAIL', 'Email'),
        ],
        default='WEB'
    )
    
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    device_info = models.JSONField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(blank=True, null=True)
    
    # Soft delete
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(blank=True, null=True)
    deleted_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='deleted_complaints'
    )
    
    class Meta:
        verbose_name = _('Complaint')
        verbose_name_plural = _('Complaints')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
            models.Index(fields=['jurisdiction']),
            models.Index(fields=['assigned_official']),
            models.Index(fields=['complaint_id']),
        ]
    
    def __str__(self):
        return f"{self.complaint_id} - {self.title or self.description[:50]}"
    
    def save(self, *args, **kwargs):
        """Override save to generate complaint_id if not set."""
        if not self.complaint_id:
            from django.db.models import Max
            last_complaint = Complaint.objects.aggregate(Max('id'))
            last_id = last_complaint['id__max'] or 0
            self.complaint_id = f"CR-{100000 + last_id + 1}"
        
        # Update SLA status
        if self.sla_deadline and timezone.now() > self.sla_deadline:
            self.sla_breached = True
            self.days_overdue = (timezone.now() - self.sla_deadline).days
        
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('complaint_detail', args=[str(self.complaint_id)])
    
    def get_status_display_with_icon(self):
        """Get status with appropriate icon."""
        status_icons = {
            ComplaintStatus.DRAFT: '📝',
            ComplaintStatus.SUBMITTED: '📤',
            ComplaintStatus.PROOF_RECEIVED: '🔍',
            ComplaintStatus.AWAITING_HUMAN_REVIEW: '⏳',
            ComplaintStatus.VERIFIED: '✅',
            ComplaintStatus.REJECTED: '❌',
            ComplaintStatus.REQUEST_MORE_INFO: '🔄',
            ComplaintStatus.NOTIFIED_TO_OFFICIAL: '📬',
            ComplaintStatus.COMMITMENT_PUBLISHED: '🤝',
            ComplaintStatus.IN_PROGRESS: '🛠️',
            ComplaintStatus.AWAITING_FIELD_WORK: '🚧',
            ComplaintStatus.FIELD_WORK_COMPLETED: '✨',
            ComplaintStatus.AWAITING_CITIZEN_VERIFICATION: '👀',
            ComplaintStatus.RESOLVED: '🎉',
            ComplaintStatus.REOPENED: '🔄',
            ComplaintStatus.ESCALATED: '🚨',
        }
        return f"{status_icons.get(self.status, '❓')} {self.get_status_display()}"
    
    def get_priority_color(self):
        """Get color for priority badge."""
        colors = {
            ComplaintPriority.LOW: 'bg-blue-100 text-blue-800',
            ComplaintPriority.MEDIUM: 'bg-yellow-100 text-yellow-800',
            ComplaintPriority.HIGH: 'bg-orange-100 text-orange-800',
            ComplaintPriority.CRITICAL: 'bg-red-100 text-red-800',
        }
        return colors.get(self.priority, 'bg-gray-100 text-gray-800')
    
    def get_priority_badge(self):
        """Get HTML badge for priority.

        Shows an honest "Pending" badge until the AI scoring engine has
        actually computed a priority, so the UI never lies about state.
        """
        if not self.is_priority_computed and self.status in (
            ComplaintStatus.DRAFT, ComplaintStatus.SUBMITTED,
            ComplaintStatus.PROOF_RECEIVED,
        ):
            return ('<span class="px-2 py-1 rounded-full text-xs font-semibold '
                    'bg-gray-100 text-gray-500">Priority Pending</span>')
        color = self.get_priority_color()
        return f'<span class="px-2 py-1 rounded-full text-xs font-semibold {color}">{self.get_priority_display()}</span>'
    
    def get_status_badge(self):
        """Get HTML badge for status."""
        status_colors = {
            ComplaintStatus.DRAFT: 'bg-gray-100 text-gray-800',
            ComplaintStatus.SUBMITTED: 'bg-blue-100 text-blue-800',
            ComplaintStatus.PROOF_RECEIVED: 'bg-indigo-100 text-indigo-800',
            ComplaintStatus.AWAITING_HUMAN_REVIEW: 'bg-purple-100 text-purple-800',
            ComplaintStatus.VERIFIED: 'bg-green-100 text-green-800',
            ComplaintStatus.REJECTED: 'bg-red-100 text-red-800',
            ComplaintStatus.REQUEST_MORE_INFO: 'bg-yellow-100 text-yellow-800',
            ComplaintStatus.NOTIFIED_TO_OFFICIAL: 'bg-cyan-100 text-cyan-800',
            ComplaintStatus.COMMITMENT_PUBLISHED: 'bg-teal-100 text-teal-800',
            ComplaintStatus.IN_PROGRESS: 'bg-blue-100 text-blue-800',
            ComplaintStatus.AWAITING_FIELD_WORK: 'bg-orange-100 text-orange-800',
            ComplaintStatus.FIELD_WORK_COMPLETED: 'bg-lime-100 text-lime-800',
            ComplaintStatus.AWAITING_CITIZEN_VERIFICATION: 'bg-amber-100 text-amber-800',
            ComplaintStatus.RESOLVED: 'bg-emerald-100 text-emerald-800',
            ComplaintStatus.REOPENED: 'bg-sky-100 text-sky-800',
            ComplaintStatus.ESCALATED: 'bg-rose-100 text-rose-800',
        }
        color = status_colors.get(self.status, 'bg-gray-100 text-gray-800')
        return f'<span class="px-2 py-1 rounded-full text-xs font-semibold {color}">{self.get_status_display()}</span>'
    
    def get_citizen_anonymous_id(self):
        """Get anonymous ID for citizen."""
        if self.citizen:
            return self.citizen.get_anonymous_id()
        return 'Anonymous'
    
    def get_resolution_time(self):
        """Calculate resolution time in days."""
        if self.submitted_at and self.resolution_date:
            delta = self.resolution_date - self.submitted_at
            return delta.days
        return None
    
    def is_overdue(self):
        """Check if complaint is overdue."""
        if self.sla_deadline:
            return timezone.now() > self.sla_deadline
        return False
    
    def get_workflow_step(self):
        """Get current workflow step (1-10)."""
        workflow_steps = {
            ComplaintStatus.DRAFT: 0,
            ComplaintStatus.SUBMITTED: 1,
            ComplaintStatus.PROOF_RECEIVED: 2,
            ComplaintStatus.AWAITING_HUMAN_REVIEW: 2,
            ComplaintStatus.VERIFIED: 3,
            ComplaintStatus.REJECTED: -1,
            ComplaintStatus.REQUEST_MORE_INFO: 2,
            ComplaintStatus.NOTIFIED_TO_OFFICIAL: 4,
            ComplaintStatus.COMMITMENT_PUBLISHED: 5,
            ComplaintStatus.IN_PROGRESS: 6,
            ComplaintStatus.AWAITING_FIELD_WORK: 6,
            ComplaintStatus.FIELD_WORK_COMPLETED: 7,
            ComplaintStatus.AWAITING_CITIZEN_VERIFICATION: 8,
            ComplaintStatus.RESOLVED: 9,
            ComplaintStatus.REOPENED: 5,
            ComplaintStatus.ESCALATED: 10,
        }
        return workflow_steps.get(self.status, 0)
    
    def get_workflow_progress(self):
        """Get workflow progress percentage."""
        step = self.get_workflow_step()
        if step <= 0:
            return 0
        return min(100, step * 10)
    
    # ------------------------------------------------------------------
    # AI / scoring state helpers (power the honest status UI)
    # ------------------------------------------------------------------
    @property
    def is_priority_computed(self):
        """True once the AI priority scoring engine has run for this complaint."""
        from apps.ai_services.models import PriorityScoringResult
        return PriorityScoringResult.objects.filter(complaint=self).exists()
    
    @property
    def ai_state(self):
        """AI verification state: PENDING (no evidence), PROCESSING, DONE."""
        if self.ai_verification_status:
            return 'DONE'
        if self.status == ComplaintStatus.SUBMITTED and self.proofs.exists():
            return 'PROCESSING'
        return 'PENDING'
    
    def get_assigned_official_display_name(self):
        """Official short name + department, used on citizen-facing pages."""
        if not self.assigned_official:
            return None
        name = self.assigned_official.get_short_name()
        if self.assigned_department:
            return f'{name} ({self.assigned_department.name})'
        return name
    
    # ------------------------------------------------------------------
    # Immutable audit trail (append-only status history)
    # ------------------------------------------------------------------
    def record_status_change(self, new_status, changed_by=None, notes=''):
        """Append an entry to the status history log (no status change)."""
        return ComplaintHistory.objects.create(
            complaint=self,
            previous_status=self.status if new_status != self.status else self.status,
            new_status=new_status,
            changed_by=changed_by,
            notes=notes or '',
        )
    
    def transition(self, new_status, changed_by=None, notes=''):
        """Change status, persist it, and write an immutable history entry."""
        if new_status == self.status:
            return None
        entry = ComplaintHistory.objects.create(
            complaint=self,
            previous_status=self.status,
            new_status=new_status,
            changed_by=changed_by,
            notes=notes or '',
        )
        self.status = new_status
        self.save(update_fields=['status', 'updated_at'])
        return entry


class ComplaintProof(models.Model):
    """Proof/evidence attached to complaints."""
    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name='proofs'
    )
    
    proof_type = models.CharField(
        max_length=20,
        choices=[
            ('PHOTO', 'Photo'),
            ('VIDEO', 'Video'),
            ('DOCUMENT', 'Document'),
            ('AUDIO', 'Audio'),
        ]
    )
    
    file = models.FileField(upload_to='complaints/proofs/')
    thumbnail = models.ImageField(upload_to='complaints/thumbnails/', blank=True, null=True)
    
    # Metadata
    file_size = models.PositiveIntegerField(help_text='File size in bytes')
    file_type = models.CharField(max_length=100, blank=True)
    duration = models.FloatField(blank=True, null=True, help_text='Duration in seconds for videos/audio')
    
    # GPS Metadata (extracted from file)
    gps_latitude = models.DecimalField(max_digits=10, decimal_places=8, blank=True, null=True)
    gps_longitude = models.DecimalField(max_digits=11, decimal_places=8, blank=True, null=True)
    gps_accuracy = models.FloatField(blank=True, null=True, help_text='GPS accuracy in meters')
    
    # Camera Metadata
    camera_make = models.CharField(max_length=100, blank=True)
    camera_model = models.CharField(max_length=100, blank=True)
    capture_timestamp = models.DateTimeField(blank=True, null=True)
    
    # AI Analysis
    ai_analysis_complete = models.BooleanField(default=False)
    ai_authenticity_score = models.FloatField(default=0.0, help_text='0-100%')
    ai_relevance_score = models.FloatField(default=0.0, help_text='0-100%')
    ai_quality_score = models.FloatField(default=0.0, help_text='0-100%')
    ai_manipulation_detected = models.BooleanField(default=False)
    ai_manipulation_confidence = models.FloatField(default=0.0, help_text='0-100%')
    ai_notes = models.TextField(blank=True)
    
    # Human Review
    human_review_complete = models.BooleanField(default=False)
    human_reviewer = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='proofs_reviewed'
    )
    human_review_notes = models.TextField(blank=True)
    human_approved = models.BooleanField(default=False)
    
    # Proof type classification
    classified_type = models.CharField(max_length=100, blank=True)
    classification_confidence = models.FloatField(default=0.0, help_text='0-100%')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Complaint Proof')
        verbose_name_plural = _('Complaint Proofs')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Proof {self.id} for {self.complaint.complaint_id}"
    
    def save(self, *args, **kwargs):
        """Override save to extract metadata."""
        if self.file and not self.file_size:
            self.file_size = self.file.size
            # content_type only exists on uploaded files, not on raw File objects
            uploaded = getattr(self.file, 'file', None)
            self.file_type = getattr(uploaded, 'content_type', '') or ''

        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        if self.file:
            return self.file.url
        return ''
    
    def get_thumbnail_url(self):
        if self.thumbnail:
            return self.thumbnail.url
        return self.get_absolute_url()


class ComplaintHistory(models.Model):
    """History log for complaint status changes."""
    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name='history'
    )
    
    previous_status = models.CharField(
        max_length=50,
        choices=ComplaintStatus.choices,
        blank=True,
        null=True
    )
    
    new_status = models.CharField(
        max_length=50,
        choices=ComplaintStatus.choices
    )
    
    changed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='status_changes'
    )
    
    notes = models.TextField(blank=True)
    
    # Metadata
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('Complaint History')
        verbose_name_plural = _('Complaint Histories')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.complaint.complaint_id}: {self.previous_status or 'None'} → {self.new_status}"


class ComplaintEndorsement(models.Model):
    """Community endorsements for complaints."""
    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name='endorsements'
    )
    
    citizen = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='endorsed_complaints',
        limit_choices_to={'role': 'CITIZEN'}
    )
    
    # Endorsement can be anonymous
    is_anonymous = models.BooleanField(default=False)
    
    comments = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('Complaint Endorsement')
        verbose_name_plural = _('Complaint Endorsements')
        ordering = ['-created_at']
        unique_together = ['complaint', 'citizen']
    
    def __str__(self):
        if self.is_anonymous:
            return f"Anonymous endorsement for {self.complaint.complaint_id}"
        return f"{self.citizen.get_short_name()} endorsed {self.complaint.complaint_id}"
    
    def get_anonymous_id(self):
        """Get anonymous ID for endorser."""
        if self.is_anonymous:
            return self.citizen.get_anonymous_id()
        return None


class ComplaintTag(models.Model):
    """Tags for categorizing complaints."""
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=20, default='#6B7280', help_text='Hex color code')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Complaint Tag')
        verbose_name_plural = _('Complaint Tags')
        ordering = ['name']
    
    def __str__(self):
        return self.name


class ComplaintTagAssignment(models.Model):
    """Assignment of tags to complaints."""
    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name='tag_assignments'
    )
    
    tag = models.ForeignKey(
        ComplaintTag,
        on_delete=models.CASCADE,
        related_name='complaints'
    )
    
    assigned_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='assigned_tags'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('Complaint Tag Assignment')
        verbose_name_plural = _('Complaint Tag Assignments')
        unique_together = ['complaint', 'tag']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.tag.name} for {self.complaint.complaint_id}"
