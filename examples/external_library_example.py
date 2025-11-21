"""
API-Server Version 外部库使用示例
演示如何使用pip install -e .安装的maim_message库构建WebSocket应用

前提条件：
1. pip install -e .
2. 本示例演示正确的导入方式：从子模块导入API-Server Version组件
"""

import asyncio
import logging
import time
from typing import Dict, Any

# ✅ 正确的导入方式：API-Server Version从子模块导入
from maim_message.server import WebSocketServer, ServerConfig, create_server_config
from maim_message.client import WebSocketClient, ClientConfig, create_client_config
from maim_message.message import (
    APIMessageBase, BaseMessageInfo, Seg, MessageDim,
    GroupInfo, UserInfo, SenderInfo, FormatInfo
)

# ❌ 错误的导入方式（会失败）
# from maim_message import APIMessageBase, WebSocketServer  # 这会导致ImportError

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ChatServer:
    """聊天服务器示例"""

    def __init__(self):
        # 创建服务器配置
        self.config = create_server_config(
            host="localhost",
            port=18050,
            path="/ws"
        )

        # 设置认证和用户处理
        self.config.on_auth = self._authenticate
        self.config.on_auth_extract_user = self._extract_user
        self.config.on_message = self._handle_message
        self.config.on_connect = self._handle_connect
        self.config.on_disconnect = self._handle_disconnect

        # 创建服务器
        self.server = WebSocketServer(self.config)

        # 注册自定义处理器
        self.config.register_custom_handler("join_room", self._handle_join_room)
        self.config.register_custom_handler("leave_room", self._handle_leave_room)

    async def _authenticate(self, metadata: Dict[str, Any]) -> bool:
        """认证连接"""
        api_key = metadata.get("api_key")
        if not api_key:
            logger.warning(f"认证失败：缺少api_key")
            return False

        # 这里可以实现你的认证逻辑
        # 例如：查询数据库验证api_key有效性
        logger.info(f"认证通过：api_key={api_key}")
        return True

    async def _extract_user(self, metadata: Dict[str, Any]) -> str:
        """提取用户标识"""
        api_key = metadata.get("api_key")
        platform = metadata.get("platform", "unknown")

        # 将api_key转换为用户ID
        user_id = f"user_{api_key}_{platform}"
        logger.info(f"用户标识转换：api_key={api_key} -> user_id={user_id}")
        return user_id

    async def _handle_connect(self, connection_uuid: str, metadata: Dict[str, Any]):
        """处理连接"""
        logger.info(f"🔗 新客户端连接: {connection_uuid} ({metadata.get('platform')})")

    async def _handle_disconnect(self, connection_uuid: str, metadata: Dict[str, Any]):
        """处理断开连接"""
        logger.info(f"🔌 客户端断开连接: {connection_uuid}")

    async def _handle_message(self, message: APIMessageBase, metadata: Dict[str, Any]):
        """处理标准消息"""
        logger.info(f"📨 收到消息: {message.message_segment.data}")
        logger.info(f"   发送者: {message.get_api_key()}")
        logger.info(f"   平台: {message.get_platform()}")
        logger.info(f"   时间: {message.message_info.time}")

        # 简单的回声处理
        if message.message_segment.data.startswith("echo "):
            echo_content = message.message_segment.data[5:]
            await self._send_echo_message(message, echo_content)
        elif message.message_segment.data == "time":
            await self._send_time_message(message)
        elif message.message_segment.data == "stats":
            await self._send_stats_message(message)

    async def _handle_join_room(self, message_data: Dict[str, Any], metadata: Dict[str, Any]):
        """处理加入房间"""
        room_name = message_data.get("room_name")
        user_id = message_data.get("user_id")
        logger.info(f"🏠 用户 {user_id} 加入房间: {room_name}")

        # 广播房间消息
        response = {
            "type": "room_notification",
            "action": "user_joined",
            "room_name": room_name,
            "user_id": user_id,
            "message": f"用户 {user_id} 加入了房间 {room_name}"
        }

        # 这里可以实现房间逻辑
        await self.server.send_custom_message(
            "room_notification", response,
            target_user=user_id  # 发送给特定用户
        )

    async def _handle_leave_room(self, message_data: Dict[str, Any], metadata: Dict[str, Any]):
        """处理离开房间"""
        room_name = message_data.get("room_name")
        user_id = message_data.get("user_id")
        logger.info(f"🚪 用户 {user_id} 离开房间: {room_name}")

    async def _send_echo_message(self, original_message: APIMessageBase, echo_content: str):
        """发送回声消息"""
        echo_message = APIMessageBase(
            message_info=BaseMessageInfo(
                platform="server",
                message_id=f"echo_{int(time.time() * 1000)}",
                time=time.time()
            ),
            message_segment=Seg(type="text", data=f"回声: {echo_content}"),
            message_dim=MessageDim(api_key="server", platform="server")
        )

        # 发送给原消息发送者
        # 使用新的接口，从原消息中获取目标API Key
        echo_message.message_dim.api_key = original_message.get_api_key()  # 设置目标API Key
        echo_message.message_dim.platform = original_message.get_platform()  # 设置目标平台
        results = await self.server.send_message(echo_message)
        logger.info(f"回声消息发送结果: {results}")

    async def _send_time_message(self, original_message: APIMessageBase):
        """发送时间消息"""
        time_message = APIMessageBase(
            message_info=BaseMessageInfo(
                platform="server",
                message_id=f"time_{int(time.time() * 1000)}",
                time=time.time()
            ),
            message_segment=Seg(type="text", data=f"当前时间: {time.ctime()}"),
            message_dim=MessageDim(api_key="server", platform="server")
        )

        # 使用新的接口，从原消息中获取目标API Key
        time_message.message_dim.api_key = original_message.get_api_key()  # 设置目标API Key
        time_message.message_dim.platform = original_message.get_platform()  # 设置目标平台
        results = await self.server.send_message(time_message)
        logger.info(f"时间消息发送结果: {results}")

    async def _send_stats_message(self, original_message: APIMessageBase):
        """发送统计消息"""
        stats = self.server.get_stats()
        stats_message = APIMessageBase(
            message_info=BaseMessageInfo(
                platform="server",
                message_id=f"stats_{int(time.time() * 1000)}",
                time=time.time()
            ),
            message_segment=Seg(type="text", data=(
                f"服务器统计:\n"
                f"当前用户数: {stats.get('current_users', 0)}\n"
                f"当前连接数: {stats.get('current_connections', 0)}\n"
                f"成功认证数: {stats.get('successful_auths', 0)}\n"
                f"处理消息数: {stats.get('messages_processed', 0)}"
            )),
            message_dim=MessageDim(api_key="server", platform="server")
        )

        # 使用新的接口，从原消息中获取目标API Key
        stats_message.message_dim.api_key = original_message.get_api_key()  # 设置目标API Key
        stats_message.message_dim.platform = original_message.get_platform()  # 设置目标平台
        results = await self.server.send_message(stats_message)
        logger.info(f"统计消息发送结果: {results}")

    async def start(self):
        """启动服务器"""
        await self.server.start()
        logger.info(f"🚀 聊天服务器启动在 ws://{self.config.host}:{self.config.port}{self.config.path}")

    async def stop(self):
        """停止服务器"""
        await self.server.stop()
        logger.info("🛑 聊天服务器已停止")


