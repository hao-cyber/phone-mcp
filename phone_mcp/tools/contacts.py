"""
Contact-related functions for Phone MCP.
This module provides functions to access and manage contacts on the phone.
"""

import asyncio
import json
import re
import shlex
from ..core import run_command


async def _check_contact_permissions():
    """Check if the app has the necessary permissions to access contacts."""
    # Try to check if we have permission by running a simple query
    cmd = "adb shell pm list permissions -g"
    success, output = await run_command(cmd)

    # Use Python to check for contacts permissions
    return success and any("contacts" in line.lower() for line in output.splitlines())


async def get_contacts(limit=20):
    """Retrieve contacts from the phone.

    Core function for accessing the contacts database on the device.
    Fetches contact information including names and phone numbers.
    Returns data in structured JSON format.

    Args:
        limit (int): Number of contacts to retrieve, defaults to 20

    Returns:
        str: JSON string with contact data or error message
    """
    # Check for connected device
    from ..core import check_device_connection

    connection_status = await check_device_connection()
    if "ready" not in connection_status:
        return connection_status

    # Check permissions
    has_permissions = await _check_contact_permissions()
    if not has_permissions:
        return "Cannot access contacts. Permission may be denied. Please check your device settings."

    try:
        # Use the verified working command first - this is known to work
        cmd = f"adb shell content query --uri content://contacts/phones/"
        success, output = await run_command(cmd)

        if success and "Row:" in output:
            # Process the output
            contacts = []
            rows = output.strip().split("Row: ")
            # Skip empty first element if it exists
            if rows and not rows[0].strip():
                rows = rows[1:]

            for row in rows:
                if not row.strip():
                    continue

                contact = {}
                parts = row.split(", ")

                for part in parts:
                    if "=" in part:
                        key, value = part.split("=", 1)
                        # Only add non-NULL values
                        if value and value != "NULL" and value != "null":
                            contact[key.strip()] = value.strip()

                # Add the contact if it has at least name and number
                if ("name" in contact or "display_name" in contact) and len(contact) > 0:
                    # Normalize the contact data
                    if "display_name" in contact and "name" not in contact:
                        contact["name"] = contact["display_name"]
                    # Ensure phone field is called 'phone' and is consistent
                    if "number" in contact:
                        contact["phone"] = contact["number"]
                    
                    contacts.append(contact)

            if contacts:
                return json.dumps(contacts, indent=2)

        # If our first approach fails, try the original fallback approaches
        # Other methods are kept as fallbacks but the main method should work on most devices

        # Try dumpsys contact
        cmd = "adb shell dumpsys contact"
        success, output = await run_command(cmd)

        if success and "Contact" in output and len(output) > 100:
            # Parse the output from dumpsys
            contacts = []

            # Extract contacts with a regex pattern
            contact_pattern = re.compile(r"name=([^,]+),\s+number=([^,]+)")
            matches = contact_pattern.findall(output)

            for name, number in matches:
                contacts.append({
                    "name": name.strip(), 
                    "phone": number.strip()
                })

            if contacts:
                # Limit the results if needed
                if len(contacts) > limit:
                    contacts = contacts[:limit]
                return json.dumps(contacts, indent=2)

        # Further fallback methods continue...
        # These are kept for device compatibility but rarely needed now

        # If prior methods didn't work, try the different content URIs
        cmd = f"adb shell content query --uri content://com.android.contacts/data --projection display_name:data1:mimetype --limit {int(limit)}"
        success, output = await run_command(cmd)

        if not success or "usage:" in output:
            cmd = f"adb shell content query --uri content://contacts/data --projection display_name:data1:mimetype --limit {int(limit)}"
            success, output = await run_command(cmd)

        if not success or "usage:" in output:
            cmd = f"adb shell content query --uri content://contacts/phones --limit {int(limit)}"
            success, output = await run_command(cmd)

        if not success or "usage:" in output:
            cmd = f"adb shell content query --uri content://com.android.contacts/data/phones --limit {int(limit)}"
            success, output = await run_command(cmd)

        if not success or "usage:" in output:
            cmd = (
                'adb shell "sqlite3 /data/data/com.android.providers.contacts/databases/contacts2.db \'SELECT display_name, data1 FROM raw_contacts JOIN data ON (raw_contacts._id = data.raw_contact_id) WHERE mimetype_id = (SELECT _id FROM mimetypes WHERE mimetype = "vnd.android.cursor.item/phone_v2") LIMIT '
                + str(limit)
                + ";'\""
            )
            success, output = await run_command(cmd)

        if (
            not success
            or not output.strip()
            or "Error:" in output
            or "usage:" in output
        ):
            return "Failed to retrieve contacts. Contact access may require additional permissions or may not be supported on this device."

        # Process the output based on its format
        contacts = []

        if "|" in output:  # SQLite output format
            lines = output.strip().split("\n")
            for line in lines:
                if "|" in line:
                    parts = line.split("|")
                    if len(parts) >= 2:
                        # Only add if name and number are not empty
                        name = parts[0].strip()
                        number = parts[1].strip()
                        if name and number:
                            contact = {"name": name, "phone": number}
                            contacts.append(contact)
        else:  # Content provider output format
            rows = output.split("Row: ")
            # Skip empty first element if it exists
            if rows and not rows[0].strip():
                rows = rows[1:]

            for row in rows:
                if not row.strip():
                    continue

                contact = {}
                parts = row.split(", ")

                for part in parts:
                    if "=" in part:
                        key, value = part.split("=", 1)
                        # Only add non-NULL values
                        if value and value != "NULL" and value != "null":
                            contact[key.strip()] = value.strip()

                # Normalize fields before adding
                if contact:
                    if "display_name" in contact and "name" not in contact:
                        contact["name"] = contact["display_name"]
                    
                    # Standardize phone number field
                    if "number" in contact:
                        contact["phone"] = contact["number"]
                    elif "data1" in contact and contact.get("mimetype", "").endswith("phone_v2"):
                        contact["phone"] = contact["data1"]
                        
                    contacts.append(contact)

        if not contacts:
            return "No contacts found or unable to parse contacts data."

        # Limit the results if needed
        if limit and len(contacts) > limit:
            contacts = contacts[:limit]

        return json.dumps(contacts, indent=2)
    except Exception as e:
        return f"Error retrieving contacts: {str(e)}"


