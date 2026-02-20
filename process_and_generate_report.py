import json
import datetime
from concurrent.futures import ThreadPoolExecutor
import urllib.parse
import requests
import sseclient
import email
from email.header import decode_header
import re

def get_decoded_header(header_text):
    """Decodes email header, handling multiple encodings."""
    decoded_parts = decode_header(header_text)
    header_str = ""
    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            try:
                header_str += part.decode(encoding or 'utf-8', 'ignore')
            except (LookupError, TypeError):
                header_str += part.decode('utf-8', 'ignore')
        else:
            header_str += str(part)
    return header_str

def get_email_body(msg):
    """Extracts and decodes the text body from an email.message.Message object."""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            if content_type == 'text/plain' and 'attachment' not in content_disposition:
                try:
                    charset = part.get_content_charset() or 'utf-8'
                    return part.get_payload(decode=True).decode(charset, 'ignore')
                except Exception:
                    continue
    else:
        try:
            charset = msg.get_content_charset() or 'utf-8'
            return msg.get_payload(decode=True).decode(charset, 'ignore')
        except Exception:
            return ""
    return ""


def read_emails_by_category(category: str, limit: int = 20, start_date: str = None, end_date: str = None) -> list:
    """Connects to the SSE endpoint and fetches emails."""
    base_url = "http://localhost:8210/tools/read_emails_by_category"
    params = {
        "category": category,
        "limit": str(limit)
    }
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    
    try:
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()
        client = sseclient.SSEClient(response)
        
        for event in client.events():
            if event.event == 'message' and event.data:
                try:
                    data = json.loads(event.data)
                    if isinstance(data, str):
                        return json.loads(data)
                    return data
                except json.JSONDecodeError:
                    return event.data
            if event.event == 'end' or event.event == 'close':
                break

    except requests.exceptions.RequestException as e:
        print(f"Error fetching emails for category {category}: {e}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred for category {category}: {e}")
        return []
    return []

def format_time_text(email_date_str):
    """Formats the date string into a user-friendly format."""
    try:
        email_date_str = re.sub(r' \([A-Z]+\)$', '', email_date_str)
        dt = datetime.datetime.strptime(email_date_str, '%a, %d %b %Y %H:%M:%S %z')
    except ValueError:
        try:
            dt = datetime.datetime.fromisoformat(email_date_str)
        except ValueError:
            return email_date_str

    today = datetime.datetime.now(dt.tzinfo).date()
    yesterday = today - datetime.timedelta(days=1)
    
    if dt.date() == today:
        return dt.strftime("%I:%M %p")
    elif dt.date() == yesterday:
        return f"昨天 {dt.strftime('%H:%M')}"
    else:
        weekday_map = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        return f"{weekday_map[dt.weekday()]} {dt.strftime('%H:%M')}"

today = datetime.date.today()
weekday = today.weekday()

if 1 <= weekday <= 4:
    start_date = today - datetime.timedelta(days=1)
    end_date = today + datetime.timedelta(days=1)
else:
    if weekday == 0:
        days_to_last_friday = 3
    elif weekday == 5:
        days_to_last_friday = 1
    else:
        days_to_last_friday = 2
    start_date = today - datetime.timedelta(days=days_to_last_friday)
    end_date = today + datetime.timedelta(days=1)

start_date_str = start_date.strftime("%Y-%m-%d")
end_date_str = end_date.strftime("%Y-%m-%d")

categories_with_dates = ['jira', 'gitlab', 'wiki']
all_emails_raw = []

with ThreadPoolExecutor(max_workers=4) as executor:
    futures_dated = {executor.submit(read_emails_by_category, cat, start_date=start_date_str, end_date=end_date_str) for cat in categories_with_dates}
    future_unread = executor.submit(read_emails_by_category, 'unread', limit=30)
    
    for future in futures_dated:
        try:
            result = future.result()
            if result and isinstance(result, list):
                all_emails_raw.extend(result)
        except Exception as e:
            print(f"A future failed: {e}")

    try:
        result_unread = future_unread.result()
        if result_unread and isinstance(result_unread, list):
            all_emails_raw.extend(result_unread)
    except Exception as e:
        print(f"Unread future failed: {e}")

