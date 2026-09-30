"""
Views for the verification app.
"""
from rest_framework import permissions, viewsets

from .models import VerificationResult
from .serializers import VerificationResultSerializer


class VerificationResultViewSet(viewsets.ReadOnlyModelViewSet):
    """List / retrieve verification results.

    Admins and reviewers see everything; citizens and officials only see
    results for complaints they are participants of.
    """
    queryset = VerificationResult.objects.select_related(
        'complaint', 'human_reviewer'
    )
    serializer_class = VerificationResultSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = [
        'is_fully_verified', 'is_rejected',
        'ai_verification_passed', 'human_verification_passed'
    ]
    search_fields = ['complaint__complaint_id']

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_staff or user.role in ('ADMIN', 'REVIEWER'):
            return queryset
        from django.db.models import Q
        return queryset.filter(
            Q(complaint__citizen=user)
            | Q(complaint__assigned_official=user)
            | Q(complaint__assigned_field_worker=user)
        ).distinct()
