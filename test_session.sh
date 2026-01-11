#!/bin/bash

# 测试会话 API 的脚本

BASE_URL="http://localhost:8000"

echo "=========================================="
echo "测试 Gemini 会话 API"
echo "=========================================="
echo ""

# 1. 检查会话状态
echo "1. 检查会话状态（初始）"
echo "----------------------------------------"
curl -X GET "${BASE_URL}/api/gemini/session/status" \
  -H "Content-Type: application/json" \
  -w "\n\nHTTP Status: %{http_code}\n"
echo ""
echo ""

# 2. 启动会话
echo "2. 启动会话"
echo "----------------------------------------"
curl -X POST "${BASE_URL}/api/gemini/session/start" \
  -H "Content-Type: application/json" \
  -d '{
    "mcp_servers": ["jira"],
    "approval_mode": "yolo"
  }' \
  -w "\n\nHTTP Status: %{http_code}\n"
echo ""
echo ""

# 等待一下让会话启动
sleep 2

# 3. 检查会话状态（启动后）
echo "3. 检查会话状态（启动后）"
echo "----------------------------------------"
curl -X GET "${BASE_URL}/api/gemini/session/status" \
  -H "Content-Type: application/json" \
  -w "\n\nHTTP Status: %{http_code}\n"
echo ""
echo ""

# 4. 第一次聊天（应该启动会话）
echo "4. 第一次聊天（会话模式）"
echo "----------------------------------------"
curl -X POST "${BASE_URL}/api/gemini/chat-session" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "你好，请介绍一下你自己",
    "mcp_servers": ["jira"]
  }' \
  -w "\n\nHTTP Status: %{http_code}\n"
echo ""
echo ""

# 等待响应
sleep 3

# 5. 第二次聊天（应该复用会话）
echo "5. 第二次聊天（复用会话）"
echo "----------------------------------------"
curl -X POST "${BASE_URL}/api/gemini/chat-session" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "你还记得我刚才说了什么吗？",
    "mcp_servers": ["jira"]
  }' \
  -w "\n\nHTTP Status: %{http_code}\n"
echo ""
echo ""

# 6. 测试 JIRA 查询（会话模式）
echo "6. 测试 JIRA 查询（会话模式）"
echo "----------------------------------------"
curl -X POST "${BASE_URL}/api/gemini/chat-session" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "查询任务ORI-135098，中文返回",
    "mcp_servers": ["jira"]
  }' \
  -w "\n\nHTTP Status: %{http_code}\n"
echo ""
echo ""

# 7. 检查会话状态（使用后）
echo "7. 检查会话状态（使用后）"
echo "----------------------------------------"
curl -X GET "${BASE_URL}/api/gemini/session/status" \
  -H "Content-Type: application/json" \
  -w "\n\nHTTP Status: %{http_code}\n"
echo ""
echo ""

# 8. 停止会话
echo "8. 停止会话"
echo "----------------------------------------"
curl -X POST "${BASE_URL}/api/gemini/session/stop" \
  -H "Content-Type: application/json" \
  -w "\n\nHTTP Status: %{http_code}\n"
echo ""
echo ""

echo "=========================================="
echo "测试完成"
echo "=========================================="
