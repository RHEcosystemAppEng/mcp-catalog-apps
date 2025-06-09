# mcp-registry

## Overview
The `mcp-registry` is a FastAPI application designed to manage and interact with Kubernetes custom resources, specifically focusing on MCP servers.

## Features
- List servers from the Kubernetes cluster.
- Create and register a new server to the registry.
- Unregister an existing server from the registry.

The MCP Registy is defined by the env variable `MCP_REGISTRY_NAME` that must be set before launching the server.

The application assumes that the registry exists in the same namespace as where this application runs. 

An optional `namespace` query parameter can be passed in to specify where the servers are deployed.

## Installation
To install the dependencies for this project using `uv`, run the following command:

```bash
uv sync
```

This will install all the required dependencies listed in the `pyproject.toml` file.

## Usage
To run the FastAPI application, use the following command:

```bash
# Catalog service
MCP_REGISTRY_NAME=foo MCP_CATALOG_NAME=red-hat-ecosystem-mcp-catalog uv run uvicorn mcp_registry.app:app --host 0.0.0.0 --port 8000
```

```bash
# Registry service
MCP_REGISTRY_NAME=demo-registry MCP_CATALOG_NAME=red-hat-ecosystem-mcp-catalog uv run uvicorn mcp_registry.app:app --host 0.0.0.0 --port 8008
```

You can then access the API at `http://localhost:8000`. E.g.:
* List server definitions:
```bash
curl -X GET localhost:8000/serverdef | jq
```
* List blueprints:
```bash
curl -X GET localhost:8000/blueprint
```
* List servers:
```bash
curl -X GET localhost:8000/server
```

* Import server definitions (TODO: ext URL)
```bash
curl -X POST localhost:8000/import
```

## API Endpoints
- **GET /blueprint**: Retrieve a list of blueprints in the specified namespace (or the current namespace if it's not specified).
- **GET /server**: Retrieve a list of servers in the specified namespace (or the current namespace if it's not specified).

# Container image
```
podman build -t quay.io/ecosystem-appeng/mcp-registry:0.1 .
podman build --platform linux/amd64 -t quay.io/ecosystem-appeng/mcp-registry:amd64-0.1 .
```

```
podman run --rm -it -p 8000:8000 \
  -v ~/.kube:/opt/app-root/src/.kube \
  -e MCP_REGISTRY_NAME=my-registry \
  -e MCP_CATALOG_NAME=my-catalog \
  quay.io/ecosystem-appeng/mcp-registry:0.1
```

## Contributing
Contributions are welcome! Please open an issue or submit a pull request for any enhancements or bug fixes.

## License
This project is licensed under the MIT License. See the LICENSE file for more details.