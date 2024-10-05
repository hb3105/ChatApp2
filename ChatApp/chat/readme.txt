# ChatApp/chat/views.py
from django.shortcuts import render, redirect
from .models import Room, DirectMessage, Message
from django.http import JsonResponse
from django.contrib import messages
from users.models import User  
from django.db.models import Q
from django.urls import reverse
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required

def index(request):
    if request.user.is_authenticated:
        rooms = Room.objects.filter(users=request.user)  # Only show rooms the user has access to
    else:
        rooms = Room.objects.none()  # No rooms for unauthenticated users

    if request.method == 'POST':
        room_name = request.POST.get('room_name', '').capitalize()
        if room_name and request.user.user_type == 'pro':  # Only allow pro users to create rooms
            room, created = Room.objects.get_or_create(name=room_name)
            room.users.add(request.user)  # Add the user to the room
            room.save()
            room_url = reverse('chat:room') + f'?room_name={room_name}'
            return redirect(room_url)
        else:
            messages.error(request, "Only PRO users can create rooms.")

    return render(request, "chat/index.html", {"rooms": rooms})

def remove_room(request, room_name):
    if request.method == 'POST' and request.user.user_type == 'pro':
        try:
            room = Room.objects.get(name=room_name)
            room.delete()
            messages.success(request, f"{room_name} has been removed.")
        except Room.DoesNotExist:
            messages.error(request, "Room does not exist.")
    else:
        messages.error(request, "Only PRO users can remove rooms.")
    
    return redirect('chat:index')

def room(request):
    room_name = request.GET.get('room_name')
    if room_name:
        try:
            room = Room.objects.get(name=room_name)
            if request.user not in room.users.all():
                messages.error(request, "You do not have access to this room.")
                return redirect('chat:index')

            # Get all users in the group except the current user
            participants = room.users.all().exclude(username=request.user.username)  

            return render(request, "chat/room.html", {
                "room_name": room_name,
                "participants": participants,
            })
        except Room.DoesNotExist:
            messages.error(request, f"Room '{room_name}' does not exist.")
            return redirect('chat:index')
    else:
        messages.error(request, "Room name is required.")
        return redirect('chat:index')

# remove a user from the group
def remove_user_from_room(request, room_name, username):
    if request.method == 'POST' and request.user.user_type == 'pro':
        try:
            room = Room.objects.get(name=room_name)
            user_to_remove = User.objects.get(username=username)
            if user_to_remove in room.users.all():
                room.users.remove(user_to_remove)
                messages.success(request, f"{username} has been removed from {room_name}.")
            else:
                messages.error(request, f"{username} is not a participant in this room.")
        except Room.DoesNotExist:
            messages.error(request, "Room does not exist.")
        except User.DoesNotExist:
            messages.error(request, "User does not exist.")
    else:
        messages.error(request, "Only PRO users can remove others.")
    
    room_url = reverse('chat:room') + f'?room_name={room_name}'
    return redirect(room_url)  # Redirect back to the room
    
# Invite users to the group
def invite_to_room(request, room_name):
    if request.method == 'POST':
        username = request.POST.get('username')
        user_to_invite = User.objects.filter(username=username).first()
        
        if user_to_invite:
            if request.user.user_type == 'pro':
                room = Room.objects.get(name=room_name)
                room.users.add(user_to_invite)
                messages.success(request, f"{username} has been invited to {room_name}.")
            else:
                messages.error(request, "Only PRO users can invite others.")
        else:
            messages.error(request, f"User '{username}' does not exist.")
    
    room_url = reverse('chat:room') + f'?room_name={room_name}'
    return redirect(room_url)  # Redirect back to the room

def direct_messages(request):
    if request.user.is_authenticated:
        receiver_username = request.GET.get('receiver')
        receiver = User.objects.filter(username=receiver_username).first() if receiver_username else None
        
        users = User.objects.exclude(id=request.user.id)  # Exclude the logged-in user
        messages = DirectMessage.objects.filter(
            Q(sender=request.user, receiver=receiver) | Q(receiver=request.user, sender=receiver)
        ).order_by('timestamp') if receiver else []

        return render(request, "chat/direct_messages.html", {
            "messages": messages,
            "users": users,
            "current_receiver": receiver
        })
    else:
        return redirect('users:login')

