"""
API-Server Version SSL WebSocket测试脚本
测试WebSocket的SSL/TLS功能，包括：
1. SSL服务器配置和启动
2. SSL客户端连接
3. 证书验证功能
4. 自签名证书测试
"""

import sys
import os
import asyncio
import logging
import time
import tempfile
import subprocess
from typing import Dict, Any

# ✅ API-Server Version 正确导入方式
from maim_message.server import WebSocketServer, create_ssl_server_config
from maim_message.client import WebSocketClient, create_ssl_client_config
from maim_message.message import APIMessageBase, BaseMessageInfo, Seg, MessageDim

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class SSLCertificateGenerator:
    """生成自签名SSL证书用于测试"""

    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        self.cert_file = os.path.join(self.temp_dir, "server_cert.pem")
        self.key_file = os.path.join(self.temp_dir, "server_key.pem")
        self.ca_file = os.path.join(self.temp_dir, "ca_cert.pem")

    def generate_self_signed_cert(self):
        """生成自签名证书"""
        try:
            # 生成私钥
            subprocess.run([
                "openssl", "genrsa", "-out", self.key_file, "2048"
            ], check=True, capture_output=True)

            # 创建证书签名请求配置
            csr_config = f"""[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
C = CN
ST = Beijing
L = Beijing
O = Test Organization
OU = Test Unit
CN = localhost

[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
DNS.2 = 127.0.0.1
IP.1 = 127.0.0.1
"""

            # 生成证书签名请求
            with open(os.path.join(self.temp_dir, "csr_config.cnf"), "w") as f:
                f.write(csr_config)

            subprocess.run([
                "openssl", "req", "-new", "-key", self.key_file,
                "-out", os.path.join(self.temp_dir, "server.csr"),
                "-config", os.path.join(self.temp_dir, "csr_config.cnf")
            ], check=True, capture_output=True)

            # 创建自签名证书
            subprocess.run([
                "openssl", "x509", "-req", "-days", "365",
                "-in", os.path.join(self.temp_dir, "server.csr"),
                "-signkey", self.key_file, "-out", self.cert_file,
                "-extensions", "v3_req", "-extfile", os.path.join(self.temp_dir, "csr_config.cnf")
            ], check=True, capture_output=True)

            # 将证书复制为CA证书（自签名情况）
            subprocess.run(["cp", self.cert_file, self.ca_file], check=True)

            logger.info(f"✅ SSL证书生成成功:")
            logger.info(f"   证书文件: {self.cert_file}")
            logger.info(f"   私钥文件: {self.key_file}")
            logger.info(f"   CA文件: {self.ca_file}")

            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"❌ 生成SSL证书失败: {e}")
            logger.error(f"   错误输出: {e.stderr.decode() if e.stderr else 'N/A'}")
            return False

    def cleanup(self):
        """清理临时文件"""
        import shutil
        try:
            shutil.rmtree(self.temp_dir)
            logger.info(f"✅ 清理临时SSL证书文件: {self.temp_dir}")
        except Exception as e:
            logger.warning(f"清理SSL证书文件时出错: {e}")


