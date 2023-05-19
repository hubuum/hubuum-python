"""Test the filter interface."""
from typing import Any, Dict

from django.conf import settings

from hubuum.models.auth import User
from hubuum.models.permissions import Namespace
from hubuum.models.resources import Host, Room

from .base import HubuumAPITestCase


class HubuumFilterTestCase(HubuumAPITestCase):
    """Base class for testing Hubuum Filtering."""

    def _make_extension_blob(
        self,
        model: str = "host",
        name: str = "fleet",
        url: str = "http://my.fleet.tld/{fqdn}",
    ) -> Dict[str, Any]:
        """Make an extension blob with the given URL."""
        return {
            "namespace": self.namespace.id,
            "name": name,
            "model": model,
            "url": url,
            "header": "Authorization: Bearer sh...==",
        }

    def _make_extension_data_blob(
        self,
        extension_id: int,
        content_type: str,
        host_id: int,
        json_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create an extension data blob."""
        return {
            "namespace": self.namespace.id,
            "extension": extension_id,
            "content_type": content_type,
            "object_id": host_id,
            "json_data": json_data,
        }

    def _add_host(self, name: str, fqdn: str) -> None:
        """Add a host to our collection."""
        self.hosts.append(
            Host.objects.create(name=name, fqdn=fqdn, namespace=self.namespace)
        )

    def setUp(self):
        """Set up the test environment for the class."""
        self.hosts = []

        self.client = self.get_superuser_client()
        self.namespace, _ = Namespace.objects.get_or_create(name="test")
        self._add_host("test1", "test1.domain.tld")
        self._add_host("test2", "test2.other.com")
        self._add_host("test3", "test3.other.com")

        ext_host_blob = self.assert_post("/extensions/", self._make_extension_blob())
        for host in self.hosts:
            self.assert_post(
                "/extensions/data/",
                self._make_extension_data_blob(
                    ext_host_blob.data["id"],
                    "host",
                    host.id,
                    {
                        "key": "value",
                        "fqdn": host.fqdn,
                        "id": host.id,
                        "dns": {"fqdn": host.fqdn},
                    },
                ),
            )

        room = Room.objects.create(room_id="BL01-02-345", namespace=self.namespace)
        ext_room_blob = self.assert_post(
            "/extensions/",
            self._make_extension_blob(
                model="room",
                name="pytagoras",
                url="https://pythagoras.top.tld/room_data/{room_id}",
            ),
        )
        self.assert_post(
            "/extensions/data/",
            self._make_extension_data_blob(
                ext_room_blob.data["id"],
                "room",
                room.id,
                {
                    "key": "value",
                    "room_id": room.room_id,
                    "list": ["one", {"two": "twovalue"}],
                    "weird": {"exact": "value"},
                },
            ),
        )

    def tearDown(self) -> None:
        """Tear down the test environment."""
        self.namespace.delete()
        return super().tearDown()

    def test_user_filtering(self):
        """Test that filtering on fields in users works."""
        test = User.objects.create(
            username="testuser", email="test@domain.tld", is_staff=False
        )
        staff = User.objects.create(
            username="stafftestuser", email="staff@domain.COM", is_staff=True
        )
        self.assert_get_elements("/iam/users/", 3)
        self.assert_get_elements("/iam/users/?email__contains=domain", 2)

        # SQLite doesn't support case-sensitive lookup operators, so results may differ.
        # Here, on SQLite, we will match the user with staff@domain.COM, but on postgres,
        # we will NOT match due to case sensitivity.
        # https://docs.djangoproject.com/en/4.2/ref/databases/#sqlite-string-matching
        # (Arguments about case sensitivity in domain names emails not withstanding,
        # this is a test of the filter)
        if settings.DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3":
            self.assert_get_elements("/iam/users/?email__endswith=com", 1)
        else:
            self.assert_get_elements("/iam/users/?email__endswith=com", 0)

        self.assert_get_elements("/iam/users/?email__iendswith=com", 1)
        self.assert_get_elements("/iam/users/?username__startswith=staff", 1)
        self.assert_get_elements("/iam/users/?username__contains=test", 2)
        self.assert_get_elements("/iam/users/?username=testuser", 1)
        # This returns every object when we explicitly ask for exact?
        # self.assert_get_elements("/iam/users/?username__exact=testuser", 1)
        self.assert_get_elements("/iam/users/?is_staff=1", 1)
        # We have two non-staff users, the test user and the superuser who runs the client.
        self.assert_get_elements("/iam/users/?is_staff=0", 2)
        self.assert_get_elements("/iam/users/?is_staff=0&email__endswith=tld", 1)

        test.delete()
        staff.delete()

    #        self.assert_get_elements("/iam/users/?fqdn__contains=other", 2)

    def test_host_filtering(self):
        """Test that filtering on fields in hosts works."""
        self.assert_get_elements("/resources/hosts/", 3)
        self.assert_get_elements("/resources/hosts/?name__contains=test", 3)
        self.assert_get_elements("/resources/hosts/?fqdn=test2.other.com", 1)
        self.assert_get_elements("/resources/hosts/?fqdn__contains=other", 2)
        self.assert_get_elements("/resources/hosts/?fqdn__startswith=test3.other", 1)
        self.assert_get_elements(f"/resources/hosts/?namespace={self.namespace.id}", 3)
        self.assert_get_elements(
            "/resources/hosts/?name__contains=test&fqdn__contains=domain", 1
        )

    def test_extension_data_basic_filtering(self):
        """Test that we can filter into the JSON blobs that extensions deliver."""
        self.assert_get_elements("/extensions/data/", 4)
        self.assert_get_elements(
            "/extensions/data/?json_data_lookup=fqdn__icontains=other", 2
        )
        self.assert_get_elements(
            "/extensions/data/?json_data_lookup=fqdn__exact=other", 0
        )
        # Implied exact
        self.assert_get_elements("/extensions/data/?json_data_lookup=fqdn=other", 0)
        self.assert_get_elements(
            "/extensions/data/?json_data_lookup=fqdn__exact=test1.domain.tld", 1
        )

    def test_extension_data_numeric_filtering(self):
        """Test that we can filter into the JSON blobs that extensions deliver."""
        host = self.assert_get("/resources/hosts/test1")
        host1id = host.data["id"]
        self.assert_get_elements(f"/extensions/data/?json_data_lookup=id={host1id}", 1)
        self.assert_get_elements(
            f"/extensions/data/?json_data_lookup=id__gt={host1id}", 2
        )

    def test_extension_data_json_scoping(self):
        """Test that we can parse JSON scopes correctly."""
        self.assert_get_elements(
            "/extensions/data/?json_data_lookup=dns__fqdn__icontains=other", 2
        )
        self.assert_get_elements(
            "/extensions/data/?json_data_lookup=dns__fqdn=other", 0
        )

    def test_extension_data_json_array_comprehension(self):
        """Test that we can parse JSON arrays correctly."""
        self.assert_get_elements(
            "/extensions/data/?json_data_lookup=list__0__exact=one", 1
        )
        self.assert_get_elements(
            "/extensions/data/?json_data_lookup=list__1__two__icontains=value", 1
        )

    def test_extension_data_filtering_mismatches(self):
        """Test that we validate JSON lookups correctly."""
        # Missing value
        self.assert_get_and_400("/extensions/data/?json_data_lookup=list")
        # Using the wrong lookup
        self.assert_get_and_400("/extensions/data/?json_data_lookup=id__contains=2")

    def test_extension_data_filtering_with_lookups_as_keys(self):
        """Test that we validate JSON lookups correctly."""
        # Here we have "weird": {"exact": "value"}, so weird__exact is valid,
        # but tests against the list, so we get zero hits.
        # See #76.
        self.assert_get_elements(
            "/extensions/data/?json_data_lookup=weird__exact=value", 0
        )
