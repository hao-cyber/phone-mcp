"""Media-related phone control functions."""

import asyncio
import subprocess
import os.path
import time
import threading
import shlex
from ..core import run_command
from ..config import SCREENSHOT_PATH, RECORDING_PATH, COMMAND_TIMEOUT


async def take_screenshot() -> str:
    """Take a screenshot of the phone's current screen.

    Captures the current screen content of the device and automatically saves to
    the phone's storage. Will create directories if they don't exist.
    Also pulls the screenshot to the computer for easier access.

    Returns:
        str: Success message with the path to the screenshot, or an error
             message if the screenshot could not be taken.
    """
    # Check for connected device
    from ..core import check_device_connection

    connection_status = await check_device_connection()
    if "ready" not in connection_status:
        return connection_status

    # Generate a timestamp for the filename
    timestamp = time.strftime("%Y%m%d_%H%M%S")

    # Define paths - use multiple potential storage locations for reliability
    filename = f"screenshot_{timestamp}.png"
    primary_path = f"{SCREENSHOT_PATH}{filename}"
    fallback_paths = [
        f"/sdcard/DCIM/{filename}",
        f"/sdcard/Pictures/{filename}",
        f"/sdcard/Download/{filename}",
        f"/data/local/tmp/{filename}",
    ]

    # Ensure the directory exists
    main_dir = SCREENSHOT_PATH
    await run_command(f"adb shell mkdir -p {main_dir}")

    # First attempt: take screenshot to configured path
    cmd = f"adb shell screencap -p {primary_path}"
    success, output = await run_command(cmd)

    # Check if the file exists
    check_cmd = f"adb shell ls {primary_path}"
    file_exists, _ = await run_command(check_cmd)

    # If primary path failed, try fallback locations
    storage_path = primary_path
    if not success or not file_exists:
        for path in fallback_paths:
            # Ensure directory exists
            dir_path = os.path.dirname(path)
            await run_command(f"adb shell mkdir -p {dir_path}")

            # Take screenshot
            cmd = f"adb shell screencap -p {path}"
            success, output = await run_command(cmd)

            # Verify file exists
            check_cmd = f"adb shell ls {path}"
            file_exists, _ = await run_command(check_cmd)

            if success and file_exists:
                storage_path = path
                break

    if success and file_exists:
        # Try to pull the file to the local machine if possible
        pull_cmd = f"adb pull {storage_path} ./{filename}"
        pull_success, pull_output = await run_command(pull_cmd)

        if pull_success:
            return f"Screenshot taken and saved to device ({storage_path}) and pulled to current directory (./{filename})"
        else:
            return f"Screenshot taken and saved to device at {storage_path}"
    else:
        # Direct capture to stdout as a last resort - platform independent approach
        import tempfile
        import os

        # Create a temporary file to store the output
        temp_file = os.path.join(tempfile.gettempdir(), "screenshot_temp.png")
        screenshot_file = "./screenshot_direct.png"

        # First capture to temp file
        cmd = f"adb shell screencap -p > {temp_file}"
        direct_success, direct_output = await run_command(cmd)

        if direct_success:
            try:
                # Open and process the file to handle line ending differences (instead of using sed)
                with open(temp_file, "rb") as f_in:
                    data = f_in.read()

                # Replace \r\n with \n (Windows-safe approach)
                if b"\r\n" in data:
                    data = data.replace(b"\r\n", b"\n")
                elif b"\r" in data:
                    data = data.replace(b"\r", b"")

                # Write the processed data
                with open(screenshot_file, "wb") as f_out:
                    f_out.write(data)

                # Remove temp file
                try:
                    os.remove(temp_file)
                except:
                    pass

                return "Screenshot taken and saved to ./screenshot_direct.png"
            except Exception as e:
                return f"Screenshot captured but failed to process: {str(e)}"
        else:
            return f"Failed to take screenshot: {direct_output}. Make sure the device is properly connected."


