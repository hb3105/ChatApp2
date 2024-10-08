# chat/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import Room, Message, DirectMessage
from users.models import User
from django.db.models import Q

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = f'chat_{self.room_name.replace(" ", "_")}'  # Replace spaces with underscores

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        messages = await self.get_messages(self.room_name)
        await self.send_messages(messages)

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get("type")

            if message_type == "message":
                await self.handle_message(data)
            elif message_type == "delete":
                await self.handle_delete(data)
        except Exception as e:
            print(f"Error in receive: {e}")

    async def handle_message(self, data):
        message = data.get("message")
        username = data.get("username")

        if not message or not username:
            raise ValueError("Message or username is missing")

        chat_message = await self.save_message(self.room_name, username, message)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": message,
                "username": username,
                "message_id": chat_message.id
            }
        )

    async def handle_delete(self, data):
        message_id = data.get("message_id")
        if not message_id:
            raise ValueError("Message ID is missing for delete request")

        await self.delete_message(message_id)
        messages = await self.get_messages(self.room_name)
        await self.channel_layer.group_send(self.room_group_name, {"type": "chat_message", "messages": messages})

    async def chat_message(self, event):
        if 'messages' in event:
            await self.send_messages(event['messages'])
        else:
            message = event["message"]
            username = event["username"]
            message_id = event['message_id']
            timestamp = self.get_current_timestamp()

            await self.send(text_data=json.dumps({
                "message": message,
                "username": username,
                "timestamp": timestamp,
                "message_id": message_id
            }))

    async def send_messages(self, messages):
        await self.send(text_data=json.dumps({"messages": messages}))

    @database_sync_to_async
    def delete_message(self, message_id):
        Message.objects.filter(id=message_id).delete()

    @database_sync_to_async
    def get_messages(self, room_name):
        yesterday = timezone.now() - timezone.timedelta(days=1)
        user = self.scope['user']

        if user.is_anonymous:
            return []

        messages = Message.objects.filter(room__name=room_name)

        if user.user_type == 'pro':
            messages = messages.order_by('timestamp').values('id', 'username', 'message', 'timestamp')
        else:
            messages = messages.filter(timestamp__gte=yesterday).order_by('timestamp').values('id', 'username', 'message', 'timestamp')

        return [
            {
                "username": msg['username'],
                "message": msg['message'],
                "timestamp": timezone.localtime(msg['timestamp']).strftime("%b %d, %Y %H:%M"),
                "message_id": msg['id']
            } for msg in messages
        ]

    @database_sync_to_async
    def save_message(self, room_name, username, message):
        room = Room.objects.get(name=room_name)
        return Message.objects.create(room=room, username=username, message=message)

    @staticmethod
    def get_current_timestamp():
        return timezone.localtime(timezone.now()).strftime("%b %d, %Y %H:%M")


class DirectMessageConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        self.receiver_username = self.scope['url_route']['kwargs']['receiver']
        self.receiver = await self.get_user(self.receiver_username)

        if self.receiver:
            self.room_group_name = f'direct_messages_{self.user.username}'
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()

            messages = await self.get_direct_messages(self.user, self.receiver)
            await self.send_messages(messages)
        else:
            await self.close()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get("type")

        try:
            if message_type == 'message':
                await self.handle_direct_message(data)
            elif message_type == 'delete':
                await self.handle_direct_delete(data)
        except Exception as e:
            print(f"Error in receive: {e}")

    async def handle_direct_message(self, data):
        message = data['message']
        receiver_username = data['receiver']

        receiver = await self.get_user(receiver_username)
        if receiver:
            direct_message = await self.save_direct_message(self.user, receiver, message)

            await self.channel_layer.group_send(
                f'direct_messages_{receiver.username}',
                {
                    'type': 'send_direct_message',
                    'message': message,
                    'username': self.user.username,
                    'message_id': direct_message.id
                }
            )
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'send_direct_message',
                    'message': message,
                    'username': self.user.username,
                    'message_id': direct_message.id
                }
            )

    async def handle_direct_delete(self, data):
        message_id = data.get("message_id")
        if message_id:
            await self.delete_direct_message(message_id)
            receiver = await self.get_user(self.receiver_username)
            messages = await self.get_direct_messages(self.user, receiver)
            await self.send(text_data=json.dumps({"messages": messages}))
            await self.channel_layer.group_send(
                f'direct_messages_{receiver.username}',
                {
                    'type': 'send_updated_messages',
                    'messages': messages
                }
            )

    async def send_updated_messages(self, event):
        await self.send_messages(event['messages'])

    async def send_direct_message(self, event):
        await self.send(text_data=json.dumps({
            "message": event["message"],
            "username": event["username"],
            "timestamp": self.get_current_timestamp(),
            "message_id": event["message_id"]
        }))
    
    async def send_messages(self, messages):
        await self.send(text_data=json.dumps({"messages": messages}))

    @database_sync_to_async
    def delete_direct_message(self, message_id):
        DirectMessage.objects.filter(id=message_id).delete()

    @database_sync_to_async
    def get_direct_messages(self, user, receiver=None):
        now = timezone.now()
        yesterday = now - timezone.timedelta(days=1)

        filter_conditions = (
            Q(sender=user) & Q(receiver=receiver) | Q(receiver=user) & Q(sender=receiver)
        )

        if user.user_type == 'pro':
            messages = DirectMessage.objects.filter(filter_conditions).order_by('timestamp').values('sender__username', 'message', 'timestamp', 'id')
        else:
            messages = DirectMessage.objects.filter(filter_conditions, timestamp__gte=yesterday).order_by('timestamp').values('sender__username', 'message', 'timestamp', 'id')

        return [
            {
                "username": msg['sender__username'],
                "message": msg['message'],
                "timestamp": timezone.localtime(msg['timestamp']).strftime("%b %d, %Y %H:%M"),
                "message_id": msg['id'],
            } for msg in messages
        ]

    @database_sync_to_async
    def get_user(self, receiver_username):
        return User.objects.filter(username=receiver_username).first()

    @database_sync_to_async
    def save_direct_message(self, sender, receiver, message):
        return DirectMessage.objects.create(sender=sender, receiver=receiver, message=message)
    
    @staticmethod
    def get_current_timestamp():
        return timezone.localtime(timezone.now()).strftime("%b %d, %Y %H:%M")
