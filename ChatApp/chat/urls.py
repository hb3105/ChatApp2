# chat/urls.py
from django.urls import path

from . import views

app_name = 'chat'

urlpatterns = [
    path("", views.index, name="home"),
    path("index/", views.index, name="index"),
    path("index/<str:any_path>", views.handle_unknown_url, name="catch-all-index"),
    path("room/", views.room, name="room"),  # Remove the room_name parameter
    # Optional catch-all
    path("<str:any_path>", views.handle_unknown_url, name="catch-all"),  
]