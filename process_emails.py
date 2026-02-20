import tempfile
import json
import datetime
from datetime import date, timedelta
import asyncio
import subprocess
import os
import time
from fastmcp import Client

# Helper function to generate summaries
def generate_summary(email_category, email_title, email_body):
    summary = ""
    # More sophisticated AI summary generation would go here.
    # For now, using simplified logic based on category and title/body content.
    if email_category == "jira":
        if "Assigned" in email_title:
            summary = "您被指派了新的Jira任务。"
        elif "Blocked" in email_title:
            summary = "Jira任务被阻碍，请关注。"
        else:
            summary = "Jira相关更新。"
    elif email_category == "gitlab":
        if "Review request" in email_title:
            summary = "有新的合并请求待审查。"
        elif "failed" in email_title:
            summary = "GitLab流水线运行失败。"
        else:
            summary = "GitLab通知。"
    elif email_category == "wiki":
        if "Action required" in email_title:
            summary = "Wiki页面更新，需您处理。"
        else:
            summary = "Wiki页面有新变动。"
    elif email_category == "unread":
        if "HR" in email_title or "福利" in email_title:
            summary = "HR重要通知，请查收。"
        elif "calendar" in email_title or "meeting" in email_title:
            summary = "会议或日程更新。"
        else:
            summary = "新邮件待阅读。"
    
    # Truncate summary to ensure it's within 20 Chinese characters
    # This is a very rough estimate; real character counting might be needed for perfect accuracy
    if len(summary) > 20:
        summary = summary[:18] + "..." # Adjust as needed for actual char length
    
    return summary


def get_dates():
    """
    Calculates start_date and end_date based on the current day of the week.
    """
    today = date.today() # Use current date
    weekday = today.weekday() # Monday is 0 and Sunday is 6

    # Tuesday to Friday (1-4)
    if 1 <= weekday <= 4:
        start_date = today - timedelta(days=1)
        end_date = today + timedelta(days=1)
    # Monday, Saturday, Sunday (0, 5, 6)
    else:
        # Calculate days to go back to the previous Friday
        # If today is Monday (0), days_to_last_friday = (0 - 4) % 7 = -4 % 7 = 3 days ago (Friday)
        # If today is Saturday (5), days_to_last_friday = (5 - 4) % 7 = 1 day ago (Friday)
        # If today is Sunday (6), days_to_last_friday = (6 - 4) % 7 = 2 days ago (Friday)
        days_to_last_friday = (weekday + 2) % 7 + 1 # Adjusted logic for last Friday
        start_date = today - timedelta(days=days_to_last_friday)
        end_date = today + timedelta(days=1)

    return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")


