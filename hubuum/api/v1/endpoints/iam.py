"""IAM URLs for hubuum API v1."""

from django.urls import path

from hubuum.api.v1.views.iam import (
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

urlpatterns = [
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
]
