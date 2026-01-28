#!/usr/bin/env python3
"""Command-line interface for the Ticketing Agent."""

from __future__ import annotations

import itertools
import logging
import os
import sys
import threading
import time

from agent.agent import TicketingAgent


class Spinner:
    """A simple CLI spinner for loading states."""

    def __init__(self, message: str = "Thinking"):
        self.message = message
        self.frames = itertools.cycle(["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"])
        self.running = False
        self.thread: threading.Thread | None = None

    def _spin(self) -> None:
        while self.running:
            frame = next(self.frames)
            print(f"\r{frame} {self.message}...", end="", flush=True)
            time.sleep(0.1)

    def start(self) -> None:
        self.running = True
        self.thread = threading.Thread(target=self._spin, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.running = False
        if self.thread:
            self.thread.join()
        print("\r" + " " * (len(self.message) + 10) + "\r", end="", flush=True)


HELP_TEXT = """
Available Commands:
  help   - Show this help message
  reset  - Clear conversation history
  quit   - Exit the CLI

Example Requests:
  "Create a ticket about my keyboard not working"
  "List all open tickets"
  "Get details for ticket <id>"
  "Update ticket <id> to RESOLVED with resolution 'Replaced keyboard'"
  "Delete ticket <id>"

Valid Ticket Statuses: OPEN, RESOLVED, CLOSED
"""


def setup_logging() -> None:
    """Configure logging based on environment."""
    level = os.getenv("LOG_LEVEL", "WARNING").upper()
    logging.basicConfig(
        level=getattr(logging, level, logging.WARNING),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def print_banner(api_url: str) -> None:
    """Print the CLI banner."""
    print("=" * 60)
    print("  Ticketing Agent CLI")
    print("=" * 60)
    print(f"API URL: {api_url}")
    print("\nType your requests in natural language.")
    print("Type 'help' for available commands and examples.")
    print("=" * 60)


def main() -> None:
    """Run the interactive CLI for the Ticketing Agent."""
    setup_logging()
    logger = logging.getLogger(__name__)

    api_url = os.getenv("API_BASE_URL", "http://localhost:8000/v1")

    print_banner(api_url)

    try:
        agent = TicketingAgent(api_base_url=api_url)
    except ValueError as e:
        print(f"\nError: {e}")
        print("\nPlease set one of the following environment variables:")
        print("  - AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY")
        print("  - OPENAI_API_KEY")
        sys.exit(1)

    print("\nAgent ready. How can I help you today?\n")

    try:
        while True:
            try:
                user_input = input("You: ").strip()
            except EOFError:
                break

            if not user_input:
                continue

            command = user_input.lower()

            if command == "quit":
                print("\nGoodbye!")
                break

            if command == "help":
                print(HELP_TEXT)
                continue

            if command == "reset":
                agent.reset_conversation()
                print("\nConversation history cleared.\n")
                continue

            spinner = Spinner("Thinking")
            try:
                spinner.start()
                response = agent.chat(user_input)
            except Exception as e:
                logger.exception("Error during chat")
                print(f"\nError: {e}\n")
            else:
                print(f"\nAgent: {response}\n")
            finally:
                spinner.stop()

    except KeyboardInterrupt:
        print("\n\nGoodbye!")
    finally:
        agent.close()


if __name__ == "__main__":
    main()
