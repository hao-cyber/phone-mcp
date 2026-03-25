"""UI inspection functions for Phone MCP.
This module provides functions to inspect and interact with UI elements on the device.
"""

import asyncio
import json
import re
import os
import tempfile
import xml.etree.ElementTree as ET
import logging
import shlex
from ..core import run_command, check_device_connection

logger = logging.getLogger("phone_mcp")


async def dump_ui():
    """Dump the current UI hierarchy from the device.
    
    This function captures the current UI state of the device screen and returns
    it in a structured format. It uses the uiautomator tool to create an XML dump
    of the UI hierarchy.
    
    Returns:
        str: JSON string containing:
            {
                "status": "success" or "error",
                "message": Error message if status is error,
                "elements": [
                    {
                        "resource_id": str,
                        "class_name": str,
                        "package": str,
                        "content_desc": str,
                        "text": str,
                        "clickable": bool,
                        "bounds": str,
                        "center_x": int (if bounds available),
                        "center_y": int (if bounds available)
                    },
                    ...
                ]
            }
            
    Raises:
        - Device connection errors
        - Permission errors when accessing UI
        - XML parsing errors
        - File system errors when handling temporary files
    
    Notes:
        - Requires USB debugging to be enabled
        - Device screen must be on and unlocked
        - May fail if the app has special security measures
    """
    # Check for connected device
    connection_status = await check_device_connection()
    if "ready" not in connection_status:
        logger.error("Device not connected or not ready")
        return connection_status

    # Create temp file path
    try:
        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, "ui_dump.xml")
        logger.debug(f"Temp file path: {temp_file}")
    except Exception as e:
        error_msg = f"Failed to create temp file: {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "status": "error",
            "message": error_msg
        }, indent=2)

    # Execute UI dump on device
    logger.debug("Starting UI dump on device")
    cmd = "adb shell uiautomator dump"
    success, output = await run_command(cmd)
    logger.debug(f"UI dump command result: {success}, output: {output}")

    if not success:
        error_msg = f"UI dump failed: {output}"
        logger.error(error_msg)
        return json.dumps({
            "status": "error",
            "message": error_msg
        }, indent=2)

    # Get dump file path
    device_file_path = ""
    match = re.search(r"UI hierchary dumped to: (.*\.xml)", output)
    if not match:
        error_msg = "Could not find dump file path"
        logger.error(error_msg)
        return json.dumps({
            "status": "error",
            "message": error_msg
        }, indent=2)
        
    device_file_path = match.group(1)
    logger.debug(f"Device dump file path: {device_file_path}")

    # Pull file from device
    cmd = f"adb pull {shlex.quote(device_file_path)} {shlex.quote(temp_file)}"
    success, output = await run_command(cmd)
    
    if not success:
        error_msg = f"Could not pull dump file from device: {output}"
        logger.error(error_msg)
        return json.dumps({
            "status": "error",
            "message": error_msg
        }, indent=2)

    # Parse XML file
    try:
        tree = ET.parse(temp_file)
        root = tree.getroot()
        
        elements = []
        for elem in root.iter():
            element_data = {
                "resource_id": elem.attrib.get('resource-id', ''),
                "class_name": elem.attrib.get('class', ''),
                "package": elem.attrib.get('package', ''),
                "content_desc": elem.attrib.get('content-desc', ''),
                "text": elem.attrib.get('text', ''),
                "clickable": elem.attrib.get('clickable', 'false').lower() == 'true',
                "bounds": elem.attrib.get('bounds', '')
            }
            
            # Parse bounds if available
            bounds = elem.attrib.get('bounds', '')
            if bounds:
                try:
                    bounds = bounds.replace('][', ',').replace('[', '').replace(']', '')
                    coords = bounds.split(',')
                    if len(coords) == 4:
                        x1, y1, x2, y2 = map(int, coords)
                        element_data["center_x"] = (x1 + x2) // 2
                        element_data["center_y"] = (y1 + y2) // 2
                except (ValueError, IndexError) as e:
                    logger.warning(f"Failed to parse element boundaries: {bounds}, error: {str(e)}")
            
            elements.append(element_data)
        
        return json.dumps({
            "status": "success",
            "elements": elements
        }, indent=2)
        
    except ET.ParseError as e:
        error_msg = f"Failed to parse XML file: {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "status": "error",
            "message": error_msg
        }, indent=2)
    except Exception as e:
        error_msg = f"Error processing UI dump: {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "status": "error",
            "message": error_msg
        }, indent=2)
    finally:
        # Clean up temp file
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        except Exception as e:
            logger.warning(f"Failed to clean up temp file: {str(e)}")


