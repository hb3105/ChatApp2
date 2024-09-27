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