"""Versioned (v1) URLs for hubuum."""

from django.urls import path

from hubuum.api.v1.views.resources import (
    HostDetail,
    HostList,
    HostTypeDetail,
    HostTypeList,
    JackDetail,
    JackList,
    PersonDetail,
    PersonList,
    PurchaseOrderDetail,
    PurchaseOrderList,
    RoomDetail,
    RoomList,
    VendorDetail,
    VendorList,
)

urlpatterns = [
    path("hosts/", HostList.as_view()),
    path("hosts/<val>", HostDetail.as_view()),
    path("hosttypes/", HostTypeList.as_view()),
    path("hosttypes/<val>", HostTypeDetail.as_view()),
    path("rooms/", RoomList.as_view()),
    path("rooms/<val>", RoomDetail.as_view()),
    path("jacks/", JackList.as_view()),
    path("jacks/<val>", JackDetail.as_view()),
    path("persons/", PersonList.as_view()),
    path("persons/<val>", PersonDetail.as_view()),
    path("vendors/", VendorList.as_view()),
    path("vendors/<val>", VendorDetail.as_view()),
    path("pos/", PurchaseOrderList.as_view()),
    path(
        "pos/<val>",
        PurchaseOrderDetail.as_view(),
    ),
]
