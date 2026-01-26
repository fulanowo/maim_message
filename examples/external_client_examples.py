"""
非maim_message客户端示例
展示如何使用原生WebSocket协议与maim_message API-Server通信

这些示例不依赖maim_message库，仅使用标准WebSocket和JSON库
"""

import asyncio
import json
import websockets
import time
import uuid
import ssl

# ===========================================
# 基础Python WebSocket客户端
# ===========================================


class BasicWebSocketClient:
    """基础WebSocket客户端"""

    def __init__(self, url, api_key, platform="python_basic"):
        self.url = url
        self.api_key = api_key
        self.platform = platform
        self.websocket = None

    async def connect(self):
        """连接到WebSocket服务器"""
        try:
            # 方式1：通过查询参数（推荐）
            ws_url = f"{self.url}?api_key={self.api_key}&platform={self.platform}"
            self.websocket = await websockets.connect(ws_url, max_size=104_857_600)
            print(f"✅ 连接成功: {self.url}")
            return True
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            return False

    def create_message(self, text, user_info=None):
        """创建符合maim_message协议的消息"""
        if user_info is None:
            user_info = {
                "user_id": f"{self.platform}_user",
                "user_nickname": f"{self.platform}客户端",
                "user_cardname": f"{self.platform}客户端",
            }

        message = {
            "message_info": {
                "platform": self.platform,
                "message_id": f"msg_{uuid.uuid4()}",
                "time": time.time(),
                "sender_info": {"user_info": {"platform": self.platform, **user_info}},
            },
            "message_segment": {"type": "text", "data": text},
            "message_dim": {"api_key": self.api_key, "platform": self.platform},
        }
        return message

    async def send_message(self, text, user_info=None):
        """发送消息"""
        if not self.websocket:
            raise ConnectionError("WebSocket未连接")

        message = self.create_message(text, user_info)
        try:
            await self.websocket.send(json.dumps(message))
            print(f"📤 消息已发送: {text}")
            return True
        except Exception as e:
            print(f"❌ 发送失败: {e}")
            return False

    async def receive_message(self):
        """接收消息"""
        if not self.websocket:
            raise ConnectionError("WebSocket未连接")

        try:
            message = await self.websocket.recv()
            data = json.loads(message)
            print(
                f"📨 收到消息: {data.get('message_segment', {}).get('data', 'Unknown')}"
            )
            return data
        except Exception as e:
            print(f"❌ 接收失败: {e}")
            return None

    async def close(self):
        """关闭连接"""
        if self.websocket:
            await self.websocket.close()
            print("🔌 连接已关闭")


# ===========================================
# SSL安全连接客户端
# ===========================================


class SecureWebSocketClient(BasicWebSocketClient):
    """支持SSL的WebSocket客户端"""

    def __init__(
        self, url, api_key, platform="python_secure", ssl_verify=True, ssl_ca_file=None
    ):
        # 确保使用wss://协议
        if not url.startswith("wss://"):
            url = url.replace("ws://", "wss://")

        super().__init__(url, api_key, platform)
        self.ssl_verify = ssl_verify
        self.ssl_ca_file = ssl_ca_file

    async def connect(self):
        """连接到SSL WebSocket服务器"""
        try:
            # 配置SSL上下文
            ssl_context = ssl.create_default_context()

            if not self.ssl_verify:
                # 开发环境：禁用证书验证
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                print("⚠️ SSL证书验证已禁用（仅限开发环境）")

            if self.ssl_ca_file:
                # 加载CA证书
                ssl_context.load_verify_locations(self.ssl_ca_file)
                print(f"✅ 已加载CA证书: {self.ssl_ca_file}")

            # 构建连接URL（包含API Key和平台）
            ws_url = f"{self.url}?api_key={self.api_key}&platform={self.platform}"
            self.websocket = await websockets.connect(
                ws_url, ssl=ssl_context, max_size=104_857_600
            )
            print(f"✅ SSL连接成功: {self.url}")
            return True

        except Exception as e:
            print(f"❌ SSL连接失败: {e}")
            return False


# ===========================================
# 自动重连客户端
# ===========================================


