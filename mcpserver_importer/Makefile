default: test

format:
	uv run python -m isort .
	uv run python -m ruff check --fix importer tests
	uv run python -m ruff format importer tests

lint: format
	uv run python -m ruff check importer
	uv run python -m ruff format --check importer

test: lint
	uv run pytest tests/ -v

test-coverage: test
	uv run pytest tests/ --cov=importer --cov-report=html --cov-report=term-missing

test-unit:
	uv run pytest tests/ -m unit -v

test-integration:
	uv run pytest tests/ -m integration -v

run-app:
	uv run -m importer.importer

help: ## Show this help
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'
