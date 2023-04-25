# Extensions

## Overview

Hubuum supports `extensions` to extend basic storage functionality of object models. Each extension applies to a specific model, and objects of that model will then have the option to have associated data from the extension applied to them.

The only currently supported extension type is to retrieve data from a REST endpoint and store it as JSON for the object in question. An extension has the following properties:

- `name`: The name of the extension. This is a globally unique identifier for the extension.
- `content_type`: The model that the extension applies to.
- `url`: The URL endpoint that the extensions uses to fetch data. Supports interpolation fields.
- `require_interpolation` (optional): If set to true, the URL has to have at least one interpolation field.
- `header` (optional): A header to send with the request. This is a formatted HTTP header string. Typically used to pass authentication information.
- `cache_time` (optional, defaults to 60s): The time in seconds to cache the response from the endpoint.

### Interpolation fields

A url may take interpolation fields on the form of `{fieldname}` where the fieldname is a field on the object. For example, if the URL is `http://example.com/users/{username}/`, and the object has a field `username` with the value `admin`, the URL will be interpolated to `http://example.com/users/admin/` for that object. If you do not require interpolation, you can set `require_interpolation` to false and the URL will be used as-is.

### Populating the data for an object

There is currently no automatic population of an objects extension data. This also implies that the cache_data field is unused. There is an issue on how to do this gracefully: [https://github.com/terjekv/hubuum/issues/69](https://github.com/terjekv/hubuum/issues/69)

## Example usage

### Register a new extension

```bash
# Assume we have a host in the database with the FQDN test.example.tld, and ID=1
# This host resides in the namespace with ID=1

# Create a new extension
POST /api/v1/extensions/ -d '{
    "name": "example",
    "content_type": "host",
    "url": "https://example.tld/hostname/{fqdn}/",
    "header": "Authorization: Bearer sh...=="
}'
# We assume this gives is the ID for the extension as '1'

# Populate data for the host test.example.tld
# Assume that the endpoint returns the following JSON:
# { "foo": "bar" }
data=$( curl -X GET \
  -H "Content-type: application/json" \
  -H "Accept: application/json" \
  "https://example.tld/hostname/test.example.tld" )

# Add the data to the object
# Note that the namespace and extension IDs are used, not their names
# The object ID is the ID of the host
POST /api/v1/extension_data/ -d "{
    'namespace': 1,
    'extension': 1,
    'content_type': 'host',
    'object_id': 1,
    'json_data': ${data}
}"

# We can now search for the data using the extension API. Note that we do not
# limit this search to any specific namespace or extension id.
GET /api/v1/extension_data/?content_type=host&json_data_lookup__foo=bar

# This should return at least one hit, an extension data with our object:
{
    "id": 1,
    "namespace": 1,
    "extension": 1,
    "content_type": "host",
    "object_id": 1,
    "json_data": {
        "foo": "bar"
    }
}
```
