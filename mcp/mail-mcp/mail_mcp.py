import imaplib
import email
import sys
import json
import shlex
import re
import datetime
from email.header import decode_header
from mcp.server.fastmcp import FastMCP

from mail_cleaner import clean_jira_emails

# 初始化 MCP Server
mcp = FastMCP("Gmail Server")

# ==========================================
# 1. 配置区域 (请修改这里！)
# ==========================================
GMAIL_USER = "rui.zeng@veeva.com"
GMAIL_APP_PASS = "hpvbqyghtjlxgzxl"

# 🗺️ 本地映射配置
CATEGORY_MAP = {
    "jira": {
        "folder": "jira",
        "query": 'FROM "jira-admin@veeva.com"'
    },
    "gitlab": {
        "folder": "gitlab",
        "query": 'FROM "gitlab@veevadev.com"'
    },
    "wiki": {
        "folder": "wiki",
        "query": 'FROM "wiki@veevadev.com"'
    },
    "calendar": {
        "folder": "INBOX",
        "query": '(OR FROM "calendar-notification@google.com" SUBJECT "Invitation")'
    },
    "unread": {
        "folder": "INBOX",
        "query": 'UNSEEN'
    },
    "all": {
        "folder": "[Gmail]/All Mail",
        "query": "ALL"
    }
}


# ==========================================
# 2. 辅助函数
# ==========================================
def log(msg):
    """日志打印到 stderr"""
    print(f"[LOG] {msg}", file=sys.stderr)


def clean_text(text, encoding):
    """解码邮件标题"""
    if isinstance(text, bytes):
        if encoding:
            try:
                return text.decode(encoding)
            except LookupError:
                return text.decode('utf-8', errors='ignore')
        return text.decode('utf-8', errors='ignore')
    return text


def parse_imap_folder_list(folder_bytes_list):
    """解析 IMAP list 返回的复杂格式"""
    folders = []
    for f in folder_bytes_list:
        try:
            decoded = f.decode('utf-8')
            parts = shlex.split(decoded)
            folder_name = parts[-1]
            folders.append(folder_name)
        except Exception:
            folders.append(str(f))
    return folders


def _convert_to_imap_date(date_str):
    """
    将 YYYY-MM-DD 格式转换为 IMAP 需要的 DD-Mon-YYYY 格式。
    例如: 2026-01-25 -> 25-Jan-2026
    """
    try:
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        # 注意：这里依赖系统 Locale 为英文，如果系统是中文环境，%b 可能会输出中文月份导致 IMAP 报错
        # 建议在运行环境确保 export LC_TIME="en_US.UTF-8"
        return dt.strftime("%d-%b-%Y")
    except ValueError:
        return None

def _create_gmail_link(gm_msgid_str):
    """
    根据 Gmail 的 X-GM-MSGID 创建一个跳转到邮件的链接。
    """
    if not gm_msgid_str:
        return ""
    try:
        # 将字符串 ID 转换为整数，然后转换为十六进制，并去掉 '0x' 前缀
        hex_id = hex(int(gm_msgid_str))[2:]
        return f"https://mail.google.com/mail/u/0/#all/{hex_id}"
    except (ValueError, TypeError) as e:
        log(f"创建 Gmail 链接失败: {e}")
        return ""


# ==========================================
# 3. 工具：列出文件夹
# ==========================================
@mcp.tool()
def list_mailboxes() -> str:
    """列出 Gmail 中所有的文件夹/标签名称。"""
    log("正在获取文件夹列表...")
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_APP_PASS)

        status, response = mail.list()

        if status != "OK":
            return json.dumps({"error": "获取列表失败"})

        folder_names = parse_imap_folder_list(response)
        mail.logout()
        return json.dumps(folder_names, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)})


