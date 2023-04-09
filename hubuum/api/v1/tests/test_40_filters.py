"""Test the filter interface."""
from hubuum.models.auth import User
from hubuum.models.base import Host, Namespace, Room

from .base import HubuumAPITestCase


class HubuumFilterTestCase(HubuumAPITestCase):
    """Base class for testing Hubuum Filtering."""

    def _make_extension_blob(
        self, model="host", name="fleet", url="http://my.fleet.tld/{fqdn}"
    ):
        """Make an extension blob with the given URL."""
        return {
            "namespace": self.namespace.id,
            "name": name,
            "model": model,
            "url": url,
            "header": "Authorization: Bearer sh...==",
        }

    def _make_extension_data_blob(self, extension_id, content_type, host_id, json_data):
        """Create an extension data blob."""
        blob = {
            "namespace": self.namespace.id,
            "extension": extension_id,
            "content_type": content_type,
            "object_id": host_id,
            "json_data": json_data,
        }
        return blob

    def _add_host(self, name, fqdn):
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
                "/extension_data/",
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
            "/extension_data/",
            self._make_extension_data_blob(
                ext_room_blob.data["id"],
                "room",
                room.id,
                {"key": "value", "room_id": room.room_id},
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
        self.assert_get_elements("/users/", 3)
        self.assert_get_elements("/users/?email__contains=domain", 2)
        self.assert_get_elements("/users/?email__endswith=com", 0)
        self.assert_get_elements("/users/?email__iendswith=com", 1)
        self.assert_get_elements("/users/?username__startswith=staff", 1)
        self.assert_get_elements("/users/?username__contains=test", 2)
        self.assert_get_elements("/users/?username=testuser", 1)
        # This returns every object when we explicitly ask for exact?
        # self.assert_get_elements("/users/?username__exact=testuser", 1)
        self.assert_get_elements("/users/?is_staff=1", 1)
        # We have two non-staff users, the test user and the superuser who runs the client.
        self.assert_get_elements("/users/?is_staff=0", 2)
        self.assert_get_elements("/users/?is_staff=0&email__endswith=tld", 1)

        test.delete()
        staff.delete()

    #        self.assert_get_elements("/users/?fqdn__contains=other", 2)

    def test_host_filtering(self):
        """Test that filtering on fields in hosts works."""
        self.assert_get_elements("/hosts/", 3)
        self.assert_get_elements("/hosts/?name__contains=test", 3)
        self.assert_get_elements("/hosts/?fqdn=test2.other.com", 1)
        self.assert_get_elements("/hosts/?fqdn__contains=other", 2)
        self.assert_get_elements("/hosts/?fqdn__startswith=test3.other", 1)
        self.assert_get_elements(f"/hosts/?namespace={self.namespace.id}", 3)
        self.assert_get_elements("/hosts/?name__contains=test&fqdn__contains=domain", 1)

    def test_extension_data_filtering(self):
        """Test that we can filter into the JSON blobs that extensions deliver."""
        host = self.assert_get("/hosts/test1")
        host1id = host.data["id"]
        self.assert_get_elements("/extension_data/", 4)
        self.assert_get_elements(
            "/extension_data/?json_data_lookup=fqdn,other,icontains", 2
        )
        self.assert_get_elements(
            "/extension_data/?json_data_lookup=fqdn,other,exact", 0
        )
        # Implied exact
        self.assert_get_elements("/extension_data/?json_data_lookup=fqdn,other", 0)
        self.assert_get_elements(
            "/extension_data/?json_data_lookup=fqdn,test1.domain.tld,exact", 1
        )
        self.assert_get_and_400(
            "/extension_data/?json_data_lookup=json_data_lookup,1,endswith"
        )
        #        self.assert_get_and_400(
        #            "/extension_data/?json_data_lookup=json_data_lookup,[],endswith"
        #        )
        self.assert_get_elements(f"/extension_data/?json_data_lookup=id,{host1id}", 1)
        self.assert_get_elements(
            f"/extension_data/?json_data_lookup=id,{host1id},gt", 2
        )

        # Test scoping:
        self.assert_get_elements(
            "/extension_data/?json_data_lookup=dns__fqdn,other,icontains", 2
        )
        self.assert_get_elements("/extension_data/?json_data_lookup=dns__fqdn,other", 0)
