# chat/models.py
from django.conf import settings
from django.db import models
from users.models import User

class Room(models.Model):
    name = models.CharField(max_length=100, unique=True)
    users = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='rooms', blank=True)

    def clean_name(self):
        # Capitalize the first letter of the room name
        return self.name.capitalize()

    def save(self, *args, **kwargs):
        # Call clean_name before saving
        self.name = self.clean_name()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Message(models.Model):
    room = models.ForeignKey(Room, related_name='messages', on_delete=models.CASCADE)
    username = models.CharField(max_length=100)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.username}: {self.message[:20]} at {self.timestamp}" 
   
class DirectMessage(models.Model):
    # Use settings.AUTH_USER_MODEL for flexibility with custom user models
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='sent_messages', on_delete=models.CASCADE)
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='received_messages', on_delete=models.CASCADE)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True, auto_now=False)  # Recommended

    def __str__(self):
        return f"From {self.sender.username} to {self.receiver.username}: {self.message[:20]} at {self.timestamp}"
