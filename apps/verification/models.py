"""
Verification models for NARADHA application.

Tracks the AI + human verification lifecycle of a complaint in one place.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.complaints.models import Complaint
from apps.users.models import CustomUser


class VerificationResult(models.Model):
    """Combined AI and human verification outcome for a complaint."""
    complaint = models.OneToOneField(
        Complaint,
        on_delete=models.CASCADE,
        related_name='verification_result'
    )

    # AI verification
    ai_verification_passed = models.BooleanField(default=False)
    ai_confidence_score = models.FloatField(
        default=0.0,
        help_text='Average AI confidence score across proofs (0-100%)'
    )
    ai_verified_at = models.DateTimeField(blank=True, null=True)
    ai_notes = models.TextField(blank=True)

    # Human verification
    human_verification_passed = models.BooleanField(default=False)
    human_reviewer = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='verification_results_reviewed',
        limit_choices_to={'role': 'REVIEWER'}
    )
    human_verification_notes = models.TextField(blank=True)
    human_verified_at = models.DateTimeField(blank=True, null=True)

    # Final outcome
    is_fully_verified = models.BooleanField(default=False)
    is_rejected = models.BooleanField(default=False)
    rejection_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Verification Result')
        verbose_name_plural = _('Verification Results')
        ordering = ['-updated_at']

    def __str__(self):
        return f"Verification for {self.complaint.complaint_id}"

    def update_final_status(self):
        """Recalculate the combined verification outcome."""
        self.is_fully_verified = self.ai_verification_passed and self.human_verification_passed
        self.save(update_fields=['is_fully_verified', 'updated_at'])
        return self.is_fully_verified


class VerificationAuditLog(models.Model):
    """Audit trail of verification state transitions."""
    verification = models.ForeignKey(
        VerificationResult,
        on_delete=models.CASCADE,
        related_name='audit_logs'
    )

    action = models.CharField(
        max_length=50,
        choices=[
            ('AI_VERIFICATION', 'AI Verification'),
            ('HUMAN_VERIFICATION', 'Human Verification'),
            ('REJECTION', 'Rejection'),
            ('RESET', 'Reset'),
        ]
    )
    performed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='verification_actions'
    )
    is_ai_action = models.BooleanField(default=False)

    details = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Verification Audit Log')
        verbose_name_plural = _('Verification Audit Logs')
        ordering = ['-created_at']

    def __str__(self):
        actor = 'AI' if self.is_ai_action else (self.performed_by or 'System')
        return f"{self.action} on {self.verification} by {actor}"
