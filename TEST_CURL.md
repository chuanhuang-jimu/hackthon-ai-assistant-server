# 会话 API 测试 curl 命令

## 快速测试命令

### 1. 检查会话状态
```bash
curl -X GET "http://localhost:8000/api/gemini/session/status" \
  -H "Content-Type: application/json"
```

### 2. 启动会话
```bash
curl -X POST "http://localhost:8000/api/gemini/session/start" \
  -H "Content-Type: application/json" \
  -d '{
    "mcp_servers": ["jira"],
    "approval_mode": "yolo"
  }'
```

### 3. 第一次聊天（会话模式 - 会自动启动会话）
```bash
curl -X POST "http://localhost:8000/api/gemini/chat-session" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "你好，请介绍一下你自己",
    "mcp_servers": ["jira"]
  }'
```

### 4. 第二次聊天（复用同一个会话）
```bash
curl -X POST "http://localhost:8000/api/gemini/chat-session" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "你还记得我刚才说了什么吗？",
    "mcp_servers": ["jira"]
  }'
```

### 5. 测试 JIRA 查询（会话模式）
```bash
curl -X POST "http://localhost:8000/api/gemini/chat-session" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "查询任务ORI-135098，中文返回",
    "mcp_servers": ["jira"]
  }'
```

### 6. 停止会话
```bash
curl -X POST "http://localhost:8000/api/gemini/session/stop" \
  -H "Content-Type: application/json"
```

## 完整测试流程

### 方式一：使用测试脚本
```bash
bash test_session_curl.sh
```

### 方式二：手动执行（推荐用于调试）

**步骤 1：检查初始状态**
```bash
curl -X GET "http://localhost:8000/api/gemini/session/status"
```

**步骤 2：第一次聊天（会自动启动会话）**
```bash
curl -X POST "http://localhost:8000/api/gemini/chat-session" \
  -H "Content-Type: application/json" \
  -d '{"message": "你好", "mcp_servers": ["jira"]}'
```

**步骤 3：等待响应后，第二次聊天**
```bash
curl -X POST "http://localhost:8000/api/gemini/chat-session" \
  -H "Content-Type: application/json" \
  -d '{"message": "继续对话", "mcp_servers": ["jira"]}'
```

**步骤 4：检查会话状态**
```bash
curl -X GET "http://localhost:8000/api/gemini/session/status"
```

**步骤 5：停止会话**
```bash
curl -X POST "http://localhost:8000/api/gemini/session/stop"
```

## 对比测试

### 普通模式（每次新进程）
```bash
curl -X POST "http://localhost:8000/api/gemini/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "查询任务ORI-135098", "mcp_servers": ["jira"]}'
```

### 会话模式（复用进程）
```bash
curl -X POST "http://localhost:8000/api/gemini/chat-session" \
  -H "Content-Type: application/json" \
  -d '{"message": "查询任务ORI-135098", "mcp_servers": ["jira"]}'
```

## 预期结果

### 会话模式的优势
1. **首次请求**：启动进程（可能稍慢）
2. **后续请求**：复用进程（应该更快）
3. **上下文保持**：可以记住之前的对话
4. **MCP 连接复用**：不需要重新连接 MCP 服务器

### 验证方法
- 检查会话状态：`is_running` 和 `process_alive` 应该为 `true`
- 多次请求：观察响应时间（后续请求应该更快）
- 上下文测试：询问"你还记得..."来验证上下文保持
