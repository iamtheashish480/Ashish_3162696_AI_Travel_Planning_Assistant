"""Small MCP client used by the LangChain agent.

The agent does not call Open-Meteo or the exchange-rate service directly.
It calls this module, which starts the MCP server as a stdio subprocess and
invokes the registered MCP tool through the official MCP client protocol.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from langchain.tools import tool
from mcp import Client, StdioServerParameters


PROJECT_ROOT = Path(__file__).resolve().parent
MCP_SERVER_PATH = PROJECT_ROOT / "mcp_server.py"


def _extract_mcp_result(result: Any) -> str:
    """Turn an MCP CallToolResult into readable text for the LLM."""
    if getattr(result, "is_error", False):
        raise RuntimeError("MCP server reported a tool error.")

    structured = getattr(result, "structured_content", None)
    if structured:
        return json.dumps(structured, ensure_ascii=False, indent=2)

    parts: list[str] = []
    for item in getattr(result, "content", []) or []:
        text = getattr(item, "text", None)
        if text:
            parts.append(text)

    if parts:
        return "\n".join(parts)

    return str(result)


async def _call_mcp_tool(tool_name: str, arguments: dict[str, Any]) -> str:
    """Connect to the local MCP server over stdio and call one tool."""
    if not MCP_SERVER_PATH.exists():
        raise FileNotFoundError(f"MCP server not found: {MCP_SERVER_PATH}")

    env = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONPATH": str(PROJECT_ROOT),
        "HOME": os.environ.get("HOME", ""),
    }

    server = StdioServerParameters(
        command=sys.executable,
        args=[str(MCP_SERVER_PATH)],
        env=env,
    )

    async with Client(server) as client:
        available = await client.list_tools()
        tool_names = {item.name for item in available.tools}
        if tool_name not in tool_names:
            raise RuntimeError(
                f"MCP tool '{tool_name}' is not available. Found: {sorted(tool_names)}"
            )

        result = await client.call_tool(tool_name, arguments)
        return _extract_mcp_result(result)


def call_mcp_tool(tool_name: str, arguments: dict[str, Any]) -> str:
    """Synchronous bridge used by the synchronous LangChain tools."""
    try:
        return asyncio.run(_call_mcp_tool(tool_name, arguments))
    except Exception as exc:
        return f"[MCP CLIENT FAILURE] Could not call '{tool_name}': {exc}"


@tool("get_weather_forecast")
def mcp_weather_forecast(start_date: str = "", days: int = 3) -> str:
    """Use the MCP weather tool for a live 1-7 day Singapore forecast.

    Use start_date in YYYY-MM-DD format when the user asks about a future
    trip. Leave it blank for the current Singapore forecast.
    """
    return call_mcp_tool(
        "get_weather_forecast",
        {"start_date": start_date, "days": days},
    )


@tool("convert_currency")
def mcp_currency_converter(
    amount: float,
    from_currency: str,
    to_currency: str = "SGD",
) -> str:
    """Use the MCP currency tool for a live exchange-rate conversion."""
    return call_mcp_tool(
        "convert_currency",
        {
            "amount": amount,
            "from_currency": from_currency,
            "to_currency": to_currency,
        },
    )
