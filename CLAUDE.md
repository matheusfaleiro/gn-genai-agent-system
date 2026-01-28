# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A fault-tolerant GenAI agent system that interacts with a mock ticketing API. The system has four main components:
1. **Mock Ticketing API** - FastAPI REST API with in-memory storage
2. **GenAI Agent** - OpenAI-powered agent with function calling for ticket operations
3. **PR Review Bot** - GitHub Actions workflow that uses LLM to review pull requests
4. **Infrastructure** - Terraform configs for Azure App Service deployment

## Common Commands

```bash
# Run API server
uvicorn main:app --reload

# Run agent CLI (requires OPENAI_API_KEY or AZURE_OPENAI_* env vars)
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
- `api/routes.py` - Aggregates versioned routers under `/v1` prefix
- `api/v1/endpoints.py` - CRUD endpoints for tickets
- `api/models.py` - Pydantic models (Ticket, TicketCreate, TicketUpdate)
- `api/storage.py` - Thread-safe in-memory storage with `TicketStorage` class

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

- **API credentials**: Agent supports both Azure OpenAI (`AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`) and standard OpenAI (`OPENAI_API_KEY`)
- **Ticket statuses**: OPEN, RESOLVED, CLOSED. Resolution note required when setting status to RESOLVED
- **Coverage requirement**: 80% minimum, enforced in CI
- **Ruff version**: Pinned to 0.14.14 in CI

## Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | Standard OpenAI API key |
| `OPENAI_MODEL` | Model name (default: gpt-4) |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key |
| `AZURE_OPENAI_DEPLOYMENT` | Azure deployment name (default: gpt-5-mini) |
| `API_BASE_URL` | API URL for agent (default: http://localhost:8000/v1) |
| `LOG_LEVEL` | Logging level for CLI (default: WARNING) |
