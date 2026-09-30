"""
Admin configuration for the messaging app.
"""
from django.contrib import admin

from .models import Conversation, Message, Notification


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = (
        'complaint', 'subject', 'last_message', 'citizen_unread_count',
        'official_unread_count', 'is_archived', 'updated_at'
    )
    list_filter = ('is_archived',)
    search_fields = ('complaint__complaint_id', 'subject')
    filter_horizontal = ('participants',)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'complaint', 'sender', 'recipient', 'message_type',
        'is_delivered', 'is_read', 'is_deleted', 'created_at'
    )
    list_filter = ('message_type', 'is_delivered', 'is_read', 'is_deleted')
    search_fields = ('content', 'complaint__complaint_id')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'notification_type', 'priority', 'title',
        'complaint', 'is_read', 'delivered_via_app', 'created_at'
    )
    list_filter = ('notification_type', 'priority', 'is_read', 'delivered_via_app')
    search_fields = ('title', 'body', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
