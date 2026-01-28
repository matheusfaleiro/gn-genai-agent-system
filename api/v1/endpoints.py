"""V1 API endpoints for ticket management.

This module defines the REST API endpoints for managing support tickets.
It provides create, read, update, and delete operations with proper
error handling and validation.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.auth import verify_api_key
from api.models import Ticket, TicketCreate, TicketStatus, TicketUpdate
from api.storage import storage

router = APIRouter(
    prefix="/tickets",
    tags=["tickets"],
    dependencies=[Depends(verify_api_key)],
)


@router.post("", response_model=Ticket, status_code=status.HTTP_201_CREATED)
async def create_ticket(data: TicketCreate):
    """Create a new ticket.

    Args:
        data: Ticket data with title and description.

    Returns:
        The created ticket with generated ID and timestamp.
    """
    return storage.create(data)


@router.get("", response_model=list[Ticket])
async def list_tickets(
    status: Optional[TicketStatus] = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
):
    """List all tickets with pagination.

    Args:
        status: Optional filter to return only tickets with this status.
        skip: Number of records to skip for pagination.
        limit: Maximum number of records to return (1-1000).

    Returns:
        List of tickets sorted by creation date (newest first).
    """
    return storage.list_all(status=status, skip=skip, limit=limit)


@router.get("/{ticket_id}", response_model=Ticket)
async def get_ticket(ticket_id: UUID):
    """Get a specific ticket by ID.

    Args:
        ticket_id: The unique identifier (UUID) of the ticket.

    Returns:
        The requested ticket.

    Raises:
        HTTPException: 404 if ticket not found.
    """
    ticket = storage.get(str(ticket_id))
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket with ID '{ticket_id}' not found",
        )
    return ticket


@router.patch("/{ticket_id}", response_model=Ticket)
async def update_ticket(ticket_id: UUID, data: TicketUpdate):
    """Update an existing ticket.

    Args:
        ticket_id: The unique identifier (UUID) of the ticket to update.
        data: Fields to update. Only provided fields are modified.

    Returns:
        The updated ticket.

    Raises:
        HTTPException: 404 if ticket not found.
        HTTPException: 422 if status is RESOLVED but no resolution provided.
    """
    ticket_id_str = str(ticket_id)
    existing = storage.get(ticket_id_str)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket with ID '{ticket_id}' not found",
        )

    # Business rule: resolution required when setting status to RESOLVED
    if data.status == TicketStatus.RESOLVED:
        has_new_resolution = data.resolution is not None
        has_existing_resolution = existing.resolution is not None
        if not has_new_resolution and not has_existing_resolution:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Resolution is required when setting status to RESOLVED",
            )

    return storage.update(ticket_id_str, data)


@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ticket(ticket_id: UUID):
    """Delete a ticket.

    Args:
        ticket_id: The unique identifier (UUID) of the ticket to delete.

    Raises:
        HTTPException: 404 if ticket not found.
    """
    if not storage.delete(str(ticket_id)):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket with ID '{ticket_id}' not found",
        )
    return None
