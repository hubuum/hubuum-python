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
    # Users and groups.
    path("users/", views.UserList.as_view()),
    path("users/<val>", views.UserDetail.as_view()),
    path("groups/", views.GroupList.as_view()),
    path("groups/<val>", views.GroupDetail.as_view()),
    path("groups/<val>/members/", views.GroupMembers.as_view()),
    path("groups/<val>/members/<userid>", views.GroupMembersUser.as_view()),
    # Permissions
    path("permissions/", views.PermissionList.as_view()),
    path(
        "permissions/<val>",
        views.PermissionDetail.as_view(),
    ),
    # Namespaces
    path("namespaces/", views.NamespaceList.as_view()),
    path("namespaces/<val>", views.NamespaceDetail.as_view()),
    path(
        "namespaces/<val>/groups/",
        views.NamespaceMembers.as_view(),
    ),
    path(
        "namespaces/<val>/groups/<groupid>",
        views.NamespaceMembersGroup.as_view(),
    ),
    # Extension API.
    path("extensions/", views.ExtensionList.as_view()),
    path(
        "extensions/<val>",
        views.ExtensionDetail.as_view(),
    ),
    path("extension_data/", views.ExtensionDataList.as_view()),
    path(
        "extension_data/<val>",
        views.ExtensionDataDetail.as_view(),
    ),
    # Attachment API.
    # List attachment setup for all models, or post a new setup for a model.
    path("attachments/", views.AttachmentManagerList.as_view()),
    # A specific attachment setup for a given model.
    path(
        "attachments/<val>",
        views.AttachmentManagerDetail.as_view(),
    ),
    # Every attachment belonging to a given model.
    path("attachments/<model>/", views.AttachmentList.as_view()),
    # Every attachment belonging to a given object in a given model.
    path(
        "attachments/<model>/<instance>",
        views.AttachmentDetail.as_view(),
    ),
    # A specific attachment object (ie, metadata) belonging to a given object in a given model.
    path(
        "attachments/<model>/<instance>/<attachment>",
        views.AttachmentDetail.as_view(),
    ),
    # The actual attachment file
    path(
        "attachments/<model>/<instance>/<attachment>/download",
        views.AttachmentDetail.as_view(),
        name="download_attachment",
    ),
    # Object models and their endpoints.
    path("hosts/", views.HostList.as_view()),
    path("hosts/<val>", views.HostDetail.as_view()),
    path("hosttypes/", views.HostTypeList.as_view()),
    path("hosttypes/<val>", views.HostTypeDetail.as_view()),
    path("rooms/", views.RoomList.as_view()),
    path("rooms/<val>", views.RoomDetail.as_view()),
    path("jacks/", views.JackList.as_view()),
    path("jacks/<val>", views.JackDetail.as_view()),
    path("persons/", views.PersonList.as_view()),
    path("persons/<val>", views.PersonDetail.as_view()),
    path("vendors/", views.VendorList.as_view()),
    path("vendors/<val>", views.VendorDetail.as_view()),
    path("pos/", views.PurchaseOrderList.as_view()),
    path(
        "pos/<val>",
        views.PurchaseOrderDetail.as_view(),
    ),
    path("purchasedocuments/", views.PurchaseDocumentList.as_view()),
    path(
        "purchasedocuments/<val>",
        views.PurchaseDocumentDetail.as_view(),
    ),
]
