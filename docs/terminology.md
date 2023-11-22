# Terminology

## Namespace

A namespace is a collection that an object belongs to. Every object in hubuum belongs to one and only one namespace. A namespace is identified by a unique name. A namespace can have zero or more groups with permissions for the namespace, and these groups can have zero or more users. Each group has a set of [permissions](permissions.md#namespaces) to the namespace in question.

## Class

Every data object in Hubuum belongs to a Hubuum Class. These classes are user-defined, and may optionally use JSON validation schemas to enforce data integrity. One may also attach a schema to a class but not enforce it, only to have Hubuum warn when objects break the contract.

Classes are identified by a unique name.

## Object

An object is an instance of a class. It is a JSON document that may either be free-form or adhere to a JSON schema. Objects are identified by a unique name within each class.

## Group

Groups contain users and have permissions for any number of namespaces.
