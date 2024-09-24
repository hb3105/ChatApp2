from django.shortcuts import render
from .models import Room

def index(request):
    rooms = Room.objects.all()  # Fetch all rooms from the database
    return render(request, "chat/index.html", {"rooms": rooms})

def room(request, room_name):
    room, created = Room.objects.get_or_create(name=room_name)  # Create room if it doesn't exist
    return render(request, "chat/room.html", {"room_name": room_name})
