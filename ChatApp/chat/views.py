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