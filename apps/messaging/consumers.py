"""
WebSocket consumers for real-time messaging.
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from apps.complaints.models import Complaint
from apps.users.models import CustomUser
from .models import Message, Conversation, Notification
from django.utils import timezone


class MessageConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time messaging."""
    
    async def connect(self):
        """Handle new WebSocket connection."""
        self.complaint_id = self.scope['url_route']['kwargs']['complaint_id']
        self.user = self.scope['user']
        
        # Check if user is authenticated
        if not self.user.is_authenticated:
            await self.close(code=4001)
            return
        
        # Check if user has permission to access this complaint
        complaint = await self.get_complaint(self.complaint_id)
        if not complaint:
            await self.close(code=4004)
            return
        
        # Check permission
        has_permission = await self.check_permission(complaint)
        if not has_permission:
            await self.close(code=4003)
            return
        
        self.complaint = complaint
        self.room_group_name = f'complaint_{self.complaint_id}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send welcome message
        await self.send(text_data=json.dumps({
            'type': 'connection.established',
            'complaint_id': self.complaint_id,
            'user_id': self.user.id
        }))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Handle incoming WebSocket message."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'message.send':
                await self.handle_message(data)
            elif message_type == 'message.read':
                await self.handle_message_read(data)
            elif message_type == 'typing':
                await self.handle_typing(data)
            
        except json.JSONDecodeError:
            await self.send_error('Invalid JSON')
        except Exception as e:
            await self.send_error(str(e))
    
    async def handle_message(self, data):
        """Handle sending a message."""
        content = data.get('content', '')
        recipient_id = data.get('recipient_id')

        if not content:
            await self.send_error('Content is required')
            return

        # Get recipient (explicit recipient, else the other participant)
        recipient = None
        if recipient_id:
            try:
                recipient = await self.get_user(recipient_id)
                if not recipient:
                    await self.send_error('Recipient not found')
                    return
            except Exception:
                recipient = None

        if recipient is None:
            recipient = await self.get_other_participant()

        if recipient is None:
            # No counterpart yet (complaint not assigned) - store as unaddressed
            recipient = None

        # Create message
        message = await self.create_message(
            complaint=self.complaint,
            sender=self.user,
            recipient=recipient,
            content=content,
            message_type='TEXT'
        )
        
        if message:
            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'message.sent',
                    'message': {
                        'id': message.id,
                        'complaint_id': self.complaint_id,
                        'sender_id': self.user.id,
                        'sender_name': self.user.get_short_name(),
                        'sender_role': self.user.role,
                        'recipient_id': message.recipient.id if message.recipient else None,
                        'content': message.content,
                        'message_type': message.message_type,
                        'created_at': str(message.created_at),
                        'is_read': message.is_read
                    }
                }
            )
            
            # Create notification for recipient (only when one exists)
            if message.recipient:
                await self.create_notification(
                    user=message.recipient,
                    notification_type='NEW_MESSAGE',
                    complaint=message.complaint,
                    message=message,
                    title=f'New message for complaint {self.complaint_id}',
                    body=content[:100],
                    priority='MEDIUM'
                )
    
    async def handle_message_read(self, data):
        """Handle marking messages as read."""
        message_ids = data.get('message_ids', [])
        
        if message_ids:
            # Mark messages as read
            await self.mark_messages_as_read(message_ids)
            
            # Notify sender that messages were read
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'messages.read',
                    'message_ids': message_ids,
                    'read_by': self.user.id
                }
            )
    
    async def handle_typing(self, data):
        """Handle typing indicator."""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user.typing',
                'user_id': self.user.id,
                'user_name': self.user.get_short_name()
            }
        )
    
    async def message_sent(self, event):
        """Send message to WebSocket."""
        message = event['message']
        
        # Mark as delivered if this is the recipient
        if message['recipient_id'] == self.user.id:
            await self.mark_message_as_delivered(message['id'])
            message['is_delivered'] = True
        
        await self.send(text_data=json.dumps({
            'type': 'message.received',
            'message': message
        }))
    
    async def messages_read(self, event):
        """Notify that messages were read."""
        await self.send(text_data=json.dumps({
            'type': 'messages.read',
            'message_ids': event['message_ids'],
            'read_by': event['read_by']
        }))
    
    async def user_typing(self, event):
        """Notify that user is typing."""
        await self.send(text_data=json.dumps({
            'type': 'user.typing',
            'user_id': event['user_id'],
            'user_name': event['user_name']
        }))
    
    async def send_error(self, error):
        """Send error message."""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'error': error
        }))
    
    @database_sync_to_async
    def get_complaint(self, complaint_id):
        """Get complaint from database."""
        try:
            return Complaint.objects.get(complaint_id=complaint_id)
        except Complaint.DoesNotExist:
            return None
    
    @database_sync_to_async
    def check_permission(self, complaint):
        """Check if user has permission to access complaint."""
        user = self.user
        return (complaint.citizen == user or 
                complaint.assigned_official == user or 
                complaint.assigned_field_worker == user)
    
    @database_sync_to_async
    def get_user(self, user_id):
        """Get user from database."""
        try:
            return CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return None
    
    @database_sync_to_async
    def get_other_participant(self):
        """Get the other participant in the conversation."""
        complaint = self.complaint
        if complaint.citizen == self.user:
            return complaint.assigned_official
        elif complaint.assigned_official == self.user:
            return complaint.citizen
        return None
    
    @database_sync_to_async
    def create_message(self, complaint, sender, recipient, content, message_type):
        """Create a message."""
        message = Message.objects.create(
            complaint=complaint,
            sender=sender,
            recipient=recipient,
            content=content,
            message_type=message_type,
            is_delivered=True,
            delivered_at=timezone.now()
        )
        
        # Update conversation
        conversation, created = Conversation.objects.get_or_create(complaint=complaint)
        conversation.last_message = message
        conversation.updated_at = timezone.now()
        conversation.save()
        conversation.participants.add(sender, recipient)
        
        # Update unread count
        conversation.update_unread_counts()
        
        return message
    
    @database_sync_to_async
    def mark_message_as_delivered(self, message_id):
        """Mark message as delivered."""
        try:
            message = Message.objects.get(id=message_id)
            if not message.is_delivered:
                message.is_delivered = True
                message.delivered_at = timezone.now()
                message.save()
        except Message.DoesNotExist:
            pass
    
    @database_sync_to_async
    def mark_messages_as_read(self, message_ids):
        """Mark messages as read."""
        messages = Message.objects.filter(id__in=message_ids, recipient=self.user)
        for message in messages:
            if not message.is_read:
                message.is_read = True
                message.read_at = timezone.now()
                message.save()
        
        # Update conversation unread count
        if messages.exists():
            conversation = Conversation.objects.get(complaint=messages.first().complaint)
            conversation.update_unread_counts()
    
    @database_sync_to_async
    def create_notification(self, user, notification_type, complaint, message, title, body, priority):
        """Create a notification."""
        Notification.objects.create(
            user=user,
            notification_type=notification_type,
            complaint=complaint,
            message=message,
            title=title,
            body=body,
            priority=priority,
            delivered_via_app=True
        )


class NotificationConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time notifications."""
    
    async def connect(self):
        """Handle new WebSocket connection."""
        self.user = self.scope['user']
        
        # Check if user is authenticated
        if not self.user.is_authenticated:
            await self.close(code=4001)
            return
        
        self.room_group_name = f'notifications_{self.user.id}'
        
        # Join user's notification group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send welcome message
        await self.send(text_data=json.dumps({
            'type': 'connection.established',
            'user_id': self.user.id
        }))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Handle incoming WebSocket message."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'notification.read':
                await self.handle_notification_read(data)
            
        except json.JSONDecodeError:
            await self.send_error('Invalid JSON')
        except Exception as e:
            await self.send_error(str(e))
    
    async def handle_notification_read(self, data):
        """Handle marking notification as read."""
        notification_id = data.get('notification_id')
        
        if notification_id:
            await self.mark_notification_as_read(notification_id)
    
    async def send_notification(self, event):
        """Send notification to WebSocket."""
        notification = event['notification']
        
        await self.send(text_data=json.dumps({
            'type': 'notification.received',
            'notification': notification
        }))
    
    async def send_error(self, error):
        """Send error message."""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'error': error
        }))
    
    @database_sync_to_async
    def mark_notification_as_read(self, notification_id):
        """Mark notification as read."""
        try:
            notification = Notification.objects.get(id=notification_id, user=self.user)
            if not notification.is_read:
                notification.is_read = True
                notification.read_at = timezone.now()
                notification.save()
        except Notification.DoesNotExist:
            pass
