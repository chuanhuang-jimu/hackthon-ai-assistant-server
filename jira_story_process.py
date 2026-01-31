import datetime

from models import ChatResponse, ChatRequest
from fastapi import HTTPException, APIRouter
from analyze_data_storage import parse_to_json, get_story_description
from gemini_client import gemini_client
from redis_utils import query_redis, set_redis
import json

router = APIRouter()


@router.get("/story/description")
async def story_description(story_id):
    """
    给浏览器油猴用的
    """
    return get_story_description(story_id)



@router.post("/api/gemini/board/personal/task/processing", response_model=ChatResponse)
async def personal_task_processing(request: ChatRequest):
    get_personal_tasks_prompt = """
    请按照以下步骤执行：
    step1: 获取看板[3485]状态为 'active' 的 sprint_id。
    step2: 使用 jira_search (jira MCP Server) 获取当前sprint下，用户名为 '{{USER_EMAIL}}' 的正在进行中的task和defect。
    step3: 检查每个正在进行中的任务，获取已log时间和剩余时间，并检查是否有当天的work_log及其备注。
    step4: 最后，请不要输出任何多余的分析文字，直接返回一个 JSON 数组，格式严格遵守如下定义：
    [
        {
            "jira_id": "ORI-XXX",
            "sumamry": "任务标题",
            "today_work_hours": "今日log工时",
            "comment": "进度备注",
            "logged": "已log时间",
            "remaining": "剩余时间"
        }
    ]
    """
    prompt = get_personal_tasks_prompt.replace("{{USER_EMAIL}}", request.user_email)

    try:
        if request.mock:
            # Mock response for testing
            mock_response = [
                {
                    "jira_id": "ORI-12345",
                    "sumamry": "这是一个测试任务",
                    "today_work_hours": "2h",
                    "comment": "完成了大部分功能",
                    "logged": "4h",
                    "remaining": "1d"
                }
            ]
            return ChatResponse(
                success=True,
                response=json.dumps(mock_response, indent=4),
                error=None,
                logs="Mock response returned."
            )

        kwargs = {
            "approval_mode": "yolo"
        }
        result = gemini_client.chat(
            prompt,
            model=request.model,
            mcp_servers=['jira'],
            **kwargs
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Unknown error occurred during gemini chat")
            )

        response_content = result.get('response', '')
        # Extract JSON from the response
        if '```json' in response_content:
            json_str = response_content.split('```json')[1].split('```')[0].strip()
        else:
            json_str = response_content

        try:
            # Validate if it's a valid JSON
            json.loads(json_str)
            final_response = json_str
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="Failed to parse JSON from response")

        return ChatResponse(
            success=True,
            response=final_response,
            error=result.get("error"),
            logs=result.get("logs")
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/api/gemini/board/story/list", response_model=ChatResponse)
async def story_list(request: ChatRequest):
    """
    查看看板下当前sprint正在进行的story，并打上风险标记
    """
    # 规则获取
    delay_rules = []
    risk_rules = []

    tags_data = query_redis('get', 'scrum_master_tag_rules')
    for tag in tags_data:
        if tag.get('tagName', '') == 'delay':
            delay_rules += tag.get('rules', [])
        elif tag.get('tagName', '') == 'risk':
            risk_rules += tag.get('rules', [])

    get_jira_board_story = """
    请按照以下步骤执行：
    step1: 获取看板[3485]状态为 'active' 的 sprint_id
    step2: 使用jira_search (jira MCP Server)获取当前sprint的story {"limit":50,"jql":"project = ORI AND sprint = {sprint_id} AND issuetype = Story"}
    step3: 按照当前jira返回顺序排序，并结合status进行二次排序，按照OPEN、DEVELOPMENT IN PROGRESS、DEVELOPMENT COMPLETE、QA IN PROGRESS、CLOSED
    step4: 对于每个story, 打上标签，标签规则如下，注意如果规则依赖其他信息 请调用合适的MCP获取更多信息
         delay规则有：
{{DELAY_RULES}}
         risk规则有：
{{RISK_RULES}}

    最后，请不要输出任何多余的分析文字，直接返回一个 JSON 数组，格式严格遵守如下定义：
    [
        {
            "key": "Issue ID (例如 ORI-123)",
            "summary": "story的标题",
            "status": "当前状态",
            "tags": {
                "delay": [
                    "风险x(x为命中规则对应的下标+1)",
                    "风险x(x为命中规则对应的下标+1)"
                ],
                "risk": [
                    "风险x(x为命中规则对应的下标+1)"
                ]
            }
        }
    ]
    """

    indented_delay_rules = [f"           {rule}" for rule in delay_rules]
    indented_risk_rules = [f"           {rule}" for rule in risk_rules]

    get_jira_board_story = get_jira_board_story.replace("{{DELAY_RULES}}", '\n'.join(indented_delay_rules))
    get_jira_board_story = get_jira_board_story.replace("{{RISK_RULES}}", '\n'.join(indented_risk_rules))

    try:
        # 1. Mock 模式处理
        if request.mock:
            result = {
                "success": True,
                "response": "```json\n[\n    {\n        \"key\": \"ORI-135482\",\n        \"summary\": \"【调研】在BR V2 中，支持数据更新\",\n        \"status\": \"Open\",\n        \"tags\": {\n            \"delay\": [],\n            \"risk\": [\n                \"风险3\"\n            ]\n        }\n    },\n    {\n        \"key\": \"ORI-120625\",\n        \"summary\": \"调研 Python、Django 升级\",\n        \"status\": \"Open\",\n        \"tags\": {\n            \"delay\": [],\n            \"risk\": [\n                \"风险3\"\n            ]\n        }\n    },\n    {\n        \"key\": \"ORI-135977\",\n        \"summary\": \"列表页/related list的multi_lookup/multi-select_picklist字段支持filter_by_list_data（ 2.5 提测 ）\",\n        \"status\": \"Development in Progress\",\n        \"tags\": {\n            \"delay\": [\n                \"风险1\"\n            ],\n            \"risk\": [\n                \"风险3\"\n            ]\n        }\n    },\n    {\n        \"key\": \"ORI-134586\",\n        \"summary\": \"【调研】 Hardcode PageList 重写get_record_value 导致「有数据项」过滤项不准的问题\",\n        \"status\": \"Development in Progress\",\n        \"tags\": {\n            \"delay\": [],\n            \"risk\": []\n        }\n    },\n    {\n        \"key\": \"ORI-133951\",\n        \"summary\": \"【实现2】详情页中lookup字段迁移rls_config - 开启use_rls_config 开关 （1.14 提测）\",\n        \"status\": \"Development in Progress\",\n        \"tags\": {\n            \"delay\": [\n                \"风险1\"\n            ],\n            \"risk\": [\n                \"风险3\"\n            ]\n        }\n    },\n    {\n        \"key\": \"ORI-132922\",\n        \"summary\": \"【BR V2】BR v2 提示信息 on-tab（2.11）\",\n        \"status\": \"Development in Progress\",\n        \"tags\": {\n            \"delay\": [\n                \"风险1\"\n            ],\n            \"risk\": [\n                \"风险3\"\n            ]\n        }\n    },\n    {\n        \"key\": \"ORI-131672\",\n        \"summary\": \"标准列表页/related list支持为空/不为空/属于（in）/不属于（not in）的筛选（2.5 提测）\",\n        \"status\": \"Development in Progress\",\n        \"tags\": {\n            \"delay\": [\n                \"风险1\"\n            ],\n            \"risk\": [\n                \"风险3\"\n            ]\n        }\n    },\n    {\n        \"key\": \"ORI-135104\",\n        \"summary\": \"pagelayout field 中 metadata reference 字段可以设置configuration （metadata reference conditions）✅\",\n        \"status\": \"QA In Progress\",\n        \"tags\": {\n            \"delay\": [],\n            \"risk\": []\n        }\n    },\n    {\n        \"key\": \"ORI-132930\",\n        \"summary\": \"【实现】支持refer lookup字段，并且列表筛选可以按照原生lookup来筛选（1.23 提测✅）\",\n        \"status\": \"QA In Progress\",\n        \"tags\": {\n            \"delay\": [],\n            \"risk\": [\n                \"风险3\"\n            ]\n        }\n    },\n    {\n        \"key\": \"ORI-132921\",\n        \"summary\": \"【BR V2】关闭新建 V1 BR 的入口（1.19提测）✅\",\n        \"status\": \"QA In Progress\",\n        \"tags\": {\n            \"delay\": [],\n            \"risk\": [\n                \"风险3\"\n            ]\n        }\n    },\n    {\n        \"key\": \"ORI-132920\",\n        \"summary\": \"【BR V2】BR V2 兼容 Check Point（01.13 提测）✅\",\n        \"status\": \"Closed\",\n        \"tags\": {\n            \"delay\": [],\n            \"risk\": []\n        }\n    },\n    {\n        \"key\": \"ORI-118140\",\n        \"summary\": \"【调研】调用 field.configuration的地方，都可以支持由page_list_field/page_layout_field.configuration覆盖object_field.configuration\",\n        \"status\": \"Closed\",\n        \"tags\": {\n            \"delay\": [\n                \"风险2\"\n            ],\n            \"risk\": []\n        }\n    },\n    {\n        \"key\": \"ORI-114277\",\n        \"summary\": \"affect other 界面化补齐 longtext 类型字段 （1.19提测）✅\",\n        \"status\": \"Closed\",\n        \"tags\": {\n            \"delay\": [\n                \"风险2\"\n            ],\n            \"risk\": [\n                \"风险1\"\n            ]\n        }\n    }\n]\n```",
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

        response_content = result.get('response', '')
        if '```json' in response_content:
            # Extract JSON string from markdown code block
            json_str = response_content.split('```json')[1].split('```')[0].strip()
            try:
                stories = json.loads(json_str)
                expiry = 30 * 24 * 60 * 60  # 1 month in seconds
                for story in stories:
                    story_key = story.get('key')
                    story_tags = story.get('tags')
                    if story_key and story_tags is not None:
                        tags_redis_key = f"story:tags:{story_key}"
                        set_redis(tags_redis_key, story_tags, expiry_seconds=expiry)
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON from response for redis caching: {e}")
            except Exception as e:
                print(f"An error occurred while caching story tags to redis: {e}")

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


@router.post("/api/gemini/story/check", response_model=ChatResponse)
async def story_check(request: ChatRequest):
    """
    story风险分析，并记录追踪分析当前story下所有sub-task的最近两日工作进展
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
        if request.mock:
            result = {
                "success": True,
                "response": "## 🚁 Plum 25R3.2 Sprint 2 : ORI-114277 整体进展综述\n> **当前状态**: QA In Progress | **整体进度**: 4/11\n> **风险提示**: 🟠 进度滞后\n\n**📝 最新情况摘要**:\nStory 主要研发工作已完成并转入测试阶段。过去两天，开发人员 Garry Peng 集中处理了三个相关的子任务/缺陷，并记录了 3.5 小时工时，主要解决了多个富文本字段在特定场景下的显示和值清空问题。QA 负责人 Zijie Tang 已开始介入，并要求提供用于PS代码自定义逻辑的Demo数据。\n\n---\n\n## 👥 团队成员详细动态 (过去两天)\n\n### 👤 Chuan Huang\n\n#### 🔹 ORI-136135 【admin】longtext 字段在初始拖入页面时，设置关联字段的固定值输入框，没有展示富文本样式 ([🔵 task])\n* **2026-01-23**:\n    * **[Comment]** [~garry.peng@veeva.com] feature/ORI-136135/admin-affect-others-support-long-text\n上面分支加上了\n\n### 👤 Garry Peng\n\n#### 🔹 ORI-136183 【admin】 longtext 字段为文本类型时，配置字段影响关系页面，在关联字段配置固定值处输入带标签的内容，在预览页面会变成富文本的样式 ([🔵 task])\n* **2026-01-23**:\n    * **[Worklog 1h]** \n\n#### 🔹 ORI-136135 【admin】longtext 字段在初始拖入页面时，设置关联字段的固定值输入框，没有展示富文本样式 ([🔵 task])\n* **2026-01-22**:\n    * **[Worklog 30m]** \n    * **[Comment]** /admin-api/object/\\{object_id}/page-layout/\\{layout_id}/ 接口返回的 all_fields 中的字段也需要带上 text_type [~chuan.huang@veeva.com] \n\n!image-2026-01-22-17-37-48-539.png!\n* **2026-01-23**:\n    * **[Worklog 1h]** \n\n#### 🔹 ORI-136130 【online】 控制字段将longtext 字段 带入值后，再将控制字段的值清空，longtext 字段的值未清空 ([🔴 defect])\n* **2026-01-22**:\n    * **[Worklog 1h 30m]** \n\n### 👤 Zijie Tang\n\n#### 🔹 ORI-136130 【online】 控制字段将longtext 字段 带入值后，再将控制字段的值清空，longtext 字段的值未清空 ([🔴 defect])\n* **2026-01-22**:\n    * **[Comment]** wechat 端同样存在这个问题\n\n---\n*注：报表生成时间 2026-01-24*",
                "error": None,
                "logs": "YOLO mode is enabled. All tool calls will be automatically approved.\nLoaded cached credentials.\nServer 'jira' supports tool updates. Listening for changes..."
            }

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
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Unknown error occurred")
            )
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
