"""Test namespaces."""

from rest_framework.test import APIClient

from .base import HubuumAPITestCase


class APINamespace(HubuumAPITestCase):
    """Test namespaces."""

    def test_namespace_access_as_noone(self):
        """Test access to namespaces as a noone."""
        self.client = self.get_superuser_client()
        self.assert_post("/iam/namespaces/", {"name": "yes"})

        self.client = APIClient()
        self.assert_post_and_401("/iam/namespaces/", {"name": "no"})
        self.assert_patch_and_401("/iam/namespaces/yes", {"name": "maybe"})
        self.assert_get_and_401("/iam/namespaces/yes")
        self.assert_get_and_401("/iam/namespaces/no")
        self.assert_delete_and_401("/iam/namespaces/yes")
        self.assert_get_and_401("/iam/namespaces/")

    def test_field_validation(self):
        """Test that we can't write to read-only fields."""
        self.assert_post("/iam/namespaces/", {"name": "namespaceone"})
        self.assert_patch_and_400("/iam/namespaces/namespaceone", {"created_at": "2022-01-01"})
        self.assert_patch_and_400("/iam/namespaces/namespaceone", {"nosuchkey": "2022-01-01"})

        # NOTICE: Comma, not colon. This leads to a set being serialized as a list...
        self.assert_patch_and_400("/iam/namespaces/namespaceone", {"not_a", "dict"})
        self.assert_delete("/iam/namespaces/namespaceone")

    def test_namespaces_as_superuser(self):
        """Test namespaces as a superuser."""
        self.client = self.get_superuser_client()

        self.assert_post("/iam/namespaces/", {"name": "namespaceone"})
        self.assert_post_and_400("/iam/namespaces/", {"name": "namespaceone"})
        self.assert_get("/iam/namespaces/namespaceone")

        self.assert_get_elements("/iam/namespaces/", 1)
        self.assert_post("/iam/namespaces/", {"name": "namespacetwo"})
        self.assert_get_elements("/iam/namespaces/", 2)
        self.assert_delete("/iam/namespaces/namespaceone")
        self.assert_get_elements("/iam/namespaces/", 1)
        self.assert_delete_and_404("/iam/namespaces/namespaceone")

        response = self.assert_get_elements("/iam/namespaces/", 1)
        nid = response.data[0]["id"]
        self.assert_patch_and_404("/iam/namespaces/nope", {"name": "namespace_not_two"})
        self.assert_patch(f"/iam/namespaces/{nid}", {"name": "namespace_not_two"})
        self.assert_get("/iam/namespaces/namespace_not_two")
        self.assert_get(f"/iam/namespaces/{nid}")
        self.assert_delete(f"/iam/namespaces/{nid}")
        self.assert_get_elements("/iam/namespaces/", 0)
        self.assert_get_and_404("/iam/namespaces/namespace_not_two")

    def test_namespace_get_as_user(self):
        """Test get on namespaces as a normal user."""
        # This creates the user and the group in one go.
        self.client = userclient = self.get_user_client(username="tmp", groupname="tmpgroup")
        self.client = self.get_superuser_client()
        self.assert_post("/iam/namespaces/", {"name": "yes"})
        self.assert_post("/iam/namespaces/", {"name": "no"})
        self.assert_post_and_204("/iam/namespaces/yes/groups/tmpgroup", {"has_read": True})
        self.assert_get_elements("/iam/namespaces/", 2)

        self.client = userclient
        self.assert_get_elements("/iam/namespaces/", 1)
        self.assert_get("/iam/namespaces/yes")
        self.assert_get_and_403("/iam/namespaces/no")
        self.assert_get_and_404("/iam/namespaces/doesnotexist")
        self.assert_patch_and_403("/iam/namespaces/yes", {"name": "maybe"})
        self.assert_delete_and_403("/iam/namespaces/yes")

    def test_namespace_patch_as_user(self):
        """Test patch on namespaces as a normal user."""
        # This creates the user and the group in one go.
        self.client = userclient = self.get_user_client(username="tmp", groupname="tmpgroup")
        self.client = self.get_superuser_client()
        self.assert_post("/iam/namespaces/", {"name": "yes"})

        self.client = userclient
        self.assert_patch_and_403("/iam/namespaces/yes", {"name": "maybe"})

        self.client = self.get_superuser_client()
        self.assert_post_and_204("/iam/namespaces/yes/groups/tmpgroup", {"has_namespace": True})

        self.client = userclient
        self.assert_patch("/iam/namespaces/yes", {"name": "maybe"})
        self.assert_get("/iam/namespaces/maybe")

    def test_namespace_delete_as_user(self):
        """Test delete on namespaces as a normal user."""
        # This creates the user and the group in one go.
        self.client = userclient = self.get_user_client(username="tmp", groupname="tmpgroup")
        self.client = self.get_superuser_client()
        self.assert_post("/iam/namespaces/", {"name": "yes"})

        self.client = userclient
        self.assert_delete_and_403("/iam/namespaces/yes")

        self.client = self.get_superuser_client()
        self.assert_post_and_204("/iam/namespaces/yes/groups/tmpgroup", {"has_namespace": True})

        self.client = userclient
        self.assert_delete("/iam/namespaces/yes")
        self.assert_get_and_404("/iam/namespaces/yes")

    def test_namespace_has_namespace_as_user(self):
        """Test has_namespace on namespaces as a normal user."""
        self.client = userclient = self.get_user_client(username="tmp", groupname="tmpgroup")
        self.client = self.get_superuser_client()
        self.assert_post("/iam/namespaces/", {"name": "yes"})

        self.client = userclient
        self.assert_post_and_405("/iam/namespaces/yes", {"name": "subnamespace"})

        self.client = self.get_superuser_client()
        self.assert_post_and_204("/iam/namespaces/yes/groups/tmpgroup", {"has_namespace": True})

        self.client = userclient
        self.assert_post_and_405("/iam/namespaces/yes", {"name": "subnamespace"})
        self.assert_post_and_405("/iam/namespaces/yes", {"namespace": "subnamespace"})
        # Not implemented, see permissions.py -> has_permission.
        self.assert_get("/iam/namespaces/yes")
        self.assert_post("/iam/namespaces/", {"name": "yes.subnamespace"})

        self.client = self.get_superuser_client()
        self.assert_get("/iam/namespaces/yes.subnamespace")

        self.client = userclient
        self.assert_get("/iam/namespaces/yes.subnamespace")

    def test_namespace_as_user_with_multiple_group_memberships(self):
        """Test has_namespace as a normal user but with multiple group memberships."""
        userclient = self.get_user_client(username="userone", groupname="groupone")
        self.client = self.get_superuser_client()
        self.assert_post("/iam/namespaces/", {"name": "yes"})
        groupone = self.assert_get("/iam/groups/groupone")
        grouptwo = self.assert_post("/iam/groups/", {"name": "grouptwo"})
        groupthree = self.assert_post("/iam/groups/", {"name": "groupthree"})

        self.assert_post_and_204("/iam/namespaces/yes/groups/groupone", {"has_namespace": True})

        self.assert_patch(
            "/iam/users/userone",
            {
                "groups": [groupone.data["id"], grouptwo.data["id"]],
            },
        )

        self.client = userclient
        self.add_user_to_groups(["groupone", "grouptwo"])
        self.assert_get("/iam/namespaces/yes")
        # This fails as the user is a member of more than one group and none are offered.
        self.assert_post_and_400("/iam/namespaces/", {"name": "yes.subnamespace"})
        # This fails as the user is not a member of groupthree.
        self.assert_post_and_400(
            "/iam/namespaces/",
            {"name": "yes.subnamespace", "group": groupthree.data["id"]},
        )
        # This works.
        self.assert_post(
            "/iam/namespaces/",
            {"name": "yes.subnamespace", "group": grouptwo.data["id"]},
        )
        self.assert_get("/iam/namespaces/yes.subnamespace")
