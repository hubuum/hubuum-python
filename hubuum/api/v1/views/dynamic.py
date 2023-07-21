"""Views for the resources in API v1."""

from rest_framework.exceptions import NotFound
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.schemas.openapi import AutoSchema

from hubuum.api.v1.serializers import DynamicClassSerializer, DynamicObjectSerializer
from hubuum.filters import DynamicClassFilterSet, DynamicObjectFilterSet
from hubuum.models.dynamic import DynamicClass, DynamicObject

from .base import LoggingMixin


class DynamicAutoSchema(AutoSchema):
    """Custom AutoSchema for generating unique operation IDs for the dynamic views.

    The generated operation IDs will utilize specific path parameters to ensure uniqueness.
    """

    def get_operation_id(self, path: str, method: str) -> str:
        """Generate a unique operation ID by appending specific path parameters to the base ID.

        :param path: The path of the current route.
        :param method: The HTTP method of the current route.

        :return: The unique operation ID for the route.
        """
        path = (
            path.strip("/")
            .replace("/", "_")
            .replace("<", "")
            .replace(">", "")
            .replace("{", "")
            .replace("}", "")
        )
        name = self.view.get_view_name().lower().replace(" ", "_")
        method_name = getattr(self.view, "action", method.lower())
        operation_id = f"{name}_{method_name}_{path}"
        return operation_id


class DynamicBaseView(LoggingMixin):
    """Base view for user defined classes and objects."""

    schema = DynamicAutoSchema(
        tags=["Resources"],
    )


class DynamicListView(DynamicBaseView, ListCreateAPIView):  # type: ignore
    """List view for user defined classes and objects."""

    pass


class DynamicDetailView(DynamicBaseView, RetrieveUpdateDestroyAPIView):  # type: ignore
    """Detail view for user defined classes and objects."""

    def get_object(self):
        """Return the object the view is displaying.

        Note:
        ----
            Overridden to handle lookup by either `id` or `name`.
        """
        queryset = self.filter_queryset(self.get_queryset())

        # Get the lookup value from the URL parameters.
        lookup_value = self.kwargs["pk"]

        try:
            # Attempt to use the lookup value as an ID.
            obj = queryset.get(id=int(lookup_value))
        except (
            ValueError,
            TypeError,
            DynamicClass.DoesNotExist,
            DynamicObject.DoesNotExist,
        ):
            # If that fails, try to use it as a name.
            try:
                obj = queryset.get(name=lookup_value)
            except (DynamicObject.DoesNotExist, DynamicClass.DoesNotExist) as exc:
                raise NotFound(
                    f"No {queryset.model.__name__} found with ID or name {lookup_value}"
                ) from exc

        # Check object permissions.
        self.check_object_permissions(self.request, obj)

        return obj


class DynamicClassList(DynamicListView):
    """Get: List user defined classes. Post: Add a new user defined class."""

    queryset = DynamicClass.objects.all().order_by("id")
    serializer_class = DynamicClassSerializer
    filterset_class = DynamicClassFilterSet


class DynamicClassDetail(DynamicDetailView):
    """Get, Patch, or Destroy a user defined class."""

    queryset = DynamicClass.objects.all().order_by("id")
    serializer_class = DynamicClassSerializer


class DynamicObjectList(DynamicListView):
    """Get or Post a user defined object.

    Get: List all objects of a specific user defined class.
    Post: Add a new object to a user defined class.

    Requires a `classname` in the URL.
    """

    queryset = DynamicObject.objects.all().order_by("id")
    serializer_class = DynamicObjectSerializer
    filterset_class = DynamicObjectFilterSet

    def get_queryset(self):
        """Get the queryset for this view.

        This is overridden to filter by the classname.
        Requires a `classname` in the URL.
        """
        # This is an issue with generateschema, so we need to check if the request exists
        if not self.request:
            return DynamicObject.objects.none()

        classname = self.kwargs["classname"]
        return DynamicObject.objects.filter(dynamic_class__name=classname).order_by(
            "id"
        )

    def perform_create(self, serializer) -> None:  # type: ignore
        """Perform the create operation.

        Overridden to get the `DynamicClass` instance from the `classname` in the URL
        and add it to the validated data.
        """
        classname = self.kwargs["classname"]

        try:
            # Attempt to retrieve the DynamicClass using `classname` as an ID
            dynamic_class = DynamicClass.objects.get(id=int(classname))
        except (ValueError, DynamicClass.DoesNotExist):
            # If `classname` cannot be cast to an integer, try retrieving it as a name
            try:
                dynamic_class = DynamicClass.objects.get(name=classname)
            except DynamicClass.DoesNotExist as exc:
                raise NotFound(
                    f"No DynamicClass found with ID or name '{classname}'"
                ) from exc

        serializer.save(dynamic_class=dynamic_class)


class DynamicObjectDetail(DynamicDetailView):
    """Get, Patch, or Destroy an object from a user defined class.

    Requires a `classname` and `pk` in the URL.
    """

    queryset = DynamicObject.objects.all().order_by("id")
    serializer_class = DynamicObjectSerializer

    def get_queryset(self):
        """Get the queryset for this view.

        This is overridden to filter by the classname.
        Requires a `classname` in the URL along with the `pk`.
        """
        # This is an issue with generateschema, so we need to check if the request exists
        if not self.request:
            return DynamicObject.objects.none()

        classname = self.kwargs["classname"]
        return DynamicObject.objects.filter(dynamic_class__name=classname).order_by(
            "id"
        )
