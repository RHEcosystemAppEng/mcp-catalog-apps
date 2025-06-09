default: test

format:
	uv run python -m isort .
	uv run python -m ruff check --fix mcp_registry
	uv run python -m ruff format mcp_registry

lint: format
	uv run python -m ruff check mcp_registry
	uv run python -m ruff format --check mcp_registry

test: lint
	# uv run pytest mcp_registry

run-app:
	uv run uvicorn mcp_registry.app:app --host 0.0.0.0 --port 8000

help: ## Show this help
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'
