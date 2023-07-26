"""Views for the resources in API v1."""

from typing import Any, Dict, Tuple

from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import NotFound
from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveDestroyAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.response import Response
from rest_framework.schemas.openapi import AutoSchema

from hubuum.api.v1.serializers import (
    DynamicClassSerializer,
    DynamicLinkSerializer,
    DynamicObjectSerializer,
    LinkTypeSerializer,
    PathSerializer,
)
from hubuum.api.v1.views.base import LoggingMixin
from hubuum.exceptions import Conflict
from hubuum.filters import DynamicClassFilterSet, DynamicObjectFilterSet
from hubuum.models.dynamic import DynamicClass, DynamicLink, DynamicObject, LinkType
from hubuum.models.iam import Namespace
from hubuum.permissions import NameSpace as NamespacePermission


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
    permission_classes = (NamespacePermission,)


class DynamicListView(DynamicBaseView, ListCreateAPIView):  # type: ignore
    """List view for user defined classes and objects."""


class DynamicDetailView(DynamicBaseView, RetrieveUpdateDestroyAPIView):  # type: ignore
    """Detail view for user defined classes and objects."""


class DynamicClassList(DynamicListView):
    """Get: List user defined classes. Post: Add a new user defined class."""

    queryset = DynamicClass.objects.all().order_by("name")
    serializer_class = DynamicClassSerializer
    filterset_class = DynamicClassFilterSet


class DynamicClassDetail(DynamicDetailView):
    """Get, Patch, or Destroy a user defined class."""

    queryset = DynamicClass.objects.all()
    serializer_class = DynamicClassSerializer
    lookup_field = "name"

    def get_object(self):
        """Override to use `classname` instead of `name`."""
        queryset = self.get_queryset()
        filter_kwargs = {"name": self.kwargs["classname"]}
        obj = get_object_or_404(queryset, **filter_kwargs)
        return obj


class DynamicObjectList(DynamicListView):
    """Get or Post a user defined object.

    Get: List all objects of a specific user defined class.
    Post: Add a new object to a user defined class.

    Requires a `classname` in the URL.
    """

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
            "name"
        )

    def perform_create(self, serializer) -> None:  # type: ignore
        """Perform the create operation.

        Overridden to get the `DynamicClass` instance from the `classname` in the URL
        and add it to the validated data.
        """
        classname = self.kwargs["classname"]

        try:
            dynamic_class = DynamicClass.objects.get(name=classname)
        except DynamicClass.DoesNotExist as exc:
            raise NotFound(f"No DynamicClass found with name '{classname}'") from exc

        serializer.save(dynamic_class=dynamic_class)


class DynamicObjectDetail(DynamicDetailView):
    """Get, Patch, or Destroy an object from a user defined class.

    Requires a `classname` and `obj` in the URL.
    """

    queryset = DynamicObject.objects.all()
    serializer_class = DynamicObjectSerializer

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> Response:
        """Get the queryset for this view.

        This is overridden to filter by the classname.
        Requires a `classname` in the URL along with the `obj`.
        """
        # This is an issue with generateschema, so we need to check if the request exists
        if not self.request:  # pragma: no cover
            return DynamicObject.objects.none()

        obj = get_object_or_404(
            self.queryset,
            dynamic_class__name=self.kwargs["classname"],
            name=self.kwargs["obj"],
        )

        serializer = self.get_serializer(obj)
        return Response(serializer.data)


