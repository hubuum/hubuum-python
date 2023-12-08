"""Test the filter interface."""

from hubuum.api.v1.tests.helpers.populators import APIv1Objects
from hubuum.models.iam import User


class HubuumFilterTestCase(APIv1Objects):
    """Base class for testing Hubuum Filtering."""

    def host_json_data_lookup(self, lookup: str, expected_results: int) -> None:
        """Test a JSON lookup on the Host model."""
        self.assert_get_elements(f"/dynamic/Host/?json_data_lookup={lookup}", expected_results)

    # These tests will differ on different database engines, but each coverage
    # pass only uses one engine, so we can't get 100% coverage.
    def test_database_specific_filtering(self):  # pragma: no cover
        """Test filters that differ between database engines."""
        User.objects.create(username="stafftestuser", email="staff@domain.COM", is_staff=True)
        # SQLite doesn't support case-sensitive lookup operators, so results may differ.
        # Here, on SQLite, we will match the user with staff@domain.COM, but on postgres,
        # we will NOT match due to case sensitivity.
        # https://docs.djangoproject.com/en/4.2/ref/databases/#sqlite-string-matching
        # (Arguments about case sensitivity in domain names emails not withstanding,
        # this is a test of the filter)
        if self.db_engine_is_sqlite():
            self.assert_get_elements("/iam/users/?email__endswith=com", 1)
        else:
            self.assert_get_elements("/iam/users/?email__endswith=com", 0)

    def test_user_filtering(self):
        """Test that filtering on fields in users works."""
        test = User.objects.create(username="testuser", email="test@domain.tld", is_staff=False)
        staff = User.objects.create(
            username="stafftestuser", email="staff@domain.COM", is_staff=True
        )
        self.assert_get_elements("/iam/users/", 3)
        self.assert_get_elements("/iam/users/?email__contains=domain", 2)

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

    def test_bad_filters_returning_400(self):
        """Test that using bad filters returns a 400."""
        self.assert_get_and_400("/dynamic/Host/?nosuchfield=foo")
        self.assert_get_and_400("/dynamic/Host/?nosuchfield__withlookup=foo")
        self.assert_get_and_400("/dynamic/Host/?name__nosuchlookup=foo")
        # name__gt is not supported, it's a numeric lookup on a textual field
        self.assert_get_and_400("/dynamic/Host/?name__gt=foo")

    def test_host_filtering(self):
        """Test that filtering on fields in hosts works."""
        ns = self.namespace
        self.assert_get_elements("/dynamic/Host/", 3)
        self.assert_get_elements("/dynamic/Host/?name__contains=host", 3)
        self.assert_get_elements("/dynamic/Host/?name=host1", 1)
        self.assert_get_elements("/dynamic/Host/?name__endswith=2", 1)
        self.assert_get_elements(f"/dynamic/Host/?namespace__name={ns.name}", 3)
        self.assert_get_elements(f"/dynamic/Host/?namespace={ns.id}", 3)
        # Regex testing
        self.assert_get_elements(r"/dynamic/Host/?name__regex=host[23]", 2)
        self.assert_get_elements(r"/dynamic/Host/?name__regex=host[3-9]", 1)
        self.assert_get_elements(r"/dynamic/Host/?name__regex=^host[13]", 2)

    def test_basic_filtering(self):
        """Test that we can filter into the JSON blobs that extensions deliver."""
        self.host_json_data_lookup("name=host1", 1)
        self.host_json_data_lookup("name=host_nope", 0)
        self.host_json_data_lookup("name__icontains=host", 3)
        self.host_json_data_lookup("name__icontains=host1", 1)
        self.host_json_data_lookup("name__exact=host", 0)
        self.host_json_data_lookup("name__exact=host1", 1)
        self.host_json_data_lookup("name__startswith=host", 3)

        # Implied exact
        self.host_json_data_lookup("name=other", 0)
        self.host_json_data_lookup("name=host1", 1)

    def test_numeric_filtering(self):
        """Test that we can filter into the JSON blobs that extensions deliver."""
        ns1id = self.namespaces[0].id
        ns2id = self.namespaces[1].id
        host_class = self.get_class_from_cache("Host")
        host4 = self.create_object_direct(host_class, self.namespaces[1], name="host4")

        self.host_json_data_lookup(f"namespace_id={ns1id}", 3)
        self.host_json_data_lookup(f"namespace_id={ns2id}", 1)
        self.host_json_data_lookup(f"namespace_id__exact={ns1id}", 3)

        self.host_json_data_lookup(f"namespace_id__gt={ns1id}", 1)
        self.host_json_data_lookup(f"namespace_id__gte={ns1id}", 4)
        self.host_json_data_lookup(f"namespace_id__lt={ns2id}", 3)
        self.host_json_data_lookup(f"namespace_id__gt={ns2id}", 0)
        host4.delete()

    def test_json_scoping(self):
        """Test that we can parse JSON scopes correctly."""
        self.host_json_data_lookup("dictkey__one=valueone", 3)
        self.host_json_data_lookup("dictkey__one__exact=valueone", 3)
        self.host_json_data_lookup("dictkey__two__name=host1", 1)
        self.host_json_data_lookup("dictkey__two__name__exact=host1", 1)
        self.host_json_data_lookup("dictkey__two__name__icontains=host", 3)
        self.host_json_data_lookup("dictkey__two__name__endswith=t2", 1)

        self.host_json_data_lookup("dictkey__two__name__endswith=nope", 0)
        self.host_json_data_lookup("dictkey__two__name=hostnope", 0)

    def test_json_array_comprehension(self):
        """Test that we can parse JSON arrays correctly."""
        self.host_json_data_lookup("listkey__0=1", 3)
        self.host_json_data_lookup("listkey__1=2", 3)
        self.host_json_data_lookup("listkey__2=3", 3)
        self.host_json_data_lookup("listkey__0__gt=1", 0)
        self.host_json_data_lookup("listkey__1__gt=1", 3)

    def test_filtering_mismatches(self):
        """Test that we validate JSON lookups correctly."""
        # Missing value
        self.assert_get_and_400("/dynamic/Host/?json_data_lookup=list")
        # Using the wrong lookup
        self.assert_get_and_400("/dynamic/Host/?json_data_lookup=id__contains=2")

    def test_extension_data_filtering_with_lookups_as_keys(self):
        """Test that we validate JSON lookups correctly."""
        # Here we have "weird": {"exact": "value"}, so weird__exact is valid,
        # but tests against the list, so we get zero hits.
        # See #76.
        self.assert_get_elements("/dynamic/Host/?json_data_lookup=weird__exact=value", 0)
