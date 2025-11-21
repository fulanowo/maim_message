# API-Server Version 使用指导

## 概述

API-Server Version是maim_message库的WebSocket网络驱动器架构实现，提供了高性能的WebSocket服务端和客户端功能。

### 安装

```bash
pip install -e .
```

## 导入方式

### 重要说明

从maim_message根模块直接导入的只能是Legacy字段（message_base相关），API-Server Version的导入必须使用子模块：

- ❌ **不推荐**：从根模块导入API-Server Version组件
- ✅ **推荐**：从专门的子模块导入

### Legacy组件（向后兼容）

```python
# 这些组件可以从根模块直接导入（向后兼容）
from maim_message import (
    MessageClient, MessageServer, Router, RouteConfig, TargetConfig,
    MessageBase, Seg, GroupInfo, UserInfo, FormatInfo, TemplateInfo,
    BaseMessageInfo, InfoBase, SenderInfo, ReceiverInfo
)
```

### API-Server Version组件（推荐使用）

```python
# ✅ 消息相关组件
from maim_message.message import (
    APIMessageBase,        # 主要消息类
    MessageDim,           # 消息维度信息
    BaseMessageInfo,      # 消息基础信息
    Seg,                  # 消息片段
    GroupInfo,            # 群组信息
    UserInfo,             # 用户信息
    InfoBase,             # 信息基类
    SenderInfo,           # 发送者信息
    ReceiverInfo,         # 接收者信息
    FormatInfo,           # 格式信息
    TemplateInfo,         # 模板信息
)

# ✅ WebSocket服务端组件
from maim_message.server import (
    WebSocketServer,      # WebSocket服务端业务层API
    ServerConfig,         # 服务端配置
    AuthResult,           # 认证结果
    ConfigManager,        # 配置管理器
    create_server_config, # 创建服务端配置的便捷函数
)

# ✅ WebSocket客户端组件
from maim_message.client import (
    WebSocketClient,      # WebSocket客户端业务层API
    ClientConfig,         # 客户端配置
    create_client_config, # 创建客户端配置的便捷函数
)
```

## 快速开始

### 1. 简单的WebSocket服务器

```python
import asyncio
import logging
from maim_message.server import WebSocketServer, create_server_config
from maim_message.message import APIMessageBase

# 配置日志
logging.basicConfig(level=logging.INFO)

async def main():
    # 创建服务器配置
    config = create_server_config(
        host="localhost",
        port=18040,
        path="/ws"
    )

    # 创建服务器实例
    server = WebSocketServer(config)

    # 启动服务器
    await server.start()

    print("🚀 WebSocket服务器已启动在 ws://localhost:18040/ws")

    try:
        # 保持服务器运行
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 正在停止服务器...")
        await server.stop()
        print("✅ 服务器已停止")

if __name__ == "__main__":
    asyncio.run(main())
```

### 2. WebSocket客户端

#### 单连接客户端

```python
import asyncio
import logging
from maim_message.client import WebSocketClient, create_client_config
from maim_message.message import APIMessageBase, BaseMessageInfo, Seg, MessageDim

# 配置日志
logging.basicConfig(level=logging.INFO)

async def single_client_demo():
    # 创建客户端配置
    config = create_client_config(
        url="ws://localhost:18040/ws",
        api_key="your_api_key",
        platform="test_platform"
    )

    # 创建客户端实例
    client = WebSocketClient(config)

    # 启动客户端
    await client.start()

    # 连接到服务器
    connected = await client.connect()
    if connected:
        print("✅ 连接到服务器成功")

        # 发送消息（自动路由）
        message = APIMessageBase(
            message_info=BaseMessageInfo(
                platform="test_platform",
                message_id="test_001",
                time=asyncio.get_event_loop().time()
            ),
            message_segment=Seg(type="text", data="Hello from client!"),
            message_dim=MessageDim(api_key="your_api_key", platform="test_platform")
        )

        success = await client.send_message(message)
        print(f"消息发送{'成功' if success else '失败'}")

        # 保持连接一段时间
        await asyncio.sleep(5)

        # 断开连接
        await client.disconnect()
    else:
        print("❌ 连接到服务器失败")

    # 停止客户端
    await client.stop()

if __name__ == "__main__":
    asyncio.run(single_client_demo())
```

