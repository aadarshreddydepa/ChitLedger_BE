from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from .views import SigninView,FirebasePasswordResetView, PermissionRequiredView, FirebaseSignupView

urlpatterns = [
    path("signup/", FirebaseSignupView.as_view(), name="signup"),
    path("signin/", SigninView.as_view(), name="signin"),
    path("forgotpassword/", FirebasePasswordResetView.as_view(), name="forgot-password"),
    path("authcheck/", PermissionRequiredView.as_view(), name="authcheck"),
     # JWT built-in endpoints
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),   # login (access + refresh)
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),  # get new access token
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),     # optional, verify token validity
]
