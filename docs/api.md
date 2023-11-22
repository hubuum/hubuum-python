# The hubuum API

## Creating classes

Classes are created via the API. The API endpoint is `/api/v1/dynamic/`. Creating a class is done by sending a POST request to the endpoint with a JSON body containing the class definition. The class definition is a JSON object with the following keys:

- `name` (required): The name of the class. This must be unique.
- `schema` (optional): A JSON schema that the objects of this class must adhere to. If this is not provided, the objects of this class will be free-form.
- `validate_schema` (optional): A boolean value that determines whether the schema is enforced or not. If this is not provided, the schema will not be enforced.
- `namespace` (required): The namespace that this class belongs to. This must be a valid namespace ID.

For more information about namespaces, [permissions](permissions.md).

    ```python
    # For a free-form class:
    client.post(
        "/api/v1/dynamic/",
        {
            "name": "Host",
            "namespace": 1,
        },
    )
    # For a class with a schema:
    valid_schema = {
    "$id": "https://example.com/person.schema.json",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Person",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "age": {
            "description": "Age in years which must be equal to or greater than zero.",
            "type": "integer",
            "minimum": 0,
            "maximum": 150,
        },
    }
    client.post(
        "/api/v1/dynamic/",
        {
            "name": "Person",
            "namespace": 1,
            "schema": valid_schema,
            "validate_schema": True,
        },
    )
    ```

## Creating objects

Objects are created via the API. The API endpoint is `/api/v1/dynamic/<class_name>/`. Creating an object is done by sending a POST request to the endpoint with a JSON body containing the object definition. The object definition is a JSON object with the following keys:

- `name` (required): The name of the object. This must be unique within the class.
- `json_data` (required): A JSON object that is the object data. This must adhere to the schema of the class, if one is defined.
- `namespace` (required): The namespace that this object belongs to. This must be a valid namespace ID.

Note that this implies that classes can belong to different namespaces than the objects they contain. This is intentional, and allows for a more flexible data model. Within a class, objects can again belong to different namespaces. This ensures that an organization may share a class, but not the objects within it, or vice versa.

    ```python
    client.post(
        "/api/v1/dynamic/Person/",
        {
            "name": "John Doe",
            "json_data": {
                "age": 42,
            },
            "namespace": 1,
        },
    )
    ```

## Working with individual classes or objects

As per standard REST practice, individual classes or objects can be accessed via their unique name. The API endpoints are `/api/v1/dynamic/<class_name>` and `/api/v1/dynamic/<class_name>/<object_name>/` for objects. These endpoints all support the default REST methods: GET, PUT, PATCH, and DELETE.

## Filtering

Querying using the API is done via standard HTTP GET requests using django-filter. The API supports filtering, ordering, and pagination. The API also supports querying JSON fields of the models directly (see below).

!!! note
    Filtering on a field that does not exist, or using an unsupported lookup key for an existing, field will return `400 Bad Request`, with some information about the fields or lookups that failed.

## Operators

### Text or character fields

For text or character fields, the following operators are supported:

- `exact` (default)
- `startswith` (case-sensitive, string start with)
- `endswith` (case-sensitive, string end with)
- `contains` (case-sensitive, string contains)
- `regex` (case-sensitive, regular expression)

These may also be prefixed with `i` to make them case-insensitive, eg. `icontains`.

#### Examples for text or character fields

    ```bash
    # These two are identical:
    /iam/users/?name=johndoe
    /iam/users/?name__exact=johndoe

    # Find all users with a username that ends with "doe"
    /iam/users/?name__endswith=doe
    /iam/users/?name__regex=doe$

    # Find all users that start with "john"
    /iam/users/?name__startswith=john
    /iam/users/?name__regex=^john

    # Find all users that start with "j", contains "do", and ends with "e"
    /iam/users/?name__regex=^j.*do.*e$

    # Find all Persons with a name that contains "doe"
    /api/v1/dynamic/Persons/?json_data_lookup__name__icontains=doe
    ```

### Numeric fields

For numeric fields, the following operators are supported:

- `exact` (default)
- `gt` (greater than)
- `gte` (greater than or equal to)
- `lt` (less than)
- `lte` (less than or equal to)
- `range` (between)

#### Examples for numeric fields

    ```bash
    # These two are identical:
    /iam/users/?id=1
    /iam/users/?id__exact=1

    # Find all users with an ID over 5 but under 9, these three are identical
    /iam/users/?id__gt=5&id__lt=9
    /iam/users/?id__gte=6&id__lte=8
    /iam/users/?id__range=6,8
    ```

### Date fields

For date fields, the following operators are supported:

- `exact` (default)
- `day` (day of the month)
- `week` (week of the year)
- `month` (month of the year)
- `year` (year)
- `quarter` (quarter of the year)
- `week_day` (day of the week)
- `iso_week_day` (day of the week, ISO 8601)
- `iso_year` (week of the year, ISO 8601)

### JSON fields, object data

The API supports querying JSON fields of the models directly. This is done by querying the field name suffixed by `__lookup`. For example, to query the `json_data` field of an object, you would use `json_data_lookup` as the lookup key.

When querying into the json field, use `__` to separate the keys. Some mapping examples:

    ```python
    1. json_data['foo']==value
    # /?json_data_lookup__foo=value
    2. json_data['foo']['bar']==value
    # /?json_data_lookup__foo__bar=value
    3. if 'value'.lower() in json_data['foo']['bar'].lower()
    # /?json_data_lookup__foo__bar__icontains=value
    ```

!!! warning
    You always want to use case-insensitive operators for JSON fields. Otherwise, you will get unexpected (ie, no) results.
