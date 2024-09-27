# chat/urls.py
from django.urls import path

from . import views

app_name = 'chat'

urlpatterns = [
    path("", views.index, name="home"),
    path("index/", views.index, name="index"),
    path("room/", views.room, name="room"),  # Remove the room_name parameter
]