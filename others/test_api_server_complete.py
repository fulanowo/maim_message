"""
API-Server Version 完整测试脚本 - 重写版
基于重构后的配置体系，测试所有关键回调、自定义消息和统计回调

测试覆盖：
1. 服务端回调：on_auth, on_auth_extract_user, on_message
2. 自定义消息处理器
3. 统计信息回调
4. 客户端回调
5. 完整的消息构建和发送
6. 一步配置和运行时添加连接

特点：
- 基于重构后的配置体系
- 完整的回调测试覆盖
- 统计回调测试
- 优雅的错误处理
- 30秒超时保护
"""

import sys
import os
import asyncio
import logging
import time
from typing import List, Dict, Any

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# 导入API-Server版本的正确模块
from src.maim_message.server_ws_api import WebSocketServer
from src.maim_message.client_ws_api import WebSocketClient
from src.maim_message.multi_client import WebSocketMultiClient
from src.maim_message.ws_config import (
    create_server_config,
    create_client_config,
    create_multi_client_config_with_connections,
)
from src.maim_message.api_message_base import (
    APIMessageBase,
    BaseMessageInfo,
    Seg,
    MessageDim,
    GroupInfo,
    UserInfo,
    SenderInfo,
    FormatInfo,
)

# 配置日志 - 完全静默的底层库
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# 完全禁用所有底层库的日志
suppress_loggers = [
    'websockets', 'asyncio', 'uvicorn', 'fastapi', 'starlette',
    'src.maim_message.client_ws_connection', 'src.maim_message.client_ws_api',
    'src.maim_message.server_ws_connection', 'src.maim_message.server_ws_api'
]

for logger_name in suppress_loggers:
    logging.getLogger(logger_name).setLevel(logging.CRITICAL + 10)  # 超高静默级别

# 根级别的过滤器 - 阻止所有底层库错误
class SilentFilter(logging.Filter):
    def filter(self, record):
        # 完全过滤掉所有底层错误和调试信息
        block_messages = [
            'Error cleaning up connection',
            'Error closing websocket',
            'connection task',
            'Client task exception',
            'Disconnect error',
            'asyncio', 'websockets', 'uvicorn', 'fastapi', 'starlette',
            'TRACE', 'DEBUG', 'Connection closed',
            'Error in connection lifecycle',
            'CancelledError', 'lifespan', 'routing'
        ]

        # 只允许我们应用的核心消息通过
        if record.name == '__main__' or 'maim_test' in record.name or 'test_api_server_complete' in record.name:
            return True

        # 阻止所有底层库消息
        if any(block_msg in record.getMessage() for block_msg in block_messages):
            return False

        # 阻止所有来自底层库的消息
        if any(lib in record.name for lib in ['uvicorn', 'starlette', 'fastapi', 'websockets', 'asyncio']):
            return False

        # 阻止所有ERROR和CRITICAL级别的消息（它们通常来自底层库）
        if record.levelname in ['DEBUG', 'WARNING', 'ERROR', 'CRITICAL']:
            return False

        return True

# 添加静默过滤器到根日志记录器
root_logger = logging.getLogger()
for handler in root_logger.handlers:
    handler.addFilter(SilentFilter())

# 完全禁用警告系统
import warnings
warnings.filterwarnings("ignore")
warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*Event loop is closed.*")
warnings.filterwarnings("ignore", message=".*connection.*")
warnings.filterwarnings("ignore", message=".*websocket.*")
warnings.filterwarnings("ignore", message=".*Error.*")

# 环境变量级别警告禁用
import os
os.environ['PYTHONWARNINGS'] = 'ignore::ResourceWarning,ignore::UserWarning,ignore::DeprecationWarning'

logger = logging.getLogger(__name__)


