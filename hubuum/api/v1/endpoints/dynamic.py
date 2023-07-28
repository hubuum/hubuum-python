"""Versioned (v1) URLs for hubuum."""

from django.urls import path

from hubuum.api.v1.views.dynamic import (
    DynamicClassDetail,
    DynamicClassList,
    DynamicLinkDetailView,
    DynamicLinkListView,
    DynamicObjectDetail,
    DynamicObjectList,
    LinkTypeView,
)

urlpatterns = [
    # Classes
    path("", DynamicClassList.as_view()),
    path("<classname>", DynamicClassDetail.as_view()),
    # Objects
    path("<classname>/", DynamicObjectList.as_view()),
    path("<classname>/<obj>", DynamicObjectDetail.as_view()),
    # Links
    # This endpoint supports POST, GET, and DELETE.
    path("<source_class>/<target_class>/linktype/", LinkTypeView.as_view()),
    # Lists all direct links for an object
    # Post to create a direct link
    path("<classname>/<obj>/links/", DynamicLinkListView.as_view()),
    # Get the link object of a spesific (direct) link.
    # Returns 404 if no such path exists.
    # Delete removes a specific link, may NOT be transitive.
    # Does not support patch.
    path(
        "<classname>/<obj>/link/<targetclass>/<targetobject>",
        DynamicLinkDetailView.as_view(),
    ),
    # Check if an object can reach a class via links (possibly transitive)
    # Optionally takes query parameters:
    # transitive: boolean, default False
    # max_depth: integer, default 0 (no limit) - only valid if transitive is True
    path("<classname>/<obj>/links/<targetclass>/", DynamicLinkListView.as_view()),
]
