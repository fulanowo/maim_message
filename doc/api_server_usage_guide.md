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
    WebSocketClient,      # 单连接WebSocket客户端业务层API
    WebSocketMultiClient, # 多连接WebSocket客户端业务层API
    ClientConfig,         # 客户端配置
    create_client_config, # 创建客户端配置的便捷函数
)
from maim_message.client_factory import (
    create_client_config,     # 创建单连接客户端配置的便捷函数
    create_ssl_client_config, # 创建SSL客户端配置的便捷函数
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

# 关键回调函数：API Key认证
async def auth_handler(metadata: dict) -> bool:
    """验证客户端连接的API Key"""
    api_key = metadata.get("api_key", "")
    # 这里可以实现实际的API Key验证逻辑
    valid_keys = ["test_key_123", "demo_key_456", "prod_key_789"]

    if api_key in valid_keys:
        logging.info(f"✅ 认证成功: {api_key}")
        return True
    else:
        logging.warning(f"❌ 认证失败: 无效的API Key - {api_key}")
        return False

# 关键回调函数：用户标识提取
async def extract_user_handler(metadata: dict) -> str:
    """从API Key提取用户标识"""
    api_key = metadata.get("api_key", "")

    # 从API Key解析用户ID（示例逻辑）
    if api_key.startswith("test_"):
        return f"user_{api_key.split('_')[1]}"
    elif api_key.startswith("demo_"):
        return f"demo_user_{api_key.split('_')[2]}"
    elif api_key.startswith("prod_"):
        return f"prod_user_{api_key.split('_')[2]}"
    else:
        return f"unknown_user_{hash(api_key) % 10000}"

# 关键回调函数：消息处理
async def message_handler(message: APIMessageBase, metadata: dict) -> None:
    """处理收到的消息 - 直接执行完整业务逻辑"""
    content = message.message_segment.data
    platform = metadata.get("platform", "unknown")
    api_key = metadata.get("api_key", "unknown")
    user_id = metadata.get("user_id", "unknown")

    logging.info(f"📨 收到消息 [{platform}] {user_id}: {content}")

    # 直接执行业务逻辑，因为回调已经在独立异步任务中执行
    try:
        # 保存消息到数据库
        await save_message_to_database(content, user_id, platform)

        # 检查消息内容并执行相应操作
        if "hello" in content.lower():
            response = f"你好！收到你的消息: {content}"
            await send_welcome_response(user_id, platform, response)

        elif "ping" in content.lower():
            await send_pong_response(user_id, platform)

        elif "help" in content.lower():
            await send_help_message(user_id, platform)

        else:
            # 处理普通消息
            await process_normal_message(content, user_id, platform)

        logging.info(f"✅ 消息处理完成 [{platform}] {user_id}: {content}")

    except DatabaseError as e:
        logging.error(f"❌ 数据库操作失败: {e}")
        await send_error_response(user_id, platform, "消息保存失败")

    except Exception as e:
        logging.error(f"❌ 消息处理失败: {e}")
        # 不重新抛出异常，系统会自动处理错误隔离

async def main():
    # 创建带回调的服务器配置
    config = create_server_config(
        host="localhost",
        port=18040,
        path="/ws",
        # 关键回调函数
        on_auth=auth_handler,
        on_auth_extract_user=extract_user_handler,
        on_message=message_handler
    )

    # 创建服务器实例
    server = WebSocketServer(config)

    # 启动服务器
    await server.start()

    print("🚀 WebSocket服务器已启动在 ws://localhost:18040/ws")
    print("📋 支持的API Key: test_key_123, demo_key_456, prod_key_789")
    print("💬 连接时需要在Header中提供: x-apikey: YOUR_API_KEY")
    print("🏷️  连接时需要在Header中提供: x-platform: your_platform_name")

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

#### 单连接客户端（WebSocketClient）

```python
import asyncio
import logging
from maim_message.client import WebSocketClient
from maim_message.client_factory import create_client_config
from maim_message.message import APIMessageBase, BaseMessageInfo, Seg, MessageDim

# 配置日志
logging.basicConfig(level=logging.INFO)

# 关键回调函数：客户端消息处理
async def client_message_handler(message: APIMessageBase, metadata: dict) -> None:
    """处理从服务器收到的消息 - 直接执行完整业务逻辑"""
    content = message.message_segment.data
    message_id = message.message_info.message_id
    platform = message.message_info.platform
    sender_user = metadata.get("sender_user", "unknown")
    timestamp = message.message_info.time

    logging.info(f"📤 客户端收到消息 [{platform}] {sender_user}: {content}")
    logging.info(f"🆔 消息ID: {message_id}, 时间戳: {timestamp}")

    # 直接处理业务逻辑，因为回调已经在独立异步任务中执行
    try:
        if "ping" in content.lower():
            # 自动回复pong
            response_content = f"pong from client! Reply to {sender_user}"
            logging.info(f"🏓 收到ping，准备回复pong")
            # 这里可以调用client.send_message()发送回复

        elif "broadcast" in content.lower():
            # 处理广播消息
            logging.info(f"📢 收到广播消息: {content}")
            # 可以触发通知或更新UI
            await notify_user_broadcast(content, platform)

        elif "command" in content.lower():
            # 处理服务器命令
            await execute_server_command(content, metadata)

        elif "notification" in content.lower():
            # 处理通知消息
            await handle_server_notification(content, metadata)

        else:
            # 普通消息处理
            logging.info(f"💬 普通消息处理: {content}")
            # 可以显示给用户或存储到本地

    except Exception as e:
        logging.error(f"❌ 服务器消息处理失败: {e}")
        # 可以选择重试或记录错误日志

async def single_client_demo():
    # 使用配置工厂函数创建配置，包含消息处理回调
    config = create_client_config(
        "ws://localhost:18040/ws",
        "test_key_123",  # 使用之前服务器示例中有效的API Key
        platform="test_platform",
        # 关键回调函数
        on_message=client_message_handler
    )

    # 注册自定义消息处理器
    config.register_custom_handler("server_notification", handle_server_notification)

    client = WebSocketClient(config)

    try:
        # 启动客户端
        await client.start()

        # 连接到服务器
        connected = await client.connect()
        if connected:
            print("✅ 连接到服务器成功")

            # 发送消息（无需指定连接名称）
            message = APIMessageBase(
                message_info=BaseMessageInfo(
                    platform="test_platform",
                    message_id="test_001",
                    time=asyncio.get_event_loop().time()
                ),
                message_segment=Seg(type="text", data="Hello from single client!"),
                message_dim=MessageDim(api_key="test_key_123", platform="test_platform")
            )

            success = await client.send_message(message)
            print(f"消息发送{'成功' if success else '失败'}")

            # 发送自定义消息（无需指定连接名称）
            success = await client.send_custom_message("client_heartbeat", {
                "status": "active",
                "timestamp": asyncio.get_event_loop().time()
            })
            print(f"自定义消息发送{'成功' if success else '失败'}")

            # 保持连接一段时间，等待可能的服务器消息
            print("⏳ 等待服务器消息...")
            await asyncio.sleep(10)

            # 断开连接
            await client.disconnect()
        else:
            print("❌ 连接到服务器失败")

    finally:
        # 停止客户端
        await client.stop()

async def handle_server_notification(data: dict, metadata: dict) -> None:
    """处理服务器自定义通知"""
    notification_type = data.get("type", "unknown")
    content = data.get("content", "")

    logging.info(f"🔔 服务器通知 [{notification_type}]: {content}")

    # 根据通知类型执行不同操作
    if notification_type == "maintenance":
        logging.warning("⚠️ 服务器维护通知")
    elif notification_type == "update":
        logging.info("🔄 系统更新通知")

if __name__ == "__main__":
    asyncio.run(single_client_demo())
```

#### 多连接客户端（WebSocketMultiClient）

```python
import asyncio
import logging
from maim_message.client import WebSocketMultiClient
from maim_message.message import APIMessageBase, BaseMessageInfo, Seg, MessageDim

# 配置日志
logging.basicConfig(level=logging.INFO)

# 关键回调函数：多连接客户端消息处理
async def multi_client_message_handler(message: APIMessageBase, metadata: dict) -> None:
    """处理从服务器收到的消息（支持多平台）- 直接执行完整业务逻辑"""
    content = message.message_segment.data
    platform = message.message_info.platform
    message_id = message.message_info.message_id
    connection_name = metadata.get("connection_name", "unknown")
    sender_user = metadata.get("sender_user", "unknown")

    logging.info(f"📤 多客户端收到消息 [{platform}] {connection_name} {sender_user}: {content}")
    logging.info(f"🆔 消息ID: {message_id}, 连接: {connection_name}")

    # 直接处理多平台业务逻辑，因为回调已经在独立异步任务中执行
    try:
        sender_user = metadata.get("sender_user", "unknown")

        # 根据不同平台执行不同的处理逻辑
        if platform == "wechat":
            await handle_wechat_message(content, connection_name, sender_user)
        elif platform == "qq":
            await handle_qq_message(content, connection_name, sender_user)
        elif platform == "telegram":
            await handle_telegram_message(content, connection_name, sender_user)
        else:
            logging.info(f"📨 未知平台消息 [{platform}]: {content}")
            await handle_unknown_platform_message(content, platform, metadata)

    except Exception as e:
        logging.error(f"❌ 多平台消息处理失败: {e}")
        # 可以选择将失败的消息保存到重试队列

async def handle_wechat_message(content: str, connection_name: str, sender_user: str) -> None:
    """处理微信平台消息"""
    logging.info(f"💬 微信消息处理 [{connection_name}] {sender_user}: {content}")

    # 微信特定的业务逻辑
    if "图片" in content or "image" in content.lower():
        logging.info("🖼️  处理微信图片消息")
    elif "语音" in content or "voice" in content.lower():
        logging.info("🎵 处理微信语音消息")
    else:
        logging.info("📝 处理微信文本消息")

async def handle_qq_message(content: str, connection_name: str, sender_user: str) -> None:
    """处理QQ平台消息"""
    logging.info(f"🐧 QQ消息处理 [{connection_name}] {sender_user}: {content}")

    # QQ特定的业务逻辑
    if "[图片]" in content:
        logging.info("🖼️  处理QQ图片消息")
    elif "[语音]" in content:
        logging.info("🎵 处理QQ语音消息")
    else:
        logging.info("📝 处理QQ文本消息")

async def handle_telegram_message(content: str, connection_name: str, sender_user: str) -> None:
    """处理Telegram平台消息"""
    logging.info(f"✈️  Telegram消息处理 [{connection_name}] {sender_user}: {content}")

    # Telegram特定的业务逻辑
    if content.startswith("/"):
        logging.info("⚡ 处理Telegram命令消息")
        if "/start" in content:
            logging.info("🚀 处理/start命令")
    elif "photo" in content.lower():
        logging.info("🖼️  处理Telegram图片消息")
    else:
        logging.info("📝 处理Telegram文本消息")

async def multi_client_demo():
    # 直接创建多连接客户端
    client = WebSocketMultiClient()

    # 注册全局消息处理回调
    client.register_custom_handler("platform_broadcast", handle_platform_broadcast)

    try:
        # 启动客户端
        await client.start()

        # 注册多个连接（使用有效的API Key）
        client.register_connection("wechat", "ws://localhost:18040/ws", "demo_key_456", "wechat")
        client.register_connection("qq", "ws://localhost:18040/ws", "test_key_123", "qq")
        client.register_connection("telegram", "ws://localhost:18040/ws", "prod_key_789", "telegram")

        # 连接所有注册的连接
        connect_results = await client.connect()
        print(f"连接结果: {connect_results}")

        # 等待连接建立
        await asyncio.sleep(2)

        # 查看活跃连接
        active_connections = client.get_active_connections()
        print(f"活跃连接: {list(active_connections.keys())}")

        # 发送消息到指定连接（需要指定连接名称）
        # 发送到微信连接
        wechat_message = APIMessageBase(
            message_info=BaseMessageInfo(
                platform="wechat", message_id="wechat_001", time=asyncio.get_event_loop().time()
            ),
            message_segment=Seg(type="text", data="发送到微信连接的消息"),
            message_dim=MessageDim(api_key="demo_key_456", platform="wechat")
        )
        success = await client.send_message("wechat", wechat_message)
        print(f"微信消息发送{'成功' if success else '失败'}")

        # 发送到QQ连接
        qq_message = APIMessageBase(
            message_info=BaseMessageInfo(
                platform="qq", message_id="qq_001", time=asyncio.get_event_loop().time()
            ),
            message_segment=Seg(type="text", data="发送到QQ连接的消息"),
            message_dim=MessageDim(api_key="test_key_123", platform="qq")
        )
        success = await client.send_message("qq", qq_message)
        print(f"QQ消息发送{'成功' if success else '失败'}")

        # 发送自定义消息到指定连接
        success = await client.send_custom_message("telegram", "system_notification", {
            "title": "Telegram通知",
            "content": "来自多连接客户端的自定义消息",
            "priority": "high"
        })
        print(f"Telegram自定义消息发送{'成功' if success else '失败'}")

        # 发送平台广播自定义消息
        success = await client.send_custom_message("wechat", "platform_broadcast", {
            "message": "多平台客户端广播测试",
            "target_platforms": ["wechat", "qq", "telegram"],
            "timestamp": asyncio.get_event_loop().time()
        })
        print(f"平台广播消息发送{'成功' if success else '失败'}")

        # 保持连接，等待服务器消息
        print("⏳ 等待各平台服务器消息...")
        await asyncio.sleep(10)

        # 断开指定连接
        await client.disconnect("wechat")
        print("微信连接已断开")

    finally:
        # 停止客户端（会断开所有连接）
        await client.stop()

async def handle_platform_broadcast(data: dict, metadata: dict) -> None:
    """处理平台广播消息"""
    message = data.get("message", "")
    target_platforms = data.get("target_platforms", [])
    timestamp = data.get("timestamp", 0)

    logging.info(f"📢 收到平台广播: {message}")
    logging.info(f"🎯 目标平台: {target_platforms}")

    # 根据广播内容执行操作
    if "维护" in message or "maintenance" in message.lower():
        logging.warning("⚠️  平台维护广播，准备执行维护操作")
    elif "更新" in message or "update" in message.lower():
        logging.info("🔄 平台更新广播，检查版本信息")

if __name__ == "__main__":
    asyncio.run(multi_client_demo())
```

#### 客户端选择指南

**使用场景对比：**

| 特性           | WebSocketClient                      | WebSocketMultiClient                       |
| -------------- | ------------------------------------ | ------------------------------------------ |
| **适用场景**   | 单连接场景（最常见）                 | 多连接场景（特殊情况）                     |
| **连接管理**   | 自动管理单一连接                     | 通过名称管理多个连接                       |
| **消息发送**   | `send_message(message)`              | `send_message(name, message)`              |
| **自定义消息** | `send_custom_message(type, payload)` | `send_custom_message(name, type, payload)` |
| **配置复杂度** | 简单                                 | 中等                                       |
| **路由方式**   | 自动使用缓存的连接参数               | 指定连接名称路由                           |

**推荐选择：**
- 大多数情况使用 `WebSocketClient`（通过 `create_client_config` + `WebSocketClient(config)` 创建）
- 只有需要同时连接多个不同服务时才使用 `WebSocketMultiClient`（直接创建）

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
import asyncio
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)

