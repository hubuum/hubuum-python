"""Models for the hubuum project."""
# from datetime import datetime
import re

from django.apps import apps
from django.contrib.auth.models import AbstractUser, Group
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from rest_framework.exceptions import NotFound, ValidationError

from hubuum.exceptions import MissingParam
from hubuum.permissions import fully_qualified_operations, operation_exists


def get_model(model):
    """Return the model from a string. Raises ValueError on error."""
    return apps.get_model("hubuum", model)


def model_exists(model):
    """Check if a given model exists by name."""
    try:
        apps.get_model("hubuum", model)
    except LookupError:
        return False

    return True


def model_is_open(model):
    """Check if the model is an open model."""
    return model in models_that_are_open()


def models_that_are_open():
    """Return a list of models open to all authenticated users."""
    return ("user", "group")


def model_supports_extensions(model):
    """Check if a model supports extensions."""
    if isinstance(model, str):
        model = get_model(model)

    return issubclass(model, ExtensionsModel)


class User(AbstractUser):
    """Extension to the default User class."""

    model_permissions_pattern = re.compile(
        r"^hubuum.(create|read|update|delete|namespace)_(\w+)$"
    )
    lookup_fields = ["id", "username", "email"]

    _group_list = None

    def is_admin(self):
        """Check if the user is any type of admin (staff/superadmin) (or in a similar group?)."""
        return self.is_staff or self.is_superuser

    @property
    def group_list(self):
        """List the names of all the groups the user is a member of."""
        if self._group_list is None:
            self._group_list = list(self.groups.values_list("name", flat=True))
        return self._group_list

    def group_count(self):
        """Return the number of groups the user is a member of."""
        return self.groups.count()

    def has_only_one_group(self):
        """Return true if the user is a member of only one group."""
        return self.group_count() == 1

    def is_member_of(self, group):
        """Check if the user is a member of a specific group."""
        return self.is_member_of_any([group])

    def is_member_of_any(self, groups):
        """Check to see if a user is a member of any of the groups in the list."""
        return bool([i for i in groups if i in self.groups.all()])

    def namespaced_can(self, perm, namespace) -> bool:
        """Check to see if the user can perform perm for namespace.

        param: perm (permission string, 'has_[create|read|update|delete|namespace])
        param: namespace (namespace object)
        return True|False
        """
        if not operation_exists(perm, fully_qualified=True):
            raise MissingParam(f"Unknown permission '{perm}' passed to namespaced_can.")

        # We need to check if the user is a member of a group
        # that has the given permission the namespace.
        groups = namespace.groups_that_can(perm)
        return self.is_member_of_any(groups)

    def has_namespace(
        self,
        namespace,
        write_perm="has_namespace",
    ):
        """Check if the user has namespace permissions for the given namespace.

        Only admin users can create or populate root namespaces.

        For users, if the namespace isn't scoped (contains no dots), return False.
        Otherwise, check if the user can:
          - create the namespace (using has_namespace) or,
          - create objects in the namespace (using has_create) on the last element.
        """
        if isinstance(namespace, int):
            try:
                namespace_obj = Namespace.objects.get(pk=namespace)
                return self.namespaced_can(write_perm, namespace_obj)
            except Namespace.DoesNotExist as exc:
                raise NotFound from exc

        scope = namespace.split(".")
        if len(scope) == 1:
            return False

        if write_perm == "has_namespace":
            target = scope[-2]

        try:
            namespace_obj = Namespace.objects.get(name=target)
        except Namespace.DoesNotExist as exc:
            raise NotFound from exc

        return self.namespaced_can(write_perm, namespace_obj)

    #        try:
    #            parent = Namespace.objects.get(name=scope[-1])
    #        except Namespace.DoesNotExist:
    #            return False

    #        return Permission.objects.filter(
    #            namespace=parent.id, has_namespace=True, group__in=self.groups.all()
    #        ).exists()

    def has_perm(self, perm: str, obj: object = None) -> bool:
        """
        Model (?) permissions check for an object.

        perm: see permissions.py
        obj: Hubuum Object
        """
        field = None

        try:
            operation, model = re.match(User.model_permissions_pattern, perm).groups()
        except AttributeError as exc:
            raise MissingParam(
                f"Unknown permission '{perm}' passed to has_perm"
            ) from exc

        if operation_exists(operation) and model_exists(model):
            field = "has_" + operation
        else:
            raise MissingParam(
                f"Unknown operation or model '{operation} / {model}' passed to has_perm"
            )

        # We should always get an object to test against.
        if obj:
            return Permission.objects.filter(
                namespace=obj.namespace, **{field: True}, group__in=self.groups.all()
            ).exists()

        return False


