# The hubuum API

The generic lookup key is `val` for all models. Usually, any unique identifier for the object will be usable as the lookup key. For example, for a user, the username or email can be used as the lookup key. For a group, the group name can be used as the lookup key.

## Filtering

Querying using the API is done via standard HTTP GET requests using django-filter. The API supports filtering, ordering, and pagination. The API also supports querying JSON fields of the models directly (see below).

## Operators

### Text or character fields

For text fields, the following operators are supported:

- `exact` (default)
- `startswith` (case-sensitive, string start with)
- `endswith` (case-sensitive, string end with)
- `contains` (case-sensitive, string contains)

These may also be prefixed with `i` to make them case-insensitive, eg. `icontains`.

### Numeric fields

For numeric fields, the following operators are supported:

- `exact` (default)
- `gt` (greater than)
- `gte` (greater than or equal to)
- `lt` (less than)
- `lte` (less than or equal to)
- `range` (between)


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


