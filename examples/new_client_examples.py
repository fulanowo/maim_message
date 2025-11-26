"""新客户端使用示例 - 展示WebSocketClient单连接和WebSocketMultiClient多连接客户端的使用方法"""

import asyncio
import logging
import time
from maim_message.message import APIMessageBase, BaseMessageInfo, Seg, MessageDim

# 导入新的客户端类
from maim_message.client import WebSocketClient, WebSocketMultiClient
from maim_message.client_factory import create_client_config

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def single_client_example():
    """单连接客户端示例"""
    print("\n🟢 单连接客户端示例")
    print("=" * 50)

    # 方式1：使用配置工厂函数创建配置，然后用配置初始化客户端
    config = create_client_config(
        "ws://localhost:18040/ws",
        "single_api_key",
        platform="single_client"
    )
    client = WebSocketClient(config)

    try:
        # 启动客户端
        await client.start()
        print("✅ 单连接客户端已启动")

        # 连接服务器
        connected = await client.connect()
        if connected:
            print("✅ 连接服务器成功")

            # 查看缓存的连接信息
            conn_info = client.get_cached_connection_info()
            print(f"📋 连接信息: {conn_info}")

            # 发送标准消息
            message = APIMessageBase(
                message_info=BaseMessageInfo(
                    platform="single_client",
                    message_id=f"single_{int(time.time())}",
                    time=time.time()
                ),
                message_segment=Seg(type="text", data="来自单连接客户端的消息"),
                message_dim=MessageDim(
                    api_key="target_api_key",    # 目标接收者
                    platform="single_client"     # 目标平台
                )
            )

            success = await client.send_message(message)
            print(f"📤 标准消息发送: {'✅ 成功' if success else '❌ 失败'}")

            # 发送自定义消息
            success = await client.send_custom_message(
                "notification",
                {
                    "title": "单连接通知",
                    "content": "这是来自单连接客户端的自定义消息",
                    "timestamp": time.time()
                }
            )
            print(f"📤 自定义消息发送: {'✅ 成功' if success else '❌ 失败'}")

            # 获取统计信息
            stats = client.get_stats()
            print(f"📊 统计信息: 发送消息数={stats['messages_sent']}, 连接状态={stats['connected']}")

            await asyncio.sleep(2)
        else:
            print("❌ 连接服务器失败")

    finally:
        await client.stop()
        print("🛑 单连接客户端已停止")


