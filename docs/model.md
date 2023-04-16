# Hubuum Project Models Documentation

This documentation provides an overview of the models used in the Hubuum project, including their fields and relationships.

## HubuumModel

<a id="hubuummodel"></a>
**Inherits:** `models.Model`

The base model for all Hubuum objects. It provides the following fields:

- `created_at`: The date and time when the object was created, automatically set.
- `updated_at`: The date and time when the object was last updated, automatically set.

<a id="namespacedhubuummodel"></a>
## NamespacedHubuumModel

**Inherits:** [`HubuumModel`](#hubuummodel)

A base model for namespaced Hubuum objects. It provides the following fields:

- `namespace`: A foreign key to the `Namespace` model, which represents the namespace (domain) of the object.

## Extension

**Inherits:** [`NameSpacedHubuumModel`](#namespacedhubuummodel)

An extension to a specific model. It provides the following fields:

- `name`: A unique name for the extension.
- `model`: The name of the model that the extension applies to, validated with `validate_model`.
- `url`: The URL for the extension, validated with `validate_url`.
- `require_interpolation`: A boolean indicating if the URL requires interpolation.
- `header`: The header for the extension.
- `cache_time`: The time in seconds for which the extension's data should be cached.

## ExtensionData

**Inherits:** [`NameSpacedHubuumModel`](#namespacedhubuummodel)

A model for storing extension data for objects. It provides the following fields:

- `extension`: A foreign key to the `Extension` model.
- `content_type`: A foreign key to Django's built-in `ContentType` model.
- `object_id`: An integer representing the object's ID.
- `content_object`: A generic foreign key to the object.
- `json_data`: JSON data for the extension.

## ExtensionsModel

**Inherits:** `models.Model`

A model that supports extensions. It provides the following fields:

- `extension_data_objects`: A generic relation to the `ExtensionData` model.

<a id="namespacedhubuummodelwithextensions"></a>
## NamespacedHubuumModelWithExtensions

**Inherits:** `NamespacedHubuumModel`, `ExtensionsModel`

An abstract model that provides namespaces and extensions.

## Namespace

**Inherits:** [`HubuumModel`](#hubuummodel)

The namespace ('domain') of an object. It provides the following fields:

- `name`: A unique name for the namespace.
- `description`: A description of the namespace.

<a id="permission"></a>
## Permission

**Inherits:** [`HubuumModel`](#hubuummodel)

Permissions in Hubuum are set by group and objects belong to a namespace. Every namespace has zero or more groups with permissions for the namespace. It provides the following fields:

- `namespace`: A foreign key to the `Namespace` model.
- `group`: A foreign key to Django's built-in `Group` model.
- `has_create`: A boolean indicating if the group has create permission.
- `has_read`: A boolean indicating if the group has read permission.
- `has_update`: A boolean indicating if the group has update permission.
- `has_delete`: A boolean indicating if the group has delete permission.
- `has_namespace`: A boolean indicating if the group has namespace permission.

## Host

**Inherits:** [`NamespacedHubuumModelWithExtensions`](#namespacedhubuummodelwithextensions)

The `Host` model represents a computing device or system within an organization's network infrastructure. The model captures various details about the device, such as its name, type, location, network connectivity, and associated purchase order and person.

- `name`: The name of the host.
- `fqdn`: The fully qualified domain name of the host (optional).
- `type`: The type of the host, linked to a `HostType` entry. If the associated `HostType` entry is deleted, the host's type link will be empty (optional).
- `serial`: The serial number of the host (optional).
- `registration_date`: The date and time when the host was registered, automatically set to the current date and time when the object is created.
- `room`: The room where the host is located, linked to a `Room` entry. If the associated `Room` entry is deleted, the host's room link will be empty (optional).
- `jack`: The network jack the host is connected to, linked to a `Jack` entry. If the associated `Jack` entry is deleted, the host's jack link will be empty (optional).
- `purchase_order`: The purchase order associated with the host, linked to a `PurchaseOrder` entry. If the associated `PurchaseOrder` entry is deleted, the host's purchase order link will be empty (optional).
- `person`: The person associated with the host, linked to a `Person` entry. If the associated `Person` entry is deleted, the host's person link will be empty (optional).


## HostType

**Inherits:** [`NameSpacedHubuumModelWithExtensions`](#namespacedhubuummodelwithextensions)

A model for the types of hosts. It provides the following fields:

- `name`: The name of the host type.
- `description`: A description of the host type.

## Room

**Inherits:** [`NameSpacedHubuumModelWithExtensions`](#namespacedhubuummodelwithextensions)

A model for rooms within a location. It provides the following fields:

- `name`: The name of the room.
- `location`: A foreign key to the `Location` model.


## Jack

**Inherits:** [`NameSpacedHubuumModelWithExtensions`](#namespacedhubuummodelwithextensions)

A model for network jacks. It provides the following fields:

- `name`: The name of the jack.
- `room`: A foreign key to the `Room` model.

## Person

**Inherits:** [`NameSpacedHubuumModelWithExtensions`](#namespacedhubuummodelwithextensions)

A model representing a person who may have a room, and a computer may be assigned to them.

- `username`: A unique identifier for the person.
- `room`: A foreign key relation to the "Room" model, indicating the room assigned to the person.
- `section`: An integer representing the section of the person's department.
- `department`: A string representing the person's department.
- `email`: The person's email address.
- `office_phone`: The person's office phone number.
- `mobile_phone`: The person's mobile phone number.

## PurchaseDocuments

**Inherits:** [`NameSpacedHubuumModelWithExtensions`](#namespacedhubuummodelwithextensions)

A model representing the documents associated with a purchase order.

- `document_id`: A unique identifier for the document.
- `purchase_order`: A foreign key relation to the "PurchaseOrder" model.
- `document`: A binary field storing the document's data.

## PurchaseOrder

**Inherits:** [`NameSpacedHubuumModelWithExtensions`](#namespacedhubuummodelwithextensions)

A model representing a purchase order.

- `vendor`: A foreign key relation to the "Vendor" model, indicating the vendor involved in the purchase.
- `order_date`: A date-time field representing the date and time of the order.
- `po_number`: A unique identifier for the purchase order.

## Vendor

**Inherits:** [`NameSpacedHubuumModelWithExtensions`](#namespacedhubuummodelwithextensions)

A model representing a vendor who sells products or services.

- `vendor_name`: The name of the vendor.
- `vendor_url`: The vendor's website URL.
- `vendor_credentials`: The vendor's credentials, such as an account number.
- `contact_name`: The name of the vendor's contact person.
- `contact_email`: The email address of the vendor's contact person.
- `contact_phone`: The phone number of the vendor's contact person.


These models, when combined, form the structure of the Hubuum project. They allow for easy management and organization of various aspects of the IT infrastructure, such as hosts, host types, rooms, and more. Additionally, they support extensions and permissions for customization and access control.