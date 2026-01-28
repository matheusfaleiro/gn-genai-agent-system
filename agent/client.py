"""HTTP client for the Ticketing API."""

from __future__ import annotations

import logging
import os
from types import TracebackType

import httpx

from agent.types import ApiResponse

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "http://localhost:8000/v1"


class TicketingClient:
    """Client for interacting with the Ticketing API.

    Supports context manager protocol for proper resource cleanup.

    Example:
        with TicketingClient() as client:
            result = client.list_tickets()
    """

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
        api_key: str | None = None,
    ):
        self.base_url = base_url
        headers = {}
        # Use provided api_key or fall back to environment variable
        key = api_key or os.getenv("API_KEY")
        if key:
            headers["X-API-Key"] = key
        self.client = httpx.Client(timeout=timeout, headers=headers)
        logger.debug("Initialized client with base_url=%s", base_url)

    def __enter__(self) -> TicketingClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()

    def _handle_response(self, response: httpx.Response) -> ApiResponse:
        """Handle API response, returning structured result."""
        logger.debug("Response: %d %s", response.status_code, response.url)

        if response.status_code >= 400:
            try:
                error_detail = response.json().get("detail", response.text)
            except (ValueError, KeyError):
                error_detail = response.text

            logger.warning("API error: %d - %s", response.status_code, error_detail)
            return {
                "success": False,
                "status_code": response.status_code,
                "error": error_detail,
            }

        if response.status_code == 204:
            return {"success": True, "data": None}

        return {"success": True, "data": response.json()}

    def _request(
        self,
        method: str,
        path: str,
        **kwargs,
    ) -> ApiResponse:
        """Make an HTTP request with error handling."""
        url = f"{self.base_url}{path}"
        logger.debug("Request: %s %s", method, url)

        try:
            response = self.client.request(method, url, **kwargs)
            return self._handle_response(response)
        except httpx.ConnectError as e:
            logger.error("Connection failed: %s", e)
            return {
                "success": False,
                "status_code": None,
                "error": f"Failed to connect to API: {e}",
            }
        except httpx.TimeoutException as e:
            logger.error("Request timed out: %s", e)
            return {
                "success": False,
                "status_code": None,
                "error": f"Request timed out: {e}",
            }

    def create_ticket(self, title: str, description: str) -> ApiResponse:
        """Create a new ticket."""
        return self._request(
            "POST",
            "/tickets",
            json={"title": title, "description": description},
        )

    def list_tickets(self, status: str | None = None) -> ApiResponse:
        """List all tickets, optionally filtered by status."""
        params = {}
        if status:
            params["status"] = status
        return self._request("GET", "/tickets", params=params)

    def get_ticket(self, ticket_id: str) -> ApiResponse:
        """Get a specific ticket by ID."""
        return self._request("GET", f"/tickets/{ticket_id}")

    def update_ticket(
        self,
        ticket_id: str,
        title: str | None = None,
        description: str | None = None,
        status: str | None = None,
        resolution: str | None = None,
    ) -> ApiResponse:
        """Update an existing ticket."""
        data = {}
        if title is not None:
            data["title"] = title
        if description is not None:
            data["description"] = description
        if status is not None:
            data["status"] = status
        if resolution is not None:
            data["resolution"] = resolution

        return self._request("PATCH", f"/tickets/{ticket_id}", json=data)

    def delete_ticket(self, ticket_id: str) -> ApiResponse:
        """Delete a ticket."""
        return self._request("DELETE", f"/tickets/{ticket_id}")

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()
        logger.debug("Client closed")
