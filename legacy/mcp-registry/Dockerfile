FROM registry.redhat.io/rhel9/python-311 AS uv
RUN python3 -m ensurepip && pip install --no-cache-dir uv

WORKDIR /opt/app-root/src/

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
COPY mcp_registry ./mcp_registry
RUN pwd
RUN find .

RUN uv sync --frozen --no-dev --no-editable
RUN find . -name .venv

FROM registry.redhat.io/rhel9/python-311
COPY --from=uv /opt/app-root/src/.venv /opt/app-root/src/.venv

ENV PATH="/opt/app-root/src/.venv/bin:$PATH"

ENV PORT=8000

ENV MCP_CATALOG_NAME=""
ENV MCP_REGISTRY_NAME=""
ENV MCP_IMPORT_JOB_NAME=""

ENTRYPOINT ["uvicorn", "mcp_registry.app:app", "--host", "0.0.0.0", "--port", "8000"]