def process_ui_xml(xml_content):
    """Process UI XML content and convert to simplified JSON.

    Args:
        xml_content (str): XML string from UI Automator

    Returns:
        str: JSON string with simplified UI elements
    """
    # Parse the XML
    root = ET.fromstring(xml_content)

    # Extract elements into a simplified structure
    elements = []

    for node in root.findall(".//node"):
        element = {}

        # Extract key attributes
        for attr in [
            "resource-id",
            "class",
            "package",
            "text",
            "content-desc",
            "clickable",
            "checkable",
            "checked",
            "enabled",
            "password",
            "selected",
        ]:
            if attr in node.attrib:
                # Convert boolean attributes
                if attr in [
                    "clickable",
                    "checkable",
                    "checked",
                    "enabled",
                    "password",
                    "selected",
                ]:
                    element[attr.replace("-", "_")] = node.attrib[attr] == "true"
                else:
                    element[attr.replace("-", "_")] = node.attrib[attr]

        # Extract bounds as string for compatibility with existing code
        if "bounds" in node.attrib:
            element["bounds"] = node.attrib["bounds"]
            
            # Also extract parsed bounds
            bounds_str = node.attrib["bounds"]
            bounds_match = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds_str)
            if bounds_match:
                x1, y1, x2, y2 = map(int, bounds_match.groups())
                element["bounds_parsed"] = {
                    "left": x1,
                    "top": y1,
                    "right": x2,
                    "bottom": y2
                }
                element["center_x"] = (x1 + x2) // 2
                element["center_y"] = (y1 + y2) // 2

        # Add element if it has useful info
        if element:
            elements.append(element)

    if not elements:
        logger.warning("No UI elements found")
        
    return json.dumps(
        {"status": "success", "count": len(elements), "elements": elements}, indent=2
    )


async def find_element_by_text(text, partial_match=False):
    """Find UI element by text content.

    Args:
        text (str): Text to search for
        partial_match (bool): If True, find elements containing the text. If False,
                             only exact matches are returned.

    Returns:
        str: JSON string with matching elements or error message
    """
    # Get the full UI dump first
    dump_response = await dump_ui()

    try:
        dump_data = json.loads(dump_response)

        if dump_data.get("status") != "success":
            return dump_response  # Return error from dump_ui

        # Find matching elements
        matches = []
        for element in dump_data.get("elements", []):
            element_text = element.get("text", "")

            if (partial_match and text in element_text) or element_text == text:
                matches.append(element)

        return json.dumps(
            {
                "status": "success",
                "query": text,
                "partial_match": partial_match,
                "count": len(matches),
                "elements": matches,
            },
            indent=2,
        )
    except json.JSONDecodeError:
        return json.dumps(
            {
                "status": "error",
                "message": "Failed to process UI data",
                "raw_response": dump_response[
                    :500
                ],  # Include part of the raw response for debugging
            },
            indent=2,
        )


async def find_element_by_id(resource_id, package_name=None):
    """Find UI element by resource ID.

    Args:
        resource_id (str): Resource ID to search for
        package_name (str, optional): Package name to limit search to

    Returns:
        str: JSON string with matching elements or error message
    """
    # Get the full UI dump first
    dump_response = await dump_ui()

    try:
        dump_data = json.loads(dump_response)

        if dump_data.get("status") != "success":
            return dump_response  # Return error from dump_ui

        # Find matching elements
        matches = []
        for element in dump_data.get("elements", []):
            element_id = element.get("resource_id", "")
            element_package = element.get("package", "")

            # Check if ID matches and (no package filter or package matches)
            if resource_id in element_id and (
                package_name is None or package_name in element_package
            ):
                matches.append(element)

        return json.dumps(
            {
                "status": "success",
                "query": resource_id,
                "package_filter": package_name,
                "count": len(matches),
                "elements": matches,
            },
            indent=2,
        )
    except json.JSONDecodeError:
        return json.dumps(
            {
                "status": "error",
                "message": "Failed to process UI data",
                "raw_response": dump_response[
                    :500
                ],  # Include part of the raw response for debugging
            },
            indent=2,
        )


async def tap_element(element_json):
    """Tap on a UI element by using its center coordinates.

    Args:
        element_json (str): JSON representation of the element with bounds

    Returns:
        str: Success or error message
    """
    try:
        element = json.loads(element_json)
        
        # Try to get center coordinates directly
        center_x = element.get("center_x")
        center_y = element.get("center_y")
        
        if not center_x or not center_y:
            # Check for parsed bounds
            bounds_parsed = element.get("bounds_parsed")
            if bounds_parsed:
                center_x = (bounds_parsed.get("left", 0) + bounds_parsed.get("right", 0)) // 2
                center_y = (bounds_parsed.get("top", 0) + bounds_parsed.get("bottom", 0)) // 2
            else:
                # Try to parse from bounds string
                bounds = element.get("bounds", "")
                if bounds and isinstance(bounds, str):
                    bounds_match = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds)
                    if bounds_match:
                        x1, y1, x2, y2 = map(int, bounds_match.groups())
                        center_x = (x1 + x2) // 2
                        center_y = (y1 + y2) // 2

        if not center_x or not center_y:
            return json.dumps({
                "status": "error",
                "message": "Could not determine element coordinates"
            })

        # Now use our existing tap function
        from .interactions import tap_screen
        return await tap_screen(center_x, center_y)

    except json.JSONDecodeError:
        return json.dumps({
            "status": "error",
            "message": "Invalid element JSON format"
        })
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Error tapping element: {str(e)}"
        })
