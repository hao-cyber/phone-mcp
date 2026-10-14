"""Exercise installed entry points from outside the source checkout."""
import asyncio
import subprocess
import sys
from datetime import timedelta

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def test_installed_cli_help(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "phone_mcp.cli", "--help"],
        cwd=tmp_path, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "screenshot" in result.stdout


@pytest.mark.asyncio
async def test_installed_mcp_server_initializes_and_lists_tools(tmp_path):
    async def connect():
        params = StdioServerParameters(
            command=sys.executable, args=["-m", "phone_mcp"], cwd=str(tmp_path),
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=15)) as session:
                await session.initialize()
                response = await session.list_tools()
                tools = {tool.name: tool for tool in response.tools}
                assert "analyze_screen" in tools
                assert "include_screenshot" in tools["analyze_screen"].inputSchema["properties"]
    await asyncio.wait_for(connect(), timeout=30)


@pytest.mark.asyncio
async def test_optional_tool_arguments_accept_explicit_null(tmp_path):
    """Optional arguments advertise ``"default": null``, so null must validate."""
    async def connect():
        params = StdioServerParameters(
            command=sys.executable, args=["-m", "phone_mcp"], cwd=str(tmp_path),
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=15)) as session:
                await session.initialize()
                response = await session.list_tools()
                tools = {tool.name: tool for tool in response.tools}
                for tool_name, argument in [
                    ("create_contact", "email"),
                    ("launch_app_activity", "activity_name"),
                ]:
                    schema = tools[tool_name].inputSchema["properties"][argument]
                    assert schema.get("default") is None
                    allowed = [option.get("type") for option in schema.get("anyOf", [schema])]
                    assert "null" in allowed, (tool_name, argument, schema)
    await asyncio.wait_for(connect(), timeout=30)
