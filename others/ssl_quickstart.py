"""
API-Server Version SSL快速开始示例
演示如何快速设置和使用SSL/TLS加密的WebSocket连接

这个示例展示了最基础的SSL配置，不需要真实证书文件。
"""

import asyncio
import logging

# ✅ API-Server Version SSL相关导入
from maim_message.server import create_ssl_server_config, WebSocketServer
from maim_message.client import create_ssl_client_config, WebSocketClient
from maim_message.message import APIMessageBase, BaseMessageInfo, Seg, MessageDim

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def ssl_server_example():
    """SSL服务器示例"""
    print("🔒 启动SSL服务器示例...")

    # 创建SSL服务器配置（注意：这里的证书文件路径是示例，实际使用时需要真实证书）
    try:
        config = create_ssl_server_config(
            host="localhost",
            port=18044,
            ssl_certfile="/path/to/your/server.crt",     # 需要替换为真实证书路径
            ssl_keyfile="/path/to/your/server.key",       # 需要替换为真实私钥路径
            on_auth_extract_user=lambda metadata: metadata.get("api_key", "ssl_user"),
            on_message=lambda msg, meta: logger.info(f"SSL服务器收到: {msg.message_segment.data}"),
        )

        server = WebSocketServer(config)
        await server.start()
        logger.info("✅ SSL服务器配置完成（需要真实证书文件才能启动）")

    except Exception as e:
        logger.error(f"❌ SSL服务器配置失败: {e}")


async def ssl_client_example():
    """SSL客户端示例"""
    print("🔗 启动SSL客户端示例...")

    try:
        # 创建SSL客户端配置
        config = create_ssl_client_config(
            url="wss://localhost:18044/ws",
            api_key="ssl_test_key",
            ssl_ca_certs="/path/to/your/ca.crt",  # 需要替换为真实CA证书路径
            ssl_verify=True,
            ssl_check_hostname=True,
            on_message=lambda msg, meta: logger.info(f"SSL客户端收到: {msg.message_segment.data}")
        )

        client = WebSocketClient(config)
        await client.start()
        logger.info("✅ SSL客户端配置完成（需要真实证书文件才能连接）")

    except Exception as e:
        logger.error(f"❌ SSL客户端配置失败: {e}")


def demonstrate_ssl_config():
    """演示SSL配置选项"""
    print("📋 SSL配置选项演示:")
    print("=" * 50)

    print("\n🔒 SSL服务器配置选项:")
    server_config = create_ssl_server_config(
        host="localhost",
        port=18044,
        ssl_certfile="/path/to/server.crt",
        ssl_keyfile="/path/to/server.key",
        ssl_ca_certs="/path/to/ca.crt",  # 可选
        ssl_verify=False,                  # 是否验证客户端证书
    )
    print(f"   SSL启用: {server_config.ssl_enabled}")
    print(f"   证书文件: {server_config.ssl_certfile}")
    print(f"   私钥文件: {server_config.ssl_keyfile}")
    print(f"   CA证书: {server_config.ssl_ca_certs}")
    print(f"   客户端验证: {server_config.ssl_verify}")

    print("\n🔗 SSL客户端配置选项:")
    client_config = create_ssl_client_config(
        url="wss://localhost:18044/ws",
        api_key="ssl_test_key",
        ssl_ca_certs="/path/to/ca.crt",     # 可选
        ssl_verify=True,                   # 验证服务器证书
        ssl_check_hostname=True,            # 检查主机名
        ssl_certfile="/path/to/client.crt",  # 客户端证书（双向认证）
        ssl_keyfile="/path/to/client.key"     # 客户端私钥（双向认证）
    )
    print(f"   SSL启用: {client_config.ssl_enabled}")
    print(f"   SSL验证: {client_config.ssl_verify}")
    print(f"   主机名检查: {client_config.ssl_check_hostname}")
    print(f"   CA证书: {client_config.ssl_ca_certs}")
    print(f"   客户端证书: {client_config.ssl_certfile}")
    print(f"   客户端私钥: {client_config.ssl_keyfile}")

    print("\n🔧 便捷SSL配置:")
    print("   create_ssl_server_config() - 专用于SSL服务器")
    print("   create_ssl_client_config() - 专用于SSL客户端")
    print("   自动检测协议: ws:// -> HTTP, wss:// -> HTTPS")


