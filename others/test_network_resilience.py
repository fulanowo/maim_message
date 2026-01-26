"""
网络弹性测试脚本 (Network Resilience Test)

测试目标：
1. 验证服务器在客户端异常断开（无Reset信号/无Close帧）时的处理能力
2. 验证客户端在服务器异常断开时的重连机制
"""

import sys
import os
import asyncio
import logging
import time
import socket
from typing import Dict, Any

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

import websockets
from src.maim_message.server_ws_api import WebSocketServer
from src.maim_message.client_ws_api import WebSocketClient
from src.maim_message.ws_config import create_server_config, create_client_config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# 抑制无关日志
logging.getLogger("websockets").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)


class NetworkResilienceTester:
    def __init__(self):
        self.server = None
        self.clients = []
        self.test_port = 18081  # 使用不同于主测试的端口
        self.abrupt_disconnect_detected = False
        self.reconnect_success = False
        self.connected_clients_count = 0

    async def _setup_server(self):
        """启动测试服务器"""
        config = create_server_config(
            host="localhost", port=self.test_port, path="/ws", enable_stats=True
        )

        # 简单的认证和消息处理
        config.on_auth = self._mock_auth
        config.on_message = self._mock_on_message

        # 监控连接数变化
        original_stats_callback = config.stats_callback

        # 我们不能直接hook on_connect/disconnect因为它们是内部的，
        # 但我们可以通过stats或者周期性检查来验证

        self.server = WebSocketServer(config)
        await self.server.start()
        logger.info(f"✅ 服务器启动在端口 {self.test_port}")

    async def _mock_auth(self, metadata):
        return True

    async def _mock_on_message(self, message, metadata):
        # 简单的回显
        return True

    async def test_server_resilience_to_abrupt_disconnect(self):
        """场景1: 测试服务器处理客户端强制断开(无Close帧)的能力"""
        logger.info("\n🧪 开始测试: 服务器应对客户端强制断开")

        if not self.server:
            await self._setup_server()

        # 1. 建立一个"杀手"客户端 - 连接后直接关闭底层socket
        uri = f"ws://localhost:{self.test_port}/ws"
        logger.info("   启动 KillerClient...")

        try:
            # 手动建立连接以便获取socket控制权
            async with websockets.connect(uri, max_size=104_857_600) as ws:
                logger.info("   KillerClient 已连接")

                # 发送一条消息确保连接活跃
                await ws.send("Hello before kill")
                logger.info("   KillerClient 发送了消息")

                await asyncio.sleep(0.5)

                # 检查服务器连接数 - 使用 'current_connections' 或 'network'->'active_connections'
                stats = self.server.get_stats()
                server_conns = stats.get("current_connections", 0)
                logger.info(f"   当前服务器连接数: {server_conns} (预期: >=1)")
                if server_conns < 1:
                    logger.error("❌ 测试前置条件失败: 服务器未记录连接")
                    return False

                logger.info("   🔪 KillerClient 正在强制关闭 socket (模拟断电/断网)...")
                # 强制关闭底层 transport，不发送 websocket close frame
                ws.transport.close()
                # 或者更彻底地: ws.transport._sock.close() if available

        except Exception as e:
            # 预期会发生异常，因为我们粗暴地关闭了连接
            logger.info(f"   (预期内) KillerClient 发生异常: {e}")

        # 2. 验证服务器状态
        logger.info("   ⏳ 等待服务器检测断开 (2秒)...")
        await asyncio.sleep(2)

        final_conns = self.server.get_stats().get("current_connections", 0)
        logger.info(f"   当前服务器连接数: {final_conns}")

        if final_conns == 0:
            logger.info("✅ 成功: 服务器正确检测并清理了异常断开的连接")
            return True
        else:
            logger.error(f"❌ 失败: 服务器仍保留着僵尸连接 (连接数: {final_conns})")
            return False

    async def test_client_reconnect_on_server_failure(self):
        """场景2: 测试客户端在服务器重启/断开时的重连能力"""
        logger.info("\n🧪 开始测试: 客户端断线重连")

        if not self.server:
            await self._setup_server()

        # 1. 启动正常客户端
        client_config = create_client_config(
            url=f"ws://localhost:{self.test_port}/ws",
            api_key="resilient_client",
            platform="test",
        )
        # 启用自动重连
        client_config.auto_reconnect = True
        client_config.reconnect_interval = 1  # 快速重连以便测试

        client = WebSocketClient(client_config)

        # 追踪连接状态
        reconnect_event = asyncio.Event()

        # Hook connect event handler to monitor reconnection
        original_handle_connect = client._handle_connect_event

        connect_count = 0

        async def monitored_handle_connect(event):
            nonlocal connect_count
            connect_count += 1
            logger.info(f"   客户端捕捉到连接事件 #{connect_count}")
            await original_handle_connect(event)
            reconnect_event.set()

        client._handle_connect_event = monitored_handle_connect

        await client.start()

        # 显式发起首次连接
        logger.info("   发起首次连接...")
        await client.connect()

        # 等待首次连接
        logger.info("   等待客户端首次连接...")
        await asyncio.sleep(2)
        if not client.is_connected():
            logger.error("❌ 客户端首次连接失败")
            await client.stop()
            return False

        logger.info("✅ 客户端首次连接成功")
        reconnect_event.clear()  # 重置事件

        # 2. 强制停止服务器 (模拟服务器崩溃/重启)
        logger.info("   💣 强制停止服务器...")
        await self.server.stop()
        self.server = None

        logger.info("   等待客户端检测到断开...")
        await asyncio.sleep(2)

        if client.is_connected():
            logger.warning("⚠️ 客户端仍认为自己已连接 (可能处于各种超时中)")

        # 3. 重启服务器
        logger.info("   🔄 重启服务器...")
        await self._setup_server()

        # 4. 等待客户端重连
        logger.info("   ⏳ 等待客户端重连 (最多5秒)...")
        try:
            await asyncio.wait_for(reconnect_event.wait(), timeout=5.0)
            logger.info("✅ 检测到客户端重连成功!")

            # 双重确认
            await asyncio.sleep(1)
            if client.is_connected():
                logger.info("✅ 客户端状态确认: 已连接")
                await client.stop()
                return True
            else:
                logger.error("❌ 客户端虽有连接动作但最终状态未连接")
                await client.stop()
                return False

        except asyncio.TimeoutError:
            logger.error("❌ 客户端未在规定时间内重连")
            await client.stop()
            return False

    async def run(self):
        try:
            res1 = await self.test_server_resilience_to_abrupt_disconnect()

            # 清理之前的服务器实例，确保环境干净
            if self.server:
                await self.server.stop()
                self.server = None

            # 稍作等待
            await asyncio.sleep(1)

            res2 = await self.test_client_reconnect_on_server_failure()

            logger.info("\n" + "=" * 30)
            if res1 and res2:
                logger.info("🎉 所有网络弹性测试通过!")
                logger.info("   1. 服务器由于异常断开处理: 通过")
                logger.info("   2. 客户端断线重连: 通过")
            else:
                logger.error("❌ 部分测试失败")
                if not res1:
                    logger.error("   - 服务器异常断开处理失败")
                if not res2:
                    logger.error("   - 客户端重连失败")
            logger.info("=" * 30)

        finally:
            if self.server:
                await self.server.stop()
            for client in self.clients:
                await client.stop()


if __name__ == "__main__":
    tester = NetworkResilienceTester()
    asyncio.run(tester.run())
