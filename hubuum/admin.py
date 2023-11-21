"""Set up the admin site with the models we want to allow access to."""


from django.contrib import admin

from hubuum.models.core import Attachment, AttachmentManager, HubuumClass, HubuumObject
from hubuum.models.iam import Namespace, Permission, User

admin.site.register(
    [
        HubuumClass,
        HubuumObject,
        Namespace,
        Permission,
        User,
        Attachment,
        AttachmentManager,
    ]
)
