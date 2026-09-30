"""
Serializers for user, department, and jurisdiction models.
"""
from rest_framework import serializers

from .models import CustomUser, Department, Jurisdiction


class DepartmentSerializer(serializers.ModelSerializer):
    """Serializer for the Department model."""

    member_count = serializers.SerializerMethodField()
    head_name = serializers.CharField(source='head.get_short_name', read_only=True, default=None)

    class Meta:
        model = Department
        fields = [
            'id', 'name', 'code', 'description', 'parent_department',
            'email', 'phone', 'address', 'head', 'head_name',
            'default_sla_days', 'is_active', 'member_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_member_count(self, obj):
        return obj.members.count()


class JurisdictionSerializer(serializers.ModelSerializer):
    """Serializer for the Jurisdiction model."""

    parent_name = serializers.CharField(source='parent.name', read_only=True, default=None)
    full_path = serializers.CharField(read_only=True)

    class Meta:
        model = Jurisdiction
        fields = [
            'id', 'name', 'code', 'jurisdiction_type', 'parent', 'parent_name',
            'full_path', 'latitude', 'longitude', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserSerializer(serializers.ModelSerializer):
    """Public serializer for users (used across other apps)."""

    department = DepartmentSerializer(read_only=True)
    jurisdiction = JurisdictionSerializer(read_only=True)
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name',
            'display_name', 'get_short_name', 'role', 'phone_number',
            'avatar', 'bio', 'preferred_language', 'department',
            'jurisdiction', 'anonymous_id', 'notify_email', 'notify_sms',
            'notify_push', 'is_verified_user', 'date_joined'
        ]
        read_only_fields = ['id', 'email', 'role', 'anonymous_id', 'date_joined']

    def get_display_name(self, obj):
        """Respect the user's anonymous-only preference."""
        request = self.context.get('request')
        if obj.show_anonymous_only and request and request.user != obj:
            return obj.get_anonymous_id()
        return obj.get_short_name()


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for creating new accounts."""

    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        min_length=8
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model = CustomUser
        fields = [
            'email', 'first_name', 'last_name', 'phone_number',
            'password', 'password_confirm', 'role',
            'jurisdiction', 'preferred_language'
        ]
        extra_kwargs = {
            'first_name': {'required': True},
        }

    def validate_role(self, value):
        """Only citizens and field workers may self-register."""
        allowed = {CustomUser.Role.CITIZEN, CustomUser.Role.FIELD_WORKER}
        if value not in allowed:
            raise serializers.ValidationError(
                'This role cannot be self-registered. Contact an administrator.'
            )
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs.pop('password_confirm'):
            raise serializers.ValidationError({'password_confirm': 'Passwords do not match.'})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = CustomUser(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserDetailSerializer(serializers.ModelSerializer):
    """Private serializer for a user viewing/updating their own profile."""

    department = DepartmentSerializer(read_only=True)
    jurisdiction = JurisdictionSerializer(read_only=True)

    class Meta:
        model = CustomUser
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name', 'role',
            'phone_number', 'avatar', 'date_of_birth', 'address', 'bio',
            'preferred_language', 'department', 'jurisdiction',
            'anonymous_id', 'notify_email', 'notify_sms', 'notify_push',
            'show_anonymous_only', 'is_verified_user', 'date_joined'
        ]
        read_only_fields = [
            'id', 'email', 'role', 'anonymous_id',
            'is_verified_user', 'date_joined'
        ]


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change."""

    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, min_length=8)

    def validate_old_password(self, value):
        user = self.context.get('request').user
        if not user.check_password(value):
            raise serializers.ValidationError('Current password is incorrect.')
        return value

    def save(self, **kwargs):
        user = self.context.get('request').user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user