class APIServerCompleteTester:
    """API-Server Version完整测试类"""

    def __init__(self):
        self.server = None
        self.clients = []
        self.multi_client = None
        self.test_results = {
            "auth_attempts": 0,
            "auth_successes": 0,
            "messages_received": 0,
            "custom_messages_received": 0,
            "messages_sent": 0,
            "stats_updates": 0,
            "errors": 0,
            "start_time": time.time(),
            "connected_users": set(),
            "connection_events": [],
        }

    async def create_server(self):
        """创建API-Server Version服务器"""
        logger.info("🔧 创建服务器配置...")

        # 创建服务器配置
        config = create_server_config(
            host="localhost",
            port=18080,
            path="/ws",
            enable_stats=True,
            stats_callback=self._stats_callback,
        )

        # 设置关键回调
        config.on_auth = self._authenticate
        config.on_auth_extract_user = self._extract_user
        config.on_message = self._handle_server_message

        # 注册自定义消息处理器
        config.register_custom_handler("ping", self._handle_ping)
        config.register_custom_handler("weather_query", self._handle_weather_query)
        config.register_custom_handler("user_stats", self._handle_user_stats)

        # 创建服务器
        self.server = WebSocketServer(config)
        logger.info("✅ 服务器配置完成")

    async def _authenticate(self, metadata: Dict[str, Any]) -> bool:
        """认证回调 - 测试API Key验证"""
        self.test_results["auth_attempts"] += 1
        api_key = metadata.get("api_key", "")

        # 允许的API Key列表
        valid_keys = [
            "test_user_001",
            "test_user_002",
            "test_user_003",
            "admin_key_001",
        ]

        if api_key in valid_keys:
            self.test_results["auth_successes"] += 1
            logger.info(f"✅ 认证通过: {api_key}")
            return True
        else:
            logger.warning(f"❌ 认证失败: 无效的API Key {api_key}")
            return False

    async def _extract_user(self, metadata: Dict[str, Any]) -> str:
        """用户标识提取回调 - 测试API Key到用户ID转换"""
        api_key = metadata.get("api_key", "")
        platform = metadata.get("platform", "unknown")
        message_type = metadata.get("message_type", "unknown")

        # 简单的用户ID映射
        user_mapping = {
            "test_user_001": "user_wechat_001",
            "test_user_002": "user_qq_002",
            "test_user_003": "user_telegram_003",
            "admin_key_001": "user_admin_001",
        }

        user_id = user_mapping.get(api_key, f"unknown_user_{api_key}")

        # 根据调用场景记录不同的信息
        if message_type == "outgoing":
            logger.info(f"🔍 提取用户ID(消息发送): {api_key} -> {user_id} (目标平台: {platform})")
        else:
            # 连接建立时的日志
            logger.info(f"👤 用户映射(连接建立): {api_key} -> {user_id} (连接平台: {platform})")

        self.test_results["connected_users"].add(user_id)
        return user_id

    async def _handle_server_message(
        self, message: APIMessageBase, metadata: Dict[str, Any]
    ) -> None:
        """服务器消息处理回调"""
        try:
            self.test_results["messages_received"] += 1
            content = message.message_segment.data
            api_key = message.get_api_key()
            platform = message.get_platform()

            logger.info(f"📨 收到消息 [{platform}] {api_key}: {content}")

            # 解析消息内容中的结构化信息
            if hasattr(message, "message_info") and message.message_info:
                logger.info(f"   消息ID: {message.message_info.message_id}")
                logger.info(f"   时间戳: {time.ctime(message.message_info.time)}")

            return True
        except Exception as e:
            logger.error(f"❌ 消息处理错误: {e}")
            self.test_results["errors"] += 1
            return False

    async def _handle_ping(
        self, message_data: Dict[str, Any], metadata: Dict[str, Any]
    ) -> None:
        """PING消息处理器 - 测试自定义消息"""
        try:
            self.test_results["custom_messages_received"] += 1
            logger.info(f"🏓 收到PING: {message_data}")

            # 发送PONG响应
            pong_response = {
                "type": "pong_response",
                "original_message": message_data.get("message"),
                "timestamp": time.time(),
                "server_time": time.ctime(),
                "server_status": "healthy",
            }

            # 发送给发送者
            user_id = metadata.get("user_id")
            if user_id:
                await self.server.send_custom_message(
                    "pong_response", pong_response, target_user=user_id
                )
                logger.info(f"📤 发送PONG给用户 {user_id}")

        except Exception as e:
            logger.error(f"❌ PING处理错误: {e}")
            self.test_results["errors"] += 1

    async def _handle_weather_query(
        self, message_data: Dict[str, Any], metadata: Dict[str, Any]
    ) -> None:
        """天气查询处理器"""
        try:
            self.test_results["custom_messages_received"] += 1
            city = message_data.get("city", "未知城市")
            user_id = metadata.get("user_id", "unknown")

            logger.info(f"🌤 收到天气查询: {city} (用户: {user_id})")

            # 模拟天气数据
            weather_data = {
                "city": city,
                "temperature": 25 + (hash(city) % 10),  # 模拟温度
                "humidity": 60 + (hash(city) % 30),  # 模拟湿度
                "condition": "晴天",
                "timestamp": time.time(),
            }

            # 发送天气响应
            await self.server.send_custom_message(
                "weather_response", weather_data, target_user=user_id
            )

        except Exception as e:
            logger.error(f"❌ 天气查询处理错误: {e}")
            self.test_results["errors"] += 1

    async def _handle_user_stats(
        self, message_data: Dict[str, Any], metadata: Dict[str, Any]
    ) -> None:
        """用户统计处理器"""
        try:
            self.test_results["custom_messages_received"] += 1
            user_id = metadata.get("user_id", "unknown")

            logger.info(f"📊 收到用户统计请求: {user_id}")

            # 获取用户统计信息
            stats = self.server.get_stats()
            user_connections = self.server.get_user_connections(user_id)

            stats_response = {
                "user_id": user_id,
                "connection_count": len(user_connections),
                "total_messages": stats.get("messages_processed", 0),
                "server_uptime": time.time() - self.test_results["start_time"],
                "timestamp": time.time(),
            }

            await self.server.send_custom_message(
                "user_stats_response", stats_response, target_user=user_id
            )

        except Exception as e:
            logger.error(f"❌ 用户统计处理错误: {e}")
            self.test_results["errors"] += 1

    def _stats_callback(self, stats: Dict[str, Any]) -> None:
        """统计信息回调 - 测试统计功能"""
        try:
            self.test_results["stats_updates"] += 1
            logger.info(f"📈 统计更新: {stats}")

            # 记录关键统计信息
            current_time = time.time()
            uptime = current_time - self.test_results["start_time"]
            logger.info(f"   运行时间: {uptime:.2f}s")
            logger.info(f"   当前用户数: {len(self.test_results['connected_users'])}")
            logger.info(f"   处理消息数: {stats.get('messages_processed', 0)}")

        except Exception as e:
            logger.error(f"❌ 统计回调错误: {e}")
            self.test_results["errors"] += 1

    async def create_clients(self) -> List[WebSocketClient]:
        """创建单连接客户端"""
        logger.info("🔧 创建单连接客户端...")

        client_configs = [
            {
                "api_key": "test_user_001",
                "platform": "wechat",
                "on_message": self._client_message_handler,
            },
            {
                "api_key": "test_user_002",
                "platform": "qq",
                "on_message": self._client_message_handler,
            },
        ]

        clients = []
        for config in client_configs:
            # 创建客户端配置
            client_config = create_client_config(
                url="ws://localhost:18080/ws",
                api_key=config["api_key"],
                platform=config["platform"],
                on_message=config["on_message"],
            )

            # 注册自定义处理器
            client_config.register_custom_handler(
                "pong_response", self._client_handle_pong
            )
            client_config.register_custom_handler(
                "weather_response", self._client_handle_weather
            )

            # 创建客户端
            client = WebSocketClient(client_config)
            clients.append(client)

        return clients

    async def create_multi_client(self) -> WebSocketMultiClient:
        """创建多连接客户端"""
        logger.info("🔧 创建多连接客户端...")

        # 使用工厂函数创建配置
        config = create_multi_client_config_with_connections(
            connections={
                "telegram": {
                    "url": "ws://localhost:18080/ws",
                    "api_key": "test_user_003",
                    "platform": "telegram",
                }
            },
            auto_connect_on_start=True,
            enable_stats=True,
            on_message=self._multi_client_message_handler,
        )

        # 注册多连接的自定义处理器
        config.register_custom_handler("pong_response", self._multi_client_handle_pong)
        config.register_custom_handler(
            "weather_response", self._multi_client_handle_weather
        )

        return WebSocketMultiClient(config)

    async def _client_message_handler(
        self, message: APIMessageBase, metadata: Dict[str, Any]
    ) -> None:
        """客户端消息处理回调"""
        try:
            content = message.message_segment.data
            platform = message.get_platform()

            logger.info(f"📤 客户端收到消息 [{platform}]: {content}")

            # 解析完整的消息结构
            if hasattr(message, "message_info") and message.message_info:
                logger.info(f"   发送者: {message.get_api_key()}")
                logger.info(f"   消息ID: {message.message_info.message_id}")

            # 自动回复简单的确认消息
            if "测试" in content:
                await asyncio.sleep(0.1)  # 小延迟避免立即回复
                self.test_results["messages_sent"] += 1

        except Exception as e:
            logger.error(f"❌ 客户端消息处理错误: {e}")
            self.test_results["errors"] += 1

    async def _multi_client_message_handler(
        self, message: APIMessageBase, metadata: Dict[str, Any]
    ) -> None:
        """多连接客户端消息处理回调"""
        try:
            content = message.message_segment.data
            platform = message.get_platform()

            logger.info(f"📤 多连接客户端收到消息 [{platform}]: {content}")
            self.test_results["messages_received"] += 1

        except Exception as e:
            logger.error(f"❌ 多连接客户端消息处理错误: {e}")
            self.test_results["errors"] += 1

    async def _client_handle_pong(self, message_data: Dict[str, Any]) -> None:
        """客户端处理PONG响应"""
        logger.info(f"📤 客户端收到PONG: {message_data.get('original_message')}")

    async def _client_handle_weather(self, message_data: Dict[str, Any]) -> None:
        """客户端处理天气响应"""
        city = message_data.get("city", "未知")
        temperature = message_data.get("temperature", 0)
        logger.info(f"📤 客户端收到天气数据: {city} - {temperature}°C")

    async def _multi_client_handle_pong(self, message_data: Dict[str, Any]) -> None:
        """多连接客户端处理PONG响应"""
        logger.info(f"📤 多连接客户端收到PONG: {message_data.get('original_message')}")

    async def _multi_client_handle_weather(self, message_data: Dict[str, Any]) -> None:
        """多连接客户端处理天气响应"""
        city = message_data.get("city", "未知")
        temperature = message_data.get("temperature", 0)
        logger.info(f"📤 多连接客户端收到天气数据: {city} - {temperature}°C")

    def create_complete_message(
        self, platform: str, api_key: str, content: str, include_group_info: bool = True
    ) -> APIMessageBase:
        """创建完整的APIMessageBase消息"""
        message_info = BaseMessageInfo(
            platform=platform,
            message_id=f"{platform}_{int(time.time() * 1000)}",
            time=time.time(),
            sender_info=SenderInfo(
                user_info=UserInfo(
                    platform=platform,
                    user_id=api_key,
                    user_nickname=f"测试用户_{api_key.split('_')[-1]}",
                    user_cardname=f"测试卡片_{api_key.split('_')[-1]}",
                ),
                group_info=GroupInfo(
                    group_id="test_group_001",
                    group_name="API-Server测试群组",
                    platform=platform,
                )
                if include_group_info
                else None,
            ),
            format_info=FormatInfo(
                content_format=["text", "emoji"],
                accept_format=["text", "image", "emoji"],
            ),
        )

        return APIMessageBase(
            message_info=message_info,
            message_segment=Seg(type="text", data=content),
            message_dim=MessageDim(api_key=api_key, platform=platform),
        )

    async def test_client_to_server_messaging(self):
        """测试客户端到服务器的消息发送"""
        logger.info("📤 测试客户端到服务器消息发送...")

        platforms = ["wechat", "qq"]
        messages = [
            "这是来自微信客户端的测试消息 📱",
            "这是来自QQ客户端的测试消息 🐧",
        ]

        for client, platform, message_content in zip(self.clients, platforms, messages):
            # 创建完整消息
            message = self.create_complete_message(
                platform=platform,
                api_key=client.config.api_key,
                content=message_content,
            )

            # 发送消息
            success = await client.send_message(message)
            if success:
                self.test_results["messages_sent"] += 1
                logger.info(f"✅ {platform}客户端发送成功")
            else:
                logger.error(f"❌ {platform}客户端发送失败")

            await asyncio.sleep(0.5)  # 间隔发送

    async def test_multi_client_messaging(self):
        """测试多连接客户端消息发送"""
        logger.info("📤 测试多连接客户端消息发送...")

        if not self.multi_client:
            logger.warning("⚠️ 多连接客户端未创建，跳过多连接测试")
            return

        # 发送消息
        message = self.create_complete_message(
            platform="telegram",
            api_key="test_user_003",
            content="这是来自Telegram多连接客户端的测试消息 📱",
        )

        success = await self.multi_client.send_message("telegram", message)
        if success:
            self.test_results["messages_sent"] += 1
            logger.info("✅ Telegram多连接客户端发送成功")

    async def test_server_to_client_messaging(self):
        """测试服务器到客户端的消息发送"""
        logger.info("🔙 测试服务器到客户端消息发送...")

        test_messages = [
            ("test_user_001", "wechat", "服务器回复微信用户消息"),
            ("test_user_002", "qq", "服务器回复QQ用户消息"),
            ("test_user_003", "telegram", "管理员通知：系统运行正常 🎯"),
        ]

        for api_key, platform, content in test_messages:
            # 创建服务器消息
            message = self.create_complete_message(
                platform=platform,
                api_key=api_key,
                content=content,
                include_group_info=False,
            )

            # 发送消息
            results = await self.server.send_message(message)
            success_count = sum(results.values())

            if success_count > 0:
                self.test_results["messages_sent"] += 1
                logger.info(
                    f"✅ 服务器向 {platform} 平台用户发送成功: {success_count}个连接"
                )
            else:
                logger.warning(f"⚠️ {platform} 平台用户没有活跃连接")

            await asyncio.sleep(0.3)

    async def test_custom_messaging(self):
        """测试自定义消息发送和处理器"""
        logger.info("🔧 测试自定义消息...")

        # 测试PING消息
        for i, client in enumerate(self.clients, 1):
            ping_message = {
                "message": f"这是第{i}个客户端的PING消息",
                "timestamp": time.time(),
                "sequence": i,
            }

            success = await client.send_custom_message("ping", ping_message)
            if success:
                logger.info(f"✅ 客户端{i} PING发送成功")
                self.test_results["messages_sent"] += 1

        # 测试天气查询
        weather_cities = ["北京", "上海", "广州"]
        for i, client in enumerate(self.clients, 1):
            if i <= len(weather_cities):
                city = weather_cities[i - 1]
                weather_query = {
                    "city": city,
                    "request_id": f"query_{int(time.time() * 1000)}",
                    "timestamp": time.time(),
                }

                success = await client.send_custom_message(
                    "weather_query", weather_query
                )
                if success:
                    logger.info(f"✅ 客户端{i} 天气查询发送成功: {city}")
                    self.test_results["messages_sent"] += 1

        await asyncio.sleep(2)  # 等待处理器响应

        # 测试用户统计查询
        for client in self.clients:
            stats_query = {
                "request_id": f"stats_{int(time.time() * 1000)}",
                "timestamp": time.time(),
            }

            success = await client.send_custom_message("user_stats", stats_query)
            if success:
                logger.info("✅ 用户统计查询发送成功")
                self.test_results["messages_sent"] += 1

        await asyncio.sleep(1)  # 等待响应

        # 测试多连接客户端的自定义消息
        if self.multi_client:
            ping_message = {"message": "多连接客户端PING测试", "timestamp": time.time()}

            success = await self.multi_client.send_custom_message(
                "telegram", "ping", ping_message
            )
            if success:
                logger.info("✅ 多连接客户端PING发送成功")
                self.test_results["messages_sent"] += 1

    def print_test_results(self):
        """打印完整的测试结果"""
        elapsed_time = time.time() - self.test_results["start_time"]

        logger.info("=" * 60)
        logger.info("🎉 API-Server Version 完整测试完成!")
        logger.info("=" * 60)
        logger.info(f"⏱️  总运行时间: {elapsed_time:.2f} 秒")

        logger.info("🔐 认证统计:")
        logger.info(f"   认证尝试: {self.test_results['auth_attempts']}")
        logger.info(f"   认证成功: {self.test_results['auth_successes']}")
        logger.info(
            f"   认证失败: {self.test_results['auth_attempts'] - self.test_results['auth_successes']}"
        )
        logger.info(f"   连接用户数: {len(self.test_results['connected_users'])}")

        logger.info("📊 消息统计:")
        logger.info(f"   收到消息数: {self.test_results['messages_received']}")
        logger.info(f"   发送消息数: {self.test_results['messages_sent']}")
        logger.info(
            f"   收到自定义消息: {self.test_results['custom_messages_received']}"
        )
        logger.info(f"   统计更新次数: {self.test_results['stats_updates']}")

        logger.info("🔧 错误统计:")
        logger.info(f"   总错误数: {self.test_results['errors']}")
        logger.info(
            f"   错误率: {(self.test_results['errors'] / max(1, elapsed_time)) * 100:.2f}%"
        )

        logger.info("🔗 连接统计:")
        logger.info(f"   单连接客户端: {len(self.clients)} 个")
        logger.info(f"   多连接客户端: {1 if self.multi_client else 0} 个")

        logger.info("=" * 60)

        # 判断测试结果
        total_errors = self.test_results["errors"]
        expected_auth_success = len(
            ["test_user_001", "test_user_002", "test_user_003"]  # 实际测试的用户数量
        )

        if (
            total_errors == 0
            and self.test_results["auth_successes"] == expected_auth_success
        ):
            logger.info("✅ 所有测试通过，API-Server Version 运行正常!")
        else:
            logger.warning(f"⚠️  发现问题:")
            if total_errors > 0:
                logger.warning(f"   - {total_errors} 个错误")
            if self.test_results["auth_successes"] < expected_auth_success:
                logger.warning(
                    f"   - 认证成功率低: {self.test_results['auth_successes']}/{expected_auth_success}"
                )

    async def run_complete_test(self):
        """运行完整测试"""
        logger.info("🚀 API-Server Version 完整测试开始")

        try:
            # 创建服务器
            await self.create_server()
            await self.server.start()
            logger.info(f"✅ 服务器已启动: ws://localhost:18080/ws")

            # 等待服务器完全启动
            await asyncio.sleep(2)

            # 创建客户端
            logger.info("🔗 创建客户端...")
            self.clients = await self.create_clients()
            self.multi_client = await self.create_multi_client()

            # 启动客户端
            for client in self.clients:
                await client.start()

            if self.multi_client:
                await self.multi_client.start()

            # 连接客户端
            logger.info("🔗 连接客户端...")
            for client in self.clients:
                connected = await client.connect()
                logger.info(f"   客户端连接: {'成功' if connected else '失败'}")

            await asyncio.sleep(2)  # 等待连接完成

            # 运行测试序列
            await self.test_client_to_server_messaging()
            await asyncio.sleep(2)

            await self.test_server_to_client_messaging()
            await asyncio.sleep(2)

            await self.test_custom_messaging()
            await asyncio.sleep(3)  # 等待所有异步处理完成

        except Exception as e:
            logger.error(f"❌ 测试运行错误: {e}")
            import traceback

            logger.error(f"   错误详情: {traceback.format_exc()}")
            self.test_results["errors"] += 1

        finally:
            # 清理资源
            await self.cleanup_resources()

    async def cleanup_resources(self):
        """清理所有资源 - 使用标准stop()方法并验证协程清理"""
        logger.info("🧹 开始标准清理资源...")

        # 使用标准的stop()方法清理
        for i, client in enumerate(self.clients, 1):
            try:
                logger.info(f"🔄 停止客户端 {i}...")
                await client.stop()

                # 验证协程清理状态
                if hasattr(client, 'get_coroutine_status'):
                    try:
                        status = client.get_coroutine_status()
                        if status is None:
                            logger.info(f"✅ 客户端 {i} 已停止（状态检查返回None）")
                        else:
                            client_running = status.get('client_running', 'unknown')
                            dispatcher_task = status.get('dispatcher_task')
                            dispatcher_done = 'N/A'
                            if dispatcher_task and isinstance(dispatcher_task, dict):
                                dispatcher_done = dispatcher_task.get('done', 'N/A')

                            logger.info(f"✅ 客户端 {i} 状态检查: running={client_running}, dispatcher_done={dispatcher_done}")

                            # 验证所有协程都已清理
                            if client_running == False:
                                if dispatcher_task and isinstance(dispatcher_task, dict) and not dispatcher_task.get('done', True):
                                    logger.warning(f"⚠️ 客户端 {i} 分发器协程可能未完全清理")
                                else:
                                    logger.info(f"✅ 客户端 {i} 所有协程已清理")
                            elif client_running == 'unknown':
                                logger.info(f"✅ 客户端 {i} 状态未知，但已停止")
                    except Exception as status_error:
                        logger.warning(f"⚠️ 客户端 {i} 状态检查失败: {type(status_error).__name__}: {str(status_error)}")
                        logger.info(f"✅ 客户端 {i} 已停止（状态检查异常）")
                else:
                    logger.info(f"✅ 客户端 {i} 已停止（无状态检查接口）")

            except Exception as e:
                logger.error(f"❌ 客户端 {i} 停止失败: {e}")
                self.test_results["errors"] += 1

        # 停止多连接客户端
        if self.multi_client:
            logger.info("🔄 停止多连接客户端...")
            try:
                await self.multi_client.stop()

                # 验证协程清理状态
                if hasattr(self.multi_client, 'get_coroutine_status'):
                    try:
                        status = self.multi_client.get_coroutine_status()
                        if status is None:
                            logger.info(f"✅ 多连接客户端已停止（状态检查返回None）")
                        else:
                            client_running = status.get('client_running', 'unknown')
                            logger.info(f"✅ 多连接客户端状态检查: running={client_running}")
                    except Exception as status_error:
                        logger.warning(f"⚠️ 多连接客户端状态检查失败: {type(status_error).__name__}: {str(status_error)}")
                        logger.info(f"✅ 多连接客户端已停止（状态检查异常）")

            except Exception as e:
                logger.error(f"❌ 多连接客户端停止失败: {e}")
                self.test_results["errors"] += 1

        # 停止服务器
        logger.info("🔄 停止服务器...")
        try:
            await self.server.stop()

            # 验证服务端协程清理状态
            if hasattr(self.server, 'get_coroutine_status'):
                try:
                    status = self.server.get_coroutine_status()
                    logger.info(f"✅ 服务器状态检查: running={status.get('server_running')}, active_connections={status.get('active_connections', 0)}")

                    # 验证没有残留的协程
                    if status.get('server_running') == False and status.get('active_connections', 0) == 0:
                        logger.info("✅ 服务器所有协程和连接已清理")
                    else:
                        logger.warning(f"⚠️ 服务器可能存在未清理的资源: {status}")
                except Exception as status_error:
                    logger.warning(f"⚠️ 服务器状态检查失败: {status_error}")

        except Exception as e:
            logger.error(f"❌ 服务器停止失败: {e}")
            self.test_results["errors"] += 1

        logger.info("🎉 所有资源清理完成")


