# -*- coding: utf-8 -*-
"""
Screen Analysis and Interaction Interface - Provides structured screen information and unified interaction methods
Integrates multiple tools, reduces redundant functionality, making it easier for models to understand and use
"""

import json
import asyncio
import logging
import time
from typing import Dict, List, Any, Optional, Tuple

# Import base functionality modules
from .ui import dump_ui, find_element_by_text, find_element_by_id
from .ui_enhanced import (
    find_element_by_content_desc, find_element_by_class, 
    find_clickable_elements, wait_for_element, scroll_to_element
)
from .interactions import tap_screen, swipe_screen, press_key, input_text, get_screen_size
from .media import take_screenshot

logger = logging.getLogger("phone_mcp")

class UIElement:
    """Class representing a UI element, containing its properties and interaction methods
    
    Attributes:
        text (str): Element text content
        resource_id (str): Element resource ID
        class_name (str): Element class name
        content_desc (str): Element content description
        clickable (bool): Whether the element is clickable
        bounds (str): Element boundary coordinates string "[x1,y1][x2,y2]"
        x1, y1, x2, y2 (int): Boundary coordinate values
        center_x, center_y (int): Element center point coordinates
    
    Methods:
        to_dict(): Convert element to dictionary format
        tap(): Tap the center of the element
    """
    
    def __init__(self, element_data: Dict[str, Any]):
        """Initialize UI element
        
        Args:
            element_data: Dictionary containing element properties
        """
        self.data = element_data
        self.text = element_data.get("text", "")
        self.resource_id = element_data.get("resource_id", "")
        self.class_name = element_data.get("class_name", "")
        self.content_desc = element_data.get("content_desc", "")
        self.clickable = element_data.get("clickable", False)
        self.bounds = element_data.get("bounds", "")
        
        # Parse boundaries to get coordinates
        if self.bounds and isinstance(self.bounds, str):
            try:
                coords = self.bounds.replace("[", "").replace("]", "").split(",")
                if len(coords) == 4:
                    self.x1 = int(coords[0])
                    self.y1 = int(coords[1])
                    self.x2 = int(coords[2])
                    self.y2 = int(coords[3])
                    self.center_x = (self.x1 + self.x2) // 2
                    self.center_y = (self.y1 + self.y2) // 2
            except Exception as e:
                logger.warning(f"Failed to parse element boundaries: {self.bounds}, error: {str(e)}")
        elif self.bounds and isinstance(self.bounds, dict):
            # If bounds is in dictionary format, try to extract coordinates from it
            try:
                if all(k in self.bounds for k in ["left", "top", "right", "bottom"]):
                    self.x1 = int(self.bounds.get("left", 0))
                    self.y1 = int(self.bounds.get("top", 0))
                    self.x2 = int(self.bounds.get("right", 0))
                    self.y2 = int(self.bounds.get("bottom", 0))
                    self.center_x = (self.x1 + self.x2) // 2
                    self.center_y = (self.y1 + self.y2) // 2
            except Exception as e:
                logger.warning(f"Failed to parse element boundaries from dictionary: {self.bounds}, error: {str(e)}")
            
    def to_dict(self) -> Dict[str, Any]:
        """Convert UI element to dictionary format for JSON serialization
        
        Returns:
            Dictionary containing all element attributes
        """
        result = {
            "text": self.text,
            "resource_id": self.resource_id,
            "class_name": self.class_name,
            "content_desc": self.content_desc,
            "clickable": self.clickable,
            "bounds": self.bounds,
        }
        
        if hasattr(self, "center_x") and hasattr(self, "center_y"):
            result["center_x"] = self.center_x
            result["center_y"] = self.center_y
            
        return result
        
    async def tap(self) -> str:
        """Tap the center of this element
        
        Returns:
            str: JSON string of operation result, containing status and message
        """
        if hasattr(self, "center_x") and hasattr(self, "center_y"):
            return await tap_screen(self.center_x, self.center_y)
        return json.dumps({"status": "error", "message": "Element does not have valid coordinates"})


