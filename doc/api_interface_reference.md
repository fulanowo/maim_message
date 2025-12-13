# API-Server Version 对外接口文档

## 概述

本文档详细列出了 maim_message API-Server Version 的所有对外暴露接口，包括服务端、单连接客户端和多连接客户端的所有公共方法和属性。

## 服务端 (WebSocketServer)

### 构造函数

```python
WebSocketServer(config: Optional[ServerConfig] = None)
```

- `config`: 可选的服务端配置，如果不提供则使用默认配置

### 核心方法 (14个公共方法)

#### 生命周期管理 (2个方法)

| 方法      | 参数 | 返回值 | 说明                     |
| --------- | ---- | ------ | ------------------------ |
| `start()` | 无   | `None` | 启动服务器，开始监听连接 |
| `stop()`  | 无   | `None` | 停止服务器，关闭所有连接 |

#### 消息发送 (2个方法)

| 方法                                                                                                                                                                               | 参数                                                                                                                                                       | 返回值            | 说明                       |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------- | -------------------------- |
| `send_message(message: APIMessageBase)`                                                                                                                                            | `message`: 标准消息                                                                                                                                        | `Dict[str, bool]` | 发送标准消息到目标客户端   |
| `send_custom_message(message_type: str, payload: Dict[str, Any], target_user: Optional[str] = None, target_platform: Optional[str] = None, connection_uuid: Optional[str] = None)` | `message_type`: 消息类型<br>`payload`: 消息载荷<br>`target_user`: 可选的目标用户<br>`target_platform`: 可选的目标平台<br>`connection_uuid`: 可选的连接UUID | `Dict[str, bool]` | 发送自定义消息到目标客户端 |

#### 用户和连接管理 (5个方法)

| 方法                                                    | 参数                                      | 返回值                     | 说明                                 |
| ------------------------------------------------------- | ----------------------------------------- | -------------------------- | ------------------------------------ |
| `get_user_count()`                                      | 无                                        | `int`                      | 获取当前连接的用户总数               |
| `get_user_connections(user_id: str)`                    | `user_id`: 用户ID                         | `Set[str]`                 | 获取指定用户的所有连接UUID           |
| `get_platform_connections(user_id: str, platform: str)` | `user_id`: 用户ID<br>`platform`: 平台标识 | `Set[str]`                 | 获取指定用户在指定平台的所有连接UUID |
| `get_connection_info(connection_uuid: str)`             | `connection_uuid`: 连接UUID               | `Optional[Dict[str, str]]` | 获取连接对应的用户ID和平台信息       |
| `get_connection_count()`                                | 无                                        | `int`                      | 获取当前连接数                       |
| `get_coroutine_status()`                                | 无                                        | `Dict[str, Any]`           | 获取协程状态信息                     |

#### 配置和处理器管理 (3个方法)

| 方法                                                            | 参数                                            | 返回值 | 说明                 |
| --------------------------------------------------------------- | ----------------------------------------------- | ------ | -------------------- |
| `update_config(**kwargs)`                                       | `kwargs`: 配置键值对                            | `None` | 动态更新服务端配置   |
| `register_custom_handler(message_type: str, handler: Callable)` | `message_type`: 消息类型<br>`handler`: 处理函数 | `None` | 注册自定义消息处理器 |
| `unregister_custom_handler(message_type: str)`                  | `message_type`: 消息类型                        | `None` | 注销自定义消息处理器 |

#### 统计信息 (1个方法)

| 方法          | 参数 | 返回值           | 说明                   |
| ------------- | ---- | ---------------- | ---------------------- |
| `get_stats()` | 无   | `Dict[str, Any]` | 获取服务器运行统计信息 |

### 配置类 (ServerConfig)

#### 所有配置字段

| 字段名                  | 类型                                                         | 默认值      | 必填                   | 说明                     |
| ----------------------- | ------------------------------------------------------------ | ----------- | ---------------------- | ------------------------ |
| **基础网络配置**        |                                                              |             |                        |                          |
| `host`                  | `str`                                                        | `"0.0.0.0"` | 否                     | 监听地址                 |
| `port`                  | `int`                                                        | `18000`     | 否                     | 监听端口                 |
| `path`                  | `str`                                                        | `"/ws"`     | 否                     | WebSocket路径            |
| **SSL/TLS配置**         |                                                              |             |                        |                          |
| `ssl_enabled`           | `bool`                                                       | `False`     | 否                     | 是否启用SSL              |
| `ssl_certfile`          | `Optional[str]`                                              | `None`      | ssl_enabled=True时必填 | SSL证书文件路径          |
| `ssl_keyfile`           | `Optional[str]`                                              | `None`      | ssl_enabled=True时必填 | SSL私钥文件路径          |
| `ssl_ca_certs`          | `Optional[str]`                                              | `None`      | 否                     | CA证书文件路径           |
| `ssl_verify`            | `bool`                                                       | `False`     | 否                     | 是否验证客户端证书       |
| **核心回调函数**        |                                                              |             |                        |                          |
| `on_auth`               | `Optional[Callable[[Dict[str, Any]], bool]]`                 | `None`      | 推荐                   | API Key认证回调          |
| `on_auth_extract_user`  | `Optional[Callable[[Dict[str, Any]], str]]`                  | `None`      | 必填                   | 用户标识提取回调         |
| `on_message`            | `Optional[Callable[[APIMessageBase, Dict[str, Any]], None]]` | `None`      | 推荐                   | 标准消息处理回调         |
| **自定义消息处理器**    |                                                              |             |                        |                          |
| `custom_handlers`       | `Dict[str, Callable[[Dict[str, Any]], None]]`                | `{}`        | 否                     | 自定义消息类型处理器字典 |
| **统计信息配置**        |                                                              |             |                        |                          |
| `enable_stats`          | `bool`                                                       | `True`      | 否                     | 是否启用统计信息收集     |
| `stats_callback`        | `Optional[Callable[[Dict[str, Any]], None]]`                 | `None`      | 否                     | 统计信息回调函数         |
| **日志配置**            |                                                              |             |                        |                          |
| `log_level`             | `str`                                                        | `"INFO"`    | 否                     | 日志级别                 |
| `enable_connection_log` | `bool`                                                       | `True`      | 否                     | 是否启用连接日志         |
| `enable_message_log`    | `bool`                                                       | `True`      | 否                     | 是否启用消息日志         |