async def process_emails_async():
    """
    Processes emails according to the specified logic and returns a JSON output.
    """
    start_date, end_date = get_dates()
    
    # --- Start MCP server in background ---
    mcp_process = None
    try:
        # Start the mail_mcp.py server as a subprocess
        # Using DEVNULL to prevent stdout/stderr from cluttering the agent's output
        # You might want to redirect to a log file for debugging in a real scenario
        mcp_tmp_dir = "/Users/ChuanHuang/.gemini/tmp/7eff59d515465bf446f541958aa85af7fdc3a621e0d2f13749b23f47a074f505"
        mcp_stdout_path = os.path.join(mcp_tmp_dir, "mail_mcp_stdout.log")
        mcp_stderr_path = os.path.join(mcp_tmp_dir, "mail_mcp_stderr.log")

        with open(mcp_stdout_path, "w") as fout, open(mcp_stderr_path, "w") as ferr:
            mcp_process = subprocess.Popen(
                ["python", "mcp/mail-mcp/mail_mcp.py"],
                stdout=fout,
                stderr=ferr,
                preexec_fn=os.setsid # Create a new process group
            )
        print(f"MCP server started in background. Stdout: {mcp_stdout_path}, Stderr: {mcp_stderr_path}")
        await asyncio.sleep(5)  # Give the server some time to start up

        # --- Connect to MCP server ---
        async with Client("ws://localhost:8210") as client:
            await client.ping() # Test connection
            print("Connected to MCP server.")

            # --- Call actual tool calls ---
            jira_emails = json.loads(await client.call_tool("read_emails_by_category", {"category": "jira", "start_date": start_date, "end_date": end_date}))
            gitlab_emails = json.loads(await client.call_tool("read_emails_by_category", {"category": "gitlab", "start_date": start_date, "end_date": end_date}))
            wiki_emails = json.loads(await client.call_tool("read_emails_by_category", {"category": "wiki", "start_date": start_date, "end_date": end_date}))
            unread_emails = json.loads(await client.call_tool("read_emails_by_category", {"category": "unread", "limit": 30}))
        
        all_emails = jira_emails + gitlab_emails + wiki_emails + unread_emails
        
        # --- Data Cleaning & Filtering ---
        
        # 1. Filter out Zoom emails
        cleaned_emails = [
            email for email in all_emails 
            if "zoom" not in email.get("sender", "").lower() and "zoom" not in email.get("subject", "").lower()
        ]
        
        # 2. Deduplicate
        unique_emails = {}
        for email in cleaned_emails:
            # Using a combination of id and category to handle cases where an email might genuinely appear different
            # but still be considered the "same" for deduplication if IDs are consistent across categories.
            # However, the requirement is "If the same email appears in multiple categories, only keep one."
            # So, using ID should be sufficient as it's meant to be unique per email.
            if email["id"] not in unique_emails:
                unique_emails[email["id"]] = email

        final_emails = list(unique_emails.values())
        
        # --- Analysis & UI Mapping ---
        
        items = []
        current_today = date.today()
        current_yesterday = current_today - timedelta(days=1)
        
        # Initialize counts for AI summary
        urgent_count = 0
        jira_count = 0
        gitlab_pr_count = 0
        gitlab_failed_count = 0
        mentioned_count = 0

        for email in final_emails:
            # Basic info
            title = email["subject"]
            summary = generate_summary(email["category"], title, email.get("body", ""))

            # Status flags
            body_and_subject = title + email.get("body", "")
            is_mentioned = any(name.lower() in body_and_subject.lower() for name in ["RuiZeng", "曾睿", "zengrui"])
            
            is_urgent = False
            if is_mentioned:
                is_urgent = True
                mentioned_count += 1
            
            # Additional checks for urgency based on category and keywords
            if email["category"] == "gitlab":
                if "Review" in title or "review request" in title.lower():
                    is_urgent = True
                    gitlab_pr_count += 1
                if "failed" in title:
                    is_urgent = True
                    gitlab_failed_count += 1
            elif email["category"] == "jira":
                if "Assigned" in title or "Block" in title:
                    is_urgent = True
                    jira_count += 1
            elif email["category"] == "wiki" and "Action" in title:
                is_urgent = True
            
            if is_urgent:
                urgent_count += 1
                
            # Time formatting
            # Example date string: "Tue, 10 Feb 2026 09:00:00 +0000"
            email_date_obj = datetime.datetime.strptime(email["date"], "%a, %d %b %Y %H:%M:%S %z")
            
            time_text = ""
            if email_date_obj.date() == current_today:
                time_text = email_date_obj.strftime("%I:%M %p")
            elif email_date_obj.date() == current_yesterday:
                time_text = f"昨天 {email_date_obj.strftime('%H:%M')}"
            else:
                # For dates older than yesterday, use "周X HH:MM"
                # Need to map weekday to Chinese character
                weekday_map = {
                    0: "周一", 1: "周二", 2: "周三", 3: "周四",
                    4: "周五", 5: "周六", 6: "周日"
                }
                time_text = f"{weekday_map[email_date_obj.weekday()]} {email_date_obj.strftime('%H:%M')}"


            # Source label
            source_label_map = {"jira": "Jira", "gitlab": "GitLab", "wiki": "Wiki", "unread": "Email"}
            source_label = source_label_map.get(email["category"], "Email")

            items.append({
                "id": email["id"],
                "title": title,
                "summary": summary,
                "gmail_link": email["gmail_link"],
                "is_urgent": is_urgent,
                "is_mentioned": is_mentioned,
                "time_text": time_text,
                "source_label": source_label,
                "icon_type": "email"
            })

        # Sort items by date (newest first)
        items.sort(key=lambda x: datetime.datetime.strptime(
            [e for e in final_emails if e['id'] == x['id']][0]['date'], 
            "%a, %d %b %Y %H:%M:%S %z"
        ), reverse=True)


        # AI Summary Generation
        ai_summary_parts = []
        ai_summary_parts.append(f"{current_today.strftime('%m月%d日')}，您有 {urgent_count} 个紧急事项。")
        
        if jira_count > 0:
            ai_summary_parts.append(f"其中 {jira_count} 个Jira任务需要关注。")
        if gitlab_pr_count > 0:
            ai_summary_parts.append(f"{gitlab_pr_count} 个合并请求待审查。")
        if gitlab_failed_count > 0:
            ai_summary_parts.append(f"{gitlab_failed_count} 个GitLab流水线失败。")
        if mentioned_count > 0:
            ai_summary_parts.append(f"有 {mentioned_count} 封邮件直接提及了您。")
        
        if not ai_summary_parts:
            ai_summary = f"{current_today.strftime('%m月%d日')}，今天很平静，没有发现紧急事项。"
        else:
            ai_summary = "".join(ai_summary_parts).replace("。其中", "，其中").replace("。有", "，有").strip()

        output = {
            "ai_summary": ai_summary,
            "items": items
        }
        
        print(json.dumps(output, indent=2, ensure_ascii=False))

    finally:
        # --- Shutdown MCP server ---
        if mcp_process and mcp_process.poll() is None:
            # Terminate the entire process group
            os.killpg(os.getpgid(mcp_process.pid), 9) 
            print("MCP server process terminated.")


def process_emails():
    # Entry point to run the async function
    asyncio.run(process_emails_async())

if __name__ == "__main__":
    process_emails()