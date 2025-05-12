import os

from fastapi import FastAPI, Query, HTTPException
from kubernetes import client, config
from typing import List

GROUP = "mcp.opendatahub.io"
VERSION = "v1"


def get_k8s_client():
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()

    return client.CustomObjectsApi()


def _get_current_namespace():
    try:
        with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace", "r") as f:
            return f.read().strip()
    except Exception:
        context = config.list_kube_config_contexts()[1]
        return context.get("context", {}).get("namespace", "default")


def _match_registry(
    server_namespace: str,
    registry_ref: dict,
) -> bool:
    if registry_ref.get("name") == registry_name:
        registry_namespace = registry_ref.get("namespace", _get_current_namespace())
        if registry_namespace == server_namespace:
            return True
    return False


app = FastAPI()
crd_api = client.CustomObjectsApi()
crd_api = get_k8s_client()
registry_name = os.getenv("MCP_REGISTRY_NAME", None)
if not registry_name:
    raise ValueError("Environment variable 'MCP_REGISTRY_NAME' is not set.")


@app.get("/server")
async def list_servers(
    namespace: str = Query(None, description="Namespace to query servers")
):
    resources = crd_api.list_namespaced_custom_object(
        group=GROUP,
        version=VERSION,
        namespace=namespace if namespace else _get_current_namespace(),
        plural="mcpservers",
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
        if _match_registry(
            item["metadata"]["namespace"],
            item["spec"].get("registry-ref", {}),
        )
    ]


# Connect a given MCP Registry (by name)
# List the managed MCP servers
# Create and register a new MCP server from a blueprint, a given container or an external URL
# Unregister a given server
