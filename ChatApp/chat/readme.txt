# chat/models.py
from django.db import models
from django.contrib.auth.models import User

class Room(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def clean_name(self):
        # Capitalize the first letter of the room name
        return self.name.capitalize()

    def save(self, *args, **kwargs):
        # Call clean_name before saving
        self.name = self.clean_name()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Message(models.Model):
    room = models.ForeignKey(Room, related_name='messages', on_delete=models.CASCADE)
    username = models.CharField(max_length=100)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.username}: {self.message[:20]} at {self.timestamp}"
    
class DirectMessage(models.Model):
    sender = models.ForeignKey(User, related_name='sent_messages', on_delete=models.CASCADE)
    receiver = models.ForeignKey(User, related_name='received_messages', on_delete=models.CASCADE)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"From {self.sender.username} to {self.receiver.username}: {self.message[:20]} at {self.timestamp}"


from django.shortcuts import render, redirect
from .models import Room, DirectMessage
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Q
from django.urls import reverse

def index(request):
    rooms = Room.objects.all()
    if request.method == 'POST':
        room_name = request.POST.get('room_name', '').capitalize()
        if room_name:
            Room.objects.get_or_create(name=room_name)
            # Manually append room_name as a query parameter
            room_url = reverse('chat:room') + f'?room_name={room_name}'
            return redirect(room_url)
    return render(request, "chat/index.html", {"rooms": rooms})

def room(request):
    room_name = request.GET.get('room_name')
    if room_name:
        try:
            room = Room.objects.get(name=room_name)
            return render(request, "chat/room.html", {"room_name": room_name})
        except Room.DoesNotExist:
            messages.error(request, f"Room '{room_name}' does not exist.")
            return redirect('chat:index')
    else:
        messages.error(request, "Room name is required.")
        return redirect('chat:index')

def handle_unknown_url(request, any_path):
    if any_path == "dashboard":
        # Handle the dashboard URL specifically
        return redirect('users:dashboard')
    else:
        # Handle other unmatched URLs
        return redirect('chat:index')  # Redirect to index
    
def direct_messages(request):
    if request.user.is_authenticated:
        receiver_username = request.GET.get('receiver')
        receiver = User.objects.filter(username=receiver_username).first() if receiver_username else None
        
        users = User.objects.exclude(id=request.user.id)  # Exclude the logged-in user
        messages = DirectMessage.objects.filter(
            Q(sender=request.user, receiver=receiver) | Q(receiver=request.user, sender=receiver)
        ).order_by('-timestamp') if receiver else []

        return render(request, "chat/direct_messages.html", {
            "messages": messages,
            "users": users,
            "current_receiver": receiver
        })
    else:
        return redirect('users:login')

<!-- chat/templates/chat/room.html -->

{% extends 'base.html' %}

{% block title %}Chat Room - {{ room_name }}{% endblock %}

