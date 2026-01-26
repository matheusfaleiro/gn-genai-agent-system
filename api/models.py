"""Pydantic models for the ticketing API.

This module defines the data structures used throughout the ticketing system,
including request/response models and enumerations for ticket status.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TicketStatus(str, Enum):
    """Valid ticket statuses.

    Attributes:
        OPEN: Ticket is active and awaiting resolution.
        RESOLVED: Issue has been fixed, resolution notes required.
        CLOSED: Ticket is complete and archived.
    """

    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class TicketCreate(BaseModel):
    """Request model for creating a new ticket.

    Attributes:
        title: Brief summary of the issue (1-200 characters).
        description: Detailed explanation of the problem (1-5000 characters).
    """

    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=5000)


class TicketUpdate(BaseModel):
    """Request model for updating an existing ticket.

    All fields are optional, allowing partial updates. Only provided
    fields will be modified.

    Attributes:
        title: New title for the ticket.
        description: New description for the ticket.
        status: New status (OPEN, RESOLVED, or CLOSED).
        resolution: Resolution notes, required when status is RESOLVED.
    """

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=1, max_length=5000)
    status: Optional[TicketStatus] = None
    resolution: Optional[str] = Field(None, max_length=2000)


class Ticket(BaseModel):
    """Complete ticket model representing a support ticket.

    Attributes:
        id: Unique identifier (UUID).
        title: Brief summary of the issue.
        description: Detailed explanation of the problem.
        created: Timestamp when the ticket was created.
        status: Current status of the ticket.
        resolution: Notes explaining how the issue was resolved.
    """

    id: str
    title: str
    description: str
    created: datetime
    status: TicketStatus = TicketStatus.OPEN
    resolution: Optional[str] = None
