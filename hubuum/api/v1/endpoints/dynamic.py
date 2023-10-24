"""Versioned (v1) URLs for hubuum."""

from django.urls import path

from hubuum.api.v1.views.dynamic import (
    ClassLinkView,
    HubuumClassDetail,
    HubuumClassList,
    HubuumObjectDetail,
    HubuumObjectList,
    ObjectLinkDetailView,
    ObjectLinkListView,
)

urlpatterns = [
    # Classes
    path("", HubuumClassList.as_view()),
    path("<classname>", HubuumClassDetail.as_view()),
    # Objects
    path("<classname>/", HubuumObjectList.as_view()),
    path("<classname>/<obj>", HubuumObjectDetail.as_view()),
    # Links
    # This endpoint supports POST, GET, and DELETE.
    path("<source_class>/link/<target_class>/", ClassLinkView.as_view()),
    # Lists all direct links for an object
    # Post to create a direct link
    path("<classname>/<obj>/links/", ObjectLinkListView.as_view()),
    # Get the link object of a spesific (direct) link.
    # Returns 404 if no such path exists.
    # Delete removes a specific link, may NOT be transitive.
    # Does not support patch.
    path(
        "<classname>/<obj>/link/<targetclass>/<targetobject>",
        ObjectLinkDetailView.as_view(),
    ),
    # Check if an object can reach a class via links (possibly transitive)
    # Optionally takes query parameters:
    # transitive: boolean, default False
    # max_depth: integer, default 0 (no limit) - only valid if transitive is True
    path("<classname>/<obj>/links/<targetclass>/", ObjectLinkListView.as_view()),
]
