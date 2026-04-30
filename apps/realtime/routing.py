"""
LMS Enterprise - WebSocket URL Routing
"""
from django.urls import re_path
from realtime.consumers import (
    NotificationConsumer,
    LiveClassConsumer,
    SystemBroadcastConsumer,
)

websocket_urlpatterns = [
    re_path(r'ws/notifications/$', NotificationConsumer.as_asgi()),
    re_path(r'ws/class/(?P<class_id>[0-9a-f-]+)/$', LiveClassConsumer.as_asgi()),
    re_path(r'ws/broadcast/$', SystemBroadcastConsumer.as_asgi()),
]
