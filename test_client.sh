#!/bin/bash

# FastAPI Gemini Client 测试脚本
# 使用方法: bash test_client.sh

BASE_URL="http://localhost:8000"

echo "=========================================="
echo "FastAPI Gemini Client 测试"
echo "=========================================="
echo ""

# 1. 测试基础接口
echo "1. 测试 Hello World 接口"
echo "----------------------------------------"
curl -X GET "${BASE_URL}/" \
  -H "Content-Type: application/json" \
  -w "\n\nHTTP Status: %{http_code}\n"
echo ""
echo ""

# 2. 测试 Health 检查接口
echo "2. 测试 Gemini Health 检查接口"
echo "----------------------------------------"
curl -X GET "${BASE_URL}/api/gemini/health" \
  -H "Content-Type: application/json" \
  -w "\n\nHTTP Status: %{http_code}\n"
echo ""
echo ""

# 3. 测试简单聊天接口
echo "3. 测试简单聊天接口"
echo "----------------------------------------"
curl -X POST "${BASE_URL}/api/gemini/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "你好，请介绍一下你自己"
  }' \
  -w "\n\nHTTP Status: %{http_code}\n"
echo ""
echo ""

# 4. 测试带模型参数的聊天接口
echo "4. 测试带模型参数的聊天接口"
echo "----------------------------------------"
curl -X POST "${BASE_URL}/api/gemini/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "解释一下量子计算",
    "model": "gemini-pro",
    "temperature": 0.7
  }' \
  -w "\n\nHTTP Status: %{http_code}\n"
echo ""
echo ""

# 5. 测试带自定义参数的聊天接口
echo "5. 测试带自定义参数的聊天接口"
echo "----------------------------------------"
curl -X POST "${BASE_URL}/api/gemini/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "写一首关于春天的诗",
    "args": ["--model", "gemini-pro", "--temperature", "0.8"]
  }' \
  -w "\n\nHTTP Status: %{http_code}\n"
echo ""
echo ""

# 6. 测试带所有参数的聊天接口
echo "6. 测试带所有参数的聊天接口"
echo "----------------------------------------"
curl -X POST "${BASE_URL}/api/gemini/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "什么是人工智能？",
    "model": "gemini-pro",
    "temperature": 0.9,
    "max_tokens": 500
  }' \
  -w "\n\nHTTP Status: %{http_code}\n"
echo ""
echo ""

echo "=========================================="
echo "测试完成"
echo "=========================================="