# 关键回调函数：SSL环境下的安全认证
async def ssl_auth_handler(metadata: dict) -> bool:
    """SSL环境下的安全认证回调"""
    api_key = metadata.get("api_key", "")
    client_cert = metadata.get("client_cert", "")

    logging.info(f"🔐 SSL连接认证请求: API Key={api_key}, 证书={bool(client_cert)}")

    # 在SSL环境下，可以结合证书和API Key进行双重验证
    valid_api_keys = ["secure_key_001", "secure_key_002", "secure_key_003"]

    if api_key not in valid_api_keys:
        logging.warning(f"❌ SSL认证失败: 无效API Key - {api_key}")
        return False

    # 可选：验证客户端证书
    if client_cert and "expired" in client_cert.lower():
        logging.warning(f"❌ SSL认证失败: 客户端证书已过期")
        return False

    logging.info(f"✅ SSL认证成功: {api_key}")
    return True

# 关键回调函数：SSL环境用户标识提取
async def ssl_extract_user_handler(metadata: dict) -> str:
    """SSL环境下的用户标识提取"""
    api_key = metadata.get("api_key", "")
    client_ip = metadata.get("client_ip", "")

    # 在SSL环境下可以创建更安全的用户标识
    user_id = f"secure_user_{api_key.split('_')[-1]}"

    logging.info(f"👤 SSL用户标识提取: {api_key} -> {user_id} (IP: {client_ip})")
    return user_id

