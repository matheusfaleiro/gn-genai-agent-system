#!/usr/bin/env python3
"""Analyze a PR diff using OpenAI and generate a review comment."""

import os
import sys
from openai import AzureOpenAI, OpenAI

SYSTEM_PROMPT = """You are a code reviewer. Analyze the provided git diff and provide a concise review.

Focus on:
1. Code quality and best practices
2. Potential bugs or issues
3. Security concerns
4. Performance considerations
5. Suggestions for improvement

Format your response as markdown with clear sections. Be constructive and specific.
Keep the review concise but thorough. If the changes look good, say so briefly.
"""

# Configuration via environment variables with defaults
MAX_DIFF_SIZE = int(os.getenv("MAX_DIFF_SIZE", "10000"))
MIN_DIFF_SIZE = int(os.getenv("MIN_DIFF_SIZE", "50"))

# Azure OpenAI settings
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-5-mini")
AZURE_API_VERSION = os.getenv("AZURE_API_VERSION", "2024-12-01-preview")

# Standard OpenAI settings (fallback)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")


def get_client():
    """Get the appropriate OpenAI client (Azure or standard)."""
    if AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY:
        return AzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_API_VERSION,
        ), AZURE_OPENAI_DEPLOYMENT
    elif OPENAI_API_KEY:
        return OpenAI(api_key=OPENAI_API_KEY), OPENAI_MODEL
    else:
        return None, None


def analyze_diff(diff_content: str) -> str:
    """Analyze the diff using OpenAI."""
    client, model = get_client()

    if not client:
        return "Error: No API credentials configured. Set AZURE_OPENAI_* or OPENAI_API_KEY."

    # Skip tiny changes
    if len(diff_content.strip()) < MIN_DIFF_SIZE:
        return "Changes are minimal - no detailed review needed."

    # Truncate very large diffs to avoid token limits
    if len(diff_content) > MAX_DIFF_SIZE:
        diff_content = diff_content[:MAX_DIFF_SIZE] + "\n\n... (diff truncated)"

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Please review the following changes:\n\n```diff\n{diff_content}\n```",
                },
            ],
        )

        return response.choices[0].message.content or "No review generated."

    except Exception as e:
        return f"Review could not be completed: {e}"


def main():
    if len(sys.argv) < 2:
        print("Usage: analyze_pull_request.py <diff_file>")
        sys.exit(1)

    diff_file = sys.argv[1]

    try:
        with open(diff_file, "r") as f:
            diff_content = f.read()
    except FileNotFoundError:
        print(f"Error: File {diff_file} not found")
        sys.exit(1)

    if not diff_content.strip():
        review = "No changes detected in this PR."
    else:
        review = analyze_diff(diff_content)

    comment = f"""## AI Code Review

{review}

---
*This review was generated automatically by the PR Review Bot.*
"""

    with open("review_comment.md", "w") as f:
        f.write(comment)

    print("Review generated successfully")
    print("-" * 40)
    print(comment)


if __name__ == "__main__":
    main()