class ReconnectingWebSocketClient(BasicWebSocketClient):
    """支持自动重连的WebSocket客户端"""

    def __init__(
        self,
        url,
        api_key,
        platform="python_reconnect",
        max_reconnect_attempts=5,
        reconnect_delay=2,
    ):
        super().__init__(url, api_key, platform)
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_delay = reconnect_delay
        self.reconnect_count = 0

    async def connect_with_retry(self):
        """支持重试的连接"""
        attempt = 0

        while attempt < self.max_reconnect_attempts:
            try:
                if await self.connect():
                    self.reconnect_count = 0
                    return True
            except Exception as e:
                print(f"连接尝试 {attempt + 1} 失败: {e}")

            attempt += 1
            if attempt < self.max_reconnect_attempts:
                print(f"等待 {self.reconnect_delay} 秒后重试...")
                await asyncio.sleep(self.reconnect_delay)

        print(f"❌ 连接失败，已达到最大重试次数 ({self.max_reconnect_attempts})")
        return False

    async def send_message_with_reconnect(self, text, user_info=None):
        """支持重连的消息发送"""
        if not self.websocket or self.websocket.closed:
            print("连接已断开，尝试重新连接...")
            if not await self.connect_with_retry():
                return False

        try:
            return await self.send_message(text, user_info)
        except Exception as e:
            print(f"发送失败，尝试重连: {e}")
            if await self.connect_with_retry():
                return await self.send_message(text, user_info)
            return False


# ===========================================
# 客户端工厂和便捷函数
# ===========================================


class WebSocketClientFactory:
    """WebSocket客户端工厂"""

    @staticmethod
    def create_basic_client(
        host="localhost", port=18040, api_key="demo_key", platform="demo"
    ):
        """创建基础客户端"""
        url = f"ws://{host}:{port}/ws"
        return BasicWebSocketClient(url, api_key, platform)

    @staticmethod
    def create_ssl_client(
        host="localhost",
        port=18044,
        api_key="demo_key",
        platform="demo",
        ssl_verify=False,
    ):
        """创建SSL客户端"""
        url = f"wss://{host}:{port}/ws"
        return SecureWebSocketClient(url, api_key, platform, ssl_verify)

    @staticmethod
    def create_reconnecting_client(
        host="localhost", port=18040, api_key="demo_key", platform="demo"
    ):
        """创建自动重连客户端"""
        url = f"ws://{host}:{port}/ws"
        return ReconnectingWebSocketClient(url, api_key, platform)


# ===========================================
# 示例使用函数
# ===========================================


async def basic_client_example():
    """基础客户端示例"""
    print("\n🔗 基础WebSocket客户端示例")
    print("-" * 40)

    client = WebSocketClientFactory.create_basic_client(
        api_key="basic_demo_key", platform="python_basic_demo"
    )

    try:
        if await client.connect():
            # 发送多条消息
            messages = [
                "Hello from basic client!",
                "这是来自基础Python客户端的消息",
                "WebSocket通信测试 🎉",
            ]

            for msg in messages:
                await client.send_message(msg)
                # 等待可能的响应
                response = await asyncio.wait_for(client.receive_message(), timeout=2)
                if response:
                    print(f"  服务器响应内容: {response}")
                await asyncio.sleep(1)

    finally:
        await client.close()


async def ssl_client_example():
    """SSL客户端示例"""
    print("\n🔒 SSL WebSocket客户端示例")
    print("-" * 40)

    client = WebSocketClientFactory.create_ssl_client(
        port=18044,
        api_key="ssl_demo_key",
        platform="python_ssl_demo",
        ssl_verify=False,  # 开发环境禁用证书验证
    )

    try:
        if await client.connect():
            secure_messages = [
                "🛡️ 安全连接测试消息",
                "这是通过SSL/TLS加密传输的消息",
                "数据加密验证成功 🔐",
            ]

            for msg in secure_messages:
                await client.send_message(msg)
                await asyncio.sleep(1)

    finally:
        await client.close()


