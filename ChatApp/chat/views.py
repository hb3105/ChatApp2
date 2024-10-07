# ChatApp/chat/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.urls import reverse
from chat.models import Room, DirectMessage, Message
from users.models import User  

# The main chat page view where rooms, users can be found
def index(request):
    if request.user.is_authenticated:
        rooms = Room.objects.filter(users=request.user)  # Only show rooms the user has access to
    else:
        rooms = Room.objects.none()  # No rooms for unauthenticated users

    # Create a group/room if pro users
    if request.method == 'POST':
        room_name = request.POST.get('room_name', '').capitalize()
        if room_name and request.user.user_type == 'pro':  # Only allow pro users to create rooms
            room, created = Room.objects.get_or_create(name=room_name)
            room.users.add(request.user)  # Add the user to the room
            room.save()
            # redirect the user to the newly created room/group
            room_url = reverse('chat:room') + f'?room_name={room_name}'
            return redirect(room_url)
        else:
            messages.error(request, "Only PRO users can create rooms.")

    return render(request, "chat/index.html", {"rooms": rooms})

# The view to handle deleting a room
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

# load the room view for user
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
            emoji_list = ['😀', '😂', '❤️', '👍', '🎉', '😎', '🥳', '😢', '🔥', '🎈']

            return render(request, "chat/room.html", {
                "room_name": room_name,
                "participants": participants,
                'emoji_list': emoji_list,
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
                messages.success(request, f"{username.capitalize()} has been removed from {room_name}.")
            else:
                messages.error(request, f"{username.capitalize()} is not a participant in this room.")
        except Room.DoesNotExist:
            messages.error(request, "Room does not exist.")
        except User.DoesNotExist:
            messages.error(request, "User does not exist.")
    else:
        messages.error(request, "Only PRO users can remove others.")
    
    #return to the same room
    room_url = reverse('chat:room') + f'?room_name={room_name}'
    return redirect(room_url)
    
# Invite users to the group
def invite_to_room(request, room_name):
    if request.method == 'POST':
        username = request.POST.get('username')
        user_to_invite = User.objects.filter(username=username).first()
        
        if user_to_invite:
            if request.user.user_type == 'pro':
                room = Room.objects.get(name=room_name)
                room.users.add(user_to_invite)
                messages.success(request, f"{username.capitalize()} has been invited to {room_name}.")
            else:
                messages.error(request, "Only PRO users can invite others.")
        else:
            messages.error(request, f"User '{username.capitalize()}' does not exist.")
    
    #return to the same room
    room_url = reverse('chat:room') + f'?room_name={room_name}'
    return redirect(room_url)

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