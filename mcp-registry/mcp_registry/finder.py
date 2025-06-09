from kubernetes import client
from mcp_registry.defaults import (
    MCP_BLUEPRINT_PLURALS,
    MCP_GROUP,
    MCP_SERVER_DEFINITION_KIND,
    MCP_SERVER_DEFINITION_PLURALS,
    MCP_SERVER_PLURALS,
    MCP_VERSION,
)
from mcp_registry.utils import (
    get_current_namespace,
    logger,
    match_catalog,
    match_registry,
)


class Finder:
    """
    Finder class to interact with the MCP catalog and retrieve server definitions and blueprints.
    """

    def __init__(self, crd_api, catalog_name: str, registry_name: str):
        self.crd_api = crd_api
        self.catalog_name = catalog_name
        self.registry_name = registry_name
        self.namespace = get_current_namespace()

    def find_server_defs(self) -> list:
        """
        Find server definitions in the MCP catalog.

        Returns a list of server definitions with their metadata and specifications.
        """
        resources = self.crd_api.list_namespaced_custom_object(
            group=MCP_GROUP,
            version=MCP_VERSION,
            namespace=self.namespace,
            plural=MCP_SERVER_DEFINITION_PLURALS,
        )
        return [
            {
                "name": item["metadata"]["name"],
                "namespace": item["metadata"]["namespace"],
                "server-name": item["spec"].get("server_detail", {}).get("name", ""),
                "description": item["spec"]
                .get("server_detail", {})
                .get("description", ""),
                "repository": item["spec"]
                .get("server_detail", {})
                .get("repository", {})
                .get("url", ""),
            }
            for item in resources.get("items", [])
            # TODO: Match registry using annotations
        ]

    def find_blueprints(self) -> list:
        """
        Find blueprints in the MCP catalog.
        Returns a list of blueprints with their metadata and specifications.
        """
        resources = self.crd_api.list_namespaced_custom_object(
            group=MCP_GROUP,
            version=MCP_VERSION,
            namespace=self.namespace,
            plural=MCP_BLUEPRINT_PLURALS,
        )
        return [
            {
                "name": item["metadata"]["name"],
                "namespace": item["metadata"]["namespace"],
                "description": item["spec"]["description"],
                "catalog": item["spec"].get("catalog-ref"),
                "provider": item["spec"].get("provider", ""),
                "license": item["spec"].get("license", ""),
                "competencies": item["spec"].get("competencies", []),
                "image": item["spec"].get("mcp-server", {}).get("image", ""),
            }
            for item in resources.get("items", [])
            if match_catalog(
                self.catalog_name,
                item["metadata"]["namespace"],
                item["spec"].get("catalog-ref", {}),
            )
        ]

    def find_servers(self) -> list:
        resources = self.crd_api.list_namespaced_custom_object(
            group=MCP_GROUP,
            version=MCP_VERSION,
            namespace=self.namespace,
            plural=MCP_SERVER_PLURALS,
        )
        return [
            {
                "name": item["metadata"]["name"],
                "namespace": item["metadata"]["namespace"],
                "registry": item["spec"].get("registry-ref"),
                "server-mode": item["spec"].get("server-mode"),
                "blueprint": item["spec"]
                .get("mcp-server")
                .get("blueprint-ref", {"name": None})
                .get("name"),
            }
            for item in resources.get("items", [])
            if match_registry(
                self.registry_name,
                item["metadata"]["namespace"],
                item["spec"].get("registry-ref", {}),
            )
        ]

    def find_server_def(self, server_definition_name: str):
        try:
            return self.crd_api.get_namespaced_custom_object(
                group=MCP_GROUP,
                version=MCP_VERSION,
                name=server_definition_name,
                namespace=self.namespace,
                plural=MCP_SERVER_DEFINITION_PLURALS,
            )
        except client.ApiException as e:
            if e.status == 404:
                logger.warning(
                    f"{MCP_SERVER_DEFINITION_KIND} '{server_definition_name}' not found."
                )
                return None
            else:
                logger.error(
                    f"Error fetching {MCP_SERVER_DEFINITION_KIND} '{server_definition_name}': {e}"
                )
                return None
