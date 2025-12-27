# 非maim_message客户端与API-Server通信指南

## 概述

本文档指导开发者如何使用原生WebSocket协议与非maim_message库的客户端程序与maim_message API-Server服务端进行通信。通过理解协议规范，任何支持WebSocket的编程语言和框架都可以与maim_message服务端正常通信。

## 协议基础

### 连接信息

- **协议**: WebSocket (RFC 6455)
- **消息格式**: JSON
- **认证方式**: API Key通过查询参数或HTTP头 `x-apikey` 传递
- **字符编码**: UTF-8

### 连接建立

maim_message API-Server支持两种API Key传递方式：

#### 方式1：通过查询参数（推荐用于浏览器客户端）

##### HTTP/WebSocket连接
```
ws://host:port/ws?api_key=your_api_key&platform=your_platform
```

##### SSL/TLS安全连接
```
wss://host:port/ws?api_key=your_api_key&platform=your_platform
```

#### 方式2：通过HTTP头（推荐用于服务器端客户端）

##### HTTP/WebSocket连接
```
ws://host:port/ws
```

##### SSL/TLS安全连接
```
wss://host:port/ws
```

### HTTP头要求

```http
Connection: Upgrade
Upgrade: websocket
Sec-WebSocket-Key: <客户端生成的随机字符串>
Sec-WebSocket-Version: 13
```

**方式1必需的查询参数**：
```
api_key: your_api_key
platform: your_platform (可选)
```

**方式2必需的认证头**：
```http
x-apikey: your_api_key
```

**可选的头信息**：
```http
x-uuid: <客户端唯一标识符>
x-platform: <平台标识符>
```

**优先级**：查询参数优先于HTTP头，如果同时提供查询参数和HTTP头，将使用查询参数中的值。

## 消息格式规范

### 消息结构

所有消息都必须是JSON格式，包含**外层协议信封 (Envelope)** 和 **内层业务数据 (Payload)**。

#### 外层信封结构 (Envelope)

```json
{
  "ver": 1,                          // 协议版本，当前为1
  "msg_id": "消息一标识符",          // 客户端生成，用于追踪和ACK
  "type": "sys_std",                 // 消息类型：sys_std (标准消息) 或 sys_ack (确认消息)
  "meta": {                          // 元数据
    "sender_user": "api_key_or_id",  // 发送者API Key或用户ID
    "platform": "platform_name",     // 发送平台
    "timestamp": 1234567890.123      // 发送时间戳
  },
  "payload": { ... }                 // 内层业务数据
}
```

### 1. 标准消息 (sys_std)

业务消息必须封装在 `sys_std` 类型的信封中。

```json
{
  "ver": 1,
  "msg_id": "msg_unique_id_123",
  "type": "sys_std",
  "meta": {
    "sender_user": "your_api_key",
    "platform": "your_platform",
    "timestamp": 1703123456.789
  },
  "payload": {
    "message_info": {
      "platform": "platform_name",
      "message_id": "unique_message_id",
      "time": 1234567890.123,
      "sender_info": {
        "user_info": {
          "platform": "platform_name",
          "user_id": "user_unique_id",
          "user_nickname": "用户昵称",
          "user_cardname": "用户名片"
        },
        "group_info": {
          "platform": "platform_name",
          "group_id": "group_unique_id",
          "group_name": "群组名称"
        }
      }
    },
    "message_segment": {
      "type": "text|image|file|at|face",
      "data": "消息内容数据"
    },
    "message_dim": {
      "api_key": "target_receiver_api_key",    # ⚠️ 目标接收者的API密钥
      "platform": "target_receiver_platform"  # ⚠️ 目标接收者的平台
    }
  }
}
```

### 2. ACK确认消息 (sys_ack)

服务端和客户端会自动发送ACK确认消息来确认消息接收：

```json
{
  "ver": 1,
  "msg_id": "ack_unique_id_456",
  "type": "sys_ack",
  "meta": {
    "uuid": "连接UUID",
    "acked_msg_id": "msg_unique_id_123",  # 被确认的消息ID
    "timestamp": 1234567890.123
  },
  "payload": {
    "status": "received",
    "server_timestamp": 1234567890.123
  }
}
```

### 字段说明

#### 外层信封字段

