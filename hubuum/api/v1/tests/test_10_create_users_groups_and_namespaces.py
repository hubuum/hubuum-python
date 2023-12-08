"""Test users, groups, and namespaces."""

from .base import HubuumAPITestCase


class APIUsersAndGroupsTestCase(HubuumAPITestCase):
    """Test creating users and groups operations."""

    def test_staff_create_user(self):
        """Test authenticated user creation."""
        self.client = self.get_staff_client()
        response = self.assert_post("/iam/users/", {"username": "userone", "password": "test"})
        data = response.json()
        self.assertEqual(data["username"], "userone")

    def test_user_create_user(self):
        """Test normal users ability to create users."""
        self.client = self.get_user_client()
        self.assert_post_and_403("/iam/users/", {"username": "userone", "password": "test"})

    def test_list_users(self):
        """Test listing of users."""
        self.client = self.get_staff_client()
        # We currently have two users created during setUp()
        self.assert_get_elements("/iam/users/", 2)

        # Repeat the same for a normal user. This implicitly creates another user.
        self.client = self.get_user_client()
        self.assert_get_elements("/iam/users/", 3)

    def test_get_user_by_username_or_email(self):
        """Test getting of users by username or email."""
        self.client = self.get_staff_client()
        self.assert_post(
            "/iam/users/",
            {"username": "userone", "password": "test", "email": "test@test.nowhere"},
        )
        response = self.assert_get("/iam/users/userone")
        self.assertEqual(response.data["username"], "userone")
        response = self.assert_get("/iam/users/test@test.nowhere")
        self.assertEqual(response.data["username"], "userone")
        self.assert_get_and_404("/iam/users/nosuchusername")

    def test_create_and_delete_group(self):
        """Test authenticated group creation."""
        self.client = self.get_staff_client()
        response = self.assert_post("/iam/groups/", {"name": "groupone"})
        self.assertEqual(response.data["name"], "groupone")
        response = self.assert_get_elements("/iam/groups/", 1)

        self.assert_delete("/iam/groups/" + str(response.data[0]["id"]))
        self.assert_get_elements("/iam/groups/", 0)

        # Repeat the same for a normal user. This implicitly creates another group...
        self.client = self.get_user_client()
        self.assert_get_elements("/iam/groups/", 1)

        self.assert_delete_and_403("/iam/groups/" + str(response.data[0]["id"]))
        self.assert_get_elements("/iam/groups/", 1)

    def test_staff_add_user_to_group(self):
        """Test add user to group."""
        self.client = self.get_staff_client()
        self.assert_post(
            "/iam/users/",
            {"username": "userone", "password": "test", "email": "test@test.nowhere"},
        )
        userresponse = self.assert_get("/iam/users/userone")
        self.assertEqual(userresponse.data["username"], "userone")
        self.assertEqual(len(userresponse.data["groups"]), 0)
        groupresponse = self.assert_post("/iam/groups/", {"name": "groupone"})
        self.assertEqual(groupresponse.data["name"], "groupone")

        userresponse = self.assert_patch(
            "/iam/users/userone", {"groups": [groupresponse.data["id"]]}
        )
        self.assertTrue(groupresponse.data["id"] in userresponse.data["groups"])
        userresponse = self.assert_get("/iam/users/userone")
        self.assertEqual(userresponse.data["username"], "userone")

    def test_user_create_group(self):
        """Test normal users ability to create groups."""
        self.client = self.get_user_client()
        self.assert_post_and_403("/iam/groups/", {"name": "groupone"})

    def test_patch_group(self):
        """Test normal users ability to patch groups."""
        self.client = self.get_staff_client()
        self.assert_post("/iam/groups/", {"name": "groupone"})
        self.assert_patch_and_400("/iam/groups/groupone", {"wrongkey": "nope"})

        self.client = self.get_user_client()
        self.assert_get("/iam/groups/groupone")
        self.assert_patch_and_403("/iam/groups/groupone", {"name": "nope"})

    def test_user_delete_group(self):
        """Test normal users ability to delete groups."""
        self.client = self.get_user_client()
        self.assert_delete_and_403("/iam/groups/0")

    def test_combined_reference_list_endpoint(self):
        """Test the /groups/<gid>/members/ endpoint."""
        self.client = self.get_staff_client()
        self.assert_post("/iam/groups/", {"name": "groupone"})
        self.assert_get_elements("/iam/groups/groupone/members/", 0)
        self.assert_get_and_404("/iam/groups/groupnope/members/")
        self.assert_post_and_405("/iam/groups/groupnope/members/")
        self.assert_patch_and_405("/iam/groups/groupnope/members/")

        self.assert_delete("/iam/groups/groupone")

    def test_combined_reference_singular_endpoint(self):
        """Test the /groups/<gid>/members/<uid> endpoint."""
        self.client = self.get_staff_client()
        self.assert_post("/iam/groups/", {"name": "groupone"})
        self.assert_post(
            "/iam/users/",
            {"username": "userone", "password": "test", "email": "test@test.nowhere"},
        )

        self.assert_post_and_201("/iam/groups/groupone/members/userone")
        self.assert_post_and_200("/iam/groups/groupone/members/userone")

        self.assert_get_and_404("/iam/groups/groupnotfound/members/")
        self.assert_get_and_404("/iam/groups/groupnotfound/members/userone")

        self.assert_post_and_404("/iam/groups/groupnotfound/members/userone")
        self.assert_post_and_404("/iam/groups/groupone/members/usernotfound")

        self.assert_get("/iam/groups/groupone/members/userone")
        self.assert_get_elements("/iam/groups/groupone/members/", 1)

        self.assert_delete("/iam/groups/groupone/members/userone")
        self.assert_delete("/iam/groups/groupone/members/userone")
        self.assert_delete_and_404("/iam/groups/groupone/members/usernotfound")
        self.assert_get_and_404("/iam/groups/groupone/members/userone")
        self.assert_patch_and_405("/iam/groups/groupone/members/userone")
        self.assert_get_elements("/iam/groups/groupone/members/", 0)

        self.assert_delete("/iam/groups/groupone")
        self.assert_delete("/iam/users/userone")

        # This should delete all members from the group


