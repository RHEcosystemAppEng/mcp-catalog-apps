# GitHub Actions Workflows

This directory contains GitHub Actions workflows for the mcp-catalog-apps monorepo.

## Available Workflows

### 1. Test Coverage - mcpserver_importer (`mcpserver_importer-test-coverage.yml`)

**Triggers:**
- Push to `main` or `develop` branches (only when `mcpserver_importer/**` files change)
- Pull requests to `main` or `develop` branches (only when `mcpserver_importer/**` files change)
- Manual execution via `workflow_dispatch`

**Features:**
- Runs on Python 3.11 and 3.12
- Installs dependencies using `uv`
- Runs linting checks
- Executes test coverage with `make test-coverage`
- Uploads coverage reports to Codecov
- Comments on PRs with coverage results
- Optional: Run all tests (not just coverage) via manual input

**Manual Execution:**
1. Go to the "Actions" tab in GitHub
2. Select "Test Coverage - mcpserver_importer" workflow
3. Click "Run workflow"
4. Optionally check "Run all tests" for additional test execution

### 2. Run Tests - mcpserver_importer (`mcpserver_importer-test.yml`)

**Triggers:**
- Push to `main` or `develop` branches (only when `mcpserver_importer/**` files change)
- Pull requests to `main` or `develop` branches (only when `mcpserver_importer/**` files change)
- Manual execution via `workflow_dispatch`

**Features:**
- Runs on Python 3.11 only (faster execution)
- Installs dependencies using `uv`
- Runs linting checks
- Executes tests with `make test`
- Uploads test results as artifacts

**Use Case:**
This workflow is designed for faster feedback during development, as it doesn't generate coverage reports and runs on fewer Python versions.

## Workflow Configuration

### Path Filtering
Both workflows use path filtering to only trigger when files in the `mcpserver_importer/` directory change:

```yaml
paths:
  - 'mcpserver_importer/**'
```

### Caching
Dependencies are cached using `mcpserver_importer/uv.lock` as the cache key to improve build times:

```yaml
key: ${{ runner.os }}-uv-mcpserver_importer-${{ hashFiles('mcpserver_importer/uv.lock') }}
```

### Environment Variables
The `PYTHONPATH` is set to ensure proper module resolution:

```yaml
env:
  PYTHONPATH: ${{ github.workspace }}/mcpserver_importer
```

## Monorepo Structure

This repository contains multiple projects:

```
mcp-catalog-apps/
├── .github/workflows/          # GitHub Actions workflows
│   ├── mcpserver_importer-test-coverage.yml
│   ├── mcpserver_importer-test.yml
│   └── README.md
├── mcpserver_importer/         # MCP Server Importer project
├── mcp-registry/              # MCP Registry project
├── mcp-proxy/                 # MCP Proxy project
├── policy-handler/            # Policy Handler project
└── ...                        # Other projects
```

Each project can have its own workflows, and they are triggered independently based on path changes.

## Local Development

To run the same commands locally for the mcpserver_importer project:

```bash
# Navigate to the project directory
cd mcpserver_importer

# Install dependencies
uv sync --extra test

# Run linting
uv run make lint

# Run tests
uv run make test

# Run test coverage
uv run make test-coverage
```

## Troubleshooting

### Common Issues

1. **Workflow not triggering**: Ensure your changes are in the `mcpserver_importer/` directory
2. **Dependency issues**: Check that `mcpserver_importer/uv.lock` is up to date
3. **Test failures**: Run tests locally first to debug issues
4. **Coverage upload failures**: The workflow continues even if Codecov upload fails

### Manual Workflow Execution

If you need to run workflows manually:

1. Navigate to the "Actions" tab in your GitHub repository
2. Select the desired workflow (e.g., "Test Coverage - mcpserver_importer")
3. Click "Run workflow"
4. Choose the branch and any optional inputs
5. Click "Run workflow"

## Dependencies

The workflows use the following GitHub Actions:

- `actions/checkout@v4` - Check out repository code
- `actions/setup-python@v4` - Set up Python environment
- `astral-sh/setup-uv@v3` - Install uv package manager
- `actions/cache@v4` - Cache dependencies
- `codecov/codecov-action@v4` - Upload coverage to Codecov
- `actions/upload-artifact@v4` - Upload test results
- `actions/github-script@v7` - Comment on PRs with results

## Adding New Projects

To add workflows for other projects in the monorepo:

1. Create a new workflow file in `.github/workflows/` with the naming pattern: `{project-name}-{workflow-type}.yml`
2. Use the same structure as the mcpserver_importer workflows
3. Update the path filtering to match your project directory
4. Update cache keys and artifact names to be project-specific
5. Update the workflow name to include the project name

**Example naming convention:**
- `mcp-registry-test.yml`
- `mcp-registry-test-coverage.yml`
- `policy-handler-test.yml`
- `policy-handler-test-coverage.yml` 