| 字段      | 类型   | 必填 | 说明                              |
| --------- | ------ | ---- | --------------------------------- |
| `ver`     | int    | -    | 协议版本，建议为 1                |
| `msg_id`  | string | ✅    | 消息唯一标识符，用于ACK确认       |
| `type`    | string | ✅    | 必须为 `sys_std` (发送业务消息时) |
| `meta`    | object | -    | 元数据，建议包含发送者信息        |
| `payload` | object | ✅    | 内层业务数据对象                  |

#### 内层业务字段 (payload中)

| 字段路径                  | 类型   | 必填 | 说明                                         |
| ------------------------- | ------ | ---- | -------------------------------------------- |
| `message_info.platform`   | string | ✅    | 消息平台标识符                               |
| `message_info.message_id` | string | ✅    | 业务层消息ID                                 |
| `message_info.time`       | float  | ✅    | Unix时间戳                                   |
| `message_segment.type`    | string | ✅    | 消息内容类型                                 |
| `message_segment.data`    | string | ✅    | 消息内容                                     |
| `message_dim.api_key`     | string | ✅    | ⚠️ **目标接收者的API密钥**（用于服务端路由）  |
| `message_dim.platform`    | string | ✅    | ⚠️ **目标接收者的平台标识**（用于服务端路由） |

## 消息类型

### 协议消息类型 (Envelope Type)

| 类型值    | 说明         | 发送方        | 接收方处理                               |
| --------- | ------------ | ------------- | ---------------------------------------- |
| `sys_std` | 标准业务消息 | 客户端/服务端 | 解析payload，路由到业务逻辑，自动回复ACK |
| `sys_ack` | 消息确认应答 | 服务端/客户端 | 确认消息接收，无需回复ACK                |

### 业务消息类型 (payload.message_segment.type)

| 类型值  | 说明       | data字段格式    |
| ------- | ---------- | --------------- |
| `text`  | 纯文本消息 | 字符串          |
| `image` | 图片消息   | 图片URL或Base64 |
| `file`  | 文件消息   | 文件URL或Base64 |
| `at`    | @消息      | JSON格式        |
| `face`  | 表情消息   | 表情标识符      |

## ACK确认机制

### 自动ACK规则

1. **触发条件**: 接收到的消息包含`msg_id`字段且消息类型(type)不是`sys_ack`
2. **自动发送**: 服务端会自动对接收到的消息发送`sys_ack`应答
3. **客户端行为**: 建议客户端也对收到的服务端`sys_std`消息回复`sys_ack`

## send_message返回值说明

### 服务端send_message返回值

当服务端调用`send_message`方法时，返回值为`Dict[str, bool]`格式：

```python
# 服务端返回示例
{
    "connection_uuid_1": True,    # 连接1发送成功
    "connection_uuid_2": False,   # 连接2发送失败
    "connection_uuid_3": True     # 连接3发送成功
}
```

**返回值说明**：
- **键(key)**: 连接UUID，标识特定的客户端连接
- **值(value)**: 布尔值，表示该连接的发送结果
  - `True`: 消息成功发送到该连接
  - `False`: 消息发送失败（连接断开、网络错误等）

### 客户端send_message返回值

当客户端调用`send_message`方法时，返回值为`bool`类型：

```python
# 客户端返回示例
True    # 发送成功
False   # 发送失败
```

**返回值说明**：
- `True`: 消息成功发送到服务端
- `False`: 发送失败（连接断开、网络错误、格式错误等）

### 消息示例

#### 文本消息

```json
{
  "ver": 1,
  "msg_id": "msg_001",
  "type": "sys_std",
  "meta": {
    "sender_user": "your_api_key",
    "platform": "custom_client",
    "timestamp": 1703123456.789
  },
  "payload": {
    "message_info": {
      "platform": "custom_client",
      "message_id": "msg_inner_001",
      "time": 1703123456.789,
      "sender_info": {
        "user_info": {
          "platform": "custom_client",
          "user_id": "user_123",
          "user_nickname": "测试用户",
          "user_cardname": "测试名片"
        }
      }
    },
    "message_segment": {
      "type": "text",
      "data": "Hello from custom client!"
    },
    "message_dim": {
      "api_key": "target_receiver_api_key",
      "platform": "target_receiver_platform"
    }
  }
}
```

