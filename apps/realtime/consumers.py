"""
LMS Enterprise - WebSocket Consumers
Handles real-time WebSocket connections for live class events,
notifications, and system broadcasts.
"""
import json
import logging
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async

logger = logging.getLogger('lms.realtime')


class LMSBaseConsumer(AsyncJsonWebsocketConsumer):
    """Base WebSocket consumer with tenant & auth awareness."""

    async def connect(self):
        self.user = self.scope.get('user')
        self.tenant_id = self.scope.get('tenant_id')

        if not self.user or self.user.is_anonymous:
            await self.close(code=4001)
            return

        await self.accept()

    async def disconnect(self, close_code):
        pass

    async def receive_json(self, content, **kwargs):
        event_type = content.get('type', 'unknown')
        handler = getattr(self, f'handle_{event_type}', None)
        if handler:
            await handler(content)
        else:
            await self.send_json({'error': f'Unknown event type: {event_type}'})


class NotificationConsumer(LMSBaseConsumer):
    """Per-user notification channel."""

    async def connect(self):
        await super().connect()
        if hasattr(self, 'user') and self.user and not self.user.is_anonymous:
            self.group_name = f'notifications_{self.user.id}'
            await self.channel_layer.group_add(self.group_name, self.channel_name)

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def notification_message(self, event):
        """Handle notification broadcast."""
        await self.send_json({
            'type': 'notification',
            'data': event['data']
        })


class LiveClassConsumer(LMSBaseConsumer):
    """Live class channel for attendance tracking & chat."""

    async def connect(self):
        self.class_id = self.scope['url_route']['kwargs'].get('class_id')
        self.group_name = f'class_{self.class_id}'

        await super().connect()
        if hasattr(self, 'user') and self.user and not self.user.is_anonymous:
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'user_joined',
                    'data': {
                        'user_id': str(self.user.id),
                        'username': getattr(self.user, 'username', 'Unknown'),
                    }
                }
            )

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'user_left',
                    'data': {'user_id': str(self.user.id)}
                }
            )
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def handle_chat(self, content):
        """Broadcast chat message to class group."""
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'chat_message',
                'data': {
                    'user_id': str(self.user.id),
                    'message': content.get('message', ''),
                    'timestamp': content.get('timestamp'),
                }
            }
        )

    async def handle_heartbeat(self, content):
        """Process heartbeat for watch time tracking."""
        await self.send_json({
            'type': 'heartbeat_ack',
            'data': {'status': 'ok'}
        })

    # Group message handlers
    async def user_joined(self, event):
        await self.send_json({'type': 'user_joined', 'data': event['data']})

    async def user_left(self, event):
        await self.send_json({'type': 'user_left', 'data': event['data']})

    async def chat_message(self, event):
        await self.send_json({'type': 'chat_message', 'data': event['data']})

    async def class_status_update(self, event):
        await self.send_json({'type': 'class_status', 'data': event['data']})


class SystemBroadcastConsumer(LMSBaseConsumer):
    """Tenant-wide or system-wide broadcast channel."""

    async def connect(self):
        await super().connect()
        if hasattr(self, 'tenant_id') and self.tenant_id:
            self.group_name = f'tenant_{self.tenant_id}'
            await self.channel_layer.group_add(self.group_name, self.channel_name)

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def system_broadcast(self, event):
        await self.send_json({'type': 'system_broadcast', 'data': event['data']})

    async def maintenance_alert(self, event):
        await self.send_json({'type': 'maintenance_alert', 'data': event['data']})