# 关键回调函数：SSL消息处理
async def ssl_message_handler(message, metadata: dict) -> None:
    """SSL环境下的消息处理"""
    content = message.message_segment.data
    platform = metadata.get("platform", "ssl_platform")
    user_id = metadata.get("user_id", "unknown")
    client_ip = metadata.get("client_ip", "unknown")

    logging.info(f"🔒 收到SSL消息 [{platform}] {user_id} ({client_ip}): {content}")

    # SSL环境下的安全消息处理
    asyncio.create_task(process_secure_message(content, metadata))

async def process_secure_message(content: str, metadata: dict) -> None:
    """处理安全消息"""
    try:
        user_id = metadata.get("user_id", "unknown")
        platform = metadata.get("platform", "ssl_platform")

        # 检查消息安全性
        if "password" in content.lower() or "密码" in content:
            logging.warning(f"🚨 检测到敏感信息: {content[:50]}...")
        elif "admin" in content.lower() or "管理员" in content:
            logging.info(f"⚙️  管理员指令: {content}")
            # 处理管理员指令
            await handle_admin_command(content, metadata)
        else:
            logging.info(f"✅ 安全消息处理完成: {content}")

    except Exception as e:
        logging.error(f"❌ SSL消息处理失败: {e}")

async def handle_admin_command(content: str, metadata: dict) -> None:
    """处理管理员指令"""
    user_id = metadata.get("user_id", "unknown")

    # 验证管理员权限
    if not user_id.startswith("secure_user_"):
        logging.warning(f"⚠️  非管理员用户尝试执行管理员指令: {user_id}")
        return

    # 执行管理员操作
    if "status" in content.lower():
        logging.info("📊 执行状态查询命令")
    elif "restart" in content.lower():
        logging.info("🔄 执行重启命令")
    else:
        logging.info(f"🔧 未知管理员指令: {content}")

