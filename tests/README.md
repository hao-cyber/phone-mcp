# Screenshot and installation regressions

Run the device-free regression suite from the repository root with Python 3.10+:

```bash
uv run --no-project --with . --with pytest==8.3.5 --with pytest-asyncio==0.26.0 python -m pytest tests/test_screen_interface.py tests/test_installation.py -q
```

The screenshot tests replace the ADB subprocess with controlled PNG/error results,
including timeout and cancellation. The installation tests start the installed CLI
and a real stdio MCP server outside the checkout, initialize a client session, and
list tools without operating a phone. CI runs this suite on Linux, macOS and Windows,
plus Python 3.10 on Linux. It does not verify physical-device behavior.

The older `test_phone_mcp.py`, `test_phone_functionality.py`, and
`test_amap_functionality.py` currently fail collection because they import removed
APIs (`get_raw_messages` and `get_poi_info_by_location`). These are pre-existing
failures; this focused workflow does not claim that the full historical suite passes.
