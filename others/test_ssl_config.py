"""
API-Server Version SSL配置测试脚本
测试SSL配置的功能，但不需要实际的SSL证书
主要用于验证配置创建、参数验证等功能
"""

import sys
import os
import asyncio
import logging
from typing import Dict, Any

# ✅ API-Server Version 正确导入方式
from maim_message.server import create_ssl_server_config, ServerConfig
from maim_message.client import create_ssl_client_config, ClientConfig
from maim_message.message import APIMessageBase, BaseMessageInfo, Seg, MessageDim

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class SSLConfigTester:
    """SSL配置测试类"""

    def __init__(self):
        self.test_results = {
            "ssl_server_config_created": False,
            "ssl_client_config_created": False,
            "ssl_parameters_valid": False,
            "ssl_defaults_applied": False,
            "errors": 0
        }

    def test_ssl_server_config_creation(self):
        """测试SSL服务器配置创建"""
        logger.info("🔧 测试SSL服务器配置创建...")

        try:
            # 测试完整SSL配置
            config = create_ssl_server_config(
                host="localhost",
                port=18086,
                ssl_certfile="/path/to/server.crt",
                ssl_keyfile="/path/to/server.key"
            )

            # 验证配置
            assert config.ssl_enabled == True, "SSL应该被启用"
            assert config.host == "localhost", "主机名应该正确"
            assert config.port == 18086, "端口应该正确"
            assert config.ssl_certfile == "/path/to/server.crt", "证书文件路径应该正确"
            assert config.ssl_keyfile == "/path/to/server.key", "私钥文件路径应该正确"

            logger.info("✅ 完整SSL服务器配置创建成功")
            logger.info(f"   SSL启用: {config.ssl_enabled}")
            logger.info(f"   主机: {config.host}")
            logger.info(f"   端口: {config.port}")
            logger.info(f"   证书文件: {config.ssl_certfile}")
            logger.info(f"   私钥文件: {config.ssl_keyfile}")

            self.test_results["ssl_server_config_created"] = True

        except Exception as e:
            logger.error(f"❌ SSL服务器配置创建失败: {e}")
            self.test_results["errors"] += 1

    def test_ssl_server_config_with_ca(self):
        """测试带CA证书的SSL服务器配置"""
        logger.info("🔧 测试带CA证书的SSL服务器配置...")

        try:
            config = create_ssl_server_config(
                host="0.0.0.0",
                port=18087,
                ssl_certfile="/path/to/server.crt",
                ssl_keyfile="/path/to/server.key",
                ssl_ca_certs="/path/to/ca.crt",
                ssl_verify=True,
                on_auth_extract_user=lambda meta: meta.get("api_key")
            )

            assert config.ssl_ca_certs == "/path/to/ca.crt", "CA证书路径应该正确"
            assert config.ssl_verify == True, "客户端证书验证应该启用"
            assert callable(config.on_auth_extract_user), "认证回调应该存在"

            logger.info("✅ 带CA证书的SSL服务器配置创建成功")
            logger.info(f"   CA证书: {config.ssl_ca_certs}")
            logger.info(f"   客户端证书验证: {config.ssl_verify}")

        except Exception as e:
            logger.error(f"❌ 带CA证书的SSL服务器配置创建失败: {e}")
            self.test_results["errors"] += 1

    def test_ssl_client_config_creation(self):
        """测试SSL客户端配置创建"""
        logger.info("🔧 测试SSL客户端配置创建...")

        try:
            # 测试完整URL的SSL客户端配置
            config = create_ssl_client_config(
                url="wss://secure.example.com:18088/ws",
                api_key="test_ssl_key",
                ssl_ca_certs="/path/to/ca.crt"
            )

            assert config.url == "wss://secure.example.com:18088/ws", "URL应该正确"
            assert config.api_key == "test_ssl_key", "API密钥应该正确"
            assert config.ssl_enabled == True, "SSL应该自动启用"
            assert config.ssl_ca_certs == "/path/to/ca.crt", "CA证书路径应该正确"
            assert config.ssl_verify == True, "SSL验证应该默认启用"

            logger.info("✅ SSL客户端配置创建成功")
            logger.info(f"   URL: {config.url}")
            logger.info(f"   API密钥: {config.api_key}")
            logger.info(f"   SSL启用: {config.ssl_enabled}")
            logger.info(f"   CA证书: {config.ssl_ca_certs}")
            logger.info(f"   SSL验证: {config.ssl_verify}")

            self.test_results["ssl_client_config_created"] = True

        except Exception as e:
            logger.error(f"❌ SSL客户端配置创建失败: {e}")
            self.test_results["errors"] += 1

    def test_ssl_client_config_params(self):
        """测试SSL客户端配置参数"""
        logger.info("🔧 测试SSL客户端配置参数...")

        try:
            config = create_ssl_client_config(
                host="localhost",
                port=18089,
                api_key="param_test_key",
                ssl_ca_certs="/path/to/ca.crt",
                ssl_certfile="/path/to/client.crt",
                ssl_keyfile="/path/to/client.key",
                ssl_verify=True,
                ssl_check_hostname=False
            )

            assert config.ssl_ca_certs == "/path/to/ca.crt", "CA证书应该正确"
            assert config.ssl_certfile == "/path/to/client.crt", "客户端证书应该正确"
            assert config.ssl_keyfile == "/path/to/client.key", "客户端私钥应该正确"
            assert config.ssl_verify == True, "SSL验证应该启用"
            assert config.ssl_check_hostname == False, "主机名检查应该禁用"

            logger.info("✅ SSL客户端配置参数测试通过")
            logger.info(f"   客户端证书: {config.ssl_certfile}")
            logger.info(f"   客户端私钥: {config.ssl_keyfile}")
            logger.info(f"   主机名检查: {config.ssl_check_hostname}")

            self.test_results["ssl_parameters_valid"] = True

        except Exception as e:
            logger.error(f"❌ SSL客户端配置参数测试失败: {e}")
            self.test_results["errors"] += 1

    def test_ssl_config_validation(self):
        """测试SSL配置验证"""
        logger.info("🔧 测试SSL配置验证...")

        try:
            # 测试SSL服务器配置验证
            config = ServerConfig(
                host="localhost",
                port=18090,
                ssl_enabled=True,
                ssl_certfile="/path/to/cert.pem",
                ssl_keyfile="/path/to/key.pem",
                on_auth_extract_user=lambda meta: meta.get("api_key", "unknown")
            )

            # 验证配置有效性
            is_valid = config.validate()
            if is_valid:
                logger.info("✅ SSL服务器配置验证通过")
                logger.info(f"   缺失字段: {config.get_missing_fields()}")
                self.test_results["ssl_defaults_applied"] = True
            else:
                missing_fields = config.get_missing_fields()
                logger.error(f"❌ SSL服务器配置验证失败，缺失字段: {missing_fields}")
                self.test_results["errors"] += 1

        except Exception as e:
            logger.error(f"❌ SSL配置验证失败: {e}")
            self.test_results["errors"] += 1

    def test_non_ssl_config(self):
        """测试非SSL配置仍然正常工作"""
        logger.info("🔧 测试非SSL配置兼容性...")

        try:
            # 测试非SSL配置
            from maim_message.server import create_server_config
            from maim_message.client import create_client_config

            # 服务器配置
            server_config = create_server_config(
                host="localhost",
                port=18091,
                on_auth_extract_user=lambda meta: meta.get("api_key")
            )
            assert not server_config.ssl_enabled, "非SSL配置的SSL应该禁用"
            assert server_config.host == "localhost", "非SSL配置的主机应该正确"

            # 客户端配置
            client_config = create_client_config(
                url="ws://localhost:18091/ws",
                api_key="test_non_ssl_key"
            )
            assert not client_config.ssl_enabled, "非SSL客户端的SSL应该禁用"
            assert client_config.url == "ws://localhost:18091/ws", "非SSL客户端的URL应该正确"

            logger.info("✅ 非SSL配置兼容性测试通过")
            logger.info(f"   服务器SSL状态: {server_config.ssl_enabled}")
            logger.info(f"   客户端SSL状态: {client_config.ssl_enabled}")

        except Exception as e:
            logger.error(f"❌ 非SSL配置兼容性测试失败: {e}")
            self.test_results["errors"] += 1

    def test_ssl_message_creation(self):
        """测试在SSL环境下的消息创建"""
        logger.info("🔧 测试SSL环境下的消息创建...")

        try:
            # 创建消息（SSL应该不影响消息格式）
            message = APIMessageBase(
                message_info=BaseMessageInfo(
                    platform="ssl_test",
                    message_id=f"ssl_msg_{int(asyncio.get_event_loop().time() * 1000)}",
                    time=asyncio.get_event_loop().time()
                ),
                message_segment=Seg(type="text", data="SSL环境测试消息"),
                message_dim=MessageDim(api_key="ssl_api_key", platform="ssl_test")
            )

            # 验证消息可以序列化
            message_dict = message.to_dict()
            assert "message_info" in message_dict, "消息应该包含message_info"
            assert "message_segment" in message_dict, "消息应该包含message_segment"
            assert "message_dim" in message_dict, "消息应该包含message_dim"

            logger.info("✅ SSL环境下的消息创建测试通过")
            logger.info(f"   消息ID: {message.message_info.message_id}")
            logger.info(f"   消息内容: {message.message_segment.data}")

        except Exception as e:
            logger.error(f"❌ SSL环境下的消息创建测试失败: {e}")
            self.test_results["errors"] += 1

    def print_test_results(self):
        """打印测试结果"""
        logger.info("=" * 60)
        logger.info("🔒 SSL配置测试完成!")
        logger.info("=" * 60)
        logger.info(f"✅ SSL服务器配置创建: {'成功' if self.test_results['ssl_server_config_created'] else '失败'}")
        logger.info(f"✅ SSL客户端配置创建: {'成功' if self.test_results['ssl_client_config_created'] else '失败'}")
        logger.info(f"✅ SSL参数验证: {'通过' if self.test_results['ssl_parameters_valid'] else '失败'}")
        logger.info(f"✅ SSL配置验证: {'通过' if self.test_results['ssl_defaults_applied'] else '失败'}")
        logger.info(f"❌ 错误数: {self.test_results['errors']}")
        logger.info("=" * 60)

        total_tests = len([k for k, v in self.test_results.items() if k != 'errors'])
        passed_tests = sum(1 for k, v in self.test_results.items() if v and k != 'errors')

        if self.test_results['errors'] == 0 and passed_tests == total_tests:
            logger.info("🎉 所有SSL配置测试通过！配置系统功能正常！")
        else:
            logger.warning(f"⚠️ SSL配置测试有问题: {passed_tests}/{total_tests} 通过, {self.test_results['errors']} 个错误")

    def run_tests(self):
        """运行所有测试"""
        logger.info("🔒 开始API-Server Version SSL配置测试")
        logger.info("=" * 60)

        # 运行各项测试
        self.test_ssl_server_config_creation()
        self.test_ssl_server_config_with_ca()
        self.test_ssl_client_config_creation()
        self.test_ssl_client_config_params()
        self.test_ssl_config_validation()
        self.test_non_ssl_config()
        self.test_ssl_message_creation()

        # 打印结果
        self.print_test_results()


def main():
    """主函数"""
    try:
        # 创建测试器
        tester = SSLConfigTester()

        # 运行测试
        tester.run_tests()

    except Exception as e:
        logger.error(f"❌ SSL配置测试失败: {e}")
        import traceback
        logger.error(f"   Traceback: {traceback.format_exc()}")
    finally:
        logger.info("🏁 SSL配置测试程序退出")


if __name__ == "__main__":
    print("🔒 开始API-Server Version SSL配置测试...")
    main()