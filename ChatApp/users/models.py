# users/forms.py

from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    USER_TYPE = (
        ('basic', 'Basic User'),
        ('pro', 'Pro User'),
    )

    user_type = models.CharField(max_length=10, choices=USER_TYPE, default='basic')