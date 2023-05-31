"""Set up the admin site with the models we want to allow access to."""

from typing import List, Type

from django.contrib import admin

from hubuum.models.core import Extension, ExtensionData
from hubuum.models.iam import HubuumModel, Namespace, Permission, User
from hubuum.models.resources import (
    Host,
    HostType,
    Jack,
    Person,
    PurchaseOrder,
    Room,
    Vendor,
)

models: List[Type[HubuumModel]] = [
    User,
    Host,
    HostType,
    Person,
    Room,
    Jack,
    Vendor,
    PurchaseOrder,
    Namespace,
    Permission,
    Extension,
    ExtensionData,
]
admin.site.register(models)