#### 图片消息

```json
{
  "ver": 1,
  "msg_id": "msg_002",
  "type": "sys_std",
  "meta": { ... },
  "payload": {
    "message_info": {
      "platform": "custom_client",
      "message_id": "img_001",
      "time": 1703123456.789
    },
    "message_segment": {
      "type": "image",
      "data": "https://example.com/image.jpg"
    },
    "message_dim": {
      "api_key": "target_receiver_api_key",
      "platform": "target_receiver_platform"
    }
  }
}
```

#### 群组消息

```json
{
  "ver": 1,
  "msg_id": "msg_003",
  "type": "sys_std",
  "meta": { ... },
  "payload": {
    "message_info": {
      "platform": "custom_client",
      "message_id": "group_msg_001",
      "time": 1703123456.789,
      "sender_info": {
        "user_info": {
          "platform": "custom_client",
          "user_id": "user_123",
          "user_nickname": "群成员"
        },
        "group_info": {
          "platform": "custom_client",
          "group_id": "group_456",
          "group_name": "测试群组"
        }
      }
    },
    "message_segment": {
      "type": "text",
      "data": "群消息内容"
    },
    "message_dim": {
      "api_key": "target_receiver_api_key",
      "platform": "target_receiver_platform"
    }
  }
}
```

## 实现示例

### Python (websockets库)

```python
import asyncio
import json
import websockets
import time
import uuid

async def custom_client():
    # 方式1：通过查询参数（推荐）
    uri = "ws://localhost:18040/ws?api_key=your_api_key&platform=python_custom"
    async with websockets.connect(uri) as websocket:
        # ... 连接和消息处理逻辑
        pass

    # 方式2：通过HTTP头
    uri = "ws://localhost:18040/ws"
    headers = {
        "x-apikey": "your_api_key",
        "x-platform": "python_custom",
        "x-uuid": str(uuid.uuid4())
    }
    async with websockets.connect(uri, extra_headers=headers) as websocket:
        # 构造业务消息(Payload)
        payload = {
            "message_info": {
                "platform": "python_custom",
                "message_id": f"msg_{uuid.uuid4()}",
                "time": time.time(),
                "sender_info": {
                    "user_info": {
                        "platform": "python_custom",
                        "user_id": "user_001",
                        "user_nickname": "Python客户端",
                        "user_cardname": "Python客户端"
                    }
                }
            },
            "message_segment": {
                "type": "text",
                "data": "Hello from Python custom client!"
            },
            "message_dim": {
                "api_key": "target_receiver_api_key",  # 目标接收者的API密钥
                "platform": "python_custom"           # 目标接收者的平台
            }
        }

        # 构造协议信封(Envelope)
        envelope = {
            "ver": 1,
            "msg_id": f"msg_env_{uuid.uuid4()}",
            "type": "sys_std",
            "meta": {
                "sender_user": "your_api_key",
                "platform": "python_custom",
                "timestamp": time.time()
            },
            "payload": payload
        }

        # 发送消息
        await websocket.send(json.dumps(envelope))
        print("消息已发送")

        # 接收响应（可能包含ACK确认）
        response = await websocket.recv()
        response_data = json.loads(response)

        if response_data.get("type") == "sys_ack":
            print(f"收到ACK确认: {response_data['meta']['acked_msg_id']}")
        elif response_data.get("type") == "sys_std":
            print(f"收到业务消息: {response_data['payload']['message_segment']['data']}")

if __name__ == "__main__":
    asyncio.run(custom_client())
```

### JavaScript (原生WebSocket)