#### 多连接客户端（推荐）

```python
import asyncio
import logging
from maim_message.client import WebSocketClient, create_client_config
from maim_message.message import APIMessageBase, BaseMessageInfo, Seg, MessageDim

# 配置日志
logging.basicConfig(level=logging.INFO)

async def multi_client_demo():
    # 创建主配置
    main_config = create_client_config(
        url="ws://localhost:18040/ws",
        api_key="main_client_key",
        platform="main_platform"
    )

    # 创建客户端实例
    client = WebSocketClient(main_config)

    try:
        # 启动客户端
        await client.start()

        # 连接主服务
        await client.connect()
        print("✅ 主服务连接成功")

        # 添加多个平台连接
        wechat_conn = await client.add_connection(
            "ws://localhost:18040/ws", "wechat_key", "wechat"
        )
        qq_conn = await client.add_connection(
            "ws://localhost:18040/ws", "qq_key", "qq"
        )

        # 连接到添加的服务
        await client.connect_to(wechat_conn)
        await client.connect_to(qq_conn)

        print(f"✅ 微信连接: {wechat_conn}")
        print(f"✅ QQ连接: {qq_conn}")

        # 等待连接建立
        await asyncio.sleep(2)

        # 查看连接状态
        active_connections = client.get_active_connections()
        print(f"活跃连接: {list(active_connections.keys())}")

        # 发送消息到不同平台（自动路由）
        # 发送到微信平台
        wechat_message = APIMessageBase(
            message_info=BaseMessageInfo(
                platform="wechat", message_id="wechat_001", time=asyncio.get_event_loop().time()
            ),
            message_segment=Seg(type="text", data="发送到微信的消息"),
            message_dim=MessageDim(api_key="wechat_key", platform="wechat")
        )
        await client.send_message(wechat_message)

        # 发送到QQ平台
        qq_message = APIMessageBase(
            message_info=BaseMessageInfo(
                platform="qq", message_id="qq_001", time=asyncio.get_event_loop().time()
            ),
            message_segment=Seg(type="text", data="发送到QQ的消息"),
            message_dim=MessageDim(api_key="qq_key", platform="qq")
        )
        await client.send_message(qq_message)

        # 发送自定义消息
        await client.send_custom_message("notification", {"title": "通知", "content": "自定义消息"})

        # 保持连接
        await asyncio.sleep(5)

    finally:
        # 停止客户端
        await client.stop()

if __name__ == "__main__":
    asyncio.run(multi_client_demo())
```

## 详细配置

### 服务器配置

```python
from maim_message.server import ServerConfig, create_server_config

# 方式1：使用便捷函数
config = create_server_config(
    host="0.0.0.0",        # 监听地址
    port=18040,            # 监听端口
    path="/ws"              # WebSocket路径
)

# 方式2：直接使用ServerConfig
config = ServerConfig(
    host="0.0.0.0",
    port=18040,
    path="/ws",

    # 认证和用户标识转换回调
    on_auth=lambda metadata: bool(metadata.get("api_key")),
    on_auth_extract_user=lambda metadata: metadata["api_key"],

    # 消息处理回调
    on_message=lambda message, metadata: print(f"收到消息: {message.message_segment.data}"),

    # 连接管理回调
    on_connect=lambda connection_uuid, metadata: print(f"客户端连接: {connection_uuid}"),
    on_disconnect=lambda connection_uuid, metadata: print(f"客户端断开: {connection_uuid}"),

    # 日志配置
    log_level="INFO",
    enable_connection_log=True,
    enable_message_log=True
)
```

### SSL/TLS安全连接配置

API-Server Version支持SSL/TLS加密连接，确保WebSocket通信的安全性。

#### SSL服务器配置