class ChatClient:
    """聊天客户端示例"""

    def __init__(self, name: str, api_key: str, platform: str = "example"):
        self.name = name
        self.api_key = api_key
        self.platform = platform

        # 创建客户端配置
        self.config = create_client_config(
            url="ws://localhost:18050/ws",
            api_key=api_key,
            platform=platform
        )

        # 设置回调
        self.config.on_connect = self._on_connect
        self.config.on_disconnect = self._on_disconnect
        self.config.on_message = self._on_message

        # 注册自定义处理器
        self.config.register_custom_handler("room_notification", self._handle_room_notification)

        # 创建客户端
        self.client = WebSocketClient(self.config)

    async def _on_connect(self, connection_uuid: str, config: Dict[str, Any]):
        """连接成功回调"""
        logger.info(f"✅ {self.name} 连接成功: {connection_uuid}")

    async def _on_disconnect(self, connection_uuid: str, error: str = None):
        """断开连接回调"""
        if error:
            logger.error(f"❌ {self.name} 连接断开: {connection_uuid} - {error}")
        else:
            logger.info(f"🔌 {self.name} 连接断开: {connection_uuid}")

    async def _on_message(self, message: APIMessageBase, metadata: Dict[str, Any]):
        """收到消息回调"""
        logger.info(f"📨 {self.name} 收到消息: {message.message_segment.data}")

    async def _handle_room_notification(self, message_data: Dict[str, Any]):
        """处理房间通知"""
        logger.info(f"🏠 {self.name} 收到房间通知: {message_data}")

    async def start(self):
        """启动客户端"""
        await self.client.start()

    async def stop(self):
        """停止客户端"""
        await self.client.stop()

    async def connect(self) -> bool:
        """连接到服务器"""
        return await self.client.connect()

    async def disconnect(self):
        """断开连接"""
        await self.client.disconnect()

    async def send_message(self, content: str) -> bool:
        """发送消息"""
        message = APIMessageBase(
            message_info=BaseMessageInfo(
                platform=self.platform,
                message_id=f"{self.name}_{int(time.time() * 1000)}",
                time=time.time(),
                sender_info=SenderInfo(
                    user_info=UserInfo(
                        platform=self.platform,
                        user_id=self.api_key,
                        user_nickname=self.name
                    )
                )
            ),
            message_segment=Seg(type="text", data=content),
            message_dim=MessageDim(api_key=self.api_key, platform=self.platform)
        )

        return await self.client.send_message(message)

    async def send_join_room(self, room_name: str):
        """发送加入房间消息"""
        return await self.client.send_custom_message("join_room", {
            "room_name": room_name,
            "user_id": self.api_key
        })

    async def send_leave_room(self, room_name: str):
        """发送离开房间消息"""
        return await self.client.send_custom_message("leave_room", {
            "room_name": room_name,
            "user_id": self.api_key
        })