async def get_screen_info() -> str:
    """Get detailed information about the current screen, including all visible elements, text, coordinates, etc.
    
    This function gets the complete UI hierarchy, parses all element attributes, and extracts text and clickable elements.
    
    Returns:
        str: Screen information in JSON format, containing:
            - status: Operation status ("success" or "error")
            - screen_size: Screen size (width, height)
            - all_elements_count: Total number of elements
            - clickable_elements_count: Number of clickable elements
            - text_elements_count: Number of text elements
            - text_elements: List of elements containing text
            - clickable_elements: List of clickable elements
            - timestamp: Time when information was collected
    
    Example:
        ```
        {
          "status": "success", 
          "screen_size": {"width": 1080, "height": 2340},
          "all_elements_count": 156,
          "text_elements": [
            {"text": "Settings", "bounds": "[52,1688][228,1775]", "center_x": 140, "center_y": 1732}
          ]
        }
        ```
    """
    # 获取屏幕尺寸
    size_result = await get_screen_size()
    try:
        screen_size = json.loads(size_result)
    except:
        screen_size = {"width": 1080, "height": 1920}  # 默认尺寸
    
    # 首先尝试常规UI dump
    ui_dump = await dump_ui()
    text_elements = []
    clickable_elements = []
    all_elements = []
    
    # 处理JSON数据
    try:
        ui_data = json.loads(ui_dump)
        
        # 尝试从JSON获取可点击元素
        clickable_result = await find_clickable_elements()
        clickable_elements = json.loads(clickable_result).get("elements", [])
        
        # 从JSON解析所有元素 
        if "elements" in ui_data:
            for elem_data in ui_data["elements"]:
                element = UIElement(elem_data)
                all_elements.append(element.to_dict())
                
                # 提取文本元素
                if element.text and element.text.strip():
                    text_element = {
                        "text": element.text,
                        "bounds": element.bounds
                    }
                    if hasattr(element, "center_x") and hasattr(element, "center_y"):
                        text_element["center_x"] = element.center_x
                        text_element["center_y"] = element.center_y
                    text_elements.append(text_element)
        
        logger.info(f"JSON解析找到 {len(text_elements)} 个文本元素和 {len(clickable_elements)} 个可点击元素")
    except Exception as e:
        logger.warning(f"JSON解析失败: {str(e)}，将尝试XML方法")
    
    # 如果JSON解析结果不足，或者完全失败，尝试XML解析
    if len(text_elements) < 5:
        logger.info("尝试使用XML方法提取UI元素...")
        
        from ..core import run_command
        import os
        import xml.etree.ElementTree as ET
        
        # 直接使用uiautomator dump命令获取XML
        xml_cmd = "adb shell uiautomator dump /sdcard/window_dump.xml"
        success, output = await run_command(xml_cmd)
        
        if success:
            # 拉取XML文件
            pull_cmd = "adb pull /sdcard/window_dump.xml ./window_dump.xml"
            pull_success, pull_output = await run_command(pull_cmd)
            
            if pull_success and os.path.exists("./window_dump.xml"):
                try:
                    # 解析XML文件
                    tree = ET.parse("./window_dump.xml")
                    root = tree.getroot()
                    
                    # 提取文本元素
                    xml_text_elements = []
                    for elem in root.findall(".//*[@text]"):
                        text = elem.attrib.get('text', '').strip()
                        if text:
                            bounds = elem.attrib.get('bounds', '')
                            clickable = elem.attrib.get('clickable', 'false') == 'true'
                            
                            # 解析bounds
                            center_x = None
                            center_y = None
                            if bounds:
                                try:
                                    bounds = bounds.replace('][', ',').replace('[', '').replace(']', '')
                                    coords = bounds.split(',')
                                    if len(coords) == 4:
                                        x1 = int(coords[0])
                                        y1 = int(coords[1])
                                        x2 = int(coords[2])
                                        y2 = int(coords[3])
                                        center_x = (x1 + x2) // 2
                                        center_y = (y1 + y2) // 2
                                except Exception as e:
                                    pass
                            
                            # 添加到文本元素列表
                            xml_text_elements.append({
                                "text": text,
                                "bounds": bounds,
                                "center_x": center_x,
                                "center_y": center_y,
                                "clickable": clickable
                            })
                    
                    # 提取可点击元素
                    xml_clickable_elements = []
                    for elem in root.findall(".//*[@clickable='true']"):
                        content_desc = elem.attrib.get('content-desc', '')
                        text = elem.attrib.get('text', '')
                        bounds = elem.attrib.get('bounds', '')
                        
                        # 仅当元素有文本、内容描述或位置信息时才添加
                        if text or content_desc or bounds:
                            # 解析bounds
                            center_x = None
                            center_y = None
                            if bounds:
                                try:
                                    bounds = bounds.replace('][', ',').replace('[', '').replace(']', '')
                                    coords = bounds.split(',')
                                    if len(coords) == 4:
                                        x1 = int(coords[0])
                                        y1 = int(coords[1])
                                        x2 = int(coords[2])
                                        y2 = int(coords[3])
                                        center_x = (x1 + x2) // 2
                                        center_y = (y1 + y2) // 2
                                except Exception as e:
                                    pass
                            
                            # 添加到可点击元素列表
                            xml_clickable_elements.append({
                                "text": text,
                                "content_desc": content_desc,
                                "bounds": bounds,
                                "center_x": center_x,
                                "center_y": center_y
                            })
                    
                    # 如果XML解析找到了更多数据，使用XML结果
                    if len(xml_text_elements) > len(text_elements):
                        logger.info(f"XML解析获得更多文本元素: {len(xml_text_elements)} vs JSON的 {len(text_elements)}")
                        text_elements = xml_text_elements
                    
                    if len(xml_clickable_elements) > len(clickable_elements):
                        logger.info(f"XML解析获得更多可点击元素: {len(xml_clickable_elements)} vs JSON的 {len(clickable_elements)}")
                        clickable_elements = xml_clickable_elements
                    
                    # 合并所有元素
                    all_xml_elements = []
                    for elem in root.findall(".//*"):
                        # 基本属性
                        element_dict = {
                            "resource_id": elem.attrib.get('resource-id', ''),
                            "class_name": elem.attrib.get('class', ''),
                            "package": elem.attrib.get('package', ''),
                            "content_desc": elem.attrib.get('content-desc', ''),
                            "text": elem.attrib.get('text', ''),
                            "clickable": elem.attrib.get('clickable', 'false') == 'true',
                            "bounds": elem.attrib.get('bounds', '')
                        }
                        
                        # 解析bounds
                        bounds = elem.attrib.get('bounds', '')
                        if bounds:
                            try:
                                bounds = bounds.replace('][', ',').replace('[', '').replace(']', '')
                                coords = bounds.split(',')
                                if len(coords) == 4:
                                    x1 = int(coords[0])
                                    y1 = int(coords[1])
                                    x2 = int(coords[2])
                                    y2 = int(coords[3])
                                    element_dict["center_x"] = (x1 + x2) // 2
                                    element_dict["center_y"] = (y1 + y2) // 2
                            except:
                                pass
                        
                        # 添加到所有元素列表
                        all_xml_elements.append(element_dict)
                    
                    if len(all_xml_elements) > len(all_elements):
                        all_elements = all_xml_elements
                    
                    logger.info(f"XML解析完成，共找到 {len(all_elements)} 个元素")
                    
                    # 清理临时文件
                    try:
                        os.remove("./window_dump.xml")
                    except:
                        pass
                        
                except Exception as e:
                    logger.error(f"XML解析失败: {str(e)}")
    
    # 构建结果
    result = {
        "status": "success",
        "screen_size": {
            "width": screen_size.get("width", 0),
            "height": screen_size.get("height", 0),
        },
        "all_elements_count": len(all_elements),
        "clickable_elements_count": len(clickable_elements),
        "text_elements_count": len(text_elements),
        "text_elements": text_elements,
        "clickable_elements": clickable_elements,
        "all_elements": all_elements,
        "timestamp": time.time(),
    }
    
    # 如果没有找到任何元素，标记为失败
    if len(text_elements) == 0 and len(clickable_elements) == 0:
        result["status"] = "error"
        result["message"] = "未能提取到任何UI元素"
    
    return json.dumps(result, ensure_ascii=False, indent=2)


