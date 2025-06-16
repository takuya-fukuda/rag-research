from django.urls import path
from . import views

urlpatterns = [
    path('normalchat/', views.NormalChat.as_view()),
    path('ragchat/', views.RagChat.as_view()),
    path('dataregister/', views.DataRegsiter.as_view()),
]