async def multi_client_example():
    """多连接客户端示例"""
    print("\n🔵 多连接客户端示例")
    print("=" * 50)

    # 创建多连接客户端（可以提供默认配置，也可以不提供）
    client = WebSocketMultiClient()

    try:
        # 启动客户端
        await client.start()
        print("✅ 多连接客户端已启动")

        # 注册多个连接
        print("\n📝 注册连接...")
        client.register_connection("wechat", "ws://localhost:18040/ws", "wechat_key", "wechat")
        client.register_connection("qq", "ws://localhost:18040/ws", "qq_key", "qq")
        client.register_connection("telegram", "ws://localhost:18040/ws", "telegram_key", "telegram")

        # 查看所有注册的连接
        connections = client.list_connections()
        print(f"📋 注册的连接: {list(connections.keys())}")

        # 连接所有服务器
        print("\n🔗 连接所有服务器...")
        connect_results = await client.connect()
        print(f"连接结果: {connect_results}")

        # 等待连接建立
        await asyncio.sleep(3)

        # 查看活跃连接
        active_connections = client.get_active_connections()
        print(f"📋 活跃连接: {list(active_connections.keys())}")

        # 发送消息到不同连接
        print("\n📤 发送消息...")

        # 发送到微信连接
        wechat_message = APIMessageBase(
            message_info=BaseMessageInfo(
                platform="wechat",
                message_id=f"wechat_{int(time.time())}",
                time=time.time()
            ),
            message_segment=Seg(type="text", data="发送到微信连接的消息"),
            message_dim=MessageDim(api_key="target_wechat_key", platform="wechat")
        )

        success = await client.send_message("wechat", wechat_message)
        print(f"微信消息发送: {'✅ 成功' if success else '❌ 失败'}")

        # 发送到QQ连接
        qq_message = APIMessageBase(
            message_info=BaseMessageInfo(
                platform="qq",
                message_id=f"qq_{int(time.time())}",
                time=time.time()
            ),
            message_segment=Seg(type="text", data="发送到QQ连接的消息"),
            message_dim=MessageDim(api_key="target_qq_key", platform="qq")
        )

        success = await client.send_message("qq", qq_message)
        print(f"QQ消息发送: {'✅ 成功' if success else '❌ 失败'}")

        # 发送自定义消息到Telegram连接
        success = await client.send_custom_message(
            "telegram",
            "system_notification",
            {
                "title": "Telegram通知",
                "content": "来自多连接客户端的自定义消息",
                "timestamp": time.time(),
                "priority": "high"
            }
        )
        print(f"Telegram自定义消息发送: {'✅ 成功' if success else '❌ 失败'}")

        # 查看每个连接的详细信息
        print("\n📊 连接详细信息:")
        for name in ["wechat", "qq", "telegram"]:
            conn_info = client.get_connection_info(name)
            if conn_info:
                print(f"  {name}: 已连接={conn_info['connected']}, UUID={conn_info['connection_uuid']}")

        # 获取统计信息
        stats = client.get_stats()
        print(f"\n📊 统计信息:")
        print(f"  注册连接数: {stats['connections_registered']}")
        print(f"  活跃连接数: {stats['connections_active']}")
        print(f"  发送消息数: {stats['messages_sent']}")
        print(f"  处理自定义消息数: {stats['custom_messages_processed']}")

        await asyncio.sleep(2)

        # 断开指定连接
        print("\n🔌 断开微信连接...")
        disconnect_result = await client.disconnect("wechat")
        print(f"微信连接断开: {'✅ 成功' if disconnect_result.get('wechat', False) else '❌ 失败'}")

        # 再次查看活跃连接
        active_connections = client.get_active_connections()
        print(f"断开后活跃连接: {list(active_connections.keys())}")

        await asyncio.sleep(2)

    finally:
        # 断开所有连接并停止客户端
        await client.disconnect()
        await client.stop()
        print("🛑 多连接客户端已停止")


async def comparison_example():
    """单连接 vs 多连接对比示例"""
    print("\n🔄 单连接 vs 多连接对比示例")
    print("=" * 50)

    print("🟢 单连接客户端特点:")
    print("  - 只需考虑一个连接，配置简单")
    print("  - send_message(message) - 无需指定连接名称")
    print("  - send_custom_message(type, payload) - 无需指定连接名称")
    print("  - 适合简单的单点通信场景")

    print("\n🔵 多连接客户端特点:")
    print("  - 支持管理多个连接，每个连接有名称")
    print("  - send_message(name, message) - 需要指定连接名称")
    print("  - send_custom_message(name, type, payload) - 需要指定连接名称")
    print("  - 适合多平台、多服务的复杂通信场景")

    print("\n💡 使用方式:")
    print("  - 单连接: config = create_client_config(url, api_key); client = WebSocketClient(config)")
    print("  - 多连接: client = WebSocketMultiClient(); client.register_connection(name, url, api_key, platform)")


async def main():
    """主函数"""
    print("🚀 新客户端使用示例")
    print("=" * 50)

    try:
        # 单连接示例
        await single_client_example()

        # 多连接示例
        await multi_client_example()

        # 对比示例
        await comparison_example()

    except KeyboardInterrupt:
        print("\n⚠️ 用户中断")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 50)
    print("✨ 新客户端示例完成")


if __name__ == "__main__":
    asyncio.run(main())