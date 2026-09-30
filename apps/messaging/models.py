"""
Messaging models for NARADHA application.

Handles conversation threads attached to complaints, direct messages
between participants, and in-app notifications.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.complaints.models import Complaint
from apps.users.models import CustomUser


class Conversation(models.Model):
    """A message thread attached to a complaint."""
    complaint = models.OneToOneField(
        Complaint,
        on_delete=models.CASCADE,
        related_name='conversation'
    )

    subject = models.CharField(max_length=255, blank=True)

    participants = models.ManyToManyField(
        CustomUser,
        related_name='conversations',
        blank=True
    )

    last_message = models.ForeignKey(
        'Message',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='+'
    )

    # Unread counters maintained by update_unread_counts()
    citizen_unread_count = models.PositiveIntegerField(default=0)
    official_unread_count = models.PositiveIntegerField(default=0)

    is_archived = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Conversation')
        verbose_name_plural = _('Conversations')
        ordering = ['-updated_at']

    def __str__(self):
        return f"Conversation for {self.complaint.complaint_id}"

    def update_unread_counts(self):
        """Recalculate unread message counts for citizen and official."""
        def unread_for(user):
            if user is None:
                return 0
            return self.messages.filter(recipient=user, is_read=False).count()

        self.citizen_unread_count = unread_for(self.complaint.citizen)
        self.official_unread_count = unread_for(self.complaint.assigned_official)
        self.save(update_fields=[
            'citizen_unread_count', 'official_unread_count', 'updated_at'
        ])


class Message(models.Model):
    """A single message inside a complaint conversation."""
    MessageType = models.TextChoices('MessageType', [
        ('TEXT', 'Text'),
        ('IMAGE', 'Image'),
        ('DOCUMENT', 'Document'),
        ('SYSTEM', 'System'),
    ])

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
        blank=True,
        null=True
    )
    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name='messages'
    )

    sender = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='sent_messages'
    )
    recipient = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='received_messages'
    )

    content = models.TextField()
    message_type = models.CharField(
        max_length=20,
        choices=MessageType.choices,
        default=MessageType.TEXT
    )
    attachment = models.FileField(upload_to='messages/attachments/', blank=True, null=True)

    # Delivery state
    is_delivered = models.BooleanField(default=False)
    delivered_at = models.DateTimeField(blank=True, null=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(blank=True, null=True)

    # Soft delete / moderation
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(blank=True, null=True)

    # Auto-translation support
    original_language = models.CharField(max_length=10, blank=True)
    translated_content = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Message')
        verbose_name_plural = _('Messages')
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['complaint', 'created_at']),
            models.Index(fields=['recipient', 'is_read']),
        ]

    def __str__(self):
        sender = self.sender.get_short_name() if self.sender else 'System'
        return f"Message {self.id} on {self.complaint.complaint_id} from {sender}"

    def mark_delivered(self):
        if not self.is_delivered:
            self.is_delivered = True
            self.delivered_at = timezone.now()
            self.save(update_fields=['is_delivered', 'delivered_at'])

    def mark_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


class Notification(models.Model):
    """In-app notification for a user."""
    NotificationType = models.TextChoices('NotificationType', [
        ('NEW_MESSAGE', 'New Message'),
        ('STATUS_CHANGE', 'Status Change'),
        ('ESCALATION', 'Escalation'),
        ('SLA_BREACH', 'SLA Breach'),
        ('NEW_COMPLAINT', 'New Complaint'),
        ('VERIFICATION_RESULT', 'Verification Result'),
        ('FIELD_TASK', 'Field Task'),
        ('RESOLUTION', 'Resolution'),
        ('SYSTEM', 'System'),
    ])

    Priority = models.TextChoices('Priority', [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('URGENT', 'Urgent'),
    ])

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='notifications'
    )

    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.choices,
        default=NotificationType.SYSTEM
    )
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM
    )

    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)

    # Related objects
    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='notifications'
    )
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='notifications'
    )

    # Delivery channels
    delivered_via_app = models.BooleanField(default=False)
    delivered_via_email = models.BooleanField(default=False)
    delivered_via_sms = models.BooleanField(default=False)
    delivered_at = models.DateTimeField(blank=True, null=True)

    # Read state
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(blank=True, null=True)

    # Optional deep link
    action_url = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"{self.notification_type}: {self.title}"

    def mark_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])

    def mark_delivered(self):
        if not self.delivered_via_app:
            self.delivered_via_app = True
            self.delivered_at = timezone.now()
            self.save(update_fields=['delivered_via_app', 'delivered_at'])
