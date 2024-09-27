# chat/models.py
from django.db import models
from django.contrib.auth.models import User

class Room(models.Model):
    name = models.CharField(max_length=100, unique=True)

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