# 创建SSL服务器配置
config = create_ssl_server_config(
    host="0.0.0.0",
    port=18044,            # 建议使用443标准HTTPS端口或18044
    ssl_certfile="/path/to/server.crt",    # SSL证书文件路径
    ssl_keyfile="/path/to/server.key",     # SSL私钥文件路径
    ssl_ca_certs="/path/to/ca.crt",        # CA证书文件路径（可选）
    ssl_verify=True,                       # 是否验证客户端证书

    # 关键回调函数
    on_auth=ssl_auth_handler,
    on_auth_extract_user=ssl_extract_user_handler,
    on_message=ssl_message_handler,

    # 日志配置
    log_level="INFO",
    enable_connection_log=True,
    enable_message_log=True
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
# WebSocketMultiClient 不需要预配置，在注册连接时提供参数
# 也可以提供一个默认配置用于回调等
default_config = create_client_config(
    url="ws://localhost:18040/ws",
    api_key="default_api_key",
    platform="default_platform"
)
# 然后通过 WebSocketMultiClient(default_config=default_config) 创建
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

# 2. 通过 extract_user 回调获取用户ID（传递完整的消息元数据）
message_metadata = {
    "api_key": api_key,
    "platform": platform,
    "message_type": "outgoing",
    "timestamp": time.time()
}
target_user = await self.config.on_auth_extract_user(message_metadata)

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

#### 单连接客户端消息发送

```python
# WebSocketClient 消息发送（无需指定连接）
# 1. 发送标准消息（自动使用缓存的连接参数）
success = await client.send_message(message)
print(f"消息发送{'成功' if success else '失败'}")

# 2. 发送自定义消息（自动使用缓存的连接参数）
success = await client.send_custom_message("notification", {
    "title": "通知",
    "content": "自定义消息"
})
print(f"自定义消息发送{'成功' if success else '失败'}")
```

#### 多连接客户端消息发送

```python
# WebSocketMultiClient 消息发送（需要指定连接名称）
# 1. 发送标准消息到指定连接
success = await client.send_message("wechat", message)
print(f"微信消息发送{'成功' if success else '失败'}")

# 2. 发送自定义消息到指定连接
success = await client.send_custom_message("qq", "notification", {
    "title": "通知",
    "content": "发送到QQ连接的自定义消息"
})
print(f"QQ自定义消息发送{'成功' if success else '失败'}")
```

#### 多连接管理

```python
# WebSocketMultiClient 连接管理
# 注册连接
client.register_connection("wechat", "ws://localhost:18040/ws", "wechat_key", "wechat")
client.register_connection("qq", "ws://localhost:18040/ws", "qq_key", "qq")

# 连接所有注册的连接
connect_results = await client.connect()
print(f"连接结果: {connect_results}")

# 查看所有注册的连接
all_connections = client.list_connections()
print("所有注册的连接:", list(all_connections.keys()))

# 查看活跃连接
active_connections = client.get_active_connections()
print("活跃连接:", list(active_connections.keys()))

# 获取指定连接的详细信息
wechat_info = client.get_connection_info("wechat")
print(f"微信连接信息: {wechat_info}")

# 断开指定连接
disconnect_results = await client.disconnect("wechat")
print(f"断开结果: {disconnect_results}")

# 注销连接
client.unregister_connection("qq")
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

### 2.1 异步任务处理最佳实践

#### 消息处理器设计原则
```python
# ✅ 推荐：轻量级异步处理器
async def message_handler(message: APIMessageBase, metadata: Dict[str, Any]) -> None:
    # 快速处理
    content = message.message_segment.data

    # 异步处理耗时操作
    asyncio.create_task(process_heavy_operation(content))

    # 立即返回，不阻塞事件分发器
    logger.info(f"消息已提交处理: {content[:50]}")

# ✅ 推荐：带超时控制的处理器
async def safe_message_handler(message: APIMessageBase, metadata: Dict[str, Any]) -> None:
    try:
        # 设置处理超时
        await asyncio.wait_for(
            process_message_with_database(message),
            timeout=30.0  # 30秒超时
        )
    except asyncio.TimeoutError:
        logger.error(f"消息处理超时: {message.message_info.message_id}")
    except Exception as e:
        logger.error(f"消息处理失败: {e}")

# ❌ 避免：长时间同步操作
async def bad_message_handler(message: APIMessageBase, metadata: Dict[str, Any]) -> None:
    # 这会阻塞任务，影响并发性能
    time.sleep(5)  # 同步睡眠
    heavy_sync_operation()  # 同步重操作
```

#### 性能监控和负载管理
```python
# 任务数监控
async def monitor_server_load(server: WebSocketServer):
    while True:
        stats = server.get_stats()
        active_tasks = stats.get("active_handler_tasks", 0)

        if active_tasks > 1000:
            logger.warning(f"高负载警告: {active_tasks} 个活跃任务")

        if active_tasks > 5000:
            logger.error(f"系统过载: {active_tasks} 个活跃任务，考虑限流")

        await asyncio.sleep(10)  # 每10秒检查一次

# 启动监控
async def run_server_with_monitoring():
    config = create_server_config()
    server = WebSocketServer(config)

    # 启动监控任务
    monitor_task = asyncio.create_task(monitor_server_load(server))

    try:
        await server.start()
        # 运行服务器...
    finally:
        monitor_task.cancel()
        await server.stop()
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

### 1. 异步任务执行模式 (核心优化)

**设计理念**: 所有消息处理回调默认使用 `asyncio.create_task()` 异步执行

#### 性能优势
- **并发处理**: 多个消息可以同时被处理，不再串行等待
- **非阻塞架构**: 事件分发器不会被单个慢处理阻塞
- **吞吐量提升**: 在高并发场景下显著提升消息处理能力
- **异常隔离**: 单个回调异常不会影响其他消息处理

#### 实际效果对比
```python
# 传统阻塞模式 (伪代码)
async def handle_message(msg):
    await slow_database_operation()  # 2秒
    await slow_api_call()            # 1秒
    # 总阻塞时间：3秒，其他消息等待

# 异步任务模式 (实际实现)
async def handle_message(msg):
    await slow_database_operation()  # 2秒
    await slow_api_call()            # 1秒
    # 总阻塞时间：0秒（对事件分发器而言），其他消息并发处理
```

#### 任务管理
- **自动清理**: 任务完成后自动清理，无资源泄漏
- **状态监控**: 通过 `get_stats()["active_handler_tasks"]` 监控活跃任务数
- **安全停止**: 服务停止时所有任务安全取消

### 2. 连接池管理

服务器自动管理连接池，使用三级映射表：
- `Map<UserID, Map<Platform, Set<UUID>>>`

### 3. 异步I/O处理

所有网络I/O操作都是异步的，确保高并发性能。

### 4. 内存优化

- 消息使用引用传递
- 连接元数据按需存储
- 自动清理断开的连接
- 任务生命周期自动管理

### 5. 性能监控

```python
# 实时监控活跃任务数
stats = server.get_stats()
active_tasks = stats.get("active_handler_tasks", 0)
print(f"当前活跃处理任务: {active_tasks}")

# 监控系统负载
if active_tasks > 100:
    logger.warning(f"高负载警告：{active_tasks} 个活跃任务")
```

## 部署建议

### 1. 生产环境配置

```python
import asyncio
import logging
import time
from typing import Dict, Any
from maim_message.server import ServerConfig
from maim_message.message import APIMessageBase

# 配置生产级日志
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 生产级API Key管理
PRODUCTION_API_KEYS = {
    "prod_key_client_001": {"user": "client_001", "tier": "premium"},
    "prod_key_client_002": {"user": "client_002", "tier": "standard"},
    "prod_key_client_003": {"user": "client_003", "tier": "premium"},
}

# 生产级回调函数：安全认证
async def production_auth_handler(metadata: Dict[str, Any]) -> bool:
    """生产环境安全认证"""
    api_key = metadata.get("api_key", "")
    client_ip = metadata.get("client_ip", "")
    user_agent = metadata.get("user_agent", "")

    # 验证API Key
    if api_key not in PRODUCTION_API_KEYS:
        logger.warning(f"生产环境认证失败: 无效API Key - {api_key} (IP: {client_ip})")
        return False

    # 频率限制检查（示例）
    current_time = time.time()
    # 这里可以添加Redis等分布式缓存来检查频率限制

    logger.info(f"生产环境认证成功: {PRODUCTION_API_KEYS[api_key]['user']} (IP: {client_ip})")
    return True

# 生产级回调函数：用户标识提取
async def production_extract_user_handler(metadata: Dict[str, Any]) -> str:
    """生产环境用户标识提取"""
    api_key = metadata.get("api_key", "")

    # 从预配置的API Key映射中获取用户信息
    if api_key in PRODUCTION_API_KEYS:
        user_info = PRODUCTION_API_KEYS[api_key]
        user_id = f"prod_{user_info['tier']}_{user_info['user']}"

        logger.info(f"生产环境用户提取: {api_key} -> {user_id}")
        return user_id

    # 降级处理：如果API Key不在映射中，生成临时用户ID
    logger.warning(f"生产环境用户提取降级: {api_key} -> unknown_user")
    return f"unknown_user_{hash(api_key) % 10000}"

# 生产级回调函数：消息处理
async def production_message_handler(message: APIMessageBase, metadata: Dict[str, Any]) -> None:
    """生产环境消息处理 - 直接执行完整业务逻辑"""
    content = message.message_segment.data
    platform = metadata.get("platform", "unknown")
    user_id = metadata.get("user_id", "unknown")
    api_key = metadata.get("api_key", "")

    # 记录关键信息（避免记录敏感内容）
    safe_content = content[:100] if len(content) > 100 else content
    logger.info(f"生产环境消息处理: {platform} {user_id} -> {safe_content}")

    # 直接执行生产级业务逻辑，因为回调已经在独立异步任务中执行
    try:
        # 生产级错误处理
        if not content or not content.strip():
            logger.warning(f"生产环境收到空消息: {platform} {user_id}")
            return

        # 消息分类处理
        message_type = classify_production_message(content)

        # 根据消息类型分发到不同的处理器
        if message_type == "command":
            await handle_production_command(content, platform, user_id)
        elif message_type == "data":
            await handle_production_data(content, platform, user_id)
        elif message_type == "query":
            await handle_production_query(content, platform, user_id)
        else:
            await handle_production_general(content, platform, user_id)

        # 生产级审计日志
        await log_production_activity(user_id, platform, message_type, safe_content)

    except ValueError as e:
        # 数据格式错误
        logger.error(f"生产环境数据格式错误: {platform} {user_id} - {e}")
        await send_error_response(user_id, platform, "数据格式错误")

    except PermissionError as e:
        # 权限错误
        logger.error(f"生产环境权限错误: {platform} {user_id} - {e}")
        await send_error_response(user_id, platform, "权限不足")

    except Exception as e:
        # 生产级异常处理：记录详细信息但不暴露敏感数据
        logger.error(f"生产环境消息处理异常: {platform} {user_id} - {type(e).__name__}")
        await send_error_response(user_id, platform, "服务器内部错误")

def classify_production_message(content: str) -> str:
    """生产环境消息分类"""
    content_lower = content.lower().strip()

    if content_lower.startswith('/') or content_lower.startswith('!'):
        return "command"
    elif content_lower.startswith('{') or content_lower.startswith('['):
        return "data"
    elif any(keyword in content_lower for keyword in ['?', '查询', 'query', 'get']):
        return "query"
    else:
        return "general"

async def handle_production_command(content: str, platform: str, user_id: str) -> None:
    """处理生产环境命令"""
    logger.info(f"生产环境命令处理: {platform} {user_id} -> {content[:50]}")

    # 验证用户权限
    if not user_id.startswith("prod_premium_"):
        logger.warning(f"非高级用户尝试执行命令: {user_id}")
        return

    # 执行命令逻辑
    await execute_production_command(content, platform, user_id)

async def handle_production_data(content: str, platform: str, user_id: str) -> None:
    """处理生产环境数据消息"""
    logger.info(f"生产环境数据处理: {platform} {user_id}")

    # 数据验证和处理
    try:
        # 这里可以添加JSON解析、数据验证等
        await process_production_data(content, platform, user_id)
    except ValueError as e:
        logger.error(f"生产环境数据格式错误: {e}")

async def handle_production_query(content: str, platform: str, user_id: str) -> None:
    """处理生产环境查询"""
    logger.info(f"生产环境查询处理: {platform} {user_id} -> {content[:50]}")

    # 执行查询逻辑
    await execute_production_query(content, platform, user_id)

async def handle_production_general(content: str, platform: str, user_id: str) -> None:
    """处理生产环境普通消息"""
    logger.debug(f"生产环境普通消息处理: {platform} {user_id}")

    # 普通消息处理
    await process_production_general_message(content, platform, user_id)

# 占位符函数（在实际项目中需要完整实现）
async def execute_production_command(content: str, platform: str, user_id: str) -> None:
    """执行生产环境命令"""
    pass

async def process_production_data(content: str, platform: str, user_id: str) -> None:
    """处理生产环境数据"""
    pass

async def execute_production_query(content: str, platform: str, user_id: str) -> None:
    """执行生产环境查询"""
    pass

async def process_production_general_message(content: str, platform: str, user_id: str) -> None:
    """处理生产环境普通消息"""
    pass

# 生产环境配置
config = ServerConfig(
    host="0.0.0.0",
    port=18040,
    log_level="WARNING",  # 生产环境建议WARNING级别

    # 启用性能监控
    enable_stats=True,

    # 生产级回调函数
    on_auth=production_auth_handler,
    on_auth_extract_user=production_extract_user_handler,
    on_message=production_message_handler,

    # 连接管理配置
    enable_connection_log=True,
    enable_message_log=False,  # 生产环境关闭详细消息日志以保护隐私
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

### v0.6.0+
- 🔄 **重大接口重构**：重新设计客户端和服务端的 `send_message` 接口
- 🌐 **专用客户端设计**：推出 WebSocketClient（单连接）和 WebSocketMultiClient（多连接）两种专用客户端
- 🎯 **单连接客户端**：WebSocketClient 专门用于单连接场景，无需考虑路由，使用缓存的连接参数
- 🌍 **多连接客户端**：WebSocketMultiClient 支持连接名称路由，每个连接通过名称管理
- 🏭 **便捷工厂函数**：提供 create_client 和 create_multi_client 简化客户端创建
- 📚 **路由文档完善**：明确 `message_dim` 语义，添加路由最佳实践指南
- 🔄 **双工通信**：完整的标准消息和自定义消息双向传输支持
- 💡 **向后兼容**：保持原有API的向后兼容性

### v0.6.0
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