async def create_contact(name: str, phone_number: str, email: str = None) -> str:
    """Create a new contact on the phone.

    Opens the contact creation UI with pre-filled name and phone number,
    allowing the user to review and save the contact.

    Args:
        name (str): The contact's full name
        phone_number (str): The contact's phone number (For testing, 10086 is recommended)
        email (str, optional): The contact's email address

    Returns:
        str: Success message if the contact UI was launched, or an error message
             if the operation failed.
    
    Note:
        When testing this feature, it's recommended to use 10086 as the test phone number.
        This is China Mobile's customer service number, which is suitable for testing
        environments and easy to recognize.
    """
    # Check for connected device
    from ..core import check_device_connection

    connection_status = await check_device_connection()
    if "ready" not in connection_status:
        return connection_status

    # Check permissions
    has_permissions = await _check_contact_permissions()
    if not has_permissions:
        return "Cannot create contact. Permission may be denied. Please check your device settings."

    try:
        # Validate inputs
        name = name.strip()
        phone_number = phone_number.replace(" ", "").strip()

        if not name:
            return "Contact name cannot be empty"

        if not phone_number:
            return "Phone number cannot be empty"

        if email:
            email = email.strip()

        # Build the intent command
        intent_cmd = (
            'adb shell am start -a android.intent.action.INSERT '
            '-t vnd.android.cursor.dir/contact '
            f'--es name {shlex.quote(name)} '
            f'--es phone {shlex.quote(phone_number)} '
        )

        # Add email if provided
        if email:
            intent_cmd += f'--es email {shlex.quote(email)} '
        
        # Execute the command
        success, output = await run_command(intent_cmd)
        
        if not success or "Error" in output:
            return f"Failed to launch contact creation UI: {output}"
        
        # If we need to perform additional UI automation to click save button, we could add that here
        # But typically the user would manually review and save the contact after seeing the pre-filled form
        
        return f"Contact creation UI launched with pre-filled data for '{name}' with number '{phone_number}'. Please review and save the contact on your device."
        
    except Exception as e:
        return f"Error creating contact: {str(e)}"


