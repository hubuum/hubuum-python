"""Models for the hubuum project."""
# from datetime import datetime
from django.contrib.auth.models import Group
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from rest_framework.exceptions import NotFound

from hubuum.permissions import fully_qualified_operations
from hubuum.tools import get_model
from hubuum.validators import validate_model, validate_url


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


def object_supports_extensions(obj):
    """Check if an object supports extensions."""
    return isinstance(obj, NamespacedHubuumModelWithExtensions)


class HubuumModel(models.Model):
    """Base model for Hubuum Objects."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def supports_extensions(cls):
        """Check if a class supports extensions."""
        return issubclass(cls, ExtensionsModel)

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    class Meta:
        """Meta data for the class."""

        abstract = True


class ExtensionsModel(models.Model):
    """A model that supports extensions."""

    def extensions(self):
        """List all extensions registered for the model."""
        model_name = self._meta.model_name  # pylint: disable=protected-access
        return Extension.objects.filter(model=model_name)

    def extension_data(self):
        """Return the data for each extension the object has."""
        extension_data = {}
        #        extensions_needing_updates = []
        relevant_extensions = self.extensions()

        for extension in relevant_extensions:
            #            if self._extension_data_needs_updating(extension):
            #                extensions_needing_updates.append(extension)

            #        if extensions_needing_updates:
            #            self._update_extension_data(extensions_needing_updates)

            content_type = ContentType.objects.get(model=extension.model).id
            extension_data_obj = ExtensionData.objects.filter(
                extension=extension.id,
                object_id=self.id,
                content_type=content_type,
            ).first()

            if extension_data_obj:
                extension_data[extension.name] = extension_data_obj.json_data
            else:
                extension_data[extension.name] = None

        return extension_data

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

    def get_permissions_for_group(self, group: Group, raise_exception=True):
        """Try to find a permission object for the given group.

        param: group (Group instance)
        param: raise_exception (True)

        returns: permission object

        raises: NotFound if raise_exception is True and no object is found
        """
        try:
            obj = Permission.objects.get(namespace=self, group=group)
            return obj
        except Permission.DoesNotExist as exc:
            if raise_exception:
                raise NotFound() from exc

        return None

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

    name = models.CharField(max_length=255, null=False)
    model = models.CharField(max_length=255, null=False, validators=[validate_model])
    url = models.CharField(max_length=255, null=False, validators=[validate_url])
    require_interpolation = models.BooleanField(default=True, null=False)
    header = models.CharField(max_length=512)
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


class HostType(NamespacedHubuumModelWithExtensions):
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


class Jack(NamespacedHubuumModelWithExtensions):
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


class Person(NamespacedHubuumModelWithExtensions):
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


class PurchaseDocuments(NamespacedHubuumModelWithExtensions):
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


class PurchaseOrder(NamespacedHubuumModelWithExtensions):
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


class Room(NamespacedHubuumModelWithExtensions):
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


class Vendor(NamespacedHubuumModelWithExtensions):
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
