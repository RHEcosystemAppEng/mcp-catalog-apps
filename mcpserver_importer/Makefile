default: test

format:
	uv run python -m isort .
	uv run python -m ruff check --fix importer
	uv run python -m ruff format importer

lint: format
	uv run python -m ruff check importer
	uv run python -m ruff format --check importer

test: lint
	# uv run pytest importer

run-app:
	uv run -m importer.importer

help: ## Show this help
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'
