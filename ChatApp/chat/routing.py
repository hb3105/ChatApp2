from django.urls import re_path
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from chat.consumers import ChatConsumer, DirectMessageConsumer

websocket_urlpatterns = [
    re_path(r"ws/chat/(?P<room_name>.+)/$", ChatConsumer.as_asgi()),
    re_path(r'ws/direct_messages/(?P<receiver>\w+)/$', DirectMessageConsumer.as_asgi()),
]

application = ProtocolTypeRouter({
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
