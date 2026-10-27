"""LLM boundary. The agent only depends on `create(system, messages, tools) -> dict`,
so tests can inject a scripted model and production uses the Anthropic API."""
from __future__ import annotations

import os
from typing import Protocol


class LLM(Protocol):
    model: str

    async def create(self, system: str, messages: list[dict], tools: list[dict]) -> dict: ...


class AnthropicLLM:
    def __init__(self, model: str | None = None, max_tokens: int = 8192):
        from anthropic import AsyncAnthropic

        self.model = model or os.getenv("ANTHROPIC_MODEL", "claude-haiku-5-5")
        self.max_tokens = max_tokens
        # Credentials come from the environment (see .env.example).
        ws = os.getenv("ANTHROPIC_WORKSPACE_ID")
        self.client = AsyncAnthropic(default_headers={"anthropic-workspace-id": ws} if ws else None)

    async def create(self, system: str, messages: list[dict], tools: list[dict]) -> dict:
        r = await self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=messages,
            tools=tools,
        )
        content: list[dict] = []
        for b in r.content:
            if b.type == "text":
                content.append({"type": "text", "text": b.text})
            elif b.type == "tool_use":
                content.append({"type": "tool_use", "id": b.id, "name": b.name, "input": b.input})
        return {"stop_reason": r.stop_reason, "content": content}


def default_llm() -> LLM | None:
    """None when no API key is configured, so the API can return a clear 503."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        return None
    return AnthropicLLM()
