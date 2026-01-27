"""Tests for the agent orchestration."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from agent.agent import MAX_MESSAGE_HISTORY, MAX_TOOL_ITERATIONS, SYSTEM_PROMPT


class TestTicketingAgentInit:
    """Tests for agent initialization."""

    def test_init_fails_without_credentials(self):
        """Should raise an error when no API credentials are set."""
        with patch.dict(
            "os.environ",
            {
                "AZURE_OPENAI_ENDPOINT": "",
                "AZURE_OPENAI_API_KEY": "",
                "OPENAI_API_KEY": "",
            },
            clear=True,
        ):
            from agent.agent import TicketingAgent

            with pytest.raises(ValueError, match="No API credentials"):
                TicketingAgent()

    def test_init_with_openai_credentials(self):
        """Should initialize with OpenAI credentials."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=True):
            with patch("agent.agent.OpenAI") as mock_openai:
                from agent.agent import TicketingAgent

                agent = TicketingAgent()
                mock_openai.assert_called_once_with(api_key="test-key")
                agent.close()

    def test_init_with_azure_credentials(self):
        """Should initialize with Azure OpenAI credentials."""
        with patch.dict(
            "os.environ",
            {
                "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
                "AZURE_OPENAI_API_KEY": "test-key",
            },
            clear=True,
        ):
            with patch("agent.agent.AzureOpenAI") as mock_azure:
                from agent.agent import TicketingAgent

                agent = TicketingAgent()
                mock_azure.assert_called_once()
                agent.close()


