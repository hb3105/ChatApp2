from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/chat/(?P<room_name>\w+)/$", consumers.ChatConsumer.as_asgi()),
    re_path(r'ws/direct_messages/(?P<receiver>\w+)/$', consumers.DirectMessageConsumer.as_asgi()),  # Updated line
]
