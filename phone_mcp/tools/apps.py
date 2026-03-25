"""App-related phone control functions."""

import json
import re
import logging
import shlex
from ..core import run_command, check_device_connection
from typing import Optional, Dict

logger = logging.getLogger("phone_mcp")


async def list_installed_apps(
    only_system=False, only_third_party=False, page=1, page_size=10, basic=True
):
    """List installed applications on the device with pagination support.

    Args:
        only_system (bool): If True, only show system apps
        only_third_party (bool): If True, only show third-party apps
        page (int): Page number (starts from 1)
        page_size (int): Number of items per page
        basic (bool): If True, only return basic info (faster loading, default behavior)

    Returns:
        str: JSON string containing:
            {
                "status": "success" or "error",
                "message": Error message if status is error,
                "total_count": Total number of apps,
                "total_pages": Total number of pages,
                "current_page": Current page number,
                "page_size": Number of items per page,
                "apps": [
                    {
                        "package_name": str,
                        "app_name": str,
                        "system_app": bool,
                        "version_name": str (if not basic),
                        "version_code": str (if not basic),
                        "install_time": str (if not basic)
                    },
                    ...
                ]
            }
    """
    # Ensure page and page_size are integers
    try:
        page = int(page)
        page_size = int(page_size)
    except (ValueError, TypeError):
        return json.dumps({
            "status": "error",
            "message": "Invalid page or page_size parameter. Must be integers."
        }, indent=2)

    # Check for connected device
    connection_status = await check_device_connection()
    if "ready" not in connection_status:
        return connection_status

    # Build the command based on options
    if only_system:
        cmd = "adb shell cmd package list packages -s"  # System packages only
    elif only_third_party:
        cmd = "adb shell cmd package list packages -3"  # Third-party packages only
    else:
        cmd = "adb shell cmd package list packages"  # All packages

    success, output = await run_command(cmd)

    if not success:
        return json.dumps(
            {
                "status": "error",
                "message": "Failed to get installed apps",
                "output": output,
            },
            indent=2,
        )

    # Process the output - convert package list to array
    all_packages = []
    for line in output.strip().split("\n"):
        if line.startswith("package:"):
            package_name = line[8:].strip()  # Remove "package:" prefix
            all_packages.append(package_name)

    # Calculate pagination
    total_count = len(all_packages)
    total_pages = (total_count + page_size - 1) // page_size
    
    # Validate page number
    if page < 1:
        page = 1
    elif page > total_pages:
        page = total_pages if total_pages > 0 else 1
    
    # Calculate slice indices for pagination
    start_idx = (page - 1) * page_size
    end_idx = min(start_idx + page_size, total_count)
    
    # Get packages for current page
    current_packages = all_packages[start_idx:end_idx]
    
    # Process packages based on basic/detailed mode
    apps_info = []
    for package_name in current_packages:
        app_info = {"package_name": package_name}
        
        # Get app label (name)
        cmd = f'adb shell cmd package get-app-label {shlex.quote(package_name)}'
        success, label_output = await run_command(cmd)
        if success and label_output:
            app_info["app_name"] = label_output.strip()
        else:
            app_info["app_name"] = package_name
            
        # Check if system app
        cmd = f'adb shell pm path {shlex.quote(package_name)}'
        success, path_output = await run_command(cmd)
        app_info["system_app"] = success and "system" in path_output.lower()
        
        if not basic:
            # Get detailed info
            cmd = f'adb shell dumpsys package {shlex.quote(package_name)}'
            success, info_output = await run_command(cmd)
            if success:
                # Parse version info
                version_name = re.search(r"versionName=([^=\s]+)", info_output)
                if version_name:
                    app_info["version_name"] = version_name.group(1)
                    
                version_code = re.search(r"versionCode=(\d+)", info_output)
                if version_code:
                    app_info["version_code"] = version_code.group(1)
                    
                # Parse install time
                first_install = re.search(r"firstInstallTime=([^=\s]+)", info_output)
                if first_install:
                    app_info["install_time"] = first_install.group(1)
        
        apps_info.append(app_info)
    
    # Create the final result
    result = {
        "status": "success",
        "total_count": total_count,
        "total_pages": total_pages,
        "current_page": page,
        "page_size": page_size,
        "apps": apps_info
    }
    
    if only_system:
        result["type"] = "system"
    elif only_third_party:
        result["type"] = "third_party"
    
    return json.dumps(result, indent=2)


