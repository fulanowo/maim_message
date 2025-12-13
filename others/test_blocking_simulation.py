
"""
逻辑阻塞模拟测试 (Blocking Simulation Test)

测试目标：
1. 验证客户端主线程被阻塞住时，后台的 ClientNetworkDriver 是否依然能正常维护心跳和连接
2. 验证服务器主循环被阻塞时，客户端的超时检测机制
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
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# 开启 websockets 日志用于调试
logging.getLogger('websockets').setLevel(logging.DEBUG)
logging.getLogger('asyncio').setLevel(logging.WARNING)

class BlockingSimulator:
    def __init__(self):
        self.server = None
        self.test_port = 18082  # 使用专用端口
        self.clients = []

    async def _setup_server(self):
        """启动测试服务器"""
        config = create_server_config(
            host="localhost",
            port=self.test_port,
            path="/ws",
            enable_stats=True
        )
        config.on_auth = self._mock_auth
        
        config.on_auth = self._mock_auth
        
        # 注册自定义指令处理器
        config.register_custom_handler("command", self._mock_command_handler)
        
        self.server = WebSocketServer(config)
        await self.server.start()
        logger.info(f"✅ 服务器启动在端口 {self.test_port}")

    async def _mock_auth(self, metadata):
        return True

    async def _mock_command_handler(self, message_data, metadata):
        logging.info(f"收到指令: {message_data}")
        if isinstance(message_data, dict):
            # 注意: message_data 是完整的消息包，真正的数据在 'payload' 字段中
            inner_payload = message_data.get("payload", {})
            if isinstance(inner_payload, dict) and inner_payload.get("command") == "block_server":
                duration = inner_payload.get("duration", 2)
                logger.warning(f"⚠️ 服务器收到阻塞指令，将同步阻塞 {duration} 秒...")
                # 危险动动作：同步 Sleep 阻塞事件循环
                time.sleep(duration)
                logger.info("✅ 服务器阻塞结束")

    async def test_client_main_loop_blocked(self):
        """场景3: 验证客户端主逻辑(用户代码)被阻塞时，底层连接是否存活"""
        logger.info("\n🧪 开始测试: 客户端主线程阻塞对连接的影响")
        
        if not self.server:
            await self._setup_server()

        # 1. 启动客户端，并设置较短的心跳间隔以便观察
        client_config = create_client_config(
            url=f"ws://localhost:{self.test_port}/ws",
            api_key="blocked_client",
            platform="test",
            ping_interval=5,
            ping_timeout=5
        )
        
        client = WebSocketClient(client_config)
        await client.start()
        await client.connect()
        await asyncio.sleep(1) # 等待连接稳定

        if not client.is_connected():
            logger.error("❌ 客户端启动失败")
            return False

        logger.info("✅ 客户端已连接，将在主线程模拟 5 秒同步阻塞...")
        logger.info("   预期: 由于 ClientNetworkDriver 运行在独立线程/独立循环中，心跳应该照常发送，连接保持活跃")

        # 2. 模拟长时间同步阻塞 (模拟用户写了个死循环或者 heavy computation)
        # 注意：这里的阻塞实际上阻塞的是当前的 asyncio loop
        # 如果 WebSocketClient 的 network_driver 真的是运行在独立线程，那么它不受影响
        start_time = time.time()
        time.sleep(5) 
        end_time = time.time()
        
        logger.info(f"   主线程苏醒 (阻塞时长: {end_time - start_time:.2f}s)")

        # 3. 验证连接状态
        # 立即检查连接状态。如果驱动器在后台正常工作，连接应该还是 True。
        # 如果驱动器也被阻塞了（比如没正确使用线程），那么心跳可能丢失导致断连（取决于服务器是否踢人）
        # 或者仅仅是状态没更新。
        
        # 为了验证"活跃"，我们可以让客户端立即发个消息
        try:
            logger.info("   尝试发送消息验证连接...")
            success = await client.send_custom_message("ping_after_block", {"content": "I am back"})
            if success:
                logger.info("✅ 消息发送成功，连接依然活跃")
                
                # 双重检查 API 状态
                if client.is_connected():
                    logger.info("✅ is_connected() 返回 True")
                    await client.stop()
                    return True
                else:
                    logger.error("❌ 消息发送成功但 is_connected() 返回 False")
                    await client.stop()
                    return False
            else:
                logger.error("❌ 消息发送失败，连接可能已断开")
                await client.stop()
                return False
        except Exception as e:
            logger.error(f"❌ 发送消息异常: {e}")
            await client.stop()
            return False

    async def test_server_loop_blocked(self):
        """场景4: 服务器主循环被阻塞"""
        logger.info("\n🧪 开始测试: 服务器主循环阻塞")
        
        if not self.server:
            await self._setup_server()

        # 1. 客户端连接
        client_config = create_client_config(
            url=f"ws://localhost:{self.test_port}/ws",
            api_key="watcher_client",
            platform="test",
            # 设置极端的超时参数以便快速检测死掉的服务器
            ping_interval=1,
            ping_timeout=2
        )
        client = WebSocketClient(client_config)
        await client.start()
        await client.connect()
        await asyncio.sleep(1)

        # 2. 发送指令让服务器自我阻塞
        logger.info("   发送指令让服务器同步阻塞 4 秒...")
        # 我们的超时只有2秒，所以预期客户端会检测到心跳丢失并断开
        
        # 这是一个"自杀式"请求，因为服务器处理它时就会卡住
        # 增加阻塞时间到 8秒，确保必定触发 ping超时 (2秒)
        await client.send_custom_message("command", {
            "command": "block_server", 
            "duration": 8
        })

        # 3. 观察客户端反应
        logger.info("   等待客户端检测超时 (预期应该不仅没收到ACK，心跳也会失败)...")
        
        # 等待服务器阻塞的时间 + 一点缓冲
        wait_start = time.time()
        
        # 轮询检查连接状态
        disconnected_by_timeout = False
        for i in range(100): # 10秒内
            await asyncio.sleep(0.1)
            is_conn = client.is_connected()
            if i % 10 == 0:
                logger.info(f"   [Loop {i}] client.is_connected() = {is_conn}")
            
            if not is_conn:
                logger.info(f"✅ 客户端检测到断开 (耗时: {time.time() - wait_start:.2f}s)")
                disconnected_by_timeout = True
                break
        
        # 等待服务器醒来以能够优雅退出
        await asyncio.sleep(2)
        
        await client.stop()
        
        if disconnected_by_timeout:
            logger.info("✅ 测试通过: 客户端正确检测到了因为服务器阻塞导致的心跳超时")
            return True
        else:
            logger.error("❌ 测试失败: 尽管服务器阻塞了，客户端仍认为连接活跃 (可能超时设置未生效或底层有缓冲)")
            return False

    async def run(self):
        try:
            res1 = await self.test_client_main_loop_blocked()
            
            # 重置环境
            if self.server:
                await self.server.stop()
                self.server = None
            await asyncio.sleep(1)

            res2 = await self.test_server_loop_blocked()
            
            logger.info("\n" + "="*30)
            if res1 and res2:
                logger.info("🎉 所有阻塞模拟测试通过!")
                logger.info("   1. 客户端主线程阻塞(后台保活): 通过")
                logger.info("   2. 服务器阻塞(客户端超时检测): 通过")
            else:
                logger.error("❌ 部分测试失败")
            logger.info("="*30)
            
        finally:
            if self.server:
                await self.server.stop()
            for client in self.clients:
                await client.stop()

if __name__ == "__main__":
    sim = BlockingSimulator()
    asyncio.run(sim.run())
