"""Pydantic models for the ticketing API."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TicketStatus(str, Enum):
    """Valid ticket statuses."""

    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class TicketCreate(BaseModel):
    """Request model for creating a ticket."""

    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=5000)


class TicketUpdate(BaseModel):
    """Request model for updating a ticket."""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=1, max_length=5000)
    status: Optional[TicketStatus] = None
    resolution: Optional[str] = Field(None, max_length=2000)


class Ticket(BaseModel):
    """Full ticket model."""

    id: str
    title: str
    description: str
    created: datetime
    status: TicketStatus = TicketStatus.OPEN
    resolution: Optional[str] = None
