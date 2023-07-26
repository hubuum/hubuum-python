"""Test hubuum attachments."""

import hashlib
from typing import Union
from unittest.mock import MagicMock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponse
from django.urls import reverse
from structlog import get_logger
from structlog.testing import capture_logs

from hubuum.api.v1.views.attachment import AttachmentAutoSchema, AttachmentDetail
from hubuum.api.v1.views.base import HubuumDetail
from hubuum.models.core import Attachment, HubuumModel
from hubuum.models.iam import Namespace
from hubuum.models.resources import Host, Person

from .base import HubuumAPITestCase, create_mocked_view


class HubuumAttachmentSchemaTestCase(HubuumAPITestCase):
    """Test the custom autoschema for operation IDs."""

    def setUp(self):
        """Set up the test environment for the class."""
        self.action = "list"
        self.model_name = "MockModel"
        self.schema = AttachmentAutoSchema()
        self.schema.view = create_mocked_view(self.action, self.model_name)
        return super().setUp()

    def test_operation_id_generation_from_url(self):
        """Test different URLs and see what we get back."""
        # We're using lists rather than a dict because black refuses
        # to break key-value pairs into multiple lines, causing the line
        # length to exceed limits.
        question = [
            "/prefix/doesntmatter/{model}",
            "/attachments/data/{model}",
            "/{model}/",
            "/{model}/{instance}",
            "/{model}/{instance}/",
            "/{model}/{instance}/{attachment}",
            "/{model}/{instance}/{attachment}/download",
        ]

        # The first three are the same because the prefix is stripped
        answer = [
            "listMockModelsModel",
            "listMockModelsModel",
            "listMockModelsModel",
            "listMockModelsModelInstance",
            "listMockModelsModelInstanceObject",
            "listMockModelsModelInstanceObjectAttachment",
            "listMockModelsModelInstanceObjectAttachmentDownload",
        ]

        # Enumerate through the lists and test each one
        for i, value in enumerate(question):
            operation_id = self.schema.get_operation_id(value, "get")
            self.assertEqual(operation_id, answer[i])


class HubuumAttachmentTestCase(HubuumAPITestCase):
    """Base class for testing Hubuum Attachments."""

    def setUp(self):
        """Set up the test environment for the class."""
        self.client = self.get_superuser_client()
        self.namespace, _ = Namespace.objects.get_or_create(name="test")
        self.file_content = b"this is a test file"

    def tearDown(self) -> None:
        """Tear down the test environment for the class."""
        self.namespace.delete()
        return super().tearDown()

    def _enable_attachments(self, model: str) -> HttpResponse:
        """Enable attachments for a model."""
        return self.assert_post(
            "/attachments/manager/", {"model": model, "enabled": True}
        )

    def _enable_attachments_for_hosts(self) -> HttpResponse:
        """Enable attachments for hosts."""
        return self._enable_attachments("host")

    def _create_host(self, name: str = "test_host") -> Host:
        """Create a host."""
        return Host.objects.create(name=name, namespace=self.namespace)

    def _create_person(self, username: str = "test_person") -> Person:
        """Create a person."""
        return Person.objects.create(username=username, namespace=self.namespace)

    def _add_attachment(
        self, model: str, obj: HubuumModel, content: bytes
    ) -> HttpResponse:
        """Add an attachment to an object."""
        file = self._create_test_file(content)
        return self.assert_post_and_201(
            f"/attachments/data/{model}/{obj.id}",
            {"attachment": file, "namespace": self.namespace.id},
            format="multipart",
        )

    def _create_test_file(
        self, content: Union[bytes, None] = None
    ) -> SimpleUploadedFile:
        """Create a test file."""
        if content is None:
            content = self.file_content
        return SimpleUploadedFile("test_file.txt", content, content_type="text/plain")


