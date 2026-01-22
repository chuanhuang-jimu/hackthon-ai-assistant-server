from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from gemini_client import gemini_client
from gemini_session_simple import get_session

app = FastAPI(title="Personal Assistant API", version="1.o.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


class ChatRequest(BaseModel):
    """聊天请求模型"""
    mock: Optional[bool] = False
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


@app.post("/api/gemini/board/story/list", response_model=ChatResponse)
async def story_list(request: ChatRequest):
    """
     与 gemini-cli 交互的接口 (Jira Story Check 专用)
     固定使用 jira mcp server 并在 yolo 模式下运行
     """

    get_jira_board_story = """
    请按照以下步骤执行：
    step1: 获取看板[3485]状态为 'active' 的 sprint_id
    step2: 使用jira_search (jira MCP Server)获取当前sprint的story {"limit":50,"jql":"project = ORI AND sprint = {sprint_id} AND issuetype = Story"}
    step3: 对每一个筛选出的 Story，获取summary作为标题，标题中有提测时间，如果当前已经到达此时间了，状态还停留在'OPEN'或'DEVELOPMENT IN PROGRESS'，当前story则打上 tag delay
    step4: 按照当前jira返回顺序排序，并结合status进行二次排序，按照OPEN、DEVELOPMENT IN PROGRESS、DEVELOPMENT COMPLETE、QA IN PROGRESS、CLOSED
    step5: 对于每个story, 打上标签，标签规则如下：
         规则一：从summary中获取提测时间，如果当前已经到达此时间了，状态还停留在'OPEN'或'DEVELOPMENT IN PROGRESS'，'delay'的tag
         规则二：为第二个story打上risk标签

    最后，请不要输出任何多余的分析文字，直接返回一个 JSON 数组，格式严格遵守如下定义：
    [
      {
        "key": "Issue ID (例如 ORI-123)",
        "summary": "story的标题",
        "status": "当前状态",
        "tags": ['delay', 'risk'] 
      }
    ]
    """
    try:
        # 1. Mock 模式处理
        if request.mock:
            result = {
                "success": True,
                "response": "```json\n[\n  {\n    \"key\": \"ORI-114277\",\n    \"summary\": \"affect other 界面化补齐 longtext 类型字段 （1.19提测）✅\",\n    \"status\": \"Development Complete\"\n  },\n  {\n    \"key\": \"ORI-132922\",\n    \"summary\": \"【BR V2】BR v2 提示信息 on-tab（1.14）\",\n    \"status\": \"Development in Progress\"\n  }\n]\n```",
                "error": "",
                "logs": "YOLO mode is enabled. All tool calls will be automatically approved.\nLoaded cached credentials.\nServer 'jira' supports tool updates. Listening for changes..."
            }

        # 2. 真实调用逻辑
        else:
            # 强制指定参数：使用 jira server，开启 yolo 模式
            kwargs = {
                "approval_mode": "yolo"
            }

            result = gemini_client.chat(
                get_jira_board_story,
                model=request.model,
                mcp_servers=['jira'],  # 这里的逻辑是写死的，如你所愿
                **kwargs
            )

        # 3. 错误处理
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Unknown error occurred")
            )

        # 4. 返回结果
        print(f">>> story_list, {result['response']}")
        return ChatResponse(
            success=True,
            response=result["response"],
            error=result.get("error"),
            logs=result.get("logs")
        )

    except HTTPException:
        # 重新抛出已知的 HTTP 异常
        raise
    except Exception as e:
        # 捕获其他未知异常
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/api/gemini/story/check", response_model=ChatResponse)
async def story_check(request: ChatRequest):
    """
    与 gemini-cli 交互的接口 (Jira Story Check 专用)
    固定使用 jira mcp server 并在 yolo 模式下运行
    """
    jira_id = request.jira_id

    jira_story_check = f"""
        首先获取这个story {jira_id}，最新的进度，并告诉
        """

    try:
        # 1. Mock 模式处理
        if request.mock:
            result = {
                "success": True,
                "response": "```json\n111测试结果 测试结果 测试结果 测试结果 测试结果 测试结果 测试结果 测试结果 测试结果 测试结果 测试结果 测试结果 测试结果 测试结果 测试结果 \n 测试结果 测试结果 测试结果 测试结果 测试结果 测试结果 测试结果 测试结果 测试结果 测试结果 测试结果 测试结果 测试结果 测试结果 测试结果 测\n 测试结果 测试结果 测试结果 测试结果 测试结果 测试结果 测试结果 测试结果 测试结果 测试结果 测试结果 测试结果 测试结果 测```",
                "error": "",
                "logs": "YOLO mode is enabled. All tool calls will be automatically approved.\nLoaded cached credentials.\nServer 'jira' supports tool updates. Listening for changes..."
            }

        # 2. 真实调用逻辑
        else:
            # 强制指定参数：使用 jira server，开启 yolo 模式
            kwargs = {
                "approval_mode": "yolo"
            }

            result = gemini_client.chat(
                request.message,
                model=request.model,
                mcp_servers=['jira'],  # 这里的逻辑是写死的，如你所愿
                **kwargs
            )

        # 3. 错误处理
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Unknown error occurred")
            )

        # 4. 返回结果
        print(f">>> story_check, {request.jira_id}, {result['response']}")
        return ChatResponse(
            success=True,
            response=result["response"],
            error=result.get("error"),
            logs=result.get("logs")
        )

    except HTTPException:
        # 重新抛出已知的 HTTP 异常
        raise
    except Exception as e:
        # 捕获其他未知异常
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