```javascript
class MaimMessageClient {
    constructor(url, apiKey) {
        this.url = url;
        this.apiKey = apiKey;
        this.ws = null;
    }

    connect() {
        // 使用查询参数传递API Key（浏览器推荐方式）
        const wsUrl = `${this.url}?api_key=${this.apiKey}&platform=javascript_custom`;
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('WebSocket连接已建立');
        };

        this.ws.onmessage = (event) => {
            const message = JSON.parse(event.data);

            if (message.type === 'sys_ack') {
                console.log('收到ACK确认:', message.meta.acked_msg_id);
            } else if (message.type === 'sys_std') {
                console.log('收到业务消息:', message.payload);
            }
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket错误:', error);
        };

        this.ws.onclose = () => {
            console.log('WebSocket连接已关闭');
        };
    }

    sendMessage(text, senderInfo = {}) {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            throw new Error('WebSocket未连接');
        }

        // 业务消息(Payload)
        const payload = {
            message_info: {
                platform: "javascript_custom",
                message_id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
                time: Date.now() / 1000,
                sender_info: {
                    user_info: {
                        platform: "javascript_custom",
                        user_id: senderInfo.userId || "js_user_001",
                        user_nickname: senderInfo.nickname || "JavaScript客户端",
                        user_cardname: senderInfo.cardname || "JS客户端"
                    }
                }
            },
            message_segment: {
                type: "text",
                data: text
            },
            message_dim: {
                api_key: this.apiKey,
                platform: "javascript_custom"
            }
        };

        // 协议信封(Envelope)
        const envelope = {
            ver: 1,
            msg_id: `msg_${Date.now()}`,
            type: "sys_std",
            meta: {
                sender_user: this.apiKey,
                platform: "javascript_custom",
                timestamp: Date.now() / 1000
            },
            payload: payload
        };

        this.ws.send(JSON.stringify(envelope));
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
        }
    }
}

// 使用示例
const client = new MaimMessageClient('ws://localhost:18040/ws', 'your_api_key');

client.connect();

setTimeout(() => {
    client.sendMessage('Hello from JavaScript client!');
}, 1000);

setTimeout(() => {
    client.disconnect();
}, 5000);
```

### Java (Java-WebSocket库)

```java
import org.java_websocket.client.WebSocketClient;
import org.java_websocket.handshake.ServerHandshake;
import java.net.URI;
import java.time.Instant;

public class MaimMessageJavaClient extends WebSocketClient {

    private String apiKey;

    public MaimMessageJavaClient(String apiKey) throws Exception {
        // 使用查询参数传递API Key
        super(new URI("ws://localhost:18040/ws?api_key=" + apiKey + "&platform=java_custom"));
        this.apiKey = apiKey;
    }

    @Override
    public void onOpen(ServerHandshake handshake) {
        System.out.println("WebSocket连接已建立");

        // 发送测试消息
        sendMessage("Hello from Java client!");
    }

    @Override
    public void onMessage(String message) {
        System.out.println("收到消息: " + message);
    }

    @Override
    public void onClose(int code, String reason, boolean remote) {
        System.out.println("WebSocket连接已关闭: " + reason);
    }

    @Override
    public void onError(Exception ex) {
        ex.printStackTrace();
    }

    public void sendMessage(String text) {
        try {
            // 构造JSON消息 (简化示例，实际应使用JSON库如Jackson/Gson)
            String payload = String.format(
                "{" +
                "\"message_info\":{" +
                "\"platform\":\"java_custom\"," +
                "\"message_id\":\"msg_%d\"," +
                "\"time\":%f," +
                "\"sender_info\":{" +
                "\"user_info\":{" +
                "\"platform\":\"java_custom\"," +
                "\"user_id\":\"java_user_001\"," +
                "\"user_nickname\":\"Java客户端\"," +
                "\"user_cardname\":\"Java客户端\"" +
                "}" +
                "}" +
                "}," +
                "\"message_segment\":{" +
                "\"type\":\"text\"," +
                "\"data\":\"%s\"" +
                "}," +
                "\"message_dim\":{" +
                "\"api_key\":\"%s\"," +
                "\"platform\":\"java_custom\"" +
                "}" +
                "}",
                System.currentTimeMillis(),
                Instant.now().getEpochSecond(),
                text.replace("\"", "\\\""),
                apiKey
            );

            // 构造信封
            String envelope = String.format(
                "{" +
                "\"ver\":1," +
                "\"msg_id\":\"msg_%d\"," +
                "\"type\":\"sys_std\"," +
                "\"meta\":{" +
                "\"sender_user\":\"%s\"," +
                "\"platform\":\"java_custom\"," +
                "\"timestamp\":%f" +
                "}," +
                "\"payload\":%s" +
                "}",
                System.currentTimeMillis(),
                apiKey,
                Instant.now().getEpochSecond(),
                payload
            );

            this.send(envelope);
            System.out.println("消息已发送: " + text);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public static void main(String[] args) throws Exception {
        MaimMessageJavaClient client = new MaimMessageJavaClient("your_api_key");
        client.connect();

        // 保持连接
        Thread.sleep(10000);
    }
}
```

