"""Filters for hubuum permissions."""
from rest_framework import filters

from hubuum.models.base import Permission, model_is_open


class HubuumObjectPermissionsFilter(filters.BaseFilterBackend):
    """Return viewable objects for a user.

    This filter returns (request.)user-visible objects of a model in question.
    """

    def filter_queryset(self, request, queryset, view):
        """Perform the filtering."""
        # print("Filtering")
        user = request.user
        # model = queryset.model._meta.model_name
        #        permission = self.perm_format % {
        #            "app_label": queryset.model._meta.app_label,
        #            "model_name": queryset.model._meta.model_name,
        #        }

        #    Find all namespaces we can perform the given operation in.

        #        print("List of {}".format(model))
        model_name = queryset.model._meta.model_name  # pylint: disable=protected-access
        if user.is_admin() or model_is_open(model_name):
            return queryset

        res = Permission.objects.filter(
            has_read=True, group__in=user.groups.all()
        ).values_list("namespace", flat=True)
        # print(res)
        # print(queryset)
        if model_name == "namespace":
            filtered = queryset.filter(pk__in=res)
        else:
            filtered = queryset.filter(namespace__in=res)
        # print(filtered)
        return filtered


#        return get_objects_for_user(user, permission, queryset, **self.shortcut_kwargs)
