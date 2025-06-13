from django.urls import path
from . import views

urlpatterns = [
    path('normalchat/', views.NormalChat.as_view())
]