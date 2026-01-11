# 长连接会话实现方案

## 需求分析

- **首次 chat**：启动一个 gemini-cli 进程
- **后续 chat**：在同一个进程和会话中继续对话
- **保持状态**：对话上下文、MCP 连接等

## 实现思路

### 方案 1：使用 `--prompt-interactive` 模式（推荐）

gemini 支持 `--prompt-interactive` 参数来启动交互模式，可以保持进程运行。

**优点**：
- 官方支持
- 可以保持会话状态
- 可以复用 MCP 连接

**挑战**：
- 需要处理输入/输出的同步
- 需要区分不同请求的响应
- 需要处理并发请求

### 方案 2：使用 `--resume` 参数

gemini 支持 `--resume` 来恢复之前的会话。

**优点**：
- 可以恢复历史会话
- 保持对话上下文

**缺点**：
- 仍然需要每次启动新进程
- 需要管理会话文件

### 方案 3：混合方案（推荐用于生产）

结合两种方案：
1. 首次请求：启动交互式进程，保存会话 ID
2. 后续请求：使用 `--resume` 恢复会话，或继续使用交互式进程

## 实现架构

```
┌─────────────────┐
│  FastAPI Server │
└────────┬────────┘
         │
         ↓
┌─────────────────────┐
│ SessionManager      │
│ - 管理进程生命周期  │
│ - 处理请求队列      │
│ - 同步响应          │
└────────┬────────────┘
         │
         ↓
┌─────────────────────┐
│ GeminiSessionClient │
│ - start_session()   │
│ - chat()            │
│ - stop_session()    │
└────────┬────────────┘
         │
         ↓
┌─────────────────────┐
│ subprocess.Popen    │
│ (交互式进程)        │
└─────────────────────┘
```

## 关键技术点

### 1. 进程管理

```python
# 使用 Popen 而不是 run
process = subprocess.Popen(
    cmd,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=1  # 行缓冲
)
```

### 2. 输入/输出处理

**问题**：如何区分不同请求的响应？

**解决方案**：
- 方案 A：使用分隔符（如 `\n---END---\n`）
- 方案 B：使用请求 ID 标记
- 方案 C：按顺序处理（单线程队列）

### 3. 并发处理

**问题**：多个 HTTP 请求同时到达怎么办？

**解决方案**：
- 使用请求队列（FIFO）
- 使用锁确保线程安全
- 或者使用异步队列（asyncio.Queue）

### 4. 进程健康检查

```python
# 检查进程是否还在运行
if process.poll() is not None:
    # 进程已退出，需要重启
    restart_session()
```

## 实现步骤

### 步骤 1：创建 SessionManager

管理全局会话实例，确保单例模式。

### 步骤 2：实现 GeminiSessionClient

- `start_session()`: 启动交互式进程
- `chat()`: 发送消息并等待响应
- `stop_session()`: 停止进程

### 步骤 3：集成到 FastAPI

- 首次请求：启动会话
- 后续请求：复用会话
- 可选：添加会话超时机制

### 步骤 4：处理边界情况

- 进程崩溃：自动重启
- 超时：清理并重试
- 并发请求：队列化处理

## 代码示例

### 基础实现

```python
class GeminiSessionClient:
    def __init__(self):
        self.process = None
        self.is_running = False
        self.lock = threading.Lock()
    
    def start_session(self):
        cmd = ["gemini", "--prompt-interactive", ""]
        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        self.is_running = True
    
    def chat(self, message: str):
        if not self.is_running:
            self.start_session()
        
        # 发送消息
        self.process.stdin.write(message + "\n")
        self.process.stdin.flush()
        
        # 读取响应（需要实现响应解析逻辑）
        response = self._read_response()
        return response
```

### 响应解析

**关键挑战**：如何知道响应何时结束？

可能的策略：
1. **固定格式**：gemini 输出特定结束标记
2. **超时检测**：如果一段时间没有新输出，认为响应完成
3. **长度限制**：响应达到一定长度后认为完成
4. **模式匹配**：检测特定的输出模式

## 注意事项

1. **gemini 的输出格式**：需要实际测试来确定如何解析响应
2. **并发安全**：确保多线程环境下的安全性
3. **资源清理**：确保进程在应用退出时被正确清理
4. **错误处理**：处理进程崩溃、超时等情况

## 测试建议

1. **单请求测试**：验证基本功能
2. **多请求测试**：验证会话保持
3. **并发测试**：验证线程安全
4. **崩溃恢复测试**：验证自动重启
5. **长时间运行测试**：验证资源泄漏

## 备选方案

如果交互式模式实现复杂，可以考虑：

1. **会话文件**：使用 `--resume` 参数，每次请求后保存会话
2. **进程池**：维护多个 gemini 进程，实现连接复用
3. **混合模式**：短请求用 run，长对话用 session
