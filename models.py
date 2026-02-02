from pydantic import BaseModel
from typing import Optional, List


class ChatRequest(BaseModel):
    """聊天请求模型"""
    mock: Optional[bool] = False
    user_email: Optional[str] = "chuan.huang@veeva.com"
    jira_id: Optional[str] = None
    message: Optional[str] = ''
    prompt_key: Optional[str] = 'default'
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    mcp_servers: Optional[List[str]] = None  # 要使用的 MCP 服务器名称列表（如 ["geminix", "jira"]）
    approval_mode: Optional[str] = None  # 审批模式: "default", "auto_edit", "yolo" (默认: 使用 MCP 时自动设为 "yolo")
    args: Optional[List[str]] = None  # 自定义命令行参数


class ChatResponse(BaseModel):
    """聊天响应模型"""
    success: bool
    response: str
    error: Optional[str] = None  # 真正的错误消息
    logs: Optional[str] = None  # 信息性日志（非错误）

class SessionStartRequest(BaseModel):
    """会话启动请求模型"""
    model: Optional[str] = None
    mcp_servers: Optional[List[str]] = None
    approval_mode: str = "yolo"
