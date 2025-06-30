# MCP Server Importer

A Python application for importing MCP Servers from an MCP Registry into Kubernetes as custom resources.

References:
* [McpServer](https://github.com/RHEcosystemAppEng/mcp-catalog-operator/blob/main/api/v1alpha1/mcpserver_types.go)
* [McpServerImportJob](https://github.com/RHEcosystemAppEng/mcp-catalog-operator/blob/main/api/v1alpha1/mcpserverimportjob_types.go)
* [MCP Registry schema](https://github.com/modelcontextprotocol/registry/blob/main/docs/openapi.yaml)

## Overview

## Features

- **Batch Import**: Fetches server definitions from MCP Registry with pagination support
- **Kubernetes Integration**: Creates `McpServer` custom resources in the cluster
- **Duplicate Handling**: Skips existing resources to avoid conflicts
- **Name Sanitization**: Automatically sanitizes server names for Kubernetes compatibility
- **Name Filtering**: Filters servers by name pattern to import only specific servers
- **Max Servers Limit**: Configurable limit on the number of servers to import
- **Error Handling**: Robust error handling with detailed logging
- **Container Ready**: Includes Dockerfile for containerized deployment

## Architecture

The importer works by:
1. Connecting to an MCP Registry API endpoint
2. Fetching server definitions in batches (100 servers per request)
3. For each server, fetching detailed information
4. Creating `McpServer` custom resources in Kubernetes
5. Adding appropriate annotations and labels for tracking:
   - **Annotations**: 
     - `mcp.opendatahub.io/registry`: URL of the source MCP registry
   - **Labels**:
     - `app.kubernetes.io/name`: Set to "mcp-registry-operator"
     - `app.kubernetes.io/managed-by`: Name of the catalog managing the import
     - `mcp.opendatahub.io/mcpcatalog`: Catalog name for grouping
     - `mcp.opendatahub.io/mcpserverimportjob`: Import job identifier
     - `mcp.opendatahub.io/server-id`: Original server ID from the registry
   

## Installation

### Prerequisites

- Python 3.11+
- Kubernetes cluster with MCP custom resources installed
- Access to an MCP Registry API

### Local Development

Clone the repository and navigate to the importer directory:

```bash
git clone https://github.com/RHEcosystemAppEng/mcp-catalog-apps
cd mcp-catalog-apps/mcpserver_importer
```

Install dependencies using uv:

```bash
uv sync
```

Activate virtual environment:

```bash
source .venv/bin/activate
```

Run the importer with environment variables:

```bash
CATALOG_NAME=red-hat-ecosystem-mcp-catalog \
REGISTRY_URL=http://localhost:8080/v0 \
IMPORT_JOB_NAME=job-1 \
NAME_FILTER= \
MAX_SERVERS=10 \
uv run mcpserver-importer
```

### Container Deployment

Build the container image:

```bash
docker build mcpserver-importer:0.1.0 .
```

Run the container:

```bash
docker run -e CATALOG_NAME=my-catalog \
           -e REGISTRY_URL=https://registry.example.com \
           -e IMPORT_JOB_NAME=import-job-1 \
           -e NAME_FILTER= \
           -e MAX_SERVERS=100 \
           mcpserver-importer:0.1.0
```

## Configuration

### Environment Variables

The importer requires the following environment variables:

- `CATALOG_NAME`: Name of the MCP catalog (required)
- `REGISTRY_URL`: URL of the MCP Registry API (required)
- `IMPORT_JOB_NAME`: Name of the import job for tracking (required)

Optional environment variables:

- `NAME_FILTER`: Filter servers by name (substring match, default: empty)
- `MAX_SERVERS`: Maximum number of servers to import (default: 100, 0 = no limit)
- `NAMESPACE`: Namespace to deploy `McpServer` resources (default: current namespace)
- `DRY_RUN`: Enable dry run mode - shows what would be imported without creating resources (default: `false`)
- `LOG_LEVEL`: Set logging level (default: `INFO`, options: `DEBUG`, `INFO`, `WARNING`, `ERROR`)

### Execution Summary

At the end of each import execution, a `ConfigMap` is automatically generated with the following information:

- **Execution Details**: Catalog name, registry URI, import job name, timestamp, duration
- **Configuration**: Max servers limit, name filter applied
- **Server Tracking**: List of all processed servers with their IDs, McpServer names, and status (imported/skipped)

The `ConfigMap` has a random name following the pattern `mcp-import-{random-hex}` and a label to connect it to the triggering `McpServerImportJob`.

Payload data includes:

```yaml
# Example execution.yaml content
catalog_name: test-catalog
registry_uri: http://localhost:8080/v0
importjob_name: test-job
timestamp: '2025-06-27T19:03:19.343783'
duration_sec: 2.16
max_servers: 3
name_filter: null
status: completed
error: null
imported_count: 0
imported_servers:
- id: 0007544a-3948-4934-866b-b4a96fe53b55
  name: io-github-appcypher-awesome-mcp-servers
  skipped: false
  reason: null
- id: 00613acb-73e2-4f93-8b96-296df17316c8
  name: io-github-kenjihikmatullah-productboard-mcp
  skipped: true
  reason: already_exists
```

**Status Values:**
- `running`: Import process is in progress
- `completed`: Import process completed successfully
- `failed`: Import process failed with an error

**Error Field:**
- `null`: No errors occurred
- `string`: Error message describing what went wrong (e.g., connection errors, API errors)

**Imported Count:**
- Number of servers successfully imported (excludes skipped servers)

**Skip Reasons:**
- `already_exists`: Server already exists in the namespace
- `api_error`: Kubernetes API error occurred
- `unexpected_error`: Unexpected error during processing

### Kubernetes Configuration

The importer automatically detects Kubernetes configuration:
1. **In-cluster**: When running inside a Kubernetes pod
2. **Local**: Uses `~/.kube/config` when running locally

### Required Permissions

The importer needs the following Kubernetes permissions:
- Read access to the current namespace
- Create/Update access to `McpServer` custom resources
- Create access to `ConfigMap` resources for execution summaries

## API Integration

### Kubernetes Custom Resources

The importer creates `McpServer` custom resources with the following structure:

```yaml
apiVersion: mcp.opendatahub.io/v1alpha1
kind: McpServer
metadata:
  name: sanitized-server-name
  annotations:
    mcp.opendatahub.io/registry: http://localhost:8080/v0
  labels:
    app.kubernetes.io/name: mcp-registry-operator
    app.kubernetes.io/managed-by: catalog-name
    mcp.opendatahub.io/mcpcatalog: catalog-name
    mcp.opendatahub.io/mcpserverimportjob: import-job-name
    mcp.opendatahub.io/server-id: original-server-id
spec:
  server_detail: # Full server data from registry
```

## Development

### Code Quality

The project uses several tools for code quality:

- **Ruff**: For linting and formatting
- **isort**: For import sorting
- **mypy**: For type checking

Run all quality checks:

```bash
make lint
```

Format code only:

```bash
make format
```

### Testing

Run tests:

```bash
make test
```

Run specific test file:

```bash
uv run pytest importer/tests/test_importer.py
```

## Error Handling

The importer includes comprehensive error handling:

- **Network Errors**: Retries and logs connection issues
- **API Errors**: Handles HTTP errors gracefully
- **Kubernetes Errors**: Manages resource creation conflicts
- **Validation Errors**: Sanitizes and validates input data

### Common Issues

1. **Missing Environment Variables**: Ensure all required env vars are set
2. **Kubernetes Access**: Verify cluster access and permissions
3. **Registry API**: Check API endpoint availability and authentication
4. **Resource Conflicts**: Existing resources are skipped automatically

## Monitoring and Logging

The importer provides detailed logging:

- **INFO**: Successful operations and progress
- **WARNING**: Non-critical issues (e.g., missing fields)
- **ERROR**: Critical failures and exceptions

Log levels can be configured via the logging system and the `LOG_LEVEL` env variable.

## Deployment

### Job for On-Demand Imports

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: mcpserver-importer-job
spec:
  template:
    spec:
      containers:
      - name: importer
        image: mcpserver-importer:latest
        env:
        - name: CATALOG_NAME
          value: "my-catalog"
        - name: REGISTRY_URL
          value: "https://registry.example.com"
        - name: IMPORT_JOB_NAME
          value: "scheduled-import"
        - name: MAX_SERVERS
          value: "5"
      restartPolicy: OnFailure
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

Licensed under the Apache License, Version 2.0. 