all_emails = []
processed_ids = set()
mention_count = 0
gitlab_requests = 0

for email_data in all_emails_raw:
    if not isinstance(email_data, dict) or not email_data.get('id'):
        continue
        
    email_id = email_data['id']
    if email_id in processed_ids:
        continue

    raw_email_body = email_data.get('body', '')
    msg = email.message_from_string(raw_email_body)
    
    subject = get_decoded_header(msg['Subject'])
    sender = get_decoded_header(msg['From'])

    if "zoom" in sender.lower() or "zoom" in subject.lower():
        continue
        
    body_text = get_email_body(msg)
    
    processed_ids.add(email_id)
    email_data['parsed_subject'] = subject
    email_data['parsed_sender'] = sender
    email_data['parsed_body'] = body_text
    all_emails.append(email_data)

items = []
for email_detail in all_emails:
    gmail_link = email_detail.get('gmail_link', '')
    title = email_detail.get('parsed_subject', '(无标题)')
    body = email_detail.get('parsed_body', '')
    summary = body.strip().split('\n')[0].replace('\r', '').replace('>', '').strip()
    summary = (summary[:75] + '...') if len(summary) > 75 else summary
    
    chinese_summary = f"邮件摘要: {summary[:20]}"
    if "jira" in email_detail.get('category', ''):
        chinese_summary = "Jira 任务更新"
    elif "gitlab" in email_detail.get('category', ''):
        chinese_summary = "GitLab MR 通知"
    elif "wiki" in email_detail.get('category', ''):
        chinese_summary = "Wiki 页面变更"

    is_mentioned = any(name in body or name in title for name in ["RuiZeng", "曾睿", "zengrui"])
    is_urgent = is_mentioned or \
                ('gitlab' in email_detail['category'] and any(kw in title for kw in ["Review", "Failed"])) or \
                ('jira' in email_detail['category'] and any(kw in title for kw in ["Assign", "Block"])) or \
                ('wiki' in email_detail['category'] and "Action" in title)

    if is_mentioned:
        mention_count += 1
    if 'gitlab' in email_detail['category']:
        gitlab_requests += 1

    time_text = format_time_text(email_detail.get('date', ''))

    source_label_map = {"jira": "Jira", "gitlab": "GitLab", "wiki": "Wiki"}
    source_label = source_label_map.get(email_detail.get('category'), "Email")
    
    items.append({
        "id": email_detail['id'],
        "title": title,
        "summary": chinese_summary,
        "gmail_link": gmail_link,
        "is_urgent": bool(is_urgent),
        "is_mentioned": is_mentioned,
        "time_text": time_text,
        "source_label": source_label,
        "icon_type": "email"
    })

weekday_today_map = ["一", "二", "三", "四", "五", "六", "日"]
day_of_week = weekday_today_map[today.weekday()]

summary_parts = []
if gitlab_requests > 0:
    summary_parts.append(f"{gitlab_requests} 个 GitLab 请求")
    if mention_count > 0:
        summary_parts.append(f"其中 {mention_count} 个直接艾特了你")

other_emails = len(items) - gitlab_requests
if other_emails > 0:
    summary_parts.append(f"此外还有 {other_emails} 封其他邮件")

ai_summary = f"周{day_of_week}好！"
if summary_parts:
    ai_summary += "你收到了 " + "，".join(summary_parts) + "。"
else:
    ai_summary += "收件箱很干净，没有新的动态。"

output_json = {
    "ai_summary": ai_summary,
    "items": sorted(items, key=lambda x: (not x['is_urgent'], not x['is_mentioned']))
}

print(json.dumps(output_json, indent=2, ensure_ascii=False))