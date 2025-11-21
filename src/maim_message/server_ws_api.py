"""WebSocket服务端业务层API - 对标MessageServer"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Callable, Dict, Optional, Set, List
from dataclasses import dataclass

from .server_ws_connection import ServerNetworkDriver, EventType, NetworkEvent
from .message import APIMessageBase, BaseMessageInfo, Seg, MessageDim
from .ws_config import ServerConfig, AuthResult

logger = logging.getLogger(__name__)


class WebSocketServer:
    """WebSocket服务端业务层API"""

    def __init__(self, config: Optional[ServerConfig] = None):
        # 使用配置或创建默认配置
        self.config = config or ServerConfig()

        # 验证和初始化配置
        if not self.config.validate():
            raise ValueError("服务端配置验证失败")
        self.config.ensure_defaults()

        # 网络驱动器
        self.network_driver = ServerNetworkDriver(
            self.config.host,
            self.config.port,
            self.config.path,
            self.config.ssl_enabled,
            self.config.ssl_certfile,
            self.config.ssl_keyfile,
            self.config.ssl_ca_certs,
            self.config.ssl_verify,
        )

        # 业务状态管理 - 三级映射表 Map<UserID, Map<Platform, Set<UUID>>>
        self.user_connections: Dict[
            str, Set[str]
        ] = {}  # user_id -> set of connection_uuids
        self.platform_connections: Dict[
            str, Set[str]
        ] = {}  # platform -> set of connection_uuids
        self.connection_users: Dict[str, str] = {}  # connection_uuid -> user_id
        self.connection_metadata: Dict[
            str, Dict[str, Any]
        ] = {}  # connection_uuid -> metadata

        # 跨线程事件队列
        self.event_queue: asyncio.Queue = asyncio.Queue()
        self.running = False
        self.dispatcher_task: Optional[asyncio.Task] = None

        # 统计信息
        self.stats = {
            "total_auth_requests": 0,
            "successful_auths": 0,
            "failed_auths": 0,
            "messages_processed": 0,
            "custom_messages_processed": 0,
            "current_users": 0,
            "current_connections": 0,
        }

    def update_config(self, **kwargs) -> None:
        """更新配置"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                logger.info(f"服务端配置更新: {key} = {value}")
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

    async def _authenticate_connection(self, metadata: Dict[str, Any]) -> AuthResult:
        """认证连接"""
        self.stats["total_auth_requests"] += 1

        try:
            # 1. 首先调用认证回调
            auth_success = await self.config.on_auth(metadata)
            if not auth_success:
                self.stats["failed_auths"] += 1
                return AuthResult(success=False, error_message="认证失败")

            # 2. 调用用户标识提取回调，将api_key转换为user_id
            user_id = await self.config.on_auth_extract_user(metadata)
            if not user_id:
                self.stats["failed_auths"] += 1
                return AuthResult(success=False, error_message="无法提取用户标识")

            # 认证成功
            self.stats["successful_auths"] += 1
            return AuthResult(success=True, user_id=user_id)

        except Exception as e:
            logger.error(f"认证错误: {e}")
            self.stats["failed_auths"] += 1
            return AuthResult(success=False, error_message=str(e))

    async def _handle_connect_event(self, event: NetworkEvent) -> None:
        """处理连接事件"""
        metadata = event.metadata.to_dict()
        connection_uuid = event.metadata.uuid
        api_key = event.metadata.api_key
        platform = event.metadata.platform

        # 认证连接
        auth_result = await self._authenticate_connection(metadata)

        if not auth_result.success:
            logger.warning(
                f"Authentication failed for {connection_uuid}: {auth_result.error_message}"
            )
            # 拒绝连接
            await self.network_driver.disconnect_client(
                connection_uuid, f"Authentication failed: {auth_result.error_message}"
            )
            return

        # 认证通过，注册连接 - 使用转换后的user_id
        user_id = auth_result.user_id

        # 更新三级映射表 Map<UserID, Map<Platform, Set<UUID>>>
        if user_id not in self.user_connections:
            self.user_connections[user_id] = {}
        if platform not in self.user_connections[user_id]:
            self.user_connections[user_id][platform] = set()
        self.user_connections[user_id][platform].add(connection_uuid)

        # 平台索引映射
        if platform not in self.platform_connections:
            self.platform_connections[platform] = set()
        self.platform_connections[platform].add(connection_uuid)

        # 反向映射
        self.connection_users[connection_uuid] = user_id
        self.connection_metadata[connection_uuid] = metadata

        # 更新统计
        self.stats["current_users"] = len(self.user_connections)
        self.stats["current_connections"] = len(self.connection_users)

        logger.info(f"用户 {user_id} 从 {platform} 平台连接 ({connection_uuid})")

        # 调用连接回调
        try:
            await self.config.on_connect(connection_uuid, metadata)
        except Exception as e:
            logger.error(f"连接回调错误: {e}")

    async def _handle_disconnect_event(self, event: NetworkEvent) -> None:
        """处理断连事件"""
        connection_uuid = event.metadata.uuid
        user_id = self.connection_users.get(connection_uuid)

        if user_id:
            # 从三级映射表中移除
            if user_id in self.user_connections:
                metadata = self.connection_metadata.get(connection_uuid, {})
                platform = metadata.get("platform", event.metadata.platform)

                # 从用户->平台->连接映射中移除
                if platform in self.user_connections[user_id]:
                    self.user_connections[user_id][platform].discard(connection_uuid)
                    if not self.user_connections[user_id][platform]:
                        del self.user_connections[user_id][platform]

                # 如果用户没有任何平台连接了，删除用户
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]

            # 从平台索引中移除
            if event.metadata.platform in self.platform_connections:
                self.platform_connections[event.metadata.platform].discard(
                    connection_uuid
                )
                if not self.platform_connections[event.metadata.platform]:
                    del self.platform_connections[event.metadata.platform]

            # 清理反向映射
            del self.connection_users[connection_uuid]
            if connection_uuid in self.connection_metadata:
                del self.connection_metadata[connection_uuid]

            # 更新统计
            self.stats["current_users"] = len(self.user_connections)
            self.stats["current_connections"] = len(self.connection_users)

            logger.info(f"用户 {user_id} 断开连接 ({connection_uuid})")

        # 调用断连回调
        try:
            metadata = self.connection_metadata.get(
                connection_uuid, event.metadata.to_dict()
            )
            await self.config.on_disconnect(connection_uuid, metadata)
        except Exception as e:
            logger.error(f"断连回调错误: {e}")

    async def _handle_message_event(self, event: NetworkEvent) -> None:
        """处理消息事件"""
        try:
            self.stats["messages_processed"] += 1

            # 解析消息
            message_data = event.payload
            message_type = message_data.get("type", "unknown")

            # 处理标准消息
            if message_type == "sys_std":
                await self._handle_standard_message(event, message_data)
            # 处理自定义消息
            elif message_type.startswith("custom_"):
                await self._handle_custom_message(event, message_type, message_data)
            # 忽略系统消息
            elif message_type.startswith("sys_"):
                logger.debug(f"忽略系统消息: {message_type}")
            else:
                logger.warning(f"未知消息类型: {message_type}")

        except Exception as e:
            logger.error(f"消息处理错误: {e}")

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
                        platform=event.metadata.platform,
                        message_id=str(time.time()),
                        time=time.time(),
                    ),
                    message_segment=Seg(type="text", data=str(payload)),
                    message_dim=MessageDim(
                        api_key=event.metadata.api_key, platform=event.metadata.platform
                    ),
                )

            # 调用消息处理器
            try:
                await self.config.on_message(server_message, event.metadata.to_dict())
            except Exception as e:
                logger.error(f"标准消息处理器错误: {e}")

        except Exception as e:
            logger.error(f"标准消息处理错误: {e}")

    async def _handle_custom_message(
        self, event: NetworkEvent, message_type: str, message_data: Dict[str, Any]
    ) -> None:
        """处理自定义消息"""
        self.stats["custom_messages_processed"] += 1

        handler = self.config.custom_handlers.get(message_type)
        if handler:
            try:
                # 传递连接元数据给处理器
                metadata = event.metadata.to_dict()
                await handler(message_data, metadata)
            except Exception as e:
                logger.error(f"自定义处理器错误 {message_type}: {e}")
        else:
            logger.warning(f"未找到自定义消息类型处理器: {message_type}")

    async def _dispatcher_loop(self) -> None:
        """事件分发循环"""
        logger.info("Event dispatcher started")
        logger.debug(f"🔍 Event queue: {self.event_queue}, Running: {self.running}")

        while self.running:
            try:
                # 获取事件
                logger.debug(
                    f"⏳ Waiting for event from queue (current size: {self.event_queue.qsize()})"
                )
                event = await asyncio.wait_for(self.event_queue.get(), timeout=1.0)

                logger.debug(
                    f"📨 Received event: {event.event_type.value} for {event.uuid}"
                )

                # 分发事件
                if event.event_type == EventType.CONNECT:
                    logger.debug(f"🔗 Processing CONNECT event for {event.uuid}")
                    await self._handle_connect_event(event)
                elif event.event_type == EventType.DISCONNECT:
                    logger.debug(f"🔌 Processing DISCONNECT event for {event.uuid}")
                    await self._handle_disconnect_event(event)
                elif event.event_type == EventType.MESSAGE:
                    logger.debug(f"💬 Processing MESSAGE event for {event.uuid}")
                    await self._handle_message_event(event)

            except asyncio.TimeoutError:
                # 正常超时，继续循环
                continue
            except Exception as e:
                logger.error(f"❌ Dispatcher error: {e}")
                import traceback

                logger.error(f"   Traceback: {traceback.format_exc()}")

        logger.info("Event dispatcher stopped")

    async def send_message(self, message: APIMessageBase) -> Dict[str, bool]:
        """发送标准消息

        Args:
            message: 标准消息对象，包含 message_dim 信息用于路由

        Returns:
            Dict[str, bool]: 连接UUID到发送结果的映射
        """
        results = {}
        logger.info(f"🚀 WebSocketServer 开始发送消息")

        # 从消息中获取路由信息
        api_key = message.get_api_key()
        platform = message.get_platform()
        logger.info(f"📨 消息路由信息: api_key={api_key}, platform={platform}")

        # 记录当前连接状态
        logger.info(f"📊 当前连接状态: 已注册用户={len(self.user_connections)}, 用户连接映射={list(self.user_connections.keys())}")

        # 使用 extract_user 回调获取用户ID
        try:
            logger.info(f"🔍 开始从 API Key {api_key} 提取用户ID")
            target_user = await self.config.on_auth_extract_user({"api_key": api_key})
            logger.info(f"✅ 成功提取用户ID: {target_user}")
        except Exception as e:
            logger.error(f"❌ 无法从 API Key {api_key} 提取用户ID: {e}", exc_info=True)
            return results

        # 使用三级映射表获取目标用户的连接
        if target_user not in self.user_connections:
            logger.warning(f"❌ 用户 {target_user} 没有连接")
            logger.info(f"📋 可用的用户: {list(self.user_connections.keys())}")
            return results

        logger.info(f"✅ 找到用户 {target_user}，获取其连接")

        # 获取用户的所有平台连接
        user_platform_connections = self.user_connections[target_user]

        # 获取目标平台的连接
        if platform not in user_platform_connections:
            logger.warning(f"用户 {target_user} 在平台 {platform} 没有连接")
            return results
        target_connections = user_platform_connections[platform]

        # 构造消息包
        message_package = {
            "ver": 1,
            "msg_id": f"msg_{int(time.time() * 1000)}",
            "type": "sys_std",
            "meta": {
                "sender_user": "server",
                "target_user": target_user,
                "platform": platform,
                "timestamp": time.time(),
            },
            "payload": message.to_dict(),
        }

        # 发送到所有目标连接
        for connection_uuid in target_connections:
            success = await self.network_driver.send_message(
                connection_uuid, message_package
            )
            results[connection_uuid] = success

        logger.info(
            f"发送消息给用户 {target_user}: {sum(results.values())}/{len(results)} 连接成功"
        )

        return results

    async def send_custom_message(
        self,
        message_type: str,
        payload: Dict[str, Any],
        target_user: Optional[str] = None,
        target_platform: Optional[str] = None,
        connection_uuid: Optional[str] = None,
    ) -> Dict[str, bool]:
        """发送自定义消息"""
        results = {}

        # 构造消息包
        message_package = {
            "ver": 1,
            "msg_id": f"custom_{int(time.time() * 1000)}",
            "type": message_type,
            "meta": {
                "sender_user": "server",
                "target_user": target_user,
                "platform": target_platform,
                "timestamp": time.time(),
            },
            "payload": payload,
        }

        # 确定目标连接
        target_connections = set()

        if connection_uuid:
            # 发送到指定连接
            target_connections.add(connection_uuid)
        elif target_user:
            # 发送到指定用户的所有连接
            user_connections = self.user_connections.get(target_user, set())
            if target_platform:
                # 过滤平台
                platform_connections = self.platform_connections.get(
                    target_platform, set()
                )
                target_connections = user_connections & platform_connections
            else:
                target_connections = user_connections

        # 发送消息
        for conn_uuid in target_connections:
            success = await self.network_driver.send_message(conn_uuid, message_package)
            results[conn_uuid] = success

        return results

    async def broadcast_message(
        self, message: APIMessageBase, platform: Optional[str] = None
    ) -> Dict[str, bool]:
        """广播消息"""
        if platform:
            # 广播到指定平台的所有连接
            platform_connections = self.platform_connections.get(platform, set())
            message_package = {
                "ver": 1,
                "msg_id": f"broadcast_{int(time.time() * 1000)}",
                "type": "sys_std",
                "meta": {
                    "broadcast": True,
                    "platform": platform,
                    "timestamp": time.time(),
                },
                "payload": message.to_dict(),
            }

            results = {}
            for connection_uuid in platform_connections:
                success = await self.network_driver.send_message(
                    connection_uuid, message_package
                )
                results[connection_uuid] = success

            return results
        else:
            # 广播到所有连接
            message_package = {
                "ver": 1,
                "msg_id": f"broadcast_{int(time.time() * 1000)}",
                "type": "sys_std",
                "meta": {"broadcast": True, "timestamp": time.time()},
                "payload": message.to_dict(),
            }

            return await self.network_driver.broadcast_message(message_package)

    def get_user_connections(self, user_id: str) -> Set[str]:
        """获取用户的所有连接"""
        return self.user_connections.get(user_id, set())

    def get_platform_connections(self, platform: str) -> Set[str]:
        """获取平台的所有连接"""
        return self.platform_connections.get(platform, set())

    def get_connection_user(self, connection_uuid: str) -> Optional[str]:
        """获取连接对应的用户"""
        return self.connection_users.get(connection_uuid)

    def get_user_count(self) -> int:
        """获取当前用户数"""
        return len(self.user_connections)

    def get_connection_count(self) -> int:
        """获取当前连接数"""
        return len(self.connection_users)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        network_stats = self.network_driver.get_stats()
        return {**self.stats, "network": network_stats}

    async def start(self) -> None:
        """启动服务端"""
        if self.running:
            logger.warning("Server already running")
            return

        self.running = True

        # 启动事件分发器
        self.dispatcher_task = asyncio.create_task(self._dispatcher_loop())

        # 并行启动网络驱动器
        network_task = asyncio.create_task(self.network_driver.start(self.event_queue))

        logger.info(
            f"WebSocket server starting on {self.network_driver.host}:{self.network_driver.port}"
        )

        # 等待网络驱动器启动
        await asyncio.sleep(1)

        logger.info(f"WebSocket server started successfully")

    async def stop(self) -> None:
        """停止服务端"""
        if not self.running:
            return

        logger.info("Stopping WebSocket server...")
        self.running = False

        # 停止事件分发器
        if self.dispatcher_task:
            self.dispatcher_task.cancel()
            try:
                await self.dispatcher_task
            except asyncio.CancelledError:
                pass

        # 停止网络驱动器
        await self.network_driver.stop()

        # 清理状态
        self.user_connections.clear()
        self.platform_connections.clear()
        self.connection_users.clear()

        logger.info("WebSocket server stopped")
