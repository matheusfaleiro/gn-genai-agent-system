"""In-memory storage for tickets with thread safety."""

import threading
import uuid
from datetime import datetime
from typing import Optional

from api.models import Ticket, TicketCreate, TicketStatus, TicketUpdate


class TicketStorage:
    """Thread-safe in-memory storage for tickets."""

    def __init__(self):
        self._tickets: dict[str, Ticket] = {}
        self._lock = threading.RLock()

    def create(self, data: TicketCreate) -> Ticket:
        """Create a new ticket and return it."""
        with self._lock:
            ticket = Ticket(
                id=str(uuid.uuid4()),
                title=data.title,
                description=data.description,
                created=datetime.utcnow(),
                status=TicketStatus.OPEN,
            )
            self._tickets[ticket.id] = ticket
            return ticket

    def get(self, ticket_id: str) -> Optional[Ticket]:
        """Get a ticket by ID. Returns None if not found."""
        with self._lock:
            return self._tickets.get(ticket_id)

    def list_all(self, status: Optional[TicketStatus] = None) -> list[Ticket]:
        """List all tickets, optionally filtered by status."""
        with self._lock:
            tickets = list(self._tickets.values())
            if status:
                tickets = [t for t in tickets if t.status == status]
            return sorted(tickets, key=lambda t: t.created, reverse=True)

    def update(self, ticket_id: str, data: TicketUpdate) -> Optional[Ticket]:
        """Update a ticket. Returns None if not found."""
        with self._lock:
            ticket = self._tickets.get(ticket_id)
            if not ticket:
                return None

            update_fields = data.model_dump(exclude_unset=True)
            updated_ticket = ticket.model_copy(update=update_fields)
            self._tickets[ticket_id] = updated_ticket
            return updated_ticket

    def delete(self, ticket_id: str) -> bool:
        """Delete a ticket. Returns True if deleted, False if not found."""
        with self._lock:
            if ticket_id in self._tickets:
                del self._tickets[ticket_id]
                return True
            return False


# Global storage instance
storage = TicketStorage()