# ==========================================
# 4. 工具：按分类读取邮件 (修改后)
# ==========================================
@mcp.tool()
def read_emails_by_category(category: str = "jira", limit: int = 20,
                            start_date: str = None, end_date: str = None) -> str:
    """
    根据预设分类读取邮件，支持日期范围筛选。

    Args:
        category: 类别，支持 'jira', 'gitlab', 'calendar', 'unread', 'all'。
        limit: 返回数量 (默认: 5)。如果指定了日期范围，此限制可能被放宽。
        start_date: 起始日期 (包含)，格式 "YYYY-MM-DD" (例如 "2026-01-01")。
        end_date: 结束日期 (不包含)，格式 "YYYY-MM-DD"。IMAP 的 BEFORE 语义通常不包含该日期。
    """
    # 1. 读取本地映射配置
    config = CATEGORY_MAP.get(category)
    if not config:
        log(f"⚠️ 未知分类 '{category}'，回退到 INBOX/UNSEEN")
        config = CATEGORY_MAP["unread"]

    target_folder = config["folder"]
    query = config["query"]

    # 2. 处理日期范围逻辑
    date_filter_active = False

    if start_date:
        imap_start = _convert_to_imap_date(start_date)
        if imap_start:
            query = f'({query}) SINCE "{imap_start}"'
            date_filter_active = True
        else:
            log(f"⚠️ start_date 格式错误: {start_date}，已忽略")

    if end_date:
        imap_end = _convert_to_imap_date(end_date)
        if imap_end:
            query = f'({query}) BEFORE "{imap_end}"'
            date_filter_active = True
        else:
            log(f"⚠️ end_date 格式错误: {end_date}，已忽略")

    # 如果启用了日期筛选，默认扩大 limit 以获取该时间段内的所有邮件
    if date_filter_active:
        limit = 9999
        log(f"📅 启用日期筛选: Start={start_date}, End={end_date}")

    log(f"🔍 执行: Category={category} | Folder={target_folder} | Query={query} | Limit={limit}")

    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_APP_PASS)

        resp, _ = mail.select(f'"{target_folder}"')
        if resp != 'OK':
            return json.dumps({"error": f"找不到文件夹 '{target_folder}'"})

        # 3. 搜索
        status, messages = mail.search(None, query)

        if not messages[0]:
            return json.dumps([])  # 空结果

        email_ids = messages[0].split()

        # 4. 获取邮件 (根据 limit 截取)
        fetch_limit = min(len(email_ids), limit)
        latest_ids = email_ids[-fetch_limit:]
        latest_ids.reverse()  # 倒序，最新的在前面

        email_list = []

        for e_id in latest_ids:
            try:
                id_str = e_id.decode('utf-8')
                # Note: We now ask for X-GM-MSGID, a Gmail-specific message ID
                _, msg_data = mail.fetch(e_id, "(X-GM-MSGID RFC822)")

                gm_msgid = None

                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        # response_part[0] contains headers like b'1 (X-GM-MSGID 123...)'
                        header_part = response_part[0]
                        # response_part[1] is the email content
                        body_part = response_part[1]

                        match = re.search(br'X-GM-MSGID (\d+)', header_part)
                        if match:
                            gm_msgid = match.group(1).decode()

                        msg = email.message_from_bytes(body_part)

                        # 解析标题
                        subject_header = msg["Subject"]
                        if subject_header:
                            subject_val, encoding = decode_header(subject_header)[0]
                            subject = clean_text(subject_val, encoding)
                        else:
                            subject = "(无标题)"

                        # 解析发件人
                        from_val = msg.get("From", "(未知)")
                        # 解析时间
                        date_val = msg.get("Date", "")

                        # 新增：创建 gmail 链接
                        gmail_link = _create_gmail_link(gm_msgid)

                        email_list.append({
                            "id": id_str,
                            "category": category,
                            "sender": from_val,
                            "subject": subject,
                            "date": date_val,
                            "gmail_link": gmail_link,
                            "body": msg.as_string()
                        })
            except Exception as e:
                log(f"解析邮件 {e_id} 失败: {e}")
                continue

        mail.close()
        mail.logout()

        return json.dumps(clean_jira_emails(email_list), ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def mark_email_as_read(email_ids: list[str]) -> str:
    """将指定的邮件标记为已读 (Seen)。"""
    log(f"正在将邮件标记为已读: {email_ids}")

    if not email_ids:
        return "⚠️ 没有提供邮件 ID。"

    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_APP_PASS)
        mail.select("inbox")

        id_set = ",".join(email_ids)
        status, _ = mail.store(id_set, '+FLAGS', '\\Seen')

        mail.close()
        mail.logout()

        if status == 'OK':
            return f"✅ 成功将 {len(email_ids)} 封邮件标记为已读。"
        else:
            return f"❌ 标记失败，状态: {status}"

    except Exception as e:
        return f"❌ 操作错误: {str(e)}"


if __name__ == "__main__":
    mcp.settings.port = 8081
    mcp.run(transport='sse')
    # mcp.run()
    # print(read_emails_by_category(category='jira', limit=1, start_date="2026-01-29",
    #                               end_date="2026-01-30"))