### Go (gorilla/websocket库)

```go
package main

import (
    "encoding/json"
    "fmt"
    "log"
    "net/url"
    "time"

    "github.com/gorilla/websocket"
)

// 定义 payload 结构
type MessageInfo struct {
    Platform   string    `json:"platform"`
    MessageID  string    `json:"message_id"`
    Time       float64   `json:"time"`
    SenderInfo *SenderInfo `json:"sender_info,omitempty"`
}

type SenderInfo struct {
    UserInfo  *UserInfo  `json:"user_info,omitempty"`
    GroupInfo *GroupInfo `json:"group_info,omitempty"`
}

type UserInfo struct {
    Platform     string `json:"platform"`
    UserID       string `json:"user_id"`
    UserNickname string `json:"user_nickname"`
    UserCardname string `json:"user_cardname"`
}

type GroupInfo struct {
    Platform  string `json:"platform"`
    GroupID   string `json:"group_id"`
    GroupName string `json:"group_name"`
}

type MessageSegment struct {
    Type string `json:"type"`
    Data string `json:"data"`
}

type MessageDim struct {
    APIKey  string `json:"api_key"`
    Platform string `json:"platform"`
}

type Payload struct {
    MessageInfo     *MessageInfo   `json:"message_info"`
    MessageSegment  *MessageSegment `json:"message_segment"`
    MessageDim      *MessageDim     `json:"message_dim"`
}

// 定义 Envelope 结构
type Envelope struct {
    Ver     int         `json:"ver"`
    MsgID   string      `json:"msg_id"`
    Type    string      `json:"type"`
    Meta    *Meta       `json:"meta"`
    Payload *Payload    `json:"payload"`
}

type Meta struct {
    SenderUser string  `json:"sender_user"`
    Platform   string  `json:"platform"`
    Timestamp  float64 `json:"timestamp"`
}

func main() {
    apiKey := "your_api_key"

    // 构建WebSocket URL
    u := url.URL{
        Scheme: "ws",
        Host:   "localhost:18040",
        Path:   "/ws",
        RawQuery: "api_key=" + apiKey + "&platform=go_custom",
    }

    log.Printf("连接到 %s", u.String())

    // 建立WebSocket连接
    c, _, err := websocket.DefaultDialer.Dial(u.String(), nil)
    if err != nil {
        log.Fatal("连接失败:", err)
    }
    defer c.Close()

    // 构造 Payload
    payload := &Payload{
        MessageInfo: &MessageInfo{
            Platform:  "go_custom",
            MessageID: fmt.Sprintf("msg_%d", time.Now().UnixNano()),
            Time:      float64(time.Now().UnixNano()) / 1e9,
            SenderInfo: &SenderInfo{
                UserInfo: &UserInfo{
                    Platform:     "go_custom",
                    UserID:       "go_user_001",
                    UserNickname: "Go客户端",
                    UserCardname: "Go客户端",
                },
            },
        },
        MessageSegment: &MessageSegment{
            Type: "text",
            Data: "Hello from Go client!",
        },
        MessageDim: &MessageDim{
            APIKey:  apiKey,
            Platform: "go_custom",
        },
    }

    // 构造 Envelope
    envelope := &Envelope{
        Ver:    1,
        MsgID:  fmt.Sprintf("media_%d", time.Now().UnixNano()),
        Type:   "sys_std",
        Meta: &Meta{
            SenderUser: apiKey,
            Platform:   "go_custom",
            Timestamp:  float64(time.Now().UnixNano()) / 1e9,
        },
        Payload: payload,
    }

    messageBytes, err := json.Marshal(envelope)
    if err != nil {
        log.Fatal("JSON序列化失败:", err)
    }

    err = c.WriteMessage(websocket.TextMessage, messageBytes)
    if err != nil {
        log.Fatal("发送消息失败:", err)
    }

    log.Println("消息已发送")

    // 读取响应
    _, response, err := c.ReadMessage()
    if err != nil {
        log.Fatal("读取响应失败:", err)
    }

    log.Printf("收到响应: %s", response)
}
```

