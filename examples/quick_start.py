"""
API-Server Version 快速开始示例
演示最基本的服务端和客户端设置

前提条件：
pip install -e .
"""

import asyncio
import logging

# ✅ API-Server Version 正确导入方式
from maim_message.server import create_server_config, create_ssl_server_config, WebSocketServer
from maim_message.client import create_client_config, create_ssl_client_config, WebSocketClient
from maim_message.message import APIMessageBase, BaseMessageInfo, Seg, MessageDim

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def quick_server_example():
    """快速服务器示例"""
    print("🚀 启动快速服务器示例...")

    # 创建服务器配置
    config = create_server_config(host="localhost", port=18060, path="/ws")

    # 设置消息处理器
    config.on_message = lambda msg, meta: logger.info(f"收到消息: {msg.message_segment.data}")

    # 创建并启动服务器
    server = WebSocketServer(config)
    await server.start()

    print("✅ 服务器已启动在 ws://localhost:18060/ws")
    print("⏳ 运行30秒后自动停止...")

    # 运行30秒
    await asyncio.sleep(30)

    await server.stop()
    print("✅ 服务器已停止")


async def quick_client_example():
    """快速客户端示例"""
    print("🔗 启动快速客户端示例...")

    # 创建客户端配置
    config = create_client_config(
        url="ws://localhost:18060/ws",
        api_key="quick_demo_key",
        platform="demo"
    )

    # 设置消息处理器
    config.on_message = lambda msg, meta: logger.info(f"客户端收到: {msg.message_segment.data}")

    # 创建并启动客户端
    client = WebSocketClient(config)
    await client.start()

    # 连接服务器
    connected = await client.connect()
    if not connected:
        print("❌ 连接失败")
        return

    print("✅ 客户端连接成功")

    # 发送测试消息
    messages = [
        "Hello from quick client!",
        "This is a test message",
        "API-Server Version is working!",
        "🎉 WebSocket连接正常"
    ]

    for i, content in enumerate(messages, 1):
        message = APIMessageBase(
            message_info=BaseMessageInfo(
                platform="demo",
                message_id=f"quick_{i}_{int(asyncio.get_event_loop().time() * 1000)}",
                time=asyncio.get_event_loop().time()
            ),
            message_segment=Seg(type="text", data=content),
            message_dim=MessageDim(api_key="quick_demo_key", platform="demo")
        )

        success = await client.send_message(message)
        print(f"📤 消息{i}发送{'成功' if success else '失败'}: {content}")
        await asyncio.sleep(1)

    # 断开连接
    await client.disconnect()
    await client.stop()
    print("✅ 客户端已停止")


async def import_demo():
    """导入方式演示"""
    print("📦 导入方式演示:")
    print("-" * 40)

    try:
        # ✅ 正确的导入方式
        print("✅ 正确的导入方式:")
        print("   from maim_message.server import create_server_config, WebSocketServer")
        print("   from maim_message.client import create_client_config, WebSocketClient")
        print("   from maim_message.message import APIMessageBase")

        # 验证导入
        from maim_message.message import APIMessageBase as TestMsg
        from maim_message.server import WebSocketServer as TestServer
        from maim_message.client import WebSocketClient as TestClient
        print(f"   - APIMessageBase: {TestMsg}")
        print(f"   - WebSocketServer: {TestServer}")
        print(f"   - WebSocketClient: {TestClient}")

    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return

    try:
        # ❌ 错误的导入方式
        print("\n❌ 错误的导入方式（会失败）:")
        print("   from maim_message import APIMessageBase")
        from maim_message import APIMessageBase
        print("   ❌ 这不应该成功!")

    except ImportError:
        print("   ✅ 正确：无法从根模块导入API-Server Version组件")

    print("\n📝 总结:")
    print("   - Legacy组件: from maim_message import MessageBase, Seg 等")
    print("   - API-Server Version: 从子模块导入 (message, server, client)")


async def main():
    """主函数"""
    print("🎯 API-Server Version 快速开始示例")
    print("=" * 50)

    # 1. 导入演示
    await import_demo()

    # 2. 服务器示例（在后台运行）
    print("\n" + "=" * 50)
    print("📋 注意: 下面的示例演示服务器和客户端")
    print("   在实际使用中，服务器和客户端应该在不同的进程中运行")
    print("=" * 50)

    # 3. 演示基本用法
    print("\n📚 基本用法示例:")
    print("```python")
    print("# HTTP服务器")
    print("from maim_message.server import create_server_config, WebSocketServer")
    print("config = create_server_config(host='localhost', port=18060)")
    print("server = WebSocketServer(config)")
    print("await server.start()")
    print("")
    print("# HTTPS/SSL服务器")
    print("from maim_message.server import create_ssl_server_config, WebSocketServer")
    print("config = create_ssl_server_config(")
    print("    host='localhost',")
    print("    port=18044,")
    print("    ssl_certfile='/path/to/server.crt',")
    print("    ssl_keyfile='/path/to/server.key'")
    print(")")
    print("server = WebSocketServer(config)")
    print("await server.start()")
    print("")
    print("# HTTP客户端")
    print("from maim_message.client import create_client_config, WebSocketClient")
    print("from maim_message.message import APIMessageBase")
    print("config = create_client_config(url='ws://localhost:18060/ws', api_key='your_key')")
    print("client = WebSocketClient(config)")
    print("await client.connect()")
    print("")
    print("# HTTPS/SSL客户端")
    print("from maim_message.client import create_ssl_client_config, WebSocketClient")
    print("config = create_ssl_client_config(")
    print("    url='wss://localhost:18044/ws',")
    print("    api_key='your_key',")
    print("    ssl_ca_certs='/path/to/ca.crt'")
    print(")")
    print("client = WebSocketClient(config)")
    print("await client.connect()")
    print("```")

    print("\n🔒 SSL/HTTPS特性:")
    print("✅ 完整的SSL/TLS支持")
    print("✅ 自签名证书测试")
    print("✅ 客户端证书验证")
    print("✅ 双向认证支持")
    print("✅ 灵活的SSL配置选项")
    print("✅ 自动协议检测 (ws:// vs wss://)")

    print("\n✅ 快速开始示例完成!")
    print("\n📖 更多详细用法请参考:")
    print("   - doc/api_server_usage_guide.md")
    print("   - examples/external_library_example.py")


if __name__ == "__main__":
    asyncio.run(main())