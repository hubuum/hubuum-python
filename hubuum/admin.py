"""Set up the admin site with the models we want to allow access to."""

from django.contrib import admin

from hubuum.models.core import Extension, ExtensionData
from hubuum.models.permissions import Namespace, Permission
from hubuum.models.resources import (
    Host,
    HostType,
    Jack,
    Person,
    PurchaseDocuments,
    PurchaseOrder,
    Room,
    Vendor,
)

models = [
    Host,
    HostType,
    Person,
    Room,
    Jack,
    Vendor,
    PurchaseOrder,
    PurchaseDocuments,
    Namespace,
    Permission,
    Extension,
    ExtensionData,
]
admin.site.register(models)
