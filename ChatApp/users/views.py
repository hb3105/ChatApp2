# users/views.py

from django.contrib.auth import login
from users.models import User  
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

def search_users(request):
    query = request.GET.get('query')
    if query:
        # Filter users based on username (case-insensitive) excluding the logged-in user
        users = User.objects.filter(username__icontains=query).exclude(username=request.user.username)
    else:
        users = []  # Empty list if no query
    context = {'users': users, 'query': query}
    return render(request, 'users/search_users.html', context)