#### 便捷函数

| 函数                                                                                            | 参数                                                                                                                                                                                                                                                                        | 返回值         | 说明               |
| ----------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------- | ------------------ |
| `create_server_config(**kwargs)`                                                                | `host`: 监听地址 (默认: "0.0.0.0")<br>`port`: 监听端口 (默认: 18000)<br>`path`: WebSocket路径 (默认: "/ws")<br>`ssl_enabled`: 是否启用SSL<br>`on_auth`: API Key认证回调<br>`on_auth_extract_user`: 用户标识提取回调<br>`on_message`: 消息处理回调<br>`kwargs`: 其他配置参数 | `ServerConfig` | 创建标准服务器配置 |
| `create_ssl_server_config(host: str, port: int, ssl_certfile: str, ssl_keyfile: str, **kwargs)` | `host`: 监听地址<br>`port`: 监听端口<br>`ssl_certfile`: SSL证书文件<br>`ssl_keyfile`: SSL私钥文件<br>`kwargs`: 其他配置参数，包括回调函数                                                                                                                                   | `ServerConfig` | 创建SSL服务器配置  |

---

## 单连接客户端 (WebSocketClient)

### 构造函数

```python
WebSocketClient(config: ClientConfig)
```

- `config`: 客户端配置（必需）

### 核心方法 (15个公共方法)

#### 生命周期管理 (6个方法)

| 方法                     | 参数 | 返回值           | 说明                   |
| ------------------------ | ---- | ---------------- | ---------------------- |
| `start()`                | 无   | `None`           | 启动客户端             |
| `stop()`                 | 无   | `None`           | 停止客户端             |
| `connect()`              | 无   | `bool`           | 连接到服务器           |
| `disconnect()`           | 无   | `bool`           | 断开与服务器的连接     |
| `is_running()`           | 无   | `bool`           | 检查客户端是否在运行   |
| `is_connected()`         | 无   | `bool`           | 检查是否已连接到服务器 |
| `get_coroutine_status()` | 无   | `Dict[str, Any]` | 获取协程状态信息       |

#### 消息发送 (2个方法)

| 方法                                                              | 参数                                            | 返回值 | 说明                                 |
| ----------------------------------------------------------------- | ----------------------------------------------- | ------ | ------------------------------------ |
| `send_message(message: APIMessageBase)`                           | `message`: 标准消息                             | `bool` | 发送标准消息（使用缓存的连接参数）   |
| `send_custom_message(message_type: str, payload: Dict[str, Any])` | `message_type`: 消息类型<br>`payload`: 消息载荷 | `bool` | 发送自定义消息（使用缓存的连接参数） |

#### 配置和处理器管理 (3个方法)

| 方法                                                            | 参数                                            | 返回值 | 说明                 |
| --------------------------------------------------------------- | ----------------------------------------------- | ------ | -------------------- |
| `update_config(**kwargs)`                                       | `kwargs`: 配置键值对                            | `None` | 动态更新客户端配置   |
| `register_custom_handler(message_type: str, handler: Callable)` | `message_type`: 消息类型<br>`handler`: 处理函数 | `None` | 注册自定义消息处理器 |
| `unregister_custom_handler(message_type: str)`                  | `message_type`: 消息类型                        | `None` | 注销自定义消息处理器 |

#### 连接信息 (3个方法)

| 方法                           | 参数 | 返回值           | 说明               |
| ------------------------------ | ---- | ---------------- | ------------------ |
| `get_cached_connection_info()` | 无   | `Dict[str, str]` | 获取缓存的连接信息 |
| `get_connection_uuid()`        | 无   | `Optional[str]`  | 获取连接UUID       |
| `get_last_error()`             | 无   | `Optional[str]`  | 获取最后的错误信息 |

#### 统计信息 (1个方法)

| 方法          | 参数 | 返回值           | 说明                   |
| ------------- | ---- | ---------------- | ---------------------- |
| `get_stats()` | 无   | `Dict[str, Any]` | 获取客户端运行统计信息 |

### 配置类 (ClientConfig)

#### 所有配置字段

| 字段名                   | 类型                                                         | 默认值      | 必填 | 说明                                       |
| ------------------------ | ------------------------------------------------------------ | ----------- | ---- | ------------------------------------------ |
| **基础连接配置**         |                                                              |             |      |                                            |
| `url`                    | `str`                                                        | 无          | 必填 | WebSocket服务器URL                         |
| `api_key`                | `str`                                                        | 无          | 必填 | API密钥                                    |
| `platform`               | `str`                                                        | `"default"` | 否   | 平台标识                                   |
| `connection_uuid`        | `Optional[str]`                                              | `None`      | 否   | 连接UUID（通常自动生成）                   |
| **SSL/TLS配置**          |                                                              |             |      |                                            |
| `ssl_enabled`            | `bool`                                                       | `False`     | 否   | 是否启用SSL（自动从URL检测）               |
| `ssl_verify`             | `bool`                                                       | `True`      | 否   | 是否验证SSL证书                            |
| `ssl_ca_certs`           | `Optional[str]`                                              | `None`      | 否   | CA证书文件路径                             |
| `ssl_certfile`           | `Optional[str]`                                              | `None`      | 否   | 客户端证书文件路径                         |
| `ssl_keyfile`            | `Optional[str]`                                              | `None`      | 否   | 客户端私钥文件路径                         |
| `ssl_check_hostname`     | `bool`                                                       | `True`      | 否   | 是否检查主机名                             |
| **重连配置**             |                                                              |             |      |                                            |
| `auto_reconnect`         | `bool`                                                       | `True`      | 否   | 是否自动重连                               |
| `max_reconnect_attempts` | `int`                                                        | `5`         | 否   | 最大重连尝试次数                           |
| `reconnect_delay`        | `float`                                                      | `1.0`       | 否   | 重连延迟（秒）                             |
| `max_reconnect_delay`    | `float`                                                      | `30.0`      | 否   | 最大重连延迟（秒）                         |
| **心跳配置**             |                                                              |             |      |                                            |
| `ping_interval`          | `int`                                                        | `20`        | 否   | ping间隔（秒）                             |
| `ping_timeout`           | `int`                                                        | `10`        | 否   | ping超时（秒）                             |
| `close_timeout`          | `int`                                                        | `10`        | 否   | 关闭超时（秒）                             |
| **回调函数配置**         |                                                              |             |      |                                            |
| `on_message`             | `Optional[Callable[[APIMessageBase, Dict[str, Any]], None]]` | `None`      | 推荐 | 标准消息处理回调                           |
| **自定义消息处理器**     |                                                              |             |      |                                            |
| `custom_handlers`        | `Dict[str, Callable[[Dict[str, Any]], None]]`                | `{}`        | 否   | 自定义消息类型处理器字典                   |
| **统计信息配置**         |                                                              |             |      |                                            |
| `enable_stats`           | `bool`                                                       | `True`      | 否   | 是否启用统计信息收集                       |
| `stats_callback`         | `Optional[Callable[[Dict[str, Any]], None]]`                 | `None`      | 否   | 统计信息回调函数                           |
| **日志配置**             |                                                              |             |      |                                            |
| `log_level`              | `str`                                                        | `"INFO"`    | 否   | 日志级别                                   |
| `enable_connection_log`  | `bool`                                                       | `True`      | 否   | 是否启用连接日志                           |
| `enable_message_log`     | `bool`                                                       | `True`      | 否   | 是否启用消息日志                           |
| **HTTP配置**             |                                                              |             |      |                                            |
| `headers`                | `Dict[str, str]`                                             | `{}`        | 否   | HTTP请求头（自动添加x-apikey和x-platform） |

