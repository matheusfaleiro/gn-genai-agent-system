"""OpenAI function tool definitions for the Ticketing API."""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_ticket",
            "description": "Create a new support ticket in the system",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Brief summary of the issue (max 200 characters)",
                    },
                    "description": {
                        "type": "string",
                        "description": "Detailed explanation of the problem",
                    },
                },
                "required": ["title", "description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_tickets",
            "description": "List all tickets, optionally filtered by status",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["OPEN", "RESOLVED", "CLOSED"],
                        "description": "Filter tickets by status (optional)",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_ticket",
            "description": "Get details of a specific ticket by its ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticket_id": {
                        "type": "string",
                        "description": "The unique identifier (UUID) of the ticket",
                    },
                },
                "required": ["ticket_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_ticket",
            "description": "Update an existing ticket's title, description, status, or resolution.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticket_id": {
                        "type": "string",
                        "description": "The unique identifier (UUID) of the ticket to update",
                    },
                    "title": {
                        "type": "string",
                        "description": "New title for the ticket (optional)",
                    },
                    "description": {
                        "type": "string",
                        "description": "New description for the ticket (optional)",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["OPEN", "RESOLVED", "CLOSED"],
                        "description": "New status: OPEN, RESOLVED, or CLOSED",
                    },
                    "resolution": {
                        "type": "string",
                        "description": "Resolution notes (required when status is RESOLVED)",
                    },
                },
                "required": ["ticket_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_ticket",
            "description": "Delete a ticket from the system",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticket_id": {
                        "type": "string",
                        "description": "The unique identifier (UUID) of the ticket to delete",
                    },
                },
                "required": ["ticket_id"],
            },
        },
    },
]
