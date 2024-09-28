# chat/consumers.py
import json

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import Room, Message, DirectMessage
from django.contrib.auth.models import User

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = f"chat_{self.room_name}"

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

        # Load messages from the database
        messages = await self.get_messages(self.room_name)

        # Send all messages to the newly connected client
        await self.send(text_data=json.dumps({"messages": messages}))

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    # Receive message from WebSocket
    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            message = text_data_json.get("message")
            username = text_data_json.get("username")
            
            # Check if message and username are present
            if not message or not username:
                raise ValueError("Message or username is missing")

            print(f"Received message: {message} from {username}")

            # Save message to the database
            await self.save_message(self.room_name, username, message)

            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name, {
                    "type": "chat_message",
                    "message": message,
                    "username": username,
                }
            )
        except Exception as e:
            print(f"Error in receive: {e}")

    # Receive message from room group
    async def chat_message(self, event):
        print(f"Broadcasting message: {event['message']} from {event['username']}")
        message = event["message"]
        username = event["username"]
        timestamp = timezone.localtime(timezone.now()).strftime("%b %d, %Y %H:%M")
        print("timezone is: ", timezone.now())

        # Send message with timestamp to all clients in the group
        await self.send(text_data=json.dumps({
            "message": message,
            "username": username,
            "timestamp": timestamp
        }))

    @database_sync_to_async
    def get_messages(self, room_name):
        messages = Message.objects.filter(room__name=room_name).order_by('timestamp').values('username', 'message', 'timestamp')
        # Format messages to a serializable structure
        return [
            {
                "username": msg['username'],
                "message": msg['message'],
                "timestamp": msg['timestamp'].strftime("%b %d, %Y %H:%M")
            } for msg in messages
        ]

    @database_sync_to_async
    def save_message(self, room_name, username, message):
        room = Room.objects.get(name=room_name)
        Message.objects.create(room=room, username=username, message=message)

class DirectMessageConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        self.room_group_name = f'direct_messages_{self.user.username}'

        # Join the group for the logged-in user
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        print('joining the direct message room: ', self.room_group_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        receiver_username = text_data_json['receiver']
        print(f"Received message: {message} from {self.user.username} to {receiver_username}")

        # Save the message to the database
        receiver = await self.get_user(receiver_username)
        if receiver:
            await self.save_direct_message(self.user, receiver, message)

            # Send the message to the receiver's group
            await self.channel_layer.group_send(
                f'direct_messages_{receiver.username}',
                {
                    'type': 'send_direct_message',
                    'message': message,
                    'sender': self.user.username,
                }
            )

            # Send the message to the sender's group as well
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'send_direct_message',
                    'message': message,
                    'sender': self.user.username,
                }
            )

    async def send_direct_message(self, event):
        print(f"Broadcasting message: {event['message']} from {event['sender']}")
        message = event['message']
        sender = event['sender']

        await self.send(text_data=json.dumps({
            'message': message,
            'sender': sender,
        }))

    @database_sync_to_async
    def get_user(self, username):
        return User.objects.filter(username=username).first()

    @database_sync_to_async
    def save_direct_message(self, sender, receiver, message):
        DirectMessage.objects.create(sender=sender, receiver=receiver, message=message)