def handle_unknown_url(request, any_path):
    if any_path == "dashboard":
        # Handle the dashboard URL specifically
        return redirect('users:dashboard')

@login_required
def delete_message(request, message_id):

    # Check if the user is a Pro user and owns the message or has the right to delete it
    if request.user.user_type == 'pro':  # Assuming you have this method on the user model
        # Get the message to be deleted
        message = get_object_or_404(Message, id=message_id)
        message.delete()
        room_url = reverse('chat:room') + f'?room_name={message.room.name}'
        return redirect(room_url)  # Redirect back to the room
        return redirect('room', room_name=message.room.name)  # Redirect to the same chat room after deletion
    else:    
        return redirect('chat:index')  # Redirect back to the room


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
                if not message_id:
                    raise ValueError("Message ID is missing for delete request")

                # Delete the message
                await self.delete_message(message_id)

                # Notify the group about the deletion
                await self.channel_layer.group_send(
                    self.room_group_name, {
                        "type": "delete_message",
                        "message_id": message_id
                    }
                )

        except Exception as e:
            print(f"Error in receive: {e}")
    
    # Add a new method to handle notifications
    async def notification(self, event):
        notification_message = event['message']

        # Send the notification to all clients in the group
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'message': notification_message,
        }))

    # Receive message from room group
    async def chat_message(self, event):
        print(f"Broadcasting message: {event['message']} from {event['username']}")
        message = event["message"]
        username = event["username"]
        message_id = event['message_id']
        timestamp = timezone.localtime(timezone.now()).strftime("%b %d, %Y %H:%M")
       
        # Send message with timestamp to all clients in the group
        await self.send(text_data=json.dumps({
            "message": message,
            "username": username,
            "timestamp": timestamp,
            "message_id":message_id
        }))

    async def delete_message(self, event):
        message_id = event['message_id']
        
        # Send the deletion event to all clients in the group
        await self.send(text_data=json.dumps({
            'type': 'delete',
            'message_id': message_id
        }))
        print(f"Message with id {message_id} deleted.")


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
                    "timestamp": msg['timestamp'].strftime("%b %d, %Y %H:%M"),
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

    @database_sync_to_async
    def delete_message(self, message_id):
        try:
            message = Message.objects.get(id=message_id)
            message.delete()
        except Message.DoesNotExist:
            print(f"Message with id {message_id} does not exist.")


class DirectMessageConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        self.receiver_username = self.scope['url_route']['kwargs']['receiver']  # Assuming you pass it in the URL
        self.receiver = await self.get_user(self.receiver_username)
        
        if self.receiver:
            self.room_group_name = f'direct_messages_{self.user.username}'
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()

            initial_messages = await self.get_direct_messages(self.user, self.receiver)
            await self.send(text_data=json.dumps({"messages": initial_messages}))
        else:
            await self.close()
        
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
        message = event['message']
        sender = event['sender']
        timestamp = timezone.localtime(timezone.now()).strftime("%b %d, %Y %H:%M")

        await self.send(text_data=json.dumps({
            'message': message,
            'sender': sender,
            'timestamp': timestamp
        }))
 
    @database_sync_to_async
    def get_direct_messages(self, user, receiver=None):
        now = timezone.now()
        yesterday = now - timezone.timedelta(days=1)

        if receiver:
            if user.user_type == 'pro':
                messages = DirectMessage.objects.filter(
                    (Q(sender=user) & Q(receiver=receiver)) | (Q(receiver=user) & Q(sender=receiver))
                ).order_by('timestamp').select_related('sender', 'receiver').values(
                    'sender__username', 'message', 'timestamp'
                )
            else:
                messages = DirectMessage.objects.filter(
                    (Q(sender=user) & Q(receiver=receiver)) | (Q(receiver=user) & Q(sender=receiver)),
                    timestamp__gte=yesterday
                ).order_by('timestamp').select_related('sender', 'receiver').values(
                    'sender__username', 'message', 'timestamp'
                )
        else:
            messages = DirectMessage.objects.filter(
                Q(sender=user) | Q(receiver=user)
            ).order_by('timestamp').select_related('sender', 'receiver').values(
                'sender__username', 'message', 'timestamp'
            )
        return [
            {
                "username": msg['sender__username'],
                "message": msg['message'],
                "timestamp": msg['timestamp'].strftime("%b %d, %Y %H:%M")
            } for msg in messages
        ]
 
    @database_sync_to_async
    def get_user(self, receiver_username):
        return User.objects.filter(username=receiver_username).first()

    @database_sync_to_async
    def save_direct_message(self, sender, receiver, message):
        DirectMessage.objects.create(sender=sender, receiver=receiver, message=message)


    {% extends 'base.html' %}

