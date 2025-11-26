"""
测试服务器发送消息功能的简化版本
"""

import sys
import os
import asyncio
import logging
import time

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from src.maim_message.server_ws_api import WebSocketServer
from src.maim_message.client_ws_api import WebSocketClient
from src.maim_message.api_message_base import (
    APIMessageBase, BaseMessageInfo, Seg, MessageDim
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ServerSendTester:
    def __init__(self):
        self.server = None
        self.client = None
        self.received_messages = []

    async def server_auth_handler(self, auth_data):
        """服务器认证处理器"""
        api_key = auth_data.get("api_key", "")
        logger.info(f"🔐 服务器认证: {api_key}")
        return True

    async def server_extract_user_handler(self, auth_data):
        """服务器用户提取处理器"""
        api_key = auth_data.get("api_key", "")
        platform = auth_data.get("platform", "unknown")

        # 用户ID映射
        user_mapping = {
            "test_user_001": "user_wechat_001",
            "test_user_002": "user_qq_002",
            "test_user_003": "user_telegram_003"
        }

        user_id = user_mapping.get(api_key, f"unknown_user_{api_key}")
        logger.info(f"👤 用户映射: {api_key} -> {user_id} (平台: {platform})")
        return user_id

    async def server_message_handler(self, message, metadata):
        """服务器消息处理器"""
        logger.info(f"🔥 服务器收到消息: {message.message_segment.data}")
        self.received_messages.append(message.message_segment.data)
        return True

    async def client_message_handler(self, message, metadata):
        """客户端消息处理器"""
        content = message.message_segment.data
        logger.info(f"📥 客户端收到服务器消息: {content}")
        self.received_messages.append(f"客户端收到: {content}")

    async def run_test(self):
        """运行测试"""
        try:
            # 创建服务器
            logger.info("🚀 创建服务器...")
            from src.maim_message.ws_config import ServerConfig

            server_config = ServerConfig(
                host="localhost",
                port=18080,
                on_auth=self.server_auth_handler,
                on_auth_extract_user=self.server_extract_user_handler,
                on_message=self.server_message_handler
            )

            self.server = WebSocketServer(server_config)
            await self.server.start()
            logger.info("✅ 服务器已启动")

            # 等待服务器完全启动
            await asyncio.sleep(2)

            # 创建客户端
            logger.info("🔧 创建客户端...")
            from src.maim_message.ws_config import ClientConfig

            client_config = ClientConfig(
                url="ws://localhost:18080/ws",
                api_key="test_user_001",  # 使用测试API Key
                platform="wechat",
                on_message=self.client_message_handler
            )

            self.client = WebSocketClient(client_config)
            await self.client.start()
            logger.info("✅ 客户端已启动")

            # 连接客户端
            logger.info("🔗 连接客户端...")
            connected = await self.client.connect()
            logger.info(f"连接结果: {connected}")

            # 等待连接建立
            await asyncio.sleep(3)

            # 检查连接状态
            logger.info(f"客户端连接状态: {self.client.is_connected()}")
            logger.info(f"服务器连接数: {self.server.get_connection_count()}")

            # 测试1: 客户端向服务器发送消息
            logger.info("📤 测试1: 客户端向服务器发送消息...")
            client_message = APIMessageBase(
                message_info=BaseMessageInfo(
                    platform="wechat",
                    message_id=f"client_{int(time.time() * 1000)}",
                    time=time.time()
                ),
                message_segment=Seg(type="text", data="客户端发送测试消息"),
                message_dim=MessageDim(api_key="test_user_001", platform="wechat")
            )

            send_result = await self.client.send_message(client_message)
            logger.info(f"客户端发送结果: {send_result}")
            await asyncio.sleep(2)

            # 测试2: 服务器向客户端发送消息
            logger.info("📤 测试2: 服务器向客户端发送消息...")
            server_message = APIMessageBase(
                message_info=BaseMessageInfo(
                    platform="wechat",  # 使用客户端连接的平台
                    message_id=f"server_{int(time.time() * 1000)}",
                    time=time.time()
                ),
                message_segment=Seg(type="text", data="服务器发送测试消息"),
                message_dim=MessageDim(api_key="test_user_001", platform="wechat")  # 使用客户端连接的平台
            )

            # 检查服务器状态
            server_stats = self.server.get_stats()
            logger.info(f"服务器统计: {server_stats}")

            send_results = await self.server.send_message(server_message)
            logger.info(f"服务器发送结果: {send_results}")

            success_count = sum(send_results.values()) if send_results else 0
            logger.info(f"服务器发送成功连接数: {success_count}")

            # 等待消息处理
            await asyncio.sleep(3)

            # 检查收到的消息
            logger.info(f"收到的消息数量: {len(self.received_messages)}")
            for i, msg in enumerate(self.received_messages, 1):
                logger.info(f"  消息{i}: {msg}")

        except Exception as e:
            logger.error(f"❌ 测试错误: {e}")
            import traceback
            logger.error(f"错误详情: {traceback.format_exc()}")

        finally:
            # 清理资源
            logger.info("🧹 清理资源...")
            if self.client:
                await self.client.stop()
            if self.server:
                await self.server.stop()
            logger.info("✅ 测试完成")


async def main():
    """主函数"""
    tester = ServerSendTester()
    await tester.run_test()


if __name__ == "__main__":
    asyncio.run(main())