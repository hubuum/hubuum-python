"""Attachment endpoints for hubuum API v1."""

from django.urls import path

from hubuum.api.v1.views.attachment import (
    AttachmentDetail,
    AttachmentList,
    AttachmentManagerDetail,
    AttachmentManagerList,
)

urlpatterns = [
    # Every attachment setup
    path("manager/", AttachmentManagerList.as_view()),
    # A specific attachment setup for a given model.
    path("manager/<val>", AttachmentManagerDetail.as_view()),
    # Every attachment
    path("data/", AttachmentList.as_view()),
    # Every attachment belonging to a given model.
    path("data/<model>/", AttachmentList.as_view()),
    # Every attachment belonging to a given object in a given model.
    path("data/<model>/<instance>", AttachmentDetail.as_view()),
    path("data/<model>/<instance>/", AttachmentList.as_view()),
    # A specific attachment object (ie, metadata) belonging to a given object in a given model.
    path("data/<model>/<instance>/<attachment>", AttachmentDetail.as_view()),
    # The actual attachment file
    path(
        "data/<model>/<instance>/<attachment>/download",
        AttachmentDetail.as_view(),
        name="download_attachment",
    ),
]
