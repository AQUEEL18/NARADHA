"""
User and organizational models for NARADHA application.

NARADHA is a civic complaint management platform. Users are grouped by
role: citizens file complaints, reviewers verify evidence, officials and
ministers resolve them, and field workers perform on-site tasks.
"""
import uuid

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """Custom user manager where email is the unique identifier."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', CustomUser.Role.ADMIN)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


class Department(models.Model):
    """Government department responsible for complaint resolution."""
    name = models.CharField(max_length=200, unique=True)
    code = models.CharField(max_length=20, unique=True, help_text='Short unique code (e.g., PWD)')
    description = models.TextField(blank=True)

    # Hierarchy
    parent_department = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='sub_departments',
        help_text='Parent department in the org hierarchy'
    )

    # Contact details
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)

    # Head of department
    head = models.ForeignKey(
        'CustomUser',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='departments_led',
        limit_choices_to={'role__in': ['OFFICIAL', 'MINISTER']}
    )

    # SLA configuration
    default_sla_days = models.PositiveSmallIntegerField(
        default=14,
        validators=[MinValueValidator(1), MaxValueValidator(365)],
        help_text='Default SLA in days for complaints assigned to this department'
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Department')
        verbose_name_plural = _('Departments')
        ordering = ['name']

    def __str__(self):
        return self.name


class Jurisdiction(models.Model):
    """Geographic jurisdiction (state / district / city / ward)."""
    JurisdictionType = models.TextChoices('JurisdictionType', [
        ('STATE', 'State'),
        ('DISTRICT', 'District'),
        ('CITY', 'City'),
        ('WARD', 'Ward'),
    ])

    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    jurisdiction_type = models.CharField(
        max_length=20,
        choices=JurisdictionType.choices,
        default=JurisdictionType.DISTRICT
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='children',
        help_text='Parent jurisdiction'
    )

    # Boundary
    latitude = models.DecimalField(max_digits=10, decimal_places=8, blank=True, null=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, blank=True, null=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Jurisdiction')
        verbose_name_plural = _('Jurisdictions')
        ordering = ['name']
        unique_together = [['name', 'parent']]

    def __str__(self):
        return self.name

    def get_full_path(self):
        """Get the full hierarchical path (e.g., 'State > District > City')."""
        path = [self.name]
        current = self.parent
        while current:
            path.append(current.name)
            current = current.parent
        return ' > '.join(reversed(path))


class CustomUser(AbstractUser):
    """Custom user model for NARADHA with role-based access."""

    class Role(models.TextChoices):
        CITIZEN = 'CITIZEN', _('Citizen')
        REVIEWER = 'REVIEWER', _('Reviewer')
        OFFICIAL = 'OFFICIAL', _('Official')
        MINISTER = 'MINISTER', _('Minister')
        FIELD_WORKER = 'FIELD_WORKER', _('Field Worker')
        ADMIN = 'ADMIN', _('Administrator')

    # Email is the login identifier
    username = models.CharField(
        _('username'),
        max_length=150,
        unique=False,
        blank=True,
        null=True,
        help_text=_('Optional. Used for display purposes.')
    )
    email = models.EmailField(_('email address'), unique=True)

    # Role-based access
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CITIZEN,
        db_index=True
    )

    # Profile
    phone_number = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    address = models.TextField(blank=True)
    bio = models.TextField(blank=True)

    # Preferred language for notifications and UI
    preferred_language = models.CharField(max_length=10, default='en')

    # Organization
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='members',
        help_text='Department (for officials, ministers, reviewers, field workers)'
    )
    jurisdiction = models.ForeignKey(
        Jurisdiction,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='residents',
        help_text='Home jurisdiction (mainly for citizens)'
    )

    # Job title (for officials / ministers)
    designation = models.CharField(max_length=100, blank=True)

    # Last known GPS position (updated by field workers / mobile clients)
    current_latitude = models.DecimalField(
        max_digits=10, decimal_places=8, blank=True, null=True
    )
    current_longitude = models.DecimalField(
        max_digits=11, decimal_places=8, blank=True, null=True
    )

    # Anonymous identity used when posting publicly
    anonymous_id = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        editable=False,
        help_text='Public anonymous ID (e.g., AN-123456)'
    )

    # Notification preferences
    notify_email = models.BooleanField(default=True)
    notify_sms = models.BooleanField(default=False)
    notify_push = models.BooleanField(default=True)

    # Privacy
    show_anonymous_only = models.BooleanField(
        default=False,
        help_text='Always display anonymous ID instead of name on public pages'
    )

    # Verification of the account itself (e.g., field workers / officials)
    is_verified_user = models.BooleanField(default=False)
    verified_at = models.DateTimeField(blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ['-date_joined']

    def save(self, *args, **kwargs):
        if not self.anonymous_id:
            self.anonymous_id = f"AN-{uuid.uuid4().int % 1000000:06d}"
        if not self.username:
            self.username = self.email.split('@')[0] + '-' + self.anonymous_id.split('-')[1]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.get_short_name()

    def get_short_name(self):
        """Return a display-friendly short name."""
        if self.first_name:
            return self.first_name
        return self.email.split('@')[0]

    def get_full_name_or_email(self):
        full = self.get_full_name()
        return full if full.strip() else self.email

    def get_anonymous_id(self):
        """Get the anonymous public ID for this user."""
        return self.anonymous_id

    # ------------------------------------------------------------------
    # Role helpers
    # NOTE: role checks are callable methods (e.g. user.is_official());
    # is_admin is a property matching the rest of the codebase.
    # ------------------------------------------------------------------
    def is_citizen(self):
        return self.role == self.Role.CITIZEN

    def is_reviewer(self):
        return self.role == self.Role.REVIEWER

    def is_official(self):
        return self.role in (self.Role.OFFICIAL, self.Role.MINISTER)

    def is_minister(self):
        return self.role == self.Role.MINISTER

    def is_field_worker(self):
        return self.role == self.Role.FIELD_WORKER

    def is_government(self):
        """Any government-side role."""
        return self.role in {
            self.Role.REVIEWER,
            self.Role.OFFICIAL,
            self.Role.MINISTER,
            self.Role.FIELD_WORKER,
            self.Role.ADMIN,
        }

    @property
    def is_admin(self):
        """Administrator flag (role-based or Django staff)."""
        return self.role == self.Role.ADMIN or self.is_staff

    # ------------------------------------------------------------------
    # Performance helpers (derived from assigned complaints)
    # ------------------------------------------------------------------
    @property
    def total_complaints_handled(self):
        """Number of complaints currently assigned to this user."""
        if not hasattr(self, 'complaints_assigned'):
            return 0
        return self.complaints_assigned.filter(is_deleted=False).count()

    @property
    def response_rate(self):
        """Percentage of assigned complaints that have progressed past 'VERIFIED'."""
        total = self.total_complaints_handled
        if total == 0:
            return 0.0
        acted = self.complaints_assigned.filter(
            is_deleted=False
        ).exclude(status__in=['SUBMITTED', 'VERIFIED', 'NOTIFIED_TO_OFFICIAL']).count()
        return round((acted / total) * 100, 2)

    @property
    def avg_response_time(self):
        """Average first-action time (returns None when no data)."""
        # Kept as a lightweight placeholder; the OfficialPerformance
        # model holds the authoritative persisted metrics.
        performance = getattr(self, 'official_performance', None) if self.pk else None
        return performance.avg_response_time if performance else None

    def get_performance_score(self):
        """Return the persisted performance score (0-100) when available."""
        performance = getattr(self, 'official_performance', None) if self.pk else None
        if performance is None:
            performance = getattr(self, 'field_performance', None) if self.pk else None
        return performance.performance_score if performance else 0.0