class TestTicketingAgentChat:
    """Tests for agent chat functionality."""

    @pytest.fixture
    def mock_agent(self):
        """Create an agent with a mocked OpenAI client."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=True):
            with patch("agent.agent.OpenAI") as mock_openai:
                mock_client = MagicMock()
                mock_openai.return_value = mock_client

                from agent.agent import TicketingAgent

                agent = TicketingAgent()
                yield agent, mock_client
                agent.close()

    def test_chat_returns_response(self, mock_agent):
        """Should return response from OpenAI."""
        agent, mock_client = mock_agent

        mock_message = MagicMock()
        mock_message.tool_calls = None
        mock_message.content = "Hello! How can I help you?"

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=mock_message)]

        mock_client.chat.completions.create.return_value = mock_response

        result = agent.chat("Hello")

        assert result == "Hello! How can I help you?"
        assert len(agent.messages) == 3  # system + user + assistant

    def test_chat_executes_tool_calls(self, mock_agent):
        """Should execute tool calls and return a final response."""
        agent, mock_client = mock_agent

        mock_tool_call = MagicMock()
        mock_tool_call.id = "call_123"
        mock_tool_call.function.name = "list_tickets"
        mock_tool_call.function.arguments = "{}"

        mock_tool_message = MagicMock()
        mock_tool_message.tool_calls = [mock_tool_call]
        mock_tool_message.content = None

        mock_final_message = MagicMock()
        mock_final_message.tool_calls = None
        mock_final_message.content = "Here are your tickets."

        mock_client.chat.completions.create.side_effect = [
            MagicMock(choices=[MagicMock(message=mock_tool_message)]),
            MagicMock(choices=[MagicMock(message=mock_final_message)]),
        ]

        with patch.object(agent.client, "list_tickets") as mock_list:
            mock_list.return_value = {"success": True, "data": []}
            result = agent.chat("List my tickets")

        assert result == "Here are your tickets."
        mock_list.assert_called_once()

    def test_chat_stops_after_max_iterations(self, mock_agent):
        """Should stop after max tool iterations."""
        agent, mock_client = mock_agent

        mock_tool_call = MagicMock()
        mock_tool_call.id = "call_123"
        mock_tool_call.function.name = "list_tickets"
        mock_tool_call.function.arguments = "{}"

        mock_tool_message = MagicMock()
        mock_tool_message.tool_calls = [mock_tool_call]

        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=mock_tool_message)]
        )

        with patch.object(agent.client, "list_tickets") as mock_list:
            mock_list.return_value = {"success": True, "data": []}
            result = agent.chat("List my tickets")

        assert "unable to complete" in result.lower()
        assert mock_list.call_count == MAX_TOOL_ITERATIONS

    def test_reset_conversation(self, mock_agent):
        """Should reset conversation to the initial state."""
        agent, mock_client = mock_agent

        agent.messages.append({"role": "user", "content": "test"})
        agent.reset_conversation()

        assert len(agent.messages) == 1
        assert agent.messages[0]["role"] == "system"
        assert agent.messages[0]["content"] == SYSTEM_PROMPT


class TestTicketingAgentTools:
    """Tests for tool execution."""

    @pytest.fixture
    def mock_agent(self):
        """Create an agent with a mocked OpenAI client."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=True):
            with patch("agent.agent.OpenAI"):
                from agent.agent import TicketingAgent

                agent = TicketingAgent()
                yield agent
                agent.close()

    def test_execute_create_ticket(self, mock_agent):
        """Should execute create_ticket tool."""
        with patch.object(mock_agent.client, "create_ticket") as mock_create:
            mock_create.return_value = {"success": True, "data": {"id": "123"}}
            result = mock_agent._execute_tool(
                "create_ticket",
                {"title": "Test", "description": "Test desc"},
            )

        assert "success" in result
        mock_create.assert_called_once_with(title="Test", description="Test desc")

    def test_execute_list_tickets(self, mock_agent):
        """Should execute list_tickets tool."""
        with patch.object(mock_agent.client, "list_tickets") as mock_list:
            mock_list.return_value = {"success": True, "data": []}
            result = mock_agent._execute_tool("list_tickets", {"status": "OPEN"})

        assert "success" in result
        mock_list.assert_called_once_with(status="OPEN")

    def test_execute_get_ticket(self, mock_agent):
        """Should execute get_ticket tool."""
        with patch.object(mock_agent.client, "get_ticket") as mock_get:
            mock_get.return_value = {"success": True, "data": {"id": "123"}}
            result = mock_agent._execute_tool("get_ticket", {"ticket_id": "123"})

        assert "success" in result
        mock_get.assert_called_once_with(ticket_id="123")

    def test_execute_update_ticket(self, mock_agent):
        """Should execute update_ticket tool."""
        with patch.object(mock_agent.client, "update_ticket") as mock_update:
            mock_update.return_value = {"success": True, "data": {"id": "123"}}
            result = mock_agent._execute_tool(
                "update_ticket",
                {"ticket_id": "123", "status": "RESOLVED", "resolution": "Fixed"},
            )

        assert "success" in result
        mock_update.assert_called_once()

    def test_execute_delete_ticket(self, mock_agent):
        """Should execute delete_ticket tool."""
        with patch.object(mock_agent.client, "delete_ticket") as mock_delete:
            mock_delete.return_value = {"success": True, "data": None}
            result = mock_agent._execute_tool("delete_ticket", {"ticket_id": "123"})

        assert "success" in result
        mock_delete.assert_called_once_with(ticket_id="123")

    def test_execute_unknown_tool(self, mock_agent):
        """Should return error for an unknown tool."""
        result = mock_agent._execute_tool("unknown_tool", {})

        assert "Unknown tool" in result


class TestMessageHistoryTrimming:
    """Tests for message history management."""

    @pytest.fixture
    def mock_agent(self):
        """Create an agent with a mocked OpenAI client."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=True):
            with patch("agent.agent.OpenAI"):
                from agent.agent import TicketingAgent

                agent = TicketingAgent()
                yield agent
                agent.close()

    def test_trim_message_history(self, mock_agent):
        """Should trim message history when exceeding max."""
        for i in range(MAX_MESSAGE_HISTORY + 10):
            mock_agent.messages.append({"role": "user", "content": f"message {i}"})

        mock_agent._trim_message_history()

        assert len(mock_agent.messages) == MAX_MESSAGE_HISTORY
        assert mock_agent.messages[0]["role"] == "system"