class HubuumModel(models.Model):
    """Base model for Hubuum Objects."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    class Meta:
        """Meta data for the class."""

        abstract = True


class ExtensionsModel(models.Model):  # pylint: disable=too-few-public-methods
    """A model that supports extensions."""

    #    def extensions(self):
    #        """List all extensions registered for the model."""
    #        model_name = self._meta.model_name  # pylint: disable=protected-access
    #        return Extension.objects.filter(model=model_name)

    class Meta:
        """Meta data for the class."""

        abstract = True


class NamespacedHubuumModel(HubuumModel):
    """Base model for a namespaced Hubuum Objects."""

    # When we delete a namespace, do we want *all* the objects to disappear?
    # That'd be harsh. But, well... What is the realistic option?
    namespace = models.ForeignKey(
        "Namespace",
        on_delete=models.CASCADE,
        blank=False,
        null=False,
    )

    class Meta:
        """Meta data for the class."""

        abstract = True


class NamespacedHubuumModelWithExtensions(NamespacedHubuumModel, ExtensionsModel):
    """An abstract model that provides Namespaces and Extensions."""

    class Meta:
        """Meta data for the class."""

        abstract = True


class Namespace(HubuumModel):
    """The namespace ('domain') of an object."""

    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)

    def grant_all(self, group):
        """Grant all permissions to the namespace to the given group."""
        create = {}
        create["namespace"] = self
        create["group"] = group
        for perm in fully_qualified_operations():
            create[perm] = True
        Permission.objects.update_or_create(**create)
        return True

    def groups_that_can(self, perm):
        """Fetch groups that can perform a specific permission.

        param: perm (permission string, 'has_[read|create|update|delete|namespace])
        return [group objects] (may be empty)
        """
        qs = Permission.objects.filter(namespace=self.id, **{perm: True}).values(
            "group"
        )
        groups = Group.objects.filter(id__in=qs)
        return groups


class Permission(HubuumModel):
    """
    Permissions in Hubuum.

    - Permissions are set by group.
    - Objects belong to a namespace.
    - Every namespace has zero or more groups with permissions for the namespace.

    The permission `has_namespace` allows for the group to create new namespaces scoped
    under the current one.

    """

    # If the namespace the permission points to goes away, clear the entry.
    namespace = models.ForeignKey(
        "Namespace", related_name="p_namespace", on_delete=models.CASCADE
    )
    # If the group the permission uses goes away, clear the entry.
    group = models.ForeignKey(
        "auth.Group", related_name="p_group", on_delete=models.CASCADE
    )

    has_create = models.BooleanField(null=False, default=False)
    has_read = models.BooleanField(null=False, default=False)
    has_update = models.BooleanField(null=False, default=False)
    has_delete = models.BooleanField(null=False, default=False)
    has_namespace = models.BooleanField(null=False, default=False)

    class Meta:
        """Metadata permissions."""

        unique_together = ("namespace", "group")


class Extension(NamespacedHubuumModel):
    """An extension to a specific model.

    For now, it is implied that the extension uses REST.
    """

    def validate_model(self, data):
        """Validate that the textual name of the model is valid.

        Requirements:
         - Is a string.
         - Resolves as the name of a Hubuum model.
        """
        if not isinstance(data["model"], str):
            raise ValidationError({"model": "The model name must be a string."})

        model_name = data["model"]
        if not model_exists(model_name):
            raise ValidationError({"model": "No such model"})

        if not model_supports_extensions(model_name):
            raise ValidationError({"model": "Model does not support extensions."})

        return data

    name = models.CharField(max_length=255, null=False)
    model = models.CharField(max_length=255, null=False)
    url = models.CharField(max_length=255, null=False)
    header = models.CharField(max_length=255)
    cache_time = models.PositiveSmallIntegerField(default=60)


class ExtensionData(NamespacedHubuumModel):
    """A model for the extensions data for objects.

    Note that the object_id refers to an object of the appropriate model.
    https://docs.djangoproject.com/en/4.1/ref/contrib/contenttypes/#generic-relations
    """

    extension = models.ForeignKey("Extension", on_delete=models.CASCADE, null=False)

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    json_data = models.JSONField(null=True)

    class Meta:
        """Meta for the model."""

        unique_together = ("extension", "content_type", "object_id")


class Host(NamespacedHubuumModelWithExtensions):
    """Host model, a portal into hosts of any kind."""

    name = models.CharField(max_length=255)
    fqdn = models.CharField(max_length=255, blank=True)
    type = models.ForeignKey(
        "HostType",
        on_delete=models.DO_NOTHING,
        related_name="hosts",
        blank=True,
        null=True,
    )
    serial = models.CharField(max_length=255, blank=True)
    registration_date = models.DateTimeField(auto_now_add=True)
    room = models.ForeignKey(
        "Room", on_delete=models.DO_NOTHING, related_name="hosts", blank=True, null=True
    )
    jack = models.ForeignKey(
        "Jack", on_delete=models.DO_NOTHING, related_name="hosts", blank=True, null=True
    )
    purchase_order = models.ForeignKey(
        "PurchaseOrder",
        on_delete=models.DO_NOTHING,
        related_name="hosts",
        blank=True,
        null=True,
    )

    person = models.ForeignKey(
        "Person",
        on_delete=models.DO_NOTHING,
        related_name="hosts",
        blank=True,
        null=True,
    )

    def __str__(self):
        """Stringify the object, used to represent the object towards users."""
        return self.name


# Unique names sounds like a good idea, but "bob's laptop" might happen repeatedly.
# Serial numbers are also only vendor-unique...
#    class Meta:
#        constraints = [
#            models.UniqueConstraint(
#                fields=['name'], name="unique_hostname_constraint",
#            )
#        ]


# class ExternalSource(models.Model):
#     service_name = models.CharField(max_length=255)
#     web_url = models.CharField(max_length=255, blank=True, null=True)
#     api_url = models.CharField(max_length=255, blank=True, null=True)

#     def __str__(self):
#         """Stringify the object, used to represent the object towards users."""
#         return self.service_name


# class DetectedHostData(models.Model):
#     host_id = models.OneToOneField(
#         Host, verbose_name="Host identifier", on_delete=models.CASCADE
#     )
#     source = models.OneToOneField(ExternalSource, on_delete=models.CASCADE)
#     fqdn = models.CharField(max_length=255, blank=True, null=True)
#     serial_number = models.CharField(max_length=50, blank=True, null=True)
#     mac = models.CharField(
#         max_length=20, blank=True, null=True
#     )  # https://github.com/django-macaddress/django-macaddress
#     ipv4_address = models.GenericIPAddressField(blank=True, null=True, protocol="IPv4")
#     ipv6_address = models.GenericIPAddressField(blank=True, null=True, protocol="IPv6")
#     memory = models.IntegerField(blank=True, null=True)
#     cpu = models.CharField(max_length=50, blank=True, null=True)
#     arch = models.CharField(max_length=10, blank=True, null=True)
#     model = models.CharField(max_length=50, blank=True, null=True)
#     vendor = models.CharField(max_length=50, blank=True, null=True)
#     os = models.CharField(max_length=20, blank=True, null=True)
#     os_major_version = models.SmallIntegerField(blank=True, null=True)
#     os_minor_version = models.SmallIntegerField(blank=True, null=True)
#     os_patch_version = models.SmallIntegerField(blank=True, null=True)
#     last_fetched = models.DateTimeField(blank=True, null=True)
#     switch = models.CharField(max_length=255, blank=True, null=True)
#     port = models.CharField(max_length=30, blank=True, null=True)
#     display = models.CharField(max_length=50, blank=True, null=True)
#     primary_user = models.CharField(max_length=50, blank=True, null=True)

#     class Meta:
#         verbose_name_plural = "detected host Data"
#         constraints = [
#             models.UniqueConstraint(
#                 fields=["host_id", "source"], name="host_id_and_source_combination"
#             )
#         ]

#     def __str__(self):
#         """Stringify the object, used to represent the object towards users."""
#         return Host.objects.get(pk=self.id).name + "+" + self.source

#     # Should also support other identifiers?
#     @staticmethod
#     def get_externals_for_host(hostid):
#         try:
#             objects = DetectedHostData.objects.get(hostid=hostid)
#         except DetectedHostData.DoesNotExist:
#             objects = []
#         return DetectedHostData.objects.get(hostid=hostid)


class HostType(NamespacedHubuumModel):
    """The type of hosts supported.

    These are a touple of a short name and a description, ie:

    name: mac_laptop
    description: An Apple Laptop running MacOS

    or

    name: std_office_computer
    description: A standard office computer running RHEL
    """

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    def __str__(self):
        """Stringify the object, used to represent the object towards users."""
        return self.name


class Jack(NamespacedHubuumModel):
    """The wall end of a network jack.

    Like the marking of power outlets, there are standards for such things.
    In Norway, the relevant standard is NS 3457-7.
    https://www.standard.no/fagomrader/bygg-anlegg-og-eiendom/ns-3420-/klassifikasjon-av-byggverk---ns-3457/

    Typically, a jack exists in a room. You an also set a building if your room
    identifier by itself isn't unique.
    """

    name = models.CharField(max_length=255)
    room = models.ForeignKey(
        "Room", models.CASCADE, db_column="room", blank=True, null=True
    )
    building = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        """Stringify the object, used to represent the object towards users."""
        return self.name


class Person(NamespacedHubuumModel):
    """A person.

    Persons have rooms. Computers may have people. It's all very cozy.
    """

    username = models.CharField(max_length=255)
    room = models.ForeignKey(
        "Room", models.CASCADE, db_column="room", blank=True, null=True
    )
    section = models.IntegerField(blank=True, null=True)
    department = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    office_phone = models.CharField(max_length=255, blank=True, null=True)
    mobile_phone = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        """Stringify the object, used to represent the object towards users."""
        return self.username


class PurchaseDocuments(NamespacedHubuumModel):
    """Accounting, the documents of an order.

    The documents that came with a given purchase order.
    """

    document_id = models.CharField(max_length=255)
    purchase_order = models.ForeignKey(
        "PurchaseOrder", models.CASCADE, blank=False, null=False
    )
    document = models.BinaryField(blank=False, null=False)

    class Meta:
        """Set permissions and other metadata."""

        verbose_name_plural = "purchase documents"

    def __str__(self):
        """Stringify the object, used to represent the object towards users."""
        return self.document_id


class PurchaseOrder(NamespacedHubuumModel):
    """Accounting, the order.

    When something is bought there is typically some identifier for the purchase.
    This may help you when it comes to service and maintenance.
    Or disputes about money.
    """

    vendor = models.ForeignKey(
        "Vendor", models.CASCADE, db_column="vendor", blank=True, null=True
    )
    order_date = models.DateTimeField(blank=True, null=True)
    po_number = models.CharField(max_length=255, blank=False, null=False)

    def __str__(self):
        """Stringify the object, used to represent the object towards users."""
        return str(self.po_number)


class Room(NamespacedHubuumModel):
    """A room.

    Possibly with a view. If your room_id contains a floor or building identifier, feel free to
    ignore the those fields. If your organization repeats room identifiers between buildings,
    you have my sympathies. If they repeat the room identifier per floor, well, ouch.
    """

    room_id = models.CharField(max_length=255)
    building = models.CharField(max_length=255, blank=True, null=True)
    floor = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        """Stringify the object, used to represent the object towards users."""
        return self.building + "-" + self.floor.rjust(2, "0") + "-" + self.room_id


class Vendor(NamespacedHubuumModel):
    """A vendor, they sell you things.

    Say thank you. Call your vendor today.
    """

    vendor_name = models.CharField(max_length=255)
    vendor_url = models.URLField()
    vendor_credentials = models.CharField(max_length=255, blank=True, null=True)
    contact_name = models.CharField(max_length=255, blank=True, null=True)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        """Stringify the object, used to represent the object towards users."""
        return self.vendor_name
