import re
import json
from redis_utils import query_redis, set_redis, async_query_redis, async_set_redis

# 原始 Markdown 数据
markdown_data = "## 🚁 Plum 25R3.2 Sprint 2 : ORI-114277 整体进展综述\n> **当前状态**: QA In Progress | **整体进度**: 4/11\n> **风险提示**: 🟠 进度滞后\n\n**📝 最新情况摘要**:\nStory 主要研发工作已完成并转入测试阶段。过去两天，开发人员 Garry Peng 集中处理了三个相关的子任务/缺陷，并记录了 3.5 小时工时，主要解决了多个富文本字段在特定场景下的显示和值清空问题。QA 负责人 Zijie Tang 已开始介入，并要求提供用于PS代码自定义逻辑的Demo数据。\n\n---\n\n## 👥 团队成员详细动态 (过去两天)\n\n### 👤 Chuan Huang\n\n#### 🔹 ORI-136135 【admin】longtext 字段在初始拖入页面时，设置关联字段的固定值输入框，没有展示富文本样式 ([🔵 task])\n* **2026-01-23**:\n    * **[Comment]** [~garry.peng@veeva.com] feature/ORI-136135/admin-affect-others-support-long-text\n上面分支加上了\n\n### 👤 Garry Peng\n\n#### 🔹 ORI-136183 【admin】 longtext 字段为文本类型时，配置字段影响关系页面，在关联字段配置固定值处输入带标签的内容，在预览页面会变成富文本的样式 ([🔵 task])\n* **2026-01-23**:\n    * **[Worklog 1h]** \n\n#### 🔹 ORI-136135 【admin】longtext 字段在初始拖入页面时，设置关联字段的固定值输入框，没有展示富文本样式 ([🔵 task])\n* **2026-01-22**:\n    * **[Worklog 30m]** \n    * **[Comment]** /admin-api/object/\\{object_id}/page-layout/\\{layout_id}/ 接口返回的 all_fields 中的字段也需要带上 text_type [~chuan.huang@veeva.com] \n\n!image-2026-01-22-17-37-48-539.png!\n* **2026-01-23**:\n    * **[Worklog 1h]** \n\n#### 🔹 ORI-136130 【online】 控制字段将longtext 字段 带入值后，再将控制字段的值清空，longtext 字段的值未清空 ([🔴 defect])\n* **2026-01-22**:\n    * **[Worklog 1h 30m]** \n\n### 👤 Zijie Tang\n\n#### 🔹 ORI-136130 【online】 控制字段将longtext 字段 带入值后，再将控制字段的值清空，longtext 字段的值未清空 ([🔴 defect])\n* **2026-01-22**:\n    * **[Comment]** wechat 端同样存在这个问题\n\n---\n*注：报表生成时间 2026-01-24*"


