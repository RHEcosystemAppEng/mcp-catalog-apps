FROM registry.redhat.io/rhel9/python-312

WORKDIR /opt/app-root/src
COPY --chown=1001:0 --exclude=.venv --exclude=mcp_server_registry.egg-info . /opt/app-root/src

RUN which pip
RUN python -m ensurepip && pip install --no-cache-dir uv
# ENV PATH="/usr/local/bin:$PATH" \
#   UV_PYTHON_PREFERENCE=only-system
RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --frozen --no-dev --no-editable

ENV MCP_REGISTRY_NAME=""
EXPOSE 9000

ENV PATH="/opt/app-root/src/.venv/bin:$PATH"
CMD ["uvicorn", "server_registry:app", "--host", "0.0.0.0", "--port", "9000"]