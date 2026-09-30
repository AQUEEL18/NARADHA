"""
WebSocket URL routing for the messaging app.
"""
from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(
        r'ws/complaints/(?P<complaint_id>[\w-]+)/chat/$',
        consumers.MessageConsumer.as_asgi(),
        name='complaint-chat'
    ),
    re_path(
        r'ws/notifications/$',
        consumers.NotificationConsumer.as_asgi(),
        name='notifications'
    ),
]
