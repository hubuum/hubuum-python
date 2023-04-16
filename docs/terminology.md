# Terminology

## Namespace

A namespace is a collection that an object belongs to. Every object in hubuum belongs to one and only one namespace. A namespace is identified by a unique name. A namespace can have zero or more groups with permissions for the namespace, and these groups can have zero or more users. Each group can have one of five [permissions](model.md#permission):

- `read`: The group can read the objects in the namespace, but not create or update them.
- `create`: The group can create objects in the namespace, read is implied.
- `update`: The group can update objects in the namespace, read is implied.
- `delete`: The group can delete objects in the namespace, read is implied.
- `namespace`: The group can create, read, update and delete objects in the namespace, and also create, read, update and delete the namespace itself.


## Extension

An extension adds a json_data field to an object. The json_data field can be used to store any data that is relevant to the object. The extension can also have a header and a URL. The header is a string that is sent to the URL when the object is requested, typically used for authorization. The URL is used to fetch data from an external source and store it in the json_data field. The URL may have interpolation fields that are replaced when the URL is fetched. Typically this interpolation is used to ensure a unique URL for each object.

Extensions main purpose is to be able to dynamically update the data belonging to a model without having to update the model itself.


## Group

Groups contain users and have permissions for any number of namespaces.
