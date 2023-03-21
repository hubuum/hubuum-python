"""Set up the admin site with the models we want to allow access to."""

from django.contrib import admin

from hubuum.models.base import (
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
]
admin.site.register(models)
