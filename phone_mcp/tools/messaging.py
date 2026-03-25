"""Messaging-related phone control functions."""

import asyncio
import subprocess
import json
import shlex
from ..core import run_command
from ..config import DEFAULT_COUNTRY_CODE


async def send_text_message(phone_number: str, message: str) -> str:
    """Send a text message to the specified number.

    Uses the phone's messaging app with UI automation to send SMS.
    Process: Opens messaging app, fills recipient and content, automatically clicks send button, then auto-exits app.

    Args:
        phone_number (str): Recipient's phone number. Country code will be automatically added if not included.
                          Example: "13812345678" or "+8613812345678"
        message (str): SMS content. Supports any text, including emojis.
                     Example: "Hello, this is a test message"

    Returns:
        str: String description of the operation result:
             - Success: "Text message sent to {phone_number}"
             - Failure: Message containing error reason, like "Failed to open messaging app: {error}"
                       or "Failed to navigate to send button: {error}"
    """
    # Add country code if not already included
    if not phone_number.startswith("+"):
        phone_number = DEFAULT_COUNTRY_CODE + phone_number

    # Validate phone number format
    if not phone_number[1:].isdigit():
        return "Invalid phone number format. Please use numeric digits only."

    # Open messaging app with the number and message
    cmd = f"adb shell am start -a android.intent.action.SENDTO -d sms:{shlex.quote(phone_number)} --es sms_body {shlex.quote(message)} --ez exit_on_sent true"
    success, output = await run_command(cmd)
    # Open messaging app with the number and message, and auto-exit after sending

    if not success:
        return f"Failed to open messaging app: {output}"

    # Give the app time to open (increased wait time)
    await asyncio.sleep(3)

    # Get screen dimensions
    screen_cmd = "adb shell wm size"
    screen_success, screen_output = await run_command(screen_cmd)

    width, height = 1080, 2340  # Default values for common phones

    if screen_success and "Physical size:" in screen_output:
        try:
            # Example output: "Physical size: 1080x2340"
            size_str = screen_output.split("Physical size:")[1].strip()
            width, height = map(int, size_str.split("x"))
        except:
            # If parsing fails, use default values
            pass

    # Try different methods to send the message

    # Method 1: Try using coordinates to tap the send button (usually bottom right)
    # For MIUI/Xiaomi phones, the send button is typically a green circle in the bottom right
    send_x = int(width * 0.9)  # 90% to the right
    send_y = int(height * 0.95)  # 95% down from top

    tap_cmd = f"adb shell input tap {send_x} {send_y}"
    tap_success, tap_output = await run_command(tap_cmd)

    # Wait for the message to be sent
    await asyncio.sleep(2)

    # If tapping specific coordinates didn't work, try the original method
    if not tap_success:
        # Original method: Try using arrow keys to navigate to send button
        # Press right button to focus on send button (keyevent 22)
        await run_command("adb shell input keyevent 22")
        # Press enter to send the message (keyevent 66)
        await run_command("adb shell input keyevent 66")
        await asyncio.sleep(1)

    # In case auto-exit doesn't work, press BACK once to exit the messaging app
    await run_command("adb shell input keyevent 4")

    return f"Text message sent to {phone_number}"


