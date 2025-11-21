"""
WebSocket Client Module - High-level WebSocket client components

This module provides easy-to-use interfaces for building WebSocket clients
with the maim_message library.
"""

# Core client classes
from ..client_ws_api import WebSocketClient

# Message and data structures (from message module)
from ..message import (
    APIMessageBase,
    MessageDim,
    Seg,
    BaseMessageInfo,
)


# Configuration and utilities
from ..ws_config import (
    ClientConfig,
    create_client_config,
    create_ssl_client_config,
)

# All exports
__all__ = [
    # Core Client
    "WebSocketClient",

    # Message Classes (API-Server Version)
    "APIMessageBase",          # 主要消息类
    "MessageDim",
    "Seg",
    "BaseMessageInfo",

    # Configuration
    "ClientConfig",
    "create_client_config",
    "create_ssl_client_config",
]