class SSLWebSocketTester:
    """SSL WebSocket测试类"""

    def __init__(self):
        self.server = None
        self.clients = []
        self.cert_generator = SSLCertificateGenerator()
        self.test_results = {
            "server_started": False,
            "client_connected": False,
            "messages_sent": 0,
            "messages_received": 0,
            "ssl_verified": False,
            "errors": 0
        }

    async def setup_ssl_certificates(self):
        """设置SSL证书"""
        logger.info("🔐 生成SSL证书用于测试...")
        return self.cert_generator.generate_self_signed_cert()

    async def create_ssl_server(self):
        """创建SSL WebSocket服务器"""
        try:
            # 创建SSL服务器配置
            config = create_ssl_server_config(
                host="localhost",
                port=18085,
                ssl_certfile=self.cert_generator.cert_file,
                ssl_keyfile=self.cert_generator.key_file,
                ssl_ca_certs=self.cert_generator.ca_file,
                ssl_verify=False  # 自签名证书不需要验证
            )

            # 设置认证和消息处理
            config.on_auth_extract_user = lambda metadata: f"ssl_user_{metadata.get('api_key', 'unknown')}"
            config.on_message = self._handle_message
            config.on_connect = self._handle_connect
            config.on_disconnect = self._handle_disconnect

            # 创建服务器
            self.server = WebSocketServer(config)
            logger.info("✅ SSL服务器配置完成")
            return True

        except Exception as e:
            logger.error(f"❌ 创建SSL服务器失败: {e}")
            return False

    async def create_ssl_client(self, verify_cert: bool = True) -> WebSocketClient:
        """创建SSL WebSocket客户端"""
        try:
            # 创建SSL客户端配置
            config = create_ssl_client_config(
                url="wss://localhost:18085/ws",
                api_key="ssl_test_key",
                ssl_ca_certs=self.cert_generator.ca_file if verify_cert else None,
                ssl_verify=verify_cert,
                ssl_check_hostname=False  # 自签名证书不需要检查主机名
            )

            # 设置客户端回调
            config.on_connect = self._client_on_connect
            config.on_disconnect = self._client_on_disconnect
            config.on_message = self._client_on_message

            # 创建客户端
            client = WebSocketClient(config)
            return client

        except Exception as e:
            logger.error(f"❌ 创建SSL客户端失败: {e}")
            return None

    async def _handle_connect(self, connection_uuid: str, metadata: Dict[str, Any]):
        """服务器连接回调"""
        logger.info(f"🔗 SSL客户端连接: {connection_uuid}")
        self.test_results["client_connected"] = True

    async def _handle_disconnect(self, connection_uuid: str, metadata: Dict[str, Any]):
        """服务器断开连接回调"""
        logger.info(f"🔌 SSL客户端断开: {connection_uuid}")

    async def _handle_message(self, message: APIMessageBase, metadata: Dict[str, Any]):
        """服务器收到消息回调"""
        self.test_results["messages_received"] += 1
        logger.info(f"📨 SSL服务器收到消息: {message.message_segment.data}")

        # 发送确认消息
        response = APIMessageBase(
            message_info=BaseMessageInfo(
                platform="ssl_server",
                message_id=f"ssl_response_{int(time.time() * 1000)}",
                time=time.time()
            ),
            message_segment=Seg(type="text", data=f"SSL服务器确认收到: {message.message_segment.data}"),
            message_dim=MessageDim(api_key="ssl_server", platform="ssl_server")
        )

        # 发送响应给原发送者
        user_id = metadata.get("user_id", "unknown")
        if user_id != "unknown":
            await self.server.send_message(user_id, response)

    async def _client_on_connect(self, connection_uuid: str, config: Dict[str, Any]):
        """客户端连接回调"""
        logger.info(f"✅ SSL客户端连接成功: {connection_uuid}")
        self.test_results["ssl_verified"] = True

    async def _client_on_disconnect(self, connection_uuid: str, error: str = None):
        """客户端断开连接回调"""
        if error:
            logger.error(f"❌ SSL客户端断开: {connection_uuid} - {error}")
        else:
            logger.info(f"🔌 SSL客户端断开: {connection_uuid}")

    async def _client_on_message(self, server_message: APIMessageBase, metadata: Dict[str, Any]):
        """客户端收到消息回调"""
        self.test_results["messages_received"] += 1
        logger.info(f"📤 SSL客户端收到: {server_message.message_segment.data}")

    async def test_ssl_server_start(self):
        """测试SSL服务器启动"""
        logger.info("🚀 测试SSL服务器启动...")
        try:
            await self.server.start()
            self.test_results["server_started"] = True
            logger.info("✅ SSL服务器启动成功")
            await asyncio.sleep(1)  # 等待服务器完全启动
            return True
        except Exception as e:
            logger.error(f"❌ SSL服务器启动失败: {e}")
            self.test_results["errors"] += 1
            return False

    async def test_ssl_client_connection(self):
        """测试SSL客户端连接"""
        logger.info("🔗 测试SSL客户端连接...")

        # 测试带证书验证的客户端
        client_with_verify = await self.create_ssl_client(verify_cert=True)
        if client_with_verify is None:
            return False

        try:
            await client_with_verify.start()
            connected = await client_with_verify.connect()

            if connected:
                logger.info("✅ SSL客户端连接成功（带证书验证）")
                self.clients.append(client_with_verify)
                return True
            else:
                logger.error("❌ SSL客户端连接失败")
                self.test_results["errors"] += 1
                await client_with_verify.stop()
                return False

        except Exception as e:
            logger.error(f"❌ SSL客户端连接异常: {e}")
            self.test_results["errors"] += 1
            await client_with_verify.stop()
            return False

    async def test_ssl_messaging(self):
        """测试SSL消息发送"""
        logger.info("💬 测试SSL消息发送...")

        if not self.clients:
            logger.error("❌ 没有可用的SSL客户端")
            return False

        try:
            client = self.clients[0]

            # 发送测试消息
            test_messages = [
                "Hello over SSL! 🛡️",
                "SSL WebSocket测试消息",
                "加密通信验证 🔒"
            ]

            for i, content in enumerate(test_messages, 1):
                message = APIMessageBase(
                    message_info=BaseMessageInfo(
                        platform="ssl_test",
                        message_id=f"ssl_msg_{i}_{int(time.time() * 1000)}",
                        time=time.time()
                    ),
                    message_segment=Seg(type="text", data=content),
                    message_dim=MessageDim(api_key="ssl_test_key", platform="ssl_test")
                )

                success = await client.send_message(message)
                if success:
                    self.test_results["messages_sent"] += 1
                    logger.info(f"✅ SSL消息{i}发送成功: {content}")
                else:
                    logger.error(f"❌ SSL消息{i}发送失败")
                    self.test_results["errors"] += 1

                await asyncio.sleep(0.5)  # 间隔发送

            return self.test_results["messages_sent"] > 0

        except Exception as e:
            logger.error(f"❌ SSL消息测试失败: {e}")
            self.test_results["errors"] += 1
            return False

    async def cleanup(self):
        """清理资源"""
        logger.info("🧹 清理SSL测试资源...")

        # 停止所有客户端
        for i, client in enumerate(self.clients, 1):
            try:
                await client.disconnect()
                await client.stop()
                logger.info(f"✅ SSL客户端{i} 已停止")
            except Exception as e:
                logger.error(f"❌ SSL客户端{i}停止时出错: {e}")

        # 停止服务器
        if self.server:
            try:
                await self.server.stop()
                logger.info("✅ SSL服务器已停止")
            except Exception as e:
                logger.error(f"❌ SSL服务器停止时出错: {e}")

        # 清理SSL证书
        self.cert_generator.cleanup()

    def print_test_results(self):
        """打印测试结果"""
        logger.info("=" * 60)
        logger.info("🔒 SSL WebSocket测试完成!")
        logger.info("=" * 60)
        logger.info(f"✅ 服务器启动: {'成功' if self.test_results['server_started'] else '失败'}")
        logger.info(f"✅ 客户端连接: {'成功' if self.test_results['client_connected'] else '失败'}")
        logger.info(f"✅ SSL验证: {'通过' if self.test_results['ssl_verified'] else '失败'}")
        logger.info(f"📤 发送消息数: {self.test_results['messages_sent']}")
        logger.info(f"📨 接收消息数: {self.test_results['messages_received']}")
        logger.info(f"❌ 错误数: {self.test_results['errors']}")
        logger.info("=" * 60)

        if (self.test_results['server_started'] and
            self.test_results['client_connected'] and
            self.test_results['ssl_verified'] and
            self.test_results['errors'] == 0):
            logger.info("🎉 所有SSL测试通过！WebSocket SSL/TLS功能正常！")
        else:
            logger.warning("⚠️ SSL测试存在问题，请检查日志")

    async def run_tests(self):
        """运行所有SSL测试"""
        try:
            # 1. 生成SSL证书
            if not await self.setup_ssl_certificates():
                return

            # 2. 创建SSL服务器
            if not await self.create_ssl_server():
                return

            # 3. 启动SSL服务器
            if not await self.test_ssl_server_start():
                return

            # 4. 测试SSL客户端连接
            if not await self.test_ssl_client_connection():
                return

            # 5. 等待连接稳定
            await asyncio.sleep(1)

            # 6. 测试SSL消息发送
            if await self.test_ssl_messaging():
                await asyncio.sleep(1)  # 等待消息处理完成

        except Exception as e:
            logger.error(f"❌ SSL测试运行错误: {e}")
            self.test_results["errors"] += 1

        finally:
            await asyncio.sleep(1)  # 等待清理完成
            await self.cleanup()


async def main():
    """主函数"""
    logger.info("🔒 开始API-Server Version SSL WebSocket测试")
    logger.info("=" * 60)

    try:
        # 创建测试器
        tester = SSLWebSocketTester()

        # 设置30秒超时
        await asyncio.wait_for(tester.run_tests(), timeout=30.0)

        # 打印测试结果
        tester.print_test_results()

    except asyncio.TimeoutError:
        logger.warning("⏰ SSL测试超时")
    except Exception as e:
        logger.error(f"❌ SSL测试失败: {e}")
        import traceback
        logger.error(f"   Traceback: {traceback.format_exc()}")
    finally:
        logger.info("🏁 SSL测试程序退出")


if __name__ == "__main__":
    print("🔒 开始API-Server Version SSL WebSocket功能测试...")
    asyncio.run(main())