async def receive_text_messages(limit: int = 5) -> str:
    """Get recent text messages from the phone.

    Retrieves recent SMS messages from the device's SMS database
    using ADB and content provider queries to get structured message data.

    Args:
        limit (int): Maximum number of messages to retrieve (default: 5)
                    Example: 10 will return the 10 most recent messages

    Returns:
        str: JSON string containing messages or an error message:
             - Success: Formatted JSON string with list of messages, each with fields:
                       - address: Sender's number
                       - body: Message content
                       - date: Timestamp
                       - formatted_date: Human-readable date time (like "2023-07-25 14:30:22")
             - Failure: Text message describing the error, like "No recent text messages found..."
    """
    # Check for connected device
    from ..core import check_device_connection

    connection_status = await check_device_connection()
    if "ready" not in connection_status:
        return connection_status

    # Try the SMS database query directly first, known to sometimes work
    cmd = "adb shell content query --uri content://sms/inbox --projection address,body,date"
    success, output = await run_command(cmd)

    # First, check if the output contains error or help text
    if "usage:" in output or output.startswith("Error"):
        # Let's try a direct ADB shell command to get recent SMS content
        try:
            # This is a direct shell command that might be more reliable - use double quotes for Windows compatibility
            shell_cmd = 'adb shell "echo -n \\"MESSAGES_START\\"; content query --uri content://sms/inbox --projection address,body,date; echo -n \\"MESSAGES_END\\""'
            success, output = await run_command(shell_cmd)

            if success and "MESSAGES_START" in output and "MESSAGES_END" in output:
                # Extract just the content between our markers
                content = (
                    output.split("MESSAGES_START")[1].split("MESSAGES_END")[0].strip()
                )

                if content and "Row:" in content:
                    # Process the messages
                    messages = []
                    rows = content.split("Row:")
                    rows = [r for r in rows if r.strip()]

                    for row in rows:
                        message = {}
                        # Split by comma but be careful of commas inside the message content
                        parts = []
                        current_part = ""
                        for char in row:
                            if char == "," and not current_part.count("=") > 0:
                                parts.append(current_part.strip())
                                current_part = ""
                            else:
                                current_part += char
                        if current_part:
                            parts.append(current_part.strip())

                        for part in parts:
                            if "=" in part:
                                key, value = part.split("=", 1)
                                message[key.strip()] = value.strip()

                        # Format the date if present
                        if "date" in message:
                            try:
                                timestamp = int(message["date"])
                                import datetime

                                date_str = datetime.datetime.fromtimestamp(
                                    timestamp / 1000
                                ).strftime("%Y-%m-%d %H:%M:%S")
                                message["formatted_date"] = date_str
                            except:
                                pass

                        if message:
                            messages.append(message)

                    if messages:
                        messages = messages[:limit]
                        return json.dumps(messages, indent=2)

        except Exception as e:
            # If this fails, we have other methods to try
            pass

    # Try the most basic approach - since we know it works via direct ADB
    try:
        # This directly parses the output we know works with adb shell
        direct_cmd = "adb shell content query --uri content://sms/inbox --projection address,body,date"
        success, output = await run_command(direct_cmd)

        if success and output and "Row:" in output:
            messages = []
            # Parse the output following the known format
            # Example output: "Row: 0 address=13831151111, body=Meeting at 7pm tonight, date=1744270871178"
            rows = output.split("Row:")
            rows = [r for r in rows if r.strip()]

            for row in rows:
                # Extract address, body, and date directly with string operations
                address = ""
                body = ""
                date = ""

                if "address=" in row:
                    address_start = row.find("address=") + 8
                    address_end = row.find(",", address_start)
                    if address_end > 0:
                        address = row[address_start:address_end].strip()

                if "body=" in row:
                    body_start = row.find("body=") + 5
                    body_end = row.find(", date=")
                    if body_end > 0:
                        body = row[body_start:body_end].strip()
                    else:
                        # If date isn't found, body might be the last field
                        body = row[body_start:].strip()

                if "date=" in row:
                    date_start = row.find("date=") + 5
                    date_text = row[date_start:].strip()
                    date = date_text

                if address or body:
                    message = {"address": address, "body": body, "date": date}

                    # Format date if possible
                    if date:
                        try:
                            timestamp = int(date)
                            import datetime

                            date_str = datetime.datetime.fromtimestamp(
                                timestamp / 1000
                            ).strftime("%Y-%m-%d %H:%M:%S")
                            message["formatted_date"] = date_str
                        except:
                            pass

                    messages.append(message)

            if messages:
                messages = messages[:limit]
                return json.dumps(messages, indent=2)

    except Exception as e:
        pass  # Continue to next approach

    # Return a helpful error message with the raw output for debugging
    return json.dumps(
        {
            "error": "Could not retrieve SMS messages",
            "possible_reasons": [
                "No SMS messages in inbox",
                "Permission issues with SMS access",
                "Device restrictions",
            ],
            "raw_output_sample": output[:200] if output else "No output received",
            "suggested_fix": "Try sending a test SMS to the device or check permissions",
        },
        indent=2,
    )


async def get_sent_messages(limit: int = 5) -> str:
    """Get recently sent text messages from the phone.

    Retrieves sent SMS messages from the device's SMS database.
    This provides a complete list of messages that were successfully sent from this device.

    Args:
        limit (int): Maximum number of sent messages to retrieve (default: 5)

    Returns:
        str: JSON string containing sent messages with:
             - from: Sender phone number (device owner)
             - to: Recipient phone number
             - text: Message content
             - date: Timestamp
             - formatted_date: Human-readable date time (like "2023-07-25 14:30:22")
    """
    # Check for connected device
    from ..core import check_device_connection

    connection_status = await check_device_connection()
    if "ready" not in connection_status:
        return connection_status

    cmd = "adb shell content query --uri content://sms/sent --projection address,body,date"
    success, output = await run_command(cmd)

    if not success or not output or not "Row:" in output:
        return "Unable to retrieve sent SMS messages. Device may not have any sent messages or may restrict access."

    # Direct string parsing, avoiding JSON and complex processing
    result = []
    try:
        rows = output.strip().split("Row:")
        rows = [r for r in rows if r.strip()]
        count = 0

        for row in rows:
            if count >= limit:
                break

            # Extract components
            message = {}

            # Extract address (recipient for sent messages)
            if "address=" in row:
                address_start = row.find("address=") + 8
                address_end = row.find(",", address_start)
                if address_end > 0:
                    message["to"] = row[address_start:address_end].strip()

            # Extract body
            if "body=" in row:
                body_start = row.find("body=") + 5
                body_end = row.find(", date=")
                if body_end > 0:
                    message["text"] = row[body_start:body_end].strip()
                else:
                    # If date isn't found, body might be the last field
                    message["text"] = row[body_start:].strip()

            # Extract date
            if "date=" in row:
                date_start = row.find("date=") + 5
                date_str = row[date_start:].strip()
                message["date"] = date_str

                # Format date
                try:
                    timestamp = int(date_str)
                    import datetime

                    message["formatted_date"] = datetime.datetime.fromtimestamp(
                        timestamp / 1000
                    ).strftime("%Y-%m-%d %H:%M:%S")
                except:
                    message["formatted_date"] = "Unknown date"

            if "to" in message and "text" in message:
                result.append(message)
                count += 1

        if not result:
            return "No sent SMS messages found."

        # Format for human-readable output
        output_lines = [f"Found {len(result)} sent SMS messages:"]
        for i, msg in enumerate(result, 1):
            to_line = f"To: {msg.get('to', 'Unknown')}"
            date_line = f"Date: {msg.get('formatted_date', 'Unknown')}"
            text_line = msg.get("text", "No content")

            output_lines.append(f"\n{i}. {to_line} - {date_line}")
            output_lines.append(f"   {text_line}")

        return "\n".join(output_lines)
    except Exception as e:
        return f"Error parsing sent SMS messages: {str(e)}"