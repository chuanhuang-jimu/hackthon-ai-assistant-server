import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List

from analyze_data_storage import parse_to_json, get_story_description
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


@app.get("/story/description")
async def story_description(sprint_name, story_id):
    return get_story_description(sprint_name, story_id)


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
                mcp_servers=['jira'],
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

    jira_story_check = """
    # Role
    你是一名资深的敏捷交付经理 (Delivery Manager)。你的核心能力是能够从海量的 Jira 数据中抽丝剥茧，既能总结出 Story 维度的宏观进展，又能精确还原团队成员每日的微观工作细节。

    # ⛔ CRITICAL SAFETY PROTOCOL (严禁死循环)
    **必须严格遵守以下规则，以防止工具调用死循环：**
    1.  **单次调用原则**：你被严格限制为**只能执行 1 次** `jira_search` 工具调用。
    2.  **禁止遍历详情**：严禁对搜索结果列表进行遍历，严禁对子任务单独调用 `jira_get_issue`、`jira_get_worklog` 或 `jira_get_comment`。
    3.  **接受数据截断**：如果 `jira_search` 返回的 comment 或 worklog 列表显示不全（例如有分页），**直接忽略未获取的部分**，仅基于当前响应中已有的数据进行分析。不要尝试翻页。

    # Goal
    针对指定的 Jira Story ({{STORY_KEY}})，基于**单次查询**的数据，生成一份**“全景进度日报”**。
    重点关注：整体水位（Story 完成度/风险）与 成员轨迹（过去两天的具体产出）。

    # Workflow
    ## 第一步：获取当前 Sprint 信息
    通过 `jira_get_sprints_from_board` 获取看板 **[3485]** 中状态为 **'active'** 的 Sprint 列表。
    * **Action**: 提取返回结果中的 `name` 赋值给变量 **`SPRINT_ID`**。

    ## 第二步：单次全量获取 (Single Shot)
    执行且仅执行一次 `jira_search`。
    * **JQL**: `parent = {{STORY_KEY}} OR key = {{STORY_KEY}}`
    * **Fields**: `summary, status, priority, issuetype, assignee, comment, worklog, updated, created, resolution`
        * *说明*：严格请求标准字段 `issuetype` 以确定任务类型，请求 `resolution` 以辅助判断完成情况。
    * **Limit**: `100`

    ## 第三步：时间窗口锁定
    获取当前日期，计算出以下两个绝对日期用于筛选：
    * **Target_Date_1 (昨天)**
    * **Target_Date_2 (前天)**
    * *筛选标准*：后续仅提取 `created` (评论) 或 `started` (工时) 落在 [前天 00:00:00] 至 [昨天 23:59:59] 之间的数据。

    ## 第四步：内存数据处理 (无额外工具调用)
    仅利用第二步返回的 JSON 数据，在内存中进行逻辑处理：

    1.  **宏观分析 (Story 视角)**
        * 统计子任务状态 (Todo/In Progress/Done)。
        * **风险识别**：基于 `issuetype` 检查是否有未关闭的 Defect/Bug，或 High/Critical 优先级的未完成任务。
        * **最新结论**：提取父 Story 以及 子任务中最近24H评论，综合生成当前story的进展摘要。

    2.  **微观分析 (人员视角)**
        * 初始化 `Activity_Log`。
        * 遍历列表中的每一个 Issue，执行**类型严格映射**（不猜测，严格依赖字段）：
            * **检查 `fields.issuetype.name`**：
                * 若包含 'Defect'、'Bug' 或 'Story Defect' -> 标记为 `defect`
                * 其他情况 -> 标记为 `task`
        * 遍历 Comment 和 Worklog：
            * 检查 `fields.comment.comments` 数组：若时间匹配，提取 {人, 具体日期(yyyy-MM-dd), Issue Key, Issue Summary, 内容, 映射后的类型}。
            * 检查 `fields.worklog.worklogs` 数组：若时间匹配，提取 {人, 具体日期(yyyy-MM-dd), Issue Key, Issue Summary, 耗时, 内容, 映射后的类型}。
        * **数据聚合逻辑**：
            1. 先按 **[成员姓名]** 进行一级分组。
            2. 在每个成员下，按 **[Issue Key]** 进行二级分组。
            3. 对同一 Issue 下的记录，按 **[日期]** 升序排列（从前天到昨天）。

    # Output Format (Markdown)

    请严格按照以下格式输出：

    ## 🚁 {{SPRINT_ID}} : {{STORY_KEY}} 整体进展综述
    > **当前状态**: [Story Status] | **整体进度**: [已完成子任务数]/[总子任务数]
    > **风险提示**: [无风险 / 🔴 有 N 个严重缺陷未修复 / 🟠 进度滞后]

    **📝 最新情况摘要**:
    (基于现有数据，用 2-3 句话总结 Story 状态)

    ---

    ## 👥 团队成员详细动态 (过去两天)

    *(仅展示有数据的成员)*

    **格式强制要求：**
    1. **层级结构**：一级标题为成员，二级结构为该成员处理的具体子任务 (Key - Summary)。
    2. **进展对比**：在子任务下方，必须按日期**升序**（先Target_Date_2，后Target_Date_1）列出动态，以便形成“昨天 vs 前天”的进展对比。
    3. **日期格式**：必须展示具体日期 (yyyy-MM-dd)，严禁使用相对词汇。

    ### 👤 [成员姓名]

    #### 🔹 [Issue Key] [Issue Summary] ([🔴 defect / 🔵 task])
    * **[2024-05-20]**:
        * **[Worklog 2h]** 进行接口调试，遇到参数校验报错。
    * **[2024-05-21]**:
        * **[Worklog 4h]** 修复参数校验问题，接口已调通，开始编写单元测试。
        * **[Comment]** 提测包已部署到 Dev 环境。

    #### 🔹 [Issue Key] [Issue Summary] ([🔴 defect / 🔵 task])
    * **[2024-05-20]**:
        * **[Comment]** 正在排查登录失效的问题。
    * **[2024-05-21]**:
        * *(无新增动态)*

    *(如果有更多成员，继续列出)*

    ---
    *注：报表生成时间 {{CURRENT_DATE}}*
    """

    jira_story_check = jira_story_check.replace("{{STORY_KEY}}", request.jira_id)
    jira_story_check = jira_story_check.replace("{{CURRENT_DATE}}", datetime.datetime.now().strftime("%Y-%m-%d"))
    try:
        # 1. Mock 模式处理
        if request.mock:
            result = {
                "success": True,
                "response": "## 🚁 Plum 25R3.2 Sprint 2 : ORI-114277 整体进展综述\n> **当前状态**: QA In Progress | **整体进度**: 4/11\n> **风险提示**: 🟠 进度滞后\n\n**📝 最新情况摘要**:\nStory 主要研发工作已完成并转入测试阶段。过去两天，开发人员 Garry Peng 集中处理了三个相关的子任务/缺陷，并记录了 3.5 小时工时，主要解决了多个富文本字段在特定场景下的显示和值清空问题。QA 负责人 Zijie Tang 已开始介入，并要求提供用于PS代码自定义逻辑的Demo数据。\n\n---\n\n## 👥 团队成员详细动态 (过去两天)\n\n### 👤 Chuan Huang\n\n#### 🔹 ORI-136135 【admin】longtext 字段在初始拖入页面时，设置关联字段的固定值输入框，没有展示富文本样式 ([🔵 task])\n* **2026-01-23**:\n    * **[Comment]** [~garry.peng@veeva.com] feature/ORI-136135/admin-affect-others-support-long-text\n上面分支加上了\n\n### 👤 Garry Peng\n\n#### 🔹 ORI-136183 【admin】 longtext 字段为文本类型时，配置字段影响关系页面，在关联字段配置固定值处输入带标签的内容，在预览页面会变成富文本的样式 ([🔵 task])\n* **2026-01-23**:\n    * **[Worklog 1h]** \n\n#### 🔹 ORI-136135 【admin】longtext 字段在初始拖入页面时，设置关联字段的固定值输入框，没有展示富文本样式 ([🔵 task])\n* **2026-01-22**:\n    * **[Worklog 30m]** \n    * **[Comment]** /admin-api/object/\\{object_id}/page-layout/\\{layout_id}/ 接口返回的 all_fields 中的字段也需要带上 text_type [~chuan.huang@veeva.com] \n\n!image-2026-01-22-17-37-48-539.png!\n* **2026-01-23**:\n    * **[Worklog 1h]** \n\n#### 🔹 ORI-136130 【online】 控制字段将longtext 字段 带入值后，再将控制字段的值清空，longtext 字段的值未清空 ([🔴 defect])\n* **2026-01-22**:\n    * **[Worklog 1h 30m]** \n\n### 👤 Zijie Tang\n\n#### 🔹 ORI-136130 【online】 控制字段将longtext 字段 带入值后，再将控制字段的值清空，longtext 字段的值未清空 ([🔴 defect])\n* **2026-01-22**:\n    * **[Comment]** wechat 端同样存在这个问题\n\n---\n*注：报表生成时间 2026-01-24*",
                "error": None,
                "logs": "YOLO mode is enabled. All tool calls will be automatically approved.\nLoaded cached credentials.\nServer 'jira' supports tool updates. Listening for changes..."
            }

        # 2. 真实调用逻辑
        else:
            # 强制指定参数：使用 jira server，开启 yolo 模式
            kwargs = {
                "approval_mode": "yolo"
            }

            result = gemini_client.chat(
                jira_story_check,
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

        parse_to_json(result['response'], request.jira_id)
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
