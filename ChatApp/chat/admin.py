from django.contrib import admin
from chat.models import Room, Message, DirectMessage

# Register your models here.
admin.site.register(Room)
admin.site.register(Message)
admin.site.register(DirectMessage)