async def list_app_activities(package_name: str):
    """List all activities in a specific app package.

    Args:
        package_name (str): Package name of the app

    Returns:
        str: JSON string with list of activities or error message
    """
    # Check for connected device
    connection_status = await check_device_connection()
    if "ready" not in connection_status:
        return connection_status

    # Build the command to query activities
    cmd = f"adb shell cmd package query-activities -a android.intent.action.MAIN -c android.intent.category.LAUNCHER --components {shlex.quote(package_name)}"
    success, output = await run_command(cmd)

    if not success:
        return json.dumps(
            {
                "status": "error",
                "message": f"Failed to get activities for {package_name}",
                "output": output,
            },
            indent=2,
        )

    activities = []

    # Process the output - extract activities
    for line in output.strip().split("\n"):
        if package_name in line:
            # Format: packageName/activityName
            parts = line.strip().split()
            if len(parts) > 0:
                activity = parts[0].strip()
                activities.append(activity)

    return json.dumps(
        {
            "status": "success",
            "package": package_name,
            "count": len(activities),
            "activities": activities,
        },
        indent=2,
    )


async def terminate_app(package_name: str):
    """Force stop an application on the device.

    Args:
        package_name (str): Package name of the app to terminate

    Returns:
        str: Success or error message
    """
    # Check for connected device
    connection_status = await check_device_connection()
    if "ready" not in connection_status:
        return connection_status

    # Verify the package exists
    cmd = f"adb shell pm list packages | grep {shlex.quote(package_name)}"
    success, output = await run_command(cmd)

    if not success or package_name not in output:
        # Try an exact match instead of grep
        verify_cmd = "adb shell pm list packages"
        success, verify_output = await run_command(verify_cmd)

        package_exists = False
        if success:
            for line in verify_output.strip().split("\n"):
                if line.strip() == f"package:{package_name}":
                    package_exists = True
                    break

        if not package_exists:
            return f"Package {package_name} not found on device"

    # Force stop the application
    cmd = f"adb shell am force-stop {shlex.quote(package_name)}"
    success, output = await run_command(cmd)

    if success:
        return f"Successfully terminated {package_name}"
    else:
        return f"Failed to terminate app: {output}"


async def set_alarm(hour: int, minute: int, label: str = "Alarm") -> str:
    """Set an alarm on the phone.

    Creates a new alarm with the specified time and label using the default
    clock application.

    Args:
        hour (int): Hour in 24-hour format (0-23)
        minute (int): Minute (0-59)
        label (str): Optional label for the alarm (default: "Alarm")

    Returns:
        str: Success message if the alarm was set, or an error message
             if the alarm could not be created.
    """
    # Check for connected device
    connection_status = await check_device_connection()
    if "ready" not in connection_status:
        return connection_status

    # Validate time inputs
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return "Invalid time. Hour must be 0-23 and minute must be 0-59."

    # Format time for display
    time_str = f"{hour:02d}:{minute:02d}"
    # Create the alarm using the alarm clock intent
    cmd = (
        f"adb shell am start -a android.intent.action.SET_ALARM "
        f"-e android.intent.extra.alarm.HOUR {hour} "
        f"-e android.intent.extra.alarm.MINUTES {minute} "
        f"-e android.intent.extra.alarm.MESSAGE {shlex.quote(label)} "
        f"-e android.intent.extra.alarm.SKIP_UI true"
    )

    success, output = await run_command(cmd)

    if success:
        return f"Alarm set for {time_str} with label '{label}'"
    else:
        return f"Failed to set alarm: {output}"


