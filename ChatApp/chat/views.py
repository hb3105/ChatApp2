# ChatApp/chat/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.urls import reverse
from chat.models import Room, DirectMessage
from users.models import User  

def is_pro_user(user):
    return user.user_type == 'pro'

def index(request):
    rooms = Room.objects.filter(users=request.user) if request.user.is_authenticated else Room.objects.none()

    if request.method == 'POST' and is_pro_user(request.user):
        room_name = request.POST.get('room_name', '').capitalize()
        if room_name:
            room, _ = Room.objects.get_or_create(name=room_name)
            room.users.add(request.user)
            return redirect(reverse('chat:room') + f'?room_name={room_name}')
        messages.error(request, "Only PRO users can create rooms.")

    return render(request, "chat/index.html", {"rooms": rooms})

def remove_room(request, room_name):
    room = get_object_or_404(Room, name=room_name)

    if request.method == 'POST' and is_pro_user(request.user):
        room.delete()
        messages.success(request, f"{room_name} has been removed.")
    else:
        messages.error(request, "Only PRO users can remove rooms.")
    
    return redirect('chat:index')

def room(request):
    room_name = request.GET.get('room_name')
    room = get_object_or_404(Room, name=room_name)

    if request.user not in room.users.all():
        messages.error(request, "You do not have access to this room.")
        return redirect('chat:index')

    participants = room.users.exclude(username=request.user.username)
    emoji_list = ['😀', '😂', '❤️', '👍', '🎉', '😎', '🥳', '😢', '🔥', '🎈']

    return render(request, "chat/room.html", {
        "room_name": room_name,
        "participants": participants,
        'emoji_list': emoji_list,
    })

def remove_user_from_room(request, room_name, username):
    room = get_object_or_404(Room, name=room_name)
    user_to_remove = get_object_or_404(User, username=username)

    if request.method == 'POST' and is_pro_user(request.user):
        if user_to_remove in room.users.all():
            room.users.remove(user_to_remove)
            messages.success(request, f"{username.capitalize()} has been removed from {room_name}.")
        else:
            messages.error(request, f"{username.capitalize()} is not a participant in this room.")
    else:
        messages.error(request, "Only PRO users can remove others.")

    return redirect(reverse('chat:room') + f'?room_name={room_name}')

def invite_to_room(request, room_name):
    room = get_object_or_404(Room, name=room_name)

    if request.method == 'POST':
        username = request.POST.get('username')
        user_to_invite = get_object_or_404(User, username=username)

        if is_pro_user(request.user):
            room.users.add(user_to_invite)
            messages.success(request, f"{username.capitalize()} has been invited to {room_name}.")
        else:
            messages.error(request, "Only PRO users can invite others.")

    return redirect(reverse('chat:room') + f'?room_name={room_name}')

def direct_messages(request):
    if not request.user.is_authenticated:
        return redirect('users:login')

    receiver_username = request.GET.get('receiver')
    receiver = User.objects.filter(username=receiver_username).first() if receiver_username else None

    users = User.objects.exclude(id=request.user.id)
    messages = DirectMessage.objects.filter(
        Q(sender=request.user, receiver=receiver) | Q(receiver=request.user, sender=receiver)
    ).order_by('timestamp') if receiver else []

    emoji_list = ['😀', '😂', '❤️', '👍', '🎉', '😎', '🥳', '😢', '🔥', '🎈']

    return render(request, "chat/direct_messages.html", {
        "messages": messages,
        "users": users,
        "current_receiver": receiver,
        'emoji_list': emoji_list,
    })

def handle_unknown_url(request, any_path):
    if any_path == "dashboard":
        return redirect('users:dashboard')