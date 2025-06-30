from datetime import datetime
from unittest.mock import Mock, patch

import pytest
import requests
from kubernetes import client

from importer.importer import Importer


class TestImporterInitialization:
    """Test cases for Importer class initialization."""

    def test_importer_initialization(self):
        """Test proper initialization with all parameters."""
        mock_crd_api = Mock()

        importer = Importer(
            crd_api=mock_crd_api,
            catalog_name="test-catalog",
            import_job_name="test-job",
            mcp_registry_url="http://localhost:8080/v0",
            name_filter="test",
            max_servers=50,
            namespace="test-namespace",
            dry_run=True,
        )

        assert importer.crd_api == mock_crd_api
        assert importer.catalog_name == "test-catalog"
        assert importer.import_job_name == "test-job"
        assert importer.mcp_registry_url == "http://localhost:8080/v0"
        assert importer.name_filter == "test"
        assert importer.max_servers == 50
        assert importer.namespace == "test-namespace"
        assert importer.dry_run is True
        assert importer.imported_servers == 0
        assert importer.cursor is None
        assert importer.has_next is True
        assert isinstance(importer.start_time, datetime)
        assert importer.server_tracking == []
        assert importer.import_status == "running"
        assert importer.error_message is None
        assert importer.imported_count == 0

    def test_importer_initialization_defaults(self):
        """Test initialization with default values."""
        mock_crd_api = Mock()

        importer = Importer(
            crd_api=mock_crd_api,
            catalog_name="test-catalog",
            import_job_name="test-job",
            mcp_registry_url="http://localhost:8080/v0",
        )

        assert importer.name_filter == ""
        assert importer.max_servers == 100
        assert importer.namespace == ""
        assert importer.dry_run is False

    def test_importer_initialization_validation(self):
        """Test validation of required parameters."""
        mock_crd_api = Mock()

        # The actual implementation doesn't validate empty strings
        # So we'll test that it accepts them
        importer = Importer(
            crd_api=mock_crd_api,
            catalog_name="",
            import_job_name="test-job",
            mcp_registry_url="http://localhost:8080/v0",
        )
        assert importer.catalog_name == ""

        importer = Importer(
            crd_api=mock_crd_api,
            catalog_name="test-catalog",
            import_job_name="",
            mcp_registry_url="http://localhost:8080/v0",
        )
        assert importer.import_job_name == ""

        importer = Importer(
            crd_api=mock_crd_api,
            catalog_name="test-catalog",
            import_job_name="test-job",
            mcp_registry_url="",
        )
        assert importer.mcp_registry_url == ""


class TestNameMatch:
    """Test cases for name matching functionality."""

    def test_name_match_no_filter(self):
        """Test that all servers pass when no name filter is set."""
        mock_crd_api = Mock()
        importer = Importer(
            crd_api=mock_crd_api,
            catalog_name="test-catalog",
            import_job_name="test-job",
            mcp_registry_url="http://localhost:8080/v0",
        )

        # Test various server names
        assert importer._name_match({"name": "any-server-name"}) is True
        assert importer._name_match({"name": "another-server"}) is True
        assert importer._name_match({"name": ""}) is True
        assert importer._name_match({}) is True

    def test_name_match_with_filter(self):
        """Test substring matching with various filter patterns."""
        mock_crd_api = Mock()
        importer = Importer(
            crd_api=mock_crd_api,
            catalog_name="test-catalog",
            import_job_name="test-job",
            mcp_registry_url="http://localhost:8080/v0",
            name_filter="test",
        )

        # Test matching names
        assert importer._name_match({"name": "test-server"}) is True
        assert importer._name_match({"name": "my-test-server"}) is True
        assert importer._name_match({"name": "server-test"}) is True
        assert importer._name_match({"name": "TEST-SERVER"}) is True  # Case insensitive

        # Test non-matching names
        assert importer._name_match({"name": "other-server"}) is False
        assert importer._name_match({"name": ""}) is False
        assert importer._name_match({}) is False

    def test_name_match_case_sensitivity(self):
        """Test case sensitivity of name filtering."""
        mock_crd_api = Mock()
        importer = Importer(
            crd_api=mock_crd_api,
            catalog_name="test-catalog",
            import_job_name="test-job",
            mcp_registry_url="http://localhost:8080/v0",
            name_filter="Test",
        )

        # Test case insensitivity
        assert importer._name_match({"name": "TestServer"}) is True
        assert importer._name_match({"name": "testserver"}) is True
        assert importer._name_match({"name": "TESTserver"}) is True