{% block title %}Chat Room - {{ room_name }}{% endblock %}

{% block content %}
    {% if user.is_authenticated %}
        <div>
            Hello, <b>{{ user.username|capfirst|default:'Guest' }}!</b>
            {% if user.user_type == 'pro' %}
                (Pro)<sup>*</sup>
            {% else %}
                (Basic)<sup>*</sup>
            {% endif %}
            <br>
            <span style="color: #999; font-size: 0.8em;"><sup>*</sup>Pro users can create groups and add users, in addition to seeing entire chat history.</span><br><br>
            
            <b>Group :</b> {{ room_name|capfirst }}<br>
            <b>Participants</b>
            <ul id="participant-list">
                {% for participant in participants %}
                    <li>
                        <a href="{% url 'chat:direct_messages' %}?receiver={{ participant }}">{{ participant|capfirst }}</a>
                        {% if user.user_type == 'pro' and participant != request.user %}
                            <form action="{% url 'chat:remove_user_from_room' room_name participant.username %}" method="POST" style="display:inline;" onsubmit="return confirmDelete();">
                                {% csrf_token %}
                                <input type="submit" value="X" style="color: red; background: none; border: none; cursor: pointer; font-size: 12px;">
                            </form>
                        {% endif %}
                    </li>
                {% empty %}
                    <li>No other participants.</li>
                {% endfor %}
            </ul>

            {% if user.user_type == 'pro' %}
            <b>Invite</b> User to the group.
            <form method="POST" action="{% url 'chat:invite_to_room' room_name %}">
                {% csrf_token %}
                <input type="text" name="username" placeholder="Enter username to invite" required>
                <input type="submit" value="Invite">
            </form>
            {% endif %}
            <br><br>

            <div id="chat-log" style="border: 1px solid #ccc; padding: 10px; height: 300px; overflow-y: auto;"></div><br>
            <div class="chat-input-container">
                <input id="chat-message-input" type="text" size="50">
                <input id="chat-message-submit" type="button" value="Send">
            </div>
            
            {{ room_name|json_script:"room-name" }}
            <a href="{% url 'users:dashboard' %}">Dashboard</a>
            <a href="#" onclick="logout()">Logout</a>&nbsp;
        </div>
    {% else %}
        <h5>You can access this page only if you are logged in.</h5>
        <a href="{% url 'users:dashboard' %}">Dashboard</a>
    {% endif %}
    
    <!-- Message Template -->
    <div id="message-template" style="display: none;">
        <span class="timestamp"></span> | <b class="username"></b>: <span class="message-content"></span>
        <button class="delete-message-button" style="color: red; background: none; border: none; cursor: pointer;">X</button>
        <br>
    </div>

    <script>
        const roomName = JSON.parse(document.getElementById('room-name').textContent);
        let chatSocket = null;

        function connectToChat() {
            if (!chatSocket) {
                chatSocket = new WebSocket(
                    'ws://'
                    + window.location.host
                    + '/ws/chat/'
                    + roomName
                    + '/'
                );
            }

            chatSocket.onmessage = function(e) {
                const data = JSON.parse(e.data);
                console.log(data)

                if (data.messages) {
                    data.messages.forEach(msg => {
                        const { username, message, timestamp, message_id } = msg;
                        appendMessage(username, message, timestamp, message_id);
                    });
                } else if (data.type === 'delete') {
                    handleDeleteNotification(data.message_id);
                } else {
                    const { username = "Unknown User", message = "No message", timestamp = "Unknown time", message_id } = data;
                    appendMessage(username, message, timestamp, message_id);
                }
            };

            chatSocket.onclose = function(e) {
                console.error('Chat socket closed. Reconnecting...');
                chatSocket = null;
                setTimeout(connectToChat, 2000);
            };
        }

        function appendMessage(username, message, timestamp, message_id) {
            const messageTemplate = document.getElementById('message-template').cloneNode(true);
            messageTemplate.id = '';
            messageTemplate.style.display = '';
            messageTemplate.querySelector('.timestamp').textContent = timestamp;
            messageTemplate.querySelector('.username').textContent = username;
            messageTemplate.querySelector('.message-content').textContent = message;

            if ('{{ user.user_type }}' === 'pro') {
                const deleteButton = messageTemplate.querySelector('.delete-message-button');
                deleteButton.dataset.messageId = message_id;
                deleteButton.addEventListener('click', () => handleDeleteMessage(message_id));
            } else {
                messageTemplate.querySelector('.delete-message-button').remove();
            }

            document.getElementById('chat-log').appendChild(messageTemplate);
            scrollToBottom();

            // Show notification for new message
            showNotification(username, message);
        }

        function showNotification(username, message) {
            if (Notification.permission === 'granted') {
                const notification = new Notification(`New message from ${username}`, {
                    body: message,
                    icon: '/static/chat/images/icon.png' // Customize this path if needed
                });
            }
        }

        function handleDeleteNotification(message_id) {
            const messages = document.querySelectorAll('#chat-log > div'); // Adjust as needed to target messages
            messages.forEach(msg => {
                const deleteButton = msg.querySelector('.delete-message-button');
                if (deleteButton && deleteButton.dataset.messageId == message_id) {
                    msg.remove(); // Remove the message from the chat log
                    showNotification("System", "A message has been deleted."); // Show deletion notification
                }
            });
        }

        function scrollToBottom() {
            const chatLog = document.getElementById('chat-log');
            chatLog.scrollTop = chatLog.scrollHeight;
        }

        function handleDeleteMessage(messageId) {
            if (confirm("Are you sure you want to delete this message?")) {
                fetch(`/chat/delete_message/${messageId}/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': '{{ csrf_token }}'
                    }
                }).then(response => {
                    if (response.ok) {
                        alert('Message deleted successfully.');
                        location.reload();
                    } else {
                        alert('Error deleting message.');
                    }
                });
            }
        }

        // Request notification permission
        if (Notification.permission === 'default') {
            Notification.requestPermission().then(permission => {
                if (permission === 'granted') {
                    console.log('Notification permission granted.');
                }
            });
        }
        connectToChat();
        document.querySelector('#chat-message-input').focus();
        document.querySelector('#chat-message-input').onkeyup = function(e) {
            if (e.keyCode === 13) {
                document.querySelector('#chat-message-submit').click();
            }
        };
        document.querySelector('#chat-message-submit').onclick = function(e) {
            const messageInputDom = document.querySelector('#chat-message-input');
            var messageInput = messageInputDom.value.trim();
            if (messageInput) {
                chatSocket.send(JSON.stringify({
                    message: messageInput,
                    username: '{{ request.user.username|capfirst }}',
                    type: 'message',
                }));
                messageInputDom.value = '';
            }
        };

    </script>
    <script>
        function logout() {
            var form = document.createElement('form');
            form.method = 'POST';
            form.action = '{% url "users:logout" %}';

            var csrfTokenInput = document.createElement('input');
            csrfTokenInput.type = 'hidden';
            csrfTokenInput.name = 'csrfmiddlewaretoken';
            csrfTokenInput.value = '{{ csrf_token }}';

            form.appendChild(csrfTokenInput);
            document.body.appendChild(form);
            form.submit();
        }
    </script>
    <script>
        function confirmDelete() {
            return confirm("Are you sure you want to remove this user from the group?");
        }
    </script>
    
{% endblock %}

    