class HubuumAttachmentBasicTestCase(HubuumAttachmentTestCase):
    """Test attachment availability."""

    def test_attachment_create_and_enabled(self):
        """Test that attachments are enabled."""
        self._enable_attachments_for_hosts()
        res = self.assert_get("/attachments/manager/host")

        self.assert_post_and_400(
            "/attachments/manager/", {"model": "host", "enabled": True}
        )

        self.assertEqual(res.data["enabled"], True)
        self.assertTrue(res.data["enabled"])
        self.assert_patch("/attachments/manager/host", {"enabled": False})

        res = self.assert_get("/attachments/manager/host")
        self.assertEqual(res.data["enabled"], False)
        self.assertFalse(res.data["enabled"])

    def test_attachment_unsupported_model(self):
        """Test that unsupported models are rejected."""
        self.assert_post_and_400(
            "/attachments/manager/",
            {"model": "user", "enabled": True, "namespace": self.namespace.id},
        )
        self.assert_post_and_400(
            "/attachments/manager/",
            {"model": "namespace", "enabled": True, "namespace": self.namespace.id},
        )

    def test_attachment_set_limits(self):
        """Test that attachment limitations can be set."""
        self._enable_attachments_for_hosts()
        res = self.assert_get("/attachments/manager/host")
        self.assertEqual(res.data["per_object_count_limit"], 0)
        self.assertEqual(res.data["per_object_individual_size_limit"], 0)
        self.assertEqual(res.data["per_object_total_size_limit"], 0)

        self.assert_patch("/attachments/manager/host", {"per_object_count_limit": 1})

        # This will pass even though the per_object_total_size_limit is 0, as 0 is
        # considered unlimited.
        self.assert_patch(
            "/attachments/manager/host", {"per_object_individual_size_limit": 20}
        )
        self.assert_patch(
            "/attachments/manager/host", {"per_object_total_size_limit": 100}
        )

        # Test that we can't set the total size limit to be smaller than the
        # individual size limit.
        self.assert_patch_and_400(
            "/attachments/manager/host", {"per_object_total_size_limit": 19}
        )

        # Test that we can't set the individual size limit to be larger than the
        # total size limit.
        self.assert_patch_and_400(
            "/attachments/manager/host", {"per_object_individual_size_limit": 101}
        )

        res = self.assert_get("/attachments/manager/host")
        self.assertEqual(res.data["per_object_count_limit"], 1)
        self.assertEqual(res.data["per_object_individual_size_limit"], 20)
        self.assertEqual(res.data["per_object_total_size_limit"], 100)

    def test_attachment_limit_adherence(self):
        """Test that attachment limitations are adhered to."""
        self._enable_attachments_for_hosts()
        self.assert_patch(
            "/attachments/manager/host",
            {
                "per_object_count_limit": 1,
                "per_object_individual_size_limit": 20,
                "per_object_total_size_limit": 30,
            },
        )

        host = self._create_host()
        file = self._create_test_file(b"a test file")
        self.assert_post_and_201(
            f"/attachments/data/host/{host.id}",
            {"attachment": file, "namespace": self.namespace.id},
            format="multipart",
        )

        new_file = self._create_test_file(b"a new test file")
        # Test that we can't upload more than one attachment.
        self.assert_post_and_400(
            f"/attachments/data/host/{host.id}",
            {"attachment": new_file, "namespace": self.namespace.id},
            format="multipart",
        )

        self.assert_patch("/attachments/manager/host", {"per_object_count_limit": 5})

        new_file = self._create_test_file(b"a new test file")
        self.assert_post_and_201(
            f"/attachments/data/host/{host.id}",
            {"attachment": new_file, "namespace": self.namespace.id},
            format="multipart",
        )

        # Test that we can't upload an attachment that is too large.
        # > 20 bytes
        file = self._create_test_file(b"this is a test file that is too large")
        self.assert_post_and_400(
            f"/attachments/data/host/{host.id}",
            {"attachment": file, "namespace": self.namespace.id},
            format="multipart",
        )

        # Test that we can't upload an attachment that would make the total size
        # exceed the limit. 12+16=28 bytes, limit is 30 bytes.
        file = self._create_test_file(b"no space")
        self.assert_post_and_400(
            f"/attachments/data/host/{host.id}",
            {"attachment": file, "namespace": self.namespace.id},
            format="multipart",
        )

    def test_attachment_data_upload(self):
        """Test uploading of an attachment."""
        self._enable_attachments_for_hosts()
        file = self._create_test_file()
        host = self._create_host()

        res = self.assert_post_and_201(
            f"/attachments/data/host/{host.id}",
            {"attachment": file, "namespace": self.namespace.id},
            format="multipart",
        )

        file_hash = hashlib.sha256(self.file_content).hexdigest()

        file_meta = self.assert_get(
            f"/attachments/data/host/{host.id}/{res.data['id']}"
        )

        self.assertEqual(file_meta.data["original_filename"], "test_file.txt")
        self.assertEqual(file_meta.data["size"], len(self.file_content))
        self.assertEqual(file_meta.data["sha256"], file_hash)

        fileres = self.assert_get(
            f"/attachments/data/host/{host.id}/{res.data['id']}/download"
        )

        self.assertEqual(fileres.content, self.file_content)

    def test_attachment_data_permissions(self):
        """Test that permissions are enforced."""
        self._enable_attachments_for_hosts()
        file = self._create_test_file()
        host = self._create_host()

        att = self.assert_post_and_201(
            f"/attachments/data/host/{host.id}",
            {"attachment": file, "namespace": self.namespace.id},
            format="multipart",
        )

        self.assert_get(f"/attachments/data/host/{host.id}/{att.data['id']}")
        self.assert_get(f"/attachments/data/host/{host.id}/{att.data['id']}/download")

        self.client = self.get_user_client()
        self.assert_get_and_403(
            f"/attachments/data/host/{host.id}/{att.data['id']}",
        )
        self.assert_delete_and_403(
            f"/attachments/data/host/{host.id}/{att.data['id']}/download",
        )

        new_host = Host.objects.create(name="new_host", namespace=self.namespace)
        self.assert_get_and_404(
            f"/attachments/data/host/{new_host.id}/{att.data['id']}"
        )

    def test_attachment_filtering(self):
        """Test that filtering works."""
        for model in ["host", "room", "person"]:
            self._enable_attachments(model)

        host_one = self._create_host(name="host_one")
        person_one = self._create_person(username="person_one")
        person_two = self._create_person(username="person_two")

        self._add_attachment("host", host_one, b"host_one")
        self._add_attachment("person", person_one, b"person_one")
        self._add_attachment("person", person_two, b"person_two_one")
        ptt = self._add_attachment("person", person_two, b"person_two_two")
        sha256 = ptt.data["sha256"]

        self.assert_get_elements("/attachments/data/", 4)
        self.assert_get_elements(f"/attachments/data/?sha256={sha256}", 1)
        self.assert_get_elements(
            f"/attachments/data/?sha256__endswith={sha256[-8:]}", 1
        )
        self.assert_get_elements("/attachments/data/?sha256__contains=ee", 2)

        self.assert_get_elements("/attachments/data/?model=host", 1)
        self.assert_get_elements("/attachments/data/?model=person", 3)

        # Misspell person
        self.assert_get_and_404("/attachments/data/?model=persona")

        # Fielderror
        self.assert_get_and_400("/attachments/data/?modela=person")

        self.assert_get_elements("/attachments/data/host/", 1)
        self.assert_get_elements("/attachments/data/person/", 3)
        self.assert_get_elements(f"/attachments/data/person/{person_two.id}/", 2)
        self.assert_get_elements(
            f"/attachments/data/person/{person_two.id}/?sha256__endswith=ffffff", 0
        )
        self.assert_get_elements(
            f"/attachments/data/person/{person_two.id}/?sha256__endswith={sha256[-8:]}",
            1,
        )

        # Forgetting the query string separator (?).
        self.assert_get_and_404("/attachments/data/person/username=person_two")

        # Filtering by owner objects
        self.assert_get_elements("/attachments/data/person/?username=person_one", 1)
        self.assert_get_elements("/attachments/data/person/?username=person_two", 2)
        self.assert_get_elements(f"/attachments/data/person/?id={person_two.id}", 2)

        # Filtering on sha256 in model listing (requires manipulation of the query)
        self.assert_get_elements(
            f"/attachments/data/person/?username=person_two&sha256={sha256}", 1
        )

        # Ironically, both of the attachments with sha256s that contain "ee" belong
        # to person_two.
        self.assert_get_elements(
            "/attachments/data/person/?username=person_two&sha256__contains=ee", 2
        )
        self.assert_get_elements(
            "/attachments/data/person/?username=person_two&sha256__endswith=ffff", 0
        )
        self.assert_get_elements(
            f"/attachments/data/person/?username=person_two&sha256__endswith={sha256[-8:]}",
            1,
        )

        # Broken query string
        self.assert_get_and_400("/attachments/data/person/?uname=person_two")
        self.assert_get_and_400("/attachments/data/person/?id=foo")

    def test_attachment_data_duplicate(self):
        """Test uploading of an attachment."""
        self._enable_attachments_for_hosts()
        file = self._create_test_file()
        host = self._create_host()

        self.assert_post_and_201(
            f"/attachments/data/host/{host.id}",
            {"attachment": file, "namespace": self.namespace.id},
            format="multipart",
        )

        file = self._create_test_file()
        self.assert_post_and_409(
            f"/attachments/data/host/{host.id}",
            {"attachment": file, "namespace": self.namespace.id},
            format="multipart",
        )

    def test_attachment_failures(self):
        """Test various attachment failures."""
        # No such model
        self.assert_get_and_404("/attachments/data/nope/1")
        self.assert_post_and_404("/attachments/data/nope/1", {})

        # Filter on model that does not support attachments
        self.assert_get_and_400("/attachments/data/?model=namespace")

        # Filter on non-existent model
        self.assert_get_and_404("/attachments/data/?model=nope")

        host = self._create_host()
        file = self._create_test_file()
        # Model exists, but does not have attachments enabled
        self.assert_post_and_400(
            f"/attachments/data/host/{host.id}",
            {"attachment": file, "namespace": self.namespace.id},
            format="multipart",
        )

        # Model exists, but does not have support for attachments
        self.assert_get_and_400("/attachments/data/namespace/1")
        self.assert_post_and_400(
            f"/attachments/data/namespace/{self.namespace.id}",
            {"attachment": file, "namespace": self.namespace.id},
            format="multipart",
        )

        # Model exists, has attachments enabled, but the attachment does not exist
        self._enable_attachments_for_hosts()
        self.assert_get_and_404("/attachments/data/host/1")
        self.assert_get_and_404("/attachments/data/host/wrongtypehere")

        # No such host
        self.assert_post_and_404("/attachments/data/host/99", {})

        # Disable attachments for host, and try again
        host = self._create_host()
        self.assert_patch("/attachments/manager/host", {"enabled": False})
        self.assert_post_and_400(
            f"/attachments/data/host/{host.id}", format="multipart"
        )

        # Uploading without setting format=multipart
        self.assert_post_and_415(
            f"/attachments/data/host/{host.id}",
            {"attachment": "notafile", "namespace": self.namespace.id},
        )

    def test_attachment_delete(self):
        """Test manually deleting an attachment."""
        self._enable_attachments_for_hosts()
        file = self._create_test_file()
        host = self._create_host()

        att = self.assert_post_and_201(
            f"/attachments/data/host/{host.id}",
            {"attachment": file, "namespace": self.namespace.id},
            format="multipart",
        )

        self.assert_get(f"/attachments/data/host/{host.id}/{att.data['id']}")
        self.assert_get(f"/attachments/data/host/{host.id}/{att.data['id']}/download")

        self.assert_delete(f"/attachments/data/host/{host.id}/{att.data['id']}")
        self.assert_get_and_404(f"/attachments/data/host/{host.id}/{att.data['id']}")
        self.assert_get_and_404(
            f"/attachments/data/host/{host.id}/{att.data['id']}/download"
        )

    # TODO: patch.object?
    def _patch_path(self, cls: HubuumModel, function_name: str) -> str:
        """Create a patch path for a function in a class."""
        return f"{cls.__module__}.{cls.__name__}.{function_name}"

    def test_attachment_download_file_not_found(self):
        """Test downloading an attachment that does not exist.

        This should give us a 404, and log an error. We check for both.
        """
        _get_attachment_path = self._patch_path(AttachmentDetail, "_get_attachment")
        file_response_path = self._patch_path(HubuumDetail, "file_response")

        with patch(_get_attachment_path) as mock_get_attachment:
            with patch(file_response_path) as mock_file_response:
                mock_get_attachment.return_value = MagicMock(spec=Attachment, data=b"")
                mock_file_response.side_effect = FileNotFoundError()

                url = reverse(
                    "download_attachment",
                    kwargs={
                        "model": "mymodel",
                        "instance": 1,
                        "attachment": "myattachment",
                    },
                )

                with capture_logs() as cap_logs:
                    get_logger().bind()

                    response = self.client.get(url)
                    self.assertEqual(response.status_code, 404)
                    self.assert_list_contains(
                        cap_logs,
                        lambda it: (
                            it.get("log_level") == "error"
                            and it.get("event") == "attachment_file"
                            and it.get("file_status") == "missing"
                        ),
                    )
