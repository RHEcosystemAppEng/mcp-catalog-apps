import requests

from kubernetes import client
from mcp_registry.defaults import (
    MCP_GROUP,
    MCP_SERVER_DEFINITION_KIND,
    MCP_SERVER_DEFINITION_PLURALS,
    MCP_VERSION,
)
from mcp_registry.utils import get_current_namespace, logger, sanitize_k8s_name


class Importer:
    def __init__(self, crd_api, registry_name: str, mcp_registry_source: str):
        self.crd_api = crd_api
        self.registry_name = registry_name
        self.mcp_registry_source = mcp_registry_source
        self.cursor = None
        self.has_next = True
        logger.info(f"Attempting to fetch server data from: {self.mcp_registry_source}")

    def import_next(self):
        try:
            response = requests.get(
                f"{self.mcp_registry_source}/servers?limit=100{f'&cursor={self.cursor}' if self.cursor else ''}"
            )
            response.raise_for_status()
            server_data = response.json()
            logger.info("Successfully fetched server data.")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching data from {self.mcp_registry_source}: {e}")
            self.has_next = False
            self.cursor = None
            return

        if "servers" not in server_data or not isinstance(server_data["servers"], list):
            logger.error("JSON response does not contain a 'servers' list.")
            self.has_next = False
            self.cursor = None
            return

        self.cursor = server_data.get("metadata", {}).get("next_cursor", None)
        self.has_next = bool(self.cursor)
        logger.info(f"Next cursor: {self.cursor}, has_next: {self.has_next}")

        for server_entry in server_data["servers"]:
            self._import_server_entry(server_entry)
        logger.info("Finished processing all server entries.")

    def _import_server_entry(self, server_entry):
        id = server_entry.get("id")
        server_def_name = server_entry.get("name")
        server_def_name = sanitize_k8s_name(server_def_name)
        if not server_def_name:
            logger.warning(
                f"Server entry missing 'name' field, skipping: {server_entry}"
            )
            return

        try:
            response = requests.get(f"{self.mcp_registry_source}/servers/{id}")
            response.raise_for_status()
            server_data = response.json()
        except requests.exceptions.RequestException as e:
            logger.error(
                f"Error fetching data from {self.mcp_registry_source}/servers/{id}: {e}"
            )
            return

        logger.info(f"Processing server: {server_def_name} (ID: {id})")

        mcp_server_definition = {
            "apiVersion": f"{MCP_GROUP}/{MCP_VERSION}",
            "kind": MCP_SERVER_DEFINITION_KIND,
            "metadata": {
                "name": server_def_name,
                "annotations": {
                    "mcp.opendatahub.io/mcpregistry": self.registry_name,
                },
                "labels": {
                    "app.kubernetes.io/name": "mcp-registry-operator",
                    "app.kubernetes.io/managed-by": self.registry_name,
                    "mcp.opendatahub.io/server-id": server_entry.get("id"),
                },
            },
            "spec": {"server_detail": server_data},
        }

        # print(yaml.dump(mcp_server_definition, sort_keys=False))

        try:
            namespace = get_current_namespace()
            try:
                existing_resource = self.crd_api.get_namespaced_custom_object(
                    group=MCP_GROUP,
                    version=MCP_VERSION,
                    name=server_def_name,
                    namespace=namespace,
                    plural=MCP_SERVER_DEFINITION_PLURALS,
                )
                if existing_resource:
                    logger.info(
                        f"{MCP_SERVER_DEFINITION_KIND} '{server_def_name}' already exists in {namespace}. Skipping creation."
                    )
                    return
            except client.ApiException as e:
                if e.status == 404:
                    pass
                else:
                    raise

            self.crd_api.create_namespaced_custom_object(
                group=MCP_GROUP,
                version=MCP_VERSION,
                namespace=namespace,
                plural=MCP_SERVER_DEFINITION_PLURALS,
                body=mcp_server_definition,
            )
            logger.info(f"Successfully created McpServerDefinition: {server_def_name}")
        except client.ApiException as e:
            logger.error(f"Error creating McpServerDefinition '{server_def_name}': {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred for '{server_def_name}': {e}")
