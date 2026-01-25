import re
import json
import os

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
    # 1. 核心解析逻辑
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
    # 2. 文件系统操作逻辑
    # ---------------------------------------------------------

    base_dir = "/Users/ChuanHuang/Desktop/project/hackathon-personal-assistant/analyze_data"
    sprint_dir = os.path.join(base_dir, sprint_id)

    if not os.path.exists(sprint_dir):
        print(f"文件夹不存在，正在创建: {sprint_dir}")
        os.makedirs(sprint_dir, exist_ok=True)

    json_file_path = os.path.join(sprint_dir, f"{story_id}.json")

    final_data = []

    if os.path.exists(json_file_path):
        print(f"发现已有文件，正在读取合并: {json_file_path}")
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                if isinstance(existing_data, list):
                    final_data = existing_data
                else:
                    final_data = []
        except Exception as e:
            print(f"读取旧文件出错: {e}, 将覆盖重写。")
            final_data = []
    else:
        print(f"文件不存在，将创建新文件: {json_file_path}")

    # 数据追加逻辑
    append_count = 0
    # 为了对比去重，我们将 new_item 与 final_data 中的每一项进行对比
    # 注意：字典比较顺序无关，但内容必须完全一致
    for new_item in new_parsed_data:
        if new_item not in final_data:
            final_data.append(new_item)
            append_count += 1

    if append_count > 0:
        print(f"成功追加 {append_count} 条新记录。")
    else:
        print("没有新记录需要追加（数据已存在 或 解析结果为空）。")

    # 写入最终结果
    with open(json_file_path, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, indent=2, ensure_ascii=False)

    return final_data


def get_story_description(sprint_name, story_id):
    base_dir = "/Users/ChuanHuang/Desktop/project/hackathon-personal-assistant/analyze_data"
    sprint_path = os.path.join(base_dir, sprint_name)
    if not os.path.isdir(sprint_path):
        return {"error": "sprint未完成分析"}

    story_file_path = os.path.join(sprint_path, f"{story_id}.json")
    if not os.path.isfile(story_file_path):
        return {"error": "story未完成分析"}

    with open(story_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return data


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
        story_data = story_description("Plum 25R3.2 Sprint 2", "ORI-114277")
        print(json.dumps(story_data, indent=2, ensure_ascii=False))

        story_data_not_found = story_description("Plum 25R3.2 Sprint 2", "ORI-000000")
        print(json.dumps(story_data_not_found, indent=2, ensure_ascii=False))

        sprint_not_found = story_description("Unknown Sprint", "ORI-114277")
        print(json.dumps(sprint_not_found, indent=2, ensure_ascii=False))

    except Exception as e:
        print(f"\n执行过程中遇到错误: {e}")
