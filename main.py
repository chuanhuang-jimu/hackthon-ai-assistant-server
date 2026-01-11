from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from gemini_client import gemini_client
from gemini_session_simple import get_session

app = FastAPI(title="Personal Assistant API", version="1.0.0")


class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str
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


@app.get("/")
async def hello_world():
    """Hello World 接口"""
    return {"message": "Hello World"}


@app.get("/hello")
async def hello():
    """另一个 Hello 接口"""
    return {"message": "Hello from FastAPI!"}


@app.post("/api/gemini/chat", response_model=ChatResponse)
async def chat_with_gemini(request: ChatRequest):
    """
    与 gemini-cli 交互的接口
    
    发送消息到本地 gemini-cli 并返回响应
    """
    try:
        # 如果提供了自定义参数，使用 chat_with_args
        if request.args:
            result = gemini_client.chat_with_args(request.message, request.args)
        else:
            # 构建 kwargs
            kwargs = {}
            if request.temperature is not None:
                kwargs["temperature"] = request.temperature
            if request.max_tokens is not None:
                kwargs["max_tokens"] = request.max_tokens
            if request.approval_mode is not None:
                kwargs["approval_mode"] = request.approval_mode
            
            # 如果使用了 MCP 服务器但没有指定审批模式，默认使用 yolo 模式以自动批准工具执行
            approval_mode = request.approval_mode
            if approval_mode is None and request.mcp_servers:
                approval_mode = "yolo"
                kwargs["approval_mode"] = approval_mode
            
            result = gemini_client.chat(
                request.message,
                model=request.model,
                mcp_servers=request.mcp_servers,
                **kwargs
            )
        
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Unknown error occurred")
            )
        
        return ChatResponse(
            success=True,
            response=result["response"],
            error=result.get("error"),
            logs=result.get("logs")
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/gemini/health")
async def gemini_health():
    """
    检查 gemini-cli 是否可用（快速检查，不执行实际命令）
    """
    return gemini_client.is_available()


@app.get("/api/gemini/mcp-servers")
async def get_mcp_servers():
    """
    获取可用的 MCP 服务器列表（从 settings.json 读取）
    """
    servers = gemini_client.get_available_mcp_servers()
    server_details = {}
    for server_name in servers:
        server_config = gemini_client._mcp_servers.get(server_name, {})
        server_details[server_name] = {
            "name": server_name,
            "type": "http" if "httpUrl" in server_config else "command" if "command" in server_config else "unknown",
            "config": server_config
        }
    
    return {
        "available_servers": servers,
        "server_details": server_details
    }


@app.post("/api/gemini/chat-session", response_model=ChatResponse)
async def chat_with_gemini_session(request: ChatRequest):
    """
    使用会话模式与 gemini-cli 交互（长连接）
    
    首次请求会启动一个 gemini 进程，后续请求会复用同一个进程和会话
    这样可以保持对话上下文和 MCP 连接
    """
    try:
        session = get_session()
        
        # 如果使用了 MCP 服务器但没有指定审批模式，默认使用 yolo 模式
        approval_mode = request.approval_mode
        if approval_mode is None and request.mcp_servers:
            approval_mode = "yolo"
        
        # 确保会话已启动（如果还没启动）
        if not session.is_running:
            success = session.start(
                model=request.model,
                mcp_servers=request.mcp_servers,
                approval_mode=approval_mode or "yolo"
            )
            if not success:
                raise HTTPException(
                    status_code=500,
                    detail="无法启动 gemini 会话"
                )
        
        # 发送消息
        result = session.chat(request.message, timeout=300)
        
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Unknown error occurred")
            )
        
        return ChatResponse(
            success=True,
            response=result["response"],
            error=result.get("error"),
            logs=result.get("logs")
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


class SessionStartRequest(BaseModel):
    """会话启动请求模型"""
    model: Optional[str] = None
    mcp_servers: Optional[List[str]] = None
    approval_mode: str = "yolo"


@app.post("/api/gemini/session/start")
async def start_session(request: Optional[SessionStartRequest] = None):
    """
    手动启动会话
    
    如果会话已经在运行，会返回当前状态
    """
    try:
        session = get_session()
        
        if session.is_running:
            return {
                "success": True,
                "message": "会话已初始化",
                "is_running": True
            }
        
        req = request or SessionStartRequest()
        success = session.start(
            model=req.model,
            mcp_servers=req.mcp_servers,
            approval_mode=req.approval_mode
        )
        
        if success:
            return {
                "success": True,
                "message": "会话已启动",
                "is_running": True
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="无法启动会话"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/api/gemini/session/stop")
async def stop_session():
    """
    停止会话
    """
    try:
        session = get_session()
        session.stop()
        
        return {
            "success": True,
            "message": "会话已停止",
            "is_running": False
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/gemini/session/status")
async def get_session_status():
    """
    获取会话状态
    """
    try:
        session = get_session()
        
        return {
            "is_running": session.is_running,
            "session_initialized": session.session_initialized,
            "session_id": session.session_id,
            "model": session.model,
            "mcp_servers": session.mcp_servers,
            "approval_mode": session.approval_mode
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
