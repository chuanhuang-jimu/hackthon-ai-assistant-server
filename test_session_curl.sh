#!/bin/bash

# 测试会话 API 的 curl 命令集合

BASE_URL="http://localhost:8000"

echo "=========================================="
echo "Gemini 会话 API 测试"
echo "=========================================="
echo ""

# 1. 检查会话状态（初始状态）
echo "【1】检查会话状态（初始）"
echo "----------------------------------------"
curl -X GET "${BASE_URL}/api/gemini/session/status" \
  -H "Content-Type: application/json"
echo ""
echo ""

# 2. 启动会话
echo "【2】启动会话"
echo "----------------------------------------"
curl -X POST "${BASE_URL}/api/gemini/session/start" \
  -H "Content-Type: application/json" \
  -d '{
    "mcp_servers": ["jira"],
    "approval_mode": "yolo"
  }'
echo ""
echo ""

# 等待会话启动
sleep 2

# 3. 检查会话状态（启动后）
echo "【3】检查会话状态（启动后）"
echo "----------------------------------------"
curl -X GET "${BASE_URL}/api/gemini/session/status" \
  -H "Content-Type: application/json"
echo ""
echo ""

# 4. 第一次聊天（会话模式 - 会自动启动会话）
echo "【4】第一次聊天（会话模式）"
echo "----------------------------------------"
curl -X POST "${BASE_URL}/api/gemini/chat-session" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "你好，请介绍一下你自己",
    "mcp_servers": ["jira"]
  }'
echo ""
echo ""

# 等待响应
sleep 5

# 5. 第二次聊天（复用同一个会话）
echo "【5】第二次聊天（复用会话，测试上下文保持）"
echo "----------------------------------------"
curl -X POST "${BASE_URL}/api/gemini/chat-session" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "你还记得我刚才说了什么吗？",
    "mcp_servers": ["jira"]
  }'
echo ""
echo ""

# 等待响应
sleep 5

# 6. 测试 JIRA 查询（会话模式）
echo "【6】测试 JIRA 查询（会话模式）"
echo "----------------------------------------"
curl -X POST "${BASE_URL}/api/gemini/chat-session" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "查询任务ORI-135098，中文返回",
    "mcp_servers": ["jira"]
  }'
echo ""
echo ""

# 等待响应
sleep 5

# 7. 检查会话状态（使用后）
echo "【7】检查会话状态（使用后）"
echo "----------------------------------------"
curl -X GET "${BASE_URL}/api/gemini/session/status" \
  -H "Content-Type: application/json"
echo ""
echo ""

# 8. 停止会话
echo "【8】停止会话"
echo "----------------------------------------"
curl -X POST "${BASE_URL}/api/gemini/session/stop" \
  -H "Content-Type: application/json"
echo ""
echo ""

# 9. 检查会话状态（停止后）
echo "【9】检查会话状态（停止后）"
echo "----------------------------------------"
curl -X GET "${BASE_URL}/api/gemini/session/status" \
  -H "Content-Type: application/json"
echo ""
echo ""

echo "=========================================="
echo "测试完成"
echo "=========================================="