def parse_to_json(text, story_id):
    """
    解析Markdown并将结果保存/合并到指定Sprint和Story的文件中。
    Sprint ID 会从 text 的第一行标题中自动提取。
    """

    # ---------------------------------------------------------
    # 0. 提取 Sprint ID
    # ---------------------------------------------------------
    sprint_match = re.search(r'^##\s+\S+\s+(.*?)\s*:', text, re.MULTILINE)

    if sprint_match:
        sprint_id = sprint_match.group(1).strip()
        print(f"检测到 Sprint ID: {sprint_id}")
    else:
        sprint_id = "Unknown_Sprint"
        print("Warning: 未能从文本中提取 Sprint ID，使用默认值。")

    # ---------------------------------------------------------
    # 1. 提取并存储“最新情况摘要”
    # ---------------------------------------------------------
    summary_match = re.search(r'(\*\*📝 最新情况摘要\*\*:\n.*?)---', text, re.DOTALL)
    if summary_match:
        summary_content = summary_match.group(1).strip()
        summary_redis_key = f"story:summary:{story_id}"
        set_redis(summary_redis_key, summary_content)
        print(f"成功提取“最新情况摘要”并存入 Redis (Key: {summary_redis_key})。")
    else:
        print("Warning: 未能在文本中找到“最新情况摘要”部分。")

    # ---------------------------------------------------------
    # 2. 核心解析逻辑
    # ---------------------------------------------------------
    lines = text.split('\n')
    new_parsed_data = []

    current_user = None
    current_jira_id = None
    current_jira_title = None
    current_date = None

    re_user = re.compile(r'^###\s+👤\s+(.+)')
    re_jira = re.compile(r'^####\s+🔹\s+(ORI-\d+)\s+(.+)')

    # --- 修改点在这里：去掉了 regex 中的 \[ 和 \] ---
    # 原始: r'^\*\s+\*\*\[(\d{4}-\d{2}-\d{2})\]\*\*: '
    # 修改后: r'^\*\s+\*\*(\d{4}-\d{2}-\d{2})\*\*: '
    re_date = re.compile(r'^\*\s+\*\*(\d{4}-\d{2}-\d{2})\*\*:')

    re_item = re.compile(r'^\s+\*\s+(\*\*\[.*?\]\*\*)\s*(.*)')

    for line in lines:
        line = line.rstrip()
        user_match = re_user.match(line)
        if user_match:
            current_user = user_match.group(1).strip()
            continue

        jira_match = re_jira.match(line)
        if jira_match:
            current_jira_id = jira_match.group(1).strip()
            current_jira_title = jira_match.group(2).strip()
            continue

        date_match = re_date.match(line.strip())
        if date_match:
            current_date = date_match.group(1).strip()
            continue

        item_match = re_item.match(line)
        if item_match:
            tag_part = item_match.group(1)
            text_part = item_match.group(2)

            if current_user and current_jira_id and current_date:
                new_parsed_data.append({
                    "User": current_user,
                    "Jira_ID": current_jira_id,
                    "Jira_Title": current_jira_title,
                    "Date": current_date,
                    "Content": tag_part,
                    "Comment": text_part.strip()
                })

    # ---------------------------------------------------------
    # 3. Redis 操作逻辑
    # ---------------------------------------------------------

    # 构造 Redis Key, 格式: story:personal_progress:{story_id}
    redis_key = f"story:personal_progress:{story_id}"

    # 从 Redis 读取现有数据
    existing_data = query_redis('GET', redis_key)
    if not isinstance(existing_data, list):
        final_data = []
    else:
        final_data = existing_data
    
    print(f"从 Redis (Key: {redis_key}) 读取了 {len(final_data)} 条已有数据。")

    # 数据清理与合并逻辑
    
    # 1. 清理 Redis 中的现有脏数据（去重）
    initial_count = len(final_data)
    
    # 使用字典去重，保留每个复合键最后出现的元素。
    # 这一步同时也为后续合并 new_parsed_data 准备了 existing_map。
    existing_map = {
        (item.get('User'), item.get('Jira_ID'), item.get('Date')): item
        for item in final_data if isinstance(item, dict) and all(item.get(k) for k in ['User', 'Jira_ID', 'Date'])
    }
    final_data = list(existing_map.values())
    
    cleaned_count = len(final_data)
    if initial_count > cleaned_count:
        print(f"数据清理：检测到并移除了 {initial_count - cleaned_count} 条重复的现有记录。")

    # 2. 将新解析的数据合并到已清理的数据中
    update_count = 0
    append_count = 0

    for new_item in new_parsed_data:
        # 确保 new_item 格式正确
        if not (isinstance(new_item, dict) and all(new_item.get(k) for k in ['User', 'Jira_ID', 'Date'])):
            continue
            
        key = (new_item['User'], new_item['Jira_ID'], new_item['Date'])
        existing_item = existing_map.get(key)

        if existing_item:
            # 键存在，更新
            if existing_item.get('Content') != new_item.get('Content') or existing_item.get('Comment') != new_item.get('Comment'):
                existing_item.update(new_item)
                update_count += 1
        else:
            # 键不存在，新增
            final_data.append(new_item)
            existing_map[key] = new_item
            append_count += 1

    # 3. 结果写回
    # 只要有任何变动（清理、新增、更新），就执行写回操作
    if initial_count != cleaned_count or append_count > 0 or update_count > 0:
        if append_count > 0:
            print(f"成功追加 {append_count} 条新记录。")
        if update_count > 0:
            print(f"成功更新 {update_count} 条现有记录。")
        
        set_redis(redis_key, final_data)
        print(f"数据已写回 Redis (Key: {redis_key})。")
    else:
        print("无需改动：数据已是最新且无重复。")

    return final_data