async def reconnecting_client_example():
    """自动重连客户端示例"""
    print("\n🔄 自动重连WebSocket客户端示例")
    print("-" * 40)

    client = WebSocketClientFactory.create_reconnecting_client(
        api_key="reconnect_demo_key", platform="python_reconnect_demo"
    )

    try:
        if await client.connect_with_retry():
            resilient_messages = [
                "第一条消息（正常连接）",
                "第二条消息（测试连接稳定性）",
                "第三条消息（验证重连机制）",
            ]

            for msg in resilient_messages:
                success = await client.send_message_with_reconnect(msg)
                if success:
                    print(f"  ✅ 消息发送成功: {msg}")
                else:
                    print(f"  ❌ 消息发送失败: {msg}")
                await asyncio.sleep(1)

    finally:
        await client.close()


async def group_message_example():
    """群组消息示例"""
    print("\n👥 群组消息示例")
    print("-" * 40)

    client = WebSocketClientFactory.create_basic_client(
        api_key="group_demo_key", platform="python_group_demo"
    )

    try:
        if await client.connect():
            # 群组用户信息
            group_user_info = {
                "user_id": "group_user_001",
                "user_nickname": "群成员小明",
                "user_cardname": "产品经理-小明",
            }

            # 群组消息结构
            group_message = {
                "message_info": {
                    "platform": "python_group_demo",
                    "message_id": f"group_msg_{uuid.uuid4()}",
                    "time": time.time(),
                    "sender_info": {
                        "user_info": {
                            "platform": "python_group_demo",
                            **group_user_info,
                        },
                        "group_info": {
                            "platform": "python_group_demo",
                            "group_id": "demo_group_001",
                            "group_name": "maim_message技术交流群",
                        },
                    },
                },
                "message_segment": {
                    "type": "text",
                    "data": "大家好，我是通过自定义客户端加入群聊的成员！",
                },
                "message_dim": {
                    "api_key": "group_demo_key",
                    "platform": "python_group_demo",
                },
            }

            await client.websocket.send(json.dumps(group_message))
            print(f"📤 群组消息已发送: {group_message['message_segment']['data']}")

            # 等待响应
            response = await asyncio.wait_for(client.receive_message(), timeout=3)
            if response:
                print("  📨 收到群组消息响应")

    finally:
        await client.close()


async def image_message_example():
    """图片消息示例"""
    print("\n🖼️ 图片消息示例")
    print("-" * 40)

    client = WebSocketClientFactory.create_basic_client(
        api_key="image_demo_key", platform="python_image_demo"
    )

    try:
        if await client.connect():
            # 创建图片消息
            image_message = client.create_message("")
            image_message["message_segment"] = {
                "type": "image",
                "data": "https://via.placeholder.com/300x200.png?text=Demo+Image",
            }

            await client.websocket.send(json.dumps(image_message))
            print(f"📤 图片消息已发送: {image_message['message_segment']['data']}")

            # 等待响应
            response = await asyncio.wait_for(client.receive_message(), timeout=3)
            if response:
                print("  📨 收到图片消息响应")

    finally:
        await client.close()


# ===========================================
# 主函数和测试套件
# ===========================================


async def main():
    """主函数 - 运行所有示例"""
    print("🚀 非maim_message客户端示例启动")
    print("=" * 50)

    # 注意：这些示例需要maim_message API-Server正在运行
    # 基础服务器：ws://localhost:18040/ws
    # SSL服务器：wss://localhost:18044/ws (如果配置了SSL)

    examples = [
        ("基础客户端", basic_client_example),
        ("自动重连客户端", reconnecting_client_example),
        ("群组消息", group_message_example),
        ("图片消息", image_message_example),
        # SSL客户端示例（仅在服务器配置SSL时启用）
        # ("SSL客户端", ssl_client_example),
    ]

    for name, example_func in examples:
        print(f"\n📋 开始执行: {name}")
        try:
            await example_func()
            print(f"✅ {name} 示例完成")
        except Exception as e:
            print(f"❌ {name} 示例失败: {e}")

        # 示例之间的间隔
        if example_func != examples[-1][1]:
            await asyncio.sleep(2)

    print("\n🎉 所有示例执行完成!")
    print("\n💡 提示:")
    print("   - 确保maim_message API-Server正在运行")
    print("   - 默认连接地址: ws://localhost:18040/ws")
    print("   - 可以通过修改示例参数连接到不同服务器")
    print("   - 更多信息请参考: doc/external_client_communication_guide.md")


if __name__ == "__main__":
    print("🔧 启动非maim_message客户端示例...")
    asyncio.run(main())
