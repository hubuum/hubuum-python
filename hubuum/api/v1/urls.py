"""Versioned (v1) URLs for hubuum."""

from django.urls import include, path
from rest_framework import routers

from . import views

router = routers.DefaultRouter()
# router.register(r'host', views.HeroViewSet)

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    path("", include(router.urls)),
    path("users/", views.UserList.as_view()),
    path("users/<val>", views.UserDetail.as_view()),
    path("groups/", views.GroupList.as_view()),
    path("groups/<val>", views.GroupDetail.as_view()),
    path("groups/<val>/members/", views.GroupMembers.as_view()),
    path("groups/<val>/members/<userid>", views.GroupMembersUser.as_view()),
    #    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    #    path('token-auth/', tokens.ObtainExpiringAuthToken.as_view()),
    path("permissions/", views.PermissionList.as_view()),
    path(
        "permissions/<val>", views.PermissionDetail.as_view(), name="permission-detail"
    ),
    path("namespaces/", views.NamespaceList.as_view()),
    path("namespaces/<val>", views.NamespaceDetail.as_view(), name="namespace-detail"),
    path("extensions/", views.ExtensionList.as_view()),
    path(
        "extensions/<val>",
        views.ExtensionDetail.as_view(),
        name="extension-data-detail",
    ),
    path("extension_data/", views.ExtensionDataList.as_view()),
    path(
        "extension_data/<val>",
        views.ExtensionDataDetail.as_view(),
        name="namespace-detail",
    ),
    path(
        "namespaces/<val>/groups/",
        views.NamespaceMembers.as_view(),
        name="namespace-groups",
    ),
    path(
        "namespaces/<val>/groups/<groupid>",
        views.NamespaceMembersGroup.as_view(),
        name="namespace-groups",
    ),
    path("hosts/", views.HostList.as_view()),
    path("hosts/<val>", views.HostDetail.as_view(), name="host-detail"),
    path("hosttypes/", views.HostTypeList.as_view()),
    path("hosttypes/<val>", views.HostTypeDetail.as_view(), name="hosttype-detail"),
    path("rooms/", views.RoomList.as_view()),
    path("rooms/<val>", views.RoomDetail.as_view(), name="room-detail"),
    path("jacks/", views.JackList.as_view()),
    path("jacks/<val>", views.JackDetail.as_view(), name="jack-detail"),
    path("persons/", views.PersonList.as_view()),
    path("persons/<val>", views.PersonDetail.as_view(), name="person-detail"),
    path("vendors/", views.VendorList.as_view()),
    path("vendors/<val>", views.VendorDetail.as_view(), name="vendor-detail"),
    path("pos/", views.PurchaseOrderList.as_view()),
    path(
        "pos/<val>",
        views.PurchaseOrderDetail.as_view(),
        name="purchaseorder-detail",
    ),
    path("purchasedocuments/", views.PurchaseDocumentList.as_view()),
    path(
        "purchasedocuments/<val>",
        views.PurchaseDocumentDetail.as_view(),
        name="purchasedocument-detail",
    ),
]
