"""WebSocket网络驱动器模式外部库导入测试脚本
测试标准APIMessageBase消息格式的发送、接收和回调功能（API-Server Version）
使用pip install -e .安装的外部maim_message库进行测试，验证真实使用场景
"""

import sys
import os
import asyncio
import logging
import time
from typing import List, Dict, Any

# 外部库导入测试 - 使用pip安装的maim_message包
# API-Server Version 必须从子模块导入
from maim_message.server import WebSocketServer, ServerConfig, AuthResult, create_server_config
from maim_message.client import WebSocketClient, ClientConfig, create_client_config
from maim_message.message import (
    APIMessageBase, BaseMessageInfo, Seg, MessageDim,
    GroupInfo, UserInfo, SenderInfo, FormatInfo
)


# 配置日志 - 设置INFO级别
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class WebSocketTester:
    """WebSocket API测试器"""

    def __init__(self, host: str = "localhost", port: int = 18040):
        self.host = host
        self.port = port
        self.server = None
        self.clients: List[WebSocketClient] = []
        self.test_results = {
            "server_started": False,
            "clients_connected": 0,
            "messages_sent": 0,
            "messages_received": 0,
            "custom_messages_sent": 0,
            "custom_messages_received": 0,
            "callback_triggered": 0,
            "errors": []
        }

        # 收集的数据
        self.received_messages: List[Dict[str, Any]] = []
        self.received_custom_messages: List[Dict[str, Any]] = []
        self.connection_events: List[Dict[str, Any]] = []
        self.disconnect_events: List[Dict[str, Any]] = []

    def create_auth_handler(self):
        """创建认证处理器"""
        async def auth_handler(metadata):
            api_key = metadata.get("api_key", "")
            platform = metadata.get("platform", "unknown")

            # 简单的认证逻辑：包含"test"的api_key通过认证
            if "test" in api_key:
                return True
            else:
                return False
        return auth_handler

    def create_user_extractor(self):
        """创建用户标识提取器 - 将api_key转换为user_id"""
        async def user_extractor(metadata):
            api_key = metadata.get("api_key", "")
            if not api_key:
                raise ValueError("缺少api_key")

            # 模拟真实的用户标识转换逻辑
            # 例如：test_user_001 -> real_user_001
            # 或者：tenant123:agent456 -> user_uuid_789
            if api_key.startswith("test_user_"):
                # 测试环境：test_user_001 -> real_user_001
                user_id = api_key.replace("test_user_", "real_user_")
            elif ":" in api_key:
                # 生产环境：tenant_id:agent_id -> user_uuid
                tenant_id, agent_id = api_key.split(":", 1)
                user_id = f"user_uuid_{tenant_id}_{agent_id}"
            else:
                # 默认转换
                user_id = f"user_{api_key}"

            logger.info(f"🔄 用户标识转换: api_key='{api_key}' -> user_id='{user_id}'")
            return user_id
        return user_extractor

    def create_message_handlers(self):
        """创建消息处理器"""
        async def message_handler(server_message: APIMessageBase, metadata: Dict[str, Any]):
            """处理标准消息"""
            try:
                logger.info(f"📨 收到标准消息: {server_message.message_segment.data}")
                logger.info(f"   发送者: {server_message.get_api_key()}")
                logger.info(f"   平台: {server_message.get_platform()}")

                self.test_results["messages_received"] += 1
                self.test_results["callback_triggered"] += 1

                # 保存收到的消息
                self.received_messages.append({
                    "data": server_message.message_segment.data,
                    "api_key": server_message.get_api_key(),
                    "platform": server_message.get_platform(),
                    "message_id": server_message.message_info.message_id,
                    "timestamp": time.time()
                })

            except Exception as e:
                logger.error(f"消息处理器错误: {e}")
                self.test_results["errors"].append(f"消息处理器错误: {e}")

        async def ping_handler(message_data, metadata):
            """处理PING自定义消息"""
            try:
                payload = message_data.get("payload", {})
                logger.info(f"🏓 收到PING: {payload}")

                self.test_results["custom_messages_received"] += 1
                self.test_results["callback_triggered"] += 1

                # 保存自定义消息
                self.received_custom_messages.append({
                    "type": "custom_ping",
                    "payload": payload,
                    "timestamp": time.time()
                })

                # 自动回复PONG - 服务端根据连接元数据确定用户
                await self.send_pong_response(payload, metadata)

            except Exception as e:
                logger.error(f"PING处理器错误: {e}")
                self.test_results["errors"].append(f"PING处理器错误: {e}")

        async def status_handler(message_data, metadata):
            """处理状态查询自定义消息"""
            try:
                payload = message_data.get("payload", {})
                logger.info(f"📊 收到状态查询: {payload}")

                self.test_results["custom_messages_received"] += 1

                # 回复状态信息
                await self.send_status_response(payload)

            except Exception as e:
                logger.error(f"状态处理器错误: {e}")
                self.test_results["errors"].append(f"状态处理器错误: {e}")

        return message_handler, ping_handler, status_handler

    async def send_pong_response(self, original_ping: Dict[str, Any], metadata: Dict[str, Any]):
        """发送PONG响应"""
        pong_message = APIMessageBase(
            message_info=BaseMessageInfo(
                platform="server",
                message_id=f"pong_{int(time.time() * 1000)}",
                time=time.time()
            ),
            message_segment=Seg(
                type="text",
                data=f"PONG response to: {original_ping.get('message', 'unknown')}"
            ),
            message_dim=MessageDim(
                api_key="server",
                platform="server"
            )
        )

        # 服务端根据连接元数据中的connection_uuid获取对应的user_id
        connection_uuid = metadata.get("uuid")
        if connection_uuid:
            # 从服务端获取该连接对应的user_id
            user_id = self.server.get_connection_user(connection_uuid)
            if user_id:
                results = await self.server.send_message(user_id, pong_message)
                success_count = sum(results.values())
                logger.info(f"   📤 发送PONG给用户 {user_id}: {success_count} 个连接成功")
            else:
                logger.warning(f"   ⚠️ 找不到连接 {connection_uuid} 对应的用户")
        else:
            logger.warning(f"   ⚠️ 连接元数据中没有uuid")

    async def send_status_response(self, original_request: Dict[str, Any]):
        """发送状态响应"""
        status_info = {
            "server_status": "running",
            "connected_users": self.server.get_user_count(),
            "connected_clients": self.server.get_connection_count(),
            "messages_processed": self.test_results["messages_received"],
            "custom_messages_processed": self.test_results["custom_messages_received"]
        }

        status_message = APIMessageBase(
            message_info=BaseMessageInfo(
                platform="server",
                message_id=f"status_{int(time.time() * 1000)}",
                time=time.time()
            ),
            message_segment=Seg(
                type="json",
                data=str(status_info)
            ),
            message_dim=MessageDim(
                api_key="server",
                platform="server"
            )
        )

        await self.server.broadcast_message(status_message)
        logger.info(f"   📊 广播状态信息: {status_info}")

    def create_standard_message(self, platform: str, api_key: str, message_content: str) -> APIMessageBase:
        """创建标准APIMessageBase消息"""
        return APIMessageBase(
            message_info=BaseMessageInfo(
                platform=platform,
                message_id=f"{platform}_{int(time.time() * 1000)}",
                time=time.time(),
                sender_info=SenderInfo(
                    user_info=UserInfo(
                        platform=platform,
                        user_id="test_user_001",
                        user_nickname="测试用户",
                        user_cardname="测试卡片"
                    ),
                    group_info=GroupInfo(
                        group_id="test_group_001",
                        group_name="测试群组",
                        platform=platform
                    )
                ),
                format_info=FormatInfo(
                    content_format=["text"],
                    accept_format=["text", "emoji"]
                )
            ),
            message_segment=Seg(
                type="text",
                data=message_content
            ),
            message_dim=MessageDim(
                api_key=api_key,
                platform=platform
            )
        )

    async def setup_server(self):
        """设置服务器"""
        logger.info("🚀 启动WebSocket服务器...")

        # 创建服务器配置
        server_config = ServerConfig(
            host=self.host,
            port=self.port,
            path="/ws"
        )

        # 设置认证和用户标识提取处理器
        server_config.on_auth = self.create_auth_handler()
        server_config.on_auth_extract_user = self.create_user_extractor()

        # 设置消息处理器
        message_handler, ping_handler, status_handler = self.create_message_handlers()
        server_config.on_message = message_handler
        server_config.register_custom_handler("ping", ping_handler)
        server_config.register_custom_handler("status", status_handler)

        # 设置连接/断连处理器
        async def connect_handler(connection_uuid, metadata):
            event = {
                "type": "connect",
                "connection_uuid": connection_uuid,
                "metadata": metadata,
                "timestamp": time.time()
            }
            self.connection_events.append(event)
            logger.info(f"🔗 客户端连接: {connection_uuid}")

        async def disconnect_handler(connection_uuid, error):
            event = {
                "type": "disconnect",
                "connection_uuid": connection_uuid,
                "error": error,
                "timestamp": time.time()
            }
            self.disconnect_events.append(event)
            logger.info(f"🔌 客户端断开: {connection_uuid}")

        server_config.on_connect = connect_handler
        server_config.on_disconnect = disconnect_handler

        # 创建服务器
        self.server = WebSocketServer(server_config)

        # 启动服务器
        await self.server.start()
        self.test_results["server_started"] = True
        logger.info(f"✅ 服务器已启动在 {self.host}:{self.port}")

    async def setup_clients(self, client_count: int = 3):
        """设置多个客户端"""
        logger.info(f"🔗 创建 {client_count} 个客户端...")

        platforms = ["wechat", "qq", "telegram"]

        for i in range(client_count):
            platform = platforms[i % len(platforms)]
            api_key = f"test_user_{i+1:03d}"

            # 创建客户端配置
            client_config = ClientConfig(
                url=f"ws://{self.host}:{self.port}/ws",
                api_key=api_key,
                platform=platform,
                auto_reconnect=True
            )

            # 设置客户端消息处理器
            async def client_message_handler(server_message, metadata, client_idx=i+1):
                logger.info(f"📤 客户端{client_idx}收到: {server_message.message_segment.data}")
                self.test_results["callback_triggered"] += 1

            client_config.on_message = client_message_handler

            # 创建客户端
            client = WebSocketClient(client_config)
            self.clients.append(client)

            # 启动客户端
            await client.start()
            # 主动建立连接
            await client.connect()
            await asyncio.sleep(1.0)  # 给连接更多时间

            if client.is_connected():
                self.test_results["clients_connected"] += 1
                logger.info(f"✅ 客户端{i+1} ({platform}) 连接成功")
            else:
                logger.warning(f"⚠️ 客户端{i+1} ({platform}) 连接失败")

    async def test_standard_messages(self):
        """测试标准消息发送"""
        logger.info("📨 测试标准消息发送...")

        test_messages = [
            ("wechat", "test_user_001", "Hello from WeChat client!"),
            ("qq", "test_user_002", "Hello from QQ client!"),
            ("telegram", "test_user_003", "Hello from Telegram client!")
        ]

        for platform, api_key, content in test_messages:
            # 创建标准消息（客户端使用api_key）
            message = self.create_standard_message(platform, api_key, content)

            # 找到对应的客户端并发送
            for i, client in enumerate(self.clients):
                if client.config.platform == platform:
                    success = await client.send_message(message)
                    if success:
                        self.test_results["messages_sent"] += 1
                        logger.info(f"✅ {platform} 客户端发送成功 (api_key: {api_key})")
                    else:
                        logger.error(f"❌ {platform} 客户端发送失败")
                    break

            await asyncio.sleep(0.3)  # 消息间隔

        # 等待服务端处理
        await asyncio.sleep(1)

        # 服务端向转换后的user_id发送消息，测试路由
        logger.info("🔙 服务端向转换后的user_id发送消息...")
        test_user_ids = ["real_user_001", "real_user_002", "real_user_003"]

        for user_id in test_user_ids:
            response_message = APIMessageBase(
                message_info=BaseMessageInfo(
                    platform="server",
                    message_id=f"server_{int(time.time() * 1000)}",
                    time=time.time()
                ),
                message_segment=Seg(
                    type="text",
                    data=f"服务器消息给 {user_id} (已转换的用户标识)"
                ),
                message_dim=MessageDim(
                    api_key="server",
                    platform="server"
                )
            )

            # 使用转换后的user_id发送 - 测试路由
            results = await self.server.send_message(user_id, response_message)
            success_count = sum(results.values())
            if success_count > 0:
                self.test_results["messages_sent"] += 1
                logger.info(f"✅ 服务端向用户 {user_id} 发送成功: {success_count} 个连接")
            else:
                logger.warning(f"⚠️ 用户 {user_id} 没有在线连接")

            await asyncio.sleep(0.3)

    async def test_custom_messages(self):
        """测试自定义消息发送"""
        logger.info("🔧 测试自定义消息发送...")

        # 每个客户端发送PING和状态查询
        for i, client in enumerate(self.clients):
            # 发送PING - 客户端只知道自己知道的api_key，不包含user_id
            ping_success = await client.send_custom_message("ping", {
                "message": f"Hello from client {i+1}",
                "timestamp": time.time()
            })

            if ping_success:
                self.test_results["custom_messages_sent"] += 1
                logger.info(f"✅ 客户端{i+1} PING发送成功")

            # 发送状态查询
            status_success = await client.send_custom_message("status", {
                "request_type": "server_status",
                "client_id": i+1,
                "timestamp": time.time()
            })

            if status_success:
                self.test_results["custom_messages_sent"] += 1
                logger.info(f"✅ 客户端{i+1} 状态查询发送成功")

            await asyncio.sleep(0.3)  # 消息间隔

    async def test_server_broadcast(self):
        """测试服务器广播"""
        logger.info("📡 测试服务器广播...")

        broadcast_message = APIMessageBase(
            message_info=BaseMessageInfo(
                platform="server",
                message_id=f"broadcast_{int(time.time() * 1000)}",
                time=time.time()
            ),
            message_segment=Seg(
                type="text",
                data="📢 Broadcast message from server to all clients!"
            ),
            message_dim=MessageDim(
                api_key="server",
                platform="server"
            )
        )

        results = await self.server.broadcast_message(broadcast_message)
        success_count = sum(results.values())
        logger.info(f"📡 广播结果: {success_count}/{len(results)} 客户端收到")

    async def cleanup(self):
        """清理资源"""
        logger.info("🧹 清理资源...")

        try:
            # 优雅停止所有客户端
            for i, client in enumerate(self.clients):
                try:
                    logger.info(f"🔄 正在停止客户端{i+1}...")
                    await asyncio.wait_for(client.stop(), timeout=5.0)
                    logger.info(f"✅ 客户端{i+1} 已优雅停止")
                except asyncio.TimeoutError:
                    logger.warning(f"⚠️ 客户端{i+1} 停止超时，但已触发关闭信号")
                except Exception as e:
                    logger.error(f"❌ 客户端{i+1} 停止时出错: {e}")

            # 优雅停止服务器
            if self.server:
                try:
                    logger.info("🔄 正在停止服务器...")
                    await asyncio.wait_for(self.server.stop(), timeout=10.0)
                    logger.info("✅ 服务器已优雅停止")
                except asyncio.TimeoutError:
                    logger.warning("⚠️ 服务器停止超时，但已触发关闭信号")
                except Exception as e:
                    logger.error(f"❌ 服务器停止时出错: {e}")

            logger.info("🎉 所有资源已优雅清理完成")

        except Exception as e:
            logger.error(f"❌ 清理过程中发生错误: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

    def print_test_results(self):
        """打印测试结果"""
        print("\n" + "="*60)
        print("🧪 WebSocket API 测试结果")
        print("="*60)

        print(f"\n📊 基本统计:")
        print(f"  服务器启动: {'✅' if self.test_results['server_started'] else '❌'}")
        print(f"  客户端连接数: {self.test_results['clients_connected']}/{len(self.clients)}")
        print(f"  标准消息发送: {self.test_results['messages_sent']}")
        print(f"  标准消息接收: {self.test_results['messages_received']}")
        print(f"  自定义消息发送: {self.test_results['custom_messages_sent']}")
        print(f"  自定义消息接收: {self.test_results['custom_messages_received']}")
        print(f"  回调触发次数: {self.test_results['callback_triggered']}")

        print(f"\n🔗 连接事件:")
        print(f"  连接建立: {len(self.connection_events)}")
        print(f"  连接断开: {len(self.disconnect_events)}")

        if self.test_results["errors"]:
            print(f"\n❌ 错误信息:")
            for error in self.test_results["errors"]:
                print(f"  - {error}")

        if self.received_messages:
            print(f"\n📨 收到的标准消息:")
            for msg in self.received_messages[:3]:  # 只显示前3条
                print(f"  - {msg['platform']}: {msg['data']}")

        if self.received_custom_messages:
            print(f"\n🔧 收到的自定义消息:")
            for msg in self.received_custom_messages[:3]:  # 只显示前3条
                print(f"  - {msg['type']}: {msg['payload']}")

        success = (
            self.test_results['server_started'] and
            self.test_results['clients_connected'] == len(self.clients) and
            self.test_results['messages_sent'] > 0 and
            self.test_results['messages_received'] > 0 and
            self.test_results['custom_messages_sent'] > 0 and
            self.test_results['custom_messages_received'] > 0 and
            len(self.test_results['errors']) == 0
        )

        print(f"\n🎯 测试结果: {'✅ 全部通过' if success else '❌ 存在问题'}")
        print("="*60)

        return success


async def main():
    """主测试函数"""
    tester = WebSocketTester(host="localhost", port=18040)

    try:
        # 设置超时，确保程序能正常退出
        timeout_task = asyncio.create_task(asyncio.sleep(15))  # 15秒超时
        test_task = asyncio.create_task(run_test(tester))

        # 等待测试完成或超时
        done, pending = await asyncio.wait(
            [test_task, timeout_task],
            return_when=asyncio.FIRST_COMPLETED
        )

        # 取消未完成的任务
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        if timeout_task in done:
            print("⏰ 测试超时，强制退出")
        else:
            print("✅ 测试正常完成")

    except KeyboardInterrupt:
        print("\n用户中断测试")
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理资源 - 确保在任何情况下都执行优雅关闭
        try:
            await asyncio.wait_for(tester.cleanup(), timeout=20.0)
        except asyncio.TimeoutError:
            print("⚠️ 清理超时，但已触发所有关闭信号")
        except Exception as e:
            print(f"⚠️ 清理过程中发生错误: {e}")
        finally:
            print("🏁 测试程序退出")


async def run_test(tester):
    """运行实际测试"""
    # 1. 启动服务器
    await tester.setup_server()
    await asyncio.sleep(1)

    # 2. 连接客户端
    await tester.setup_clients(client_count=3)
    await asyncio.sleep(2)

    # 3. 测试标准消息
    await tester.test_standard_messages()
    await asyncio.sleep(2)

    # 4. 测试自定义消息
    await tester.test_custom_messages()
    await asyncio.sleep(2)

    # 5. 测试服务器广播
    await tester.test_server_broadcast()
    await asyncio.sleep(2)

    # 6. 打印测试结果
    tester.print_test_results()


if __name__ == "__main__":
    print("🚀 开始WebSocket网络驱动器模式外部库导入测试...")
    asyncio.run(main())