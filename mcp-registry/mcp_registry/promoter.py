from kubernetes import client
from mcp_registry.command_def import CommandDef
from mcp_registry.defaults import (
    MCP_BLUEPRINT_PLURALS,
    MCP_GROUP,
    MCP_SERVER_KIND,
    MCP_VERSION,
)
from mcp_registry.image_builder import ImageBuilder
from mcp_registry.utils import get_current_namespace, logger


class Promoter:
    def __init__(self, crd_api, registry_name: str, server_definition: dict):
        self.crd_api = crd_api
        self.registry_name = registry_name
        self.server_definition = server_definition
        self.server_definition_name = server_definition.get("metadata", {}).get("name")
        self.image_builder = ImageBuilder(
            crd_api=crd_api, server_definition=server_definition
        )

    def promote(self):
        """
        Promote the given MCP server definition to an McbBlueprint instance
        """
        command_def, image_name = self.image_builder.build_server_image()
        logger.info(
            f"Server image '{image_name}' built successfully for {self.server_definition_name}."
        )
        if not image_name:
            logger.error("Failed to build server image. Promotion aborted.")
            return

        return self._build_mcp_blueprint(command_def=command_def, image_name=image_name)

    def _build_mcp_blueprint(self, command_def: CommandDef, image_name: str):
        blueprint_name = f"{self.server_definition_name}-"
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

        mcp_blueprint = {
            "apiVersion": f"{MCP_GROUP}/{MCP_VERSION}",
            "kind": MCP_SERVER_KIND,
            "metadata": {
                "generateName": blueprint_name,
                "annotations": {
                    "mcp.opendatahub.io/mcpregistry": self.registry_name,
                },
                "labels": {
                    "app.kubernetes.io/name": "mcp-registry-operator",
                    "app.kubernetes.io/managed-by": self.registry_name,
                },
            },
            "spec": {
                "registryRef": {
                    "name": self.registry_name,
                    "namespace": namespace,
                },
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
                    name=blueprint_name,
                    namespace=namespace,
                    plural=MCP_BLUEPRINT_PLURALS,
                )
                if existing_resource:
                    logger.info(
                        f"{MCP_SERVER_KIND} '{blueprint_name}' already exists in {namespace}. Skipping creation."
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
                plural=MCP_BLUEPRINT_PLURALS,
                body=mcp_blueprint,
            )
            logger.info(f"Successfully created {MCP_SERVER_KIND} '{blueprint_name}'")
        except client.ApiException as e:
            logger.exception(
                f"Error creating {MCP_SERVER_KIND} '{blueprint_name}': {e}"
            )
        except Exception as e:
            logger.exception(
                f"An unexpected error occurred for {MCP_SERVER_KIND} '{blueprint_name}': {e}"
            )
