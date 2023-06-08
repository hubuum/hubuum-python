# Meta is a bit bugged: https://github.com/microsoft/pylance-release/issues/3814
# pyright: reportIncompatibleVariableOverride=false
"""Resource models.

These models are the ones used by end users to create objects in Hubuum.
"""

from django.db import models

from hubuum.models.iam import NamespacedHubuumModelWithExtensions


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

    class Meta:
        """Meta for the model."""

        ordering = ["id"]

    def __str__(self):
        """Stringify the object, used to represent the object towards users."""
        return self.name


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

    class Meta:
        """Meta for the model."""

        ordering = ["id"]

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

    class Meta:
        """Meta for the model."""

        ordering = ["id"]


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

    class Meta:
        """Meta for the model."""

        ordering = ["id"]


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

    class Meta:
        """Meta for the model."""

        ordering = ["id"]

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

    class Meta:
        """Meta for the model."""

        ordering = ["id"]

    def __str__(self):
        """Stringify the object, used to represent the object towards users."""
        return self.room_id


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

    class Meta:
        """Meta for the model."""

        ordering = ["id"]

    def __str__(self):
        """Stringify the object, used to represent the object towards users."""
        return self.vendor_name
