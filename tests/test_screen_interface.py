"""Screenshot regressions for both public screen-analysis entry points."""
import asyncio
import base64
import json
from unittest.mock import AsyncMock, Mock

import pytest

from phone_mcp.tools import media, screen_interface

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aS1sAAAAASUVORK5CYII="
)


@pytest.fixture
def screen_ui(monkeypatch):
    monkeypatch.setattr(screen_interface, "dump_ui", AsyncMock(return_value=json.dumps({
        "status": "success", "elements": [{"text": "Settings", "bounds": "[0,0][100,100]"}]
    })))
    monkeypatch.setattr(screen_interface, "get_screen_size", AsyncMock(return_value='{"width":1080,"height":1920}'))
    monkeypatch.setattr(screen_interface, "find_clickable_elements", AsyncMock(return_value='{"status":"success","elements":[]}'))


@pytest.fixture
def adb_process(monkeypatch):
    process = Mock(returncode=0)
    process.communicate = AsyncMock(return_value=(PNG, b""))
    process.kill = Mock()
    start = AsyncMock(return_value=process)
    monkeypatch.setattr(media.asyncio, "create_subprocess_exec", start)
    return process, start


@pytest.mark.asyncio
@pytest.mark.parametrize("analyze", [screen_interface.get_screen_info, screen_interface.analyze_screen])
async def test_screenshot_is_preserved_as_binary_png(screen_ui, adb_process, analyze):
    result = json.loads(await analyze(include_screenshot=True))
    assert result["status"] == "success"
    assert base64.b64decode(result["screenshot"], validate=True) == PNG
    assert "screenshot_error" not in result
    adb_process[1].assert_awaited_once_with(
        "adb", "exec-out", "screencap", "-p",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("analyze", [screen_interface.get_screen_info, screen_interface.analyze_screen])
async def test_disabled_screenshot_does_not_start_adb(screen_ui, adb_process, analyze):
    result = json.loads(await analyze(include_screenshot=False))
    assert result["status"] == "success"
    assert "screenshot" not in result
    assert "screenshot_error" not in result
    adb_process[1].assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("analyze", [screen_interface.get_screen_info, screen_interface.analyze_screen])
async def test_adb_failure_preserves_ui_and_reports_capture_error(screen_ui, adb_process, analyze):
    process, _ = adb_process
    process.returncode = 1
    process.communicate.return_value = (b"", b"error: no devices/emulators found")
    result = json.loads(await analyze(include_screenshot=True))
    assert result["status"] == "success"
    assert result["screenshot"] == ""
    assert result["screenshot_error"] == "error: no devices/emulators found"
    assert "Settings" in json.dumps(result)


@pytest.mark.asyncio
@pytest.mark.parametrize("output", [b"", b"adb error", b"\xff\xfeinvalid"])
async def test_non_png_output_is_rejected(adb_process, output):
    adb_process[0].communicate.return_value = (output, b"")
    success, error = await media.capture_screenshot_base64()
    assert not success
    assert "did not return PNG" in error


@pytest.mark.asyncio
async def test_missing_adb_is_reported(adb_process):
    adb_process[1].side_effect = FileNotFoundError("adb not found")
    assert await media.capture_screenshot_base64() == (False, "adb not found")


@pytest.mark.asyncio
async def test_timeout_kills_and_reaps_capture(adb_process):
    process, _ = adb_process
    process.communicate.side_effect = [asyncio.TimeoutError(), (b"", b"")]
    success, error = await media.capture_screenshot_base64()
    assert not success
    assert "timed out" in error
    process.kill.assert_called_once()
    assert process.communicate.await_count == 2


@pytest.mark.asyncio
async def test_cancellation_kills_capture_and_propagates(adb_process):
    process, _ = adb_process
    process.communicate.side_effect = [asyncio.CancelledError(), (b"", b"")]
    with pytest.raises(asyncio.CancelledError):
        await media.capture_screenshot_base64()
    process.kill.assert_called_once()
    assert process.communicate.await_count == 2


@pytest.mark.asyncio
async def test_adb_error_decoding_does_not_hide_failure(adb_process):
    process, _ = adb_process
    process.returncode = 1
    process.communicate.return_value = (b"", b"device error: \xff")
    success, error = await media.capture_screenshot_base64()
    assert not success
    assert "device error" in error
