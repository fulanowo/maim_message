"""WebSocket业务层配置类 - 统一管理所有回调配置"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Dict, Optional, Set
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

from .message import APIMessageBase, BaseMessageInfo, Seg, MessageDim

logger = logging.getLogger(__name__)


class ConfigValidator(ABC):
    """配置验证器基类"""

    @abstractmethod
    def validate(self) -> bool:
        """验证配置是否有效"""
        pass

    @abstractmethod
    def get_missing_fields(self) -> Set[str]:
        """获取缺失的必填字段"""
        pass


@dataclass
class ServerConfig(ConfigValidator):
    """WebSocket服务端配置类"""

    # 基础网络配置
    host: str = "0.0.0.0"
    port: int = 18000
    path: str = "/ws"

    # SSL/TLS配置
    ssl_enabled: bool = False
    ssl_certfile: Optional[str] = None  # SSL证书文件路径
    ssl_keyfile: Optional[str] = None   # SSL私钥文件路径
    ssl_ca_certs: Optional[str] = None  # CA证书文件路径（可选）
    ssl_verify: bool = False             # 是否验证客户端证书

    # 回调函数配置
    on_auth: Optional[Callable[[Dict[str, Any]], bool]] = None
    on_auth_extract_user: Optional[Callable[[Dict[str, Any]], str]] = None
    on_message: Optional[Callable[[APIMessageBase, Dict[str, Any]], None]] = None
    on_connect: Optional[Callable[[str, Dict[str, Any]], None]] = None
    on_disconnect: Optional[Callable[[str, Dict[str, Any]], None]] = None

    # 自定义消息处理器
    custom_handlers: Dict[str, Callable[[Dict[str, Any]], None]] = field(default_factory=dict)

    # 统计信息配置
    enable_stats: bool = True
    stats_callback: Optional[Callable[[Dict[str, Any]], None]] = None

    # 日志配置
    log_level: str = "INFO"
    enable_connection_log: bool = True
    enable_message_log: bool = True

    def validate(self) -> bool:
        """验证配置是否有效"""
        missing = self.get_missing_fields()
        if missing:
            logger.error(f"服务端配置缺失必填字段: {missing}")
            return False
        return True

    def get_missing_fields(self) -> Set[str]:
        """获取缺失的必填字段"""
        missing = set()

        # on_auth_extract_user是必须的，因为需要将api_key转换为user_id
        if self.on_auth_extract_user is None:
            missing.add("on_auth_extract_user")

        return missing

    def get_default_auth_handler(self) -> Callable[[Dict[str, Any]], bool]:
        """获取默认认证处理器"""
        async def default_auth(metadata: Dict[str, Any]) -> bool:
            """默认认证：只要有api_key就通过"""
            api_key = metadata.get("api_key", "")
            if api_key:
                logger.info(f"默认认证通过: {api_key}")
                return True
            else:
                logger.warning(f"默认认证失败: 缺少api_key")
                return False
        return default_auth

    def get_default_user_extractor(self) -> Callable[[Dict[str, Any]], str]:
        """获取默认用户标识提取器"""
        def default_extract_user(metadata: Dict[str, Any]) -> str:
            """默认用户标识提取：直接使用api_key作为user_id"""
            api_key = metadata.get("api_key", "")
            if not api_key:
                raise ValueError("无法提取用户标识：缺少api_key")
            return api_key
        return default_extract_user

    def get_default_message_handler(self) -> Callable[[APIMessageBase, Dict[str, Any]], None]:
        """获取默认消息处理器"""
        async def default_message_handler(message: APIMessageBase, metadata: Dict[str, Any]) -> None:
            """默认消息处理器：记录消息"""
            if self.enable_message_log:
                logger.info(f"收到消息: {message.message_segment.data} "
                           f"from {message.get_api_key()}")
        return default_message_handler

    def get_default_connect_handler(self) -> Callable[[str, Dict[str, Any]], None]:
        """获取默认连接处理器"""
        async def default_connect_handler(connection_uuid: str, metadata: Dict[str, Any]) -> None:
            """默认连接处理器：记录连接"""
            if self.enable_connection_log:
                logger.info(f"客户端连接: {connection_uuid} from {metadata.get('platform', 'unknown')}")
        return default_connect_handler

    def get_default_disconnect_handler(self) -> Callable[[str, Dict[str, Any]], None]:
        """获取默认断连处理器"""
        async def default_disconnect_handler(connection_uuid: str, metadata: Dict[str, Any]) -> None:
            """默认断连处理器：记录断连"""
            if self.enable_connection_log:
                logger.info(f"客户端断开: {connection_uuid}")
        return default_disconnect_handler

    def ensure_defaults(self) -> None:
        """确保所有必填的回调都有默认值"""
        if self.on_auth is None:
            self.on_auth = self.get_default_auth_handler()
            logger.info("使用默认认证处理器")

        if self.on_auth_extract_user is None:
            self.on_auth_extract_user = self.get_default_user_extractor()
            logger.info("使用默认用户标识提取器")

        if self.on_message is None:
            self.on_message = self.get_default_message_handler()
            logger.info("使用默认消息处理器")

        if self.on_connect is None:
            self.on_connect = self.get_default_connect_handler()
            logger.info("使用默认连接处理器")

        if self.on_disconnect is None:
            self.on_disconnect = self.get_default_disconnect_handler()
            logger.info("使用默认断连处理器")

    def register_custom_handler(self, message_type: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        """注册自定义消息处理器"""
        if not message_type.startswith("custom_"):
            message_type = f"custom_{message_type}"
        self.custom_handlers[message_type] = handler
        logger.info(f"注册自定义处理器: {message_type}")

    def unregister_custom_handler(self, message_type: str) -> None:
        """注销自定义消息处理器"""
        if not message_type.startswith("custom_"):
            message_type = f"custom_{message_type}"
        self.custom_handlers.pop(message_type, None)
        logger.info(f"注销自定义处理器: {message_type}")


@dataclass
class ClientConfig(ConfigValidator):
    """WebSocket客户端配置类"""

    # 基础连接配置
    url: str
    api_key: str
    platform: str = "default"
    connection_uuid: Optional[str] = None

    # SSL/TLS配置
    ssl_enabled: bool = False                    # 是否启用SSL
    ssl_verify: bool = True                     # 是否验证SSL证书
    ssl_ca_certs: Optional[str] = None         # CA证书文件路径
    ssl_certfile: Optional[str] = None         # 客户端证书文件路径
    ssl_keyfile: Optional[str] = None          # 客户端私钥文件路径
    ssl_check_hostname: bool = True             # 是否检查主机名

    # 重连配置
    auto_reconnect: bool = True
    max_reconnect_attempts: int = 5
    reconnect_delay: float = 1.0
    max_reconnect_delay: float = 30.0

    # 心跳配置
    ping_interval: int = 20
    ping_timeout: int = 10
    close_timeout: int = 10

    # 回调函数配置
    on_connect: Optional[Callable[[str, Dict[str, Any]], None]] = None
    on_disconnect: Optional[Callable[[str, Optional[str]], None]] = None
    on_message: Optional[Callable[[APIMessageBase, Dict[str, Any]], None]] = None

    # 自定义消息处理器
    custom_handlers: Dict[str, Callable[[Dict[str, Any]], None]] = field(default_factory=dict)

    # 统计信息配置
    enable_stats: bool = True
    stats_callback: Optional[Callable[[Dict[str, Any]], None]] = None

    # 日志配置
    log_level: str = "INFO"
    enable_connection_log: bool = True
    enable_message_log: bool = True

    # HTTP Headers
    headers: Dict[str, str] = field(default_factory=dict)

    def validate(self) -> bool:
        """验证配置是否有效"""
        missing = self.get_missing_fields()
        if missing:
            logger.error(f"客户端配置缺失必填字段: {missing}")
            return False

        # 验证URL格式
        if not (self.url.startswith("ws://") or self.url.startswith("wss://")):
            logger.error("客户端配置错误: URL必须以ws://或wss://开头")
            return False

        return True

    def get_missing_fields(self) -> Set[str]:
        """获取缺失的必填字段"""
        missing = set()

        if not self.url:
            missing.add("url")
        if not self.api_key:
            missing.add("api_key")

        return missing

    def get_default_connect_handler(self) -> Callable[[str, Dict[str, Any]], None]:
        """获取默认连接处理器"""
        async def default_connect_handler(connection_uuid: str, config: Dict[str, Any]) -> None:
            """默认连接处理器：记录连接"""
            if self.enable_connection_log:
                logger.info(f"已连接到服务器: {self.url} ({connection_uuid})")
        return default_connect_handler

    def get_default_disconnect_handler(self) -> Callable[[str, Optional[str]], None]:
        """获取默认断连处理器"""
        async def default_disconnect_handler(connection_uuid: str, error: Optional[str]) -> None:
            """默认断连处理器：记录断连"""
            if self.enable_connection_log:
                if error:
                    logger.warning(f"与服务器断开连接: {connection_uuid} - {error}")
                else:
                    logger.info(f"与服务器断开连接: {connection_uuid}")
        return default_disconnect_handler

    def get_default_message_handler(self) -> Callable[[APIMessageBase, Dict[str, Any]], None]:
        """获取默认消息处理器"""
        async def default_message_handler(message: APIMessageBase, metadata: Dict[str, Any]) -> None:
            """默认消息处理器：记录消息"""
            if self.enable_message_log:
                logger.info(f"收到消息: {message.message_segment.data}")
        return default_message_handler

    def ensure_defaults(self) -> None:
        """确保所有必填的回调都有默认值"""
        if self.on_connect is None:
            self.on_connect = self.get_default_connect_handler()
            logger.info("使用默认连接处理器")

        if self.on_disconnect is None:
            self.on_disconnect = self.get_default_disconnect_handler()
            logger.info("使用默认断连处理器")

        if self.on_message is None:
            self.on_message = self.get_default_message_handler()
            logger.info("使用默认消息处理器")

        # 设置默认headers
        default_headers = {
            "x-apikey": self.api_key,
            "x-platform": self.platform
        }
        for key, value in default_headers.items():
            if key not in self.headers:
                self.headers[key] = value

    def register_custom_handler(self, message_type: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        """注册自定义消息处理器"""
        if not message_type.startswith("custom_"):
            message_type = f"custom_{message_type}"
        self.custom_handlers[message_type] = handler
        logger.info(f"注册自定义处理器: {message_type}")

    def unregister_custom_handler(self, message_type: str) -> None:
        """注销自定义消息处理器"""
        if not message_type.startswith("custom_"):
            message_type = f"custom_{message_type}"
        self.custom_handlers.pop(message_type, None)
        logger.info(f"注销自定义处理器: {message_type}")


@dataclass
class AuthResult:
    """认证结果"""
    success: bool
    user_id: Optional[str] = None
    error_message: Optional[str] = None


class ConfigManager:
    """配置管理器 - 统一管理所有配置的更新和访问"""

    def __init__(self):
        self._server_config: Optional[ServerConfig] = None
        self._client_config: Optional[ClientConfig] = None
        self._config_validators: Dict[str, ConfigValidator] = {}

    def set_server_config(self, config: ServerConfig) -> None:
        """设置服务端配置"""
        if not config.validate():
            raise ValueError("服务端配置验证失败")
        config.ensure_defaults()
        self._server_config = config
        self._config_validators["server"] = config
        logger.info("服务端配置已设置")

    def set_client_config(self, config: ClientConfig) -> None:
        """设置客户端配置"""
        if not config.validate():
            raise ValueError("客户端配置验证失败")
        config.ensure_defaults()
        self._client_config = config
        self._config_validators["client"] = config
        logger.info("客户端配置已设置")

    def get_server_config(self) -> Optional[ServerConfig]:
        """获取服务端配置"""
        return self._server_config

    def get_client_config(self) -> Optional[ClientConfig]:
        """获取客户端配置"""
        return self._client_config

    def update_server_config(self, **kwargs) -> None:
        """更新服务端配置"""
        if self._server_config is None:
            raise ValueError("服务端配置未设置")

        for key, value in kwargs.items():
            if hasattr(self._server_config, key):
                setattr(self._server_config, key, value)
                logger.info(f"服务端配置更新: {key} = {value}")
            else:
                logger.warning(f"无效的服务端配置项: {key}")

        # 重新验证配置
        if not self._server_config.validate():
            raise ValueError("更新后的服务端配置验证失败")

    def update_client_config(self, **kwargs) -> None:
        """更新客户端配置"""
        if self._client_config is None:
            raise ValueError("客户端配置未设置")

        for key, value in kwargs.items():
            if hasattr(self._client_config, key):
                setattr(self._client_config, key, value)
                logger.info(f"客户端配置更新: {key} = {value}")
            else:
                logger.warning(f"无效的客户端配置项: {key}")

        # 重新验证配置
        if not self._client_config.validate():
            raise ValueError("更新后的客户端配置验证失败")

    def validate_all_configs(self) -> bool:
        """验证所有配置"""
        all_valid = True
        for name, config in self._config_validators.items():
            if not config.validate():
                logger.error(f"{name}配置验证失败")
                all_valid = False
            else:
                logger.info(f"{name}配置验证通过")
        return all_valid


# 全局配置管理器实例
config_manager = ConfigManager()


def get_config_manager() -> ConfigManager:
    """获取全局配置管理器"""
    return config_manager


# 便捷函数
def create_server_config(**kwargs) -> ServerConfig:
    """创建服务端配置的便捷函数

    Args:
        host: 监听地址 (默认: "0.0.0.0")
        port: 监听端口 (默认: 18000)
        path: WebSocket路径 (默认: "/ws")
        ssl_enabled: 是否启用SSL (默认: False)
        ssl_certfile: SSL证书文件路径 (ssl_enabled=True时必填)
        ssl_keyfile: SSL私钥文件路径 (ssl_enabled=True时必填)
        ssl_ca_certs: CA证书文件路径 (可选)
        ssl_verify: 是否验证客户端证书 (默认: False)
        on_auth_extract_user: 用户标识提取回调 (必填)
        ...其他回调函数

    Returns:
        ServerConfig: 服务端配置对象

    Example:
        # HTTP服务器
        config = create_server_config(host="localhost", port=18040)

        # HTTPS服务器
        config = create_server_config(
            host="localhost",
            port=18044,
            ssl_enabled=True,
            ssl_certfile="/path/to/cert.pem",
            ssl_keyfile="/path/to/key.pem"
        )
    """
    return ServerConfig(**kwargs)


def create_client_config(url: str, api_key: str, **kwargs) -> ClientConfig:
    """创建客户端配置的便捷函数

    Args:
        url: WebSocket服务器URL
        api_key: API密钥
        platform: 平台标识 (默认: "default")
        ssl_enabled: 是否启用SSL (自动从URL协议检测)
        ssl_verify: 是否验证SSL证书 (默认: True)
        ssl_ca_certs: CA证书文件路径 (可选)
        ssl_certfile: 客户端证书文件路径 (可选)
        ssl_keyfile: 客户端私钥文件路径 (可选)
        ssl_check_hostname: 是否检查主机名 (默认: True)
        ...其他配置

    Returns:
        ClientConfig: 客户端配置对象

    Example:
        # HTTP客户端
        config = create_client_config(
            url="ws://localhost:18040/ws",
            api_key="your_api_key"
        )

        # HTTPS客户端
        config = create_client_config(
            url="wss://localhost:18044/ws",
            api_key="your_api_key",
            ssl_ca_certs="/path/to/ca.pem"
        )
    """
    # 自动检测SSL
    if url.startswith("wss://"):
        kwargs["ssl_enabled"] = True

    return ClientConfig(url=url, api_key=api_key, **kwargs)


def create_ssl_server_config(
    host: str = "0.0.0.0",
    port: int = 18044,
    ssl_certfile: str = None,
    ssl_keyfile: str = None,
    **kwargs
) -> ServerConfig:
    """创建SSL服务端配置的便捷函数

    Args:
        host: 监听地址
        port: 监听端口
        ssl_certfile: SSL证书文件路径
        ssl_keyfile: SSL私钥文件路径
        **kwargs: 其他ServerConfig参数

    Returns:
        ServerConfig: 配置了SSL的服务端配置

    Example:
        config = create_ssl_server_config(
            host="localhost",
            port=18044,
            ssl_certfile="/path/to/cert.pem",
            ssl_keyfile="/path/to/key.pem"
        )
    """
    kwargs.update({
        "host": host,
        "port": port,
        "ssl_enabled": True,
        "ssl_certfile": ssl_certfile,
        "ssl_keyfile": ssl_keyfile
    })
    return create_server_config(**kwargs)


def create_ssl_client_config(
    url: str = None,
    host: str = "localhost",
    port: int = 18044,
    api_key: str = None,
    path: str = "/ws",
    ssl_ca_certs: str = None,
    **kwargs
) -> ClientConfig:
    """创建SSL客户端配置的便捷函数

    Args:
        url: 完整的WebSocket URL (如果提供，会忽略其他参数)
        host: 服务器主机名
        port: 服务器端口
        api_key: API密钥
        path: WebSocket路径
        ssl_ca_certs: CA证书文件路径
        **kwargs: 其他ClientConfig参数

    Returns:
        ClientConfig: 配置了SSL的客户端配置

    Example:
        config = create_ssl_client_config(
            url="wss://localhost:18044/ws",
            api_key="your_api_key",
            ssl_ca_certs="/path/to/ca.pem"
        )
    """
    if url is None:
        url = f"wss://{host}:{port}{path}"

    kwargs.update({
        "ssl_enabled": True,
        "ssl_ca_certs": ssl_ca_certs
    })

    if api_key is not None:
        return create_client_config(url, api_key, **kwargs)
    else:
        raise ValueError("api_key is required for client configuration")