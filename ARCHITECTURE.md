# 架构说明：如何将 gemini-cli 转换为 HTTP API

## 整体架构

```
HTTP 客户端 (curl/浏览器/Postman)
    ↓ HTTP Request (POST /api/gemini/chat)
    ↓
FastAPI 服务器 (main.py)
    ↓ 调用 GeminiCLIClient
    ↓
GeminiCLIClient (gemini_client.py)
    ↓ 通过 subprocess 调用
    ↓
gemini 命令行工具 (本地可执行文件)
    ↓ 执行并返回结果
    ↓
GeminiCLIClient 解析输出
    ↓ 返回结构化数据
    ↓
FastAPI 返回 JSON 响应
    ↓
HTTP 客户端收到响应
```

## 核心实现原理

### 1. HTTP 层 (FastAPI) - `main.py`

**作用**：提供 HTTP 接口，接收请求并返回响应

**关键代码**：
```python
@app.post("/api/gemini/chat", response_model=ChatResponse)
async def chat_with_gemini(request: ChatRequest):
    # 接收 HTTP POST 请求
    # 将 JSON 请求体转换为 Python 对象
    # 调用 GeminiCLIClient 处理
    # 返回 JSON 响应
```

**数据流转换**：
- **输入**：HTTP JSON 请求
  ```json
  {
    "message": "查询任务",
    "mcp_servers": ["jira"]
  }
  ```
- **输出**：HTTP JSON 响应
  ```json
  {
    "success": true,
    "response": "gemini 的回复",
    "error": null,
    "logs": "信息性日志"
  }
  ```

### 2. 适配层 (GeminiCLIClient) - `gemini_client.py`

**作用**：将 HTTP 请求转换为命令行调用，并将命令行输出转换为结构化数据

#### 2.1 命令构建 (`chat` 方法)

**步骤 1：构建命令行参数**
```python
cmd = [self.cli_path]  # 例如: ["/opt/homebrew/bin/gemini"]

# 添加参数
if model:
    cmd.extend(["--model", model])
    
if mcp_servers:
    for server_name in mcp_servers:
        cmd.extend(["--allowed-mcp-server-names", server_name])
        
if approval_mode:
    cmd.extend(["--approval-mode", approval_mode])
```

**最终命令示例**：
```bash
/opt/homebrew/bin/gemini \
  --allowed-mcp-server-names jira \
  --approval-mode yolo
```

#### 2.2 执行命令 (`subprocess.run`)

**关键实现**：
```python
process = subprocess.run(
    cmd,                    # 命令列表
    input=message,          # 通过 stdin 传递用户消息
    stdout=subprocess.PIPE, # 捕获标准输出
    stderr=subprocess.PIPE, # 捕获标准错误
    text=True,              # 文本模式
    env=env,                # 增强的环境变量（包含 PATH 等）
    timeout=300             # 超时设置
)
```

**工作原理**：
1. **stdin**：将用户消息通过标准输入传递给 gemini
2. **stdout**：捕获 gemini 的正常输出（AI 回复）
3. **stderr**：捕获 gemini 的日志和错误信息
4. **环境变量**：确保包含必要的 PATH（如 Docker、gemini 路径）

#### 2.3 输出解析 (`_parse_stderr` 方法)

**问题**：gemini 会将信息性日志输出到 stderr，需要区分真正的错误和信息性消息

**解决方案**：
```python
def _parse_stderr(self, stderr: str) -> Tuple[Optional[str], Optional[str]]:
    # 区分错误和信息性消息
    # 信息性消息关键词：Loaded cached credentials, Server supports...
    # 错误消息关键词：error, failed, exception...
    
    if self._is_info_message(line):
        info_lines.append(line)  # 信息性日志
    else:
        error_lines.append(line)  # 真正的错误
```

**结果**：
- `error`：真正的错误消息
- `logs`：信息性日志（如 "Loaded cached credentials"）

### 3. 命令行工具层 (gemini)

**作用**：实际的 AI 处理引擎

**工作方式**：
- 从 stdin 读取用户消息
- 处理消息（可能调用 MCP 工具）
- 将回复输出到 stdout
- 将日志输出到 stderr

## 数据流详细说明

### 完整请求流程

```
1. HTTP 请求
   POST /api/gemini/chat
   Body: {"message": "查询任务ORI-135098", "mcp_servers": ["jira"]}
   
2. FastAPI 接收
   - 解析 JSON → ChatRequest 对象
   - 调用 chat_with_gemini(request)
   
3. GeminiCLIClient 处理
   - 构建命令: ["gemini", "--allowed-mcp-server-names", "jira", "--approval-mode", "yolo"]
   - 准备环境变量（包含 PATH、GOOGLE_CLOUD_PROJECT 等）
   - 执行 subprocess.run(cmd, input=message, ...)
   
4. gemini 执行
   - 读取 stdin 中的消息
   - 连接 Jira MCP 服务器
   - 调用 jira_get_issue 工具
   - 处理结果并生成回复
   - 输出到 stdout
   - 日志输出到 stderr
   
5. GeminiCLIClient 解析
   - stdout → response（AI 回复）
   - stderr → 解析为 error 和 logs
   - 返回结构化字典
   
6. FastAPI 响应
   - 转换为 ChatResponse 对象
   - 序列化为 JSON
   - 返回 HTTP 响应
   
7. HTTP 响应
   {
     "success": true,
     "response": "Jira 任务 ORI-135098 的详细信息...",
     "error": null,
     "logs": "YOLO mode is enabled..."
   }
```

