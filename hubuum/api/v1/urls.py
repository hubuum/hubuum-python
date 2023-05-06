"""Versioned (v1) URLs for hubuum."""

from django.urls import include, path
from rest_framework import routers

from .views.attachment import (
    AttachmentDetail,
    AttachmentList,
    AttachmentManagerDetail,
    AttachmentManagerList,
)
from .views.extension import (
    ExtensionDataDetail,
    ExtensionDataList,
    ExtensionDetail,
    ExtensionList,
)
from .views.iam import (
    GroupDetail,
    GroupList,
    GroupMembers,
    GroupMembersUser,
    NamespaceDetail,
    NamespaceList,
    NamespaceMembers,
    NamespaceMembersGroup,
    PermissionDetail,
    PermissionList,
    UserDetail,
    UserList,
)
from .views.resources import (
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

router = routers.DefaultRouter()
# router.register(r'host', views.HeroViewSet)

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    path("", include(router.urls)),
    # Users and groups.
    path("users/", UserList.as_view()),
    path("users/<val>", UserDetail.as_view()),
    path("groups/", GroupList.as_view()),
    path("groups/<val>", GroupDetail.as_view()),
    path("groups/<val>/members/", GroupMembers.as_view()),
    path("groups/<val>/members/<userid>", GroupMembersUser.as_view()),
    # Permissions
    path("permissions/", PermissionList.as_view()),
    path(
        "permissions/<val>",
        PermissionDetail.as_view(),
    ),
    # Namespaces
    path("namespaces/", NamespaceList.as_view()),
    path("namespaces/<val>", NamespaceDetail.as_view()),
    path(
        "namespaces/<val>/groups/",
        NamespaceMembers.as_view(),
    ),
    path(
        "namespaces/<val>/groups/<groupid>",
        NamespaceMembersGroup.as_view(),
    ),
    # Extension API.
    path("extensions/", ExtensionList.as_view()),
    path(
        "extensions/<val>",
        ExtensionDetail.as_view(),
    ),
    path("extension_data/", ExtensionDataList.as_view()),
    path(
        "extension_data/<val>",
        ExtensionDataDetail.as_view(),
    ),
    # Attachment API.
    # List attachment setup for all models, or post a new setup for a model.
    path("attachment_manager/", AttachmentManagerList.as_view()),
    # A specific attachment setup for a given model.
    path(
        "attachment_manager/<val>",
        AttachmentManagerDetail.as_view(),
    ),
    # Every attachment
    path("attachments/", AttachmentList.as_view()),
    # Every attachment belonging to a given model.
    path("attachments/<model>/", AttachmentList.as_view()),
    # Every attachment belonging to a given object in a given model.
    path(
        "attachments/<model>/<instance>",
        AttachmentDetail.as_view(),
    ),
    path(
        "attachments/<model>/<instance>/",
        AttachmentList.as_view(),
    ),
    # A specific attachment object (ie, metadata) belonging to a given object in a given model.
    path(
        "attachments/<model>/<instance>/<attachment>",
        AttachmentDetail.as_view(),
    ),
    # The actual attachment file
    path(
        "attachments/<model>/<instance>/<attachment>/download",
        AttachmentDetail.as_view(),
        name="download_attachment",
    ),
    # Object models and their endpoints.
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