```python
from maim_message.server import create_ssl_server_config

# 创建SSL服务器
config = create_ssl_server_config(
    host="0.0.0.0",
    port=18044,            # 建议使用443标准HTTPS端口或18044
    ssl_certfile="/path/to/server.crt",    # SSL证书文件路径
    ssl_keyfile="/path/to/server.key",     # SSL私钥文件路径
    ssl_ca_certs="/path/to/ca.crt",        # CA证书文件路径（可选）
    ssl_verify=True,                       # 是否验证客户端证书

    # 其他配置
    on_auth_extract_user=lambda metadata: metadata["api_key"],
    on_message=lambda message, metadata: print(f"收到SSL消息: {message.message_segment.data}"),
)

# 或者使用完整的ServerConfig
config = ServerConfig(
    host="0.0.0.0",
    port=18044,
    path="/ws",

    # SSL配置
    ssl_enabled=True,
    ssl_certfile="/path/to/server.crt",
    ssl_keyfile="/path/to/server.key",
    ssl_ca_certs="/path/to/ca.crt",
    ssl_verify=False,  # 对于自签名证书通常设置为False

    # 认证配置
    on_auth_extract_user=lambda metadata: metadata["api_key"],
)
```

#### SSL客户端配置

```python
from maim_message.client import create_ssl_client_config

# 自动检测wss://协议
config = create_ssl_client_config(
    url="wss://localhost:18044/ws",      # 使用wss://协议
    api_key="your_api_key",
    ssl_ca_certs="/path/to/ca.crt",        # CA证书文件
    ssl_verify=True,                       # 验证服务器证书
    ssl_check_hostname=True                # 检查主机名
)

# 或者指定详细参数
config = create_ssl_client_config(
    host="localhost",
    port=18044,
    api_key="your_api_key",
    ssl_ca_certs="/path/to/ca.crt",
    ssl_certfile="/path/to/client.crt",    # 客户端证书（双向认证）
    ssl_keyfile="/path/to/client.key",      # 客户端私钥（双向认证）
    ssl_verify=True,
    ssl_check_hostname=False               # 自签名证书通常禁用
)

# 使用标准ClientConfig
config = ClientConfig(
    url="wss://localhost:18044/ws",
    api_key="your_api_key",
    ssl_enabled=True,
    ssl_verify=True,
    ssl_ca_certs="/path/to/ca.crt",
    ssl_check_hostname=True
)
```

#### SSL证书生成

对于开发和测试，可以使用OpenSSL生成自签名证书：

```bash
# 生成私钥
openssl genrsa -out server.key 2048

# 生成自签名证书
openssl req -new -x509 -key server.key -out server.crt -days 365 \
    -subj "/C=CN/ST=Beijing/L=Beijing/O=Test/CN=localhost"

# 生成CA证书（用于客户端验证）
cp server.crt ca.crt
```

#### SSL配置最佳实践

1. **生产环境**：
   - 使用权威CA签发的证书
   - 启用客户端证书验证
   - 使用标准HTTPS端口（443）
   - 配置证书自动更新

2. **开发环境**：
   - 可以使用自签名证书
   - 禁用主机名检查
   - 使用测试端口（18044）

3. **安全建议**：
   - 定期更新证书
   - 使用强加密算法
   - 禁用过时的SSL/TLS版本
   - 监控证书过期时间

### 客户端配置

```python
from maim_message.client import ClientConfig, create_client_config

# 方式1：使用便捷函数（单连接模式）
config = create_client_config(
    url="ws://localhost:18040/ws",
    api_key="your_api_key",
    platform="your_platform"
)

# 方式2：直接使用ClientConfig（单连接模式）
config = ClientConfig(
    url="ws://localhost:18040/ws",
    api_key="your_api_key",
    platform="your_platform",

    # 重连配置
    auto_reconnect=True,
    max_reconnect_attempts=5,
    reconnect_delay=1.0,
    max_reconnect_delay=30.0,

    # 心跳配置
    ping_interval=20,
    ping_timeout=10,
    close_timeout=10,

    # 回调函数
    on_connect=lambda connection_uuid, config: print(f"已连接: {connection_uuid}"),
    on_disconnect=lambda connection_uuid, error: print(f"断开连接: {connection_uuid}"),
    on_message=lambda message, metadata: print(f"收到消息: {message.message_segment.data}"),

    # 日志配置
    log_level="INFO",
    enable_connection_log=True,
    enable_message_log=True
)

# 方式3：多连接客户端配置
# 使用任意一个连接的配置创建客户端，然后通过 add_connection 添加更多连接
main_config = create_client_config(
    url="ws://localhost:18040/ws",
    api_key="main_api_key",
    platform="main_platform"
)
```

