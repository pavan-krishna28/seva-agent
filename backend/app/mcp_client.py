"""Thin async wrapper around an MCP stdio session."""
from __future__ import annotations

import json
import sys
from contextlib import AsyncExitStack
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

DEFAULT_SERVER = Path(__file__).resolve().parents[2] / "mcp_server" / "server.py"


class McpToolbox:
    def __init__(self, server_path: Path | str = DEFAULT_SERVER):
        self.server_path = str(server_path)
        self.session: ClientSession | None = None
        self.tools: list[dict] = []  # Anthropic tool-schema format

    async def start(self, stack: AsyncExitStack) -> None:
        params = StdioServerParameters(command=sys.executable, args=[self.server_path])
        read, write = await stack.enter_async_context(stdio_client(params))
        self.session = await stack.enter_async_context(ClientSession(read, write))
        await self.session.initialize()
        listed = await self.session.list_tools()
        self.tools = [
            {"name": t.name, "description": t.description or "", "input_schema": t.inputSchema}
            for t in listed.tools
        ]

    async def call(self, name: str, args: dict) -> tuple[object, bool]:
        """Returns (parsed_result, is_error)."""
        assert self.session is not None, "MCP session not started"
        res = await self.session.call_tool(name, args)
        text = "".join(getattr(c, "text", "") for c in res.content)
        if res.isError:
            return text, True
        try:
            return json.loads(text), False
        except json.JSONDecodeError:
            return text, False
