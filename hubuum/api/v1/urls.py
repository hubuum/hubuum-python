"""Versioned (v1) URLs for hubuum."""

from django.urls import include, path
from rest_framework import routers

router = routers.DefaultRouter()

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    path("", include(router.urls)),
    path("iam/", include("hubuum.api.v1.endpoints.iam")),
    path("extensions/", include("hubuum.api.v1.endpoints.extensions")),
    path("attachments/", include("hubuum.api.v1.endpoints.attachments")),
    path("resources/", include("hubuum.api.v1.endpoints.resources")),
]
