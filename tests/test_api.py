"""Tests for the ticketing API."""

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.storage import storage


@pytest.fixture(autouse=True)
def clear_storage():
    """Clear storage before each test to ensure isolation."""
    storage._tickets.clear()
    yield
    storage._tickets.clear()


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def sample_ticket(client):
    """Create a sample ticket for testing and return its JSON."""
    response = client.post(
        "/tickets", json={"title": "Test ticket", "description": "Test description"}
    )
    return response.json()


class TestHealthCheck:
    """Tests for the health check endpoint."""

    def test_health_check_returns_200_ok(self, client):
        """Should return 200 OK and healthy status."""
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestCreateTicket:
    """Tests for ticket creation."""

    def test_create_ticket_valid_payload_returns_201_created(self, client):
        """Should create a ticket successfully when payload is valid."""
        response = client.post(
            "/tickets",
            json={"title": "Keyboard broken", "description": "My keyboard stopped working"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Keyboard broken"
        assert data["status"] == "OPEN"
        assert data["id"] is not None

    def test_create_ticket_missing_required_field_returns_422(self, client):
        """Should return 422 Unprocessable Entity when title is missing."""
        response = client.post("/tickets", json={"description": "Missing title"})
        assert response.status_code == 422

    def test_create_ticket_empty_string_title_returns_422(self, client):
        """Should return 422 Unprocessable Entity when title is an empty string."""
        response = client.post("/tickets", json={"title": "", "description": "Empty title"})
        assert response.status_code == 422


class TestListTickets:
    """Tests for listing tickets."""

    def test_list_tickets_empty_db_returns_empty_list(self, client):
        """Should return an empty list when no tickets exist in storage."""
        response = client.get("/tickets")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_tickets_populated_db_returns_all_records(self, client, sample_ticket):
        """Should return all existing tickets when no filter is applied."""
        response = client.get("/tickets")
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_list_tickets_filter_query_param_returns_matching_subset(self, client, sample_ticket):
        """Should filter tickets correctly when status query parameter is provided."""
        # Test positive match
        response = client.get("/tickets?status=OPEN")
        assert response.status_code == 200
        assert len(response.json()) == 1

        # Test negative match
        response = client.get("/tickets?status=CLOSED")
        assert response.status_code == 200
        assert len(response.json()) == 0


class TestGetTicket:
    """Tests for getting a single ticket."""

    def test_get_ticket_valid_id_returns_200_ok(self, client, sample_ticket):
        """Should return the correct ticket data when ID exists."""
        ticket_id = sample_ticket["id"]
        response = client.get(f"/tickets/{ticket_id}")
        assert response.status_code == 200
        assert response.json()["id"] == ticket_id

    def test_get_ticket_non_existent_id_returns_404(self, client):
        """Should return 404 Not Found when the ticket ID does not exist."""
        non_existent_uuid = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/tickets/{non_existent_uuid}")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_get_ticket_invalid_uuid_returns_422(self, client):
        """Should return 422 when ticket ID is not a valid UUID."""
        response = client.get("/tickets/invalid-id")
        assert response.status_code == 422


class TestUpdateTicket:
    """Tests for updating tickets."""

    def test_update_ticket_valid_partial_update_returns_200_ok(self, client, sample_ticket):
        """Should successfully update specific fields (patch) and return 200."""
        ticket_id = sample_ticket["id"]
        response = client.put(f"/tickets/{ticket_id}", json={"title": "Updated title"})
        assert response.status_code == 200
        assert response.json()["title"] == "Updated title"

    def test_update_ticket_non_existent_id_returns_404(self, client):
        """Should return 404 Not Found when trying to update a missing ticket."""
        non_existent_uuid = "00000000-0000-0000-0000-000000000000"
        response = client.put(f"/tickets/{non_existent_uuid}", json={"title": "New title"})
        assert response.status_code == 404

    def test_update_ticket_invalid_uuid_returns_422(self, client):
        """Should return 422 when ticket ID is not a valid UUID."""
        response = client.put("/tickets/invalid-id", json={"title": "New title"})
        assert response.status_code == 422

    def test_update_ticket_invalid_status_enum_returns_422(self, client, sample_ticket):
        """Should return 422 when status is not one of the allowed enum values."""
        ticket_id = sample_ticket["id"]
        response = client.put(f"/tickets/{ticket_id}", json={"status": "INVALID"})
        assert response.status_code == 422

    def test_update_resolved_without_resolution_returns_422(self, client, sample_ticket):
        """Should return 422 when status is set to RESOLVED without a resolution note."""
        ticket_id = sample_ticket["id"]
        response = client.put(f"/tickets/{ticket_id}", json={"status": "RESOLVED"})
        assert response.status_code == 422
        assert "Resolution is required" in response.json()["detail"]

    def test_update_ticket_status_resolved_with_note_returns_200(self, client, sample_ticket):
        """Should return 200 OK when resolving a ticket with the required resolution note."""
        ticket_id = sample_ticket["id"]
        response = client.put(
            f"/tickets/{ticket_id}", json={"status": "RESOLVED", "resolution": "Fixed the issue"}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "RESOLVED"
        assert response.json()["resolution"] == "Fixed the issue"


class TestDeleteTicket:
    """Tests for deleting tickets."""

    def test_delete_ticket_existing_id_returns_204_no_content(self, client, sample_ticket):
        """Should delete an existing ticket and return 204 No Content."""
        ticket_id = sample_ticket["id"]
        response = client.delete(f"/tickets/{ticket_id}")
        assert response.status_code == 204

        # Verify it's gone
        response = client.get(f"/tickets/{ticket_id}")
        assert response.status_code == 404

    def test_delete_ticket_non_existent_id_returns_404(self, client):
        """Should return 404 Not Found when trying to delete a missing ticket."""
        non_existent_uuid = "00000000-0000-0000-0000-000000000000"
        response = client.delete(f"/tickets/{non_existent_uuid}")
        assert response.status_code == 404

    def test_delete_ticket_invalid_uuid_returns_422(self, client):
        """Should return 422 when ticket ID is not a valid UUID."""
        response = client.delete("/tickets/invalid-id")
        assert response.status_code == 422