async def async_parse_to_json(text, story_id):
    """
    异步解析Markdown并将结果保存/合并到指定Sprint和Story的文件中。
    """
    sprint_match = re.search(r'^##\s+\S+\s+(.*?)\s*:', text, re.MULTILINE)

    if sprint_match:
        sprint_id = sprint_match.group(1).strip()
    else:
        sprint_id = "Unknown_Sprint"

    summary_match = re.search(r'(\*\*📝 最新情况摘要\*\*:\n.*?)---', text, re.DOTALL)
    if summary_match:
        summary_content = summary_match.group(1).strip()
        summary_redis_key = f"story:summary:{story_id}"
        await async_set_redis(summary_redis_key, summary_content)

    lines = text.split('\n')
    new_parsed_data = []
    current_user = None
    current_jira_id = None
    current_jira_title = None
    current_date = None

    re_user = re.compile(r'^###\s+👤\s+(.+)')
    re_jira = re.compile(r'^####\s+🔹\s+(ORI-\d+)\s+(.+)')
    re_date = re.compile(r'^\*\s+\*\*(\d{4}-\d{2}-\d{2})\*\*:')
    re_item = re.compile(r'^\s+\*\s+(\*\*\[.*?\]\*\*)\s*(.*)')

    for line in lines:
        line = line.rstrip()
        user_match = re_user.match(line)
        if user_match:
            current_user = user_match.group(1).strip()
            continue
        jira_match = re_jira.match(line)
        if jira_match:
            current_jira_id = jira_match.group(1).strip()
            current_jira_title = jira_match.group(2).strip()
            continue
        date_match = re_date.match(line.strip())
        if date_match:
            current_date = date_match.group(1).strip()
            continue
        item_match = re_item.match(line)
        if item_match:
            tag_part = item_match.group(1)
            text_part = item_match.group(2)
            if current_user and current_jira_id and current_date:
                new_parsed_data.append({
                    "User": current_user,
                    "Jira_ID": current_jira_id,
                    "Jira_Title": current_jira_title,
                    "Date": current_date,
                    "Content": tag_part,
                    "Comment": text_part.strip()
                })

    redis_key = f"story:personal_progress:{story_id}"
    existing_data = await async_query_redis('GET', redis_key)
    
    if not isinstance(existing_data, list):
        final_data = []
    else:
        final_data = existing_data

    existing_map = {
        (item.get('User'), item.get('Jira_ID'), item.get('Date')): item
        for item in final_data if isinstance(item, dict) and all(item.get(k) for k in ['User', 'Jira_ID', 'Date'])
    }
    
    update_count = 0
    append_count = 0

    for new_item in new_parsed_data:
        if not (isinstance(new_item, dict) and all(new_item.get(k) for k in ['User', 'Jira_ID', 'Date'])):
            continue
        key = (new_item['User'], new_item['Jira_ID'], new_item['Date'])
        existing_item = existing_map.get(key)
        if existing_item:
            if existing_item.get('Content') != new_item.get('Content') or existing_item.get('Comment') != new_item.get('Comment'):
                existing_item.update(new_item)
                update_count += 1
        else:
            final_data.append(new_item)
            existing_map[key] = new_item
            append_count += 1

    if len(existing_data) != len(final_data) or append_count > 0 or update_count > 0:
        await async_set_redis(redis_key, final_data)

    return final_data


def get_story_description(story_id):
    # 1. Get personal progress data
    personal_progress_key = f"story:personal_progress:{story_id}"
    personal_process_data = query_redis('GET', personal_progress_key)

    # 2. Get tags data
    tags_key = f"story:tags:{story_id}"
    tags_data = query_redis('GET', tags_key)

    # 3. Get summary data
    summary_key = f"story:summary:{story_id}"
    summary_data = query_redis('GET', summary_key)

    # If all are missing, return an error
    if not personal_process_data and not tags_data and not summary_data:
        return {"error": f"在 Redis 中未找到 story '{story_id}' 的任何相关数据（进度、标签或综述）。"}

    # 4. Combine into the final dictionary
    result = {
        "summary": summary_data if summary_data else "",
        "tags": tags_data if tags_data else [],
        "personal_process_data": personal_process_data if personal_process_data else []
    }

    return result


async def async_get_story_description(story_id):
    # 1. Get personal progress data
    personal_progress_key = f"story:personal_progress:{story_id}"
    personal_process_data = await async_query_redis('GET', personal_progress_key)

    # 2. Get tags data
    tags_key = f"story:tags:{story_id}"
    tags_data = await async_query_redis('GET', tags_key)

    # 3. Get summary data
    summary_key = f"story:summary:{story_id}"
    summary_data = await async_query_redis('GET', summary_key)

    # If all are missing, return an error
    if not personal_process_data and not tags_data and not summary_data:
        return {"error": f"在 Redis 中未找到 story '{story_id}' 的任何相关数据（进度、标签或综述）。"}

    # 4. Combine into the final dictionary
    result = {
        "summary": summary_data if summary_data else "",
        "tags": tags_data if tags_data else [],
        "personal_process_data": personal_process_data if personal_process_data else []
    }

    return result


# --- 测试调用 ---
if __name__ == "__main__":
    try:
        result = parse_to_json(markdown_data, story_id="ORI-114277")
        print(f"\n最终数据条数: {len(result)}")
        if len(result) > 0:
            print("预览第一条数据:")
            print(json.dumps(result[:1], indent=2, ensure_ascii=False))
        else:
            print("警告: 结果为空，请检查 Regex 匹配逻辑。")
        
        print("\n--- Testing story_description ---")
        story_data = get_story_description("ORI-114277")
        print(json.dumps(story_data, indent=2, ensure_ascii=False))

        story_data_not_found = get_story_description("ORI-000000")
        print(json.dumps(story_data_not_found, indent=2, ensure_ascii=False))

    except Exception as e:
        print(f"\n执行过程中遇到错误: {e}")