async def launch_app_activity(package_name: str, activity_name: str = None) -> str:
    """Launch an app using package name and optionally an activity name
    
    This function uses adb to start an application on the device either by package name
    or by specifying both package and activity. It provides reliable app launching across
    different Android devices and versions.
    
    Args:
        package_name (str): The package name of the app to launch (e.g., "com.android.contacts")
        activity_name (str): The specific activity to launch. If not provided,
                                      launches the app's main activity. Defaults to None.
    
    Returns:
        str: JSON string with operation result:
            For successful operations:
                {
                    "status": "success",
                    "message": "Successfully launched <package_name>"
                }
            
            For failed operations:
                {
                    "status": "error",
                    "message": "Failed to launch app: <error details>"
                }
    
    Examples:
        # Launch an app using just the package name
        result = await launch_app_activity("com.android.contacts")
        
        # Launch a specific activity within an app
        result = await launch_app_activity("com.android.dialer", "com.android.dialer.DialtactsActivity")
        
        # Launch Android settings
        result = await launch_app_activity("com.android.settings")
    """
    try:
        if activity_name:
            # Launch specific activity
            cmd = f"adb shell am start -n {shlex.quote(package_name + '/' + activity_name)}"
        else:
            # Launch app's main activity
            cmd = f"adb shell monkey -p {shlex.quote(package_name)} -c android.intent.category.LAUNCHER 1"
        
        success, output = await run_command(cmd)
        
        if success:
            return json.dumps({
                "status": "success",
                "message": f"Successfully launched {package_name}"
            })
        else:
            return json.dumps({
                "status": "error",
                "message": f"Failed to launch app: {output}"
            })
    except Exception as e:
        logger.error(f"Error launching app {package_name}: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"Failed to launch app: {str(e)}"
        })


async def launch_intent(intent_action: str, intent_type: Optional[str] = None, extras: Optional[Dict[str, str]] = None) -> str:
    """Launch an activity using Android intent system
    
    This function allows launching activities using Android's intent system, which can be used
    to perform various actions like opening the contacts app in "add new contact" mode,
    opening URLs, or sharing content between apps.
    
    Args:
        intent_action (str): The action to perform (e.g., "android.intent.action.INSERT",
                          "android.intent.action.VIEW", "android.intent.action.SEND")
        intent_type (str, optional): The MIME type for the intent (e.g., "vnd.android.cursor.dir/contact",
                                  "text/plain", "image/jpeg"). Defaults to None.
        extras (Dict[str, str], optional): Extra data to pass with the intent as key-value pairs.
                                        Useful for pre-populating fields or passing data. Defaults to None.
    
    Returns:
        str: JSON string with operation result:
            For successful operations:
                {
                    "status": "success",
                    "message": "Successfully launched intent: <intent_action>"
                }
            
            For failed operations:
                {
                    "status": "error",
                    "message": "Failed to launch intent: <error details>"
                }
    
    Examples:
        # Open contacts app in "add new contact" mode
        extras = {"name": "John Doe", "phone": "1234567890"}
        result = await launch_intent(
            "android.intent.action.INSERT", 
            "vnd.android.cursor.dir/contact", 
            extras
        )
        
        # Open URL in browser
        result = await launch_intent(
            "android.intent.action.VIEW",
            None,
            {"uri": "https://www.example.com"}
        )
        
        # Share text
        result = await launch_intent(
            "android.intent.action.SEND",
            "text/plain",
            {"android.intent.extra.TEXT": "Hello world!"}
        )
    """
    try:
        # Construct base command
        cmd = f"adb shell am start -a {shlex.quote(intent_action)}"

        # Add type if provided
        if intent_type:
            cmd += f" -t {shlex.quote(intent_type)}"

        # Add extras if provided
        if extras:
            for key, value in extras.items():
                cmd += f' --es {shlex.quote(key)} {shlex.quote(value)}'
        
        success, output = await run_command(cmd)
        
        if success:
            return json.dumps({
                "status": "success",
                "message": f"Successfully launched intent: {intent_action}"
            })
        else:
            return json.dumps({
                "status": "error",
                "message": f"Failed to launch intent: {output}"
            })
    except Exception as e:
        logger.error(f"Error launching intent {intent_action}: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"Failed to launch intent: {str(e)}"
        })
