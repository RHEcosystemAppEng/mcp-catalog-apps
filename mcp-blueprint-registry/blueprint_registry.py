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


def _match_catalog(
    blueprint_namespace: str,
    catalog_ref: dict,
) -> bool:
    if catalog_ref.get("name") == catalog_name:
        catalog_namespace = catalog_ref.get("namespace", _get_current_namespace())
        if catalog_namespace == blueprint_namespace:
            return True
    return False


app = FastAPI()
crd_api = client.CustomObjectsApi()
crd_api = get_k8s_client()
catalog_name = os.getenv("MCP_CATALOG_NAME", None)
if not catalog_name:
    raise ValueError("Environment variable 'MCP_CATALOG_NAME' is not set.")


@app.get("/blueprint")
async def list_blueprints(
    namespace: str = Query(None, description="Namespace to query blueprints")
):
    resources = crd_api.list_namespaced_custom_object(
        group=GROUP,
        version=VERSION,
        namespace=namespace if namespace else _get_current_namespace(),
        plural="mcpblueprints",
    )
    return [
        {
            "name": item["metadata"]["name"],
            "namespace": item["metadata"]["namespace"],
            "description": item["metadata"]["namespace"],
            "catalog": item["spec"].get("catalog-ref"),
            "provider": item["spec"].get("provider", ""),
            "license": item["spec"].get("license", ""),
            "competencies": item["spec"].get("competencies", []),
            "image": item["spec"].get("mcp-server", {}).get("image", ""),
        }
        for item in resources.get("items", [])
        if _match_catalog(
            item["metadata"]["namespace"],
            item["spec"].get("catalog-ref", {}),
        )
    ]