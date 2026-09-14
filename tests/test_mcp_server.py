from __future__ import annotations

import pytest
from mcp import Client

from mcp_server import mcp


@pytest.mark.anyio
async def test_mcp_server_exposes_required_tools():
    async with Client(mcp) as client:
        result = await client.list_tools()
        names = {tool.name for tool in result.tools}

    assert "get_weather_forecast" in names
    assert "convert_currency" in names
