# Examples of using the hubuum API

```bash
# Get the user with the username "admin" (it is unique)
GET /api/v1/users/?username=admin

# Get hosts that end with "example.tld" in FQDN
GET /api/v1/hosts/?fqdn__endswith=example.tld

# Get extensions that have json_data with a key "foo" and value "bar"
GET /api/v1/extensions/?json_data_lookup__foo=bar

# Get extensions that apply to a host that has json_data with a key "foo",
# with a subkey "bar", and has a value that contains "baz"
GET /api/v1/extensions/?content_type=host&json_data_lookup__foo__bar__icontains=baz
```

!!! warning
    You always want to use case-insensitive operators for JSON fields. Otherwise, you will get unexpected (ie, no) results.
