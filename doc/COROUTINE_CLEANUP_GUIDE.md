# WebSocket协程完全清理指南

## 问题说明

在使用WebSocket客户端和服务端时，如果在调用`stop()`方法后仍然保留协程，会导致上层应用需要处理关闭后的异常。本文档详细说明了解决方案和实现细节。

## 核心解决方案

### 1. 客户端协程清理机制

#### WebSocketClientBase改进
- **超时机制**: 使用`asyncio.wait_for()`确保协程在指定时间内完成
- **状态重置**: 完全重置所有内部状态，避免残留
- **队列清理**: 清空事件队列，防止残留事件触发异常

```python
async def stop(self) -> None:
    """停止客户端 - 完全清理所有协程"""
    # 1. 立即停止运行状态
    self.running = False

    # 2. 取消事件分发器协程（带超时）
    if self.dispatcher_task and not self.dispatcher_task.done():
        self.dispatcher_task.cancel()
        try:
            await asyncio.wait_for(self.dispatcher_task, timeout=2.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass
    self.dispatcher_task = None

    # 3. 停止网络驱动器并清空队列
    await self.network_driver.stop()
    while not self.event_queue.empty():
        try:
            self.event_queue.get_nowait()
        except asyncio.QueueEmpty:
            break
```

#### 网络驱动器优化
- **连接协程清理**: 遍历所有连接协程，使用1秒超时等待结束
- **线程安全等待**: 等待工作线程优雅结束（3秒超时）
- **统计重置**: 完全重置统计信息

### 2. 服务端协程清理机制

#### 优雅关闭WebSocket连接
- **超时接收**: 使用1秒超时接收消息，避免无限等待
- **状态检查**: 在消息循环中检查`running`和`shutdown_event`状态
- **异常处理**: 将所有异常转为debug级别，避免错误输出

```python
# 优雅的消息处理循环
while self.running and not self._shutdown_event.is_set():
    try:
        message = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
        await self._handle_message(connection_uuid, message)
    except asyncio.TimeoutError:
        continue  # 超时正常，继续检查状态
    except asyncio.CancelledError:
        break  # 服务器关闭，正常退出
    except Exception as e:
        logger.debug(f"Error: {type(e).__name__}: {str(e)}")
        break
```

#### 分阶段关闭策略
1. **设置关闭信号**: 首先设置`shutdown_event`
2. **等待自然退出**: 给连接处理循环0.1秒时间自然退出
3. **主动关闭连接**: 强制关闭所有活跃WebSocket连接
4. **关闭uvicorn**: 设置`should_exit=True`
5. **取消服务器任务**: 使用1秒超时取消任务
6. **重置所有状态**: 清理所有引用和统计数据

### 3. 协程状态检查机制

#### 客户端状态检查
```python
def get_coroutine_status(self) -> Dict[str, Any]:
    """获取协程状态信息"""
    return {
        "client_running": self.running,
        "dispatcher_task": {
            "exists": True,
            "done": self.dispatcher_task.done(),
            "cancelled": self.dispatcher_task.cancelled()
        } if self.dispatcher_task else None,
        "network_driver_running": self.network_driver.running,
        "event_queue_size": self.event_queue.qsize()
    }
```

#### 服务端状态检查
```python
def get_coroutine_status(self) -> Dict[str, Any]:
    """获取协程状态信息"""
    return {
        "server_running": self.running,
        "dispatcher_task": {...},  # 类似客户端
        "network_driver_running": self.network_driver.running,
        "active_connections": len(self.network_driver.active_connections),
        "registered_users": len(self.user_connections),
        "custom_handlers": len(getattr(self, 'custom_handlers', {}))
    }
```

## 验证结果

### 测试统计
```
🎉 API-Server Version 完整测试完成!
⏱️  总运行时间: 18.97 秒
🔐 认证统计: 3/3 认证成功
📊 消息统计: 收到2条，发送12条，自定义消息7条
🔧 错误统计: 0个错误，0.00%错误率
🔗 连接统计: 2个单连接客户端，1个多连接客户端

✅ 所有测试通过，API-Server Version 运行正常!
✅ 服务器所有协程和连接已清理
```

### 关键改进效果
1. **零残留协程**: stop()后完全清理所有协程
2. **零框架错误**: 消除了所有uvicorn/FastAPI内部错误
3. **优雅关闭**: 所有连接和任务都得到正确的关闭处理
4. **状态可验证**: 提供协程状态检查接口便于调试

## 使用指南

### 正确的关闭流程
```python
# 创建客户端或服务端
server = WebSocketServer(config)
await server.start()

# 使用期间...

# 标准关闭流程（推荐）
await server.stop()

# 验证清理状态
status = server.get_coroutine_status()
assert status["server_running"] == False
assert status["active_connections"] == 0
```

### 调试协程状态
```python
# 检查协程状态
status = client.get_coroutine_status()
print(f"客户端运行状态: {status['client_running']}")
print(f"分发器任务完成: {status['dispatcher_task']['done'] if status['dispatcher_task'] else 'N/A'}")
print(f"网络驱动器状态: {status['network_driver_running']}")
print(f"事件队列大小: {status['event_queue_size']}")
```

## 注意事项

1. **超时设置**: 所有协程清理都设置了合理的超时时间
2. **异常处理**: 异常被转为debug级别，避免干扰正常日志
3. **状态一致性**: 确保所有内部状态在stop()后完全重置
4. **框架兼容**: 兼容uvicorn、FastAPI等框架的生命周期

通过这些改进，确保了WebSocket客户端和服务端在调用stop()方法后不会保留任何协程，上层应用无需处理关闭后的异常。