async def analyze_screen() -> str:
    """Analyze the current screen and provide structured information
    
    This function analyzes the current screen content, extracts useful information and organizes it by category, including:
    - Text elements classified by region (top/middle/bottom)
    - UI pattern detection (such as list view, bottom navigation bar, etc.)
    - Possible interaction suggestions
    
    Suitable for understanding screen content and deciding next steps.
    
    Returns:
        str: Screen analysis results in JSON format, containing:
            - status: Operation status ("success" or "error")
            - screen_size: Screen size
            - screen_analysis: Analysis results including text elements, UI patterns, clickable elements, etc.
            - suggested_actions: Suggested interaction operations
            - screenshot_path: Screenshot save path (if available)
    
    Example:
        ```
        {
          "status": "success",
          "screen_analysis": {
            "text_elements": {
              "top": [{"text": "Settings", "center_x": 540, "center_y": 89}],
              "middle": [{"text": "WLAN", "center_x": 270, "center_y": 614}],
              "bottom": [{"text": "OK", "center_x": 540, "center_y": 2200}]
            },
            "ui_patterns": ["list_view"],
            "notable_clickables": [...]
          },
          "suggested_actions": [
            {"action": "tap_element", "element_text": "OK"}
          ]
        }
        ```
    """
    # 初始化基本变量，确保在任何执行路径都有定义
    filtered_text_elements = []
    ui_patterns = []
    notable_clickables = []
    suggested_actions = []
    all_text_elements = []
    all_screen_text = []
    
    # Take a screenshot first for analysis and reference
    screenshot_result = await take_screenshot()
    screenshot_path = None
    if "success" in screenshot_result:
        screenshot_path = "./screen_snapshot.png"
    
    # Get screen information
    screen_info_str = await get_screen_info()
    
    try:
        screen_info = json.loads(screen_info_str)
    except json.JSONDecodeError:
        return json.dumps({"status": "error", "message": "Unable to parse screen information JSON"})
    
    # 增强解析：如果JSON解析成功但信息较少，也尝试XML解析
    if screen_info.get("status") == "success" and len(screen_info.get("text_elements", [])) < 10:
        logger.info("JSON parsing succeeded but with limited text elements, trying XML method for enhancement...")
        
        # 尝试使用XML dump获取更多信息
        from ..core import run_command
        import os
        import xml.etree.ElementTree as ET
        
        xml_cmd = "adb shell uiautomator dump /sdcard/window_dump.xml"
        success, output = await run_command(xml_cmd)
        
        if success:
            # 拉取XML文件
            pull_cmd = "adb pull /sdcard/window_dump.xml ./window_dump.xml"
            pull_success, pull_output = await run_command(pull_cmd)
            
            if pull_success and os.path.exists("./window_dump.xml"):
                # 解析XML文件
                try:
                    tree = ET.parse("./window_dump.xml")
                    root = tree.getroot()
                    
                    # 提取文本元素
                    xml_text_elements = []
                    for elem in root.findall(".//*[@text]"):
                        text = elem.attrib.get('text', '').strip()
                        if text:
                            bounds = elem.attrib.get('bounds', '')
                            clickable = elem.attrib.get('clickable', 'false') == 'true'
                            
                            # 解析bounds
                            center_x = None
                            center_y = None
                            if bounds:
                                try:
                                    bounds = bounds.replace('][', ',').replace('[', '').replace(']', '')
                                    coords = bounds.split(',')
                                    if len(coords) == 4:
                                        x1 = int(coords[0])
                                        y1 = int(coords[1])
                                        x2 = int(coords[2])
                                        y2 = int(coords[3])
                                        center_x = (x1 + x2) // 2
                                        center_y = (y1 + y2) // 2
                                except Exception as e:
                                    pass
                            
                            xml_text_elements.append({
                                "text": text,
                                "bounds": bounds,
                                "center_x": center_x,
                                "center_y": center_y,
                                "clickable": clickable
                            })
                    
                    # 如果XML方式找到了更多文本，合并结果
                    if len(xml_text_elements) > len(screen_info.get("text_elements", [])):
                        logger.info(f"XML enhancement successful: found {len(xml_text_elements)} text elements vs. JSON's {len(screen_info.get('text_elements', []))}")
                        
                        # 合并去重
                        existing_texts = {elem.get("text", "") for elem in screen_info.get("text_elements", [])}
                        for xml_elem in xml_text_elements:
                            if xml_elem["text"] not in existing_texts:
                                screen_info.setdefault("text_elements", []).append(xml_elem)
                                existing_texts.add(xml_elem["text"])
                        
                        # 更新计数
                        screen_info["text_elements_count"] = len(screen_info.get("text_elements", []))
                        screen_info["status"] = "success_enhanced"
                    
                    # 清理临时文件
                    try:
                        os.remove("./window_dump.xml")
                    except:
                        pass
                        
                except Exception as e:
                    logger.warning(f"XML enhancement attempt failed: {str(e)}")
    
    if screen_info.get("status") != "success" and screen_info.get("status") != "success_enhanced":
        # Attempt fallback methods for screen analysis if standard method failed
        logger.warning("Standard UI analysis failed, attempting fallback methods")
        
        # Try to get UI dump again with a slight delay
        await asyncio.sleep(1)
        retry_ui_dump = await dump_ui()
        
        try:
            retry_info = json.loads(retry_ui_dump)
            if "elements" in retry_info:
                # Process the retry data
                text_elements = []
                for elem in retry_info["elements"]:
                    if "text" in elem and elem["text"].strip():
                        text_elements.append({
                            "text": elem["text"],
                            "bounds": elem.get("bounds", "")
                        })
                
                # Use basic screen size if available
                size_result = await get_screen_size()
                try:
                    screen_size = json.loads(size_result)
                except:
                    screen_size = {"width": 1080, "height": 1920}  # Default fallback
                
                # Create a minimalist result
                screen_info = {
                    "status": "partial_success",
                    "screen_size": screen_size,
                    "text_elements_count": len(text_elements),
                    "text_elements": text_elements,
                    "clickable_elements_count": 0,
                    "clickable_elements": []
                }
            else:
                # 在解析部分添加XML备用解析方式
                logger.info("JSON parsing failed, trying XML method...")
                
                # 尝试使用直接XML dump
                from ..core import run_command
                import os
                import xml.etree.ElementTree as ET
                
                xml_cmd = "adb shell uiautomator dump /sdcard/window_dump.xml"
                success, output = await run_command(xml_cmd)
                
                if success:
                    # 拉取XML文件到当前目录
                    pull_cmd = "adb pull /sdcard/window_dump.xml ./window_dump.xml"
                    pull_success, pull_output = await run_command(pull_cmd)
                    
                    if pull_success and os.path.exists("./window_dump.xml"):
                        # 解析XML文件
                        try:
                            tree = ET.parse("./window_dump.xml")
                            root = tree.getroot()
                            
                            # 提取文本元素
                            text_elements = []
                            for elem in root.findall(".//*[@text]"):
                                text = elem.attrib.get('text', '').strip()
                                if text:
                                    bounds = elem.attrib.get('bounds', '')
                                    clickable = elem.attrib.get('clickable', 'false') == 'true'
                                    
                                    # 解析bounds "[x1,y1][x2,y2]"
                                    center_x = None
                                    center_y = None
                                    if bounds:
                                        try:
                                            bounds = bounds.replace('][', ',').replace('[', '').replace(']', '')
                                            coords = bounds.split(',')
                                            if len(coords) == 4:
                                                x1 = int(coords[0])
                                                y1 = int(coords[1])
                                                x2 = int(coords[2])
                                                y2 = int(coords[3])
                                                center_x = (x1 + x2) // 2
                                                center_y = (y1 + y2) // 2
                                        except Exception as e:
                                            logger.warning(f"Failed to parse bounds: {bounds}, error: {str(e)}")
                                    
                                    text_elements.append({
                                        "text": text,
                                        "bounds": bounds,
                                        "center_x": center_x,
                                        "center_y": center_y,
                                        "clickable": clickable
                                    })
                            
                            # 提取可点击元素
                            clickable_elements = []
                            for elem in root.findall(".//*[@clickable='true']"):
                                content_desc = elem.attrib.get('content-desc', '')
                                text = elem.attrib.get('text', '')
                                bounds = elem.attrib.get('bounds', '')
                                
                                # 解析bounds
                                center_x = None
                                center_y = None
                                if bounds:
                                    try:
                                        bounds = bounds.replace('][', ',').replace('[', '').replace(']', '')
                                        coords = bounds.split(',')
                                        if len(coords) == 4:
                                            x1 = int(coords[0])
                                            y1 = int(coords[1])
                                            x2 = int(coords[2])
                                            y2 = int(coords[3])
                                            center_x = (x1 + x2) // 2
                                            center_y = (y1 + y2) // 2
                                    except Exception as e:
                                        logger.warning(f"Failed to parse bounds: {bounds}, error: {str(e)}")
                                
                                clickable_elements.append({
                                    "text": text,
                                    "content_desc": content_desc,
                                    "bounds": bounds,
                                    "center_x": center_x,
                                    "center_y": center_y
                                })
                            
                            # 获取屏幕尺寸
                            size_result = await get_screen_size()
                            try:
                                screen_size = json.loads(size_result)
                            except:
                                # 尝试从XML中获取屏幕尺寸
                                try:
                                    width = int(root.attrib.get('width', 1080))
                                    height = int(root.attrib.get('height', 1920))
                                    screen_size = {"width": width, "height": height}
                                except:
                                    screen_size = {"width": 1080, "height": 1920}  # 默认值
                            
                            # 创建结果
                            screen_info = {
                                "status": "success_xml",
                                "screen_size": screen_size,
                                "text_elements_count": len(text_elements),
                                "text_elements": text_elements,
                                "clickable_elements_count": len(clickable_elements),
                                "clickable_elements": clickable_elements,
                                "all_elements": text_elements + clickable_elements  # 添加所有元素列表，便于后续分析
                            }
                            
                            # 清理下载的文件
                            try:
                                os.remove("./window_dump.xml")
                            except:
                                pass
                                
                            # 处理成功，跳过返回截图的逻辑
                            logger.info(f"XML parsing successful: found {len(text_elements)} text elements and {len(clickable_elements)} clickable elements")
                            
                        except Exception as e:
                            logger.error(f"XML parsing failed: {str(e)}")
                            # 如果XML解析也失败但我们有截图，返回最小数据
                            if screenshot_path:
                                return json.dumps({
                                    "status": "partial_success_screenshot_only",
                                    "message": f"UI analysis and XML parsing failed, but screenshot was taken. Error: {str(e)}",
                                    "screenshot_path": screenshot_path
                                }, ensure_ascii=False)
                
                # 如果所有备用方法都失败但有截图，返回截图
                if not 'status' in screen_info and screenshot_path:
                    return json.dumps({
                        "status": "partial_success_screenshot_only",
                        "message": "UI analysis failed, but screenshot was taken. Use visual inspection.",
                        "screenshot_path": screenshot_path
                    }, ensure_ascii=False)
                else:
                    return screen_info_str  # Return original error
        except Exception as e:
            # 如果所有备用方法都失败但有截图，返回截图
            if screenshot_path:
                return json.dumps({
                    "status": "partial_success_screenshot_only",
                    "message": f"UI analysis failed: {str(e)}, but screenshot was taken. Use visual inspection.",
                    "screenshot_path": screenshot_path
                }, ensure_ascii=False)
            else:
                return screen_info_str
    
    # 分析文本按屏幕区域
    texts_by_region = {
        "top": [],
        "middle": [],
        "bottom": []
    }
    
    # 获取所有文本元素用于分析
    all_text_elements = screen_info.get("text_elements", [])
    
    # 增强过滤以避免重复同时保留信息
    unique_texts = {}
    for text_elem in all_text_elements:
        text = text_elem.get("text", "").strip()
        if text:
            # 如果文本尚未存在，或者新元素有坐标而旧元素没有，则更新
            if text not in unique_texts or (
                    "center_y" in text_elem and 
                    text_elem["center_y"] and 
                    not unique_texts[text].get("center_y")):
                unique_texts[text] = text_elem
    
    filtered_text_elements = list(unique_texts.values())
    
    # 处理所有元素列表
    if not filtered_text_elements:
        logger.warning("没有找到任何文本元素，检查屏幕是否为空或XML解析是否失败")
        
        # 尝试直接从all_elements中提取文本
        for elem in screen_info.get("all_elements", []):
            if elem.get("text") and elem.get("text").strip():
                filtered_text_elements.append(elem)
    
    screen_height = screen_info["screen_size"]["height"]
    top_threshold = screen_height * 0.25
    bottom_threshold = screen_height * 0.75
    
    # 根据y位置排序文本元素（如果有坐标）
    for text_elem in filtered_text_elements:
        y_pos = text_elem.get("center_y", 0)
        
        # 如果元素没有坐标但有边界，尝试提取
        if y_pos == 0 and "bounds" in text_elem:
            bounds = text_elem["bounds"]
            if isinstance(bounds, str):
                try:
                    # 处理"[x1,y1][x2,y2]"或"x1,y1,x2,y2"格式
                    if '[' in bounds:
                        bounds = bounds.replace('][', ',').replace('[', '').replace(']', '')
                    coords = bounds.split(',')
                    if len(coords) == 4:
                        x1 = int(coords[0])
                        y1 = int(coords[1])
                        x2 = int(coords[2])
                        y2 = int(coords[3])
                        text_elem["center_x"] = (x1 + x2) // 2
                        text_elem["center_y"] = (y1 + y2) // 2
                        y_pos = text_elem["center_y"]
                except Exception:
                    pass
            elif isinstance(bounds, dict) and all(k in bounds for k in ["left", "top", "right", "bottom"]):
                try:
                    x1 = int(bounds["left"])
                    y1 = int(bounds["top"])
                    x2 = int(bounds["right"])
                    y2 = int(bounds["bottom"])
                    text_elem["center_x"] = (x1 + x2) // 2
                    text_elem["center_y"] = (y1 + y2) // 2
                    y_pos = text_elem["center_y"]
                except Exception:
                    pass
        
        # 根据y位置放入区域
        if y_pos < top_threshold:
            texts_by_region["top"].append(text_elem)
        elif y_pos > bottom_threshold:
            texts_by_region["bottom"].append(text_elem)
        else:
            texts_by_region["middle"].append(text_elem)
    
    # 对于没有已知位置的文本元素，按比例分配
    unknown_position_texts = [t for t in filtered_text_elements if not t.get("center_y", 0)]
    if unknown_position_texts:
        # 如果无法确定位置，均匀分布在区域中
        chunk_size = len(unknown_position_texts) // 3
        texts_by_region["top"].extend(unknown_position_texts[:chunk_size])
        texts_by_region["bottom"].extend(unknown_position_texts[-chunk_size:] if chunk_size > 0 else [])
        texts_by_region["middle"].extend(unknown_position_texts[chunk_size:-chunk_size if chunk_size > 0 else None])
    
    # Identify UI patterns
    ui_patterns = []
    
    # Check if it's a list view
    if len(texts_by_region["middle"]) > 3:
        middle_texts = texts_by_region["middle"]
        y_positions = [t.get("center_y") for t in middle_texts if "center_y" in t]
        
        if y_positions and len(y_positions) > 1:
            y_diffs = [abs(y_positions[i] - y_positions[i-1]) for i in range(1, len(y_positions))]
            if y_diffs and max(y_diffs) - min(y_diffs) < 20:
                ui_patterns.append("list_view")
    
    # Check if there's a bottom navigation bar
    bottom_clickables = []
    clickable_elements = screen_info.get("clickable_elements", [])
    for e in clickable_elements:
        try:
            bounds = e.get("bounds", "")
            if isinstance(bounds, str) and bounds:
                y_value = int(bounds.split(",")[1].replace("]", ""))
                if y_value > bottom_threshold:
                    bottom_clickables.append(e)
            elif isinstance(bounds, dict) and "top" in bounds:
                if int(bounds["top"]) > bottom_threshold:
                    bottom_clickables.append(e)
        except (IndexError, ValueError):
            continue
            
    if len(bottom_clickables) >= 3:
        ui_patterns.append("bottom_navigation")
    
    # Check if it's likely a web page
    webview_detected = False
    for elem in screen_info.get("all_elements", []):
        class_name = elem.get("class_name", "").lower()
        if "webview" in class_name or "browser" in class_name:
            webview_detected = True
            ui_patterns.append("web_content")
            break
    
    # Predict possible actions
    suggested_actions = []
    
    # Collect all text from elements for better action suggestions
    all_screen_text = [elem.get("text", "") for elem in all_text_elements if elem.get("text")]
    
    # Suggest clicking obvious buttons
    for elem in screen_info.get("clickable_elements", []):
        if elem.get("text") and len(elem.get("text")) < 20:
            suggested_actions.append({
                "action": "tap_element", 
                "element_text": elem.get("text"),
                "description": f"Click button: {elem.get('text')}"
            })
    
    # For list views, suggest scrolling
    if "list_view" in ui_patterns:
        suggested_actions.append({
            "action": "swipe", 
            "description": "Scroll down the list"
        })
    
    # For web content, suggest browser-specific actions
    if "web_content" in ui_patterns:
        suggested_actions.append({
            "action": "swipe", 
            "description": "Scroll down the web page"
        })
    
    # Build list of clickable elements to return, ensuring safe coordinate parsing
    notable_clickables = []
    for e in screen_info.get("clickable_elements", [])[:10]:
        try:
            clickable_item = {
                "text": e.get("text", ""), 
                "content_desc": e.get("content_desc", "")
            }
            
            # If the element already has calculated center point coordinates, use them directly
            if "center_x" in e and "center_y" in e:
                clickable_item["center_x"] = e["center_x"]
                clickable_item["center_y"] = e["center_y"]
            # Otherwise try to calculate from bounds
            elif "bounds" in e:
                bounds = e["bounds"]
                if isinstance(bounds, str):
                    coords = bounds.replace("[", "").replace("]", "").split(",")
                    if len(coords) == 4:
                        x1 = int(coords[0])
                        y1 = int(coords[1])
                        x2 = int(coords[2])
                        y2 = int(coords[3])
                        clickable_item["center_x"] = (x1 + x2) // 2
                        clickable_item["center_y"] = (y1 + y2) // 2
                elif isinstance(bounds, dict) and all(k in bounds for k in ["left", "top", "right", "bottom"]):
                    x1 = int(bounds["left"])
                    y1 = int(bounds["top"])
                    x2 = int(bounds["right"])
                    y2 = int(bounds["bottom"])
                    clickable_item["center_x"] = (x1 + x2) // 2
                    clickable_item["center_y"] = (y1 + y2) // 2
            
            # Only add elements with center_x and center_y, or with meaningful text/content_desc
            if ("center_x" in clickable_item and "center_y" in clickable_item) or clickable_item["text"] or clickable_item["content_desc"]:
                notable_clickables.append(clickable_item)
        except Exception:
            continue
    
    # If very few clickable elements are found, try to extract more based on text context
    if len(notable_clickables) < 3 and all_screen_text:
        # Look for typical button/link text patterns
        button_patterns = ["确定", "取消", "下一步", "返回", "登录", "注册", "提交", "查询", 
                          "OK", "Cancel", "Next", "Back", "Login", "Register", "Submit", "Search"]
        
        for text in all_screen_text:
            if any(pattern in text for pattern in button_patterns) and len(text) < 20:
                # This text might be a button even if not marked as clickable
                for elem in all_text_elements:
                    if elem.get("text") == text and "center_x" in elem and "center_y" in elem:
                        clickable_item = {
                            "text": text,
                            "content_desc": "",
                            "center_x": elem["center_x"],
                            "center_y": elem["center_y"],
                            "inferred": True  # Mark this as inferred rather than explicitly clickable
                        }
                        notable_clickables.append(clickable_item)
                        suggested_actions.append({
                            "action": "tap_element", 
                            "element_text": text,
                            "description": f"Click possible button: {text} (inferred)"
                        })
    
    # Build AI-friendly output
    final_result = {
        "status": "success",
        "screen_size": screen_info["screen_size"],
        "screen_analysis": {
            "text_elements": {
                "total": len(filtered_text_elements),
                "by_region": texts_by_region,
                "all_text": [t.get("text", "") for t in filtered_text_elements]
            },
            "ui_patterns": ui_patterns,
            "clickable_count": len(screen_info.get("clickable_elements", [])),
            "notable_clickables": notable_clickables
        },
        "suggested_actions": suggested_actions,
    }
    
    # 添加解析方法标识
    if screen_info.get("status") == "success_xml":
        final_result["parse_method"] = "xml"
    elif screen_info.get("status") == "success_enhanced":
        final_result["parse_method"] = "json+xml"
    else:
        final_result["parse_method"] = "json"
    
    # 添加截图路径（如果有）
    if screenshot_path:
        final_result["screenshot_path"] = screenshot_path
    
    return json.dumps(final_result, ensure_ascii=False)


