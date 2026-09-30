"""
URLs for users app: registration, profile, and authentication.
"""
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.urls import path
from rest_framework.views import APIView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from .models import CustomUser, Department, Jurisdiction
from .serializers import (
    ChangePasswordSerializer,
    DepartmentSerializer,
    JurisdictionSerializer,
    UserDetailSerializer,
    UserRegistrationSerializer,
    UserSerializer,
)


class RegisterView(generics.CreateAPIView):
    """Public endpoint to create a new account."""
    queryset = CustomUser.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]


class ProfileView(generics.RetrieveUpdateAPIView):
    """Get or update the authenticated user's profile."""
    serializer_class = UserDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    """Change the authenticated user's password."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'message': 'Password changed successfully.'})


class DepartmentListView(generics.ListAPIView):
    """List all active departments."""
    queryset = Department.objects.filter(is_active=True)
    serializer_class = DepartmentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class JurisdictionListView(generics.ListAPIView):
    """List all active jurisdictions."""
    queryset = Jurisdiction.objects.filter(is_active=True)
    serializer_class = JurisdictionSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


urlpatterns = [
    # JWT auth
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),

    # Account management
    path('register/', RegisterView.as_view(), name='register'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),

    # Reference data
    path('departments/', DepartmentListView.as_view(), name='department-list'),
    path('jurisdictions/', JurisdictionListView.as_view(), name='jurisdiction-list'),
]