async def create_contact_ui(name: str, phone: str) -> str:
    """Create a new contact with the given name and phone number using UI automation
    
    This function uses UI automation to create a new contact on the device. It:
    1. Opens the contact creation intent
    2. Pre-fills name and phone number fields
    3. Waits for the contact form to appear
    4. Analyzes the screen to find confirmation buttons
    5. Taps the confirmation button to save the contact
    
    Args:
        name (str): The contact's full name
        phone (str): The phone number for the contact
    
    Returns:
        str: JSON string with operation result containing:
            For successful operations:
                {
                    "status": "success",
                    "message": "Successfully created contact <name> with phone <phone>"
                }
            
            For partial success operations:
                {
                    "status": "partial_success",
                    "message": "Attempted to tap potential confirmation button location. Please verify contact creation."
                }
            
            For failed operations:
                {
                    "status": "error",
                    "message": "Error description"
                }
    
    Examples:
        # Create a contact with name and phone number
        result = await create_contact_ui("John Doe", "123-456-7890")
        
        # Create a contact using a test phone number (recommended for testing)
        result = await create_contact_ui("Test Contact", "10086")
            
    Note:
        When testing this feature, it's recommended to use 10086 as the test phone number.
        This is China Mobile's customer service number, which is suitable for testing
        environments and easy to recognize.
    """
    try:
        # Import app launcher functions
        from .apps import launch_intent
        from .ui_enhanced import wait_for_element
        from .screen_interface import analyze_screen, tap_screen
        import json
        import logging
        
        logger = logging.getLogger("phone_mcp")
        
        # Step 1: Launch the contact creation intent
        extras = {
            "name": name,
            "phone": phone
        }
        intent_result = await launch_intent(
            "android.intent.action.INSERT", 
            "vnd.android.cursor.dir/contact",
            extras
        )
        
        intent_data = json.loads(intent_result)
        if intent_data.get("status") != "success":
            return intent_result
        
        # Step 2: Wait for the contact form to appear
        await wait_for_element("text", "Contact", timeout=5)  # Wait for Contact form
        
        # Step 3: Analyze screen to find confirmation button
        screen_result = await analyze_screen()
        screen_data = json.loads(screen_result)
        
        if screen_data.get("status") != "success":
            return json.dumps({
                "status": "error",
                "message": "Failed to analyze screen to find confirmation button"
            })
        
        # Look for confirmation button - common patterns
        confirmation_buttons = ["Save", "Done", "Confirm", "OK", "✓", "√"]
        found_button = None
        
        # Check suggested actions first
        for action in screen_data.get("suggested_actions", []):
            if action.get("action") == "tap_element":
                text = action.get("element_text", "")
                if text in confirmation_buttons or any(btn in text for btn in confirmation_buttons):
                    found_button = text
                    break
        
        # If not found in suggested actions, search in all clickable elements
        if not found_button:
            clickables = screen_data.get("screen_analysis", {}).get("notable_clickables", [])
            for element in clickables:
                text = element.get("text", "")
                if text in confirmation_buttons or any(btn in text for btn in confirmation_buttons):
                    found_button = text
                    break
        
        # As a last resort, look for confirmation buttons in top-right corner
        if not found_button:
            # Try to tap top-right corner where save button is often located
            size = screen_data.get("screen_size", {})
            width = size.get("width", 1080)
            
            # Create tap action at approximately 90% of width and 10% of height
            tap_x = int(width * 0.9)
            tap_y = int(size.get("height", 1920) * 0.1)
            
            tap_result = await tap_screen(tap_x, tap_y)
            tap_data = json.loads(tap_result)
            
            return json.dumps({
                "status": "partial_success" if tap_data.get("status") == "success" else "error",
                "message": "Attempted to tap potential confirmation button location. Please verify contact creation."
            })
        
        # Step 4: Click the confirmation button if found
        if found_button:
            # Import in a narrower scope to avoid circular imports
            from .screen_interface import interact_with_screen
            tap_result = await interact_with_screen("tap", {"element_text": found_button})
            tap_data = json.loads(tap_result)
            
            if tap_data.get("status") == "success":
                return json.dumps({
                    "status": "success",
                    "message": f"Successfully created contact {name} with phone {phone}"
                })
            else:
                return json.dumps({
                    "status": "error",
                    "message": f"Failed to tap confirmation button: {tap_data.get('message')}"
                })
        else:
            return json.dumps({
                "status": "error",
                "message": "Could not find confirmation button"
            })
    
    except Exception as e:
        logger.error(f"Error creating contact: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"Failed to create contact: {str(e)}"
        })
