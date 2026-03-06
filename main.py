# main.py
import os
import sys
import requests
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
import smtplib
from http import HTTPStatus
import time
import traceback

# ========== 配置 ==========
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
TO_EMAIL = os.getenv("TO_EMAIL")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))

# ========== 工具函数 ==========
def fetch_github_trending():
    print("🔍 正在抓取 GitHub 今日热门项目...")
    url = "https://github.com/trending?since=daily"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; GitHub Digest Bot)"}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"❌ 抓取失败: {e}")
        return []

    soup = BeautifulSoup(resp.text, 'html.parser')
    repos = []
    for article in soup.select('article'):
        name_tag = article.select_one('h2 a')
        if not name_tag:
            continue
        name = ''.join(name_tag.stripped_strings).replace(' ', '')
        link = "https://github.com" + name_tag['href']
        desc_tag = article.select_one('p')
        description = desc_tag.get_text(strip=True) if desc_tag else ""
        repos.append({"name": name, "link": link, "description": description})
        if len(repos) >= 10:
            break
    print(f"✅ 成功获取 {len(repos)} 个项目")
    return repos

def send_email(subject, body):
    print("📧 正在发送邮件...")
    if not all([EMAIL_USER, EMAIL_PASS, TO_EMAIL]):
        raise ValueError("邮箱配置缺失！请检查 Secrets。")

    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = EMAIL_USER
    msg['To'] = TO_EMAIL

    try:
        if SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=15)
        else:
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15)
            server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, [TO_EMAIL], msg.as_string())
        server.quit()
        print("✅ 邮件发送成功！")
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        traceback.print_exc()
        raise

# ========== 主流程 ==========
def main():
    print("🚀 GitHub Daily Digest 开始运行...")
    
    # 1. 抓取项目
    projects = fetch_github_trending()
    if not projects:
        print("⚠️ 未获取到任何项目，跳过分析。")
        return

    # 2. 为每个项目生成「用途」和「应用示例」
    project_details = []
    for p in projects:
        try:
            prompt = (
                f"你是一位技术布道师，请用中文回答以下关于 GitHub 项目的问题。\n"
                f"项目名称：{p['name']}\n"
                f"项目描述：{p['description']}\n\n"
                f"请严格按以下格式输出（不要任何额外文字）：\n"
                f"【用途】\n"
                f"<一句话说明项目是做什么的，不超过 100 字>\n"
                f"【示例】\n"
                f"<举一个具体的应用场景，比如“可用于...”或“适合在...场景中使用”，不超过 100 字>"
            )
            from dashscope import Generation
            response = Generation.call(
                model="qwen-max",
                prompt=prompt,
                api_key=DASHSCOPE_API_KEY,
                max_tokens=300
            )
            if response.status_code == HTTPStatus.OK:
                text = response.output.text.strip()
                if "【用途】" in text and "【示例】" in text:
                    parts = text.split("【示例】", 1)
                    purpose = parts[0].replace("【用途】", "").strip()
                    example = parts[1].strip() if len(parts) > 1 else "暂无示例"
                else:
                    # 回退：整段当作用途
                    purpose = text
                    example = "（未能生成应用示例）"
            else:
                purpose = p['description'] or "暂无描述"
                example = "（分析失败）"
        except Exception as e:
            print(f"⚠️ 项目 {p['name']} 分析失败: {e}")
            purpose = p['description'] or "暂无描述"
            example = "（异常）"

        project_details.append({
            "name": p['name'],
            "link": p['link'],
            "purpose": purpose,
            "example": example
        })

    # 3. 构建清晰、宽松的邮件正文
    project_lines = []
    for i, proj in enumerate(project_details, 1):
        project_lines.append(f"{i}. 【{proj['name']}】")
        project_lines.append(f"   {proj['link']}")
        project_lines.append("")
        project_lines.append(f"   💡 {proj['purpose']}")
        project_lines.append(f"   🌰 {proj['example']}")
        project_lines.append("")  # 项目之间空一行

    analysis_text = "\n".join(project_lines).rstrip()

    # 4. 构建最终邮件
    subject = "🚀 GitHub 每日热门项目速览"
    body = f"""您好！

以下是 {time.strftime('%Y年%m月%d日')} GitHub 最热门的开源项目（由 Qwen-Max 自动分析）：

{'='*60}

{analysis_text}

{'='*60}
"""
    send_email(subject, body)
    print("🎉 全部任务完成！")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"💥 程序异常退出: {e}")
        traceback.print_exc()
        sys.exit(1)