### C# (ClientWebSocket)

```csharp
using System;
using System.Net.WebSockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Newtonsoft.Json;

public class MaimMessageCSharpClient
{
    private readonly string _url;
    private readonly string _apiKey;
    private ClientWebSocket _webSocket;

    public MaimMessageCSharpClient(string url, string apiKey)
    {
        _url = url;
        _apiKey = apiKey;
    }

    public async Task ConnectAsync()
    {
        _webSocket = new ClientWebSocket();

        // 添加API Key到查询参数
        var uri = new Uri($"{_url}?api_key={_apiKey}");

        await _webSocket.ConnectAsync(uri, CancellationToken.None);
        Console.WriteLine("WebSocket连接已建立");
    }

    public async Task SendMessageAsync(string text)
    {
        if (_webSocket?.State != WebSocketState.Open)
        {
            throw new InvalidOperationException("WebSocket未连接");
        }

        // 构造 Payload
        var payload = new
        {
            message_info = new
            {
                platform = "csharp_custom",
                message_id = $"msg_{DateTime.Now.Ticks}",
                time = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                sender_info = new
                {
                    user_info = new
                    {
                        platform = "csharp_custom",
                        user_id = "cs_user_001",
                        user_nickname = "C#客户端",
                        user_cardname = "C#客户端"
                    }
                }
            },
            message_segment = new
            {
                type = "text",
                data = text
            },
            message_dim = new
            {
                api_key = _apiKey,
                platform = "csharp_custom"
            }
        };

        // 构造 Envelope
        var envelope = new
        {
            ver = 1,
            msg_id = $"env_{DateTime.Now.Ticks}",
            type = "sys_std",
            meta = new
            {
                sender_user = _apiKey,
                platform = "csharp_custom",
                timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds()
            },
            payload = payload
        };

        var json = JsonConvert.SerializeObject(envelope);
        var buffer = Encoding.UTF8.GetBytes(json);

        await _webSocket.SendAsync(
            new ArraySegment<byte>(buffer),
            WebSocketMessageType.Text,
            true,
            CancellationToken.None
        );

        Console.WriteLine($"消息已发送: {text}");
    }

    public async Task<string> ReceiveMessageAsync()
    {
        var buffer = new byte[4096];
        var result = await _webSocket.ReceiveAsync(
            new ArraySegment<byte>(buffer),
            CancellationToken.None
        );

        return Encoding.UTF8.GetString(buffer, 0, result.Count);
    }

    public async Task DisconnectAsync()
    {
        if (_webSocket != null)
        {
            await _webSocket.CloseAsync(
                WebSocketCloseStatus.NormalClosure,
                "客户端关闭",
                CancellationToken.None
            );
            _webSocket.Dispose();
        }
    }

    public static async Task Main(string[] args)
    {
        var client = new MaimMessageCSharpClient("ws://localhost:18040/ws", "your_api_key");

        await client.ConnectAsync();
        await client.SendMessageAsync("Hello from C# client!");

        var response = await client.ReceiveMessageAsync();
        Console.WriteLine($"收到响应: {response}");

        await client.DisconnectAsync();
    }
}
```

## SSL/TLS安全连接

### 连接要求

对于启用SSL的服务端，客户端需要：

1. **使用wss://协议**
2. **验证服务器证书**（生产环境）
3. **可能需要客户端证书**（双向认证）

### Python SSL示例

```python
import ssl
import websockets

async def ssl_client():
    # SSL上下文配置
    ssl_context = ssl.create_default_context()

    # 开发环境可以禁用证书验证
    # ssl_context.check_hostname = False
    # ssl_context.verify_mode = ssl.CERT_NONE

    # 生产环境应该加载CA证书
    # ssl_context.load_verify_locations("/path/to/ca.crt")

    uri = "wss://localhost:18044/ws?api_key=your_api_key&platform=csharp_custom"

    async with websockets.connect(uri, ssl=ssl_context) as websocket:
        # ... 消息发送接收逻辑
        pass
```

### JavaScript SSL示例