async def interact_with_screen(action: str, params: Dict[str, Any]) -> str:
    """Execute screen interaction actions
    
    Unified interaction interface supporting multiple interaction methods, including tapping, swiping, key pressing, text input, etc.
    
    Args:
        action: Action type, can be one of:
            - "tap": Tap screen, requires coordinates or element text
            - "swipe": Swipe screen, requires start and end coordinates
            - "key": Press key, requires key code
            - "text": Input text, requires text content
            - "find": Find element, requires search method and value
            - "wait": Wait for element to appear, requires search method, value and timeout parameters
            - "scroll": Scroll to find element, requires search method, value and direction
        params: Action parameter dictionary, different parameters needed for different actions:
            - tap: element_text or x/y coordinates
            - swipe: x1, y1, x2, y2, optional duration
            - key: keycode
            - text: content
            - find: method, value
            - wait: method, value, timeout, interval
            - scroll: method, value, direction, max_swipes
    
    Returns:
        str: JSON string of operation result, containing status and message
    
    Example:
        ```python
        # Tap coordinates
        result = await interact_with_screen("tap", {"x": 100, "y": 200})
        
        # Tap text element
        result = await interact_with_screen("tap", {"element_text": "Login"})
        
        # Swipe screen
        result = await interact_with_screen("swipe", 
                                           {"x1": 500, "y1": 1000, 
                                            "x2": 500, "y2": 200, 
                                            "duration": 300})
        
        # Wait for element to appear
        result = await interact_with_screen("wait", 
                                           {"method": "text", 
                                            "value": "Success", 
                                            "timeout": 10})
        ```
    """
    try:
        if action == "tap":
            if "element_text" in params:
                element_result = await find_element_by_text(
                    params["element_text"], 
                    params.get("partial", True)
                )
                element_data = json.loads(element_result)
                
                if element_data.get("status") == "success" and element_data.get("elements"):
                    element = UIElement(element_data["elements"][0])
                    return await element.tap()
                else:
                    return json.dumps({
                        "status": "error", 
                        "message": f"Could not find element with text '{params['element_text']}'"
                    }, ensure_ascii=False)
            elif "x" in params and "y" in params:
                return await tap_screen(params["x"], params["y"])
            else:
                return json.dumps({
                    "status": "error", 
                    "message": "Missing valid tap parameters"
                }, ensure_ascii=False)
                
        elif action == "swipe":
            if all(k in params for k in ["x1", "y1", "x2", "y2"]):
                duration = params.get("duration", 300)
                return await swipe_screen(
                    params["x1"], params["y1"], 
                    params["x2"], params["y2"], 
                    duration
                )
            else:
                return json.dumps({
                    "status": "error", 
                    "message": "Missing coordinates required for swipe"
                }, ensure_ascii=False)
                
        elif action == "key":
            if "keycode" in params:
                return await press_key(params["keycode"])
            else:
                return json.dumps({
                    "status": "error", 
                    "message": "Missing key parameter"
                }, ensure_ascii=False)
                
        elif action == "text":
            if "content" in params:
                return await input_text(params["content"])
            else:
                return json.dumps({
                    "status": "error", 
                    "message": "Missing text content parameter"
                }, ensure_ascii=False)
                
        elif action == "find":
            method = params.get("method", "text")
            value = params.get("value", "")
            
            if not value and method != "clickable":
                return json.dumps({
                    "status": "error", 
                    "message": "Finding element requires a search value"
                }, ensure_ascii=False)
                
            if method == "text":
                return await find_element_by_text(value, params.get("partial", True))
            elif method == "id":
                return await find_element_by_id(value)
            elif method == "content_desc":
                return await find_element_by_content_desc(value, params.get("partial", True))
            elif method == "class":
                return await find_element_by_class(value)
            elif method == "clickable":
                return await find_clickable_elements()
            else:
                return json.dumps({
                    "status": "error", 
                    "message": f"Unsupported search method: {method}"
                }, ensure_ascii=False)
                
        elif action == "wait":
            method = params.get("method", "text")
            value = params.get("value", "")
            timeout = params.get("timeout", 30)
            interval = params.get("interval", 1.0)
            
            if not value:
                return json.dumps({
                    "status": "error", 
                    "message": "Waiting for element requires a search value"
                }, ensure_ascii=False)
                
            return await wait_for_element(method, value, timeout, interval)
            
        elif action == "scroll":
            method = params.get("method", "text")
            value = params.get("value", "")
            direction = params.get("direction", "down")
            max_swipes = params.get("max_swipes", 5)
            
            if not value:
                return json.dumps({
                    "status": "error", 
                    "message": "Scrolling to find requires a search value"
                }, ensure_ascii=False)
                
            return await scroll_to_element(method, value, direction, max_swipes)
            
        else:
            return json.dumps({
                "status": "error", 
                "message": f"Unsupported interaction action: {action}"
            }, ensure_ascii=False)
            
    except Exception as e:
        logger.error(f"Error executing interaction action {action}: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"Interaction operation failed: {str(e)}"
        }, ensure_ascii=False) 