## 消息格式

### APIMessageBase 结构

```python
from maim_message.message import (
    APIMessageBase, BaseMessageInfo, Seg, MessageDim,
    SenderInfo, GroupInfo, UserInfo, FormatInfo
)
import time

# 创建完整的消息
message = APIMessageBase(
    message_info=BaseMessageInfo(
        platform="wechat",                    # 平台标识
        message_id="msg_123456789",           # 消息ID
        time=time.time(),                     # 时间戳
        sender_info=SenderInfo(               # 发送者信息
            user_info=UserInfo(
                platform="wechat",
                user_id="user_001",
                user_nickname="用户昵称",
                user_cardname="用户名片"
            ),
            group_info=GroupInfo(             # 群组信息（可选）
                platform="wechat",
                group_id="group_001",
                group_name="群组名称"
            )
        ),
        format_info=FormatInfo(               # 格式信息（可选）
            content_format=["text"],
            accept_format=["text", "emoji"]
        )
    ),
    message_segment=Seg(type="text", data="消息内容"),
    message_dim=MessageDim(
        api_key="your_api_key",      # ⚠️ 重要：这是目标接收者的API密钥，用于路由
        platform="wechat"            # ⚠️ 重要：这是目标接收者的平台标识，用于路由
    )
)
```

### 消息路由机制

#### 🔍 路由原理

`maim_message` 使用 `message_dim` 字段进行智能路由：

- **`message_dim.api_key`**: 目标接收者的API密钥
- **`message_dim.platform`**: 目标接收者的平台标识

#### 🏗️ 服务端路由流程

```python
# 1. 从消息中提取路由信息
api_key = message.get_api_key()      # message_dim.api_key
platform = message.get_platform()    # message_dim.platform

# 2. 通过 extract_user 回调获取用户ID
target_user = self.extract_user(api_key)

# 3. 查找用户连接：user_connections[target_user][platform]
# 4. 发送到所有匹配的连接
```

#### 🧠 客户端路由流程

```python
# 智能连接匹配（按优先级）：
# 1. 完全匹配：connection.api_key == target_api_key AND connection.platform == target_platform
# 2. API Key匹配：connection.api_key == target_api_key
# 3. 平台匹配：connection.platform == target_platform
```

#### ⚠️ 重要说明

1. **`message_dim` 表示接收者**：不是发送者，而是消息的目标接收者
2. **路由信息必需**：`api_key` 和 `platform` 都不能为空
3. **精确匹配**：服务端使用精确的 `user+platform` 匹配
4. **智能容错**：客户端支持多级匹配以提高送达率

#### 🎯 路由最佳实践

```python
# ✅ 正确：指定目标接收者的信息
message = APIMessageBase(
    message_info=BaseMessageInfo(
        platform="wechat",
        message_id="msg_001",
        time=time.time()
    ),
    message_segment=Seg(type="text", data="Hello"),
    message_dim=MessageDim(
        api_key="target_user_api_key",    # 接收者的API密钥
        platform="wechat"                  # 接收者的平台
    )
)

# ❌ 错误：使用发送者的信息作为路由
message = APIMessageBase(
    # ...其他字段...
    message_dim=MessageDim(
        api_key="sender_api_key",  # 这会导致路由到发送者自己
        platform="wechat"
    )
)
```

## 路由最佳实践

### 🎯 核心原则

1. **`message_dim` 表示接收者**：始终设置为目标接收者的信息
2. **路由信息必需**：`api_key` 和 `platform` 都必须正确设置
3. **避免混淆**：不要将发送者信息用于路由

### 📋 路由检查清单

在发送消息前，请确认：

```python
def validate_message_routing(message: APIMessageBase) -> bool:
    """验证消息路由信息"""

    # 检查路由字段是否存在
    if not hasattr(message, 'message_dim'):
        return False

    if not message.message_dim.api_key:
        logger.error("缺少目标接收者的API密钥")
        return False

    if not message.message_dim.platform:
        logger.error("缺少目标接收者的平台标识")
        return False

    return True

# 使用示例
message = APIMessageBase(
    # ... 其他字段
    message_dim=MessageDim(
        api_key="target_user_key",    # ✅ 接收者的API密钥
        platform="wechat"             # ✅ 接收者的平台
    )
)

if validate_message_routing(message):
    await server.send_message(message)
```