{% block content %}
    {% if user.is_authenticated %}
    <a href="{% url 'chat:index' %}">Back to Chatrooms</a> <br>
    <h5>Room: {{room_name|capfirst}}</h5>
    <h5>Username: {{request.user|capfirst}}</h5>
    <br>

    <textarea id="chat-log" cols="100" rows="20" readonly></textarea><br>
    <div class="chat-input-container">
        <input id="chat-message-input" type="text" size="95">
        <input id="chat-message-submit" type="button" value="Send">
    </div>
    
    {{ room_name|json_script:"room-name" }}

    <a href="#" onclick="logout()">Logout</a>
    {% else %}
        <h5>You can access this page only if you are logged in.</h5>
        <a href="{% url 'users:dashboard' %}">Dashboard</a>
    {% endif %}
    
    <script>
        const roomName = JSON.parse(document.getElementById('room-name').textContent);

        const chatSocket = new WebSocket(
            'ws://'
            + window.location.host
            + '/ws/chat/'
            + roomName
            + '/'
        );

        chatSocket.onmessage = function(e) {
            const data = JSON.parse(e.data);
    
            // This should handle messages from other users
            const { username = "Unknown User", message = "No message", timestamp = "Unknown time" } = data;
            
            // Check if messages are present
            if (data.messages) {
                data.messages.forEach(msg => {
                    const { username, message, timestamp } = msg;
                    document.querySelector('#chat-log').value += `${timestamp} ${username}: ${message}\n`;
                });
            } else {
                const { username = "Unknown User", message = "No message", timestamp = "Unknown time" } = data;
                document.querySelector('#chat-log').value += `${timestamp} ${username}: ${message}\n`;
            }
        };

        chatSocket.onclose = function(e) {
            console.error('Chat socket closed unexpectedly');
        };

        document.querySelector('#chat-message-input').focus();
        document.querySelector('#chat-message-input').onkeyup = function(e) {
            if (e.keyCode === 13) {  // enter, return
                document.querySelector('#chat-message-submit').click();
            }
        };

        document.querySelector('#chat-message-submit').onclick = function(e) {
        const messageInputDom = document.querySelector('#chat-message-input');   

        var messageInput = messageInputDom.value.trim();  // remove leading or trailing whitespaces
        if (messageInput) {  // Only send message if there's valid input
            chatSocket.send(JSON.stringify({
            message: messageInput,
            username: '{{ request.user.username|capfirst }}'
            }));
            messageInputDom.value = '';
        }
        };
    </script>

    <script>
        function logout() {
            // Create a form element
            var form = document.createElement('form');
            form.method = 'POST';
            form.action = '{% url "users:logout" %}';
        
            // Create a hidden input field for the CSRF token
            var csrfTokenInput = document.createElement('input');
            csrfTokenInput.type = 'hidden';
            csrfTokenInput.name = 'csrfmiddlewaretoken';
            csrfTokenInput.value = '{{ csrf_token }}';
        
            // Append the CSRF token input to the form
            form.appendChild(csrfTokenInput);
        
            // Append the form to the document body
            document.body.appendChild(form);
        
            // Submit the form
            form.submit();
        }
    </script>

    
{% endblock %}

{% extends 'base.html' %}

{% block content %}
<h2>Direct Messages</h2>

{% if current_receiver %}
    <h3>Chatting with: {{ current_receiver.username }}</h3>
{% else %}
    <h3>Select a user to chat with.</h3>
{% endif %}

<div id="messages-log" style="height: 400px; overflow-y: scroll; border: 1px solid #ccc; padding: 10px;">
    {% for msg in messages %}
        {{ msg.timestamp }}: {{ msg.sender.username }}: {{ msg.message }}<br>
    {% endfor %}
</div>

<input id="message-input" type="text" placeholder="Type your message...">
<button id="send-message" disabled>Send</button>

<script>
    let currentReceiver = '{{ current_receiver.username }}';

    // Function to check input and enable/disable send button
    function toggleSendButton() {
        const messageInput = document.querySelector('#message-input');
        const sendButton = document.querySelector('#send-message');
        sendButton.disabled = messageInput.value.trim() === '';
    }

    // Event listener for input changes
    document.querySelector('#message-input').addEventListener('input', toggleSendButton);

    document.querySelector('#send-message').onclick = function(e) {
        const message = document.querySelector('#message-input').value.trim();
        if (message && currentReceiver) {
            chatSocket.send(JSON.stringify({
                'message': message,
                'receiver': currentReceiver
            }));
            document.querySelector('#message-input').value = '';
            toggleSendButton(); // Disable the button after sending
        }
    };

    // WebSocket connection
    const chatSocket = new WebSocket(
        'ws://' + window.location.host + '/ws/direct_messages/'
    );

    chatSocket.onmessage = function(e) {
        const data = JSON.parse(e.data);
        const { message, sender } = data;
        
        // Append the message to the messages log
        const messagesLog = document.querySelector('#messages-log');
        messagesLog.innerHTML += `<p><strong>${sender}:</strong> ${message} <em>${new Date().toLocaleString()}</em></p>`;
        
        // Scroll to the bottom of the div
        messagesLog.scrollTop = messagesLog.scrollHeight;
    };

    chatSocket.onclose = function(e) {
        console.error('Chat socket closed unexpectedly');
    };
</script>

{% endblock %}

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



I have room view where multiple users can chat with each other. All the message in the room are stored in the database and are loaded when users go to a particular room retaining all the chat history. 
Similarly I have a directmessage model where one user can talk with another user. The above code is working only if both users are online and communicate with each other. I need to ensure all the messages between the two users are fetched correctly and displayed in the directmessage view so that both offline and online messaging can happen. 
Please make the methods smilar to that of room to get this implemented.