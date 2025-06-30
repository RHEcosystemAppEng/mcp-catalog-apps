from importer.defaults import (
    MCP_CATALOG_PLURALS,
    MCP_CERTIFIED_SERVER_KIND,
    MCP_CERTIFIED_SERVER_PLURALS,
    MCP_GROUP,
    MCP_REGISTRY_PLURALS,
    MCP_SERVER_KIND,
    MCP_SERVER_PLURALS,
    MCP_SERVERRUN_KIND,
    MCP_SERVERRUN_PLURALS,
    MCP_VERSION,
    NODE_BASE_IMAGE,
    PYTHON_BASE_IMAGE,
)


class TestMcpConstants:
    """Test cases for MCP constants."""

    def test_mcp_group_and_version(self):
        """Test MCP group and version constants."""
        assert MCP_GROUP == "mcp.opendatahub.io"
        assert MCP_VERSION == "v1alpha1"

    def test_mcp_catalog_constants(self):
        """Test MCP catalog related constants."""
        assert MCP_CATALOG_PLURALS == "mcpcatalogs"

    def test_mcp_server_constants(self):
        """Test MCP server related constants."""
        assert MCP_SERVER_KIND == "McpServer"
        assert MCP_SERVER_PLURALS == "mcpservers"

    def test_mcp_certified_server_constants(self):
        """Test MCP certified server related constants."""
        assert MCP_CERTIFIED_SERVER_KIND == "McpCertifiedServer"
        assert MCP_CERTIFIED_SERVER_PLURALS == "mcpcertifiedservers"

    def test_mcp_registry_constants(self):
        """Test MCP registry related constants."""
        assert MCP_REGISTRY_PLURALS == "mcpserverpools"

    def test_mcp_serverrun_constants(self):
        """Test MCP server run related constants."""
        assert MCP_SERVERRUN_KIND == "McpServerRun"
        assert MCP_SERVERRUN_PLURALS == "mcpserverruns"

    def test_base_image_constants(self):
        """Test base image constants."""
        assert PYTHON_BASE_IMAGE == "registry.redhat.io/ubi9/python-311:latest"
        assert NODE_BASE_IMAGE == "registry.redhat.io/ubi9/nodejs-22:latest"

    def test_all_constants_are_strings(self):
        """Test that all constants are strings."""
        constants = [
            MCP_GROUP,
            MCP_VERSION,
            MCP_CATALOG_PLURALS,
            MCP_SERVER_KIND,
            MCP_SERVER_PLURALS,
            MCP_CERTIFIED_SERVER_KIND,
            MCP_CERTIFIED_SERVER_PLURALS,
            MCP_REGISTRY_PLURALS,
            MCP_SERVERRUN_KIND,
            MCP_SERVERRUN_PLURALS,
            PYTHON_BASE_IMAGE,
            NODE_BASE_IMAGE,
        ]

        for constant in constants:
            assert isinstance(constant, str), f"Constant {constant} is not a string"
            assert len(constant) > 0, f"Constant {constant} is empty"

    def test_mcp_group_format(self):
        """Test that MCP group follows Kubernetes API group format."""
        # Should be a valid domain name format
        assert "." in MCP_GROUP
        assert MCP_GROUP.count(".") >= 1
        assert not MCP_GROUP.startswith(".")
        assert not MCP_GROUP.endswith(".")

    def test_mcp_version_format(self):
        """Test that MCP version follows Kubernetes API version format."""
        # Should start with 'v' followed by version
        assert MCP_VERSION.startswith("v")
        assert len(MCP_VERSION) > 1
