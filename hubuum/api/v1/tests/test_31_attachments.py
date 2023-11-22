"""Test hubuum attachments."""

import hashlib
from typing import Union
from unittest.mock import MagicMock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponse
from django.urls import reverse
from structlog import get_logger
from structlog.testing import capture_logs

from hubuum.api.v1.tests.helpers.populators import APIv1Objects
from hubuum.api.v1.views.attachment import AttachmentAutoSchema, AttachmentDetail
from hubuum.api.v1.views.base import HubuumDetail
from hubuum.models.core import Attachment, HubuumModel

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
            "/prefix/doesntmatter/{class}",
            "/attachments/data/{class}",
            "/{class}/",
            "/{class}/{instance}",
            "/{class}/{instance}/",
            "/{class}/{instance}/{attachment}",
            "/{class}/{instance}/{attachment}/download",
        ]

        # The first three are the same because the prefix is stripped
        answer = [
            "listMockModelsClass",
            "listMockModelsClass",
            "listMockModelsClass",
            "listMockModelsClassInstance",
            "listMockModelsClassInstanceObject",
            "listMockModelsClassInstanceObjectAttachment",
            "listMockModelsClassInstanceObjectAttachmentDownload",
        ]

        # Enumerate through the lists and test each one
        for i, value in enumerate(question):
            operation_id = self.schema.get_operation_id(value, "get")
            self.assertEqual(operation_id, answer[i])