```javascript
// 浏览器会自动处理SSL证书验证
const wsUrl = 'wss://localhost:18044/ws?api_key=your_api_key&platform=javascript_secure';
const ws = new WebSocket(wsUrl);

// Node.js可能需要额外配置
const WebSocket = require('ws');
const ws = new WebSocket(wsUrl, {
    rejectUnauthorized: false  // 仅用于开发环境
});
```

## 错误处理

### 常见错误码和消息

| 错误类型     | 说明                         | 解决方案                 |
| ------------ | ---------------------------- | ------------------------ |
| 连接被拒绝   | 服务端未启动或端口错误       | 检查服务端状态和端口配置 |
| 认证失败     | API Key无效或缺失            | 检查API Key是否正确      |
| 消息格式错误 | JSON格式不正确或缺少必填字段 | 验证消息格式是否符合规范 |
| 连接超时     | 网络问题或服务端无响应       | 检查网络连接和服务端状态 |

### 错误处理示例

```python
try:
    async with websockets.connect(uri) as websocket:
        await websocket.send(json.dumps(message))
        response = await websocket.recv()
except websockets.exceptions.ConnectionClosed:
    print("连接已关闭")
except websockets.exceptions.InvalidURI:
    print("无效的WebSocket URI")
except json.JSONEncodeError:
    print("消息JSON格式错误")
except Exception as e:
    print(f"其他错误: {e}")
```

## 最佳实践

### 1. 连接管理

- 实现自动重连机制
- 监控连接状态
- 优雅关闭连接

### 2. 消息处理

- 验证消息格式完整性
- 处理大消息分片
- 实现消息确认机制
- 正确处理ACK确认消息，避免ACK消息循环
- 基于ACK消息实现消息传输可靠性监控

### 3. 性能优化

- 使用连接池
- 压缩大消息
- 异步处理消息

### 4. 安全考虑

- 生产环境必须使用SSL/TLS
- 定期轮换API Key
- 验证服务器证书

## 测试工具

### WebSocket测试客户端

推荐使用以下工具测试连接：

1. **Postman**: 支持WebSocket测试
2. **wscat**: 命令行WebSocket客户端
3. **浏览器开发者工具**: 内置WebSocket客户端

### 测试消息 (含信封)

```json
{
  "ver": 1,
  "msg_id": "test_msg_001",
  "type": "sys_std",
  "meta": {
    "sender_user": "test_api_key",
    "platform": "test_client",
    "timestamp": 1703123456.789
  },
  "payload": {
    "message_info": {
      "platform": "test_client",
      "message_id": "test_001",
      "time": 1703123456.789
    },
    "message_segment": {
      "type": "text",
      "data": "Test message"
    },
    "message_dim": {
      "api_key": "test_api_key",
      "platform": "test_client"
    }
  }
}
```

## 故障排除

### 调试步骤

1. 检查WebSocket连接状态
2. 验证HTTP头和查询参数
3. 确认消息JSON格式
4. 检查服务端日志
5. 使用网络抓包工具分析

### 常见问题

**Q: 连接建立成功但收不到消息响应**
A: 检查消息是否包含了每一层结构：**Envelope (type=sys_std)** -> **Payload (message_segment)**。缺少 Envelope 会导致服务器忽略消息。

**Q: 消息路由失败，接收方收不到消息**
A: 确认 message_dim.api_key 和 message_dim.platform 设置正确，这些字段指定**目标接收者**而不是发送者

**Q: SSL连接失败**
A: 确认使用wss://协议，检查证书配置，开发环境可以临时禁用证书验证

**Q: 消息发送成功但格式错误**
A: 确保JSON格式正确，字符串字段使用双引号，检查时间戳格式

**Q: 消息路由到了错误的用户**
A: 检查 message_dim.api_key 是否正确设置了目标接收者的API密钥，而不是发送者的API密钥

## 版本兼容性

- **WebSocket协议**: RFC 6455
- **JSON格式**: UTF-8编码
- **时间戳**: Unix时间戳（秒）
- **最低协议版本**: WebSocket Version 13

---

更多技术细节请参考：
- [WebSocket RFC 6455](https://tools.ietf.org/html/rfc6455)
- [maim_message API-Server使用指南](./api_server_usage_guide.md)
- [WebSocket安全最佳实践](https://tools.ietf.org/html/rfc6455#section-10)