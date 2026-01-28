"""Application configuration.

This module loads environment variables from .env files for local development.
Import this module first in entry points (main.py, cli.py) before other imports.

For production, use a secrets manager (e.g., Azure Key Vault) instead of .env files.
"""

from dotenv import load_dotenv

# Load .env file if present. override=False ensures existing env vars take precedence.
load_dotenv(override=False)
