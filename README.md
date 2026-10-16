[![MseeP.ai Security Assessment Badge](https://mseep.net/pr/hao-cyber-phone-mcp-badge.png)](https://mseep.ai/app/hao-cyber-phone-mcp)

# 📱 Phone MCP Plugin
![Downloads](https://pepy.tech/badge/phone-mcp)

🌟 A powerful MCP plugin that lets you control your Android phone with ease through ADB commands.

## Example
- Based on today's weather by browser, automatically select and play netease music, no confirmation needed
![play_mucic_x2](https://github.com/user-attachments/assets/58a39b26-6e8b-4f00-8073-3881f657aa5c)


- Call Hao from the contacts. If he doesn't answer, send a text message telling him to come to Meeting Room 101.
![call_sms_x2](https://github.com/user-attachments/assets/9a155e7c-6dde-4248-b499-0444f19448d0)


[中文文档](README_zh.md)

## ⚡ Quick Start

### 📥 Installation
Use Python 3.10+ and [uv](https://docs.astral.sh/uv/getting-started/installation/) to run in an isolated environment:

```bash
uvx --with "mcp<2" --with requests phone-mcp
```

The extra dependencies keep existing PyPI releases compatible with the MCP v1 API and provide `requests`, which the maps module imports. They are declared in the updated source package but are needed for older releases.

For a persistent installation with uv:

```bash
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python phone-mcp "mcp<2" requests
.venv/bin/phone-cli --help
```

Or use Python's built-in virtual environment and pip on Linux/macOS:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install phone-mcp "mcp<2" requests
.venv/bin/phone-cli --help
```

On Windows, create the environment with `py -3 -m venv .venv`, then use `.venv\Scripts\python.exe` and `.venv\Scripts\phone-cli.exe` instead of the `.venv/bin/` paths above.

On Debian/Ubuntu, an `externally-managed-environment` error means the system Python is managed by the OS. Use `uvx` or a virtual environment; do not bypass it with `sudo pip` or `--break-system-packages`. If `venv` is unavailable, install `python3-venv` with your system package manager first.

### 🔧 Configuration

#### AI Assistant Configuration
Configure in your AI assistant configuration (Cursor, Trae, Claude, etc.):

```json
{
    "mcpServers": {
        "phone-mcp": {
            "command": "uvx",
            "args": [
                "--with", "mcp<2",
                "--with", "requests",
                "phone-mcp"
            ]
        }
    }
}
```

Alternatively, if you installed with pip:
```json
{
    "mcpServers": {
        "phone-mcp": {
            "command": "/absolute/path/to/.venv/bin/python",
            "args": [
                "-m",
                "phone_mcp"
            ]
        }
    }
}
```

> **Important**: Use the absolute path to Python inside the virtual environment where you installed phone-mcp, not the system Python. On Linux/macOS this is `/absolute/path/to/.venv/bin/python`; on Windows use `C:\path\to\.venv\Scripts\python.exe` (escape backslashes as `\\` in JSON). You do not need to activate the environment before launching your AI assistant.

> **Note**: For Cursor, place this configuration in `~/.cursor/mcp.json`

Usage:
- Use commands directly in Claude conversation, for example:
  ```
  Please call contact hao
  ```

⚠️ Before using, ensure:
- ADB is properly installed and configured
- USB debugging is enabled on your Android device
- Device is connected to computer via USB

## 🎯 Key Features

- 📞 **Call Functions**: Make calls, end calls, receive incoming calls
- 💬 **Messaging**: Send and receive SMS, get raw messages
- 👥 **Contacts**: Access phone contacts, create new contacts with automated UI interaction
- 📸 **Media**: Screenshots, screen recording, media control
- 📱 **Apps**: Launch applications, launch specific activities with intents, list installed apps, terminate apps
- 🔧 **System**: Window info, app shortcuts
- 🗺️ **Maps**: Search POIs with phone numbers
- 🖱️ **UI Interaction**: Tap, swipe, type text, press keys
- 🔍 **UI Inspection**: Find elements by text, ID, class or description
- 🤖 **UI Automation**: Wait for elements, scroll to find elements
- 🧠 **Screen Analysis**: Structured screen information and unified interaction
- 🌐 **Web Browser**: Open URLs in device's default browser
- 🔄 **UI Monitoring**: Monitor UI changes and wait for specific elements to appear or disappear

## 🛠️ Requirements

- Python 3.10+
- Android device with USB debugging enabled
- ADB tools

## 📋 Basic Commands

### Device & Connection
```bash
# Check device connection
phone-cli check

# Get screen size
phone-cli screen-interact find method=clickable
```

### Communication
```bash
# Make a call
phone-cli call 1234567890

# End current call
phone-cli hangup

# Send SMS
phone-cli send-sms 1234567890 "Hello"

# Get received messages (with pagination)
phone-cli messages --limit 10

# Get sent messages (with pagination)
phone-cli sent-messages --limit 10

# Get contacts (with pagination)
phone-cli contacts --limit 20

# Create a new contact with UI automation
phone-cli create-contact "John Doe" "1234567890"
```

### Media & Apps
```bash
# Take screenshot
phone-cli screenshot

# Record screen
phone-cli record --duration 30

# Launch app (may not work on all devices)
phone-cli app camera

# Alternative app launch method using open_app (if app command doesn't work)
phone-cli open_app camera

# Close app
phone-cli close-app com.android.camera

# List installed apps (basic info, faster)
phone-cli list-apps

# List apps with pagination
phone-cli list-apps --page 1 --page-size 10

# List apps with detailed info (slower)
phone-cli list-apps --detailed

# Launch specific activity (reliable method for all devices)
phone-cli launch com.android.settings/.Settings

# Launch app by package name (may not work on all devices)
phone-cli app com.android.contacts

# Alternative launch by package name (if app command doesn't work)
phone-cli open_app com.android.contacts

# Launch app by package and activity (most reliable method)
phone-cli launch com.android.dialer/com.android.dialer.DialtactsActivity

# Open URL in default browser
phone-cli open-url google.com
```

### Screen Analysis & Interaction
```bash
# Analyze current screen with structured information
phone-cli analyze-screen

# Unified interaction interface
phone-cli screen-interact <action> [parameters]

# Tap at coordinates
phone-cli screen-interact tap x=500 y=800

# Tap element by text
phone-cli screen-interact tap element_text="Login"

# Tap element by content description
phone-cli screen-interact tap element_content_desc="Calendar"

# Swipe gesture (scroll down)
phone-cli screen-interact swipe x1=500 y1=1000 x2=500 y2=200 duration=300

# Press key
phone-cli screen-interact key keycode=back

# Input text
phone-cli screen-interact text content="Hello World"

# Find elements
phone-cli screen-interact find method=text value="Login" partial=true

# Wait for element
phone-cli screen-interact wait method=text value="Success" timeout=10

# Scroll to find element
phone-cli screen-interact scroll method=text value="Settings" direction=down max_swipes=5

# Monitor UI for changes
phone-cli monitor-ui --interval 0.5 --duration 30

# Monitor UI until specific text appears
phone-cli monitor-ui --watch-for text_appears --text "Welcome"

# Monitor UI until specific element ID appears
phone-cli monitor-ui --watch-for id_appears --id "login_button"

# Monitor UI until specific element class appears
phone-cli monitor-ui --watch-for class_appears --class-name "android.widget.Button"

# Monitor UI changes with output as raw JSON
phone-cli monitor-ui --raw
```

### Location & Maps
```bash
# Search nearby POIs with phone numbers
phone-cli get-poi 116.480053,39.987005 --keywords restaurant --radius 1000
```

## 📚 Advanced Usage

### App and Activity Launch

The plugin provides multiple ways to launch apps and activities:

1. **By App Name** (Two Methods): 
   ```bash
   # Method 1: Using app command (may not work on all devices)
   phone-cli app camera
   
   # Method 2: Using open_app command (alternative if app command fails)
   phone-cli open_app camera
   ```

2. **By Package Name** (Two Methods): 
   ```bash
   # Method 1: Using app command (may not work on all devices)
   phone-cli app com.android.contacts
   
   # Method 2: Using open_app command (alternative if app command fails)
   phone-cli open_app com.android.contacts
   ```

3. **By Package and Activity** (Most Reliable Method):
   ```bash
   # This method works on all devices
   phone-cli launch com.android.dialer/com.android.dialer.DialtactsActivity
   ```

> **Note**: If you encounter issues with the `app` or `open_app` commands, always use the `launch` command with the full component name (package/activity) for the most reliable operation.

### Contact Creation with UI Automation

The plugin provides a way to create contacts through UI interaction:

```bash
# Create a new contact with UI automation
phone-cli create-contact "John Doe" "1234567890"
```

This command will:
1. Open the contacts app
2. Navigate to the contact creation interface
3. Fill in the name and phone number fields
4. Save the contact automatically

### Screen-Based Automation

The unified screen interaction interface allows intelligent agents to easily:

1. **Analyze screens**: Get structured analysis of UI elements and text
2. **Make decisions**: Based on detected UI patterns and available actions
3. **Execute interactions**: Through a consistent parameter system

### UI Monitoring and Automation

The plugin provides powerful UI monitoring capabilities to detect interface changes:

1. **Basic UI monitoring**:
   ```bash
   # Monitor any UI changes with custom interval (seconds)
   phone-cli monitor-ui --interval 0.5 --duration 30
   ```

2. **Wait for specific elements to appear**:
   ```bash
   # Wait for text to appear (useful for automated testing)
   phone-cli monitor-ui --watch-for text_appears --text "Login successful"
   
   # Wait for specific ID to appear
   phone-cli monitor-ui --watch-for id_appears --id "confirmation_dialog"
   ```

3. **Monitor elements disappearing**:
   ```bash
   # Wait for text to disappear
   phone-cli monitor-ui --watch-for text_disappears --text "Loading..."
   ```

4. **Get detailed UI change reports**:
   ```bash
   # Get raw JSON data with all UI change information
   phone-cli monitor-ui --raw
   ```

> **Tip**: UI monitoring is especially useful for automation scripts to wait for loading screens to complete or confirm that actions have taken effect in the UI.

## 📚 Detailed Documentation

For complete documentation and configuration details, visit our [GitHub repository](https://github.com/hao-cyber/phone-mcp).

## 🧰 Tool Documentation

### Screen Interface API

The plugin provides a powerful screen interface with comprehensive APIs for interacting with the device. Below are the key functions and their parameters:

#### interact_with_screen
```python
async def interact_with_screen(action: str, params: Dict[str, Any] = None) -> str:
    """Execute screen interaction actions"""
```
- **Parameters:**
  - `action`: Type of action ("tap", "swipe", "key", "text", "find", "wait", "scroll")
  - `params`: Dictionary with parameters specific to each action type
- **Returns:** JSON string with operation results

**Examples:**
```python
# Tap by coordinates
result = await interact_with_screen("tap", {"x": 100, "y": 200})

# Tap by element text
result = await interact_with_screen("tap", {"element_text": "Login"})

# Swipe down
result = await interact_with_screen("swipe", {"x1": 500, "y1": 300, "x2": 500, "y2": 1200, "duration": 300})

# Input text
result = await interact_with_screen("text", {"content": "Hello world"})

# Press back key
result = await interact_with_screen("key", {"keycode": "back"})

# Find element by text
result = await interact_with_screen("find", {"method": "text", "value": "Settings", "partial": True})

# Wait for element to appear
result = await interact_with_screen("wait", {"method": "text", "value": "Success", "timeout": 10, "interval": 0.5})

# Scroll to find element
result = await interact_with_screen("scroll", {"method": "text", "value": "Privacy Policy", "direction": "down", "max_swipes": 8})
```

#### analyze_screen
```python
async def analyze_screen(include_screenshot: bool = False, max_elements: int = 50) -> str:
    """Analyze the current screen and provide structured information about UI elements"""
```
- **Parameters:**
  - `include_screenshot`: Whether to include base64-encoded screenshot in result
  - `max_elements`: Maximum number of UI elements to process
- **Returns:** JSON string with detailed screen analysis

#### create_contact
```python
async def create_contact(name: str, phone: str) -> str:
    """Create a new contact with the given name and phone number"""
```
- **Parameters:**
  - `name`: The contact's full name
  - `phone`: The phone number for the contact
- **Returns:** JSON string with operation result
- **Location:** This function is found in the 'contacts.py' module and implements UI automation to create contacts

#### launch_app_activity
```python
async def launch_app_activity(package_name: str, activity_name: Optional[str] = None) -> str:
    """Launch an app using package name and optionally an activity name"""
```
- **Parameters:**
  - `package_name`: The package name of the app to launch
  - `activity_name`: The specific activity to launch (optional)
- **Returns:** JSON string with operation result
- **Location:** This function is found in the 'apps.py' module

#### launch_intent
```python
async def launch_intent(intent_action: str, intent_type: Optional[str] = None, extras: Optional[Dict[str, str]] = None) -> str:
    """Launch an activity using Android intent system"""
```
- **Parameters:**
  - `intent_action`: The action to perform
  - `intent_type`: The MIME type for the intent (optional)
  - `extras`: Extra data to pass with the intent (optional)
- **Returns:** JSON string with operation result
- **Location:** This function is found in the 'apps.py' module

## 📄 License

Apache License, Version 2.0

# Contact Creation Tool

This tool provides a simple way to create contacts on an Android device using ADB.

## Prerequisites

- Python 3.x
- ADB (Android Debug Bridge) installed and configured
- Android device connected and authorized for ADB

## Usage

### Basic Usage

Simply run the script:

```bash
python create_contact.py
```

This will create a contact with default values:
- Account name: "你的账户名"
- Account type: "com.google"

### Advanced Usage

You can provide custom account name and type using a JSON string:

```bash
python create_contact.py '{"account_name": "your_account", "account_type": "com.google"}'
```

### Output

The script outputs a JSON object with:
- `success`: boolean indicating if the operation was successful
- `message`: any output or error message from the command

Example success output:
```json
{"success": true, "message": ""}
```

## Error Handling

- If ADB is not available or device is not connected, the script will return an error
- Invalid JSON input will result in an error message
- Any ADB command errors will be captured and returned in the message field

## Notes

- Make sure your Android device is connected and authorized for ADB use
- The device screen should be unlocked when running the command
- Some devices might require additional permissions to modify contacts

### Apps & Shortcuts
```bash
# Get app shortcuts (with pagination)
phone-cli shortcuts --package "com.example.app"
```
