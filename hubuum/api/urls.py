"""Non-versioned URLs for hubuum."""

from django.urls import re_path

from . import views

urlpatterns = [
    re_path(r"auth/login/", views.LoginView.as_view(), name="knox_login"),
    re_path(r"auth/logout/", views.LogoutView.as_view(), name="knox_logout"),
    re_path(
        r"auth/logoutall/",
        views.LogoutAllView.as_view(),
        name="knox_logoutall",
    ),
]
