# mcp-server-registry

## Overview
The `mcp-server-registry` is a FastAPI application designed to manage and interact with Kubernetes custom resources, specifically focusing on MCP servers.

## Features
- List servers from the Kubernetes cluster.
- Create and register a new server to the registry.
- Unregister an existing server from the registry.

The MCP Registy is defined by the env variable `MCP_CATALOG_NAME` that must be set before launching the server.

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
uvicorn blueprint_registry:app --host 0.0.0.0 --port 9000
```

You can then access the API at `http://localhost:9000`.

```
curl "http://localhost:9000/blueprint?namespace=foo"
```

## API Endpoints
- **GET /blueprint**: Retrieve a list of blueprints in the specified namespace (or the current namespace if it's not specified).
- **GET /server**: Retrieve a list of servers in the specified namespace (or the current namespace if it's not specified).

# Container image
```
podman build -t quay.io/ecosystem-appeng/mcp-blueprint-registry:1.0 .
```

```
podman run --rm -it -p 9000:9000 \
  -v ~/.kube:/opt/app-root/src/.kube \
  -e MCP_CATALOG_NAME=red-hat-ecosystem-mcp-catalog \
  quay.io/ecosystem-appeng/mcp-blueprint-registry:1.0
```

## Contributing
Contributions are welcome! Please open an issue or submit a pull request for any enhancements or bug fixes.

## License
This project is licensed under the MIT License. See the LICENSE file for more details.