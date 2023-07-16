"""Versioned (v1) URLs for hubuum."""

from django.urls import path

from hubuum.api.v1.views.dynamic import (
    DynamicClassDetail,
    DynamicClassList,
    DynamicObjectDetail,
    DynamicObjectList,
)

urlpatterns = [
    # Classes
    path("", DynamicClassList.as_view()),
    path("<pk>", DynamicClassDetail.as_view()),
    # Objects
    path("<classname>/", DynamicObjectList.as_view()),
    path("<classname>/<pk>", DynamicObjectDetail.as_view()),
    # Links
    path("<classname>/<pk>/link/<object1>/<object2>", DynamicObjectDetail.as_view()),
    path("<classname>/<pk>/unlink/<objectid>", DynamicObjectDetail.as_view()),
    path("<classname>/<pk>/links/", DynamicObjectDetail.as_view()),
    # List first link to a specific class, may be transitive
    path("<classname>/<pk>/links/<class>/", DynamicObjectDetail.as_view()),
    path("<classname>/<pk>/links/<class>/first", DynamicObjectDetail.as_view()),
    path("<classname>/<pk>/links/<class>/all", DynamicObjectDetail.as_view()),
]