## 关键技术点

### 1. 进程间通信 (IPC)

**使用 subprocess 的原因**：
- gemini 是独立的命令行工具，不是 Python 库
- 需要通过进程间通信来调用
- subprocess 提供了标准的方式

**通信方式**：
- **输入**：通过 `stdin` 传递消息（`input=message`）
- **输出**：通过 `stdout` 和 `stderr` 捕获结果

### 2. 环境变量管理

**问题**：PyCharm 启动时可能不继承系统环境变量

**解决方案**：
```python
def _get_enhanced_env(self) -> Dict[str, str]:
    env = os.environ.copy()
    # 确保 PATH 包含必要路径
    path_parts = env.get("PATH", "").split(os.pathsep)
    important_paths = [
        "/opt/homebrew/bin",      # gemini 路径
        "/Users/ChuanHuang/.orbstack/bin",  # Docker 路径
    ]
    # 添加缺失的路径
    env["PATH"] = os.pathsep.join(path_parts)
    return env
```

### 3. 错误处理

**分层错误处理**：
1. **subprocess 层**：捕获超时、文件未找到等系统错误
2. **解析层**：区分真正的错误和信息性消息
3. **API 层**：转换为 HTTP 错误响应

### 4. MCP 服务器支持

**配置读取**：
- 从 `~/.gemini/settings.json` 读取 MCP 服务器配置
- 支持 HTTP 类型（geminix）和命令类型（jira Docker）

**参数传递**：
```python
if mcp_servers:
    for server_name in mcp_servers:
        cmd.extend(["--allowed-mcp-server-names", server_name])
```

## 优势与限制

### 优势

1. **无需修改 gemini 源码**：通过命令行接口调用
2. **保持 gemini 功能完整**：支持所有命令行参数和功能
3. **易于维护**：gemini 更新不影响适配层
4. **支持 MCP**：完整支持 MCP 服务器功能

### 限制

1. **性能开销**：每次请求都启动新进程
   - 使用 `subprocess.run()` 是同步阻塞调用
   - 每次请求完成后，gemini 进程会自动关闭
   - 下次请求需要重新启动进程，有启动开销
   
2. **状态管理**：无法保持会话状态（每次都是新调用）
   - 每次请求都是独立的进程
   - 无法保持对话上下文（除非 gemini 支持会话文件）
   
3. **连接复用**：无法复用 MCP 服务器连接
   - 每次请求都需要重新连接 MCP 服务器
   - 可能影响性能（特别是 HTTP 类型的 MCP 服务器）
   
4. **错误处理**：需要解析命令行输出，可能不够精确
5. **环境依赖**：需要确保 gemini 和依赖工具（如 Docker）在 PATH 中

## 改进方向

### 1. 进程池/长连接（如果 gemini 支持）

**当前实现**：每次请求启动新进程
```python
# 当前：subprocess.run() - 同步，进程自动关闭
process = subprocess.run(cmd, ...)
```

**改进方案**：保持进程运行
```python
# 改进：subprocess.Popen() - 保持进程运行
process = subprocess.Popen(cmd, stdin=PIPE, stdout=PIPE, ...)
# 可以多次向同一个进程发送请求
process.stdin.write(message1)
process.stdin.write(message2)
# 需要手动管理进程生命周期
```

**优点**：
- 减少启动开销
- 可以保持会话状态
- 可以复用 MCP 连接

**缺点**：
- 需要管理进程生命周期
- 需要处理进程崩溃
- 需要处理并发请求（可能需要进程池）

### 2. 其他改进

- **缓存**：缓存常见请求的响应
- **异步处理**：对于长时间运行的请求，可以异步处理
- **WebSocket 支持**：支持流式响应
- **进程池**：维护多个 gemini 进程，实现连接复用

## 总结

这个实现通过以下方式将 gemini-cli 转换为 HTTP API：

1. **FastAPI** 提供 HTTP 接口层
2. **GeminiCLIClient** 作为适配层，将 HTTP 请求转换为命令行调用
3. **subprocess** 执行 gemini 命令并捕获输出
4. **输出解析** 将命令行输出转换为结构化 JSON 响应

这种架构的优点是**解耦**：HTTP API 层和命令行工具层完全分离，可以独立更新和维护。
