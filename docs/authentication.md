# Authentication

Hubuum uses [Django REST Framework](https://www.django-rest-framework.org/) for its API. In typical REST fashion, the authentication endpoint for username and password returns a token, which is then used for the rest of the API. The endpoint is `/api/auth/login` and one can code such as this to log in:_

    ```python
    basic_auth = b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=auth)
    client.post("/api/auth/login/")
    ```

In return, on a successful login, one will get a JSON blob akin to this. Note that the token in the example is truncated for brevity. By default the token is 64 characters long, and has an expiry of 10 hours. Every login from a user will generate a new token, and every generated token is valid until it expires.

    ```json
    {
        "expiry": "2023-11-23T09:33:53.990672Z",
        "token":"b61...77f" 
    }
    ```

Using the token is done as follows:

    ```python
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    ```

## Deleting a single token

Any token can be deleted by calling the `/api/auth/logout` endpoint. This will invalidate the token in question.

## Purging all tokens for a user

If you need to purge all tokens for a user, you can do so by calling the `/api/auth/logoutall` endpoint. This will invalidate all tokens for the user owning the token in question.
