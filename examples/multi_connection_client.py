"""多连接客户端示例 - 演示客户端连接多个服务端并智能路由消息"""

import asyncio
import logging
import time
from maim_message.client import WebSocketClient, create_client_config
from maim_message.message import APIMessageBase, BaseMessageInfo, Seg, MessageDim

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def multi_connection_demo():
    """多连接客户端演示"""

    # 创建客户端实例（使用默认配置作为主连接）
    main_config = create_client_config(
        url="ws://localhost:18040/ws",
        api_key="main_client_key",
        platform="demo_main"
    )

    client = WebSocketClient(main_config)

    try:
        # 启动客户端
        await client.start()

        # 1. 连接主服务
        print("🔗 连接主服务...")
        main_connected = await client.connect()
        if main_connected:
            print("✅ 主服务连接成功")
        else:
            print("❌ 主服务连接失败")
            return

        # 2. 添加多个额外连接
        print("\n🔗 添加额外连接...")

        # 连接到wechat平台
        wechat_connection = await client.add_connection(
            "ws://localhost:18040/ws",
            "wechat_api_key",
            "wechat"
        )
        if wechat_connection:
            await client.connect_to(wechat_connection)
            print(f"✅ 微信平台连接成功: {wechat_connection}")

        # 连接到qq平台
        qq_connection = await client.add_connection(
            "ws://localhost:18040/ws",
            "qq_api_key",
            "qq"
        )
        if qq_connection:
            await client.connect_to(qq_connection)
            print(f"✅ QQ平台连接成功: {qq_connection}")

        # 连接到telegram平台
        telegram_connection = await client.add_connection(
            "ws://localhost:18040/ws",
            "telegram_api_key",
            "telegram"
        )
        if telegram_connection:
            await client.connect_to(telegram_connection)
            print(f"✅ Telegram平台连接成功: {telegram_connection}")

        # 3. 等待连接建立
        print("\n⏳ 等待连接建立...")
        await asyncio.sleep(2)

        # 4. 查看所有连接状态
        print("\n📊 连接状态:")
        all_connections = client.get_connections()
        for uuid, info in all_connections.items():
            print(f"  {uuid}: {info['platform']} ({info['state']})")

        active_connections = client.get_active_connections()
        print(f"活跃连接数: {len(active_connections)}")

        # 5. 演示自动路由消息发送
        print("\n📤 演示自动路由消息发送...")

        # 发送到微信平台（会自动找到wechat连接）
        wechat_message = APIMessageBase(
            message_info=BaseMessageInfo(
                platform="wechat",
                message_id=f"wechat_{int(time.time())}",
                time=time.time()
            ),
            message_segment=Seg(type="text", data="发送到微信平台的消息"),
            message_dim=MessageDim(api_key="wechat_api_key", platform="wechat")
        )

        success = await client.send_message(wechat_message)
        print(f"微信消息发送: {'✅ 成功' if success else '❌ 失败'}")

        # 发送到QQ平台（会自动找到qq连接）
        qq_message = APIMessageBase(
            message_info=BaseMessageInfo(
                platform="qq",
                message_id=f"qq_{int(time.time())}",
                time=time.time()
            ),
            message_segment=Seg(type="text", data="发送到QQ平台的消息"),
            message_dim=MessageDim(api_key="qq_api_key", platform="qq")
        )

        success = await client.send_message(qq_message)
        print(f"QQ消息发送: {'✅ 成功' if success else '❌ 失败'}")

        await asyncio.sleep(1)

        # 6. 发送消息到Telegram平台（自动路由）
        print("\n📤 演示自动路由消息发送...")

        telegram_message = APIMessageBase(
            message_info=BaseMessageInfo(
                platform="telegram",
                message_id=f"telegram_{int(time.time())}",
                time=time.time()
            ),
            message_segment=Seg(type="text", data="自动路由发送到Telegram"),
            message_dim=MessageDim(api_key="telegram_api_key", platform="telegram")
        )

        success = await client.send_message(telegram_message)
        print(f"Telegram自动路由消息发送: {'✅ 成功' if success else '❌ 失败'}")

        # 7. 演示自定义消息发送
        print("\n🔧 演示自定义消息发送...")

        # 发送自定义通知消息（通过主连接发送）
        success = await client.send_custom_message("notification", {
            "title": "系统通知",
            "content": "这是一条自定义通知消息",
            "timestamp": time.time(),
            "priority": "high"
        })
        print(f"自定义通知发送: {'✅ 成功' if success else '❌ 失败'}")

        # 9. 等待消息处理
        print("\n⏳ 等待消息处理...")
        await asyncio.sleep(3)

        # 10. 演示连接管理
        print("\n🔧 演示连接管理...")

        # 断开微信连接
        if wechat_connection:
            success = await client.disconnect(wechat_connection)
            print(f"断开微信连接: {'✅ 成功' if success else '❌ 失败'}")

        # 移除Telegram连接
        if telegram_connection:
            success = await client.remove_connection(telegram_connection)
            print(f"移除Telegram连接: {'✅ 成功' if success else '❌ 失败'}")

        # 再次查看连接状态
        print("\n📊 最终连接状态:")
        final_connections = client.get_connections()
        for uuid, info in final_connections.items():
            print(f"  {uuid}: {info['platform']} ({info['state']})")

        await asyncio.sleep(2)

    except KeyboardInterrupt:
        print("\n⚠️ 用户中断")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 停止客户端
        print("\n🛑 停止客户端...")
        await client.stop()
        print("✅ 客户端已停止")


async def main():
    """主函数"""
    print("🚀 多连接客户端演示开始")
    print("=" * 50)

    await multi_connection_demo()

    print("\n" + "=" * 50)
    print("✨ 多连接客户端演示完成")


if __name__ == "__main__":
    asyncio.run(main())