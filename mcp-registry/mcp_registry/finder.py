from kubernetes import client
from mcp_registry.defaults import (
    MCP_GROUP,
    MCP_SERVER_DEFINITION_KIND,
    MCP_SERVER_DEFINITION_PLURALS,
    MCP_SERVER_PLURALS,
    MCP_SERVERRUN_PLURALS,
    MCP_VERSION,
)
from mcp_registry.utils import (
    get_current_namespace,
    logger,
    match_registry,
    match_serverpool,
)


class Finder:
    """
    Finder class to interact with the MCP registry and retrieve servers and running servers.
    """

    def __init__(self, crd_api, registry_name: str, serverpool_name: str):
        self.crd_api = crd_api
        self.registry_name = registry_name
        self.serverpool_name = serverpool_name
        self.namespace = get_current_namespace()

    def find_server_defs(self) -> list:
        """
        Find server definitions in the MCP registry.

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

    def find_servers(self) -> list:
        """
        Find servers in the MCP registry.
        Returns a list of servers with their metadata and specifications.
        """
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
                "description": item["spec"]["description"],
                "registry": item["spec"].get("registryRef"),
                "provider": item["spec"].get("provider", ""),
                "license": item["spec"].get("license", ""),
                "competencies": item["spec"].get("competencies", []),
                "image": item["spec"].get("mcpServer", {}).get("image", ""),
            }
            for item in resources.get("items", [])
            if match_registry(
                self.registry_name,
                item["metadata"]["namespace"],
                item["spec"].get("registryRef", {}),
            )
        ]

    def find_server_runs(self) -> list:
        resources = self.crd_api.list_namespaced_custom_object(
            group=MCP_GROUP,
            version=MCP_VERSION,
            namespace=self.namespace,
            plural=MCP_SERVERRUN_PLURALS,
        )
        return [
            {
                "name": item["metadata"]["name"],
                "namespace": item["metadata"]["namespace"],
                "server-pool": item["spec"].get("serverPoolRef"),
                "server-mode": item["spec"].get("server-mode"),
                "server": item["spec"]
                .get("mcpServer")
                .get("mcpServerRef", {"name": None})
                .get("name"),
            }
            for item in resources.get("items", [])
            if match_serverpool(
                self.registry_name,
                item["metadata"]["namespace"],
                item["spec"].get("serverPoolRef", {}),
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
