"""Generic exceptions for hubuum."""

from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import APIException


class MissingParam(Exception):
    """An exception thrown when a parameter is missing, or the param lacks a value."""


class InvalidParam(Exception):
    """An exception thrown when a parameter is invalid."""


class Conflict(APIException):
    """Thrown when trying to overwrite an existing object."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = _("Resource already exists.")
    default_code = "resource_exists"


class UnsupportedAttachmentModelError(APIException):
    """Thrown when trying to attach a file to a model that does not support attachments."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "The specified model does not support attachments."


class AttachmentsNotEnabledError(APIException):
    """Thrown when trying to attach a file to an object that does not support attachments."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Attachments are not enabled for this object."


class InvalidRequestDataError(APIException):
    """Thrown when the request data is invalid."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Invalid request data."


class ObjectDoesNotExistError(APIException):
    """Thrown when the specified object does not exist."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "The specified object does not exist."


class AttachmentCountLimitExceededError(APIException):
    """Thrown when the number of attachments would exceed the limit."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Attachment count reached for the object."


class AttachmentSizeLimitExceededError(APIException):
    """Thrown when the size of attachments would exceed the limit."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Total attachment size reached for the object."


class AttachmentTooBig(APIException):
    """Thrown when the size of an individual attachment is too big."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Attachment is too big."
