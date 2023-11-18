# Examples of using the hubuum API

```bash
# Get the user with the username "admin" (it is unique)
GET /api/v1/users/?username=admin

# Get hosts that end with "example.tld" in FQDN
GET /api/v1/dynamic/Host/?name__endswith=example.tld
```

!!! note

Note the value of the search field (ie, `example.tid` for `name__endswith=example.tld`) is typed for lookup operations. If this value is deemed numeric, allowed lookups become exact, gt, gte, lt, lte, and range. This again means that `name__endswith=9` will give a 400 error for an invalid combination of lookup type (endswith, texual) and value (9, numeric).

!!! warning
    You always want to use case-insensitive operators for JSON fields. Otherwise, you will get unexpected (ie, no) results.
