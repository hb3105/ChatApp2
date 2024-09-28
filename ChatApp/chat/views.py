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
