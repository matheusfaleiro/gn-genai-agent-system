"""Agent orchestration for interacting with the Ticketing API."""

from __future__ import annotations

import json
import logging
import os
from typing import TYPE_CHECKING

from openai import AzureOpenAI, OpenAI

from agent.client import TicketingClient
from agent.tools import TOOLS

if TYPE_CHECKING:
    from openai import OpenAI as OpenAIClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a helpful support ticket assistant. You help users \
manage their support tickets by creating, viewing, updating, and deleting them.

When users ask about tickets, use the available tools to interact with the \
ticketing system. Always provide clear, helpful responses based on the results.

If an operation fails (e.g., ticket not found, invalid status), explain the \
error clearly to the user and suggest what they can do instead.

Valid ticket statuses are: OPEN, RESOLVED, CLOSED. If a user tries to use an \
invalid status, inform them of the valid options.

When resolving a ticket (setting status to RESOLVED), a resolution note \
explaining how the issue was fixed is required.
"""

MAX_TOOL_ITERATIONS = 10
MAX_MESSAGE_HISTORY = 50


class TicketingAgent:
    """Agent that uses OpenAI function calling to interact with the Ticketing API."""

    def __init__(self, api_base_url: str = "http://localhost:8000/v1"):
        self.client = TicketingClient(base_url=api_base_url)
        self.openai_client, self.model = self._get_openai_client()
        self.messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
        logger.info("Agent initialized with model=%s", self.model)

    def _get_openai_client(self) -> tuple[OpenAIClient, str]:
        """Get the appropriate OpenAI client (Azure or standard)."""
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        azure_key = os.getenv("AZURE_OPENAI_API_KEY")
        azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-5-mini")
        azure_version = os.getenv("AZURE_API_VERSION", "2024-12-01-preview")

        openai_key = os.getenv("OPENAI_API_KEY")
        openai_model = os.getenv("OPENAI_MODEL", "gpt-4")

        if azure_endpoint and azure_key:
            logger.info("Using Azure OpenAI: %s", azure_endpoint)
            return (
                AzureOpenAI(
                    azure_endpoint=azure_endpoint,
                    api_key=azure_key,
                    api_version=azure_version,
                ),
                azure_deployment,
            )
        elif openai_key:
            logger.info("Using OpenAI API")
            return OpenAI(api_key=openai_key), openai_model
        else:
            raise ValueError(
                "No API credentials configured. "
                "Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY, "
                "or OPENAI_API_KEY."
            )

    def _execute_tool(self, tool_name: str, arguments: dict) -> str:
        """Execute a tool and return the result as a string."""
        logger.debug("Executing tool: %s with args: %s", tool_name, arguments)

        if tool_name == "create_ticket":
            result = self.client.create_ticket(
                title=arguments["title"],
                description=arguments["description"],
            )
        elif tool_name == "list_tickets":
            result = self.client.list_tickets(status=arguments.get("status"))
        elif tool_name == "get_ticket":
            result = self.client.get_ticket(ticket_id=arguments["ticket_id"])
        elif tool_name == "update_ticket":
            result = self.client.update_ticket(
                ticket_id=arguments["ticket_id"],
                title=arguments.get("title"),
                description=arguments.get("description"),
                status=arguments.get("status"),
                resolution=arguments.get("resolution"),
            )
        elif tool_name == "delete_ticket":
            result = self.client.delete_ticket(ticket_id=arguments["ticket_id"])
        else:
            logger.error("Unknown tool: %s", tool_name)
            result = {"success": False, "error": f"Unknown tool: {tool_name}"}

        logger.debug("Tool result: %s", result)
        return json.dumps(result, indent=2, default=str)

    def _trim_message_history(self) -> None:
        """Trim message history to prevent unbounded growth."""
        if len(self.messages) > MAX_MESSAGE_HISTORY:
            # Keep system message and recent messages
            system_msg = self.messages[0]
            recent_msgs = self.messages[-(MAX_MESSAGE_HISTORY - 1) :]
            self.messages = [system_msg] + recent_msgs
            logger.debug("Trimmed message history to %d messages", len(self.messages))

    def chat(self, user_message: str) -> str:
        """Process a user message and return the agent's response."""
        self.messages.append({"role": "user", "content": user_message})
        logger.debug("User message: %s", user_message[:100])

        iterations = 0
        while iterations < MAX_TOOL_ITERATIONS:
            iterations += 1
            logger.debug("Iteration %d/%d", iterations, MAX_TOOL_ITERATIONS)

            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                tools=TOOLS,
            )

            message = response.choices[0].message

            if message.tool_calls:
                self.messages.append(message)

                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)

                    tool_result = self._execute_tool(tool_name, arguments)

                    self.messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": tool_result,
                        }
                    )
            else:
                self.messages.append(message)
                self._trim_message_history()
                return message.content or ""

        logger.warning("Max iterations reached, returning partial response")
        self._trim_message_history()
        return "I apologize, but I was unable to complete the request. Please try again."

    def reset_conversation(self) -> None:
        """Reset the conversation history."""
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        logger.info("Conversation reset")

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()
        logger.debug("Agent closed")
