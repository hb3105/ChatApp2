# users/urls.py

from django.contrib import admin
from . import views
from django.urls import path, include

urlpatterns = [
    path("accounts/", include("django.contrib.auth.urls")),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("register/", views.register, name="register"),
]
