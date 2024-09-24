from django.db import models

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