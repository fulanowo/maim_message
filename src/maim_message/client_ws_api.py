"""WebSocket客户端业务层API - 对标MessageClient"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Callable, Dict, Optional, Set

from .client_ws_connection import (
    ClientNetworkDriver,
    EventType,
    NetworkEvent,
    ConnectionConfig,
)
from .message import APIMessageBase, BaseMessageInfo, Seg, MessageDim
from .ws_config import ClientConfig

logger = logging.getLogger(__name__)


class WebSocketClient:
    """WebSocket客户端业务层API"""

    def __init__(self, config: ClientConfig):
        # 验证和初始化配置
        if not config.validate():
            raise ValueError("客户端配置验证失败")
        config.ensure_defaults()
        self.config = config

        # 网络驱动器
        self.network_driver = ClientNetworkDriver()

        # 跨线程事件队列
        self.event_queue: asyncio.Queue = asyncio.Queue()
        self.running = False
        self.dispatcher_task: Optional[asyncio.Task] = None

        # 连接状态
        self.connected = False
        self.last_error: Optional[str] = None

        # 自定义消息处理器从配置中获取

        # 统计信息
        self.stats = {
            "connect_attempts": 0,
            "successful_connects": 0,
            "failed_connects": 0,
            "messages_received": 0,
            "messages_sent": 0,
            "custom_messages_processed": 0,
            "reconnect_attempts": 0,
        }

    def update_config(self, **kwargs) -> None:
        """更新配置"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                logger.info(f"客户端配置更新: {key} = {value}")
            else:
                logger.warning(f"无效的配置项: {key}")

        # 重新验证配置
        if not self.config.validate():
            raise ValueError("更新后的配置验证失败")
        self.config.ensure_defaults()

    def register_custom_handler(
        self, message_type: str, handler: Callable[[Dict[str, Any]], None]
    ) -> None:
        """注册自定义消息处理器"""
        self.config.register_custom_handler(message_type, handler)

    def unregister_custom_handler(self, message_type: str) -> None:
        """注销自定义消息处理器"""
        self.config.unregister_custom_handler(message_type)

    async def _handle_connect_event(self, event: NetworkEvent) -> None:
        """处理连接事件"""
        connection_uuid = event.connection_uuid
        self.connected = True
        self.last_error = None
        self.stats["successful_connects"] += 1

        logger.info(f"已连接到服务器 ({connection_uuid})")

        # 调用连接回调
        try:
            await self.config.on_connect(connection_uuid, event.config.to_dict())
        except Exception as e:
            logger.error(f"连接回调错误: {e}")

    async def _handle_disconnect_event(self, event: NetworkEvent) -> None:
        """处理断连事件"""
        connection_uuid = event.connection_uuid
        self.connected = False
        self.last_error = event.error

        logger.info(f"与服务器断开连接 ({connection_uuid})")

        # 调用断连回调
        try:
            await self.config.on_disconnect(connection_uuid, event.error)
        except Exception as e:
            logger.error(f"断连回调错误: {e}")

    async def _handle_message_event(self, event: NetworkEvent) -> None:
        """处理消息事件"""
        try:
            self.stats["messages_received"] += 1

            # 解析消息
            message_data = event.payload
            message_type = message_data.get("type", "unknown")

            # 忽略系统消息
            if message_type.startswith("sys_"):
                if message_type == "sys_std":
                    await self._handle_standard_message(event, message_data)
                # 忽略其他系统消息如ACK
            # 处理自定义消息
            elif message_type.startswith("custom_"):
                await self._handle_custom_message(event, message_type, message_data)
            else:
                logger.warning(f"未知消息类型: {message_type}")

        except Exception as e:
            logger.error(f"Message handling error: {e}")

    async def _handle_standard_message(
        self, event: NetworkEvent, message_data: Dict[str, Any]
    ) -> None:
        """处理标准消息"""
        try:
            # 构建APIMessageBase对象
            payload = message_data.get("payload", {})

            # 如果payload是标准的APIMessageBase格式
            if "message_info" in payload and "message_segment" in payload:
                # 直接解析
                server_message = APIMessageBase.from_dict(payload)
            else:
                # 包装成标准格式
                server_message = APIMessageBase(
                    message_info=BaseMessageInfo(
                        platform=event.config.platform,
                        message_id=str(time.time()),
                        time=time.time(),
                    ),
                    message_segment=Seg(type="text", data=str(payload)),
                    message_dim=MessageDim(
                        api_key=event.config.api_key, platform=event.config.platform
                    ),
                )

            # 调用消息处理器
            try:
                await self.config.on_message(server_message, event.config.to_dict())
            except Exception as e:
                logger.error(f"消息处理器错误: {e}")

        except Exception as e:
            logger.error(f"Standard message handling error: {e}")

    async def _handle_custom_message(
        self, event: NetworkEvent, message_type: str, message_data: Dict[str, Any]
    ) -> None:
        """处理自定义消息"""
        self.stats["custom_messages_processed"] += 1

        handler = self.config.custom_handlers.get(message_type)
        if handler:
            try:
                await handler(message_data)
            except Exception as e:
                logger.error(f"自定义处理器错误 {message_type}: {e}")
        else:
            logger.warning(f"未找到自定义消息类型处理器: {message_type}")

    async def _dispatcher_loop(self) -> None:
        """事件分发循环"""
        logger.info("Client event dispatcher started")

        while self.running:
            try:
                # 获取事件
                event = await asyncio.wait_for(self.event_queue.get(), timeout=1.0)

                # 分发事件
                if event.event_type == EventType.CONNECT:
                    await self._handle_connect_event(event)
                elif event.event_type == EventType.DISCONNECT:
                    await self._handle_disconnect_event(event)
                elif event.event_type == EventType.MESSAGE:
                    await self._handle_message_event(event)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Dispatcher error: {e}")

        logger.info("Client event dispatcher stopped")

    async def connect(self) -> bool:
        """连接到服务器"""
        if not self.running:
            logger.error("Client not started")
            return False

        connection_uuid = self.config.connection_uuid
        if not connection_uuid:
            # 生成新的连接UUID
            self.config.connection_uuid = f"client_{int(time.time() * 1000)}"
            connection_uuid = self.config.connection_uuid

        # 添加连接到网络驱动器
        connection_config = ConnectionConfig(
            url=self.config.url,
            api_key=self.config.api_key,
            platform=self.config.platform,
            connection_uuid=connection_uuid,
            headers=self.config.headers,
            max_reconnect_attempts=self.config.max_reconnect_attempts,
            reconnect_delay=self.config.reconnect_delay,
            # SSL配置
            ssl_enabled=self.config.ssl_enabled,
            ssl_verify=self.config.ssl_verify,
            ssl_ca_certs=self.config.ssl_ca_certs,
            ssl_certfile=self.config.ssl_certfile,
            ssl_keyfile=self.config.ssl_keyfile,
            ssl_check_hostname=self.config.ssl_check_hostname,
        )

        success = await self.network_driver.add_connection(connection_config)
        if success:
            self.stats["connect_attempts"] += 1
            logger.info(f"📞 准备启动连接到 {connection_uuid}")
            # 启动连接
            await self.network_driver.connect(connection_uuid)
            logger.info(f"📞 连接命令已发送给网络驱动器: {connection_uuid}")

            # 等待连接真正建立
            logger.info(f"等待连接 {connection_uuid} 建立...")
            max_wait_time = 15  # 增加到15秒
            wait_interval = 0.2  # 每0.2秒检查一次

            for _ in range(int(max_wait_time / wait_interval)):
                current_state = self.network_driver.connection_states.get(connection_uuid)
                logger.info(f"🔍 连接状态检查 {connection_uuid}: {current_state}")
                if current_state == "connected":
                    logger.info(f"✅ 连接 {connection_uuid} 已成功建立")
                    self.connected = True
                    self.stats["successful_connects"] += 1
                    return True
                elif current_state == "error":
                    logger.error(f"❌ 连接 {connection_uuid} 失败，状态: {current_state}")
                    self.stats["failed_connects"] += 1
                    return False
                elif current_state == "disconnected":
                    # 刚开始可能是disconnected，稍等片刻
                    pass

                await asyncio.sleep(wait_interval)

            # 检查最终状态
            final_state = self.network_driver.connection_states.get(connection_uuid)
            if final_state == "connected":
                logger.info(f"✅ 连接 {connection_uuid} 最终成功建立")
                self.connected = True
                self.stats["successful_connects"] += 1
                return True
            else:
                logger.error(f"⏰ 连接 {connection_uuid} 超时，最终状态: {final_state}")
                self.stats["failed_connects"] += 1
                return False

        self.stats["failed_connects"] += 1
        return False

    async def disconnect(self, connection_uuid: Optional[str] = None) -> bool:
        """断开连接

        Args:
            connection_uuid: 可选的连接UUID，如果不指定则断开主配置的连接

        Returns:
            bool: 断开是否成功
        """
        target_uuid = connection_uuid or self.config.connection_uuid
        if target_uuid:
            return await self.network_driver.disconnect(target_uuid)
        return False

    async def add_connection(
        self, url: str, api_key: str, platform: str, **kwargs
    ) -> Optional[str]:
        """添加新的连接

        Args:
            url: WebSocket URL
            api_key: API Key
            platform: 平台标识
            **kwargs: 其他连接配置参数

        Returns:
            Optional[str]: 新增连接的UUID，失败返回None
        """
        connection_config = ConnectionConfig(
            url=url,
            api_key=api_key,
            platform=platform,
            connection_uuid=f"client_{int(time.time() * 1000)}_{len(self.network_driver.connections)}",
            headers=kwargs.get("headers", {}),
            max_reconnect_attempts=kwargs.get("max_reconnect_attempts", 5),
            reconnect_delay=kwargs.get("reconnect_delay", 1.0),
            # SSL配置
            ssl_enabled=kwargs.get("ssl_enabled", False),
            ssl_verify=kwargs.get("ssl_verify", True),
            ssl_ca_certs=kwargs.get("ssl_ca_certs"),
            ssl_certfile=kwargs.get("ssl_certfile"),
            ssl_keyfile=kwargs.get("ssl_keyfile"),
            ssl_check_hostname=kwargs.get("ssl_check_hostname", True),
        )

        success = await self.network_driver.add_connection(connection_config)
        if success:
            logger.info(f"添加连接成功: {connection_config.connection_uuid} -> {url}")
            return connection_config.connection_uuid
        else:
            logger.error(f"添加连接失败: {url}")
            return None

    async def connect_to(self, connection_uuid: str) -> bool:
        """连接到指定的连接

        Args:
            connection_uuid: 连接UUID

        Returns:
            bool: 连接是否成功
        """
        return await self.network_driver.connect(connection_uuid)

    async def remove_connection(self, connection_uuid: str) -> bool:
        """移除连接

        Args:
            connection_uuid: 连接UUID

        Returns:
            bool: 移除是否成功
        """
        return await self.network_driver.remove_connection(connection_uuid)

    def get_connections(self) -> Dict[str, Dict[str, Any]]:
        """获取所有连接的信息

        Returns:
            Dict[str, Dict[str, Any]]: 连接UUID到连接信息的映射
        """
        connections_info = {}
        for (
            connection_uuid,
            connection_config,
        ) in self.network_driver.connections.items():
            connections_info[connection_uuid] = {
                "url": connection_config.url,
                "api_key": connection_config.api_key,
                "platform": connection_config.platform,
                "state": self.network_driver.connection_states.get(
                    connection_uuid, "unknown"
                ),
            }
        return connections_info

    def get_active_connections(self) -> Dict[str, Dict[str, Any]]:
        """获取所有活跃连接的信息

        Returns:
            Dict[str, Dict[str, Any]]: 连接UUID到连接信息的映射（仅包含已连接的）
        """
        active_connections = {}
        for (
            connection_uuid,
            connection_config,
        ) in self.network_driver.connections.items():
            if (
                self.network_driver.connection_states.get(connection_uuid)
                == "connected"
            ):
                active_connections[connection_uuid] = {
                    "url": connection_config.url,
                    "api_key": connection_config.api_key,
                    "platform": connection_config.platform,
                }
        return active_connections

    async def send_message(self, message: APIMessageBase) -> bool:
        """发送标准消息

        Args:
            message: 标准消息对象，包含 message_dim 信息用于路由

        Returns:
            bool: 发送是否成功
        """
        # 根据消息的目标信息自动选择连接
        target_api_key = message.get_api_key()
        target_platform = message.get_platform()
        connection_uuid = await self._find_connection_for_target(
            target_api_key, target_platform
        )
        logger.info(
            f"Sending message to target_api_key={target_api_key}, target_platform={target_platform} via connection_uuid={connection_uuid}"
        )

        if not connection_uuid:
            logger.warning(
                f"找不到适合的连接: api_key={message.get_api_key()}, platform={message.get_platform()}"
            )
            return False

        # 构造消息包
        message_package = {
            "ver": 1,
            "msg_id": f"msg_{int(time.time() * 1000)}",
            "type": "sys_std",
            "meta": {
                "sender_user": self.config.api_key,
                "platform": self.config.platform,
                "timestamp": time.time(),
            },
            "payload": message.to_dict(),
        }

        success = await self.network_driver.send_message(
            connection_uuid, message_package
        )
        if success:
            self.stats["messages_sent"] += 1

        return success

    async def _find_connection_for_target(
        self, target_api_key: str, target_platform: str
    ) -> Optional[str]:
        """根据目标的API Key和Platform找到合适的连接

        Args:
            target_api_key: 目标API Key
            target_platform: 目标平台

        Returns:
            Optional[str]: 找到的连接UUID，如果没找到返回None
        """
        connections = self.network_driver.connections
        connection_states = self.network_driver.connection_states
        logger.info(f"connections: {connections}")
        logger.info(f"connection_states: {connection_states}")

        # 优先查找完全匹配的连接
        for connection_uuid, connection_config in connections.items():
            current_state = connection_states.get(connection_uuid)
            logger.info(f"检查连接 {connection_uuid}: api_key={connection_config.api_key}, platform={connection_config.platform}, state={current_state}")
            if (
                connection_config.api_key == target_api_key
                and connection_config.platform == target_platform
                and current_state == "connected"
            ):
                logger.info(f"找到完全匹配的连接: {connection_uuid}")
                return connection_uuid

        # 如果没有完全匹配，查找API Key匹配的连接
        for connection_uuid, connection_config in connections.items():
            if (
                connection_config.api_key == target_api_key
                and self.network_driver.connection_states.get(connection_uuid)
                == "connected"
            ):
                return connection_uuid

        # 最后查找平台匹配的连接
        for connection_uuid, connection_config in connections.items():
            if (
                connection_config.platform == target_platform
                and self.network_driver.connection_states.get(connection_uuid)
                == "connected"
            ):
                return connection_uuid

        return None

    async def send_custom_message(
        self, message_type: str, payload: Dict[str, Any]
    ) -> bool:
        """发送自定义消息"""
        if not self.connected:
            logger.warning("Not connected, cannot send custom message")
            return False

        connection_uuid = self.config.connection_uuid
        if not connection_uuid:
            return False

        # 确保类型前缀
        if not message_type.startswith("custom_"):
            message_type = f"custom_{message_type}"

        # 构造消息包
        message_package = {
            "ver": 1,
            "msg_id": f"custom_{int(time.time() * 1000)}",
            "type": message_type,
            "meta": {
                "sender_user": self.config.api_key,
                "platform": self.config.platform,
                "timestamp": time.time(),
            },
            "payload": payload,
        }

        success = await self.network_driver.send_message(
            connection_uuid, message_package
        )
        if success:
            self.stats["messages_sent"] += 1

        return success

    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self.connected

    def get_connection_uuid(self) -> Optional[str]:
        """获取连接UUID"""
        return self.config.connection_uuid

    def get_last_error(self) -> Optional[str]:
        """获取最后的错误信息"""
        return self.last_error

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        network_stats = self.network_driver.get_stats()
        return {
            **self.stats,
            "network": network_stats,
            "connected": self.connected,
            "last_error": self.last_error,
        }

    async def start(self) -> None:
        """启动客户端"""
        if self.running:
            logger.warning("Client already running")
            return

        self.running = True

        # 启动网络驱动器
        await self.network_driver.start(self.event_queue)

        # 启动事件分发器
        self.dispatcher_task = asyncio.create_task(self._dispatcher_loop())

        logger.info(f"WebSocket client started for {self.config.url}")

    async def stop(self) -> None:
        """停止客户端"""
        if not self.running:
            return

        logger.info("Stopping WebSocket client...")
        self.running = False

        # 断开连接
        await self.disconnect()

        # 停止事件分发器
        if self.dispatcher_task:
            self.dispatcher_task.cancel()
            try:
                await self.dispatcher_task
            except asyncio.CancelledError:
                pass

        # 停止网络驱动器
        await self.network_driver.stop()

        logger.info("WebSocket client stopped")
