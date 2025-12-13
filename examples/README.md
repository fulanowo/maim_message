# API-Server Version 使用示例

本目录包含API-Server Version的使用示例，演示如何正确使用外部导入库。

## 🆕 v0.6.0+ 新特性

### 多连接客户端和智能路由
API-Server Version 现在支持：
- **多连接管理**：单个客户端同时连接多个服务端
- **智能路由**：根据目标的 `api_key+platform` 自动选择连接
- **灵活目标选择**：支持多种消息发送模式
- **双工通信**：完整的标准消息和自定义消息支持

详细请参考 `multi_connection_client.py` 示例。

## 文件说明

### 快速开始
- **`quick_start.py`** - 快速入门示例，演示基本的导入方式和用法
- **`external_library_example.py`** - 完整的聊天应用示例，展示高级功能
- **`multi_connection_client.py`** - 多连接客户端示例，演示智能路由和连接管理
- **`new_client_examples.py`** - 新客户端使用示例，演示WebSocketClient单连接和WebSocketMultiClient多连接客户端

### 测试文件
- **`../others/test_external_library_import.py`** - 外部库导入集成测试
- **`../others/test_websocket_api_complete.py`** - 完整功能测试

## 使用前准备

### 1. 安装库

```bash
# 在项目根目录执行
pip install -e .
```

### 2. 验证安装

```python
# 验证导入是否正确
from maim_message.message import APIMessageBase
from maim_message.server import WebSocketServer
from maim_message.client import WebSocketClient
print("✅ 导入成功!")
```

## 导入规则

### ✅ 正确的导入方式

```python
# API-Server Version 组件 - 从子模块导入
from maim_message.message import APIMessageBase, MessageDim, BaseMessageInfo, Seg
from maim_message.server import WebSocketServer, ServerConfig, create_server_config
from maim_message.client import WebSocketClient, WebSocketMultiClient, ClientConfig
from maim_message.client_factory import create_client_config, create_ssl_client_config

# Legacy 组件 - 从根模块导入（向后兼容）
from maim_message import MessageBase, Seg, GroupInfo, UserInfo, MessageClient, MessageServer
```

### ❌ 错误的导入方式

```python
# 这会导致 ImportError
from maim_message import APIMessageBase  # ❌
from maim_message import WebSocketServer  # ❌
from maim_message import WebSocketClient  # ❌
```

## 运行示例

### 快速开始示例

```bash
cd examples
python quick_start.py
```

这个示例会：
- 验证正确的导入方式
- 演示基本的服务器和客户端创建
- 显示代码示例

### 完整聊天示例

```bash
cd examples
python external_library_example.py
```

这个示例会：
- 创建一个完整的聊天服务器
- 启动多个客户端
- 演示消息发送、接收、房间功能
- 展示完整的导入和使用方式

### 集成测试

```bash
cd others
python test_external_library_import.py
```

这个测试会：
- 验证外部库导入的所有功能
- 测试3个客户端同时连接
- 验证消息发送、接收、自定义消息等功能
- 确保优雅关闭

## 核心概念

### 1. 模块分类

```
maim_message/
├── message/          # 消息相关组件 (APIMessageBase等)
├── server/           # WebSocket服务端组件 (WebSocketServer等)
├── client/           # WebSocket客户端组件 (WebSocketClient等)
└── __init__.py       # Legacy组件导出 (向后兼容)
```

### 2. 组件关系

```
Legacy API (向后兼容)
├── MessageBase
├── MessageClient
├── MessageServer
└── Router

API-Server Version (推荐使用)
├── 消息层: maim_message.message
│   ├── APIMessageBase
│   ├── MessageDim
│   └── BaseMessageInfo
├── 服务端: maim_message.server
│   ├── WebSocketServer
│   └── ServerConfig
└── 客户端: maim_message.client
    ├── WebSocketClient      # 单连接客户端
    ├── WebSocketMultiClient # 多连接客户端
    └── ClientConfig
```

## 最佳实践

### 1. 代码组织

```python
# 推荐的导入顺序
import asyncio
import logging

# 1. 标准库
# 2. 第三方库
# 3. maim_message Legacy组件
from maim_message import MessageBase, Router

# 4. API-Server Version组件
from maim_message.message import APIMessageBase, BaseMessageInfo, Seg, MessageDim
from maim_message.server import WebSocketServer, create_server_config
from maim_message.client_factory import create_client_config, create_ssl_client_config
```

### 2. 配置管理

```python
# 使用便捷函数创建配置
server_config = create_server_config(
    host="localhost",
    port=18040,
    path="/ws"
)

client_config = create_client_config(
    url="ws://localhost:18040/ws",
    api_key="your_api_key",
    platform="your_platform"
)
```

### 3. 错误处理

```python
import asyncio

async def safe_server_start():
    try:
        config = create_server_config()
        server = WebSocketServer(config)
        await server.start()

        # 运行服务器
        while True:
            await asyncio.sleep(1)

    except Exception as e:
        logging.error(f"服务器错误: {e}")
    finally:
        await server.stop()
```

## 常见问题

### Q: 为什么不能从maim_message直接导入APIMessageBase？

A: 这是为了避免与Legacy组件的命名冲突，并明确区分两个版本的API。API-Server Version组件必须从专门的子模块导入。

### Q: 如何在项目中选择使用哪个版本？

A:
- 新项目推荐使用API-Server Version（从子模块导入）
- 现有项目可以继续使用Legacy组件（从根模块导入）
- 两个版本可以共存，互不冲突

### Q: 如何处理导入错误？

A: 确保使用正确的导入路径：

```python
# ✅ 正确
from maim_message.message import APIMessageBase

# ❌ 错误
from maim_message import APIMessageBase
```

## 更多资源

- **完整使用指导**: `../doc/api_server_usage_guide.md`
- **开发指南**: `../doc/server_dev_guide.md`
- **API文档**: 查看`src/maim_message/`下的模块文档

## 贡献

如果您发现示例中的问题或有改进建议，欢迎提交Issue或Pull Request。