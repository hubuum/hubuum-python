# Permissions

## Overview

Hubuum supports permissions based on `namespaces`. A namespace is a collection of objects, and each object belongs to one and only one namespace. A namespace can be thought of as a project, or a tenant.

Groups are given access to namespaces based on one of five boolean permissions: `read`, `create`, `update`, `delete` and `namespace`. These permissions are described in detail below.

- `read`: The group can read the objects in the namespace, but not create or update them.
- `create`: The group can create objects in the namespace, read is implied.
- `update`: The group can update objects in the namespace, read is implied.
- `delete`: The group can delete objects in the namespace, read is implied.
- `namespace`: The group can create, read, update and delete objects in the namespace, and also create, read, update and delete the namespace itself.

## Example usage

```bash
# Create a new namespace
POST /api/v1/namespaces/ -d '{
    "name": "example_namespace"
}'

# Create a new group
POST /api/v1/groups/ -d '{
    "name": "example_group"
}'

# Give the group read access to the namespace
POST /api/v1/namespaces/example_namespace/groups/example_group -d '{
    "read": true
}'
```

!!! warning
    Note that deleting a namespace deletes all objects in the namespace, and cannot be undone.
    Deleting the namespace also deletes all permission objects for the namespace,
    but the groups themselves are not deleted.