def show_ssl_benefits():
    """显示SSL/HTTPS的优势"""
    print("\n🛡️ SSL/TLS带来的安全优势:")
    print("=" * 50)
    print("🔐 数据加密:")
    print("   - 所有WebSocket通信都经过SSL/TLS加密")
    print("   - 防止中间人攻击和数据窃听")
    print("")
    print("🆔 身份验证:")
    print("   - 支持服务器和客户端证书验证")
    print("   - 双向认证（mutual TLS）")
    print("   - 确保通信端点身份真实性")
    print("")
    print("🔒 完整性保护:")
    print("   - 防止数据篡改")
    print("   - 消息完整性校验")
    print("")
    print("📊 合规性:")
    print("   - 满足现代安全标准")
    print("   - 支持企业级安全要求")


def show_ssl_cert_types():
    """显示不同类型的SSL证书"""
    print("\n📄 SSL证书类型:")
    print("=" * 50)
    print("🔑 自签名证书 (Self-Signed):")
    print("   - 用于开发和测试")
    print("   - 无需CA签名")
    print("   - 客户端需要手动信任")
    print("")
    print("🏢 CA签名证书 (CA-Signed):")
    print("   - 生产环境推荐")
    print("   - 由受信任的CA机构签发")
    print("   - 客户端自动信任")
    print("")
    print("🔄 证书链 (Certificate Chain):")
    print("   - 包含中间证书")
    print("   - 建立信任链路")
    print("   - 验证证书层次结构")


def main():
    """主函数"""
    print("🔒 API-Server Version SSL快速开始示例")
    print("=" * 60)

    # 1. 配置演示
    demonstrate_ssl_config()

    # 2. SSL优势说明
    show_ssl_benefits()

    # 3. 证书类型说明
    show_ssl_cert_types()

    print("\n📋 示例代码:")
    print("=" * 50)

    print("\n# 生成自签名证书（开发测试用）")
    print("```bash")
    print("# 生成私钥")
    print("openssl genrsa -out server.key 2048")
    print("")
    print("# 生成自签名证书")
    print("openssl req -new -x509 -key server.key -out server.crt \\")
    print("    -subj '/C=CN/ST=Beijing/L=Beijing/O=Test/CN=localhost' \\")
    print("    -days 365")
    print("```")

    print("\n# 基本SSL使用示例")
    print("```python")
    print("# 导入SSL相关函数")
    print("from maim_message.server import create_ssl_server_config")
    print("from maim_message.client import create_ssl_client_config")
    print("")
    print("# 创建SSL配置")
    print("server_config = create_ssl_server_config(")
    print("    host='localhost',")
    print("    port=18044,")
    print("    ssl_certfile='server.crt',")
    print("    ssl_keyfile='server.key'")
    print(")")
    print("")
    print("# 启动SSL服务器")
    print("server = WebSocketServer(server_config)")
    print("await server.start()")
    print("```")

    print("\n🔗 下一步:")
    print("=" * 50)
    print("1. 生成或获取SSL证书")
    print("2. 更新配置文件中的证书路径")
    print("3. 测试SSL连接")
    print("4. 部署到生产环境")

    print("\n📖 更多信息:")
    print("   - doc/api_server_usage_guide.md (完整SSL配置指南)")
    print("   - others/test_ssl_config.py (SSL配置测试)")
    print("   - others/test_ssl_websocket.py (完整SSL测试)")

    print("\n✅ SSL快速开始示例完成!")
    print("   📄 记住替换示例中的证书路径为真实路径")
    print("   🛡️ 生产环境务必使用CA签名证书")


if __name__ == "__main__":
    print("🔒 开始API-Server Version SSL快速开始示例...")
    main()