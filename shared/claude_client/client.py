import os
from anthropic import Anthropic
from anthropic.types import TextBlock

DEFAULT_MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 4096


class ClaudeClient:
    def __init__(self, model: str = DEFAULT_MODEL):
        self.client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        self.model = model

    def chat(
        self,
        system: str,
        messages: list[dict],
        max_tokens: int = MAX_TOKENS,
        cache_system: bool = True,
    ) -> str:
        """Send a chat request. Caches the system prompt by default (5-min TTL)."""
        system_param = (
            [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
            if cache_system
            else system
        )
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_param,
            messages=messages,
        )
        for block in response.content:
            if isinstance(block, TextBlock):
                return block.text
        return ""

    def analyze(
        self,
        system: str,
        user_message: str,
        max_tokens: int = MAX_TOKENS,
    ) -> str:
        return self.chat(
            system=system,
            messages=[{"role": "user", "content": user_message}],
            max_tokens=max_tokens,
        )
