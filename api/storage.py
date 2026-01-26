"""In-memory storage for tickets with thread safety.

This module provides a simple storage layer that keeps tickets in memory.
All operations are thread-safe, suitable for concurrent API requests.
"""

import threading
import uuid
from datetime import datetime, timezone
from typing import Optional

from api.models import Ticket, TicketCreate, TicketStatus, TicketUpdate


class TicketStorage:
    """Thread-safe in-memory storage for tickets.

    Uses a dictionary to store tickets and RLock for thread safety.
    Data is lost when the application restarts.

    Attributes:
        _tickets: Internal dictionary mapping ticket IDs to Ticket objects.
        _lock: Reentrant lock for thread-safe operations.
    """

    def __init__(self):
        """Initialize empty storage with a lock."""
        self._tickets: dict[str, Ticket] = {}
        self._lock = threading.RLock()

    def create(self, data: TicketCreate) -> Ticket:
        """Create a new ticket.

        Args:
            data: Ticket creation data with title and description.

        Returns:
            The created ticket with generated ID and timestamp.
        """
        with self._lock:
            ticket = Ticket(
                id=uuid.uuid4(),
                title=data.title,
                description=data.description,
                created=datetime.now(timezone.utc),
                status=TicketStatus.OPEN,
            )
            self._tickets[str(ticket.id)] = ticket
            return ticket

    def get(self, ticket_id: str) -> Optional[Ticket]:
        """Get a ticket by ID.

        Args:
            ticket_id: The unique identifier of the ticket.

        Returns:
            A copy of the ticket if found, None otherwise.
        """
        with self._lock:
            ticket = self._tickets.get(ticket_id)
            return ticket.model_copy() if ticket else None

    def list_all(self, status: Optional[TicketStatus] = None) -> list[Ticket]:
        """List all tickets, optionally filtered by status.

        Args:
            status: If provided, only return tickets with this status.

        Returns:
            List of ticket copies sorted by creation date (newest first).
        """
        with self._lock:
            tickets = list(self._tickets.values())
            if status:
                tickets = [t for t in tickets if t.status == status]
            sorted_tickets = sorted(tickets, key=lambda t: t.created, reverse=True)
            return [t.model_copy() for t in sorted_tickets]

    def update(self, ticket_id: str, data: TicketUpdate) -> Optional[Ticket]:
        """Update an existing ticket.

        Args:
            ticket_id: The unique identifier of the ticket to update.
            data: Fields to update. Only provided fields are modified.

        Returns:
            The updated ticket if found, None otherwise.
        """
        with self._lock:
            ticket = self._tickets.get(ticket_id)
            if not ticket:
                return None

            update_fields = data.model_dump(exclude_unset=True)
            updated_ticket = ticket.model_copy(update=update_fields)
            self._tickets[ticket_id] = updated_ticket
            return updated_ticket.model_copy()

    def delete(self, ticket_id: str) -> bool:
        """Delete a ticket.

        Args:
            ticket_id: The unique identifier of the ticket to delete.

        Returns:
            True if the ticket was deleted, False if not found.
        """
        with self._lock:
            if ticket_id in self._tickets:
                del self._tickets[ticket_id]
                return True
            return False


# Global storage instance
storage = TicketStorage()
