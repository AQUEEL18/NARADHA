"""
Admin configuration for the users app.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import CustomUser, Department, Jurisdiction


@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    """Admin for the custom user model."""
    list_display = (
        'email', 'get_short_name', 'role', 'department',
        'is_verified_user', 'is_staff', 'date_joined'
    )
    list_filter = ('role', 'is_verified_user', 'is_staff', 'department')
    search_fields = ('email', 'first_name', 'last_name', 'phone_number', 'anonymous_id')
    ordering = ('-date_joined',)
    filter_horizontal = ('groups', 'user_permissions')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {
            'fields': (
                'first_name', 'last_name', 'phone_number', 'date_of_birth',
                'address', 'bio', 'avatar', 'anonymous_id'
            )
        }),
        ('Role & organization', {
            'fields': ('role', 'department', 'jurisdiction', 'is_verified_user')
        }),
        ('Preferences', {
            'fields': (
                'preferred_language', 'notify_email', 'notify_sms',
                'notify_push', 'show_anonymous_only'
            )
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'role'),
        }),
    )


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'head', 'default_sla_days', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'code', 'email')
    prepopulated_fields = {}


@admin.register(Jurisdiction)
class JurisdictionAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'jurisdiction_type', 'parent', 'is_active')
    list_filter = ('jurisdiction_type', 'is_active')
    search_fields = ('name', 'code')