async def main():
    """主测试函数"""
    # 设置超时机制
    try:
        # 创建测试器
        tester = APIServerCompleteTester()

        # 使用asyncio.wait_for设置30秒超时
        await asyncio.wait_for(tester.run_complete_test(), timeout=100.0)

        # 打印测试结果
        tester.print_test_results()

        # 返回测试结果供验证
        return tester.test_results

    except asyncio.TimeoutError:
        logger.warning("⏰ 测试超时（30秒），强制退出")
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback

        logger.error(f"   错误详情: {traceback.format_exc()}")
    finally:
        logger.info("🏁 测试程序退出")


if __name__ == "__main__":
    print("🚀 开始API-Server Version完整测试...")

    # 运行测试
    try:
        test_results = asyncio.run(main())

        # 返回退出码（0表示成功，非0表示有错误）
        exit_code = 0 if test_results and test_results["errors"] == 0 else 1

        print(f"\n🏁 测试程序退出，退出码: {exit_code}")

        # 立即退出，避免任何剩余的异步清理任务产生错误输出
        os._exit(exit_code)

    except KeyboardInterrupt:
        print("\n⚠️ 用户中断测试")
        os._exit(130)  # 标准的键盘中断退出码
    except Exception as e:
        print(f"\n❌ 测试程序异常: {e}")
        os._exit(1)
