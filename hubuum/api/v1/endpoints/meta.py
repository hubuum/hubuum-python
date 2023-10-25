"""IAM URLs for hubuum API v1."""

from django.urls import path

from hubuum.api.v1.views.meta import DebugView, RuntimesView, VersionView

urlpatterns = [
    path("version", VersionView.as_view()),
    path("runtimes", RuntimesView.as_view()),
    path("debug", DebugView.as_view()),
]
