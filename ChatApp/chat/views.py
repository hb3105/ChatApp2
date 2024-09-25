from django.shortcuts import render
from .models import Room

def index(request):
    rooms = Room.objects.all()  # Fetch all rooms from the database
    print("Index view accessed")  # Add this line
    return render(request, "chat/index.html", {"rooms": rooms})

def room(request, room_name):
    try:
        room = Room.objects.get(name=room_name)  # Try to get the existing room
        return render(request, "chat/room.html", {"room_name": room_name})
    except Room.DoesNotExist:
        # Room doesn't exist, create a new one
        room = Room.objects.create(name=room_name)
        return render(request, "chat/room.html", {"room_name": room_name})