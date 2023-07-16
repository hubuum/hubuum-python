"""Provide a base class for testing api/v1."""

from base64 import b64encode
from typing import Any, Callable, Dict, List, Union

# We use dateutil.parser.isoparse instead of datetime.datetime.fromisoformat
# because the latter only supportes Z for UTC in python 3.11.
# https://github.com/python/cpython/issues/80010
from dateutil.parser import isoparse
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.http import HttpResponse
from knox.models import AuthToken
from rest_framework.test import APIClient, APITestCase

from hubuum.exceptions import MissingParam
from hubuum.models.dynamic import DynamicClass, DynamicObject
from hubuum.models.iam import Namespace


# This testsuite design is based on the testsuite for MREG:
# https://github.com/unioslo/mreg/blob/master/mreg/api/v1/tests/tests.py
class HubuumAPITestCase(APITestCase):  # pylint: disable=too-many-public-methods
    """Base APITestCase for the HubuumAPI (v1)."""

    def setUp(self):
        """By default setUp sets up an APIClient for the superuser with a token."""
        self.user, _ = get_user_model().objects.get_or_create(  # nosec
            username="superuser", password="test"
        )
        self.namespace = None
        self.client = self.get_superuser_client()

    def db_engine(self) -> str:
        """Return the database engine."""
        return settings.DATABASES["default"]["ENGINE"]

    def db_engine_is_sqlite(self) -> bool:
        """Return True if the engine is sqlite."""
        return self.db_engine() == "django.db.backends.sqlite3"

    def db_engine_is_postgresql(self) -> bool:
        """Return True if the engine is postgresql."""
        return self.db_engine() == "django.db.backends.postgresql"

    def get_superuser_client(self) -> APIClient:
        """Get a client for a superuser."""
        return self._get_token_client(superuser=True)

    def get_staff_client(self) -> APIClient:
        """Get a client for a staff user."""
        return self._get_token_client(staff=True, superuser=False)

    def get_user_client(
        self, username: str = None, groupname: str = "test_nobody_group"
    ) -> APIClient:
        """Get a client for a normal user.

        param: username (defaults to "nobody")
        param: groupname (defaults to "test_nobody_group")
        """
        return self._get_token_client(
            staff=False, superuser=False, username=username, groupname=groupname
        )

    def _create_namespace(self, namespacename: str = "namespace1") -> None:
        """Get or create the given namespace directly."""
        namespace, _ = Namespace.objects.get_or_create(name=namespacename)
        return namespace

    def _get_token_client(
        self,
        username: str = None,
        groupname: str = None,
        superuser: bool = True,
        staff: bool = False,
    ) -> APIClient:
        """Create an APIClient with a token.

        Pass one of the following combinations:

        username=string, groupname=string (they will be created if they don't exist.)
        superuser=True (no superuser group will be created)
        staff=True (no staff group will be created)

        param: username (string, defaults to "None")
        param: groupname (string, defaults to "None")
        param: superuser (boolean, defaults to "True")
        param: staff (boolean, default to "False")
        """
        if username is None:
            if superuser:
                username = "superuser"
            elif staff:
                username = "staffuser"
            else:
                username = "nobody"

        self.user, _ = get_user_model().objects.get_or_create(  # nosec
            username=username, password="test"
        )
        self.user.groups.clear()

        if superuser:
            self.user.is_superuser = True
        elif staff:
            self.user.is_staff = True
        elif username == "nobody":
            self.add_user_to_groups("test_nobody_group")
        else:
            if not groupname:
                raise MissingParam

            self.add_user_to_groups(groupname)

        self.user.save()

        #        self.namespace, _ = Namespace.objects.get_or_create(name="test")

        # https://github.com/James1345/django-rest-knox/blob/develop/knox/models.py
        token = AuthToken.objects.create(self.user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Token " + token[1])
        return client

    def add_user_to_groups(self, groups: Union[str, List[str]]) -> None:
        """Add a user to a group or a list of groups."""
        if not isinstance(groups, (list, tuple)):
            groups = (groups,)
        for groupname in groups:
            group, _ = Group.objects.get_or_create(name=groupname)
            group.user_set.add(self.user)

    def grant(self, group: str, namespace: str, permissions: List[str]) -> None:
        """Grant a set of permissions to a given group for a namespace."""
        oldclient = self.client
        self.client = self.get_superuser_client()
        perms = {}
        for perm in permissions:
            perms[perm] = True
        self.assert_post_and_204(f"/iam/namespaces/{namespace}/groups/{group}", perms)
        self.client = oldclient

    def basic_auth(self, username: str, password: str) -> str:
        """Create a basic auth header for the given username and password."""
        token = b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
        return f"Basic {token}"

    @staticmethod
    def _create_path(path: str) -> str:
        """Create a valid API path from the stub provided.

        Usage rules:

        1. If the parameter starts with /api/, use the param verbatim.
        2. If the parameter starts with /, remove the initial /, goto 2.
        3. Append the parameter to /api/v1/.

        parmams: path (string)
        """
        if path.startswith("/api/"):
            return path
        if path.startswith("/"):
            return f"/api/v1/{path[1:]}"
        return f"/api/v1/{path}"

    def _assert_status_and_debug(
        self, response: HttpResponse, expected_code: int
    ) -> None:
        """Print the response content if the status code is unexpected."""
        if not response.status_code == expected_code:
            path = f"{response.request['PATH_INFO']}{response.request['QUERY_STRING']}"
            fail = f"{path} FAILED: {response.status_code}"
            if hasattr(response, "data"):
                fail = f"{fail} [{response.data}]"
            print(fail)
        self.assertEqual(response.status_code, expected_code)

    def _assert_delete_and_status(
        self, path: str, status_code: int, client: APIClient = None
    ) -> HttpResponse:
        """Delete and assert status."""
        if client is None:
            client = self.client
        response = client.delete(self._create_path(path))
        self._assert_status_and_debug(response, status_code)
        return response

    def _assert_get_and_status(
        self, path: str, status_code: int, client: APIClient = None
    ) -> HttpResponse:
        """Get and assert status."""
        if client is None:
            client = self.client
        response = client.get(self._create_path(path))
        self._assert_status_and_debug(response, status_code)
        return response

    def _assert_patch_and_status(
        self,
        path: str,
        status_code: int,
        data: Dict[str, Any] = None,
        client: APIClient = None,
    ) -> HttpResponse:
        """Patch and assert status."""
        if client is None:
            client = self.client
        response = client.patch(self._create_path(path), data)
        self._assert_status_and_debug(response, status_code)
        return response

    def _assert_post_and_status(
        self,
        path: str,
        status_code: int,
        data: Dict[str, Any] = None,
        client: APIClient = None,
        **kwargs: Any,
    ) -> HttpResponse:
        """Post and assert status."""
        posting_format = kwargs.get("format", "json")

        if client is None:
            client = self.client
        response = client.post(self._create_path(path), data, format=posting_format)
        self._assert_status_and_debug(response, status_code)
        return response

    def _is_iso_date(self, value: str) -> bool:
        """Assert that a value is a valid date."""
        try:
            isoparse(value)
            return True
        except ValueError:
            return False

    def assert_list_contains(
        self, lst: List[Any], predicate: Callable[[Any], bool]
    ) -> None:
        """Assert that a list contains at least one item matching a function."""
        for item in lst:
            if predicate(item):
                return
        raise AssertionError(f"Elements not found in {list}")

    def assert_is_iso_date(self, value: str) -> None:
        """Assert that a value is a valid date."""
        self.assertTrue(self._is_iso_date(value))

    def assert_delete(self, path: str, **kwargs: Any) -> HttpResponse:
        """Delete and assert status as 204."""
        return self.assert_delete_and_204(path, **kwargs)

    def assert_delete_and_204(self, path: str, **kwargs: Any) -> HttpResponse:
        """Delete and assert status as 204."""
        return self._assert_delete_and_status(path, 204, **kwargs)

    def assert_delete_and_401(self, path: str, **kwargs: Any) -> HttpResponse:
        """Delete and assert status as 401."""
        return self._assert_delete_and_status(path, 401, **kwargs)

    def assert_delete_and_403(self, path: str, **kwargs: Any) -> HttpResponse:
        """Delete and assert status as 403."""
        return self._assert_delete_and_status(path, 403, **kwargs)

    def assert_delete_and_404(self, path: str, **kwargs: Any) -> HttpResponse:
        """Delete and assert status as 404."""
        return self._assert_delete_and_status(path, 404, **kwargs)

    #    def assert_delete_and_409(self, path: str, **kwargs: Any) -> HttpResponse:
    #        """Delete and assert status as 409."""
    #        return self._assert_delete_and_status(path, 409, **kwargs)

    def assert_get_elements(
        self, path: str, element_count: int, **kwargs: Any
    ) -> HttpResponse:
        """Get and assert (status == 200 and element_count == elements)."""
        response = self.assert_get_and_200(path, **kwargs)
        self.assertEqual(len(response.data), element_count)
        return response

    def assert_get(self, path: str, **kwargs: Any) -> HttpResponse:
        """Get and assert status as 200."""
        return self.assert_get_and_200(path, **kwargs)

    def assert_get_and_200(self, path: str, **kwargs: Any) -> HttpResponse:
        """Get and assert status as 200."""
        return self._assert_get_and_status(path, 200, **kwargs)

    def assert_get_and_301(self, path: str, **kwargs: Any) -> HttpResponse:
        """Get and assert status as 301."""
        return self._assert_get_and_status(path, 301, **kwargs)

    def assert_get_and_400(self, path: str, **kwargs: Any) -> HttpResponse:
        """Get and assert status as 400."""
        return self._assert_get_and_status(path, 400, **kwargs)

    def assert_get_and_401(self, path: str, **kwargs: Any) -> HttpResponse:
        """Get and assert status as 401."""
        return self._assert_get_and_status(path, 401, **kwargs)

    def assert_get_and_403(self, path: str, **kwargs: Any) -> HttpResponse:
        """Get and assert status as 403."""
        return self._assert_get_and_status(path, 403, **kwargs)

    def assert_get_and_404(self, path: str, **kwargs: Any) -> HttpResponse:
        """Get and assert status as 404."""
        return self._assert_get_and_status(path, 404, **kwargs)

    def assert_patch(self, path: str, *args: Any, **kwargs: Any) -> HttpResponse:
        """Patch and assert status as 200."""
        return self.assert_patch_and_200(path, *args, **kwargs)

    def assert_patch_and_200(
        self, path: str, *args: Any, **kwargs: Any
    ) -> HttpResponse:
        """Patch and assert status as 200."""
        return self._assert_patch_and_status(path, 200, *args, **kwargs)

    def assert_patch_and_204(
        self, path: str, *args: Any, **kwargs: Any
    ) -> HttpResponse:
        """Patch and assert status as 204."""
        return self._assert_patch_and_status(path, 204, *args, **kwargs)

    def assert_patch_and_400(
        self, path: str, *args: Any, **kwargs: Any
    ) -> HttpResponse:
        """Patch and assert status as 400."""
        return self._assert_patch_and_status(path, 400, *args, **kwargs)

    def assert_patch_and_401(
        self, path: str, *args: Any, **kwargs: Any
    ) -> HttpResponse:
        """Patch and assert status as 401."""
        return self._assert_patch_and_status(path, 401, *args, **kwargs)

    def assert_patch_and_403(
        self, path: str, *args: Any, **kwargs: Any
    ) -> HttpResponse:
        """Patch and assert status as 204."""
        return self._assert_patch_and_status(path, 403, *args, **kwargs)

    def assert_patch_and_404(
        self, path: str, *args: Any, **kwargs: Any
    ) -> HttpResponse:
        """Patch and assert status as 404."""
        return self._assert_patch_and_status(path, 404, *args, **kwargs)

    def assert_patch_and_405(
        self, path: str, *args: Any, **kwargs: Any
    ) -> HttpResponse:
        """Patch and assert status as 405."""
        return self._assert_patch_and_status(path, 405, *args, **kwargs)

    #    def assert_patch_and_409(self, path: str,*args, **kwargs):
    #        """Patch and assert status as 409."""
    #        return self._assert_patch_and_status(path, 409, *args, **kwargs)

    def assert_post(self, path: str, *args: Any, **kwargs: Any) -> HttpResponse:
        """Post and assert status as 201."""
        return self.assert_post_and_201(path, *args, **kwargs)

    def assert_post_and_200(self, path: str, *args: Any, **kwargs: Any) -> HttpResponse:
        """Post and assert status as 200."""
        return self._assert_post_and_status(path, 200, *args, **kwargs)

    def assert_post_and_201(self, path: str, *args: Any, **kwargs: Any) -> HttpResponse:
        """Post and assert status as 201."""
        return self._assert_post_and_status(path, 201, *args, **kwargs)

    def assert_post_and_204(self, path: str, *args: Any, **kwargs: Any) -> HttpResponse:
        """Post and assert status as 204."""
        return self._assert_post_and_status(path, 204, *args, **kwargs)

    def assert_post_and_400(self, path: str, *args: Any, **kwargs: Any) -> HttpResponse:
        """Post and assert status as 400."""
        return self._assert_post_and_status(path, 400, *args, **kwargs)

    def assert_post_and_401(self, path: str, *args: Any, **kwargs: Any) -> HttpResponse:
        """Post and assert status as 401."""
        return self._assert_post_and_status(path, 401, *args, **kwargs)

    def assert_post_and_403(self, path: str, *args: Any, **kwargs: Any) -> HttpResponse:
        """Post and assert status as 403."""
        return self._assert_post_and_status(path, 403, *args, **kwargs)

    def assert_post_and_404(self, path: str, *args: Any, **kwargs: Any) -> HttpResponse:
        """Post and assert status as 404."""
        return self._assert_post_and_status(path, 404, *args, **kwargs)

    def assert_post_and_405(self, path: str, *args: Any, **kwargs: Any) -> HttpResponse:
        """Post and assert status as 405."""
        return self._assert_post_and_status(path, 405, *args, **kwargs)

    def assert_post_and_409(self, path: str, *args: Any, **kwargs: Any) -> HttpResponse:
        """Post and assert status as 409."""
        return self._assert_post_and_status(path, 409, *args, **kwargs)

    def assert_post_and_415(self, path: str, *args: Any, **kwargs: Any) -> HttpResponse:
        """Post and assert status as 415."""
        return self._assert_post_and_status(path, 415, *args, **kwargs)


# def clean_and_save(entity):
#    """Perform a full clean and a save on the object.
#
#    https://docs.djangoproject.com/en/4.1/ref/models/instances/#django.db.models.Model.full_clean
#    """
#    entity.full_clean()
#    entity.save()


# def create_host(name="testhost", ownergroup=None):
#    """Create a host with an owner, directly against the model.
#
#    params: name (defaults to "testhost")
#    params: ownergroup (no default, group object expected, required)
#    """
#    if not ownergroup:
#        raise MissingParam
#
#    if not isinstance(ownergroup, Group):
#        raise TypeError
#
#    return Host.objects.create(name=name, owner=ownergroup)


# TODO: For every endpoint we should have and check input validation.


class HubuumAPITestCaseWithDynamics(HubuumAPITestCase):
    """A base class for Hubuum API test cases with dynamic classes already active.

    The following classes are created:
    - Host
    - Room
    - Building

    The following objects are created:
    - Hosts (3, named host1, host2, host3)
    - Rooms (2, named room1, room2, room3)
    - Buildings (1, named building1)
    """

    def _create_dynamic_class(
        self, name: str = "Test", namespace: Namespace = None
    ) -> DynamicClass:
        """Create a dynamic class."""
        if not namespace:
            namespace = self.namespace

        attributes = {"name": name, "namespace": namespace}
        return DynamicClass.objects.create(**attributes)

    def _create_dynamic_object(
        self,
        dynamic_class: DynamicClass = None,
        namespace: Namespace = None,
        **kwargs: Any,
    ) -> DynamicObject:
        """Create a dynamic object."""
        attributes = {
            "json_data": {"key": "value", "listkey": [1, 2, 3]},
            "namespace": namespace,
        }

        for key, value in kwargs.items():
            attributes[key] = value

        return DynamicObject.objects.create(dynamic_class=dynamic_class, **attributes)

    def setUp(self):
        """Set up a few dynamic classes for testing.

        The following classes are created:
        - Host
        - Room
        - Building

        The following objects are created:
        - Hosts (3, named host1, host2, host3)
        - Rooms (2, named room1, room2, room3)
        - Buildings (1, named building1)
        """
        super().setUp()

        self.namespace = self._create_namespace()
        self.host_class = self._create_dynamic_class(name="Host")
        self.room_class = self._create_dynamic_class(name="Room")
        self.building_class = self._create_dynamic_class(name="Building")

        # Create an array of hosts with names host1, host2, host3
        self.hosts = [
            self._create_dynamic_object(
                dynamic_class=self.host_class, namespace=self.namespace, name=f"host{i}"
            )
            for i in range(1, 4)
        ]

        # Create an array of rooms with names room1, room2, room3
        self.rooms = [
            self._create_dynamic_object(
                dynamic_class=self.room_class, namespace=self.namespace, name=f"room{i}"
            )
            for i in range(1, 3)
        ]

        # Create a building with name building1
        self.building = self._create_dynamic_object(
            dynamic_class=self.building_class,
            namespace=self.namespace,
            name="building1",
        )

    def tearDown(self) -> None:
        """Delete the namespace after the test."""
        self.namespace.delete()
        return super().tearDown()
