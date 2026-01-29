# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A fault-tolerant GenAI agent system that interacts with a mock ticketing API. The system has five main components:
1. **Mock Ticketing API** - FastAPI REST API with in-memory storage
2. **GenAI Agent** - OpenAI-powered agent with function calling for ticket operations
3. **PR Review Bot** - GitHub Actions workflow that uses LLM to review pull requests
4. **CI/CD Pipeline** - GitHub Actions with lint, test, docker, and security stages
5. **Infrastructure** - Terraform configs for Azure App Service deployment

## Common Commands

```bash
# Run API server
uvicorn main:app --reload

# Run agent CLI (requires AZURE_OPENAI_* env vars)
python -m agent.cli

# Run all tests with coverage
pytest tests/ --cov=api --cov=agent --cov=main --cov-report=term-missing

# Run a single test file
pytest tests/test_api.py -v

# Run a single test
pytest tests/test_api.py::TestCreateTicket::test_create_ticket_valid_payload_returns_201_created -v

# Lint and format
ruff check .
ruff format .

# Terraform (from infra/ directory)
terraform init -backend=false
terraform validate
terraform fmt -check -recursive

# Docker
docker build -t ticketing-api:test .
docker run -d -p 8000:8000 ticketing-api:test
```

## Architecture

### API Structure
- `main.py` - FastAPI app entry point with health check at `/`
- `config.py` - Centralizes environment loading (import first in entry points)
- `api/routes.py` - Aggregates versioned routers under `/v1` prefix
- `api/v1/endpoints.py` - CRUD endpoints for tickets
- `api/models.py` - Pydantic models (Ticket, TicketCreate, TicketUpdate)
- `api/storage.py` - Thread-safe in-memory storage with `TicketStorage` class
- `api/auth.py` - API key authentication (X-API-Key header)

### Agent Structure
- `agent/agent.py` - `TicketingAgent` class orchestrates OpenAI chat completions with tool calls
- `agent/client.py` - `TicketingClient` HTTP client wrapping API calls
- `agent/tools.py` - OpenAI function definitions for create/list/get/update/delete tickets
- `agent/cli.py` - Interactive CLI with spinner

### Agent Flow
```
User Input -> TicketingAgent.chat() -> OpenAI API (with tools)
                    |
                    v
            Tool calls detected? --yes--> _execute_tool() -> TicketingClient -> API
                    |                              |
                    no                             v
                    |                     Return to OpenAI for next iteration
                    v
            Return response to user
```

## Key Patterns

- **API credentials**: Agent uses Azure OpenAI (`AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`)
- **Ticket statuses**: OPEN, RESOLVED, CLOSED. Resolution note required when setting status to RESOLVED
- **Coverage requirement**: 80% minimum, enforced in CI
- **Ruff version**: Pinned to 0.14.14 in CI

## Environment Variables

| Variable | Description |
|----------|-------------|
| `API_KEY` | API key for authenticating with the ticketing API |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key |
| `AZURE_OPENAI_DEPLOYMENT` | Azure deployment name |
| `API_BASE_URL` | API URL for agent (default: http://localhost:8000/v1) |
| `LOG_LEVEL` | Logging level for CLI (default: WARNING) |

## Authentication

API key authentication secures all `/v1/*` endpoints. Health check (`/`) remains public.

```
Client Request                         Server
     |                                    |
     |-- X-API-Key: <key> --------------->|
     |                                    |-- Check API_KEY env var
     |                                    |-- If not set: 500 Internal Server Error
     |                                    |-- If missing header: 401 Unauthorized
     |                                    |-- If invalid: 401 Unauthorized
     |<-- Response -----------------------|
```

Key implementation details:
- `secrets.compare_digest()` for constant-time comparison (prevents timing attacks)
- API key cached with `@lru_cache(maxsize=1)` at startup
- Generic error message for missing config (avoids information disclosure)
- Server-side logging for debugging misconfigurations

## CI/CD Pipeline

Pipeline runs on push to main and pull requests. Stages are ordered for fail-fast behavior.

```
Stage 1: lint (ruff format + check)
    ↓
Stage 2: test (pytest with 80% coverage)
    ↓
Stage 3: terraform validate + docker build (parallel)
    ↓
Stage 4: security scan (Snyk: deps, image, IaC)
```

Pipeline features:
- **Concurrency**: Cancels in-progress runs when new commits are pushed
- **Permissions**: Least privilege (`contents: read`)
- **Inputs**: Manual trigger with configurable tf_environment, location, sku_name, python_version, terraform_version

## Error Handling

### API Error Responses
| Status | When | Example |
|--------|------|---------|
| 404 | Ticket not found | `{"detail": "Ticket 123 not found"}` |
| 422 | Validation error | `{"detail": "Resolution is required when status is RESOLVED"}` |
| 422 | Invalid status | `{"detail": "Input should be 'OPEN', 'RESOLVED' or 'CLOSED'"}` |
| 401 | Missing/invalid API key | `{"detail": "Invalid API key"}` |
| 500 | Server misconfiguration | `{"detail": "Internal server error"}` |

### Agent Error Flow
```python
# client.py captures API error detail
if response.status_code >= 400:
    error_detail = response.json().get("detail", response.text)
    return {"success": False, "error": error_detail}

# agent.py returns error to LLM
tool_result = json.dumps({"success": False, "error": "Ticket not found"})

# LLM interprets and explains to user based on SYSTEM_PROMPT
```

The system prompt instructs the agent to explain errors clearly and suggest valid options.

## Testing Patterns

### Fixtures
```python
@pytest.fixture
def client():
    """Authenticated test client."""
    return TestClient(app, headers={"X-API-Key": TEST_API_KEY})

@pytest.fixture
def sample_ticket(client):
    """Create a ticket for tests that need existing data."""
    response = client.post("/v1/tickets", json={...})
    return response.json()
```

### Test Organization
- `TestClassName` groups related tests
- Test names follow `test_<action>_<condition>_<expected_result>` pattern
- Example: `test_update_ticket_invalid_status_returns_422`

### Mocking OpenAI
```python
@pytest.fixture
def mock_openai(monkeypatch):
    mock_client = Mock()
    mock_client.chat.completions.create.return_value = Mock(
        choices=[Mock(message=Mock(content="Response", tool_calls=None))]
    )
    monkeypatch.setattr("agent.agent.AzureOpenAI", lambda **kw: mock_client)
    return mock_client
```

## PR Review Bot

Workflow: `.github/workflows/pull-request-review.yml`
Script: `scripts/analyze_pull_request.py`

### Flow
```
PR opened/updated
    ↓
GitHub Action triggers
    ↓
Script fetches diff via `gh pr diff`
    ↓
Sends diff to Azure OpenAI for analysis
    ↓
Posts review comment via `gh pr comment`
```

### Key Implementation
- Uses `subprocess` to run `gh` CLI commands
- Chunks large diffs to fit token limits
- Posts as a single comment (not inline reviews)
