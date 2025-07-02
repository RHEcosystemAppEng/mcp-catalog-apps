from kubernetes import client
from mcp_registry.command_def import CommandDef
from mcp_registry.defaults import (
    MCP_CERTIFIED_SERVER_KIND,
    MCP_GROUP,
    MCP_SERVER_PLURALS,
    MCP_VERSION,
)
from mcp_registry.image_builder import ImageBuilder
from mcp_registry.utils import get_current_namespace, logger


class Promoter:
    def __init__(self, crd_api, catalog_name: str, server_definition: dict):
        self.crd_api = crd_api
        self.catalog_name = catalog_name
        self.server_definition = server_definition
        self.server_definition_name = server_definition.get("metadata", {}).get("name")
        self.image_builder = ImageBuilder(
            crd_api=crd_api, server_definition=server_definition
        )

    def promote(self):
        """
        Promote the given MCP server definition to an McpServer instance
        """
        command_def, image_name = self.image_builder.build_server_image()
        logger.info(
            f"Server image '{image_name}' built successfully for {self.server_definition_name}."
        )
        if not image_name:
            logger.error("Failed to build server image. Promotion aborted.")
            return

        return self._build_mcp_server(command_def=command_def, image_name=image_name)

    def _build_mcp_server(self, command_def: CommandDef, image_name: str):
        server_name = f"{self.server_definition_name}-"
        namespace = get_current_namespace()
        description = (
            self.server_definition.get("spec", {})
            .get("server_detail", {})
            .get("description", "")
        )
        # TODO
        provider = (
            self.server_definition.get("spec", {})
            .get("repository", {})
            .get("url", "NA")
        )
        # TODO
        license = (
            self.server_definition.get("spec", {})
            .get("server_detail", {})
            .get("license", "NA")
        )
        # TODO: use LLM to extract
        competencies = []
        # TODO
        proxy = False

        mcp_server = {
            "apiVersion": f"{MCP_GROUP}/{MCP_VERSION}",
            "kind": MCP_CERTIFIED_SERVER_KIND,
            "metadata": {
                "generateName": server_name,
                "annotations": {
                    "mcp.opendatahub.io/mcpcatalog": self.catalog_name,
                },
                "labels": {
                    "app.kubernetes.io/name": "mcp-registry-operator",
                    "app.kubernetes.io/managed-by": self.catalog_name,
                },
            },
            "spec": {
                "description": description,
                "provider": provider,
                "license": license,
                "competencies": competencies,
                "mcp-server": {
                    "proxy": proxy,
                    "image": image_name,
                    "command": command_def.command,
                    "args": [arg for arg in command_def.args],
                    "env-vars": [f"{k}={v}" for k, v in command_def.env_vars.items()],
                },
            },
        }

        try:
            try:
                existing_resource = self.crd_api.get_namespaced_custom_object(
                    group=MCP_GROUP,
                    version=MCP_VERSION,
                    name=server_name,
                    namespace=namespace,
                    plural=MCP_SERVER_PLURALS,
                )
                if existing_resource:
                    logger.info(
                        f"{MCP_CERTIFIED_SERVER_KIND} '{server_name}' already exists in {namespace}. Skipping creation."
                    )
                    # TODO: should be updated instead
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
                plural=MCP_SERVER_PLURALS,
                body=mcp_server,
            )
            logger.info(
                f"Successfully created {MCP_CERTIFIED_SERVER_KIND} '{server_name}'"
            )
        except client.ApiException as e:
            logger.exception(
                f"Error creating {MCP_CERTIFIED_SERVER_KIND} '{server_name}': {e}"
            )
        except Exception as e:
            logger.exception(
                f"An unexpected error occurred for {MCP_CERTIFIED_SERVER_KIND} '{server_name}': {e}"
            )
