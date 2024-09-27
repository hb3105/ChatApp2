# chat/consumers.py
import json

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import Room, Message

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