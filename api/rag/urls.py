from django.urls import path
from . import views

from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenObtainPairView
)

urlpatterns = [
    path('normalchat/', views.NormalChat.as_view()),
    path('ragchat/', views.RagChat.as_view()),
    path('dataregister/', views.DataRegsiter.as_view()),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'), #認証認可用
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'), #認証認可用
    path('login/', views.LoginView.as_view()),  # ログイン用
    path('retry/', views.RetryView.as_view()),  # 再試行用
    path('logout/', views.LogoutView.as_view()),  # ログアウト用
]