FROM registry.redhat.io/rhel9/python-311 AS uv
RUN python3 -m ensurepip && pip install --no-cache-dir uv

WORKDIR /opt/app-root/src/

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
COPY importer ./importer
RUN uv sync --frozen --no-dev --no-editable

FROM registry.redhat.io/rhel9/python-311
COPY --from=uv /opt/app-root/src/.venv /opt/app-root/src/.venv

ENV PATH="/opt/app-root/src/.venv/bin:$PATH"

ENV PORT=8000

# Name of McpCatalog to register the servers to
ENV CATALOG_NAME="" 
# URL of the MCP Registry to import the servers from
ENV REGISTRY_URL=""
# Name of the ImportJob to annotate the servers with
ENV IMPORT_JOB_NAME=""
# Filter to apply to the name of the servers to import
ENV NAME_FILTER=""
# Maximum number of servers to import (0 = no limit)
ENV MAX_SERVERS="10"
# Kubernetes namespace to create McpServer resources in (default: current namespace)
ENV NAMESPACE=
# Enable dry run mode - shows what would be imported without creating resources (default: false)
ENV DRY_RUN="false"
# Set logging level (default: INFO, options: DEBUG, INFO, WARNING, ERROR)
ENV LOG_LEVEL="INFO"

ENTRYPOINT ["mcpserver-importer"]