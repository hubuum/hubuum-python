# Examples of using the hubuum API

```bash
# Get the user with the username "admin" (it is unique)
GET /api/v1/users/?username=admin

# Get hosts that end with "example.tld" in FQDN
GET /api/v1/hosts/?fqdn__endswith=example.tld
```

!!! warning
    You always want to use case-insensitive operators for JSON fields. Otherwise, you will get unexpected (ie, no) results.
