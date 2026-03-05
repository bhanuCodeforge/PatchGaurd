from django.urls import path
from .views import LoginView, RegisterView, RefreshView, LogoutView, PasswordChangeView, ProfileView

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("register/", RegisterView.as_view(), name="register"),
    path("refresh/", RefreshView.as_view(), name="token_refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("change-password/", PasswordChangeView.as_view(), name="change_password"),
    path("profile/", ProfileView.as_view(), name="profile"),
]