async def main():
    """主函数 - 演示外部库使用"""
    print("🎯 API-Server Version 外部库使用示例")
    print("=" * 50)

    # 1. 导入验证
    print("\n📦 验证导入方式:")
    try:
        # 这应该成功
        from maim_message.message import APIMessageBase as MsgFromSubmodule
        from maim_message.server import WebSocketServer as ServerFromSubmodule
        from maim_message.client import WebSocketClient as ClientFromSubmodule
        print("✅ 从子模块导入成功")

        # 这应该失败
        try:
            from maim_message import APIMessageBase
            print("❌ 不应该能从根模块导入APIMessageBase")
        except ImportError:
            print("✅ 正确：无法从根模块导入APIMessageBase")

    except Exception as e:
        print(f"❌ 导入验证失败: {e}")
        return

    # 2. 创建服务器
    print("\n🚀 创建聊天服务器:")
    server = ChatServer()

    # 3. 启动服务器
    await server.start()

    # 4. 等待服务器启动完成
    await asyncio.sleep(1)

    # 5. 创建多个客户端
    print("\n🔗 创建客户端:")
    clients = [
        ChatClient("Alice", "alice_123", "wechat"),
        ChatClient("Bob", "bob_456", "qq"),
        ChatClient("Charlie", "charlie_789", "telegram")
    ]

    # 6. 启动客户端
    for client in clients:
        await client.start()

    # 7. 连接客户端
    for i, client in enumerate(clients, 1):
        connected = await client.connect()
        print(f"   客户端{i} ({client.name}) 连接{'成功' if connected else '失败'}")
        await asyncio.sleep(0.5)  # 避免同时连接

    # 8. 发送测试消息
    print("\n💬 发送测试消息:")
    for client in clients:
        await client.send_message(f"Hello, I'm {client.name}!")
        await asyncio.sleep(0.5)

    # 9. 测试特殊命令
    print("\n⚡ 测试特殊命令:")
    await clients[0].send_message("echo 这是一个回声测试")
    await clients[1].send_message("time")
    await clients[2].send_message("stats")

    # 10. 测试房间功能
    print("\n🏠 测试房间功能:")
    for client in clients:
        await client.send_join_room("general_chat")
        await asyncio.sleep(0.3)

    # 11. 运行一段时间
    print("\n⏳ 运行10秒钟...")
    await asyncio.sleep(10)

    # 12. 清理资源
    print("\n🧹 清理资源:")
    for client in clients:
        await client.disconnect()
        await client.stop()
        print(f"   {client.name} 已停止")

    await asyncio.sleep(2)
    await server.stop()
    print("   服务器已停止")

    print("\n🎉 示例运行完成!")
    print("=" * 50)
    print("\n✅ 导入方式总结:")
    print("   ✅ from maim_message.message import APIMessageBase")
    print("   ✅ from maim_message.server import WebSocketServer")
    print("   ✅ from maim_message.client import WebSocketClient")
    print("   ❌ from maim_message import APIMessageBase  # 会失败")


if __name__ == "__main__":
    asyncio.run(main())