class LinkTypeView(RetrieveUpdateDestroyAPIView):  # type: ignore
    """Get, Patch, or Destroy a link type between two classes."""

    schema = DynamicAutoSchema(
        tags=["Resources"],
    )

    queryset = LinkType.objects.all()
    serializer_class = LinkTypeSerializer
    permission_classes = (NamespacePermission,)

    def get_object(self):
        """Return the object the view is displaying."""
        queryset = self.get_queryset()
        source_class_name = self.kwargs.get("source_class")
        target_class_name = self.kwargs.get("target_class")

        obj = queryset.filter(
            source_class__name=source_class_name, target_class__name=target_class_name
        ).first()

        if not obj:
            raise NotFound("No link type exists between these classes")
        return obj

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> Response:
        """Create a new link type between two classes."""
        source_class_name = self.kwargs.get("source_class")
        target_class_name = self.kwargs.get("target_class")
        namespace_id = request.data.get("namespace")
        max_links = request.data.get("max_links")

        try:
            source_class = DynamicClass.objects.get(name=source_class_name)
        except DynamicClass.DoesNotExist as exc:
            raise NotFound("The class '{source_class_name}' does not exist.") from exc

        try:
            target_class = DynamicClass.objects.get(name=target_class_name)
        except DynamicClass.DoesNotExist as exc:
            raise NotFound(f"The class '{target_class_name}' does not exist.") from exc

        try:
            namespace = Namespace.objects.get(id=namespace_id)
        except Namespace.DoesNotExist as exc:
            raise NotFound(
                f"The namespace with ID '{namespace_id}' does not exist."
            ) from exc

        try:
            LinkType.objects.get(
                source_class=source_class,
                target_class=target_class,
            )
            raise Conflict("A link type already exists between these classes.")
        except LinkType.DoesNotExist:
            link_type = LinkType.objects.create(
                source_class=source_class,
                target_class=target_class,
                namespace=namespace,
                max_links=max_links,
            )

            return Response(self.get_serializer(link_type).data, status=201)


class DynamicLinkListView(ListCreateAPIView):  # type: ignore
    """DynamicLinkListView handles the API endpoints for listing and creating dynamic links.

    Methods
    -------
    - get_queryset: retrieves the queryset based on class name and object name/id
    """

    schema = DynamicAutoSchema(
        tags=["Resources"],
    )

    permission_classes = (NamespacePermission,)

    def _query_param_is_true(self, param: str) -> bool:
        """Check if a query parameter is set to true."""
        if not self.request:  # pragma: no cover
            return False
        return self.request.query_params.get(param, "").lower() == "true"

    def get_serializer_class(self):
        """Return the serializer class based on the query parameters."""
        if self._query_param_is_true("transitive"):
            return PathSerializer
        return DynamicObjectSerializer

    def get_queryset(self):  # type: ignore
        """Override the get_queryset method to return DynamicLinks for a given source object.

        The source object can be defined by its class name and its name.

        Raises NotFound error if the source object does not exist or has no links.
        """
        if not self.request:  # pragma: no cover
            return DynamicLink.objects.none()

        classname = self.kwargs.get("classname")
        obj = self.kwargs.get("obj")
        targetclass = self.kwargs.get("targetclass")

        transitive = self._query_param_is_true("transitive")
        max_depth = int(self.request.query_params.get("max-depth", 0))

        extra_query = {}
        if targetclass:
            extra_query = {"target__dynamic_class__name": targetclass}

        if transitive:
            try:
                source = DynamicObject.objects.get(
                    dynamic_class__name=classname,
                    name=obj,
                )
            except DynamicObject.DoesNotExist as exc:
                raise NotFound(
                    f"Source object '{classname}:{obj}' does not exist."
                ) from exc

            try:
                target_class = DynamicClass.objects.get(name=targetclass)
            except DynamicClass.DoesNotExist as exc:
                raise NotFound(
                    f"The target class '{targetclass}' does not exist."
                ) from exc

            transitive_objects_and_paths = source.find_transitive_links(
                target_class, max_depth=max_depth
            )

            if not transitive_objects_and_paths:
                max_depth_string = ""
                if max_depth > 0:
                    max_depth_string = f" with max depth '{max_depth}'"

                raise NotFound(
                    f"No path from'{classname}:{obj}' to '{targetclass}'f{max_depth_string}."
                )

            return transitive_objects_and_paths

        dynamic_links = DynamicLink.objects.filter(
            link_type__source_class__name=classname,
            source__name=obj,
            **extra_query,
        )

        if dynamic_links.count() == 0:
            raise NotFound(
                "The specified source object does not exist or has no links."
            )

        # Return the target objects (not the links)
        return [link.target for link in dynamic_links]


