# GenAI Agent System

End-to-end prototype of a fault-tolerant GenAI agent interacting with a mock ticketing API, including CI/CD automation and Azure infrastructure configs.

## Prerequisites

- Python 3.9+
- Azure OpenAI resource with a deployed model
- Docker (optional, for containerized deployment)
- Terraform 1.5+ (optional, for infrastructure validation)

## Quick Start

### Step 1: Clone and Install

```bash
git clone https://github.com/matheusfaleiro/gn-genai-agent-system.git
cd gn-genai-agent-system

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

### Step 2: Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```bash
# Required: API key for authenticating with the ticketing API
API_KEY=my-secret-key-123

# Required: Azure OpenAI credentials
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-azure-openai-key
AZURE_OPENAI_DEPLOYMENT=gpt-5-mini
```

### Step 3: Start the API Server

Open a terminal and run:

```bash
source .venv/bin/activate
API_KEY=my-secret-key-123 uvicorn main:app --reload
```

Verify it's running:

```bash
curl http://localhost:8000/
# {"status":"healthy"}
```

### Step 4: Run the Agent CLI

Open a second terminal and run:

```bash
source .venv/bin/activate
export API_KEY=my-secret-key-123
export AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
export AZURE_OPENAI_API_KEY=your-azure-openai-key

python -m agent.cli
```

### Step 5: Try Example Commands

Once the CLI is running, try these natural language commands:

```
You: Create a new ticket about a keyboard not working
You: List all open tickets
You: Get details for ticket <id-from-previous-response>
You: Update ticket <id> to be RESOLVED with resolution 'Replaced faulty cable'
You: Update ticket <id> to have status 'INVALID'
```

The agent will explain validation errors (like invalid status) and handle not-found cases gracefully.

## API Reference

Base URL: `http://localhost:8000`

Health check endpoint at `/` (no auth required).

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/tickets` | Create a ticket |
| GET | `/v1/tickets` | List tickets (optional `?status=OPEN\|RESOLVED\|CLOSED`) |
| GET | `/v1/tickets/{id}` | Get ticket by ID |
| PATCH | `/v1/tickets/{id}` | Update ticket |
| DELETE | `/v1/tickets/{id}` | Delete ticket |

All `/v1/*` endpoints require `X-API-Key` header.

## Running Tests

```bash
# All tests with coverage
pytest tests/ --cov=api --cov=agent --cov=main --cov-report=term-missing

# Single test file
pytest tests/test_api.py -v

# Single test
pytest tests/test_api.py::TestCreateTicket::test_create_ticket_valid_payload_returns_201_created -v
```

## Docker

```bash
# Build and run
docker build -t ticketing-api .
docker run -p 8000:8000 -e API_KEY=your-secret-key ticketing-api

# Or use docker-compose (set API_KEY in .env file)
docker-compose up
```

## Terraform

```bash
cd infra
terraform init -backend=false
terraform validate
terraform fmt -check
```

## CI/CD Pipeline

The project uses GitHub Actions for continuous integration with the following jobs:

| Job | Description |
|-----|-------------|
| **terraform** | Validates Terraform configuration (fmt, init, validate) |
| **lint** | Checks code formatting and linting with Ruff |
| **test** | Runs pytest with 80% coverage threshold |
| **docker** | Builds image and verifies health endpoint |
| **security** | Snyk scans for Python deps, Docker image, and Terraform IaC |

Security scanning with [Snyk](https://snyk.io/) covers:
- Python dependency vulnerabilities
- Docker image vulnerabilities
- Infrastructure as Code misconfigurations

Requires `SNYK_TOKEN` secret configured in GitHub repository settings.

## Project Structure

```
├── api/                  # Mock Ticketing API
│   ├── auth.py           # API key authentication
│   ├── v1/endpoints.py   # CRUD endpoints
│   ├── models.py         # Pydantic models
│   └── storage.py        # In-memory storage
├── agent/                # GenAI Agent
│   ├── agent.py          # Agent orchestration with Azure OpenAI
│   ├── client.py         # HTTP client for API
│   ├── tools.py          # Function definitions for LLM
│   └── cli.py            # Command-line interface
├── scripts/              # CI/CD scripts
│   └── analyze_pull_request.py  # PR review bot
├── infra/                # Terraform (Azure)
│   ├── main.tf
│   ├── variables.tf
│   └── outputs.tf
├── .github/workflows/    # GitHub Actions
│   ├── ci.yml            # Lint, test, Docker, Snyk security
│   └── pull-request-review.yml  # AI code review
└── tests/                # Test suite
```

## Authentication

The API uses API key authentication to secure all `/v1/tickets` endpoints. This follows the [12-factor app](https://12factor.net/dev-prod-parity) principle of dev/prod parity by enforcing authentication in all environments.

**Implementation details:**
- `API_KEY` environment variable must be configured (server returns 500 if missing)
- Clients must include `X-API-Key` header with requests
- Uses `secrets.compare_digest` for constant-time comparison (timing attack protection)
- API key is cached at startup using `lru_cache` for performance
- Health check endpoint (`/`) remains publicly accessible

**Why API Key?**
- Simple to implement and use
- Sufficient for service-to-service communication
- Easy to rotate and manage
- Works well with the agent client architecture

**Alternative approaches for more complex scenarios:**
- **OAuth 2.0 / JWT**: For user-based authentication with token expiration
- **Azure AD / Entra ID**: For enterprise environments with SSO requirements
- **mTLS**: For high-security service mesh deployments