#        self.assert_delete_and_405("/iam/groups/groupnope/members/")


#        self.get("/")


class APIPreliminaryNamespaceTestCase(HubuumAPITestCase):
    """Test creation and manipulation of Namespaces."""

    def test_staff_create_namespace(self):
        """Test authenticated namespace creation."""
        self.client = self.get_staff_client()
        response = self.assert_post("/iam/namespaces/", {"name": "namespaceone"})
        data = response.json()
        self.assertEqual(data["name"], "namespaceone")
        self.assert_get_and_200("/iam/namespaces/namespaceone")

    def test_user_create_root_namespace(self):
        """Test users ability to create root namespaces."""
        self.client = self.get_user_client()
        self.assert_post_and_403("/iam/namespaces/", {"name": "namespaceone"})

    def test_user_create_scoped_namespace(self):
        """Test users ability to create scoped namespaces."""
        self.client = self.get_staff_client()
        self.assert_post("/iam/namespaces/", {"name": "namespaceone"})
        self.client = self.get_user_client()
        self.assert_post_and_403("/iam/namespaces/", {"name": "namespaceone.mine"})

        # Test giving the user access and create a scoped namespace


class APIPreliminaryPermissionTestCase(HubuumAPITestCase):
    """Test creation and manipulation of permissions."""

    def test_group_namespace_endpoint_post(self):
        """Test posting to the combined namespace and group endpoints."""
        self.assert_post("/iam/namespaces/", {"name": "namespaceone"})
        self.assert_post("/iam/groups/", {"name": "groupone"})
        self.assert_post("/iam/groups/", {"name": "grouptwo"})

        self.assert_post_and_404("/iam/namespaces/namespacedoesnotexist/groups/groupone")
        self.assert_post_and_204(
            "/iam/namespaces/namespaceone/groups/groupone",
            {"has_read": True},
        )
        # Try that again. Get a conflict as the object already exists.
        self.assert_post_and_409(
            "/iam/namespaces/namespaceone/groups/groupone",
            {"has_read": True},
        )

        self.assert_post_and_400(
            "/iam/namespaces/namespaceone/groups/grouptwo",
            {"has_namespacebork": False, "has_create": True},
        )

        # Post with no such group
        self.assert_post_and_404(
            "/iam/namespaces/namespaceone/groups/nosuchgroup",
            {"has_read": True},
        )
        # Post with group missing
        self.assert_post_and_405(
            "/iam/namespaces/namespaceone/groups/",
            {"has_read": True},
        )
        # Post with no permissions given
        self.assert_post_and_400(
            "/iam/namespaces/namespaceone/groups/groupone",
        )
        self.assert_delete("/iam/namespaces/namespaceone")

    def test_group_namespace_endpoint(self):
        """Test the combined namespace and group endpoints."""
        self.client = self.get_staff_client()
        self.assert_post("/iam/namespaces/", {"name": "namespaceone"})
        self.assert_post("/iam/groups/", {"name": "groupone"})
        self.assert_post("/iam/groups/", {"name": "grouptwo"})
        self.assert_get("/iam/namespaces/namespaceone/groups/")

        self.assert_post_and_204(
            "/iam/namespaces/namespaceone/groups/grouptwo",
            {"has_namespace": True},
        )

        self.assert_get_and_404("/iam/namespaces/namespacedoesnotexist/groups/")

        self.assert_post_and_204(
            "/iam/namespaces/namespaceone/groups/groupone",
            {"has_read": True},
        )

        self.assert_get_and_404(
            "/iam/namespaces/namespaceone/groups/nosuchgroup",
        )

        self.assert_get(
            "/iam/namespaces/namespaceone/groups/grouptwo",
        )

        self.assert_get_and_404(
            "/iam/namespaces/namespaceone/groups/groupdoesnotexist",
        )

        self.assert_delete("/iam/namespaces/namespaceone")

    def test_group_namespace_endpoint_delete(self):
        """Test deleting combined namespace and group endpoints."""
        self.client = self.get_staff_client()
        self.assert_post("/iam/namespaces/", {"name": "namespaceone"})
        self.assert_post("/iam/groups/", {"name": "groupone"})
        self.assert_post("/iam/groups/", {"name": "grouptwo"})

        self.assert_post_and_204(
            "/iam/namespaces/namespaceone/groups/grouptwo",
            {"has_read": True},
        )

        self.assert_post_and_204(
            "/iam/namespaces/namespaceone/groups/groupone",
            {"has_read": True},
        )

        self.assert_get_elements("/iam/namespaces/namespaceone/groups/", 2)
        self.assert_get_elements("/iam/permissions/", 2)

        self.assert_delete("/iam/namespaces/namespaceone/groups/grouptwo")

        self.assert_get_and_404(
            "/iam/namespaces/namespaceone/groups/grouptwo",
        )

        self.assert_get_elements("/iam/namespaces/namespaceone/groups/", 1)
        self.assert_get_elements("/iam/permissions/", 1)
        self.assert_delete("/iam/namespaces/namespaceone")
        self.assert_get_elements("/iam/permissions/", 0)

    def test_group_namespace_endpoint_patch(self):
        """Test patching combined namespace and group endpoints."""
        self.client = self.get_staff_client()
        self.assert_post("/iam/namespaces/", {"name": "namespaceone"})
        self.assert_post("/iam/groups/", {"name": "groupone"})

        self.assert_post_and_204(
            "/iam/namespaces/namespaceone/groups/groupone",
            {"has_read": True},
        )

        response = self.assert_get("/iam/namespaces/namespaceone/groups/groupone")
        self.assertEqual(response.data["has_read"], True)
        self.assertEqual(response.data["has_create"], False)

        self.assert_patch_and_204(
            "/iam/namespaces/namespaceone/groups/groupone",
            {"has_create": True},
        )

        response = self.assert_get("/iam/namespaces/namespaceone/groups/groupone")
        self.assertEqual(response.data["has_read"], True)
        self.assertEqual(response.data["has_create"], True)
