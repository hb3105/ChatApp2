# users/urls.py

from django.contrib import admin
from . import views
from django.urls import path, include, re_path

app_name = 'users'

urlpatterns = [
    path("", views.dashboard, name="home"), #empty path https:/127.0.0.1:8000
    path("accounts/", include("django.contrib.auth.urls")),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("register/", views.register, name="register"),
]