def _download_recording_background(storage_path: str, duration_seconds: int):
    """Background thread function for downloading the screen recording
    
    Args:
        storage_path: Path to the recording file on the device
        duration_seconds: Recording duration, used to wait for recording completion
    """
    import time
    import os
    import subprocess
    
    # Wait for recording to complete
    time.sleep(duration_seconds + 2)  # Wait an extra 2 seconds to ensure recording is complete
    
    # Define local save path
    local_filename = os.path.basename(storage_path)
    
    # Attempt to download the file
    try:
        pull_cmd = f"adb pull {shlex.quote(storage_path)} {shlex.quote(local_filename)}"
        result = subprocess.run(pull_cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"\n✅ Recording downloaded successfully to ./{local_filename}")
        else:
            print(f"\n❌ Failed to download recording: {result.stderr}")
    except Exception as e:
        print(f"\n❌ Error downloading recording: {str(e)}")


async def start_screen_recording(duration_seconds: int = 30) -> str:
    """Start recording the phone's screen.

    Records the screen activity for the specified duration and saves
    the video to the phone's storage. Automatically creates directories
    if they don't exist.

    Args:
        duration_seconds (int): Recording duration in seconds (default: 30,
                               max: 180 seconds due to ADB limitations)

    Returns:
        str: Success message with the path to the recording, or an error
             message if the recording could not be started.
    """
    # Check for connected device
    from ..core import check_device_connection

    connection_status = await check_device_connection()
    if "ready" not in connection_status:
        return connection_status

    # Limit duration to prevent excessive recordings
    if duration_seconds > 180:
        duration_seconds = 180

    # Generate filename with timestamp
    timestamp = time.strftime("%Y%m%d_%H%M%S")

    # Define paths - use multiple potential storage locations for reliability
    filename = f"recording_{timestamp}.mp4"
    primary_path = f"{RECORDING_PATH}{filename}"
    fallback_paths = [
        f"/sdcard/DCIM/Camera/{filename}",
        f"/sdcard/Movies/{filename}",
        f"/sdcard/Videos/{filename}",
        f"/sdcard/Download/{filename}",
    ]

    # Ensure the directory exists
    main_dir = RECORDING_PATH
    await run_command(f"adb shell mkdir -p {main_dir}")

    # First attempt the primary path
    storage_path = primary_path

    # Check if the main directory is writable
    mkdir_success, _ = await run_command(f"adb shell mkdir -p {main_dir}")
    if not mkdir_success:
        # Try fallback paths
        for path in fallback_paths:
            dir_path = os.path.dirname(path)
            mkdir_success, _ = await run_command(f"adb shell mkdir -p {dir_path}")
            if mkdir_success:
                storage_path = path
                break

    # Start screen recording with the specified duration
    try:
        # Use synchronous method to start screen recording, avoiding asyncio issues
        cmd = f"adb shell screenrecord --time-limit {int(duration_seconds)} {shlex.quote(storage_path)}"
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Start background thread to wait for recording completion and download the file
        download_thread = threading.Thread(
            target=_download_recording_background,
            args=(storage_path, duration_seconds)
        )
        download_thread.daemon = True  # Daemon thread, will automatically end when main thread ends
        download_thread.start()
        
        return (
            f"Started screen recording. Recording for {duration_seconds} seconds "
            f"and will be saved to {storage_path}. Will attempt to download video when complete."
        )

    except Exception as e:
        return f"Failed to start screen recording: {str(e)}"


async def play_media() -> str:
    """Simulate media button press to play/pause media.

    This function sends a keyevent that simulates pressing the media
    play/pause button, which can control music, videos, or podcasts
    that are currently playing.

    Returns:
        str: Success message, or an error message if the command failed.
    """
    cmd = "adb shell input keyevent KEYCODE_MEDIA_PLAY_PAUSE"
    success, output = await run_command(cmd)

    if success:
        return "Media play/pause command sent successfully"
    else:
        return f"Failed to send media command: {output}"
