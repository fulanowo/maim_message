#!/usr/bin/env python3
"""
WebSocket API-Server Version Quick Start Example

This example demonstrates how to use the API-Server Version WebSocket components
with the new modular import structure.
"""

import asyncio
import time
from typing import Optional

# 推荐方式: 从server子模块导入API-Server Version组件
from maim_message.server import (
    WebSocketServer,
    ServerMessageBase,
    BaseMessageInfo,
    Seg,
    MessageDim,
    create_server_config
)

# 其他导入方式:
# 从主模块导入 (兼容性)
# from maim_message import WebSocketServer, ServerMessageBase, BaseMessageInfo, Seg, MessageDim

# 从websocket子模块导入 (完整功能)
# from maim_message.websocket import WebSocketServer, WebSocketClient, ServerMessageBase


async def auth_handler(metadata: dict) -> bool:
    """简单的认证处理"""
    api_key = metadata.get('api_key')
    # 这里可以实现真实的认证逻辑
    return api_key in ['test_key', 'demo_key']


async def user_extractor(metadata: dict) -> str:
    """提取用户ID"""
    api_key = metadata.get('api_key', 'unknown')
    return f'user_{api_key}'


async def message_handler(message: ServerMessageBase, metadata: dict) -> None:
    """消息处理回调"""
    user_id = metadata.get('user_id', 'unknown')
    content = message.message_segment.data
    platform = message.message_info.platform

    print(f"收到消息 - 用户: {user_id}, 平台: {platform}, 内容: {content}")

    # 回复消息
    reply = ServerMessageBase(
        message_info=BaseMessageInfo(
            platform="server",
            message_id=f"reply_{int(time.time())}",
            time=time.time()
        ),
        message_segment=Seg(
            type="text",
            data=f"服务器收到: {content}"
        ),
        message_dim=MessageDim(
            api_key="server",
            platform="server"
        )
    )

    # 这里需要服务器实例来发送回复
    print(f"准备回复: {reply.message_segment.data}")


async def ping_handler(data: dict, metadata: dict) -> None:
    """PING消息处理器"""
    user_id = metadata.get('user_id', 'unknown')
    message = data.get('message', '')

    print(f"收到PING: {message} (来自: {user_id})")

    # 这里可以发送PONG响应
    pong_data = {
        "response": f"PONG to {message}",
        "timestamp": time.time()
    }
    print(f"PONG响应: {pong_data}")


async def main():
    """主函数"""
    print("🚀 WebSocket API-Server Version 服务器快速启动示例")
    print("=" * 50)

    # 创建服务器配置
    config = create_server_config(
        host="localhost",
        port=18000,
        path="/ws",
        on_auth=auth_handler,
        on_auth_extract_user=user_extractor,
        on_message=message_handler
    )

    # 注册自定义消息处理器
    config.register_custom_handler("ping", ping_handler)

    # 创建服务器
    server = WebSocketServer(config)

    print("✅ 服务器配置完成")
    print(f"   监听地址: {config.host}:{config.port}{config.path}")
    print(f"   注册的自定义处理器: {list(config.custom_handlers.keys())}")

    # 创建测试消息
    test_message = ServerMessageBase(
        message_info=BaseMessageInfo(
            platform="demo",
            message_id="test_001",
            time=time.time()
        ),
        message_segment=Seg(
            type="text",
            data="Hello from WebSocket!"
        ),
        message_dim=MessageDim(
            api_key="demo_key",
            platform="demo"
        )
    )

    print(f"✅ 测试消息创建: {test_message.message_segment.data}")

    print("\n📖 使用说明:")
    print("1. 运行此脚本会配置WebSocket服务器")
    print("2. 使用WebSocket客户端连接到 ws://localhost:18000/ws")
    print("3. 在Headers中设置:")
    print("   - x-uuid: 客户端唯一ID")
    print("   - x-apikey: test_key 或 demo_key")
    print("   - x-platform: 客户端平台(如: wechat, qq)")
    print("4. 发送消息测试功能")

    print("\n🎯 可用的导入方式:")
    print("# 从主模块导入")
    print("from maim_message import WebSocketServer, ServerMessageBase")
    print()
    print("# 从server子模块导入 (推荐)")
    print("from maim_message.server import WebSocketServer, create_server_config")
    print()
    print("# 从websocket子模块导入 (完整功能)")
    print("from maim_message.websocket import WebSocketServer, WebSocketClient")


if __name__ == "__main__":
    asyncio.run(main())