### 🔄 消息转发场景

当需要转发消息时，需要重新设置 `message_dim`：

```python
async def forward_message(original_message: APIMessageBase, new_target_api_key: str, new_target_platform: str):
    """转发消息到新的目标"""

    # 创建转发消息
    forwarded_message = APIMessageBase(
        message_info=BaseMessageInfo(
            platform=new_target_platform,
            message_id=f"forward_{int(time.time())}",
            time=time.time(),
            sender_info=original_message.message_info.sender_info  # 保留原始发送者信息
        ),
        message_segment=original_message.message_segment,        # 保留原始消息内容
        message_dim=MessageDim(
            api_key=new_target_api_key,    # ⚠️ 新的目标接收者
            platform=new_target_platform  # ⚠️ 新的目标平台
        )
    )

    await server.send_message(forwarded_message)
```

### ⚠️ 常见错误

#### 错误1：使用发送者信息路由

```python
# ❌ 错误：这会将消息发送给发送者自己
message = APIMessageBase(
    message_info=BaseMessageInfo(
        platform="wechat",
        message_id="msg_001",
        time=time.time(),
        sender_info=SenderInfo(user_info=UserInfo(user_id="sender_001"))
    ),
    message_segment=Seg(type="text", data="Hello"),
    message_dim=MessageDim(
        api_key="sender_api_key",  # ❌ 这是发送者的API密钥
        platform="wechat"          # ❌ 这会导致路由错误
    )
)
```

#### 正确做法

```python
# ✅ 正确：指定目标接收者
message = APIMessageBase(
    message_info=BaseMessageInfo(
        platform="wechat",
        message_id="msg_001",
        time=time.time(),
        sender_info=SenderInfo(user_info=UserInfo(user_id="sender_001"))
    ),
    message_segment=Seg(type="text", data="Hello"),
    message_dim=MessageDim(
        api_key="receiver_api_key",  # ✅ 接收者的API密钥
        platform="wechat"            # ✅ 接收者的平台
    )
)
```

### 🧪 调试路由问题

当消息路由失败时，检查以下方面：

1. **验证路由信息**：
   ```python
   print(f"目标API密钥: {message.get_api_key()}")
   print(f"目标平台: {message.get_platform()}")
   ```

2. **检查服务端连接状态**：
   ```python
   connections = server.get_connections()
   print(f"当前连接: {connections}")
   ```

3. **验证用户提取回调**：
   ```python
   try:
       user_id = server.extract_user(api_key)
       print(f"提取的用户ID: {user_id}")
   except Exception as e:
       print(f"用户提取失败: {e}")
   ```

## 高级功能

### 1. 自定义消息处理器

```python
async def custom_ping_handler(message_data, metadata):
    """自定义PING消息处理器"""
    print(f"收到PING: {message_data}")

    # 处理消息逻辑
    return True

# 注册自定义处理器
config.register_custom_handler("ping", custom_ping_handler)
```

### 2. 广播消息

```python
# 创建广播消息
broadcast_message = APIMessageBase(
    message_info=BaseMessageInfo(
        platform="server",
        message_id="broadcast_001",
        time=time.time()
    ),
    message_segment=Seg(type="text", data="系统广播消息"),
    message_dim=MessageDim(api_key="server", platform="server")
)

# 广播到所有客户端
results = await server.broadcast_message(broadcast_message)
print(f"广播结果: {sum(results.values())}/{len(results)} 成功")

# 广播到指定平台
results = await server.broadcast_message(broadcast_message, platform="wechat")
```

### 3. 消息发送

API-Server Version提供了两种消息发送方式：标准消息发送和自定义目标发送。

#### 标准消息发送