class DynamicLinkDetailView(RetrieveDestroyAPIView):  # type: ignore
    """API endpoints for retrieving and deleting a specific dynamic link."""

    schema = DynamicAutoSchema(
        tags=["Resources"],
    )

    queryset = DynamicLink.objects.all()
    serializer_class = DynamicLinkSerializer
    permission_classes = (NamespacePermission,)

    def get_object(self):
        """Retrieve a specific DynamicLink.

        The source and target objects can be defined by their class names and their names.
        Raises NotFound error if the specified link does not exist.
        """
        classname = self.kwargs.get("classname")
        obj = self.kwargs.get("obj")
        targetclass = self.kwargs.get("targetclass")
        targetobject = self.kwargs.get("targetobject")

        try:
            dynamic_link = DynamicLink.objects.get(
                link_type__source_class__name=classname,
                link_type__target_class__name=targetclass,
                source__name=obj,
                target__name=targetobject,
            )
        except DynamicLink.DoesNotExist as exc:
            raise NotFound("The specified link does not exist.") from exc

        return dynamic_link

    def get(
        self, request: HttpRequest, *args: Dict[str, Any], **kwargs: Dict[str, Any]
    ) -> Response:
        """Get a specific DynamicLink between two objects."""
        return Response(self.get_serializer(self.get_object()).data)

    def delete(self, request: HttpRequest, *args: Any, **kwargs: Any) -> Response:
        """Delete a specific DynamicLink between two objects."""
        obj = self.get_object()
        obj.delete()
        return Response(status=204)

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> Response:
        """Create a new link between two objects."""
        classname = self.kwargs.get("classname")
        obj = self.kwargs.get("obj")
        targetclass = self.kwargs.get("targetclass")
        targetobject = self.kwargs.get("targetobject")
        namespace_id = int(request.data.get("namespace"))

        source_object, target_object, link_type, namespace = self.get_link_data(
            classname, obj, targetclass, targetobject, namespace_id
        )

        # Check how many links the source object already has to the target class
        # and compare it to the max_links allowed by the link type, if it's too high,
        # raise a 409 Conflict error
        source_links = DynamicLink.objects.filter(
            source=source_object,
            target__dynamic_class__name=targetclass,
        ).count()

        if link_type.max_links > 0 and source_links >= link_type.max_links:
            raise Conflict(
                (
                    f"The source object already has {source_links} links to the target class,"
                    f"which is the maximum allowed by the link type."
                )
            )

        try:
            DynamicLink.objects.get(
                source=source_object,
                target=target_object,
            )
            raise Conflict("A link already exists between these objects.")
        except DynamicLink.DoesNotExist:
            link = DynamicLink.objects.create(
                source=source_object,
                target=target_object,
                link_type=link_type,
                namespace=namespace,
            )

            return Response(self.get_serializer(link).data, status=201)

    def get_object_from_model(
        self, model: str, error_message: str, **filter_args: Any
    ) -> object:
        """Retrieve an object from the given model."""
        try:
            return model.objects.get(**filter_args)
        except model.DoesNotExist as exc:
            raise NotFound(error_message) from exc

    def get_link_data(
        self,
        classname: str,
        obj: str,
        targetclass: str,
        targetobject: str,
        namespace_id: int,
    ) -> Tuple[DynamicObject, DynamicObject, LinkType, Namespace]:
        """Retrieve the necessary data for link creation."""
        source_object = self.get_object_from_model(
            DynamicObject,
            "The specified source object does not exist.",
            dynamic_class__name=classname,
            name=obj,
        )

        target_object = self.get_object_from_model(
            DynamicObject,
            "The specified target object does not exist.",
            dynamic_class__name=targetclass,
            name=targetobject,
        )

        link_type = self.get_object_from_model(
            LinkType,
            f"No link defined between '{classname}' and '{targetclass}'.",
            source_class__name=classname,
            target_class__name=targetclass,
        )

        namespace = self.get_object_from_model(
            Namespace,
            f"The namespace with ID '{namespace_id}' does not exist.",
            id=namespace_id,
        )

        return source_object, target_object, link_type, namespace
