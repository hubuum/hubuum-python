"""Core URLs for the hubuum project, site configuration."""

from typing import List

from django.contrib import admin
from django.urls import include, path, resolvers
from rest_framework.permissions import AllowAny
from rest_framework.schemas import get_schema_view  # type: ignore

schema_view = get_schema_view(
    title="hubuum API",
    permission_classes=(AllowAny,),
)

urlpatterns: List[resolvers.URLResolver] = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("hubuum.api.v1.urls")),
    path("api/", include("hubuum.api.urls")),
    path("docs/", schema_view),
]