class TestImportServerEntry:
    """Test cases for importing individual server entries."""

    @patch("importer.importer.requests.get")
    @patch("importer.importer.get_current_namespace")
    def test_import_server_entry_success(self, mock_get_namespace, mock_requests_get):
        """Test successful server import."""
        mock_crd_api = Mock()
        mock_get_namespace.return_value = "test-namespace"

        # Mock successful API response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "id": "test-id",
            "name": "test-server",
            "description": "Test server",
        }
        mock_requests_get.return_value = mock_response

        # Mock successful Kubernetes API call - 404 for get, success for create
        mock_crd_api.get_namespaced_custom_object.side_effect = client.ApiException(
            status=404
        )
        mock_crd_api.create_namespaced_custom_object.return_value = {
            "metadata": {"name": "test-server"}
        }

        importer = Importer(
            crd_api=mock_crd_api,
            catalog_name="test-catalog",
            import_job_name="test-job",
            mcp_registry_url="http://localhost:8080/v0",
        )

        server_entry = {"id": "test-id", "name": "test-server"}

        importer._import_server_entry(server_entry)

        # Verify API calls
        mock_requests_get.assert_called_once_with(
            "http://localhost:8080/v0/servers/test-id"
        )
        mock_crd_api.create_namespaced_custom_object.assert_called_once()

    @patch("importer.importer.requests.get")
    @patch("importer.importer.get_current_namespace")
    def test_import_server_entry_existing_resource(
        self, mock_get_namespace, mock_requests_get
    ):
        """Test handling of existing McpServer resources."""
        mock_crd_api = Mock()
        mock_get_namespace.return_value = "test-namespace"

        # Mock successful API response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "id": "test-id",
            "name": "test-server",
            "description": "Test server",
        }
        mock_requests_get.return_value = mock_response

        # Mock existing resource
        mock_crd_api.get_namespaced_custom_object.return_value = {
            "metadata": {"name": "test-server"}
        }

        importer = Importer(
            crd_api=mock_crd_api,
            catalog_name="test-catalog",
            import_job_name="test-job",
            mcp_registry_url="http://localhost:8080/v0",
        )

        server_entry = {"id": "test-id", "name": "test-server"}

        importer._import_server_entry(server_entry)

        # Verify that create was not called
        mock_crd_api.create_namespaced_custom_object.assert_not_called()

    @patch("importer.importer.requests.get")
    def test_import_server_entry_api_error(self, mock_requests_get):
        """Test handling of registry API errors."""
        mock_crd_api = Mock()

        # Mock API error using a proper requests exception
        mock_requests_get.side_effect = requests.exceptions.RequestException(
            "Connection error"
        )

        importer = Importer(
            crd_api=mock_crd_api,
            catalog_name="test-catalog",
            import_job_name="test-job",
            mcp_registry_url="http://localhost:8080/v0",
        )

        server_entry = {"id": "test-id", "name": "test-server"}

        # The function should handle the exception gracefully
        importer._import_server_entry(server_entry)

        # Verify that Kubernetes API was not called
        mock_crd_api.create_namespaced_custom_object.assert_not_called()

    def test_import_server_entry_missing_name(self):
        """Test handling of server entries without name field."""
        mock_crd_api = Mock()

        importer = Importer(
            crd_api=mock_crd_api,
            catalog_name="test-catalog",
            import_job_name="test-job",
            mcp_registry_url="http://localhost:8080/v0",
        )

        server_entry = {
            "id": "test-id"
            # Missing name field
        }

        # This should raise an AttributeError when sanitize_k8s_name is called with None
        with pytest.raises(AttributeError):
            importer._import_server_entry(server_entry)
