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
        # have a different group name without spaces to ensure rooms with spaces are created and websocket connection is established
        self.room_group_name = 'chat_{}'.format(self.room_name.replace(' ', '_'))  # replace the space with an _

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
            message_type = text_data_json.get("type")  # Expecting 'message' or 'delete'
            
            if message_type == "message":
                message = text_data_json.get("message")
                username = text_data_json.get("username")

                # Check if message and username are present
                if not message or not username:
                    raise ValueError("Message or username is missing")

                print(f"Received message: {message} from {username}")

                # Save message to the database and get the chat message object
                chat_message = await self.save_message(self.room_name, username, message)
                print('saved message: ', chat_message)

                # Send message to room group
                await self.channel_layer.group_send(
                    self.room_group_name, {
                        "type": "chat_message",
                        "message": message,
                        "username": username,
                        "message_id": chat_message.id  # Send the message ID
                    }
                )
            elif message_type == "delete":
                message_id = text_data_json.get("message_id")
                if message_id:   
                    print(f"delete message is called for message id: {message_id}")
                    
                    # Delete the message
                    await self.delete_message(message_id)

                    # Retrieve updated messages and send them to the group
                    messages = await self.get_messages(self.room_name)
                    await self.channel_layer.group_send(
                        self.room_group_name, {
                            "type": "chat_message",
                            "messages": messages
                        }
                    )
                else:
                    raise ValueError("Message ID is missing for delete request")
        except Exception as e:
            print(f"Error in receive: {e}")
    
    # Receive message from room group
    async def chat_message(self, event):
        if 'messages' in event:
            messages = event['messages']
            print('chat_message bulk delivery after deleting a message to all clients')
            # Send the entire list of messages in one go
            await self.send(text_data=json.dumps({
                "messages": messages  # Send the messages array directly
            }))
        else:
            # Handle normal message broadcasting
            message = event["message"]
            username = event["username"]
            message_id = event['message_id']
            timestamp = timezone.localtime(timezone.now()).strftime("%b %d, %Y %H:%M")
            print('chat_message single id: ', message_id)

            await self.send(text_data=json.dumps({
                "message": message,
                "username": username,
                "timestamp": timestamp,
                "message_id": message_id
            }))

    @database_sync_to_async
    def delete_message(self, message_id):
        try:
            message = Message.objects.get(id=message_id)
            message.delete()
        except Message.DoesNotExist:
            print(f"Message with id {message_id} does not exist.")

    @database_sync_to_async
    def get_messages(self, room_name):
        # get chat history based on user type 
        yesterday = timezone.now() - timezone.timedelta(days=1)

        if not self.scope['user'].is_anonymous:
            if self.scope['user'].user_type == 'pro':
                # Show entire chat history for pro users
                messages = Message.objects.filter(room__name=room_name).order_by('timestamp').values('id', 'username', 'message', 'timestamp')
            else:
                # Show messages from the last 24 hours for basic users
                messages = Message.objects.filter(
                    room__name=room_name,
                    timestamp__gte=yesterday
                ).order_by('timestamp').values('id', 'username', 'message', 'timestamp')

            return [
                {
                    "username": msg['username'],
                    "message": msg['message'],
                    "timestamp": timezone.localtime(msg['timestamp']).strftime("%b %d, %Y %H:%M"),
                    "message_id":msg['id'] # Access 'id' as a key since msg is a dictionary
                } for msg in messages
            ]
        else:
            return None

    @database_sync_to_async
    def save_message(self, room_name, username, message):
        room = Room.objects.get(name=room_name)
        chat_message = Message.objects.create(room=room, username=username, message=message)
        return chat_message

class DirectMessageConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        self.receiver_username = self.scope['url_route']['kwargs']['receiver']  # Assuming you pass it in the URL

        self.receiver = await self.get_user(self.receiver_username)
        
        if self.receiver:
            self.room_group_name = f'direct_messages_{self.user.username}'
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()

            # Load messages from the database
            messages = await self.get_direct_messages(self.user, self.receiver)
            await self.send(text_data=json.dumps({"messages": messages}))
        else:
            await self.close()
        
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json.get("type")  # Expecting 'message' or 'delete'
        print('message type: ', message_type)    

        try:
            if message_type == 'message':
                message = text_data_json['message']
                receiver_username = text_data_json['receiver']
                print(f"Received message: {message} from {self.user.username} to {receiver_username}")
                
                # Save the message to the database
                receiver = await self.get_user(receiver_username)
                if receiver:
                    direct_message = await self.save_direct_message(self.user, receiver, message)
                    print('saved message:', direct_message)

                    # Send the message to the receiver's group
                    await self.channel_layer.group_send(
                        f'direct_messages_{receiver.username}',
                        {
                            'type': 'send_direct_message',
                            'message': message,
                            'sender': self.user.username,
                            'message_id': direct_message.id
                        }
                    )

                    # Send the message to the sender's group as well
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'send_direct_message',
                            'message': message,
                            'sender': self.user.username,
                            'message_id': direct_message.id
                        }
                    )
            elif message_type=='delete':
                message_id = text_data_json.get("message_id")
                if message_id:   
                    print(f"delete message is called for message id: {message_id}")
                    
                    # Delete the message
                    await self.delete_direct_message(message_id)

                    # Retrieve updated messages and send them to both sender and receiver
                    receiver = await self.get_user(self.receiver_username)
                    messages = await self.get_direct_messages(self.user, receiver)

                    # Send updated messages to sender
                    await self.send(text_data=json.dumps({"messages": messages}))

                    # Send updated messages to receiver
                    await self.channel_layer.group_send(
                        f'direct_messages_{receiver.username}',
                        {
                            'type': 'send_updated_messages',
                            'messages': messages
                        }
                    )
                else:
                    raise ValueError("Message ID is missing for delete request")
        except Exception as e:
            print(f"Error in receive: {e}")

    async def send_updated_messages(self, event):
        messages = event['messages']
        print('Sending updated messages to the receiver after deletion')
        await self.send(text_data=json.dumps({"messages": messages}))

    async def send_direct_message(self, event):
        # Handle normal message broadcasting
        message = event["message"]
        sender = event["sender"]
        message_id = event['message_id']
        timestamp = timezone.localtime(timezone.now()).strftime("%b %d, %Y %H:%M")
        print('timestamp: ', timestamp)
        print('direct_message single id: ', message_id)

        await self.send(text_data=json.dumps({
            "message": message,
            "sender": sender,
            "timestamp": timestamp,
            "message_id": message_id
        }))

    @database_sync_to_async
    def delete_direct_message(self, message_id):
        try:
            message = DirectMessage.objects.get(id=message_id)
            message.delete()
        except Message.DoesNotExist:
            print(f"Message with id {message_id} does not exist.")

    @database_sync_to_async
    def get_direct_messages(self, user, receiver=None):
        now = timezone.now()
        yesterday = now - timezone.timedelta(days=1)

        if receiver:
            if user.user_type == 'pro':
                messages = DirectMessage.objects.filter(
                    (Q(sender=user) & Q(receiver=receiver)) | (Q(receiver=user) & Q(sender=receiver))
                ).order_by('timestamp').select_related('sender', 'receiver').values(
                    'sender__username', 'message', 'timestamp', 'id'
                )
            else:
                messages = DirectMessage.objects.filter(
                    (Q(sender=user) & Q(receiver=receiver)) | (Q(receiver=user) & Q(sender=receiver)),
                    timestamp__gte=yesterday
                ).order_by('timestamp').select_related('sender', 'receiver').values(
                    'sender__username', 'message', 'timestamp', 'id'
                )
        else:
            messages = DirectMessage.objects.filter(
                Q(sender=user) | Q(receiver=user)
            ).order_by('timestamp').select_related('sender', 'receiver').values(
                'sender__username', 'message', 'timestamp', 'id'
            )
        return [
            {
                "username": msg['sender__username'],
                "message": msg['message'],
                "timestamp": timezone.localtime(msg['timestamp']).strftime("%b %d, %Y %H:%M"),
                "message_id":msg['id'],
            } for msg in messages
        ]
 
    @database_sync_to_async
    def get_user(self, receiver_username):
        return User.objects.filter(username=receiver_username).first()

    @database_sync_to_async
    def save_direct_message(self, sender, receiver, message):
        direct_message = DirectMessage.objects.create(sender=sender, receiver=receiver, message=message)
        return direct_message