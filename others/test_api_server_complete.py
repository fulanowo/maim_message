"""
API-Server Version 完整测试脚本
测试标准APIMessageBase消息格式的发送、接收和回调功能

使用pip install -e .安装的外部maim_message库进行测试
验证API-Server Version的所有功能

特点：
1. 使用正确的模块导入方式
2. 完整的功能测试
3. 优雅的关闭机制
4. 30秒超时保护
"""

import sys
import os
import asyncio
import logging
import time
from typing import List, Dict, Any

# ✅ API-Server Version 正确导入方式
from maim_message.server import WebSocketServer, create_server_config
from maim_message.client import WebSocketClient, create_client_config
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


class APIServerTester:
    """API-Server Version完整测试类"""

    def __init__(self):
        self.server = None
        self.clients = []
        self.test_results = {
            "clients_connected": 0,
            "messages_received": 0,
            "custom_messages_received": 0,
            "messages_sent": 0,
            "errors": 0,
            "start_time": time.time()
        }

    async def create_server(self):
        """创建API-Server Version服务器"""
        # 创建服务器配置
        config = create_server_config(
            host="localhost",
            port=18070,
            path="/ws"
        )

        # 设置认证回调
        config.on_auth = self._authenticate
        config.on_auth_extract_user = self._extract_user

        # 创建消息处理器
        message_handler, ping_handler, status_handler = self.create_message_handlers()
        config.on_message = message_handler

        # 连接管理回调
        config.on_connect = self._on_connect
        config.on_disconnect = self._on_disconnect

        # 注册自定义处理器
        config.register_custom_handler("ping", ping_handler)
        config.register_custom_handler("status_request", status_handler)

        # 创建服务器
        self.server = WebSocketServer(config)
        logger.info("✅ API-Server Version服务器配置完成")

    async def _authenticate(self, metadata: Dict[str, Any]) -> bool:
        """认证连接"""
        api_key = metadata.get("api_key")
        if api_key:
            logger.debug(f"认证通过: api_key={api_key}")
            return True
        logger.warning("认证失败: 缺少api_key")
        return False

    async def _extract_user(self, metadata: Dict[str, Any]) -> str:
        """提取用户标识"""
        api_key = metadata.get("api_key", "")
        platform = metadata.get("platform", "unknown")

        # 将api_key转换为user_id
        user_id = f"real_user_{api_key.split('_')[-1]}"
        logger.info(f"🔄 用户标识转换: api_key='{api_key}' -> user_id='{user_id}'")
        return user_id

    async def _on_connect(self, connection_uuid: str, metadata: Dict[str, Any]):
        """连接回调"""
        logger.info(f"🔗 客户端连接: {connection_uuid}")
        self.test_results["clients_connected"] += 1

    async def _on_disconnect(self, connection_uuid: str, metadata: Dict[str, Any]):
        """断开连接回调"""
        logger.info(f"🔌 客户端断开: {connection_uuid}")

    def create_message_handlers(self):
        """创建消息处理器"""

        async def message_handler(server_message: APIMessageBase, metadata: Dict[str, Any]):
            """处理标准消息"""
            try:
                self.test_results["messages_received"] += 1
                logger.info(f"📨 收到标准消息: {server_message.message_segment.data}")
                logger.info(f"   发送者: {server_message.get_api_key()}")
                logger.info(f"   平台: {server_message.get_platform()}")
                return True
            except Exception as e:
                logger.error(f"标准消息处理错误: {e}")
                self.test_results["errors"] += 1
                return False

        async def ping_handler(message_data: Dict[str, Any], metadata: Dict[str, Any]):
            """处理PING消息"""
            try:
                self.test_results["custom_messages_received"] += 1
                logger.info(f"🏓 收到PING: {message_data}")

                # 发送PONG响应
                connection_uuid = metadata.get("connection_uuid")
                if connection_uuid:
                    pong_response = {
                        "type": "pong_response",
                        "original_message": message_data.get("message"),
                        "timestamp": time.time(),
                        "server_time": time.ctime()
                    }

                    await self.server.send_custom_message(
                        "pong_response", pong_response,
                        target_user=metadata.get("user_id")
                    )
                    logger.info(f"   📤 发送PONG给用户 {metadata.get('user_id')}")

                return True
            except Exception as e:
                logger.error(f"PING处理错误: {e}")
                self.test_results["errors"] += 1
                return False

        async def status_handler(message_data: Dict[str, Any], metadata: Dict[str, Any]):
            """处理状态查询"""
            try:
                self.test_results["custom_messages_received"] += 1
                logger.info(f"📊 收到状态查询: {message_data}")

                # 获取服务器统计
                stats = self.server.get_stats()
                status_info = {
                    "server_status": "running",
                    "connected_users": stats.get("current_users", 0),
                    "connected_clients": stats.get("current_connections", 0),
                    "messages_processed": self.test_results["messages_received"],
                    "custom_messages_processed": self.test_results["custom_messages_received"],
                    "uptime": time.time() - self.test_results["start_time"]
                }

                logger.info(f"   📊 广播状态信息: {status_info}")

                # 广播状态信息
                status_message = APIMessageBase(
                    message_info=BaseMessageInfo(
                        platform="server",
                        message_id=f"status_{int(time.time() * 1000)}",
                        time=time.time()
                    ),
                    message_segment=Seg(type="text", data=f"服务器状态: {status_info['connected_users']} 用户在线"),
                    message_dim=MessageDim(api_key="server", platform="server")
                )

                await self.server.broadcast_message(status_message)
                return True
            except Exception as e:
                logger.error(f"状态处理错误: {e}")
                self.test_results["errors"] += 1
                return False

        return message_handler, ping_handler, status_handler

    async def create_clients(self) -> List[WebSocketClient]:
        """创建API-Server Version客户端"""
        client_configs = [
            {"api_key": "test_user_001", "platform": "wechat"},
            {"api_key": "test_user_002", "platform": "qq"},
            {"api_key": "test_user_003", "platform": "telegram"}
        ]

        clients = []
        for i, config in enumerate(client_configs, 1):
            # 创建客户端配置
            client_config = create_client_config(
                url="ws://localhost:18070/ws",
                api_key=config["api_key"],
                platform=config["platform"]
            )

            # 设置客户端回调
            client_config.on_connect = self._client_on_connect
            client_config.on_disconnect = self._client_on_disconnect
            client_config.on_message = self._client_on_message

            # 注册自定义处理器
            client_config.register_custom_handler("pong_response", self._client_handle_pong)
            client_config.register_custom_handler("room_notification", self._client_handle_room_notification)

            # 创建客户端
            client = WebSocketClient(client_config)
            clients.append(client)

        return clients

    async def _client_on_connect(self, connection_uuid: str, config: Dict[str, Any]):
        """客户端连接回调"""
        logger.info(f"✅ 客户端连接: {connection_uuid}")

    async def _client_on_disconnect(self, connection_uuid: str, error: str = None):
        """客户端断开连接回调"""
        if error:
            logger.error(f"❌ 客户端断开: {connection_uuid} - {error}")
        else:
            logger.info(f"🔌 客户端断开: {connection_uuid}")

    async def _client_on_message(self, server_message: APIMessageBase, metadata: Dict[str, Any]):
        """客户端收到消息回调"""
        logger.info(f"📤 客户端收到: {server_message.message_segment.data}")

    async def _client_handle_pong(self, message_data: Dict[str, Any]):
        """客户端处理PONG响应"""
        logger.info(f"📤 客户端收到: PONG response to: {message_data.get('original_message')}")

    async def _client_handle_room_notification(self, message_data: Dict[str, Any]):
        """客户端处理房间通知"""
        logger.info(f"📤 客户端收到: {message_data.get('message')}")

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
                        user_id=api_key,
                        user_nickname=f"测试用户_{api_key.split('_')[-1]}",
                        user_cardname=f"测试卡片_{api_key.split('_')[-1]}"
                    ),
                    group_info=GroupInfo(
                        group_id="test_group_001",
                        group_name="API-Server Version测试群组",
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

    async def test_standard_messaging(self):
        """测试标准消息发送"""
        logger.info("📨 测试标准消息发送...")

        platforms = ["wechat", "qq", "telegram"]
        messages = [
            "Hello from WeChat client!",
            "Hello from QQ client!",
            "Hello from Telegram client!"
        ]

        for i, (client, platform, message_content) in enumerate(zip(self.clients, platforms, messages), 1):
            # 创建标准消息
            message = self.create_standard_message(
                platform=platform,
                api_key=f"test_user_{str(i).zfill(3)}",
                message_content=message_content
            )

            # 发送消息
            success = await client.send_message(message)
            self.test_results["messages_sent"] += 1

            if success:
                logger.info(f"✅ {platform} 客户端发送成功 (api_key: test_user_{str(i).zfill(3)})")
            else:
                logger.error(f"❌ {platform} 客户端发送失败")

            await asyncio.sleep(0.3)  # 避免同时发送

    async def test_server_to_client_messaging(self):
        """测试服务端向客户端发送消息"""
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
                message_dim=MessageDim(api_key="server", platform="server")
            )

            # 发送给指定用户
            results = await self.server.send_message(user_id, response_message)
            success_count = sum(results.values())
            logger.info(f"✅ 服务端向用户 {user_id} 发送成功: {success_count}/{len(results)} 个连接")

            await asyncio.sleep(0.2)

    async def test_custom_messaging(self):
        """测试自定义消息发送"""
        logger.info("🔧 测试自定义消息发送...")

        for i, client in enumerate(self.clients, 1):
            # 发送PING消息
            ping_success = await client.send_custom_message("ping", {
                "message": f"Hello from client {i}",
                "timestamp": time.time()
            })

            if ping_success:
                logger.info(f"✅ 客户端{i} PING发送成功")

            # 发送状态查询
            status_success = await client.send_custom_message("status_request", {
                "request_type": "server_status",
                "client_id": i,
                "timestamp": time.time()
            })

            if status_success:
                logger.info(f"✅ 客户端{i} 状态查询发送成功")

            await asyncio.sleep(0.5)  # 间隔发送

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
                data="📢 API-Server Version系统广播：所有客户端请注意！"
            ),
            message_dim=MessageDim(api_key="server", platform="server")
        )

        results = await self.server.broadcast_message(broadcast_message)
        success_count = sum(results.values())
        logger.info(f"📡 广播完成: {success_count}/{len(results)} 客户端成功接收")

    def print_test_results(self):
        """打印测试结果"""
        elapsed_time = time.time() - self.test_results["start_time"]

        logger.info("=" * 50)
        logger.info("🎉 API-Server Version测试完成!")
        logger.info("=" * 50)
        logger.info(f"⏱️  运行时间: {elapsed_time:.2f}秒")
        logger.info(f"🔗 连接客户端数: {self.test_results['clients_connected']}")
        logger.info(f"📨 收到消息数: {self.test_results['messages_received']}")
        logger.info(f"🔧 收到自定义消息: {self.test_results['custom_messages_received']}")
        logger.info(f"📤 发送消息数: {self.test_results['messages_sent']}")
        logger.info(f"❌ 错误数: {self.test_results['errors']}")
        logger.info("=" * 50)

        if self.test_results["errors"] == 0:
            logger.info("✅ 所有测试通过，API-Server Version运行正常！")
        else:
            logger.warning(f"⚠️  发现 {self.test_results['errors']} 个错误，请检查日志")

    async def run_tests(self):
        """运行所有测试"""
        logger.info("🚀 API-Server Version完整测试开始")

        try:
            # 创建服务器
            await self.create_server()
            await self.server.start()
            logger.info(f"✅ API-Server Version服务器已启动在 ws://localhost:18070/ws")

            # 等待服务器启动
            await asyncio.sleep(1)

            # 创建并启动客户端
            logger.info("🔗 创建 3 个客户端...")
            self.clients = await self.create_clients()

            for client in self.clients:
                await client.start()

            # 连接客户端
            for i, client in enumerate(self.clients, 1):
                connected = await client.connect()
                await asyncio.sleep(0.5)  # 间隔连接

            # 等待连接完成
            await asyncio.sleep(2)

            # 运行测试
            await self.test_standard_messaging()
            await asyncio.sleep(2)

            await self.test_server_to_client_messaging()
            await asyncio.sleep(2)

            await self.test_custom_messaging()
            await asyncio.sleep(2)

            await self.test_server_broadcast()
            await asyncio.sleep(2)

        except Exception as e:
            logger.error(f"❌ 测试运行错误: {e}")
            self.test_results["errors"] += 1

        finally:
            # 清理资源
            await self.cleanup()

    async def cleanup(self):
        """清理资源"""
        logger.info("🧹 清理资源...")

        # 停止客户端
        for i, client in enumerate(self.clients, 1):
            logger.info(f"🔄 正在停止客户端{i}...")
            try:
                await client.disconnect()
                await client.stop()
                logger.info(f"✅ 客户端{i} 已优雅停止")
            except Exception as e:
                logger.error(f"❌ 客户端{i}停止时出错: {e}")

        # 停止服务器
        logger.info("🔄 正在停止服务器...")
        try:
            await self.server.stop()
            logger.info("✅ 服务器已优雅停止")
        except Exception as e:
            logger.error(f"❌ 服务器停止时出错: {e}")

        logger.info("🎉 所有资源已优雅清理完成")


async def main():
    """主函数"""
    # 设置超时机制
    try:
        # 创建测试器
        tester = APIServerTester()

        # 使用asyncio.wait_for设置30秒超时
        await asyncio.wait_for(tester.run_tests(), timeout=30.0)

        # 打印测试结果
        tester.print_test_results()

    except asyncio.TimeoutError:
        logger.warning("⏰ 测试超时，强制退出")
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        logger.error(f"   Traceback: {traceback.format_exc()}")
    finally:
        logger.info("🏁 测试程序退出")


if __name__ == "__main__":
    print("🚀 开始API-Server Version网络驱动器模式测试...")
    asyncio.run(main())