```python
# 创建标准消息
message = APIMessageBase(
    message_info=BaseMessageInfo(
        platform="wechat",
        message_id="msg_123456789",
        time=time.time()
    ),
    message_segment=Seg(type="text", data="Hello from server!"),
    message_dim=MessageDim(
        api_key="target_user_api_key",  # 目标用户的API Key
        platform="wechat"               # 目标平台
    )
)

# 发送消息（自动从消息中获取路由信息）
results = await server.send_message(message)
print(f"发送结果: {results}")

# 发送到指定平台（覆盖消息中的平台设置）
results = await server.send_message(message, target_platform="qq")
print(f"发送到QQ平台的结果: {results}")
```

#### 自定义消息发送

```python
# 发送自定义消息（通过现有的send_custom_message接口）
results = await server.send_custom_message(
    "notification",  # 消息类型
    {"title": "系统通知", "content": "Hello via custom message!"},  # 消息载荷
    target_user="user_001",  # 可选，指定目标用户
    target_platform="wechat"  # 可选，指定目标平台
)
print(f"自定义消息发送结果: {results}")
```

#### 客户端消息发送

```python
# 1. 发送标准消息（自动路由）
success = await client.send_message(message)
print(f"消息发送{'成功' if success else '失败'}")

# 2. 发送自定义消息
success = await client.send_custom_message("notification", {
    "title": "通知",
    "content": "自定义消息"
})
print(f"自定义消息发送{'成功' if success else '失败'}")
```

#### 多连接管理

```python
# 添加多个连接
connection1 = await client.add_connection(
    "ws://localhost:18040/ws", "api_key_1", "wechat"
)
connection2 = await client.add_connection(
    "ws://localhost:18040/ws", "api_key_2", "qq"
)

# 连接到所有添加的连接
await client.connect_to(connection1)
await client.connect_to(connection2)

# 查看所有连接
all_connections = client.get_connections()
print("所有连接:", all_connections)

# 查看活跃连接
active_connections = client.get_active_connections()
print("活跃连接:", active_connections)

# 断开指定连接
await client.disconnect(connection1)

# 移除连接
await client.remove_connection(connection2)
```

### 4. 用户管理

```python
# 获取连接的用户
user_count = server.get_user_count()
print(f"当前连接用户数: {user_count}")

# 获取指定用户的所有连接
user_connections = server.get_user_connections("user_001")
print(f"用户user_001的连接: {user_connections}")
```

## 错误处理和最佳实践

### 1. 异常处理

```python
import asyncio
from maim_message.server import WebSocketServer, ServerConfig

async def safe_server_start():
    config = ServerConfig(host="localhost", port=18040, path="/ws")
    server = WebSocketServer(config)

    try:
        await server.start()
        print("服务器启动成功")

        # 运行服务器
        while True:
            await asyncio.sleep(1)

    except Exception as e:
        print(f"服务器运行错误: {e}")

    finally:
        # 确保优雅关闭
        await server.stop()
        print("服务器已关闭")
```

### 2. 资源管理

```python
import asyncio
from contextlib import asynccontextmanager

@asynccontextmanager
async def websocket_server_context():
    """WebSocket服务器上下文管理器"""
    config = create_server_config(host="localhost", port=18040)
    server = WebSocketServer(config)

    try:
        await server.start()
        yield server
    finally:
        await server.stop()

# 使用示例
async def main():
    async with websocket_server_context() as server:
        # 在这里使用server
        print("服务器运行中...")
        await asyncio.sleep(10)
```

### 3. 连接监控

```python
async def monitor_connections(server):
    """监控连接状态"""
    while True:
        stats = server.get_stats()
        print(f"连接统计: 用户数={stats['current_users']}, 连接数={stats['current_connections']}")
        await asyncio.sleep(10)

# 启动监控任务
async def main():
    config = create_server_config()
    server = WebSocketServer(config)

    await server.start()

    # 启动监控任务
    monitor_task = asyncio.create_task(monitor_connections(server))

    try:
        while True:
            await asyncio.sleep(1)
    finally:
        monitor_task.cancel()
        await server.stop()
```

## 性能优化

### 1. 连接池管理

服务器自动管理连接池，使用三级映射表：
- `Map<UserID, Map<Platform, Set<UUID>>>`

### 2. 异步处理

所有I/O操作都是异步的，确保高并发性能。

