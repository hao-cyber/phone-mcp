# 📱 Phone MCP Plugin
![Downloads](https://pepy.tech/badge/phone-mcp)

🌟 一个强大的 MCP 手机控制插件，让您轻松通过 ADB 命令控制 Android 手机。

[English Documentation](README.md)

## ⚡ 快速开始

### 📥 安装
使用 Python 3.10+ 和 [uv](https://docs.astral.sh/uv/getting-started/installation/)，在隔离环境中运行：

```bash
uvx --with "mcp<2" --with requests phone-mcp
```

额外依赖用于让现有 PyPI 版本继续使用 MCP v1 API，并提供地图模块导入的 `requests`。更新后的源码包已声明这些依赖，但旧发布版本仍需显式指定。

使用 uv 创建持久安装环境：

```bash
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python phone-mcp "mcp<2" requests
.venv/bin/phone-cli --help
```

也可以在 Linux/macOS 上使用 Python 自带的虚拟环境和 pip：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install phone-mcp "mcp<2" requests
.venv/bin/phone-cli --help
```

Windows 上先运行 `py -3 -m venv .venv`，再使用 `.venv\Scripts\python.exe` 和 `.venv\Scripts\phone-cli.exe` 替代上述 `.venv/bin/` 路径。

Debian/Ubuntu 上的 `externally-managed-environment` 错误表示系统 Python 由操作系统管理。请使用 `uvx` 或虚拟环境，不要使用 `sudo pip` 或 `--break-system-packages` 绕过限制。如果缺少 `venv`，请先通过系统包管理器安装 `python3-venv`。

### 🔧 配置说明
#### AI 助手配置
在您的 AI 助手配置中添加（适用于 Cursor、Trae、Claude 等）：

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

如果您使用 pip 安装，则配置如下：
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

> **重要提示**：请填写安装了 phone-mcp 的虚拟环境中 Python 的绝对路径，而不是系统 Python。Linux/macOS 通常为 `/absolute/path/to/.venv/bin/python`；Windows 为 `C:\path\to\.venv\Scripts\python.exe`（JSON 中反斜杠需写成 `\\`）。无需在 AI 助手启动前激活虚拟环境。

> **注意**：对于 Cursor，请将此配置放在 `~/.cursor/mcp.json` 文件中

使用方法：
- 在 AI 助手对话中直接使用命令，例如：
  ```
   帮我给联系人hao打电话
  ```

⚠️ 使用前请确保：
- ADB 已正确安装并配置
- Android 设备已启用 USB 调试
- 设备已通过 USB 连接到电脑

## 🎯 主要功能

- 📞 **通话功能**：拨打电话、结束通话、接收来电
- 💬 **短信功能**：发送短信、接收短信、获取原始短信
- 👥 **联系人功能**：访问手机联系人、自动化创建联系人界面交互
- 📸 **媒体功能**：截屏、录屏、控制媒体播放
- 📱 **应用功能**：打开应用程序、通过Intent启动特定活动、列出已安装应用、关闭应用
- 🔧 **系统功能**：获取窗口信息、应用快捷方式
- 🗺️ **地图功能**：搜索周边带电话号码的POI信息
- 🖱️ **UI交互**：点击、滑动、输入文本、按键操作
- 🔍 **UI检查**：通过文本、ID、类名或描述查找元素
- 🤖 **UI自动化**：等待元素出现、滚动查找元素
- 🧠 **屏幕分析**：结构化屏幕信息和统一交互接口
- 🌐 **浏览器功能**：在设备默认浏览器中打开URL
- 🔄 **UI监控**：监控UI变化，等待特定元素出现或消失

## 🛠️ 系统要求

- Python 3.10+
- 启用 USB 调试的 Android 设备
- ADB 工具

## 📋 基本命令

### 设备与连接
```bash
# 检查设备连接
phone-cli check

# 获取屏幕尺寸
phone-cli screen-interact find method=clickable
```

### 通讯
```bash
# 拨打电话
phone-cli call 10086

# 结束当前通话
phone-cli hangup

# 发送短信
phone-cli send-sms 10086 "你好"

# 查看短信
phone-cli messages --limit 10

# 获取联系人（带分页）
phone-cli contacts --limit 20

# 通过UI自动化创建新联系人
phone-cli create-contact "张三" "10086"
```

### 媒体与应用
```bash
# 截屏
phone-cli screenshot

# 录屏
phone-cli record --duration 30

# 打开应用（在某些设备上可能不工作）
phone-cli app camera

# 使用open_app命令打开应用（如果app命令不可用）
phone-cli open_app camera

# 关闭应用
phone-cli close-app com.android.camera

# 列出已安装应用（基本信息，速度更快）
phone-cli list-apps

# 分页显示应用列表
phone-cli list-apps --page 1 --page-size 10

# 显示应用详细信息（速度较慢）
phone-cli list-apps --detailed

# 启动特定活动（所有设备上最可靠的方法）
phone-cli launch com.android.settings/.Settings

# 通过包名启动应用（在某些设备上可能不工作）
phone-cli app com.android.contacts

# 使用open_app命令通过包名启动应用（如果app命令不可用）
phone-cli open_app com.android.contacts

# 通过包名和活动名启动应用（最可靠的方法）
phone-cli launch com.android.dialer/com.android.dialer.DialtactsActivity

# 在默认浏览器中打开网页
phone-cli open-url google.com
```

### 屏幕分析与UI交互
```bash
# 分析当前屏幕并提供结构化信息
phone-cli analyze-screen

# 统一交互接口
phone-cli screen-interact <动作> [参数]

# 通过坐标点击
phone-cli screen-interact tap x=500 y=800

# 通过文本内容点击元素
phone-cli screen-interact tap element_text="登录"

# 通过内容描述点击元素
phone-cli screen-interact tap element_content_desc="日历"

# 滑动手势（向下滚动）
phone-cli screen-interact swipe x1=500 y1=1000 x2=500 y2=200 duration=300

# 按键操作
phone-cli screen-interact key keycode=back

# 输入文本
phone-cli screen-interact text content="10086"

# 查找元素
phone-cli screen-interact find method=text value="登录" partial=true

# 等待元素出现
phone-cli screen-interact wait method=text value="成功" timeout=10

# 滚动查找元素
phone-cli screen-interact scroll method=text value="设置" direction=down max_swipes=5

# 监控UI变化
phone-cli monitor-ui --interval 0.5 --duration 30

# 监控直到特定文本出现
phone-cli monitor-ui --watch-for text_appears --text "欢迎"

# 监控直到特定元素ID出现
phone-cli monitor-ui --watch-for id_appears --id "login_button"

# 监控直到特定元素类型出现
phone-cli monitor-ui --watch-for class_appears --class-name "android.widget.Button"

# 监控UI变化并输出原始JSON数据
phone-cli monitor-ui --raw
```

### 位置与地图
```bash
# 搜索周边带电话号码的POI信息
phone-cli get-poi 116.480053,39.987005 --keywords 餐厅 --radius 1000
```

## 📚 高级用法

### 应用和活动启动

插件提供了多种方式启动应用和活动：

1. **通过应用名称**（两种方法）：
   ```bash
   # 方法1：使用app命令（在某些设备上可能不工作）
   phone-cli app camera
   
   # 方法2：使用open_app命令（如果app命令失败则使用此方法）
   phone-cli open_app camera
   ```

2. **通过包名**（两种方法）：
   ```bash
   # 方法1：使用app命令（在某些设备上可能不工作）
   phone-cli app com.android.contacts
   
   # 方法2：使用open_app命令（如果app命令失败则使用此方法）
   phone-cli open_app com.android.contacts
   ```

3. **通过包名和活动名**（最可靠的方法）：
   ```bash
   # 此方法在所有设备上都有效
   phone-cli launch com.android.dialer/com.android.dialer.DialtactsActivity
   ```

> **注意**：如果您在使用`app`或`open_app`命令时遇到问题，请始终使用`launch`命令并指定完整的组件名称（包名/活动名），这是最可靠的操作方式。

### 通过UI自动化创建联系人

插件提供了通过UI交互创建联系人的方式：

```bash
# 通过UI自动化创建新联系人
phone-cli create-contact "张三" "10086"
```

此命令将：
1. 打开联系人应用
2. 导航到联系人创建界面
3. 填写姓名和电话号码字段
4. 自动保存联系人

### 基于屏幕的自动化

统一的屏幕交互接口使智能代理能够轻松：

1. **分析屏幕**：获取UI元素和文本的结构化分析
2. **做出决策**：基于检测到的UI模式和可用操作
3. **执行交互**：通过一致的参数系统

### UI监控和自动化

插件提供强大的UI监控功能，可检测界面变化：

1. **基本UI监控**：
   ```bash
   # 以自定义间隔（秒）监控任何UI变化
   phone-cli monitor-ui --interval 0.5 --duration 30
   ```

2. **等待特定元素出现**：
   ```bash
   # 等待文本出现（对自动化测试有用）
   phone-cli monitor-ui --watch-for text_appears --text "登录成功"
   
   # 等待特定ID出现
   phone-cli monitor-ui --watch-for id_appears --id "confirmation_dialog"
   ```

3. **监控元素消失**：
   ```bash
   # 等待文本消失
   phone-cli monitor-ui --watch-for text_disappears --text "加载中..."
   ```

4. **获取详细的UI变化报告**：
   ```bash
   # 获取包含所有UI变化信息的原始JSON数据
   phone-cli monitor-ui --raw
   ```

> **提示**：UI监控对自动化脚本特别有用，可等待加载屏幕完成，或确认操作已在UI中生效。

## 📚 详细文档

完整文档和配置说明请访问我们的 [GitHub 仓库](https://github.com/hao-cyber/phone-mcp)。

## 🧰 工具文档

### 屏幕接口 API

插件提供了功能强大的屏幕接口，包含与设备交互的全面 API。以下是主要函数及其参数：

#### interact_with_screen
```python
async def interact_with_screen(action: str, params: Dict[str, Any] = None) -> str:
    """执行屏幕交互操作"""
```
- **参数：**
  - `action`: 操作类型（"tap"点击, "swipe"滑动, "key"按键, "text"文本输入, "find"查找, "wait"等待, "scroll"滚动）
  - `params`: 包含特定操作参数的字典
- **返回值：** 包含操作结果的JSON字符串

**示例：**
```python
# 通过坐标点击
result = await interact_with_screen("tap", {"x": 100, "y": 200})

# 通过元素文本点击
result = await interact_with_screen("tap", {"element_text": "登录"})

# 向下滑动
result = await interact_with_screen("swipe", {"x1": 500, "y1": 300, "x2": 500, "y2": 1200, "duration": 300})

# 输入文本
result = await interact_with_screen("text", {"content": "你好世界"})

# 按返回键
result = await interact_with_screen("key", {"keycode": "back"})

# 通过文本查找元素
result = await interact_with_screen("find", {"method": "text", "value": "设置", "partial": True})

# 等待元素出现
result = await interact_with_screen("wait", {"method": "text", "value": "成功", "timeout": 10, "interval": 0.5})

# 滚动查找元素
result = await interact_with_screen("scroll", {"method": "text", "value": "隐私政策", "direction": "down", "max_swipes": 8})
```

#### analyze_screen
```python
async def analyze_screen(include_screenshot: bool = False, max_elements: int = 50) -> str:
    """分析当前屏幕并提供UI元素的结构化信息"""
```
- **参数：**
  - `include_screenshot`: 是否在结果中包含base64编码的截图
  - `max_elements`: 要处理的最大UI元素数量
- **返回值：** 包含详细屏幕分析的JSON字符串

#### create_contact
```python
async def create_contact(name: str, phone: str) -> str:
    """创建具有指定姓名和电话号码的新联系人"""
```
- **参数：**
  - `name`: 联系人的全名
  - `phone`: 联系人的电话号码
- **返回值：** 包含操作结果的JSON字符串
- **位置：** 此函数位于 'contacts.py' 模块中，实现通过UI自动化创建联系人

#### launch_app_activity
```python
async def launch_app_activity(package_name: str, activity_name: Optional[str] = None) -> str:
    """使用包名和可选的活动名称启动应用"""
```
- **参数：**
  - `package_name`: 要启动的应用的包名
  - `activity_name`: 要启动的特定活动（可选）
- **返回值：** 包含操作结果的JSON字符串
- **位置：** 此函数位于 'apps.py' 模块中

#### launch_intent
```python
async def launch_intent(intent_action: str, intent_type: Optional[str] = None, extras: Optional[Dict[str, str]] = None) -> str:
    """使用Android意图系统启动活动"""
```
- **参数：**
  - `intent_action`: 要执行的操作
  - `intent_type`: 意图的MIME类型（可选）
  - `extras`: 要与意图一起传递的额外数据（可选）
- **返回值：** 包含操作结果的JSON字符串
- **位置：** 此函数位于 'apps.py' 模块中

## 📄 许可证

Apache License, Version 2.0