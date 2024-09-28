# chat/urls.py
from django.urls import path

from . import views

app_name = 'chat'

urlpatterns = [
    path("", views.index, name="home"),
    path("index/", views.index, name="index"),
    path("index/<str:any_path>", views.handle_unknown_url, name="catch-all-index"),
    path("room/", views.room, name="room"),  # Remove the room_name parameter
    path("direct_messages/", views.direct_messages, name="direct_messages"),
    # Optional catch-all
    path("<str:any_path>", views.handle_unknown_url, name="catch-all"),  
]