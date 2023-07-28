# The hubuum API

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

### JSON fields

The API supports querying JSON fields of the models directly. This is done by querying the field name suffixed by `__lookup`. For example, to query the `json_data` field of the `Extension` model, you would use `json_data_lookup` as the lookup key.

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
