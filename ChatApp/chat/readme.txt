I would like to add one to one communication among users and that these messages are not part of rooms. I have some files such as consumers.py and related info to share with you so you can generate all necessary changes, templates, models etc., to enable one to one communication. 
I have created a "ChatApp" project in Django and it has 2 apps "chat" and "users". It now supports creating chat rooms, where users can chat with each other. 
I also need a method to search for existing users or showing a list of users so that in future I can create direct communication among users. I am using default django user autentication model.


# users/views.py

from django.contrib.auth import login
from django.shortcuts import redirect, render
from django.urls import reverse
from users.forms import CustomUserCreationForm

def dashboard(request):
    return render(request, "users/dashboard.html")

def register(request):
    if request.method == "GET":
        return render(
            request, "users/register.html",
            {"form": CustomUserCreationForm}
        )
    elif request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect(reverse("users:dashboard"))
        else:
            return render(
            request, "users/register.html",
            {"form": CustomUserCreationForm}
        )

<!--users/templates/users/register.html-->
{% extends 'base.html' %}

{% block content %}
<h2>Register</h2>

<form method="post">
    {% csrf_token %}
    {{form.as_p}}
    <input type="submit" value="Register">
</form>

<br><br>
<a href="{% url 'users:dashboard' %}">Dashboard</a>

{% endblock %}

{% extends 'base.html' %}
{% block content %}
<br>
Hello, {{ user.username|capfirst|default:'Guest' }}!

<div>
    {% if user.is_authenticated %}
        <br>
        <a href="{% url 'chat:index' %}">Chatrooms</a> <br><br>
        <a href="{% url 'users:password_change' %}">Change password</a> <br><br>
        <a href="#" onclick="logout()">Logout</a>
    {% else %}
        <a href="{% url 'users:login' %}">Login</a>&nbsp;
        <a href="{% url 'users:register' %}">Register</a>
    {% endif %}
</div>

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

from django.shortcuts import render, redirect
from django.urls import reverse  # Import reverse function
from django.contrib.auth.decorators import login_required

from .models import Room
from .models import DirectMessage


def index(request):
    rooms = Room.objects.all()
    print("Index view accessed")
    return render(request, "chat/index.html", {"rooms": rooms})

def room(request, room_name):
    room_name = room_name.capitalize()
    try:
        room = Room.objects.get(name=room_name)
        return render(request, "chat/room.html", {"room_name": room_name})
    except Room.DoesNotExist:
        # Room doesn't exist, redirect to index with a message using reverse
        return redirect(reverse('chat:index') + '?message=Room+'+ room_name +'+does+not+exist.')
        from django.shortcuts import render, redirect
from django.urls import reverse  # Import reverse function
from django.contrib.auth.decorators import login_required

from .models import Room
from .models import DirectMessage


def index(request):
    rooms = Room.objects.all()
    print("Index view accessed")
    return render(request, "chat/index.html", {"rooms": rooms})

def room(request, room_name):
    room_name = room_name.capitalize()
    try:
        room = Room.objects.get(name=room_name)
        return render(request, "chat/room.html", {"room_name": room_name})
    except Room.DoesNotExist:
        # Room doesn't exist, redirect to index with a message using reverse
        return redirect(reverse('chat:index') + '?message=Room+'+ room_name +'+does+not+exist.')

        {% extends 'base.html' %}

{% block title %}Chat Rooms{% endblock %}

{% block content %}
    {% if user.is_authenticated %}
        <h5>Chat Rooms</h5>
        <ul id="room-list">
            {% for room in rooms %}
                <li><a href="/chat/{{ room.name }}/">{{ room.name }}</a></li>
            {% empty %}
                <li>No rooms available.</li>
            {% endfor %}
        </ul>

        <h5>Create a new Chat Room</h5>
        <input id="room-name-input" type="text" size="50"><br>
        <input id="room-name-submit" type="button" value="Enter" disabled> <br>
        <a href="#" onclick="logout()">Logout</a>
    {% else %}
        <h5>You can access this page only if you are logged in.</h5>
        <a href="{% url 'users:dashboard' %}">Dashboard</a>
    {% endif %}

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

    <script>
        submitButton.onclick = function() {
            const roomName = roomInput.value.trim();
            if (roomName) {
                // Send an AJAX request to create the room
                fetch(`/chat/create_room/${roomName}/`, {
                    method: 'POST'
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        window.location.href = `/chat/${roomName}/`; // Redirect to the created room
                    } else {
                        alert("Failed to create room. Please try again.");
                    }
                })
                .catch(error => {
                    console.error("Error creating room:", error);
                    alert("Error creating room. Please try again.");
                });
            }
        };
    </script>
{% endblock %}

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