class HubuumAttachmentTestCase(APIv1Objects):
    """Base class for testing Hubuum Attachments."""

    def setUp(self):
        """Set up the test environment for the class."""
        super().setUp()
        self.client = self.get_superuser_client()
        self.file_content = b"this is a test file"

    def _enable_attachments(self, cls: str) -> HttpResponse:
        """Enable attachments for a model."""
        return self.assert_post(
            "/attachments/manager/", {"class": cls, "enabled": True}
        )

    def _enable_attachments_for_hosts(self) -> HttpResponse:
        """Enable attachments for hosts."""
        return self._enable_attachments("Host")

    def _add_attachment(
        self, cls: str, obj: HubuumModel, content: bytes
    ) -> HttpResponse:
        """Add an attachment to an object."""
        file = self._create_test_file(content)
        return self.assert_post_and_201(
            f"/attachments/data/{cls}/{obj.id}",
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
        res = self.assert_get("/attachments/manager/Host")

        self.assert_post_and_404(
            "/attachments/manager/", {"class": "Hos", "enabled": True}
        )

        self.assertEqual(res.data["enabled"], True)
        self.assertTrue(res.data["enabled"])
        self.assert_patch("/attachments/manager/Host", {"enabled": False})

        res = self.assert_get("/attachments/manager/Host")
        self.assertEqual(res.data["enabled"], False)
        self.assertFalse(res.data["enabled"])

    def test_attachment_unsupported_class(self):
        """Test that unsupported classes are rejected."""
        self.assert_post_and_400(
            "/attachments/manager/",
            {"class": "Building", "enabled": True, "namespace": self.namespace.id},
        )
        # Namespace exists, but is not a usable class.
        self.assert_post_and_404(
            "/attachments/manager/",
            {"class": "namespace", "enabled": True, "namespace": self.namespace.id},
        )

    def test_attachment_set_limits(self):
        """Test that attachment limitations can be set."""
        self._enable_attachments_for_hosts()
        res = self.assert_get("/attachments/manager/Host")
        self.assertEqual(res.data["per_object_count_limit"], 0)
        self.assertEqual(res.data["per_object_individual_size_limit"], 0)
        self.assertEqual(res.data["per_object_total_size_limit"], 0)

        self.assert_patch("/attachments/manager/Host", {"per_object_count_limit": 1})

        # This will pass even though the per_object_total_size_limit is 0, as 0 is
        # considered unlimited.
        self.assert_patch(
            "/attachments/manager/Host", {"per_object_individual_size_limit": 20}
        )
        self.assert_patch(
            "/attachments/manager/Host", {"per_object_total_size_limit": 100}
        )

        # Test that we can't set the total size limit to be smaller than the
        # individual size limit.
        self.assert_patch_and_400(
            "/attachments/manager/Host", {"per_object_total_size_limit": 19}
        )

        # Test that we can't set the individual size limit to be larger than the
        # total size limit.
        self.assert_patch_and_400(
            "/attachments/manager/Host", {"per_object_individual_size_limit": 101}
        )

        res = self.assert_get("/attachments/manager/Host")
        self.assertEqual(res.data["per_object_count_limit"], 1)
        self.assertEqual(res.data["per_object_individual_size_limit"], 20)
        self.assertEqual(res.data["per_object_total_size_limit"], 100)

    def test_creating_attachment_on_nonexistent_object(self):
        """Test that creating attachments on nonexistent objects fails."""
        self._enable_attachments_for_hosts()
        file = self._create_test_file(b"a test file")
        self.assert_post_and_404(
            "/attachments/data/Host/hostdoesnotexist",
            {"attachment": file, "namespace": self.namespace.id},
            format="multipart",
        )

    def test_missing_attachment_manager(self):
        """Test fetching the attachment manager for a class without one."""
        self.assert_get_and_404("/attachments/manager/Host")

    def test_attachment_limit_adherence(self):
        """Test that attachment limitations are adhered to."""
        self._enable_attachments_for_hosts()
        self.assert_patch(
            "/attachments/manager/Host",
            {
                "per_object_count_limit": 1,
                "per_object_individual_size_limit": 20,
                "per_object_total_size_limit": 30,
            },
        )

        host = self.hosts[0]
        file = self._create_test_file(b"a test file")
        self.assert_post_and_201(
            f"/attachments/data/Host/{host.id}",
            {"attachment": file, "namespace": self.namespace.id},
            format="multipart",
        )

        new_file = self._create_test_file(b"a new test file")
        # Test that we can't upload more than one attachment.
        self.assert_post_and_400(
            f"/attachments/data/Host/{host.id}",
            {"attachment": new_file, "namespace": self.namespace.id},
            format="multipart",
        )

        self.assert_patch("/attachments/manager/Host", {"per_object_count_limit": 5})

        new_file = self._create_test_file(b"a new test file")
        self.assert_post_and_201(
            f"/attachments/data/Host/{host.id}",
            {"attachment": new_file, "namespace": self.namespace.id},
            format="multipart",
        )

        # Test that we can't upload an attachment that is too large.
        # > 20 bytes
        file = self._create_test_file(b"this is a test file that is too large")
        self.assert_post_and_400(
            f"/attachments/data/Host/{host.id}",
            {"attachment": file, "namespace": self.namespace.id},
            format="multipart",
        )

        # Test that we can't upload an attachment that would make the total size
        # exceed the limit. 12+16=28 bytes, limit is 30 bytes.
        file = self._create_test_file(b"no space")
        self.assert_post_and_400(
            f"/attachments/data/Host/{host.id}",
            {"attachment": file, "namespace": self.namespace.id},
            format="multipart",
        )

    def test_attachment_data_upload(self):
        """Test uploading of an attachment."""
        self._enable_attachments_for_hosts()
        file = self._create_test_file()
        host = self.hosts[0]

        res = self.assert_post_and_201(
            f"/attachments/data/Host/{host.id}",
            {"attachment": file, "namespace": self.namespace.id},
            format="multipart",
        )

        file_hash = hashlib.sha256(self.file_content).hexdigest()

        file_meta = self.assert_get(
            f"/attachments/data/Host/{host.id}/{res.data['id']}"
        )

        self.assertEqual(file_meta.data["original_filename"], "test_file.txt")
        self.assertEqual(file_meta.data["size"], len(self.file_content))
        self.assertEqual(file_meta.data["sha256"], file_hash)

        fileres = self.assert_get(
            f"/attachments/data/Host/{host.id}/{res.data['id']}/download"
        )

        self.assertEqual(fileres.content, self.file_content)

    def test_attachment_data_permissions(self):
        """Test that permissions are enforced."""
        self._enable_attachments_for_hosts()
        file = self._create_test_file()
        host = self.hosts[0]

        att = self.assert_post_and_201(
            f"/attachments/data/Host/{host.id}",
            {"attachment": file, "namespace": self.namespace.id},
            format="multipart",
        )

        self.assert_get(f"/attachments/data/Host/{host.id}/{att.data['id']}")
        self.assert_get(f"/attachments/data/Host/{host.id}/{att.data['id']}/download")

        self.client = self.get_user_client()
        self.assert_get_and_403(
            f"/attachments/data/Host/{host.id}/{att.data['id']}",
        )
        self.assert_delete_and_403(
            f"/attachments/data/Host/{host.id}/{att.data['id']}/download",
        )

        new_host = self.hosts[1]
        self.assert_get_and_404(
            f"/attachments/data/Host/{new_host.id}/{att.data['id']}"
        )

    def test_attachment_filtering(self):
        """Test that filtering works."""
        for cls in ["Host", "Room", "Building"]:
            self._enable_attachments(cls)

        host_one = self.hosts[0]

        room_one = self.rooms[0]
        room_two = self.rooms[1]

        self._add_attachment("Host", host_one, b"host_one")
        self._add_attachment("Room", room_one, b"room_one")
        self._add_attachment("Room", room_two, b"room_two_1")
        ptt = self._add_attachment("Room", room_two, b"room_two_2")
        sha256 = ptt.data["sha256"]

        self.assert_get_elements("/attachments/data/", 4)
        self.assert_get_elements(f"/attachments/data/?sha256={sha256}", 1)
        self.assert_get_elements(
            f"/attachments/data/?sha256__endswith={sha256[-8:]}", 1
        )
        self.assert_get_elements("/attachments/data/?sha256__contains=ee", 2)

        host_class_id = self.get_class_from_cache("Host").id
        room_class_id = self.get_class_from_cache("Room").id
        room_class_name = self.get_class_from_cache("Room").name

        self.assert_get_elements(f"/attachments/data/?hubuum_class={host_class_id}", 1)
        self.assert_get_elements(f"/attachments/data/?hubuum_class={room_class_id}", 3)
        self.assert_get_elements(
            f"/attachments/data/?hubuum_class__name={room_class_name}", 3
        )

        # No such class, no attachments
        self.assert_get_elements("/attachments/data/?hubuum_class=9999", 0)

        # Fielderror
        self.assert_get_and_400("/attachments/data/?hubuum_classs=Room")

        self.assert_get_elements("/attachments/data/Host/", 1)
        self.assert_get_elements("/attachments/data/Room/", 3)
        self.assert_get_elements(f"/attachments/data/Room/{room_two.id}/", 2)
        self.assert_get_elements(
            f"/attachments/data/Room/{room_two.id}/?sha256__endswith=ffffff", 0
        )
        self.assert_get_elements(
            f"/attachments/data/Room/{room_two.id}/?sha256__endswith={sha256[-8:]}",
            1,
        )

        # Forgetting the query string separator (?).
        self.assert_get_and_404("/attachments/data/Room/name=room_two")

        # Filtering by owner objects
        url = "/attachments/data/Room/?hubuum_object"
        self.assert_get_elements(f"{url}={room_one.id}", 1)
        self.assert_get_elements(f"{url}={room_two.id}", 2)
        self.assert_get_elements(
            f"/attachments/data/Room/?hubuum_object={room_two.id}", 2
        )

        name_url = "/attachments/data/Room/?hubuum_object__name"

        self.assert_get_elements(f"{name_url}={room_two.name}", 2)

        self.assert_get_elements(f"{name_url}={room_two.name}&sha256={sha256}", 1)

        self.assert_get_elements(f"{name_url}={room_two.name}&sha256__contains=e", 2)
        self.assert_get_elements(f"{name_url}={room_two.name}&sha256__endswith=ffff", 0)
        self.assert_get_elements(
            f"{name_url}={room_two.name}&sha256__endswith={sha256[-8:]}", 1
        )

        # Broken query string
        self.assert_get_and_400("/attachments/data/Room/?uname=room_two")
        self.assert_get_and_400("/attachments/data/Room/?id=foo")

    def test_attachment_data_duplicate(self):
        """Test uploading of an attachment."""
        self._enable_attachments_for_hosts()
        file = self._create_test_file()
        host = self.hosts[0]

        self.assert_post_and_201(
            f"/attachments/data/Host/{host.id}",
            {"attachment": file, "namespace": self.namespace.id},
            format="multipart",
        )

        file = self._create_test_file()
        self.assert_post_and_409(
            f"/attachments/data/Host/{host.id}",
            {"attachment": file, "namespace": self.namespace.id},
            format="multipart",
        )

    def test_attachment_failures(self):
        """Test various attachment failures."""
        # No such model
        self.assert_get_and_404("/attachments/data/nope/1")
        self.assert_post_and_404("/attachments/data/nope/1", {})

        # Filter on model that does not support attachments
        #        self.assert_get_and_400("/attachments/data/?class=1")

        # Filter on non-existent model
        #        self.assert_get_and_404("/attachments/data/?class=99")

        host = self.hosts[0]
        file = self._create_test_file()
        # Model exists, but does not have attachments enabled
        self.assert_post_and_400(
            f"/attachments/data/Host/{host.id}",
            {"attachment": file, "namespace": self.namespace.id},
            format="multipart",
        )

        self.assert_get_and_404("/attachments/data/namespace/1")
        self.assert_post_and_404(
            f"/attachments/data/namespace/{self.namespace.id}",
            {"attachment": file, "namespace": self.namespace.id},
            format="multipart",
        )

        # Model exists, has attachments enabled, but the attachment does not exist
        self._enable_attachments_for_hosts()
        self.assert_get_and_404("/attachments/data/Host/1")
        self.assert_get_and_404("/attachments/data/Host/wrongtypehere")

        # Uploading without setting format=multipart
        # Note: doing this without host supporting attachments will give a 400.
        self.assert_post_and_415(
            f"/attachments/data/Host/{host.id}",
            {"attachment": "notafile", "namespace": self.namespace.id},
        )

        # No such host
        self.assert_post_and_404("/attachments/data/Host/99", {})

        # Disable attachments for host, and try again
        host = self.hosts[0]
        self.assert_patch("/attachments/manager/Host", {"enabled": False})
        self.assert_post_and_400(
            f"/attachments/data/Host/{host.id}", format="multipart"
        )

    def test_attachment_delete(self):
        """Test manually deleting an attachment."""
        self._enable_attachments_for_hosts()
        file = self._create_test_file()
        host = self.hosts[0]

        att = self.assert_post_and_201(
            f"/attachments/data/Host/{host.id}",
            {"attachment": file, "namespace": self.namespace.id},
            format="multipart",
        )

        self.assert_get(f"/attachments/data/Host/{host.id}/{att.data['id']}")
        self.assert_get(f"/attachments/data/Host/{host.id}/{att.data['id']}/download")

        self.assert_delete(f"/attachments/data/Host/{host.id}/{att.data['id']}")
        self.assert_get_and_404(f"/attachments/data/Host/{host.id}/{att.data['id']}")
        self.assert_get_and_404(
            f"/attachments/data/Host/{host.id}/{att.data['id']}/download"
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
                        "class": "mymodel",
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
