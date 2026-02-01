import json
import email
from email.header import decode_header
from bs4 import BeautifulSoup
import re


def clean_jira_emails(raw_data_list):
    cleaned_list = []

    for item in raw_data_list:
        # 1. 基础元数据
        subject = clean_header(item.get('subject', ''))
        sender = clean_header(item.get('sender', ''))

        # 2. 解析 Raw Email Body
        raw_body = item.get('body', '')
        msg = email.message_from_string(raw_body)

        text_content = ""

        # 3. 提取正文
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))

                if "attachment" not in content_disposition:
                    if content_type == "text/html":
                        payload = part.get_payload(decode=True)
                        if payload:
                            html_payload = payload.decode(part.get_content_charset() or 'utf-8',
                                                          errors='ignore')
                            text_content = html_to_text(html_payload)
                            break
                    elif content_type == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            text_content = payload.decode(part.get_content_charset() or 'utf-8',
                                                          errors='ignore')
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                text_content = payload.decode(msg.get_content_charset() or 'utf-8', errors='ignore')
                if msg.get_content_type() == "text/html":
                    text_content = html_to_text(text_content)

        # 4. 二次清洗：去除换行符，合并为一行
        text_content = post_process_jira_text(text_content)

        cleaned_list.append({
            "id": item.get('id'),
            "sender": sender,
            "subject": subject,
            "content": text_content,
            "gmail_link": item.get('gmail_link')
        })

    return cleaned_list


def clean_header(header_text):
    if not header_text:
        return ""
    decoded_fragments = decode_header(header_text)
    header_str = ""
    for bytes_fragment, encoding in decoded_fragments:
        if isinstance(bytes_fragment, bytes):
            header_str += bytes_fragment.decode(encoding or 'utf-8', errors='ignore')
        else:
            header_str += str(bytes_fragment)
    return header_str


def html_to_text(html_content):
    if not html_content:
        return ""
    soup = BeautifulSoup(html_content, "html.parser")

    # 移除干扰元素
    for script in soup(["script", "style", "img", "head", "meta", "link"]):
        script.decompose()

    # 获取文本，separator=' ' 保证标签之间有空格
    text = soup.get_text(separator=' ')
    return text


def post_process_jira_text(text):
    """移除 Jira 废话，并将所有换行符替换为空格"""
    if not text:
        return ""

    # 1. 移除页脚
    if "This message was sent by Atlassian Jira" in text:
        text = text.split("This message was sent by Atlassian Jira")[0]

    # 2. 移除特定关键词
    text = re.sub(r'Add Comment', '', text)
    text = re.sub(r'Veeva Orion /', '', text)

    # 3. 核心修改：将所有换行符、制表符、多余空格 替换为 单个空格
    # split() 不带参数时，会把 \n \t 和空格都当做分隔符，并去除空字符串
    normalized_text = ' '.join(text.split())

    return normalized_text