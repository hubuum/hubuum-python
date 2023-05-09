"""Extension URLs for hubuum API v1."""

from django.urls import path

from hubuum.api.v1.views.extension import (
    ExtensionDataDetail,
    ExtensionDataList,
    ExtensionDetail,
    ExtensionList,
)

urlpatterns = [
    path("", ExtensionList.as_view()),
    path("<val>", ExtensionDetail.as_view()),
    path("data/", ExtensionDataList.as_view()),
    path("data/<val>", ExtensionDataDetail.as_view()),
]
