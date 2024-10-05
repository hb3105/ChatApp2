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
    path('invite/<str:room_name>/', views.invite_to_room, name='invite_to_room'),
    path('remove/<str:room_name>/', views.remove_room, name='remove_room'),
    path('remove/<str:room_name>/<str:username>/', views.remove_user_from_room, name='remove_user_from_room'),
    path('delete_message/<int:message_id>/', views.delete_message, name='delete_message'),
    # Optional catch-all
    path("<str:any_path>", views.handle_unknown_url, name="catch-all"), 
]