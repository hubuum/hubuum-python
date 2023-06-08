"""Non-versioned URLs for hubuum."""

from typing import List

from django.urls import re_path, resolvers

from . import views

urlpatterns: List[resolvers.URLPattern] = [
    re_path(r"auth/login/", views.LoginView.as_view(), name="knox_login"),
    re_path(r"auth/logout/", views.LogoutView.as_view(), name="knox_logout"),
    re_path(
        r"auth/logoutall/",
        views.LogoutAllView.as_view(),
        name="knox_logoutall",
    ),
]
