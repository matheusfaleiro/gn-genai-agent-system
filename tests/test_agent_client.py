"""Tests for the agent HTTP client."""

from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from agent.client import TicketingClient
from api.auth import clear_api_key_cache
from api.storage import storage
from main import app

TEST_API_KEY = "test-api-key"


@pytest.fixture(autouse=True)
def clear_storage():
    """Clear storage before each test to ensure isolation."""
    storage._tickets.clear()
    yield
    storage._tickets.clear()


@pytest.fixture(autouse=True)
def set_api_key(monkeypatch):
    """Set API_KEY for all tests and clear cache."""
    clear_api_key_cache()
    monkeypatch.setenv("API_KEY", TEST_API_KEY)
    yield
    clear_api_key_cache()


@pytest.fixture
def api_client():
    """Create a test client for the API with auth header."""
    return TestClient(app, headers={"X-API-Key": TEST_API_KEY})


@pytest.fixture
def agent_client(api_client):
    """Create an agent client that uses the test server."""
    # Use the test client's base URL
    with TicketingClient(base_url="http://testserver/v1", api_key=TEST_API_KEY) as client:
        # Patch the httpx client to use the test client
        client.client = api_client
        yield client


class TestTicketingClient:
    """Tests for the TicketingClient."""

    def test_create_ticket_success(self, agent_client):
        """Should successfully create a ticket."""
        result = agent_client.create_ticket(
            title="Test ticket",
            description="Test description",
        )
        assert result["success"] is True
        assert result["data"]["title"] == "Test ticket"
        assert result["data"]["status"] == "OPEN"

    def test_list_tickets_empty(self, agent_client):
        """Should return empty list when no tickets exist."""
        result = agent_client.list_tickets()
        assert result["success"] is True
        assert result["data"] == []

    def test_list_tickets_with_filter(self, agent_client):
        """Should filter tickets by status."""
        # Create a ticket
        agent_client.create_ticket(title="Test", description="Test")

        # Filter by OPEN should return it
        result = agent_client.list_tickets(status="OPEN")
        assert result["success"] is True
        assert len(result["data"]) == 1

        # Filter by CLOSED should return empty
        result = agent_client.list_tickets(status="CLOSED")
        assert result["success"] is True
        assert len(result["data"]) == 0

    def test_get_ticket_success(self, agent_client):
        """Should retrieve a ticket by ID."""
        create_result = agent_client.create_ticket(title="Test", description="Test")
        ticket_id = create_result["data"]["id"]

        result = agent_client.get_ticket(ticket_id)
        assert result["success"] is True
        assert result["data"]["id"] == ticket_id

    def test_get_ticket_not_found(self, agent_client):
        """Should return error for non-existent ticket."""
        result = agent_client.get_ticket("00000000-0000-0000-0000-000000000000")
        assert result["success"] is False
        assert result["status_code"] == 404
        assert "not found" in result["error"].lower()

    def test_update_ticket_success(self, agent_client):
        """Should update a ticket."""
        create_result = agent_client.create_ticket(title="Original", description="Test")
        ticket_id = create_result["data"]["id"]

        result = agent_client.update_ticket(ticket_id, title="Updated")
        assert result["success"] is True
        assert result["data"]["title"] == "Updated"

    def test_update_ticket_invalid_status(self, agent_client):
        """Should return error for invalid status."""
        create_result = agent_client.create_ticket(title="Test", description="Test")
        ticket_id = create_result["data"]["id"]

        result = agent_client.update_ticket(ticket_id, status="INVALID")
        assert result["success"] is False
        assert result["status_code"] == 422

    def test_update_ticket_resolved_without_resolution(self, agent_client):
        """Should return error when resolving without resolution note."""
        create_result = agent_client.create_ticket(title="Test", description="Test")
        ticket_id = create_result["data"]["id"]

        result = agent_client.update_ticket(ticket_id, status="RESOLVED")
        assert result["success"] is False
        assert result["status_code"] == 422
        assert "resolution" in result["error"].lower()

    def test_update_ticket_resolved_with_resolution(self, agent_client):
        """Should successfully resolve with resolution note."""
        create_result = agent_client.create_ticket(title="Test", description="Test")
        ticket_id = create_result["data"]["id"]

        result = agent_client.update_ticket(ticket_id, status="RESOLVED", resolution="Fixed it")
        assert result["success"] is True
        assert result["data"]["status"] == "RESOLVED"
        assert result["data"]["resolution"] == "Fixed it"

    def test_delete_ticket_success(self, agent_client):
        """Should delete a ticket."""
        create_result = agent_client.create_ticket(title="Test", description="Test")
        ticket_id = create_result["data"]["id"]

        result = agent_client.delete_ticket(ticket_id)
        assert result["success"] is True

        # Verify it's gone
        get_result = agent_client.get_ticket(ticket_id)
        assert get_result["success"] is False
        assert get_result["status_code"] == 404

    def test_delete_ticket_not_found(self, agent_client):
        """Should return error when deleting a non-existent ticket."""
        result = agent_client.delete_ticket("00000000-0000-0000-0000-000000000000")
        assert result["success"] is False
        assert result["status_code"] == 404

    def test_update_ticket_description(self, agent_client):
        """Should update ticket description."""
        create_result = agent_client.create_ticket(title="Test", description="Original")
        ticket_id = create_result["data"]["id"]

        result = agent_client.update_ticket(ticket_id, description="Updated description")
        assert result["success"] is True
        assert result["data"]["description"] == "Updated description"


class TestTicketingClientContextManager:
    """Tests for context manager support."""

    def test_context_manager_closes_client(self):
        """Should close client when exiting context."""
        with TicketingClient() as client:
            assert client.client is not None
        # After exit, a client should be closed
        assert client.client.is_closed


class TestTicketingClientErrorHandling:
    """Tests for error handling edge cases."""

    def test_connection_error(self):
        """Should handle connection errors gracefully."""
        with TicketingClient(base_url="http://localhost:9999") as client:
            with patch.object(
                client.client, "request", side_effect=httpx.ConnectError("Connection refused")
            ):
                result = client.list_tickets()

        assert result["success"] is False
        assert result["status_code"] is None
        assert "Failed to connect" in result["error"]

    def test_timeout_error(self):
        """Should handle timeout errors gracefully."""
        with TicketingClient() as client:
            with patch.object(
                client.client, "request", side_effect=httpx.TimeoutException("Request timed out")
            ):
                result = client.list_tickets()

        assert result["success"] is False
        assert result["status_code"] is None
        assert "timed out" in result["error"]

    def test_non_json_error_response(self):
        """Should handle non-JSON error responses."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.json.side_effect = ValueError("No JSON")

        with TicketingClient() as client:
            with patch.object(client.client, "request", return_value=mock_response):
                result = client.list_tickets()

        assert result["success"] is False
        assert result["status_code"] == 500
        assert result["error"] == "Internal Server Error"
