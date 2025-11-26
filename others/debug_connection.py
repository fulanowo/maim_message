"""
连接问题调试脚本
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
from src.maim_message.ws_config import create_server_config, create_client_config

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ConnectionDebugger:
    def __init__(self):
        self.server = None
        self.client = None

    async def server_message_handler(self, message, metadata):
        """服务器消息处理器"""
        logger.info(f"🔥 服务器收到消息: {message.message_segment.data}")
        return True

    async def server_auth_handler(self, api_key):
        """服务器认证处理器"""
        logger.info(f"🔐 服务器认证: {api_key}")
        return True

    async def server_extract_user_handler(self, api_key):
        """服务器用户提取处理器"""
        logger.info(f"👤 用户提取: {api_key}")
        return f"user_{api_key}"

    async def client_message_handler(self, message, metadata):
        """客户端消息处理器"""
        logger.info(f"🔥 客户端收到消息: {message.message_segment.data}")

    async def run_debug_test(self):
        """运行连接调试测试"""
        try:
            # 创建服务器
            logger.info("🚀 创建服务器...")
            server_config = create_server_config(
                host="localhost",
                port=18080,
                on_auth=self.server_auth_handler,  # 异步认证回调
                on_auth_extract_user=self.server_extract_user_handler,  # 异步用户提取回调
                on_message=self.server_message_handler
            )

            self.server = WebSocketServer(server_config)
            await self.server.start()
            logger.info("✅ 服务器已启动")

            # 等待服务器完全启动
            await asyncio.sleep(2)

            # 创建客户端
            logger.info("🔧 创建客户端...")
            client_config = create_client_config(
                url="ws://localhost:18080/ws",
                api_key="test_debug_001",
                platform="debug",
                on_message=self.client_message_handler
            )

            self.client = WebSocketClient(client_config)
            await self.client.start()
            logger.info("✅ 客户端已启动")

            # 连接客户端
            logger.info("🔗 连接客户端...")
            connected = await self.client.connect()
            logger.info(f"连接结果: {connected}")

            # 检查连接状态
            logger.info(f"客户端连接状态: {self.client.is_connected()}")
            logger.info(f"客户端UUID: {self.client.get_connection_uuid()}")
            logger.info(f"客户端最后错误: {self.client.get_last_error()}")

            # 获取服务器连接状态
            logger.info(f"服务器连接数: {self.server.get_connection_count()}")
            server_stats = self.server.get_stats()
            logger.info(f"服务器统计: {server_stats}")

            # 等待连接事件处理
            await asyncio.sleep(3)

            # 再次检查连接状态
            logger.info(f"等待3秒后客户端状态: {self.client.is_connected()}")

            if self.client.is_connected():
                # 测试发送消息
                logger.info("📤 尝试发送测试消息...")
                from src.maim_message.api_message_base import (
                    APIMessageBase, BaseMessageInfo, Seg, MessageDim
                )

                message = APIMessageBase(
                    message_info=BaseMessageInfo(
                        platform="debug",
                        message_id=f"debug_{int(time.time() * 1000)}",
                        time=time.time()
                    ),
                    message_segment=Seg(type="text", data="调试连接测试消息"),
                    message_dim=MessageDim(api_key="test_debug_001", platform="debug")
                )

                send_result = await self.client.send_message(message)
                logger.info(f"消息发送结果: {send_result}")

                # 等待消息处理
                await asyncio.sleep(2)

            # 检查服务器端看到的连接
            logger.info(f"最终服务器连接数: {self.server.get_connection_count()}")
            final_stats = self.server.get_stats()
            logger.info(f"最终服务器统计: {final_stats}")

        except Exception as e:
            logger.error(f"❌ 调试测试错误: {e}")
            import traceback
            logger.error(f"错误详情: {traceback.format_exc()}")

        finally:
            # 清理资源
            logger.info("🧹 清理资源...")
            if self.client:
                await self.client.stop()
            if self.server:
                await self.server.stop()
            logger.info("✅ 调试测试完成")


async def main():
    """主函数"""
    debugger = ConnectionDebugger()
    await debugger.run_debug_test()


if __name__ == "__main__":
    asyncio.run(main())