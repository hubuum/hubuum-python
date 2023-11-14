"""Versioned (v1) URLs for hubuum."""

from typing import List

from django.urls import include, path, resolvers
from rest_framework import routers

router = routers.DefaultRouter()

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns: List[resolvers.URLResolver] = [
    path("", include(router.urls)),
    path("iam/", include("hubuum.api.v1.endpoints.iam")),
    path("attachments/", include("hubuum.api.v1.endpoints.attachments")),
    path("resources/", include("hubuum.api.v1.endpoints.resources")),
    path("dynamic/", include("hubuum.api.v1.endpoints.dynamic")),
    path(".meta/", include("hubuum.api.v1.endpoints.meta")),
]
