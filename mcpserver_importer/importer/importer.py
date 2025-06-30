import logging
import os
import sys
import uuid
from datetime import datetime

import requests
import yaml
from kubernetes import client

from importer.defaults import (
    MCP_GROUP,
    MCP_SERVER_KIND,
    MCP_SERVER_PLURALS,
    MCP_VERSION,
)
from importer.utils import get_current_namespace, get_k8s_client, sanitize_k8s_name

logger = logging.getLogger("importer")


class Importer:
    def __init__(
        self,
        crd_api,
        catalog_name: str,
        import_job_name: str,
        mcp_registry_url: str,
        name_filter: str = "",
        max_servers: int = 100,
        namespace: str = "",
        dry_run: bool = False,
    ):
        self.crd_api = crd_api
        self.catalog_name = catalog_name
        self.import_job_name = import_job_name
        self.mcp_registry_url = mcp_registry_url
        self.name_filter = name_filter
        self.max_servers = max_servers
        self.imported_servers = 0
        self.cursor = None
        self.has_next = True
        self.namespace = namespace
        self.dry_run = dry_run

        # Tracking for ConfigMap generation
        self.start_time = datetime.now()
        self.server_tracking = []
        self.import_status = "running"
        self.error_message: str | None = None
        self.imported_count = 0

        logger.info("=" * 80)
        logger.info("🚀 MCP SERVER IMPORTER INITIALIZATION")
        logger.info("=" * 80)
        logger.info(f"📡 Registry URL: {self.mcp_registry_url}")
        logger.info(f"📚 Catalog Name: {self.catalog_name}")
        logger.info(f"🏷️  Import Job: {self.import_job_name}")
        logger.info(f"🔍 Name Filter: {self.name_filter or 'None'}")
        logger.info(f"📊 Max Servers: {self.max_servers}")
        logger.info(f"🏠 Namespace: {self.namespace}")
        logger.info(f"🔍 Dry Run: {self.dry_run}")
        logger.info("=" * 80)

    def import_next(self):
        try:
            response = requests.get(
                f"{self.mcp_registry_url}/servers?limit=100{f'&cursor={self.cursor}' if self.cursor else ''}"
            )
            response.raise_for_status()
            server_data = response.json()
            logger.info("Successfully fetched server data.")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching data from {self.mcp_registry_url}: {e}")
            self.has_next = False
            self.cursor = None
            self.import_status = "failed"
            self.error_message = f"Registry connection error: {str(e)}"
            return

        if "servers" not in server_data or not isinstance(server_data["servers"], list):
            logger.error("JSON response does not contain a 'servers' list.")
            self.has_next = False
            self.cursor = None
            self.import_status = "failed"
            self.error_message = (
                "Invalid registry response format: missing 'servers' list"
            )
            return

        self.cursor = server_data.get("metadata", {}).get("next_cursor", None)
        self.has_next = bool(self.cursor)
        logger.info(f"Next cursor: {self.cursor}, has_next: {self.has_next}")

        for server_entry in server_data["servers"]:
            if not self._name_match(server_entry):
                logger.debug(f"Skipping server: {server_entry.get('name', '')}")
                # Not tracking server if it is filtered out by name filter
                continue

            # Track server before processing
            server_id = server_entry.get("id", "")
            server_name = server_entry.get("name", "")
            mcpserver_name = sanitize_k8s_name(server_name)

            self.server_tracking.append(
                {
                    "id": server_id,
                    "name": server_name,
                    "mcpserver_name": mcpserver_name,
                    "skipped": False,
                    "reason": None,
                }
            )

            self._import_server_entry(server_entry)
            self.imported_servers += 1
            if self.max_servers > 0 and self.imported_servers >= self.max_servers:
                logger.info(f"Reached max servers: {self.max_servers}")
                self.has_next = False
                break
        logger.info("Finished processing all server entries.")

    def _name_match(self, server_entry: dict) -> bool:
        if not self.name_filter:
            return True
        return self.name_filter.lower() in server_entry.get("name", "").lower()

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
            response = requests.get(f"{self.mcp_registry_url}/servers/{id}")
            response.raise_for_status()
            server_data = response.json()
        except requests.exceptions.RequestException as e:
            logger.error(
                f"Error fetching data from {self.mcp_registry_url}/servers/{id}: {e}"
            )
            return

        logger.info(f"Processing server: {server_def_name} (ID: {id})")

        mcp_server = {
            "apiVersion": f"{MCP_GROUP}/{MCP_VERSION}",
            "kind": MCP_SERVER_KIND,
            "metadata": {
                "name": server_def_name,
                "annotations": {
                    "mcp.opendatahub.io/registry": self.mcp_registry_url,
                },
                "labels": {
                    "app.kubernetes.io/name": "mcp-registry-operator",
                    "app.kubernetes.io/managed-by": self.catalog_name,
                    "mcp.opendatahub.io/mcpcatalog": self.catalog_name,
                    "mcp.opendatahub.io/mcpserverimportjob": self.import_job_name,
                    "mcp.opendatahub.io/server-id": server_entry.get("id"),
                },
            },
            "spec": {"server_detail": server_data},
        }

        # print(yaml.dump(mcp_server_definition, sort_keys=False))

        try:
            namespace = self.namespace or get_current_namespace()
            try:
                existing_resource = self.crd_api.get_namespaced_custom_object(
                    group=MCP_GROUP,
                    version=MCP_VERSION,
                    name=server_def_name,
                    namespace=namespace,
                    plural=MCP_SERVER_PLURALS,
                )
                if existing_resource:
                    logger.info(
                        f"{MCP_SERVER_KIND} '{server_def_name}' already exists in {namespace}. Skipping creation."
                    )
                    # Update tracking to mark as skipped
                    for server in self.server_tracking:
                        if server["mcpserver_name"] == server_def_name:
                            server["skipped"] = True
                            server["reason"] = "already_exists"
                            break
                    return
            except client.ApiException as e:
                if e.status == 404:
                    pass
                else:
                    raise

            if self.dry_run:
                logger.info(
                    f"Dry run mode enabled. Would have created McpServerDefinition: {server_def_name}"
                )
                return

            self.crd_api.create_namespaced_custom_object(
                group=MCP_GROUP,
                version=MCP_VERSION,
                namespace=namespace,
                plural=MCP_SERVER_PLURALS,
                body=mcp_server,
            )
            logger.info(f"Successfully created McpServerDefinition: {server_def_name}")
            # Update tracking to mark as successfully imported
            for server in self.server_tracking:
                if server["mcpserver_name"] == server_def_name:
                    server["skipped"] = False
                    server["reason"] = None
                    self.imported_count += 1
                    break
        except client.ApiException as e:
            logger.error(f"Error creating McpServerDefinition '{server_def_name}': {e}")
            # Update tracking to mark as failed
            for server in self.server_tracking:
                if server["mcpserver_name"] == server_def_name:
                    server["skipped"] = True
                    server["reason"] = "api_error"
                    break
        except Exception as e:
            logger.error(f"An unexpected error occurred for '{server_def_name}': {e}")
            # Update tracking to mark as failed
            for server in self.server_tracking:
                if server["mcpserver_name"] == server_def_name:
                    server["skipped"] = True
                    server["reason"] = "unexpected_error"
                    break

    def generate_configmap(self):
        """Generate and create a ConfigMap with execution details."""
        end_time = datetime.now()
        duration_sec = (end_time - self.start_time).total_seconds()

        # Prepare execution data
        execution_data = {
            "catalog_name": self.catalog_name,
            "registry_uri": self.mcp_registry_url,
            "importjob_name": self.import_job_name,
            "timestamp": self.start_time.isoformat(),
            "duration_sec": duration_sec,
            "max_servers": self.max_servers,
            "name_filter": self.name_filter or None,
            "status": self.import_status,
            "error": self.error_message,
            "imported_count": self.imported_count,
            "imported_servers": [],
        }

        # Add server tracking information
        for server in self.server_tracking:
            execution_data["imported_servers"].append(
                {
                    "id": server["id"],
                    "name": server["mcpserver_name"],
                    "skipped": server["skipped"],
                    "reason": server["reason"],
                }
            )

        # Generate YAML
        execution_yaml = yaml.dump(
            execution_data, default_flow_style=False, sort_keys=False
        )

        # Generate random ConfigMap name
        configmap_name = f"mcp-import-{uuid.uuid4().hex[:8]}"

        # Create ConfigMap
        configmap = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {
                "name": configmap_name,
                "namespace": self.namespace or get_current_namespace(),
                "labels": {
                    "app.kubernetes.io/name": "mcp-registry-operator",
                    "app.kubernetes.io/managed-by": self.catalog_name,
                    "mcp.opendatahub.io/mcpserverimportjob": self.import_job_name,
                    "mcp.opendatahub.io/mcpcatalog": self.catalog_name,
                },
                "annotations": {
                    "mcp.opendatahub.io/registry": self.mcp_registry_url,
                },
            },
            "data": {"execution.yaml": execution_yaml},
        }

        try:
            if self.dry_run:
                logger.info("=" * 80)
                logger.info("🔍 DRY RUN - CONFIGMAP GENERATION")
                logger.info("=" * 80)
                logger.info(f"Would create ConfigMap: {configmap_name}")
                logger.info(f"Execution YAML:\n{execution_yaml}")
                logger.info("=" * 80)
                return configmap_name

            # Create the ConfigMap
            core_v1_api = client.CoreV1Api()
            namespace = self.namespace or get_current_namespace()

            core_v1_api.create_namespaced_config_map(
                namespace=namespace, body=configmap
            )

            logger.info("=" * 80)
            logger.info("📋 CONFIGMAP GENERATION COMPLETE")
            logger.info("=" * 80)
            logger.info(f"✅ ConfigMap created: {configmap_name}")
            logger.info(f"📊 Total servers processed: {len(self.server_tracking)}")
            logger.info(
                f"✅ Successfully imported: {len([s for s in self.server_tracking if not s['skipped']])}"
            )
            logger.info(
                f"⏭️  Skipped: {len([s for s in self.server_tracking if s['skipped']])}"
            )
            logger.info(f"⏱️  Duration: {duration_sec:.2f} seconds")
            logger.info("=" * 80)

            return configmap_name

        except Exception as e:
            logger.error(f"Failed to create ConfigMap: {e}")
            return None


