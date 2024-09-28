Updating the file.

I have created a "ChatApp" django project containing two apps "chat" and "users".
The current features include user registration, creating chat rooms and users chatting in the chat rooms.
I now want to extend realtime and offline direct/private messaging rbetween users in the app. Please help me with the necessary code.

Here is ChatApp urls.you
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path("", include("users.urls",namespace='users')),
    path("chat/", include("chat.urls", namespace='chat')),
]

"chat" app urls.py
# chat/urls.py
from django.urls import path

from . import views

app_name = 'chat'

urlpatterns = [
    path("", views.index, name="home"),
    path("index/", views.index, name="index"),
    path("index/<str:any_path>", views.handle_unknown_url, name="catch-all-index"),
    path("room/", views.room, name="room"),  # Remove the room_name parameter
    # Optional catch-all
    path("<str:any_path>", views.handle_unknown_url, name="catch-all"),  
]

"users" app urls.py
# users/urls.py

from django.contrib import admin
from . import views
from django.urls import path, include, re_path

app_name = 'users'

urlpatterns = [
    path("", views.dashboard, name="home"), #empty path https:/127.0.0.1:8000
    path("accounts/", include("django.contrib.auth.urls")),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("register/", views.register, name="register"),
    path('search/', views.search_users, name='search_users'),
]

{% extends 'base.html' %}

{% block content %}
<h2>Search Users</h2>

<form method="get">
  <label for="query">Search by username:</label>
  <input type="text" name="query" id="query" value="{{ query }}">
  <input type="submit" value="Search">
</form>

{% if users %}
  <h3>Search Results</h3>
  <ul>
    {% for user in users %}
      <li>
        <a href="#">{{ user.username }}</a> (Send message)
      </li>
    {% endfor %}
  </ul>
{% else %}
  <p>No users found for your search.</p>
{% endif %}
<a href="{% url 'users:dashboard' %}">Dashboard</a>

{% endblock %}

from django.shortcuts import render, redirect
from .models import Room
from django.http import JsonResponse
from django.contrib import messages

def index(request):
    rooms = Room.objects.all()  # Fetch all rooms from the database
    if request.method == 'POST':
        room_name = request.POST.get('room_name', '').capitalize()
        if room_name:
            # Create the room if it doesn't exist
            Room.objects.get_or_create(name=room_name)
            return redirect('chat:room', room_name=room_name)  # Redirect to the created room
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

{% block title %}Chat Rooms{% endblock %}

{% block content %}
    {% if messages %}
        <ul class="messages">
            {% for message in messages %}
                <li{% if message.tags %} class="{{ message.tags }}"{% endif %}>{{ message }}</li>
            {% endfor %}
        </ul>
    {% endif %}

    {% if user.is_authenticated %}
        <h5>Chat Rooms</h5>
        <ul id="room-list">
            {% for room in rooms %}
                <li><a href="{% url 'chat:room' %}?room_name={{ room.name }}">{{ room.name }}</a></li>
            {% empty %}
                <li>No rooms available.</li>
            {% endfor %}
        </ul>

        <h5>Create a new Chat Room</h5>
        <form id="create-room-form" method="POST">
            {% csrf_token %}
            <input id="room-name-input" name="room_name" type="text" size="50" required><br>
            <input id="room-name-submit" type="submit" value="Enter"> <br>
        </form>
        <a href="#" onclick="logout()">Logout</a>&nbsp;

    {% else %}
        <h5>You can access this page only if you are logged in.</h5>
    {% endif %}
    <a href="{% url 'users:dashboard' %}">Dashboard</a>

    <script>
        const roomInput = document.querySelector('#room-name-input');
        const submitButton = document.querySelector('#room-name-submit');

        roomInput.focus();

        roomInput.oninput = function() {
            const roomName = roomInput.value.trim();
            submitButton.disabled = roomName === '';
        };

        roomInput.onkeyup = function(e) {
            if (e.keyCode === 13 && !submitButton.disabled) {  // enter, return
                submitButton.click();
            }
        };

        submitButton.onclick = function() {
            const roomName = roomInput.value.trim();
            console.log('Redirecting to room:', roomName);
            if (roomName) {
                window.location.pathname = '/chat/' + roomName + '/';
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