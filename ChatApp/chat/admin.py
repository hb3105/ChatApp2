from django.contrib import admin
from chat.models import Room, Message, DirectMessage
from users.models import User

# Register your models here.
admin.site.register(Room)
admin.site.register(Message)
admin.site.register(DirectMessage)
admin.site.register(User)