def main():
    """Main entry point for the importer script."""
    # Configure logging to output to terminal
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    crd_api = get_k8s_client()
    catalog_name = os.getenv("CATALOG_NAME", "")
    if not catalog_name:
        raise ValueError("Environment variable 'CATALOG_NAME' is not set.")
    registry_url = os.getenv("REGISTRY_URL", "")
    if not registry_url:
        raise ValueError("Environment variable 'REGISTRY_URL' is not set.")
    importjob_name = os.getenv("IMPORT_JOB_NAME", "")
    if not importjob_name:
        raise ValueError("Environment variable 'IMPORT_JOB_NAME' is not set.")

    # Get optional environment variables
    name_filter = os.getenv("NAME_FILTER", "")
    max_servers = int(os.getenv("MAX_SERVERS", "10"))
    namespace = os.getenv("NAMESPACE", "")
    dry_run = os.getenv("DRY_RUN", "false").lower() == "true"
    level = os.getenv("LOG_LEVEL", "INFO")
    logger.setLevel(level)
    importer = Importer(
        crd_api,
        catalog_name,
        importjob_name,
        registry_url,
        name_filter=name_filter,
        max_servers=max_servers,
        namespace=namespace,
        dry_run=dry_run,
    )

    try:
        while importer.has_next:
            try:
                importer.import_next()
            except Exception as e:
                importer.import_status = "failed"
                importer.error_message = str(e)
                raise Exception(f"Error during import: {e}")

        # Set success status only if no errors occurred
        if importer.import_status == "running":
            importer.import_status = "completed"

        # Generate ConfigMap at the end
        configmap_name = importer.generate_configmap()
        if configmap_name:
            logger.info(f"📋 Execution summary saved to ConfigMap: {configmap_name}")
        else:
            logger.warning("⚠️  Failed to create ConfigMap with execution summary")

    except Exception as e:
        logger.error(f"❌ Import process failed: {e}")
        # Set failed status
        importer.import_status = "failed"
        importer.error_message = str(e)
        # Still try to generate ConfigMap even if import failed
        try:
            configmap_name = importer.generate_configmap()
            if configmap_name:
                logger.info(
                    f"📋 Partial execution summary saved to ConfigMap: {configmap_name}"
                )
        except Exception as cm_error:
            logger.error(f"❌ Failed to create ConfigMap: {cm_error}")
        raise


if __name__ == "__main__":
    main()
