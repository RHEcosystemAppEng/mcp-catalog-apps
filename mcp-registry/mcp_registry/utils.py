import hashlib
import logging
import re
from enum import Enum

from fastapi import HTTPException

from kubernetes import client, config
from mcp_registry.defaults import MCP_GROUP, MCP_VERSION

logger = logging.getLogger("uvicorn.error")
logger.setLevel(logging.INFO)


def get_k8s_client():
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()

    return client.CustomObjectsApi()


async def get_registry(crd_api, catalog_name: str, registry_name: str):
    resources = crd_api.list_namespaced_custom_object(
        group=MCP_GROUP,
        version=MCP_VERSION,
        namespace=get_current_namespace(),
        plural="mcpregistries",
    )
    matches = [
        r for r in resources.get("items", []) if r["metadata"]["name"] == registry_name
    ]
    if not matches:
        raise HTTPException(
            status_code=404,
            detail=f"Registry '{registry_name}' not found in namespace '{get_current_namespace()}'.",
        )
    return matches[0]


def get_current_namespace():
    try:
        with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace", "r") as f:
            return f.read().strip()
    except Exception:
        context = config.list_kube_config_contexts()[1]
        return context.get("context", {}).get("namespace", "default")


def sanitize_k8s_name(
    input_string: str, max_length: int = 253, add_hash_suffix: bool = False
) -> str:
    """
    Sanitizes a string to be compatible with Kubernetes resource naming conventions (DNS Subdomain Name).
    """
    original_hash = ""
    if add_hash_suffix:
        original_hash = hashlib.sha1(input_string.encode("utf-8")).hexdigest()[:8]
        max_length -= len(original_hash) + 1  # +1 for the hyphen

    s = input_string.lower()

    s = re.sub(r"[^a-z0-9\.-]+", "-", s)
    s = re.sub(r"[-.]+", "-", s)
    s = s.strip("-.")

    if not s or not (s[0].isalnum() and s[-1].isalnum()):
        s = "invalid-name-" + hashlib.sha1(input_string.encode("utf-8")).hexdigest()[:8]

    if len(s) > max_length:
        s = s[:max_length]

    if add_hash_suffix:
        s = f"{s}-{original_hash}"

    return s


def match_registry(
    registry_name: str,
    server_namespace: str,
    registry_ref: dict,
) -> bool:
    if registry_ref.get("name") == registry_name:
        registry_namespace = registry_ref.get("namespace", get_current_namespace())
        if registry_namespace == server_namespace:
            return True
    return False


def match_catalog(
    catalog_name: str,
    blueprint_namespace: str,
    catalog_ref: dict,
) -> bool:
    if catalog_ref.get("name") == catalog_name:
        catalog_namespace = catalog_ref.get("namespace", get_current_namespace())
        if catalog_namespace == blueprint_namespace:
            return True
    return False


class ServerRuntime(Enum):
    NODE = "node"
    UVX = "uvx"
    DOCKER = "docker"
    UNKNOWN = "unknown"
