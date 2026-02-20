import datetime
import asyncio

from models import ChatResponse, ChatRequest
from fastapi import HTTPException, APIRouter, Body
from analyze_data_storage import async_parse_to_json, async_get_story_description
from gemini_client import gemini_client
from redis_utils import async_query_redis, async_set_redis, query_redis, set_redis
import json

router = APIRouter()

REDIS_KEY_RULES = 'scrum_master_tag_rules'


@router.get("/story/description")
async def story_description(story_id):
    """
    给浏览器油猴用的
    """
    return await async_get_story_description(story_id)


@router.post("/api/gemini/board/personal/task/processing", response_model=ChatResponse)
async def personal_task_processing(request: ChatRequest):
    get_personal_tasks_prompt = """
    请按照以下步骤执行：
    step1: 获取看板[3485]状态为 'active' 的 sprint_id。
    step2: jira_search (jira MCP Server) {"jql":"assignee = \"{{USER_EMAIL}}\" AND status = \"In Progress\" AND sprint = sprint_id"}。
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
            await asyncio.sleep(3)
            result = {
                "success": True,
                "response": "[\n    {\n        \"jira_id\": \"ORI-136369\",\n        \"sumamry\": \"【后端】online端校验结果记录 + Ontab3个查询接口\",\n        \"today_work_hours\": \"0h\",\n        \"comment\": \"\",\n        \"logged\": \"1d 2h\",\n        \"remaining\": \"1d 3h\"\n    },\n    {\n        \"jira_id\": \"ORI-136366\",\n        \"sumamry\": \"【后端】DataModel & 框架消除逻辑\",\n        \"today_work_hours\": \"0h\",\n        \"comment\": \"\",\n        \"logged\": \"7h\",\n        \"remaining\": \"5h\"\n    },\n    {\n        \"jira_id\": \"ORI-129877\",\n        \"sumamry\": \"同一个story下的所有code review\",\n        \"today_work_hours\": \"0h\",\n        \"comment\": \"\",\n        \"logged\": \"2h\",\n        \"remaining\": \"0m\"\n    }\n]",
                "error": "Attempt 1 failed with status 429. Retrying with backoff... GaxiosError: [{\n\"error\": {\n\"errors\": [\n\"@type\": \"type.googleapis.com/google.rpc.ErrorInfo\",\nAuthorization: '<<REDACTED> - See `errorRedactor` option in `gaxios` for configuration>.',\nbody: '<<REDACTED> - See `errorRedactor` option in `gaxios` for configuration>.',\nerrorRedactor: [Function: defaultErrorRedactor]\nbody: '<<REDACTED> - See `errorRedactor` option in `gaxios` for configuration>.',\nerrorRedactor: [Function: defaultErrorRedactor]\n'  \"error\": {\\n' +\n'    \"errors\": [\\n' +\n'        \"@type\": \"type.googleapis.com/google.rpc.ErrorInfo\",\\n' +\nerror: undefined,\nSymbol(gaxios-gaxios-error): '6.7.1'",
                "logs": "(node:3466) [DEP0040] DeprecationWarning: The `punycode` module is deprecated. Please use a userland alternative instead.\n(Use `node --trace-deprecation ...` to show where the warning was created)\n(node:3484) [DEP0040] DeprecationWarning: The `punycode` module is deprecated. Please use a userland alternative instead.\n(Use `node --trace-deprecation ...` to show where the warning was created)\nYOLO mode is enabled. All tool calls will be automatically approved.\nLoaded cached credentials.\nYOLO mode is enabled. All tool calls will be automatically approved.\nHook registry initialized with 0 hook entries\nServer 'jira' supports tool updates. Listening for changes...\n\"code\": 429,\n\"message\": \"No capacity available for model gemini-2.5-pro on the server\",\n{\n\"message\": \"No capacity available for model gemini-2.5-pro on the server\",\n\"domain\": \"global\",\n\"reason\": \"rateLimitExceeded\"\n}\n],\n\"status\": \"RESOURCE_EXHAUSTED\",\n\"details\": [\n{\n\"reason\": \"MODEL_CAPACITY_EXHAUSTED\",\n\"domain\": \"cloudcode-pa.googleapis.com\",\n\"metadata\": {\n\"model\": \"gemini-2.5-pro\"\n}\n}\n]\n}\n}\n]\nat Gaxios._request (/opt/homebrew/Cellar/gemini-cli/0.26.0/libexec/lib/node_modules/@google/gemini-cli/node_modules/gaxios/build/src/gaxios.js:142:23)\nat process.processTicksAndRejections (node:internal/process/task_queues:104:5)\nat async OAuth2Client.requestAsync (/opt/homebrew/Cellar/gemini-cli/0.26.0/libexec/lib/node_modules/@google/gemini-cli/node_modules/google-auth-library/build/src/auth/oauth2client.js:429:18)\nat async CodeAssistServer.requestStreamingPost (file:///opt/homebrew/Cellar/gemini-cli/0.26.0/libexec/lib/node_modules/@google/gemini-cli/node_modules/@google/gemini-cli-core/dist/src/code_assist/server.js:169:21)\nat async CodeAssistServer.generateContentStream (file:///opt/homebrew/Cellar/gemini-cli/0.26.0/libexec/lib/node_modules/@google/gemini-cli/node_modules/@google/gemini-cli-core/dist/src/code_assist/server.js:27:27)\nat async file:///opt/homebrew/Cellar/gemini-cli/0.26.0/libexec/lib/node_modules/@google/gemini-cli/node_modules/@google/gemini-cli-core/dist/src/core/loggingContentGenerator.js:132:26\nat async retryWithBackoff (file:///opt/homebrew/Cellar/gemini-cli/0.26.0/libexec/lib/node_modules/@google/gemini-cli/node_modules/@google/gemini-cli-core/dist/src/utils/retry.js:108:28)\nat async GeminiChat.makeApiCallAndProcessStream (file:///opt/homebrew/Cellar/gemini-cli/0.26.0/libexec/lib/node_modules/@google/gemini-cli/node_modules/@google/gemini-cli-core/dist/src/core/geminiChat.js:421:32)\nat async GeminiChat.streamWithRetries (file:///opt/homebrew/Cellar/gemini-cli/0.26.0/libexec/lib/node_modules/@google/gemini-cli/node_modules/@google/gemini-cli-core/dist/src/core/geminiChat.js:253:40)\nat async Turn.run (file:///opt/homebrew/Cellar/gemini-cli/0.26.0/libexec/lib/node_modules/@google/gemini-cli/node_modules/@google/gemini-cli-core/dist/src/core/turn.js:66:30) {\nconfig: {\nurl: 'https://cloudcode-pa.googleapis.com/v1internal:streamGenerateContent?alt=sse',\nmethod: 'POST',\nparams: { alt: 'sse' },\nheaders: {\n'Content-Type': 'application/json',\n'User-Agent': 'GeminiCLI/0.26.0/gemini-2.5-pro (darwin; arm64) google-api-nodejs-client/9.15.1',\n'x-goog-api-client': 'gl-node/25.5.0'\n},\nresponseType: 'stream',\nsignal: AbortSignal { aborted: false },\nparamsSerializer: [Function: paramsSerializer],\nvalidateStatus: [Function: validateStatus],\n},\nresponse: {\nconfig: {\nurl: 'https://cloudcode-pa.googleapis.com/v1internal:streamGenerateContent?alt=sse',\nmethod: 'POST',\nparams: [Object],\nheaders: [Object],\nresponseType: 'stream',\nsignal: [AbortSignal],\nparamsSerializer: [Function: paramsSerializer],\nvalidateStatus: [Function: validateStatus],\n},\ndata: '[{\\n' +\n'    \"code\": 429,\\n' +\n'    \"message\": \"No capacity available for model gemini-2.5-pro on the server\",\\n' +\n'      {\\n' +\n'        \"message\": \"No capacity available for model gemini-2.5-pro on the server\",\\n' +\n'        \"domain\": \"global\",\\n' +\n'        \"reason\": \"rateLimitExceeded\"\\n' +\n'      }\\n' +\n'    ],\\n' +\n'    \"status\": \"RESOURCE_EXHAUSTED\",\\n' +\n'    \"details\": [\\n' +\n'      {\\n' +\n'        \"reason\": \"MODEL_CAPACITY_EXHAUSTED\",\\n' +\n'        \"domain\": \"cloudcode-pa.googleapis.com\",\\n' +\n'        \"metadata\": {\\n' +\n'          \"model\": \"gemini-2.5-pro\"\\n' +\n'        }\\n' +\n'      }\\n' +\n'    ]\\n' +\n'  }\\n' +\n'}\\n' +\n']',\nheaders: {\n'alt-svc': 'h3=\":443\"; ma=2592000,h3-29=\":443\"; ma=2592000',\n'content-length': '606',\n'content-type': 'application/json; charset=UTF-8',\ndate: 'Sat, 31 Jan 2026 14:12:48 GMT',\nserver: 'ESF',\n'server-timing': 'gfet4t7; dur=1675',\nvary: 'Origin, X-Origin, Referer',\n'x-cloudaicompanion-trace-id': '3cec9091ffc7e4be',\n'x-content-type-options': 'nosniff',\n'x-frame-options': 'SAMEORIGIN',\n'x-xss-protection': '0'\n},\nstatus: 429,\nstatusText: 'Too Many Requests',\nrequest: {\nresponseURL: 'https://cloudcode-pa.googleapis.com/v1internal:streamGenerateContent?alt=sse'\n}\n},\nstatus: 429,\n}"
            }

        else:
            kwargs = {
                "approval_mode": "yolo"
            }
            result = await gemini_client.async_chat(
                prompt,
                model=request.model,
                mcp_servers=['jira'],
                **kwargs
            )
            print(f">>> personal_task_processing gemini_res, {result}")

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


@router.get("/api/rules/get")
def get_rules():
    """获取同步至 Redis 的标签规则"""
    rules = query_redis('GET', REDIS_KEY_RULES)
    return {"success": True, "rules": rules if rules is not None else []}


@router.post("/api/rules/set")
def set_rules(rules: list = Body(...)):
    """保存标签规则至 Redis"""
    set_redis(REDIS_KEY_RULES, rules)
    return {"success": True}


@router.post("/api/gemini/board/story/list", response_model=ChatResponse)
async def story_list(request: ChatRequest):
    """
    查看看板下当前sprint正在进行的story，并打上风险标记
    """
    # 规则获取
    delay_rules = []
    risk_rules = []

    tags_data = query_redis('get', REDIS_KEY_RULES)
    if isinstance(tags_data, list):
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
            await asyncio.sleep(3)
            result = {
                "success": True,
                "response": "```json\n[\n  {\n    \"key\": \"ORI-135482\",\n    \"summary\": \"【调研】在BR V2 中，支持数据更新\",\n    \"status\": \"Open\",\n    \"tags\": {\n      \"delay\": [],\n      \"risk\": []\n    }\n  },\n  {\n    \"key\": \"ORI-120625\",\n    \"summary\": \"调研 Python、Django 升级\",\n    \"status\": \"Open\",\n    \"tags\": {\n      \"delay\": [],\n      \"risk\": []\n    }\n  },\n  {\n    \"key\": \"ORI-135977\",\n    \"summary\": \"列表页/related list的multi_lookup/multi-select_picklist字段支持filter_by_list_data（ 2.5 提测 ）\",\n    \"status\": \"Development in Progress\",\n    \"tags\": {\n      \"delay\": [],\n      \"risk\": [\n        \"风险3\"\n      ]\n    }\n  },\n  {\n    \"key\": \"ORI-134586\",\n    \"summary\": \"【调研】 Hardcode PageList 重写get_record_value 导致「有数据项」过滤项不准的问题\",\n    \"status\": \"Development in Progress\",\n    \"tags\": {\n      \"delay\": [],\n      \"risk\": []\n    }\n  },\n  {\n    \"key\": \"ORI-133951\",\n    \"summary\": \"【实现2】详情页中lookup字段迁移rls_config - 开启use_rls_config 开关 （1.14 提测）\",\n    \"status\": \"Development in Progress\",\n    \"tags\": {\n      \"delay\": [\n        \"风险1\"\n      ],\n      \"risk\": [\n        \"风险3\"\n      ]\n    }\n  },\n  {\n    \"key\": \"ORI-132922\",\n    \"summary\": \"【BR V2】BR v2 提示信息 on-tab（2.11）\",\n    \"status\": \"Development in Progress\",\n    \"tags\": {\n      \"delay\": [],\n      \"risk\": [\n        \"风险3\"\n      ]\n    }\n  },\n  {\n    \"key\": \"ORI-131672\",\n    \"summary\": \"标准列表页/related list支持为空/不为空/属于（in）/不属于（not in）的筛选（2.5 提测）\",\n    \"status\": \"Development in Progress\",\n    \"tags\": {\n      \"delay\": [],\n      \"risk\": [\n        \"风险3\"\n      ]\n    }\n  },\n  {\n    \"key\": \"ORI-135104\",\n    \"summary\": \"pagelayout field 中 metadata reference 字段可以设置configuration （metadata reference conditions）✅\",\n    \"status\": \"QA In Progress\",\n    \"tags\": {\n      \"delay\": [],\n      \"risk\": [\n        \"风险3\"\n      ]\n    }\n  },\n  {\n    \"key\": \"ORI-132930\",\n    \"summary\": \"【实现】支持refer lookup字段，并且列表筛选可以按照原生lookup来筛选（1.23 提测✅）\",\n    \"status\": \"QA In Progress\",\n    \"tags\": {\n      \"delay\": [],\n      \"risk\": [\n        \"风险3\"\n      ]\n    }\n  },\n  {\n    \"key\": \"ORI-132921\",\n    \"summary\": \"【BR V2】关闭新建 V1 BR 的入口（1.19提测）✅\",\n    \"status\": \"QA In Progress\",\n    \"tags\": {\n      \"delay\": [],\n      \"risk\": [\n        \"风险3\"\n      ]\n    }\n  },\n  {\n    \"key\": \"ORI-132920\",\n    \"summary\": \"【BR V2】BR V2 兼容 Check Point（01.13 提测）✅\",\n    \"status\": \"Closed\",\n    \"tags\": {\n      \"delay\": [],\n      \"risk\": []\n    }\n  },\n  {\n    \"key\": \"ORI-118140\",\n    \"summary\": \"【调研】调用 field.configuration的地方，都可以支持由page_list_field/page_layout_field.configuration覆盖object_field.configuration\",\n    \"status\": \"Closed\",\n    \"tags\": {\n      \"delay\": [\n        \"风险2\"\n      ],\n      \"risk\": []\n    }\n  },\n  {\n    \"key\": \"ORI-114277\",\n    \"summary\": \"affect other 界面化补齐 longtext 类型字段 （1.19提测）✅\",\n    \"status\": \"Closed\",\n    \"tags\": {\n      \"delay\": [\n        \"风险3\"\n      ],\n      \"risk\": [\n        \"风险4\"\n      ]\n    }\n  }\n]\n```",
                "error": None,
                "logs": "(node:3925) [DEP0040] DeprecationWarning: The `punycode` module is deprecated. Please use a userland alternative instead.\n(Use `node --trace-deprecation ...` to show where the warning was created)\n(node:3941) [DEP0040] DeprecationWarning: The `punycode` module is deprecated. Please use a userland alternative instead.\n(Use `node --trace-deprecation ...` to show where the warning was created)\nYOLO mode is enabled. All tool calls will be automatically approved.\nLoaded cached credentials.\nYOLO mode is enabled. All tool calls will be automatically approved.\nHook registry initialized with 0 hook entries\nServer 'jira' supports tool updates. Listening for changes..."
            }

        # 2. 真实调用逻辑
        else:
            # 强制指定参数：使用 jira server，开启 yolo 模式
            kwargs = {
                "approval_mode": "yolo"
            }

            result = await gemini_client.async_chat(
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
                        await async_set_redis(tags_redis_key, story_tags, expiry_seconds=expiry)
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
    
    # Language：中文
    
    # ⛔ CRITICAL SAFETY PROTOCOL (严禁死循环与幻觉)
    **必须严格遵守以下规则，以防止工具调用死循环及数据幻觉：**
    1. **单次调用原则**：你被严格限制为**只能执行 1 次** `jira_search` 工具调用。
    2. **禁止遍历详情**：严禁对搜索结果列表进行遍历，严禁对子任务单独调用 `jira_get_issue`、`jira_get_worklog` 或 `jira_get_comment`。
    3. **接受数据截断**：如果 `jira_search` 返回的 comment 或 worklog 列表显示不全，直接忽略未获取的部分，仅基于当前响应中已有的数据进行分析。
    4. **杜绝脑补与幻觉**：如果计算出的时间窗口内没有数据，必须如实反馈无数据，**绝不允许**为了填充报告而将历史数据伪造成今日动态；**绝不允许**将 P3 级别或 Sub-task 类型的任务捏造为“高优风险”或“缺陷”。
    
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
    
    ## 第三步：时间窗口锁定与范围界定
    首先定义参数 get_all_work_logs 的值为 `{{get_all_work_logs}}`，并根据以下分支执行：
    
    ### 分支 A：全量提取模式
    * **触发条件**：get_all_work_logs 为 `True`。
    * **执行动作**：**跳过**日期计算与时间筛选，提取所有可用的历史数据。
    
    ### 分支 B：窗口提取模式
    * **触发条件**： get_all_work_logs 为 `False` 或空。
    * **执行动作**：
        1. 获取当前日期及星期，识别出今天以及最近的两个有效工作日（往前推算时跳过周六、周日），计算出以下三个绝对日期：
            * **Target_Date_0 (今天)**：当前日期。
            * **Target_Date_1 (最近工作日)**：若当前是周一或周末，取上周五；若当前是周二，取昨天（周一）；其余情况取昨天。
            * **Target_Date_2 (前一工作日)**：若当前是周一或周末，取上周四；若当前是周二，取上周五；其余情况取前天。
        2. **筛选标准**：后续仅提取 `created` (评论) 或 `started` (工时) 落在 **[Target_Date_2 00:00:00] 至 [Target_Date_0 23:59:59]** 之间的数据。
    
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
            3. 对同一 Issue 下的记录，按 **[日期]** 升序排列（从前天到今天）。
    
    # Output Format (Markdown)

    请严格按照以下格式输出：

    ## 🚁 {{SPRINT_ID}} : {{STORY_KEY}} 整体进展综述
    > **当前状态**: [Story Status] | **整体进度**: [已完成子任务数]/[总子任务数]
    > **风险提示**: [无风险 / 🔴 有 N 个严重缺陷未修复 / 🟠 进度滞后]

    **📝 最新情况摘要**:
    (基于现有数据，用 2-3 句话总结 Story 状态。若当前窗口期无任何动态，必须在此处明确说明并指出实际的最后活跃日期。)
    
    ---

    ## 👥 团队成员详细动态 (过去三天)

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
    jira_story_check = jira_story_check.replace("{{get_all_work_logs}}", str(request.get_all_work_logs))

    try:
        if request.mock:
            await asyncio.sleep(3)
            result = {'error': None,
                      'logs': "YOLO mode is enabled. All tool calls will be automatically approved.\nLoaded cached credentials.\nYOLO mode is enabled. All tool calls will be automatically approved.\nServer 'jira' supports tool updates. Listening for changes...",
                      'response': '## 🚁 Plum 25R3.3 Sprint 2 : ORI-132922 整体进展综述\n> **当前状态**: Development in Progress | **整体进度**: 5/12\n> **风险提示**: 无风险\n\n**📝 最新情况摘要**:\n根据现有数据，Story 整体处于开发中状态，无高优风险。最近的动态是 2026-02-14 相关人员就 snapshot 数据的更新与消除逻辑进行了讨论和确认，表明团队正在积极解决业务流程中的技术细节。前端与后端开发任务均有持续进展。\n\n---\n\n## 👥 团队成员详细动态 (全量历史)\n\n*(仅展示有数据的成员)*\n\n### 👤 Chuan Huang\n\n#### 🔹 ORI-136371 【后端】联调 (🔵 task)\n* **[2026-02-10]**:\n    * **[Worklog 2h]** \n    * **[Worklog 3h]** \n\n#### 🔹 ORI-136369 【后端】online端校验结果记录 + Ontab3个查询接口 (🔵 task)\n* **[2026-01-29]**:\n    * **[Worklog 5h]** 校验记录快照存储\n* **[2026-01-30]**:\n    * **[Worklog 5h]** 业务 前后端一起核对 adv-tab交互流程 和Garry确定on-tab查询接口出入参\n* **[2026-02-02]**:\n    * **[Worklog 3h]** \n* **[2026-02-05]**:\n    * **[Worklog 1h]** 投入较少 和 业务对了一下持久化数据格式 针对多summary的场景再微调一下\n    * **[Worklog 4h]** 分拣存储 & 分tab查询接口开发完成 还剩risk区分接口\n* **[2026-02-10]**:\n    * **[Worklog 3h]** 遗留代码处理\n\n#### 🔹 ORI-136366 【后端】DataModel & 框架消除逻辑 (🔵 task)\n* **[2026-01-26]**:\n    * **[Worklog 5h]** \n* **[2026-01-27]**:\n    * **[Worklog 2h]** \n* **[2026-02-05]**:\n    * **[Worklog 3h]** datamodel调整 & 失效逻辑提交\n* **[2026-02-09]**:\n    * **[Worklog 2h]** 软提示记录改造到后端\n\n#### 🔹 ORI-136186 【后端】on-tab开发 (🔵 task)\n* **[2026-01-26]**:\n    * **[Worklog 3h]** model处理\n    * **[Comment]** 单独拆分子任务\n\n#### 🔹 ORI-135338 【后端】实现前置调研 (🔵 task)\n* **[2026-01-13]**:\n    * **[Worklog 3m]** \n    * **[Worklog 3h]** \n* **[2026-01-14]**:\n    * **[Worklog 2h]** \n* **[2026-01-15]**:\n    * **[Worklog 3h]** \n* **[2026-01-16]**:\n    * **[Worklog 5h]** \n* **[2026-01-19]**:\n    * **[Worklog 5h]** \n\n#### 🔹 ORI-132922 【BR V2】BR v2 提示信息 on-tab（2.24） (🔵 task)\n* **[2026-01-20]**:\n    * **[Comment]** 01.20 on-tab和业务后端的交互沟通了，平台后端预计5point 当前现状下多对象触发 提示信息不准的问题还没有明确解决方案，我今天会约架构师一起讨论明确一下方案，这个问题修复预计会增加2point开发工作量 01.19 昨天和业务产品技术一起确定了 产品demo的一些业务细节，01.20会拉技术一起确定两边技术交互的细节，然后可以定排期开发\n* **[2026-01-21]**:\n    * **[Comment]** * 后端BR-OnTab场景  ** BR框架支持 本次ontab数据 消除&存储&业务后端交互 【2】  ** on-Tab的前端校验写入接口 【1】  ** Tab信息聚合查询接口【1】  ** 智能建议依赖数据查询【1】  ** 原disregards接口改造【0.5】 * 联调：2 * V2 多对象场景，跨对象提示信息消除不准问题解决【2】这个感觉可以单独story\n* **[2026-02-02]**:\n    * **[Comment]** 上周五 event侧 同步policy-helper需求有变动，产品最新设计与br-onTab的交互有冲突，目前和产品以及manager沟通暂时先hold住 cc [~garry.peng@veeva.com] [~yi.yang@veeva.com] [~howie.peng@veeva.com] [~rui.zeng@veeva.com] [~jie.zhou@veeva.com]\xa0\n    * **[Comment]** 目前周一上午和杨易最新沟通，后端先正常开发，后端和[~garry.peng@veeva.com] 会先开发 提示信息记录 + 分tab查询部分功能，risk区域平台UI（不含智能建议 + 非BR risk提示混合展示）等[~yi.yang@veeva.com]提供 前端智能建议整体样式部分等[~yi.yang@veeva.com] 周二和客户沟通后有最新结论后同步我们\n    * **[Comment]** [~garry.peng@veeva.com] \xa0 【快照记录入参】 {code:java} 取v2的数据结构转json即可  {"event": {"390": {"66": {"trigger_ins": {"object_name": "event", "record_id": 390}, "rule_id": 66, "latest_comment": "\\u8df3\\u8fc7", "is_hard_stop": false, "comment_required_on_bypass": true, "check_point_name": null, "summary": [{"message": "<p>\\u5b58\\u5728<veev-exp>2</veev-exp>&#8203;\\u4f4d\\u4e0d\\u5141\\u8bb8\\u53c2\\u52a0\\u7684\\u53c2\\u4f1a\\u4eba</p>", "trigger_ins": {"object_name": "event", "record_id": 390}, "is_hard_stop": false, "comment_required_on_bypass": true, "extra_info": {}, "details": [{"message": "<p>\\u53c2\\u4f1a\\u4eba<veev-exp>\\u9ec4\\u5b87\\u5149</veev-exp>&#8203;\\u4e0d\\u5141\\u8bb8\\u53c2\\u52a0</p>", "trigger_ins": {"object_name": "event", "record_id": 390}, "extra_info": {}, "msg_info": {"custombr_86ro8R0VC": {"e1": "\\u9ec4\\u5b87\\u5149"}}, "message_key": "cs_summary_key_detail", "persistence_config": {"search_object_name": "event", "search_object_record_id": 390, "related_objects": {"event_account": [313]}}}, {"message": "<p>\\u53c2\\u4f1a\\u4eba<veev-exp>Allen.Luo</veev-exp>&#8203;\\u4e0d\\u5141\\u8bb8\\u53c2\\u52a0</p>", "trigger_ins": {"object_name": "event", "record_id": 390}, "extra_info": {}, "msg_info": {"custombr_86ro8R0VC": {"e1": "Allen.Luo"}}, "message_key": "cs_summary_key_detail", "persistence_config": {"search_object_name": "event", "search_object_record_id": 390, "related_objects": {"event_account": [315]}}}], "msg_info": {"custombr_86ro8QU2A": {"e1": "2"}}, "message_key": "cs_summary_key", "persistence_config": {"search_object_name": "event", "search_object_record_id": 390, "related_objects": {}}}]}}}}{code} 【on-tab接口】 {code:java} 入参 {"search_object_name":"event","search_object_record_id":389,"page_layout_id":"d47fd211-45ae-464d-af76-1ed792057bee","front_advanced_layout_tab_mapping":{"event_attendee":["event_account","event_professional","contact","event_speaker"],"tab_name2":["realted_name_3"]}} 返回 \xa0{"event_attendee":[[{"message":"&lt;p&gt;存在&lt;veev-exp&gt;2&lt;/veev-exp&gt;&amp;#8203;位不允许参加的参会人&lt;/p&gt;","message_key":"cs_summary_key","persistence_config":{"search_object_name":"event","search_object_record_id":389,"related_objects":{}},"details":[{"message":"&lt;p&gt;参会人&lt;veev-exp&gt;李大魁&lt;/veev-exp&gt;&amp;#8203;不允许参加&lt;/p&gt;","message_key":"cs_summary_key_detail","persistence_config":{"search_object_name":"event","search_object_record_id":389,"related_objects":{"event_account":[305]}}},{\\"message":"&lt;p&gt;参会人&lt;veev-exp&gt;李强&lt;/veev-exp&gt;&amp;#8203;不允许参加&lt;/p&gt;","message_key":"cs_summary_key_detail","persistence_config":{"search_object_name":"event","search_object_record_id":389,"related_objects":{"event_account":[306]}}}],"ai_suggestion":{"content":"将xxx医生替换为符合科室规范的参会医生","type":"text"}}],[{"message":"&lt;p&gt;存在&lt;veev-exp&gt;2&lt;/veev-exp&gt;&amp;#8203;位不允许参加的参会人&lt;/p&gt;","message_key":"cs_summary_key","persistence_config":{"search_object_name":"event","search_object_record_id":390,"related_objects":{}},"details":[{"message":"&lt;p&gt;参会人&lt;veev-exp&gt;黄宇光&lt;/veev-exp&gt;&amp;#8203;不允许参加&lt;/p&gt;","message_key":"cs_summary_key_detail","persistence_config":{"search_object_name":"event","search_object_record_id":390,"related_objects":{"event_account":[313]}}},{\\"message":"&lt;p&gt;参会人&lt;veev-exp&gt;Allen.Luo&lt;/veev-exp&gt;&amp;#8203;不允许参加&lt;/p&gt;","message_key":"cs_summary_key_detail","persistence_config":{"search_object_name":"event","search_object_record_id":390,"related_objects":{"event_account":[315]}}}],"ai_suggestion":null}]]}{code}\n* **[2026-02-05]**:\n    * **[Comment]** [~pisheng.zhong@veeva.com] [~haohao.ji@veeva.com] [~yidi.yang@veeva.com]\xa0 {code:java} br_check_snapshot.msg 分拣后的校验结果 uniq_key = rule_id + trigger_object_id + trigger_object_name [{"message": "<p> \xa0\\u5b58\\u5728<veev-exp>2</veev-exp>&#8203;\\u4f4d\\u4e0d\\u5141\\u8bb8\\u53c2\\u52a0\\u7684\\u53c2\\u4f1a\\u4eba</p>", "message_key": "cs_summary_key", "persistence_config": {"search_object_name": "event", "search_object_record_id": 390, "related_objects": {}}, "details": [{"message": "<p>\\u53c2\\u4f1a\\u4eba<veev-exp>\\u9ec4\\u5b87\\u5149</veev-exp>&#8203;\\u4e0d\\u5141\\u8bb8\\u53c2\\u52a0</p>", "message_key": "cs_summary_key_detail", "persistence_config": {"search_object_name": "event", "search_object_record_id": 390, "related_objects": {"event_account": [313]}}}, {"message": "<p>\\u53c2\\u4f1a\\u4eba<veev-exp>Allen.Luo</veev-exp>&#8203;\\u4e0d\\u5141\\u8bb8\\u53c2\\u52a0</p>", "message_key": "cs_summary_key_detail", "persistence_config": {"search_object_name": "event", "search_object_record_id": 390, "related_objects": {"event_account": [315]}}}]}]  智能建议 数据结构 { \xa0 \xa0 "ai_suggestion": { \xa0 \xa0 \xa0 \xa0 "cs_summary_key": { \xa0 \xa0 \xa0 \xa0 \xa0 \xa0 "content": "将xxx医生替换为符合科室规范的参会医生", \xa0 \xa0 \xa0 \xa0 \xa0 \xa0 "type": "text" \xa0 \xa0 \xa0 \xa0 }, \xa0 \xa0 \xa0 \xa0 "cs_summary_key_2": { \xa0 \xa0 \xa0 \xa0 \xa0 \xa0 "content": "", \xa0 \xa0 \xa0 \xa0 \xa0 \xa0 "type": "markdown" \xa0 \xa0 \xa0 \xa0 } \xa0 \xa0 } }{code} \xa0  \xa0\n* **[2026-02-13]**:\n    * **[Comment]** 硬提示的校验 如果要记录，记录的结果 必须 要和当前的数据状态保持一致，只举一个 数据校验后触发硬提示场景（可能实际业务上没有） 1. 比如 开始开会 按钮，用户将会议状态从草稿 改为 进行中，({color:#de350b}举例可能不太合适，我们只是在一次button行为中找一个数据变更触发的硬提示文案和当前数据状态不一致的场景{color})，在post_save中触发了硬提示，提示 进行中的会议，费用不能超过2000，点击去修改后会把提示记录下来 但是当前会议的状态还是草稿中，我们记录的硬提示 是在 描述 数据变更后的提示，会有和当前数据状态不一致的风险 [~yi.yang@veeva.com]\xa0 我这边暂时找不到真实的业务场景，按照刚刚的沟通，我们也可以假设不会存在这种场景（一个button在点击后修改了数据 并 触发了BR硬提示描述说明了变更后的内容，我们做了记录 但是数据还是变更前的），不对此场景做处理 或者后续发现了这种场景，我们推动客户去修改文案，让文案不和修改的数据内容有关联尽量避免歧义\n\n### 👤 Garry Peng\n\n#### 🔹 ORI-136367 【前端】功能实现 (🔵 task)\n* **[2026-01-29]**:\n    * **[Worklog 2h]** \n    * **[Worklog 1h]** 接口方案对齐\n    * **[Worklog 2h]** \n* **[2026-02-06]**:\n    * **[Worklog 1h 30m]** \n* **[2026-02-09]**:\n    * **[Worklog 2d 1h]** \n    * **[Worklog 30m]** \n* **[2026-02-10]**:\n    * **[Worklog 2h 30m]** \n    * **[Worklog 4h]** \n* **[2026-02-12]**:\n    * **[Worklog 3h 30m]** \n* **[2026-02-13]**:\n    * **[Worklog 3h]** \n\n#### 🔹 ORI-135337 【前端】调研 (🔵 task)\n* **[2026-01-13]**:\n    * **[Worklog 5h 30m]** \n    * **[Comment]** h1. 数据记录 *记录时机* 软提示br弹窗点击继续按钮时 *方案* 服务端增加一个数据记录接口 在br弹窗 trigger-dialog 的 handleContinue 函数中调用接口 \xa0 修改范围：wechat，web2 \xa0\n    * **[Comment]** h1. Tab 提示 !image-2026-01-13-14-50-14-119.png! \xa0 在页面加载阶段获取数据（调用接口） h2. Online 端 *web2*\xa0 page-layout-facade.vue h2. Wechat 端 *wechat* pl-view.html \xa0\n    * **[Comment]** h1. 消息提示区域 *需求* * 增加开关字段，用于控制是否展示新版ui * 新版 ui：智能合规提示，提示信息包含新版合规提示信息和 disregard 数据；用户自定义的提示信息展示在 risk info 区域 * 旧版 ui：disregard 数据和客户自定义提示数据一起展示在 risk info 区域 *方案* * /api/business-rule-disregards/\xa0 接口改造： ** 新增一个参数（参数名待定），bool 类型 ** true：返回 disregard 数据 + 用户自定义数据；false：只返回用户自定义数据 * 前端增加智能合规提示组件 \xa0 *web2:* page-layout-facade.vue {code:java} <router-view v-slot="{ Component }"> ... \xa0 \xa0<div class="tab-collapse-content"> <智能合规提示 /> \xa0 \xa0 \xa0 \xa0<component :is="Component" ... /> </div> ... </router-view>{code} tab-wrapper.vue {code:java} <template> <div> <智能合规提示 /> <component :is="resolvedTemplate" :meta="meta" :data="data" :parent-ctrl="pageCtrl"> </component> </div> </template> {code} *wechat* pl-view.html {code:java} <div class="page-body"> \xa0 \xa0<智能合规提示 /> </div> {code} {code:java} <uib-tab ng-repeat="tabItem in pageCtrl.tabs" ...> <智能合规提示 /> </uib-tab>{code} 智能合规提示组件 !image-2026-01-13-18-22-25-769.png! approval-warning 组件改造 h2. !image-2026-01-13-18-24-49-723.png! \xa0 \xa0 \xa0\n* **[2026-01-14]**:\n    * **[Worklog 1h]** \n\n#### 🔹 ORI-132922 【BR V2】BR v2 提示信息 on-tab（2.24） (🔵 task)\n* **[2026-01-21]**:\n    * **[Comment]** 前端点数拆分： * br 弹窗调整【1】 ** 写数据 ** 根据br类型区分行为（checkpoint类型和 button 类型表现不同） * tab 展示提示 icon （wechat 和 online 双端，2个技术栈）【2】 * 智能提示组件\xa0 ** 公共组件（wechat 和 online 双端）【2】 ** 数据更新流程调研+实现【1】 * risk 区域组件调整 【1】 ** 根据 custom setting 开关切换数据源 * 联调 + 自测【2】\n* **[2026-01-29]**:\n    * **[Comment]** h2. 交互流程图 [https://gvpp34oja7w.feishu.cn/docx/RH5fd4DrsoCgTxxHMMxchWnfnbh?blockId=TuHTdoHUfoHCw6xg0EycnUEDn9f&blockToken=ARfMwQ09mhriLZblsFxcpRpynCb&blockType=whiteboard&doc_app_id=501]\n* **[2026-02-03]**:\n    * **[Comment]** 接口地址\xa0 [http://\\{{host}}/api/business-rule-v2/record-br-check-snapshot] [http://\\{{host}}/api/business-rule-v2/validation-results] \xa0 \xa0 \xa0\n* **[2026-02-11]**:\n    * **[Comment]** 点击【去修改】按钮记录 snapshot： 在 view 页面记录，在 layout 页面不记录 只判断是否是 view 页面，不区分按钮。 即：无论哪个按钮，只要是在 view 页面触发了br弹窗，点击去修改，都会调用记录 snapshot 的接口 cc [~jie.zhou@veeva.com] [~yi.yang@veeva.com] \xa0[~chuan.huang@veeva.com]\xa0\n\n### 👤 Jie Zhou\n\n#### 🔹 ORI-135329 测试用例 (🔵 task)\n* **[2026-01-29]**:\n    * **[Worklog 1d 1h]** \n\n#### 🔹 ORI-132922 【BR V2】BR v2 提示信息 on-tab（2.24） (🔵 task)\n* **[2026-01-07]**:\n    * **[Comment]** 豁免 bug 改了以后： 点继续-回到 view 页面，只有 v2 的情况下，也会弹多次软提示框 check_business_rale_result： * identify 和 process !image-2026-01-07-16-58-58-491.png|width=592,height=144! 要看下这个场景\n    * **[Comment]** 1、期望的是 哪个对象 br 报错，点继续，就跳转到哪个 tab。如果不能实现，就跳转到基本信息页 2、需要考虑只有详情页，触发 br 的情况，没有「基本信息」title，也不会有小红点，只会有 risk info 3、 会议取消： \xa0pagelayout view 页面-点会议取消-硬提示 - 去修改 - 第一个报错的 tab \xa0pagelayout view 页面-点会议取消-软提示 - 继续 -\xa0 取消成功 -跳到 view 页面 \xa0 保存场景： 保存-硬提示 - 去修改 - 跳到edit 页面 保存-软提示 - 继续 - 保存成功 -跳到 view 页面 !image-2026-01-07-17-24-36-920.png|width=573,height=321! 不同接口 点继续-identify接口-记录了 brd 和小红点，点取消，回来显示 brd 和小红点 点确定-process接口-又调了一次 br，会显示临时增加的 rule（点继续之后增加的） \xa0 历史数据能不能支持有小红点？ \xa0 去修改 \xa0-- \xa0修改前的一个建议 \xa0不是 brd \xa0 \xa0 新表 \xa0 \xa0父集\xa0\xa0 继续 \xa0--- \xa0数据保存了，记录的 brd \xa0 子集 \xa0客户拿去做审计 \xa0\n    * **[Comment]** 调研： 前端：2\xa0 tab 组件、AI 提示 UI 后端：2 QA：7\n* **[2026-01-16]**:\n    * **[Comment]** 0116 早会： 调研需要去了解业务的东西 * 细节处理和 trigger 实现强相关 * 一些交互在 refine 上没有聊到\n\n### 👤 Rui Zeng\n\n#### 🔹 ORI-135337 【前端】调研 (🔵 task)\n* **[2026-01-26]**:\n    * **[Worklog 5h 30m]** \n\n#### 🔹 ORI-132922 【BR V2】BR v2 提示信息 on-tab（2.24） (🔵 task)\n* **[2026-01-21]**:\n    * **[Comment]** 0121 早会 预估点数： B : 7.5 F: 9 \xa0\n\n### 👤 Yi Yang\n\n#### 🔹 ORI-132922 【BR V2】BR v2 提示信息 on-tab（2.24） (🔵 task)\n* **[2026-02-14]**:\n    * **[Comment]** \xa0业务流程上，对应“ 一旦snapshot 数据更新（view 页面的去修改+继续按钮，edit 页面的 继续按钮），则需要执行消除操作 ” ---- 补充： 平台提供的功能是：一旦snapshot 数据更新，则去执行消除操作 若业务层、或者ps的特殊业务逻辑（主要是更新数据），或者 br msg 的描述问题（记录 + 消除），引发了用户的confuse，那么需要更改 br 文案，或者调整 业务层、或者ps的数据更新逻辑\n\n---\n*注：报表生成时间 2026-02-20*',
                      'return_code': 0, 'success': True}

        else:
            # 强制指定参数：使用 jira server，开启 yolo 模式
            kwargs = {
                "approval_mode": "yolo"
            }

            result = await gemini_client.async_chat(
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
        print(f">>> story_check, {request.jira_id}, {repr(result['response'])}")

        await async_parse_to_json(result['response'], request.jira_id)
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
