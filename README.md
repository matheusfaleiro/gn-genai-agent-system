# GenAI Agent System

End-to-end prototype of a fault-tolerant GenAI agent interacting with a mock ticketing API, including CI/CD automation and Azure infrastructure configs.

## Prerequisites

- Python 3.9+
- OpenAI API key or Azure OpenAI credentials
- Docker (optional, for containerized deployment)
- Terraform 1.5+ (optional, for infrastructure validation)

## Setup

```bash
# Clone the repository
git clone https://github.com/matheusfaleiro/gn-genai-agent-system.git
cd gn-genai-agent-system

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements-dev.txt
```

## Running the API

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`. Health check endpoint at `/`.

API endpoints (under `/v1`):
- `POST /v1/tickets` - Create a ticket
- `GET /v1/tickets` - List tickets (optional `?status=OPEN|RESOLVED|CLOSED` filter)
- `GET /v1/tickets/{id}` - Get ticket by ID
- `PATCH /v1/tickets/{id}` - Update ticket
- `DELETE /v1/tickets/{id}` - Delete ticket

## Running the Agent CLI

Set your API credentials:

```bash
# Option 1: OpenAI
export OPENAI_API_KEY=your-key

# Option 2: Azure OpenAI
export AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
export AZURE_OPENAI_API_KEY=your-key
```

Start the CLI (with the API running in another terminal):

```bash
python -m agent.cli
```

Example interactions:
- "Create a new ticket about a keyboard not working"
- "Retrieve all open tickets"
- "Get details for ticket [id]"
- "Update ticket [id] to have the status 'PROGRESS'" (agent explains invalid status)
- "Update ticket [id] to be RESOLVED with resolution 'Replaced faulty cable'"
- "Update ticket [non-existent-id] to CLOSED" (agent reports not found)

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
docker run -p 8000:8000 ticketing-api

# Or use docker-compose
docker-compose up
```

## Terraform

```bash
cd infra
terraform init -backend=false
terraform validate
terraform fmt -check
```

## Project Structure

```
├── api/                  # Mock Ticketing API
│   ├── v1/endpoints.py   # CRUD endpoints
│   ├── models.py         # Pydantic models
│   └── storage.py        # In-memory storage
├── agent/                # GenAI Agent
│   ├── agent.py          # Agent orchestration with OpenAI
│   ├── client.py         # HTTP client for API
│   ├── tools.py          # OpenAI function definitions
│   └── cli.py            # Command-line interface
├── scripts/              # CI/CD scripts
│   └── analyze_pull_request.py  # PR review bot
├── infra/                # Terraform (Azure)
│   ├── main.tf
│   ├── variables.tf
│   └── outputs.tf
├── .github/workflows/    # GitHub Actions
│   ├── ci.yml            # Lint, test, Docker, security
│   └── pull-request-review.yml  # AI code review
└── tests/                # Test suite
```

## Bonus: Adding Authentication to the API

To secure the API, I would implement **API Key authentication** as the simplest approach for this use case:

### Implementation

1. **Add an API key dependency** in FastAPI:

```python
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

API_KEY_HEADER = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str = Security(API_KEY_HEADER)) -> str:
    if api_key != os.getenv("API_KEY"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return api_key
```

2. **Protect endpoints** by adding the dependency:

```python
@router.post("/tickets", dependencies=[Depends(verify_api_key)])
async def create_ticket(...):
    ...
```

3. **Update the agent client** to include the API key in requests:

```python
self.client = httpx.Client(
    base_url=base_url,
    headers={"X-API-Key": os.getenv("API_KEY")}
)
```

### Why API Key?

- Simple to implement and use
- Sufficient for service-to-service communication
- Easy to rotate and manage
- Works well with the agent client architecture

### Alternative Approaches

For more complex scenarios:
- **OAuth 2.0 / JWT**: For user-based authentication with token expiration
- **Azure AD / Entra ID**: For enterprise environments with SSO requirements
- **mTLS**: For high-security service mesh deployments
