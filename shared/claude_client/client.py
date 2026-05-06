import os
from anthropic import Anthropic
from anthropic.types import TextBlock

DEFAULT_MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 4096


def _make_anthropic_client() -> Anthropic:
    """
    Build an Anthropic client from whichever credentials are available.

    Priority:
      1. ANTHROPIC_API_KEY   — direct API access (fastest, most reliable)
      2. CLAUDE_PROXY_URL    — local proxy that calls `claude --print` on the host
                               (set to http://host.docker.internal:8090 when using
                                the claude-proxy/proxy.py sidecar)
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    proxy_url = os.getenv("CLAUDE_PROXY_URL")

    if api_key:
        return Anthropic(api_key=api_key)
    if proxy_url:
        # anthropic SDK lets you override the base URL; supply a dummy key so
        # the SDK doesn't raise on construction (the proxy ignores it).
        return Anthropic(api_key="proxy", base_url=proxy_url)
    raise EnvironmentError(
        "No Claude credentials found. Set ANTHROPIC_API_KEY or CLAUDE_PROXY_URL."
    )


class ClaudeClient:
    def __init__(self, model: str = DEFAULT_MODEL):
        self.client = _make_anthropic_client()
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