#### 便捷函数

| 函数                                                         | 参数                                                                                                                                                                                                                                                            | 返回值         | 说明               |
| ------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------- | ------------------ |
| `create_client_config(url: str, api_key: str, **kwargs)`     | `url`: WebSocket服务器URL<br>`api_key`: API密钥<br>`platform`: 平台标识 (默认: "default")<br>`on_message`: 消息处理回调函数 (重要)<br>`auto_reconnect`: 是否自动重连 (默认: True)<br>`max_reconnect_attempts`: 最大重连次数 (默认: 5)<br>`kwargs`: 其他配置参数 | `ClientConfig` | 创建标准客户端配置 |
| `create_ssl_client_config(url: str, api_key: str, **kwargs)` | `url`: WebSocket服务器URL (使用wss://)<br>`api_key`: API密钥<br>`platform`: 平台标识 (默认: "default")<br>`on_message`: 消息处理回调函数 (重要)<br>`ssl_ca_certs`: CA证书文件路径 (推荐)<br>`kwargs`: 其他SSL和客户端配置参数                                   | `ClientConfig` | 创建SSL客户端配置  |

---

## 多连接客户端 (WebSocketMultiClient)

### 构造函数

```python
WebSocketMultiClient(config: Optional[MultiClientConfig] = None)
```

- `config`: 多连接客户端配置对象，如果为None则使用空配置

### 配置方式

多连接客户端使用MultiClientConfig配置类：

#### MultiClientConfig配置类

| 字段名                  | 类型                         | 默认值   | 必填 | 说明                             |
| ----------------------- | ---------------------------- | -------- | ---- | -------------------------------- |
| **连接配置**            |                              |          |      |                                  |
| `connections`           | `Dict[str, ConnectionEntry]` | `{}`     | 否   | 连接字典，键为连接名称           |
| **回调函数配置**        |                              |          |      |                                  |
| `on_message`            | `Optional[Callable]`         | `None`   | 否   | 消息处理回调函数                 |
| `custom_handlers`       | `Dict[str, Callable]`        | `{}`     | 否   | 自定义消息处理器字典             |
| **全局设置**            |                              |          |      |                                  |
| `auto_connect_on_start` | `bool`                       | `False`  | 否   | 启动时是否自动连接所有注册的连接 |
| `connect_timeout`       | `float`                      | `10.0`   | 否   | 连接超时时间                     |
| **统计信息配置**        |                              |          |      |                                  |
| `enable_stats`          | `bool`                       | `True`   | 否   | 是否启用统计信息收集             |
| `stats_callback`        | `Optional[Callable]`         | `None`   | 否   | 统计信息回调函数                 |
| **日志配置**            |                              |          |      |                                  |
| `log_level`             | `str`                        | `"INFO"` | 否   | 日志级别                         |
| `enable_connection_log` | `bool`                       | `True`   | 否   | 是否启用连接日志                 |
| `enable_message_log`    | `bool`                       | `True`   | 否   | 是否启用消息日志                 |

**ConnectionEntry连接条目类**:

| 字段名                   | 类型             | 默认值      | 说明               |
| ------------------------ | ---------------- | ----------- | ------------------ |
| `name`                   | `str`            | 无          | 连接名称           |
| `url`                    | `str`            | 无          | WebSocket URL      |
| `api_key`                | `str`            | 无          | API密钥            |
| `platform`               | `str`            | `"default"` | 平台标识           |
| **SSL配置**              |                  |             |                    |
| `ssl_enabled`            | `bool`           | `False`     | 是否启用SSL        |
| `ssl_verify`             | `bool`           | `True`      | 是否验证SSL证书    |
| `ssl_ca_certs`           | `Optional[str]`  | `None`      | CA证书文件路径     |
| `ssl_certfile`           | `Optional[str]`  | `None`      | 客户端证书文件路径 |
| `ssl_keyfile`            | `Optional[str]`  | `None`      | 客户端私钥文件路径 |
| `ssl_check_hostname`     | `bool`           | `True`      | 是否检查主机名     |
| **重连配置**             |                  |             |                    |
| `max_reconnect_attempts` | `int`            | `5`         | 最大重连次数       |
| `reconnect_delay`        | `float`          | `1.0`       | 重连延迟（秒）     |
| **其他配置**             |                  |             |                    |
| `headers`                | `Dict[str, str]` | `{}`        | HTTP请求头         |

#### 配置管理方法

| 方法                                                                            | 参数                                                                                                                                         | 返回值                      | 说明                         |
| ------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------- | ---------------------------- |
| **连接管理**                                                                    |                                                                                                                                              |                             |                              |  |
| `register_connection(name, url, api_key, platform, **kwargs)`                   | `name`: 连接名称<br>`url`: WebSocket URL<br>`api_key`: API密钥<br>`platform`: 平台标识<br>`**kwargs`: 连接参数                               | `None`                      | 一步配置后继续添加连接       |
| `register_ssl_connection(name, url, api_key, platform, ssl_ca_certs, **kwargs)` | `name`: 连接名称<br>`url`: WebSocket URL<br>`api_key`: API密钥<br>`platform`: 平台标识<br>`ssl_ca_certs`: CA证书路径<br>`**kwargs`: 其他参数 | `None`                      | 添加SSL连接的便捷方法        |
| `remove_connection(name)`                                                       | `name`: 连接名称                                                                                                                             | `bool`                      | 移除连接配置                 |
| `get_connection(name)`                                                          | `name`: 连接名称                                                                                                                             | `Optional[ConnectionEntry]` | 获取连接配置                 |
| **回调管理**                                                                    |                                                                                                                                              |                             |                              |  |
| `register_custom_handler(message_type, handler)`                                | `message_type`: 消息类型<br>`handler`: 处理函数                                                                                              | `None`                      | 注册自定义消息处理器         |
| `unregister_custom_handler(message_type)`                                       | `message_type`: 消息类型                                                                                                                     | `None`                      | 注销自定义消息处理器         |
| `ensure_defaults()`                                                             | 无                                                                                                                                           | `None`                      | 确保所有必填的回调都有默认值 |

#### 配置工厂函数

| 函数                                                                 | 参数                                                                                                                                                                                                        | 返回值              | 说明                     |
| -------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------- | ------------------------ |
| `create_multi_client_config(**kwargs)`                               | `auto_connect_on_start`: 是否自动连接 (默认: False)<br>`enable_stats`: 是否启用统计 (默认: True)<br>`log_level`: 日志级别 (默认: "INFO")<br>`on_message`: 消息处理回调函数 (重要)<br>`kwargs`: 其他配置参数 | `MultiClientConfig` | 创建空的多连接配置       |
| `create_multi_client_config_with_connections(connections, **kwargs)` | `connections`: 连接配置字典<br>`auto_connect_on_start`: 是否自动连接<br>`on_message`: 消息处理回调函数 (重要)<br>`kwargs`: 其他配置参数                                                                     | `MultiClientConfig` | 创建包含连接的多连接配置 |

### 核心方法 (17个公共方法)

#### 生命周期管理 (6个方法)

| 方法                                       | 参数                   | 返回值            | 说明                                   |
| ------------------------------------------ | ---------------------- | ----------------- | -------------------------------------- |
| `start()`                                  | 无                     | `None`            | 启动客户端                             |
| `stop()`                                   | 无                     | `None`            | 停止客户端                             |
| `connect(name: Optional[str] = None)`      | `name`: 可选的连接名称 | `Dict[str, bool]` | 连接指定的连接（不指定则连接所有）     |
| `disconnect(name: Optional[str] = None)`   | `name`: 可选的连接名称 | `Dict[str, bool]` | 断开指定的连接（不指定则断开所有）     |
| `is_running()`                             | 无                     | `bool`            | 检查客户端是否在运行                   |
| `is_connected(name: Optional[str] = None)` | `name`: 可选的连接名称 | `bool`            | 检查连接状态（不指定则检查是否有连接） |

#### 连接管理 (7个方法)

| 方法                                                                              | 参数                                                                                                                  | 返回值                      | 说明                     |
| --------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- | --------------------------- | ------------------------ |
| `register_connection(name: str, url: str, api_key: str, platform: str, **kwargs)` | `name`: 连接名称<br>`url`: WebSocket服务器URL<br>`api_key`: API密钥<br>`platform`: 平台标识<br>`kwargs`: 其他连接参数 | `bool`                      | 一步配置后继续添加新连接 |
| `update_connection(name: str, **kwargs)`                                          | `name`: 连接名称<br>`kwargs`: 要更新的配置参数                                                                        | `bool`                      | 更新已注册连接的配置     |
| `unregister_connection(name: str)`                                                | `name`: 连接名称                                                                                                      | `bool`                      | 注销连接                 |
| `list_connections()`                                                              | 无                                                                                                                    | `Dict[str, Dict[str, Any]]` | 列出所有连接的信息       |
| `get_active_connections()`                                                        | 无                                                                                                                    | `Dict[str, Dict[str, Any]]` | 获取活跃连接的信息       |
| `get_connection_info(name: str)`                                                  | `name`: 连接名称                                                                                                      | `Optional[Dict[str, Any]]`  | 获取指定连接的详细信息   |
| `get_last_error(name: Optional[str] = None)`                                      | `name`: 可选的连接名称                                                                                                | `Optional[str]`             | 获取最后的错误信息       |

#### 消息发送 (2个方法)

| 方法                                                                                    | 参数                                                                           | 返回值 | 说明                     |
| --------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ | ------ | ------------------------ |
| `send_message(connection_name: str, message: APIMessageBase)`                           | `connection_name`: 连接名称<br>`message`: 标准消息                             | `bool` | 发送标准消息到指定连接   |
| `send_custom_message(connection_name: str, message_type: str, payload: Dict[str, Any])` | `connection_name`: 连接名称<br>`message_type`: 消息类型<br>`payload`: 消息载荷 | `bool` | 发送自定义消息到指定连接 |

#### 配置和处理器管理 (2个方法)

| 方法                                             | 参数                                            | 返回值 | 说明                 |
| ------------------------------------------------ | ----------------------------------------------- | ------ | -------------------- |
| `register_custom_handler(message_type, handler)` | `message_type`: 消息类型<br>`handler`: 处理函数 | `None` | 注册自定义消息处理器 |
| `unregister_custom_handler(message_type)`        | `message_type`: 消息类型                        | `None` | 注销自定义消息处理器 |

#### 统计信息 (1个方法)

| 方法          | 参数 | 返回值           | 说明                   |
| ------------- | ---- | ---------------- | ---------------------- |
| `get_stats()` | 无   | `Dict[str, Any]` | 获取客户端运行统计信息 |

---

## 消息相关类

### 核心消息类 (4个)

| 类                | 说明                                                       |
| ----------------- | ---------------------------------------------------------- |
| `APIMessageBase`  | 主要消息类，包含message_info、message_segment、message_dim |
| `MessageDim`      | 消息维度信息，包含api_key和platform用于路由                |
| `BaseMessageInfo` | 消息基础信息，包含平台、消息ID、时间戳等                   |
| `Seg`             | 消息片段，表示不同类型的内容（文本、图片、表情等）         |

### 信息类 (7个)

| 类             | 说明       |
| -------------- | ---------- |
| `UserInfo`     | 用户信息   |
| `GroupInfo`    | 群组信息   |
| `SenderInfo`   | 发送者信息 |
| `ReceiverInfo` | 接收者信息 |
| `FormatInfo`   | 格式信息   |
| `TemplateInfo` | 模板信息   |
| `InfoBase`     | 信息基类   |

---

## 使用模式对比

### 服务端使用模式
```python
# 模式1：使用配置工厂函数
config = create_server_config(host="localhost", port=18040)
server = WebSocketServer(config)

# 模式2：使用默认配置
server = WebSocketServer()  # 使用默认配置

await server.start()
await server.send_message(message)
await server.stop()
```

### 单连接客户端使用模式
```python
# 标准模式：配置工厂函数 + 类初始化
config = create_client_config("ws://localhost:18040/ws", "api_key", platform="test")
client = WebSocketClient(config)

await client.start()
await client.connect()
await client.send_message(message)
await client.disconnect()
await client.stop()
```

### 多连接客户端使用模式

#### 模式1: 一步配置所有连接 (推荐)
```python
# 使用工厂函数创建包含所有连接和回调的配置
config = create_multi_client_config_with_connections(
    connections={
        "wechat": {
            "url": "ws://localhost:18040/ws",
            "api_key": "wechat_key",
            "platform": "wechat"
        },
        "qq": {
            "url": "wss://localhost:18044/ws",
            "api_key": "qq_key",
            "platform": "qq",
            "ssl_ca_certs": "/path/to/ca.pem"
        }
    },
    auto_connect_on_start=True,
    enable_stats=True,
    on_message=lambda message, metadata: print(f"收到消息: {message.message_segment.data}")
)

# 创建客户端
client = WebSocketMultiClient(config)

# 启动客户端（自动连接所有注册的连接）
await client.start()

# 发送消息
await client.send_message("wechat", message)
await client.send_message("qq", message)

await client.stop()
```

#### 模式2: 一步配置后继续添加
```python
# 一步配置初始连接和回调
config = create_multi_client_config_with_connections(
    connections={
        "wechat": {"url": "...", "api_key": "...", "platform": "wechat"}
    },
    auto_connect_on_start=True,
    on_message=message_handler  # 独立的消息回调
)

client = WebSocketMultiClient(config)
await client.start()  # 自动连接初始连接

# 运行时继续添加新连接（两种方式任选）

# 方式1: 通过config.register_connection添加
config.register_connection("qq", "wss://...", "qq_key", "qq",
                          ssl_ca_certs="/path/to/ca.pem")

# 方式2: 通过client.register_connection添加（会同步到config）
client.register_connection("telegram", "ws://...", "telegram_key", "telegram")

# 更新连接配置
client.update_connection("wechat", api_key="new_api_key")

await client.stop()
```

#### 模式3: 独立配置管理
```python
# 创建空配置并逐步设置
config = create_multi_client_config(
    auto_connect_on_start=True,
    enable_stats=True,
    on_message=message_handler
)

# 注册自定义消息处理器
config.register_custom_handler("weather_update", weather_handler)

# 逐步添加连接
config.register_connection("wechat", "ws://...", "wechat_key", "wechat")
config.register_ssl_connection("qq", "wss://...", "qq_key", "qq",
                             ssl_ca_certs="/path/to/ca.pem")

# 创建客户端
client = WebSocketMultiClient(config)
await client.start()

await client.stop()
```

## 接口设计原则

1. **对齐设计**：客户端和服务端都使用配置类 + 类直接初始化的方式
2. **职责分离**：工厂函数仅用于创建配置，客户端类专注于业务逻辑
3. **接口一致性**：所有核心方法（start、stop、send_message等）保持命名和行为的统一
4. **配置灵活性**：支持通过配置类和动态更新两种方式进行配置管理
5. **错误处理**：所有操作都有明确的返回值或异常处理机制

## 接口统计总结

### 服务端 (WebSocketServer)
### 服务端 (WebSocketServer)
- **公共方法总数**: 14个
- **生命周期管理**: 2个 (start, stop)
- **消息发送**: 2个 (send_message, send_custom_message)
- **用户和连接管理**: 5个 (get_user_count, get_user_connections, get_platform_connections, get_connection_info, get_connection_count)
- **配置和处理器管理**: 3个 (update_config, register_custom_handler, unregister_custom_handler)
- **状态监控**: 2个 (get_stats, get_coroutine_status)

### 单连接客户端 (WebSocketClient)
- **公共方法总数**: 16个
- **生命周期管理**: 7个 (start, stop, connect, disconnect, is_running, is_connected, get_coroutine_status)
- **消息发送**: 2个 (send_message, send_custom_message)
- **配置和处理器管理**: 3个 (update_config, register_custom_handler, unregister_custom_handler)
- **连接信息**: 3个 (get_cached_connection_info, get_connection_uuid, get_last_error)
- **统计信息**: 1个 (get_stats)

### 多连接客户端 (WebSocketMultiClient)
- **公共方法总数**: 17个
- **生命周期管理**: 6个 (start, stop, connect, disconnect, is_running, is_connected)
- **连接管理**: 7个 (register_connection, update_connection, unregister_connection, list_connections, get_active_connections, get_connection_info, get_last_error)
- **消息发送**: 2个 (send_message, send_custom_message)
- **配置和处理器管理**: 2个 (register_custom_handler, unregister_custom_handler)
- **统计信息**: 1个 (get_stats)

### 配置工厂函数 (6个)
- **服务端配置**: 2个 (create_server_config, create_ssl_server_config)
- **单连接客户端配置**: 2个 (create_client_config, create_ssl_client_config)
- **多连接客户端配置**: 2个 (create_multi_client_config, create_multi_client_config_with_connections)

### 配置类详细字段 (3个)
- **服务端配置**: 15个字段 (网络配置4个 + SSL配置5个 + 回调函数3个 + 统计配置2个 + 日志配置3个)
- **单连接客户端配置**: 20个字段 (基础连接4个 + SSL配置6个 + 重连配置4个 + 心跳配置3个 + 回调函数1个 + 统计配置2个 + 日志配置3个 + HTTP配置1个)
- **多连接客户端配置**: 12个字段 (连接管理1个 + 回调函数2个 + 全局设置2个 + 统计配置2个 + 日志配置3个 + 连接字典1个 + ConnectionEntry独立配置12个)

### 消息相关类 (11个)
- **核心消息类**: 4个 (APIMessageBase, MessageDim, BaseMessageInfo, Seg)
- **信息类**: 7个 (UserInfo, GroupInfo, SenderInfo, ReceiverInfo, FormatInfo, TemplateInfo, InfoBase)

### 接口覆盖范围
- ✅ 所有实际代码中的公共方法都已记录
- ✅ 方法签名与实际代码完全对齐
- ✅ 参数类型和返回值类型准确标注
- ✅ 方法说明清晰易懂
- ✅ 配置工厂函数支持所有重要回调配置

### 重要回调配置说明
服务器配置中最重要的回调函数：

1. **on_auth(metadata: Dict[str, Any]) -> bool**
   - 用途：验证客户端连接的API Key是否有效
   - 返回：True表示认证通过，False表示拒绝

2. **on_auth_extract_user(metadata: Dict[str, Any]) -> str**
   - 用途：从API Key提取用户标识，用于内部路由
   - 返回：用户ID字符串

3. **on_message(message: APIMessageBase, metadata: Dict[str, Any]) -> None**
   - 用途：处理收到的标准消息
   - 参数：消息对象和连接元数据

---

## 回调函数详细说明

### Metadata 结构说明

所有回调函数都会接收到 `metadata` 参数，这是一个包含连接信息的字典：

```python
metadata = {
    "uuid": str,              # 连接唯一标识符
    "api_key": str,           # 客户端API密钥
    "platform": str,          # 平台标识
    "headers": Dict[str, str], # HTTP请求头（已清理敏感信息）
    "client_ip": Optional[str], # 客户端IP地址
    "connected_at": float     # 连接建立时间戳
}
```

## 异步任务执行模式 (重要)

**设计原则**: 所有消息处理回调默认使用 `asyncio.create_task()` 异步执行

### 核心优势
- **非阻塞处理**: 回调函数的执行不会阻塞事件分发器
- **并发能力**: 支持多个消息同时被处理，提升系统吞吐量
- **异常隔离**: 单个回调的异常不会影响其他回调或主循环
- **性能优化**: 慢速处理器不会影响整体系统响应性

### 执行机制
1. 底层WebSocket连接将消息推送到业务层队列
2. 事件分发器从队列中取出消息
3. 使用 `asyncio.create_task()` 创建异步任务执行回调
4. 任务自动管理生命周期，完成后自动清理
5. 在服务/客户端停止时，所有未完成的任务会被安全取消

### 任务管理统计
- `active_handler_tasks`: 当前活跃的handler任务数量
- 可通过 `get_stats()` 方法实时监控任务状态
- 任务创建、执行、清理都有详细的日志记录

### 性能影响
- **并发处理**: 多个消息可以同时被处理，不再串行等待
- **吞吐量提升**: 在高并发场景下显著提升消息处理能力
- **资源利用率**: 更好的CPU和I/O资源利用
- **响应性**: 单个慢处理不会阻塞整个消息流

### 注意事项
- 回调函数应该是异步的 (`async def`)
- 避免在回调中执行长时间同步操作
- 长时间运行的任务应该考虑超时和取消机制
- 系统会自动清理已完成或异常的任务

### 服务端回调函数

#### 1. on_auth 回调
**签名**: `async def on_auth(metadata: Dict[str, Any]) -> bool`

- **用途**: 验证客户端连接的API Key是否有效
- **输入**: `metadata` - 连接元数据字典
- **输出**: `bool` - True表示认证通过，False表示拒绝连接
- **调用时机**: 客户端建立WebSocket连接时
- **示例**:
```python
async def auth_handler(metadata: Dict[str, Any]) -> bool:
    api_key = metadata.get("api_key", "")
    # 检查API Key是否在白名单中
    return api_key in valid_api_keys
```

#### 2. on_auth_extract_user 回调
**签名**: `async def on_auth_extract_user(metadata: Dict[str, Any]) -> str`

- **用途**: 从API Key提取用户标识，用于内部消息路由
- **输入**: `metadata` - 连接元数据字典，内容随调用场景而异
- **输出**: `str` - 用户ID字符串
- **调用时机**:
  - 连接建立时：认证通过后，用于建立用户与连接的映射关系
  - 消息发送时：从消息中提取路由信息，用于消息路由
- **metadata 内容说明**:
  - **连接建立时**: 包含完整的连接信息（api_key, platform, headers等）
  - **消息发送时**: 包含路由信息（api_key, platform, message_type等）
- **示例**:
```python
async def extract_user_handler(metadata: Dict[str, Any]) -> str:
    api_key = metadata.get("api_key", "")

    # 可以根据调用场景处理不同的逻辑
    if metadata.get("message_type") == "outgoing":
        # 消息发送场景
        logger.info(f"提取用户ID用于消息路由: {api_key}")
    else:
        # 连接建立场景
        logger.info(f"提取用户ID用于连接注册: {api_key}")

    # 从数据库或配置中映射API Key到用户ID
    return api_key  # 简单地直接使用API Key作为用户ID
```

#### 3. on_message 回调
**签名**: `async def on_message(message: APIMessageBase, metadata: Dict[str, Any]) -> None`

- **用途**: 处理收到的标准消息
- **输入**:
  - `message: APIMessageBase` - 标准消息对象
  - `metadata: Dict[str, Any]` - 发送者连接元数据
- **输出**: `None` - 无返回值
- **调用时机**: 收到标准格式消息时
- **示例**:
```python
async def message_handler(message: APIMessageBase, metadata: Dict[str, Any]) -> None:
    platform = metadata.get("platform", "unknown")
    user_id = metadata.get("api_key", "unknown")
    content = message.message_segment.data

    print(f"[{platform}] {user_id}: {content}")

    # 可以根据消息内容进行业务处理
    if "weather" in content:
        await handle_weather_query(message, metadata)
```

### 客户端回调函数

#### 4. 客户端 on_message 回调
**签名**: `async def on_message(message: APIMessageBase, metadata: Dict[str, Any]) -> None`

- **用途**: 处理从服务器收到的标准消息
- **输入**:
  - `message: APIMessageBase` - 接收到的标准消息对象
  - `metadata: Dict[str, Any]` - 连接元数据（通常包含服务器信息）
- **输出**: `None` - 无返回值
- **调用时机**: 客户端收到服务器发送的标准消息时
- **示例**:
```python
async def client_message_handler(message: APIMessageBase, metadata: Dict[str, Any]) -> None:
    content = message.message_segment.data
    platform = message.get_platform()

    print(f"收到来自 {platform} 的消息: {content}")

    # 根据消息类型处理
    if message.message_segment.type == "text":
        await handle_text_message(content)
    elif message.message_segment.type == "image":
        await handle_image_message(message.message_segment.data)
```

### 自定义消息处理器回调

#### 5. 自定义消息处理器
**签名**: `async def handler(payload: Dict[str, Any], metadata: Dict[str, Any]) -> None`

- **用途**: 处理自定义类型的消息
- **输入**:
  - `payload: Dict[str, Any]` - 自定义消息的载荷数据
  - `metadata: Dict[str, Any]` - 连接元数据
- **输出**: `None` - 无返回值
- **注册方式**: `register_custom_handler("message_type", handler)`
- **调用时机**: 收到对应类型的自定义消息时
- **示例**:
```python
# 注册天气更新处理器
server.register_custom_handler("weather_update", weather_update_handler)

async def weather_update_handler(payload: Dict[str, Any], metadata: Dict[str, Any]) -> None:
    city = payload.get("city", "unknown")
    temperature = payload.get("temperature", 0)
    humidity = payload.get("humidity", 0)

    user_id = metadata.get("api_key")
    print(f"用户 {user_id} 请求天气: {city} - {temperature}°C, 湿度: {humidity}%")

    # 处理天气更新逻辑
    await process_weather_update(city, temperature, humidity, user_id)
```

### 统计信息回调

#### 6. stats_callback 回调
**签名**: `def stats_callback(stats: Dict[str, Any]) -> None`

- **用途**: 接收统计信息更新通知
- **输入**: `stats: Dict[str, Any]` - 统计信息字典
- **输出**: `None` - 无返回值
- **调用时机**: 当启用统计功能且有统计更新时
- **统计信息结构**:
```python
stats = {
    # 基础统计
    "total_connections": int,     # 总连接数
    "active_connections": int,    # 活跃连接数
    "total_messages": int,        # 总消息数
    "successful_connects": int,   # 成功连接数
    "failed_connects": int,       # 失败连接数
    "messages_sent": int,         # 发送消息数
    "messages_received": int,     # 接收消息数

    # 时间统计
    "uptime": float,              # 运行时间（秒）
    "last_activity": float,       # 最后活动时间戳

    # 异步任务统计 (新增)
    "active_handler_tasks": int,  # 当前活跃的handler任务数

    # 错误统计
    "last_error": Optional[str],  # 最后错误信息
    "error_count": int,           # 错误次数
}
```
- **示例**:
```python
def stats_handler(stats: Dict[str, Any]) -> None:
    # 记录到监控系统
    monitoring_system.record_metrics(stats)

    # 输出关键指标
    print(f"活跃连接: {stats['active_connections']}")
    print(f"消息统计: 发送 {stats['messages_sent']}, 接收 {stats['messages_received']}")

    # 检查异常情况
    if stats['error_count'] > 10:
        alert_system.send_alert(f"错误次数过多: {stats['error_count']}")
```

### 回调函数最佳实践

**重要说明**：所有回调函数都已经默认使用 `asyncio.create_task()` 在独立的异步任务中执行，因此回调函数内部应该**直接执行业务逻辑**，而不是再次创建新任务。

#### 1. 回调函数执行模式

**架构说明**：
- 事件分发器自动为每个回调创建独立的异步任务
- 回调函数已经在并发环境中执行，不会阻塞事件分发器
- 回调函数内部不应该再使用 `asyncio.create_task()`

**正确的执行流程**：
```
WebSocket消息 → 事件队列 → 事件分发器 → create_task(回调函数) → 业务逻辑执行
```

#### 2. 回调函数设计原则

**核心理念**：回调函数可以直接执行完整的业务逻辑，因为它们已经在独立的异步任务中运行。

```python
# ✅ 推荐：直接执行业务逻辑
async def message_handler(message: APIMessageBase, metadata: Dict[str, Any]) -> None:
    """直接执行完整的业务逻辑"""
    content = message.message_segment.data
    platform = metadata.get("platform", "unknown")
    user_id = metadata.get("user_id", "unknown")

    logger.info(f"📨 收到消息 [{platform}] {user_id}: {content}")

    # 直接执行业务逻辑，因为已经在独立任务中
    await database.save_message(content, user_id, platform)
    await notification_system.notify_user(user_id, "消息已收到")

    # 处理业务逻辑
    if "hello" in content.lower():
        response = await process_greeting(content, user_id)
        await send_response(response, platform, user_id)

# ❌ 避免：在回调中再次创建任务
async def bad_message_handler(message: APIMessageBase, metadata: Dict[str, Any]) -> None:
    """错误：在已经异步的回调中再次创建异步任务"""
    content = message.message_segment.data

    # 不必要：回调已经在独立任务中执行
    asyncio.create_task(process_business_logic(content, metadata))

    # 这样做会造成任务嵌套，增加复杂度
```

#### 3. 性能优化最佳实践

**原则**：利用异步并发优势，但避免不必要的任务创建。

```python
# ✅ 推荐：合理的异步操作
async def optimized_message_handler(message: APIMessageBase, metadata: Dict[str, Any]) -> None:
    """合理的异步操作组合"""
    content = message.message_segment.data
    platform = metadata.get("platform", "unknown")

    # 并行执行多个独立操作
    tasks = [
        save_message_to_database(content, metadata),
        update_user_activity(metadata),
        check_message_content(content),
        update_statistics(content, platform)
    ]

    # 等待所有操作完成
    await asyncio.gather(*tasks, return_exceptions=True)

    # 根据检查结果执行后续操作
    await trigger_additional_processing(content, metadata)

# ✅ 推荐：带超时控制的操作
async def timeout_aware_handler(message: APIMessageBase, metadata: Dict[str, Any]) -> None:
    """带超时控制的业务逻辑"""
    content = message.message_segment.data

    try:
        # 为可能耗时的操作设置超时
        await asyncio.wait_for(
            process_with_external_api(content, metadata),
            timeout=30.0
        )
    except asyncio.TimeoutError:
        logger.error(f"消息处理超时: {message.message_info.message_id}")
        # 执行降级处理
        await handle_timeout_fallback(content, metadata)
```

#### 4. 错误处理和异常隔离

**原则**：单个回调的异常不应影响其他消息处理，系统已经自动处理异常隔离。

```python
# ✅ 推荐：直接在回调中处理错误
async def robust_message_handler(message: APIMessageBase, metadata: Dict[str, Any]) -> None:
    try:
        # 验证消息
        content = message.message_segment.data
        if not content or len(content.strip()) == 0:
            logger.warning("收到空消息，跳过处理")
            return

        # 直接执行业务逻辑
        await process_business_logic(content, metadata)

        # 发送确认消息
        await send_confirmation(metadata, "消息处理完成")

    except ValueError as e:
        # 业务逻辑错误
        logger.error(f"消息内容错误: {e}")
        await send_error_response(metadata, f"消息格式错误: {e}")

    except ConnectionError as e:
        # 网络相关错误
        logger.error(f"网络连接错误: {e}")
        # 可以选择重试或记录到队列中稍后处理
        await schedule_retry(content, metadata)

    except Exception as e:
        # 未预期的错误
        logger.error(f"消息处理异常: {e}", exc_info=True)
        # 发送通用错误响应
        await send_error_response(metadata, "服务器内部错误")

# ✅ 推荐：分级错误处理
async def分级处理_handler(message: APIMessageBase, metadata: Dict[str, Any]) -> None:
    """根据错误类型进行不同处理"""
    content = message.message_segment.data

    try:
        # 主要业务逻辑
        await main_business_logic(content, metadata)

    except ValidationError:
        # 验证错误：立即返回错误给用户
        await send_validation_error(metadata)

    except RateLimitError:
        # 限流错误：稍后重试
        await schedule_retry_later(content, metadata)

    except DatabaseError:
        # 数据库错误：降级处理
        await fallback_processing(content, metadata)

    except Exception as e:
        # 其他错误：记录并通知管理员
        logger.error(f"未处理错误: {e}")
        await notify_admin_error(e, metadata)
```

#### 3. 超时控制和资源管理

**原则**：为可能长时间运行的操作设置超时限制。

```python
# ✅ 推荐：带超时控制的处理器
async def timeout_aware_handler(message: APIMessageBase, metadata: Dict[str, Any]) -> None:
    content = message.message_segment.data

    # 对于可能耗时的操作，设置超时
    try:
        await asyncio.wait_for(
            start_business_processing(content, metadata),
            timeout=30.0  # 30秒超时
        )
    except asyncio.TimeoutError:
        logger.error(f"消息处理超时: {message.message_info.message_id}")
        # 超时处理逻辑
        asyncio.create_task(handle_timeout(content, metadata))
    except Exception as e:
        logger.error(f"消息处理异常: {e}")

async def start_business_processing(content: str, metadata: Dict[str, Any]) -> None:
    """启动业务处理，立即返回"""
    # 将实际处理放到另一个任务中
    asyncio.create_task(full_business_process(content, metadata))
```

#### 5. 负载管理和限流

**原则**：在高负载情况下保护系统稳定性，利用信号量控制并发。

```python
# ✅ 推荐：负载感知的处理器
class LoadAwareHandler:
    def __init__(self, max_concurrent_tasks: int = 100):
        self.max_concurrent_tasks = max_concurrent_tasks
        self.semaphore = asyncio.Semaphore(max_concurrent_tasks)

    async def __call__(self, message: APIMessageBase, metadata: Dict[str, Any]) -> None:
        # 使用信号量控制并发回调数量
        async with self.semaphore:
            await self.process_with_load_control(message, metadata)

    async def process_with_load_control(self, message: APIMessageBase, metadata: Dict[str, Any]) -> None:
        """负载控制的处理逻辑"""
        # 直接执行业务逻辑，回调已经在独立任务中
        await self.actual_processing(message, metadata)
```

#### 6. 消息分类和优先级处理

**原则**：根据消息特性采用不同的处理策略，直接在回调中执行相应的逻辑。

```python
# ✅ 推荐：智能消息分类处理器
async def smart_message_handler(message: APIMessageBase, metadata: Dict[str, Any]) -> None:
    content = message.message_segment.data
    message_type = classify_message(content)

    if message_type == "urgent":
        # 紧急消息：立即处理
        await process_urgent_message(content, metadata)

    elif message_type == "heavy":
        # 重型任务：直接处理（回调已在独立任务中）
        await process_heavy_task(content, metadata)

    elif message_type == "batch":
        # 批量处理：添加到批量收集器
        await batch_collector.add_message(content, metadata)

    else:
        # 普通消息：标准处理
        await process_normal_message(content, metadata)

def classify_message(content: str) -> str:
    """消息分类逻辑"""
    content_lower = content.lower()
    if "urgent" in content_lower or "紧急" in content:
        return "urgent"
    elif "report" in content_lower or "报表" in content:
        return "heavy"
    elif len(content) < 10:
        return "batch"
    return "normal"
```

#### 关键要点总结

1. **直接执行**：回调函数已经在独立异步任务中，直接执行完整业务逻辑
2. **避免嵌套**：不在回调内部再次使用 `asyncio.create_task()`
3. **异常隔离**：单个回调的错误已被系统自动隔离，但建议做好内部错误处理
4. **合理异步**：使用 `asyncio.gather()` 等工具进行并发操作，但避免不必要的任务创建
5. **超时控制**：为可能耗时的操作设置合理的超时限制
6. **负载管理**：使用信号量等机制控制系统并发度
7. **智能分类**：根据消息特性采用不同处理策略
8. **可观测性**：提供充分的监控和调试信息
9. **可测试性**：设计易于测试和调试的代码结构