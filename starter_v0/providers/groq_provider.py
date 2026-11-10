from __future__ import annotations

import os

from providers.openai_provider import OpenAIProvider


class GroqProvider(OpenAIProvider):
    """Groq's OpenAI-compatible Chat Completions API."""

    def __init__(self) -> None:
        api_key_env = "GROQ_API_KEY"
        api_key_default = os.getenv(api_key_env) or os.getenv("GROUQ_API_KEY")
        super().__init__(
            api_key_env=api_key_env,
            api_key_default=api_key_default,
            base_url="https://api.groq.com/openai/v1",
            default_model=os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
        )
