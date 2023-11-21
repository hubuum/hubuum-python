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
    path("manager/<class>", AttachmentManagerDetail.as_view()),
    # Every attachment
    path("data/", AttachmentList.as_view()),
    # Every attachment belonging to a given model.
    path("data/<class>/", AttachmentList.as_view()),
    # Every attachment belonging to a given object in a given model.
    path("data/<class>/<instance>", AttachmentDetail.as_view()),
    path("data/<class>/<instance>/", AttachmentList.as_view()),
    # A specific attachment object (ie, metadata) belonging to a given object in a given model.
    path("data/<class>/<instance>/<attachment>", AttachmentDetail.as_view()),
    # The actual attachment file
    path(
        "data/<class>/<instance>/<attachment>/download",
        AttachmentDetail.as_view(),
        name="download_attachment",
    ),
]