### 3. 内存优化

- 消息使用引用传递
- 连接元数据按需存储
- 自动清理断开的连接

## 部署建议

### 1. 生产环境配置

```python
config = ServerConfig(
    host="0.0.0.0",
    port=18040,
    log_level="WARNING",  # 生产环境建议WARNING级别

    # 启用性能监控
    enable_stats=True,

    # 自定义认证逻辑
    on_auth=your_auth_function,
    on_auth_extract_user=your_user_extractor,

    # 自定义消息处理
    on_message=your_message_handler
)
```

### 2. Docker部署

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY . .

RUN pip install -e .

EXPOSE 18040

CMD ["python", "your_server.py"]
```

## 故障排除

### 常见问题

1. **导入错误**
   ```
   ImportError: cannot import name 'APIMessageBase' from 'maim_message'
   ```
   **解决方案**: 使用正确的子模块导入：
   ```python
   from maim_message.message import APIMessageBase  # ✅
   # 而不是
   # from maim_message import APIMessageBase        # ❌
   ```

2. **连接失败**
   - 检查服务器是否启动
   - 确认URL和端口正确
   - 检查防火墙设置

3. **认证失败**
   - 确认api_key正确
   - 检查认证回调函数逻辑

### 调试技巧

1. **启用调试日志**
   ```python
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **连接状态监控**
   ```python
   stats = server.get_stats()
   print(stats)
   ```

3. **消息追踪**
   ```python
   config.enable_message_log = True
   ```

## 版本兼容性

- **Python**: 3.9+
- **依赖**: FastAPI, uvicorn, websockets, aiohttp, pydantic

## 更新日志

### v0.5.8+
- 🔄 **重大接口重构**：重新设计客户端和服务端的 `send_message` 接口
- 🌐 **多连接客户端**：支持单个客户端同时连接多个服务端
- 🧠 **智能路由**：客户端根据 `api_key+platform` 自动选择最佳连接
- 🎯 **简化接口设计**：每个类只保留两种核心消息发送方法
- 📚 **路由文档完善**：明确 `message_dim` 语义，添加路由最佳实践指南
- 🔄 **双工通信**：完整的标准消息和自定义消息双向传输支持
- 🔗 **连接管理API**：提供完整的多连接生命周期管理
- 💡 **向后兼容**：保持原有API的向后兼容性

### v0.5.8
- 实现导入分类：Legacy vs API-Server Version
- 重构模块结构：message, server, client
- 彻底删除ServerMessageBase兼容别名
- 完善外部库导入支持

---

更多详细信息请参考项目文档和示例代码。

## 外部客户端集成

### 非maim_message客户端支持

API-Server Version完全支持非maim_message库的客户端程序通过标准WebSocket协议进行通信。详细的使用指导请参考：

- **📖 [外部客户端通信指南](./external_client_communication_guide.md)** - 详细的协议规范和实现示例
- **💻 [外部客户端示例代码](../examples/external_client_examples.py)** - Python原生WebSocket客户端示例

### 支持的语言和框架

任何支持WebSocket的编程语言都可以与maim_message API-Server通信：

- **Python**: websockets库、aiohttp
- **JavaScript**: 原生WebSocket API、Socket.io
- **Java**: Java-WebSocket、Spring WebSocket
- **Go**: gorilla/websocket
- **C#**: ClientWebSocket
- **Node.js**: ws库
- **其他**: 任何RFC 6455兼容的WebSocket实现

### 快速集成要点

1. **连接格式**:
   - 查询参数方式：`ws://host:port/ws?api_key=your_key&platform=your_platform`
   - HTTP头方式：`ws://host:port/ws` + `x-apikey: your_key`
2. **消息格式**: JSON字符串，包含`message_info`、`message_segment`、`message_dim`三个部分
3. **认证方式**: API Key通过查询参数（推荐）或HTTP头 `x-apikey` 传递
4. **SSL支持**: 使用`wss://`协议进行加密通信

更多技术细节请参考：
- [WebSocket RFC 6455](https://tools.ietf.org/html/rfc6455)
- [外部客户端通信指南](./external_client_communication_guide.md)
- [API-Server使用示例](../examples/)