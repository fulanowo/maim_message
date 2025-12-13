# API-Server 版本测试说明 (test_api_server_complete.py)

本目录包含了 API-Server 版本的完整测试文件 `test_api_server_complete.py`。
此测试取代了旧的测试脚本，涵盖了完整的 API 服务器功能验证。

## 运行测试

### 方法1：直接运行
```bash
cd others
python test_api_server_complete.py
```

### 方法2：从项目根目录运行
```bash
python others/test_api_server_complete.py
```

### 方法3：使用模块方式
```bash
python -m others.test_api_server_complete
```

## 测试内容

`test_api_server_complete.py` 是一个完整的集成测试，覆盖：

1. **服务端功能测试**
   - 服务器启动和配置
   - 关键回调：on_auth, on_auth_extract_user, on_message
   - 自定义消息处理器
   - **异步任务执行模式验证**

2. **客户端功能测试**
   - 单连接客户端 (WebSocketClient)
   - 多连接客户端 (WebSocketMultiClient)
   - 消息发送和接收
   - **客户端异步任务处理**

3. **配置系统测试**
   - 服务器配置创建
   - 客户端配置创建
   - 多连接配置管理

4. **完整消息构建测试**
   - APIMessageBase 对象创建
   - 消息路由测试

5. **异步任务特性测试**
   - 非阻塞消息处理验证
   - 并发handler执行测试
   - 任务生命周期管理
   - 资源清理完整性验证

## 测试结果

### 成功运行的标志
正常情况下应该看到：
```
🎉 API-Server Version 完整测试完成!
✅ 所有测试通过，API-Server Version 运行正常!
🏁 测试程序退出，退出码: 0
错误率: 0.00%
```

### 异步任务特性验证
测试过程中会验证以下异步任务特性：

1. **任务创建日志**（如果启用DEBUG日志）：
   ```
   🚀 Handler task 1 (标准消息处理器-wechat) 已创建，当前活跃任务数: 1
   🚀 Handler task 2 (自定义消息处理器-custom_ping) 已创建，当前活跃任务数: 2
   ```

2. **任务完成日志**：
   ```
   ✅ Handler task 1 (标准消息处理器-wechat) 完成
   ✅ Handler task 2 (自定义消息处理器-custom_ping) 完成
   ```

3. **任务清理日志**：
   ```
   正在清理 X 个handler任务...
   正在清理 X 个客户端handler任务...
   ```

4. **统计信息中的任务计数**：
   ```
   活跃任务数: 0  # 停止后应该为0
   ```

### 性能表现
- **并发处理**: 多个消息可以同时被处理，不会串行等待
- **非阻塞**: 事件分发器不会被单个消息处理器阻塞
- **资源管理**: 所有异步任务在停止时都能正确清理

## 注意事项

- 测试使用 `localhost:18080` 端口
- 测试有30秒超时保护
- 测试会自动清理资源，包括所有异步任务
- 如需查看异步任务的详细日志，可以将日志级别设置为DEBUG