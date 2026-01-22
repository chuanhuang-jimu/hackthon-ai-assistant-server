# Personal Assistant API

基于 FastAPI 的个人助手 API 项目。

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行项目

```bash
uvicorn main:app --reload
```

服务启动后，访问：
- API 文档：http://localhost:8200/docs
- 替代文档：http://localhost:8200/redoc
- Hello World 接口：http://localhost:8200/

## API 接口

### 基础接口
- `GET /` - Hello World 接口
- `GET /hello` - Hello 接口

### Gemini CLI 接口
- `POST /api/gemini/chat` - 与本地 gemini-cli 交互
  - 请求体示例：
    ```json
    {
      "message": "你好，请介绍一下你自己",
      "model": "gemini-pro",
      "temperature": 0.7,
      "max_tokens": 1000
    }
    ```
  - 使用 MCP 服务器：
    ```json
    {
      "message": "查询 JIRA 任务",
      "mcp_servers": ["jira", "geminix"]
    }
    ```
    - 如果不指定 `mcp_servers`，将自动使用 `~/.gemini/settings.json` 中配置的所有 MCP 服务器
    - 如果指定了 `mcp_servers`，只使用指定的服务器
  - 或者使用自定义参数：
    ```json
    {
      "message": "你好",
      "args": ["--model", "gemini-pro", "--temperature", "0.7"]
    }
    ```

- `GET /api/gemini/health` - 检查 gemini-cli 是否可用
- `GET /api/gemini/mcp-servers` - 获取可用的 MCP 服务器列表（从 settings.json 读取）

## 使用示例

### 使用 curl 调用 Gemini 接口

```bash
# 简单聊天
curl -X POST "http://localhost:8200/api/gemini/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "你好，请介绍一下你自己"
  }'

# 指定模型和参数
curl -X POST "http://localhost:8200/api/gemini/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "解释一下量子计算",
    "model": "gemini-pro",
    "temperature": 0.7
  }'

# 检查 gemini-cli 状态
curl "http://localhost:8200/api/gemini/health"

# 查看可用的 MCP 服务器
curl "http://localhost:8200/api/gemini/mcp-servers"

# 使用 MCP 服务器进行聊天
curl -X POST "http://localhost:8200/api/gemini/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "使用 JIRA MCP 查询任务",
    "mcp_servers": ["jira"]
  }'
```

### 使用 Python 调用

```python
import requests

# 发送消息
response = requests.post(
    "http://localhost:8200/api/gemini/chat",
    json={
        "message": "你好",
        "model": "gemini-pro"
    }
)
print(response.json())
```

## MCP 服务器支持

API 支持使用 MCP (Model Context Protocol) 服务器：

1. **自动加载配置**：API 会自动从 `~/.gemini/settings.json` 读取 MCP 服务器配置
2. **使用所有服务器**：如果不指定 `mcp_servers` 参数，gemini 会自动使用 settings.json 中配置的所有服务器
3. **指定服务器**：通过 `mcp_servers` 参数可以指定要使用的服务器名称列表
4. **查看可用服务器**：使用 `GET /api/gemini/mcp-servers` 接口查看所有可用的 MCP 服务器

### MCP 服务器配置示例

在 `~/.gemini/settings.json` 中配置：

```json
{
  "mcpServers": {
    "geminix": {
      "httpUrl": "http://geminix.example.com/mcp"
    },
    "jira": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "mcp-server-image"]
    }
  }
}
```

## 注意事项

1. 确保本地已安装并配置好 `gemini-cli`
2. `gemini-cli` 需要在系统 PATH 中，或者可以通过 `GeminiCLIClient` 的 `cli_path` 参数指定路径
3. 接口会通过 subprocess 调用本地 gemini-cli，请确保有执行权限
4. MCP 服务器配置需要正确设置在 `~/.gemini/settings.json` 中
5. 如果使用 Docker 类型的 MCP 服务器（如 jira），确保 Docker 已安装并可访问